"""
Supabase (PostgreSQL) データベース接続・CRUD層。
supabase-py (REST API) を使用してダムデータ・雨量データの読み書きを行う。
"""
import os
import pandas as pd
from supabase import create_client, Client

_supabase_client: Client | None = None


def _get_supabase_client() -> Client:
    """
    Supabaseクライアントを取得する（シングルトン）。
    初回呼び出し時にインスタンスを生成し、以降はキャッシュを返す。
    .env / 環境変数 → Streamlit Secrets の順にフォールバック。
    """
    global _supabase_client
    if _supabase_client is not None:
        return _supabase_client

    url = None
    key = None

    # 1. .env ファイル / 環境変数から取得を試みる
    from dotenv import load_dotenv
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    # 2. Streamlit Secrets からのフォールバック
    if not url or not key:
        try:
            import streamlit as st
            url = url or st.secrets.get("SUPABASE_URL")
            key = key or st.secrets.get("SUPABASE_KEY")
        except Exception:
            pass

    if not url or not key:
        raise RuntimeError(
            "Supabase の接続情報が見つかりません。"
            "SUPABASE_URL と SUPABASE_KEY を環境変数または Streamlit Secrets に設定してください。"
        )

    _supabase_client = create_client(url, key)
    return _supabase_client


def _safe_float(val) -> float | None:
    """値を float に変換する。'-' / '$' / 変換不可 → None。"""
    s = str(val).strip()
    if s in ("-", "$", "", "nan", "None"):
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _vectorized_parse_timestamp(df: pd.DataFrame) -> pd.Series:
    """
    DataFrameの0列目(日付)と1列目(時刻)からUTC基準のpd.Timestampシリーズを生成する（ベクトル演算）。
    """
    # 日付と時刻を結合
    datetime_str = df["0"].astype(str).str.strip() + " " + df["1"].astype(str).str.strip()
    
    # 24:00 を 00:00 に置換し、翌日扱いにするフラグを作成
    is_2400 = df["1"].astype(str).str.strip() == "24:00"
    datetime_str = datetime_str.str.replace(" 24:00", " 00:00")
    
    try:
        # 文字列から datetime へ変換
        dt_series = pd.to_datetime(datetime_str, format="mixed", errors="coerce")
        # 24:00 だった行に1日加算
        dt_series = dt_series + pd.to_timedelta(is_2400.astype(int), unit="d")
        # JST(UTC+9) として localize してから UTC に変換
        return dt_series.dt.tz_localize("Asia/Tokyo").dt.tz_convert("UTC")
    except Exception:
        return pd.Series(pd.NaT, index=df.index)



def _batch_upsert(table_name: str, station_id: str, records: list[dict]) -> int:
    """
    Supabase APIのサイズ制限対策として、レコードのリストを500件ずつのバッチでUPSERTする。
    """
    if not records:
        print(f"[db] {table_name}: 挿入対象レコードなし (station_id={station_id})")
        return 0

    client = _get_supabase_client()
    BATCH_SIZE = 500
    total_count = 0
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i:i + BATCH_SIZE]
        try:
            result = client.table(table_name).upsert(batch).execute()
            count = len(result.data) if result.data else 0
            total_count += count
            print(f"[db] {table_name}: バッチ {i//BATCH_SIZE + 1} - {count}件 UPSERT")
        except Exception as e:
            print(f"[db] {table_name}: バッチ {i//BATCH_SIZE + 1} エラー: {e}")
            raise

    print(f"[db] {table_name}: 合計 {total_count}件 UPSERT完了 (station_id={station_id})")
    return total_count


def _prepare_upsert_df(df: pd.DataFrame, latest_ts: pd.Timestamp | None = None) -> pd.DataFrame:
    """
    UPSERT用にDataFrameのタイムスタンプをパースし、latest_ts以降のデータのみにフィルタリングする。
    """
    df = df.copy()
    df["parsed_ts"] = _vectorized_parse_timestamp(df)
    df = df.dropna(subset=["parsed_ts"])

    if latest_ts is not None:
        df = df[df["parsed_ts"] > latest_ts]
    return df


def _upsert_data(
    table_name: str,
    station_id: str,
    df: pd.DataFrame,
    col_mapping: dict[str, str],
    required_col: str,
    latest_ts: pd.Timestamp | None = None
) -> int:
    """
    データ種別によらず、汎用的にDataFrameをパースして指定テーブルにUPSERTする。
    col_mapping: DBのカラム名 -> 元DataFrame(DATファイル)の列インデックス のマッピング
    required_col: この列がNoneなら未受信行としてスキップするDBのカラム名
    """
    df = _prepare_upsert_df(df, latest_ts)

    records = []
    for _, row in df.iterrows():
        # station_id と timestamp はDBスキーマ側の複合主キー(PK)であるためそこからrecordを作成する。
        record = {
            "station_id": station_id,
            "timestamp": row["parsed_ts"].isoformat(),
        }

        # 設定されたマッピングに従ってデータを抽出        
        for db_col, df_col in col_mapping.items():
            record[db_col] = _safe_float(row.get(df_col))

        # 必須データがNoneの場合は未受信行としてスキップ
        if record.get(required_col) is None:
            continue

        records.append(record)

    return _batch_upsert(table_name, station_id, records)


def upsert_dam_data(station_id: str, df: pd.DataFrame, latest_ts: pd.Timestamp | None = None) -> int:
    """
    DataFrameをdam_dataテーブルにUPSERTする。
    """
    col_mapping = {
        "rainfall": "2",
        "volume": "4",
        "inflow": "6",
        "outflow": "8",
        "storage_rate": "10",
    }
    return _upsert_data("dam_data", station_id, df, col_mapping, required_col="volume", latest_ts=latest_ts)


def upsert_rain_data(station_id: str, df: pd.DataFrame, latest_ts: pd.Timestamp | None = None) -> int:
    """
    DataFrameをrain_dataテーブルにUPSERTする。
    """
    col_mapping = {
        "rainfall": "2",
    }
    return _upsert_data("rain_data", station_id, df, col_mapping, required_col="rainfall", latest_ts=latest_ts)


def _fetch_records_paginated(table_name: str, station_id: str):
    """
    1000件の取得制限を回避するため、ページネーションでデータを順次取得する（ジェネレータ）。
    """
    client = _get_supabase_client()
    page_size = 1000
    start = 0

    while True:
        result = (
            client.table(table_name)
            .select("*")
            .eq("station_id", station_id)
            .order("timestamp")
            .range(start, start + page_size - 1)
            .execute()
        )
        if not result.data:
            break
            
        yield from result.data
        
        if len(result.data) < page_size:
            break
        start += page_size


def load_data(table_name: str, station_id: str) -> pd.DataFrame:
    """
    指定テーブルからデータを全件取得し、DataFrameに変換して返す。
    """
    all_data = list(_fetch_records_paginated(table_name, station_id))

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def get_latest_timestamp(table_name: str, station_id: str) -> pd.Timestamp | None:
    """
    指定テーブル・観測所IDの最新タイムスタンプを返す。
    データが存在しない場合は None を返す。
    """
    client = _get_supabase_client()
    result = (
        client.table(table_name)
        .select("timestamp")
        .eq("station_id", station_id)
        .order("timestamp", desc=True)
        .limit(1)
        .execute()
    )
    if result.data:
        return pd.to_datetime(result.data[0]["timestamp"])
    return None

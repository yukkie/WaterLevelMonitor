"""
Supabase (PostgreSQL) データベース接続・CRUD層。
supabase-py (REST API) を使用してダムデータ・雨量データの読み書きを行う。
"""
import os
import pandas as pd
from supabase import create_client, Client


def _get_supabase_client() -> Client:
    """
    Supabaseクライアントを取得する。
    .env / 環境変数 → Streamlit Secrets の順にフォールバック。
    """
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

    return create_client(url, key)


def _safe_float(val) -> float | None:
    """値を float に変換する。'-' / '$' / 変換不可 → None。"""
    s = str(val).strip()
    if s in ("-", "$", "", "nan", "None"):
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _parse_timestamp(date_str: str, time_str: str) -> str:
    """
    日付文字列と時刻文字列からISO 8601形式のタイムスタンプを生成する。
    '24:00' は翌日の '00:00' として扱う。
    """
    date_str = str(date_str).strip()
    time_str = str(time_str).strip()

    dt = pd.to_datetime(date_str)
    if time_str == "24:00":
        time_str = "00:00"
        dt += pd.Timedelta(days=1)

    timestamp = pd.to_datetime(f"{dt.strftime('%Y-%m-%d')} {time_str}")
    return timestamp.isoformat()


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
            print(f"[db] {table_name}: バッチ {i//BATCH_SIZE + 1} — {count}件 UPSERT")
        except Exception as e:
            print(f"[db] {table_name}: バッチ {i//BATCH_SIZE + 1} エラー: {e}")
            raise

    print(f"[db] {table_name}: 合計 {total_count}件 UPSERT完了 (station_id={station_id})")
    return total_count


def upsert_dam_data(station_id: str, df: pd.DataFrame) -> int:
    """
    DataFrameをdam_dataテーブルにUPSERTする。
    Returns: 挿入/更新された行数
    """
    records = []
    for _, row in df.iterrows():
        rainfall = _safe_float(row.get("2"))
        volume = _safe_float(row.get("4"))
        inflow = _safe_float(row.get("6"))
        outflow = _safe_float(row.get("8"))
        storage_rate = _safe_float(row.get("10"))

        # 主要データ（volume）がNoneの場合は未受信行としてスキップ
        if volume is None:
            continue

        try:
            ts = _parse_timestamp(row["0"], row["1"])
        except Exception:
            continue

        records.append({
            "station_id": station_id,
            "timestamp": ts,
            "rainfall": rainfall,
            "volume": volume,
            "inflow": inflow,
            "outflow": outflow,
            "storage_rate": storage_rate,
        })

    return _batch_upsert("dam_data", station_id, records)


def upsert_rain_data(station_id: str, df: pd.DataFrame) -> int:
    """
    DataFrameをrain_dataテーブルにUPSERTする。
    Returns: 挿入/更新された行数
    """
    records = []
    for _, row in df.iterrows():
        rainfall = _safe_float(row.get("2"))

        # 雨量がNoneの場合は未受信行としてスキップ
        if rainfall is None:
            continue

        try:
            ts = _parse_timestamp(row["0"], row["1"])
        except Exception:
            continue

        records.append({
            "station_id": station_id,
            "timestamp": ts,
            "rainfall": rainfall,
        })

    return _batch_upsert("rain_data", station_id, records)


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


def _load_data_as_dataframe(table_name: str, station_id: str) -> pd.DataFrame:
    """
    指定テーブルからデータを全件取得し、DataFrameに変換して返す。
    """
    all_data = list(_fetch_records_paginated(table_name, station_id))

    if not all_data:
        return pd.DataFrame()

    df = pd.DataFrame(all_data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def load_dam_data(station_id: str) -> pd.DataFrame:
    """
    dam_dataテーブルからデータを読み込んでDataFrameとして返す。
    """
    return _load_data_as_dataframe("dam_data", station_id)


def load_rain_data(station_id: str) -> pd.DataFrame:
    """
    rain_dataテーブルからデータを読み込んでDataFrameとして返す。
    """
    return _load_data_as_dataframe("rain_data", station_id)

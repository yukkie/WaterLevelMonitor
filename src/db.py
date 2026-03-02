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
    Streamlit Secrets → 環境変数 の順にフォールバック。
    """
    url = None
    key = None

    # Streamlit Secrets から取得を試みる
    try:
        import streamlit as st
        url = st.secrets.get("SUPABASE_URL")
        key = st.secrets.get("SUPABASE_KEY")
    except Exception:
        pass

    # 環境変数からのフォールバック
    if not url:
        url = os.environ.get("SUPABASE_URL")
    if not key:
        key = os.environ.get("SUPABASE_KEY")

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


def upsert_dam_data(station_id: str, df: pd.DataFrame) -> int:
    """
    DataFrameをdam_dataテーブルにUPSERTする。
    Returns: 挿入/更新された行数
    """
    client = _get_supabase_client()

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

    if not records:
        print(f"[db] dam_data: 挿入対象レコードなし (station_id={station_id})")
        return 0

    # バッチUPSERT（Supabase APIのサイズ制限対策、500件ずつ）
    BATCH_SIZE = 500
    total_count = 0
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i:i + BATCH_SIZE]
        try:
            result = client.table("dam_data").upsert(batch).execute()
            count = len(result.data) if result.data else 0
            total_count += count
            print(f"[db] dam_data: バッチ {i//BATCH_SIZE + 1} — {count}件 UPSERT")
        except Exception as e:
            print(f"[db] dam_data: バッチ {i//BATCH_SIZE + 1} エラー: {e}")
            raise

    print(f"[db] dam_data: 合計 {total_count}件 UPSERT完了 (station_id={station_id})")
    return total_count


def upsert_rain_data(station_id: str, df: pd.DataFrame) -> int:
    """
    DataFrameをrain_dataテーブルにUPSERTする。
    Returns: 挿入/更新された行数
    """
    client = _get_supabase_client()

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

    if not records:
        print(f"[db] rain_data: 挿入対象レコードなし (station_id={station_id})")
        return 0

    # バッチUPSERT（Supabase APIのサイズ制限対策、500件ずつ）
    BATCH_SIZE = 500
    total_count = 0
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i:i + BATCH_SIZE]
        try:
            result = client.table("rain_data").upsert(batch).execute()
            count = len(result.data) if result.data else 0
            total_count += count
            print(f"[db] rain_data: バッチ {i//BATCH_SIZE + 1} — {count}件 UPSERT")
        except Exception as e:
            print(f"[db] rain_data: バッチ {i//BATCH_SIZE + 1} エラー: {e}")
            raise

    print(f"[db] rain_data: 合計 {total_count}件 UPSERT完了 (station_id={station_id})")
    return total_count


def load_dam_data(station_id: str) -> pd.DataFrame:
    """
    dam_dataテーブルからデータを読み込んでDataFrameとして返す。
    """
    client = _get_supabase_client()
    result = (
        client.table("dam_data")
        .select("*")
        .eq("station_id", station_id)
        .order("timestamp")
        .execute()
    )

    if not result.data:
        return pd.DataFrame()

    df = pd.DataFrame(result.data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def load_rain_data(station_id: str) -> pd.DataFrame:
    """
    rain_dataテーブルからデータを読み込んでDataFrameとして返す。
    """
    client = _get_supabase_client()
    result = (
        client.table("rain_data")
        .select("*")
        .eq("station_id", station_id)
        .order("timestamp")
        .execute()
    )

    if not result.data:
        return pd.DataFrame()

    df = pd.DataFrame(result.data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

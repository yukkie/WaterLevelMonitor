"""
データストレージ (Load層)。
Supabase (PostgreSQL) への接続と、変換済みデータのバッチUPSERT処理(CRUD)を提供する。
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


def _save_to_db(table_name: str, station_id: str, records: list[dict]) -> int:
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


def _get_latest_timestamp(table_name: str, station_id: str) -> pd.Timestamp | None:
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

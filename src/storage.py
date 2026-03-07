"""
データストレージ層。
Supabase DB への書き込みを行う。
"""
from db import upsert_dam_data, upsert_rain_data


def save_to_db(dam_id: str, dam_type: str, df, latest_ts=None) -> int:
    """
    DataFrameをSupabase DBに保存する。
    """
    if dam_type == "rain":
        return upsert_rain_data(dam_id, df, latest_ts=latest_ts)
    else:
        return upsert_dam_data(dam_id, df, latest_ts=latest_ts)

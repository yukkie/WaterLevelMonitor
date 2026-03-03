"""
データパイプライン。
スクレイピング → DB保存 → DB読み込みの一連の処理を提供する。
"""
import pandas as pd
from config import DamConfig
from scraper import fetch_dam_data
from storage import save_to_db
from db import load_dam_data, load_rain_data


def fetch_and_store(dam_config: DamConfig) -> pd.DataFrame:
    """
    データを取得し、DBに保存して結果のDataFrameを返す。
    """
    new_df = fetch_dam_data(dam_config)

    # DB に保存
    save_to_db(dam_config.id, dam_config.type, new_df)

    # DBから最新データを読み込んで返す
    return load_data(dam_config)


def load_data(dam_config: DamConfig) -> pd.DataFrame:
    """
    DBからデータを読み込んでDataFrameとして返す。
    """
    if dam_config.type == "rain":
        return load_rain_data(dam_config.id)
    else:
        return load_dam_data(dam_config.id)

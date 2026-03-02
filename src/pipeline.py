"""
データパイプライン。
スクレイピング → DB保存 → DB読み込みの一連の処理を提供する。
"""
import os
import pandas as pd
from config import DamConfig
from scraper import fetch_dam_data
from storage import save_to_db
from db import load_dam_data, load_rain_data


def resolve_data_dir(data_dir="data") -> str:
    """
    dataディレクトリの絶対パスを解決する。
    src/ 内から実行された場合やプロジェクトルートから実行された場合の両方に対応。
    """
    if os.path.exists(data_dir):
        return data_dir
    if os.path.basename(os.getcwd()) == "src":
        parent = os.path.join("..", data_dir)
        if os.path.exists(parent):
            return parent
    project_data = os.path.join(os.getcwd(), "data")
    if os.path.exists(project_data):
        return project_data
    return data_dir


def fetch_and_store(dam_config: DamConfig, data_dir="data") -> pd.DataFrame:
    """
    データを取得し、DBに保存して結果のDataFrameを返す。
    """
    new_df = fetch_dam_data(dam_config)
    
    # DB に保存（メイン）
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

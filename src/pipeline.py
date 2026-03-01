import os
import pandas as pd
from config import DamConfig
from scraper import fetch_dam_data
from storage import update_local_csv


def resolve_data_dir(data_dir="data") -> str:
    """
    dataディレクトリの絶対パスを解決する。
    src/ 内から実行された場合やプロジェクトルートから実行された場合の両方に対応。
    """
    if os.path.exists(data_dir):
        return data_dir
    # src/ 内から実行された場合
    if os.path.basename(os.getcwd()) == "src":
        parent = os.path.join("..", data_dir)
        if os.path.exists(parent):
            return parent
    # プロジェクトルートの data/ を探す
    project_data = os.path.join(os.getcwd(), "data")
    if os.path.exists(project_data):
        return project_data
    # どこにも見つからなければデフォルトをそのまま返す（後で作成される）
    return data_dir


def fetch_and_store(dam_config: DamConfig, data_dir="data") -> pd.DataFrame:
    """
    データを取得し、ローカルCSVに保存して結果のDataFrameを返す。
    """
    data_dir = resolve_data_dir(data_dir)
    new_df = fetch_dam_data(dam_config)
    return update_local_csv(dam_config.id, new_df, data_dir=data_dir)


def load_data(dam_config: DamConfig, data_dir="data") -> pd.DataFrame:
    """
    ローカルCSVからデータを読み込んでDataFrameとして返す。
    ファイルが存在しない場合は空のDataFrameを返す。
    """
    data_dir = resolve_data_dir(data_dir)
    csv_path = os.path.join(data_dir, f"{dam_config.id}.csv")

    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        df.columns = df.columns.astype(str)
        return df
    else:
        return pd.DataFrame()

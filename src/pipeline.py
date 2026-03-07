"""
データパイプライン。
スクレイピング → DB保存 → DB読み込みの一連の処理を提供する。
"""
import pandas as pd
from config import DamConfig
from scraper import fetch_dam_data
from storage import save_to_db
from db import load_data as db_load_data, get_latest_timestamp


def fetch_and_store(dam_config: DamConfig, latest_ts=None) -> pd.DataFrame:
    """
    データを取得し、DBに保存して結果のDataFrameを返す。
    latest_tsが与えられた場合、差分のみを保存する。
    """
    new_df = fetch_dam_data(dam_config)

    # DB に保存 (差分のみ)
    save_to_db(dam_config.id, dam_config.type, new_df, latest_ts=latest_ts)

    # DBから最新データを読み込んで返す
    return load_data(dam_config)


def check_and_fetch(dam_config: DamConfig, throttle_minutes: int = 20) -> bool:
    """
    DBの最終タイムスタンプを確認し、throttle_minutes 以上経過していれば
    fetch_and_store を実行する。Streamlit非依存。

    Returns:
        True  : スクレイピングを実行した
        False : 閾値以内のためスキップした
    """
    latest_ts = get_latest_timestamp(dam_config.db_table_name, dam_config.id)

    if latest_ts is not None:
        # DBのタイムスタンプはUTC aware で返るので、now も UTC で比較する
        now = pd.Timestamp.now("UTC")
        latest_utc = latest_ts.tz_convert("UTC") if latest_ts.tzinfo else latest_ts.tz_localize("UTC")
        elapsed_minutes = (now - latest_utc).total_seconds() / 60
        if elapsed_minutes < throttle_minutes:
            print(
                f"[{dam_config.name}] DBの最新データ: {elapsed_minutes:.1f}分前"
                f" ({throttle_minutes}分以内のためスキップ)"
            )
            return False

    fetch_and_store(dam_config, latest_ts=latest_ts)
    return True


def load_data(dam_config: DamConfig) -> pd.DataFrame:
    """
    DBからデータを読み込んでDataFrameとして返す。
    """
    return db_load_data(dam_config.db_table_name, dam_config.id)

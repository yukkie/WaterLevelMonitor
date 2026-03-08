"""
データコンバーター (Transform層)。
スクレイピング(Extract)されたRAWデータを受け取り、DB保存可能な形式(辞書リスト)に変換する。
抽出 → 変換 → DB保存の一連のフローを制御する。
"""

import pandas as pd

from src.config import StationConfig
from src.scraper import _fetch_dam_data as fetch_dam_data
from src.storage import (
    _get_latest_timestamp as get_latest_timestamp,
    _save_to_db as save_to_db,
)


def _safe_float(val) -> float | None:
    """値を float に変換する。'-' / '$' / 変換不可 → None。"""
    s = str(val).strip()
    if s.lower() in ("-", "$", "", "nan", "none"):
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _transform_data(
    df: pd.DataFrame,
    station_config: StationConfig,
    latest_ts: pd.Timestamp | None = None,
) -> list[dict]:
    """
    RAWデータをDBに投入可能な形式の辞書リストに変換する。
    """
    df = df.copy()

    # 日付と時刻を結合
    datetime_str = (
        df["0"].astype(str).str.strip() + " " + df["1"].astype(str).str.strip()
    )

    # 24:00 を 00:00 に置換し、翌日扱いにするフラグを作成
    is_2400 = df["1"].astype(str).str.strip() == "24:00"
    datetime_str = datetime_str.str.replace(" 24:00", " 00:00")

    try:
        dt_series = pd.to_datetime(datetime_str, format="mixed", errors="coerce")
        dt_series = dt_series + pd.to_timedelta(is_2400.astype(int), unit="d")
        df["parsed_ts"] = dt_series.dt.tz_localize("Asia/Tokyo").dt.tz_convert("UTC")
    except Exception:
        df["parsed_ts"] = pd.Series(pd.NaT, index=df.index)

    df = df.dropna(subset=["parsed_ts"])

    if latest_ts is not None:
        df = df[df["parsed_ts"] > latest_ts]

    req_col = "2" if station_config.type == "rain" else "4"
    if req_col in df.columns:
        df = df[df[req_col].astype(str).str.strip() != "-"]

    if station_config.type == "rain":
        col_mapping = {"rainfall": "2"}
        required_db_col = "rainfall"
    else:
        col_mapping = {
            "rainfall": "2",
            "volume": "4",
            "inflow": "6",
            "outflow": "8",
            "storage_rate": "10",
        }
        required_db_col = "volume"

    records = []
    for _, row in df.iterrows():
        record = {
            "station_id": station_config.id,
            "timestamp": row["parsed_ts"].isoformat(),
        }

        for db_col, df_col in col_mapping.items():
            record[db_col] = _safe_float(row.get(df_col))

        if record.get(required_db_col) is None:
            continue

        records.append(record)

    return records


def _fetch_and_store(station_config: StationConfig, latest_ts=None) -> int:
    """
    Extract層からデータを取得し、Transform層で変換後、Load層(DB)に保存する。
    latest_tsが与えられた場合、それ以降の差分のみを保存する。
    Returns:
        int: 保存されたレコード数
    """
    raw_df = fetch_dam_data(station_config)

    records = _transform_data(raw_df, station_config, latest_ts=latest_ts)

    count = save_to_db(station_config.db_table_name, station_config.id, records)
    return count


def refresh_data(station_config: StationConfig, throttle_minutes: int = 20) -> bool:
    """
    DBの最終タイムスタンプを確認し、throttle_minutes 以上経過していれば
    fetch_and_store を実行する。Streamlit非依存。

    Returns:
        True  : スクレイピングを実行した
        False : 閾値以内のためスキップした
    """
    latest_ts = get_latest_timestamp(station_config.db_table_name, station_config.id)

    if latest_ts is not None:
        # DBのタイムスタンプはUTC aware で返るので、now も UTC で比較する
        now = pd.Timestamp.now("UTC")
        latest_utc = (
            latest_ts.tz_convert("UTC")
            if latest_ts.tzinfo
            else latest_ts.tz_localize("UTC")
        )
        elapsed_minutes = (now - latest_utc).total_seconds() / 60
        if elapsed_minutes < throttle_minutes:
            print(
                f"[{station_config.name}] DBの最新データ: {elapsed_minutes:.1f}分前"
                f" ({throttle_minutes}分以内のためスキップ)"
            )
            return False

    _fetch_and_store(station_config, latest_ts=latest_ts)
    return True

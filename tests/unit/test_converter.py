import pandas as pd

from src.converter import _safe_float, _transform_data


def test_safe_float():
    """値が正しくfloatに変換されるか、無効な値がNoneに変換されるかテスト。"""
    assert _safe_float("123.45") == 123.45
    assert _safe_float(100) == 100.0
    assert _safe_float("-") is None
    assert _safe_float("$") is None
    assert _safe_float("") is None
    assert _safe_float("NaN") is None
    assert _safe_float("None") is None
    assert _safe_float(None) is None


def test_transform_data_dam(test_config):
    """
    ダムのRAWデータ(DataFrame)が、DB登録用の辞書リストに期待通り変換されるかテストする。
    """
    dam_config = test_config.sites["miyagase"].dam

    # ダミーのRAWデータ (scraperが返す形式に近いもの)
    raw_data = {
        "0": ["2023/10/01", "2023/10/01", "2023/10/01"],
        "1": ["10:00", "24:00", "11:00"],  # 24:00の繰り上げエッジケースを含む
        "2": ["1.5", "$", "0.0"],  # $ は欠測
        "4": ["12000", "-", "12050"],  # - は除外されるべき行（volumeカラム基準）
        "6": ["15.0", "10.0", "5.0"],
        "8": ["0.0", "0.0", "0.0"],
        "10": ["80.5", "80.0", "81.0"],
    }
    df = pd.DataFrame(raw_data)

    records = _transform_data(df, dam_config)

    # 変換後のリストの長さの確認 ('-' がある2行目はスキップされる)
    assert len(records) == 2

    # 1件目 (正常ケース)
    record1 = records[0]
    assert record1["station_id"] == dam_config.id
    # JST 10:00 -> UTC 01:00
    assert record1["timestamp"] == "2023-10-01T01:00:00+00:00"
    assert record1["rainfall"] == 1.5
    assert record1["volume"] == 12000.0
    assert record1["inflow"] == 15.0

    # JST 11:00 -> UTC 02:00
    assert records[1]["timestamp"] == "2023-10-01T02:00:00+00:00"
    assert records[1]["rainfall"] == 0.0


def test_transform_data_rain(test_config):
    """
    雨量計のRAWデータが期待通り変換されるかテストする。
    """
    rain_config = test_config.sites["miyagase"].rain

    raw_data = {
        "0": ["2023/10/01"],
        "1": ["24:00"],
        "2": ["2.5"],
    }
    df = pd.DataFrame(raw_data)

    records = _transform_data(df, rain_config)

    assert len(records) == 1
    record = records[0]
    # JST 10/01 24:00 -> JST 10/02 00:00 -> UTC 10/01 15:00
    assert record["timestamp"] == "2023-10-01T15:00:00+00:00"
    assert record["rainfall"] == 2.5
    # 雨量用の構成なので、volume等のキーは存在しない
    assert "volume" not in record


def test_transform_data_with_latest_ts(test_config):
    """
    latest_tsが指定された場合、それ以降のデータのみが抽出されるかテストする。
    """
    dam_config = test_config.sites["miyagase"].dam
    raw_data = {
        "0": ["2023/10/01", "2023/10/01", "2023/10/01"],
        "1": ["10:00", "11:00", "12:00"],
        "4": ["10", "20", "30"],
        "2": ["0", "0", "0"],
        "6": ["0", "0", "0"],
        "8": ["0", "0", "0"],
        "10": ["0", "0", "0"],
    }
    df = pd.DataFrame(raw_data)

    # latest_ts を JST 10:30 (UTC 01:30) とする
    latest_ts = pd.to_datetime("2023-10-01T01:30:00+00:00")

    records = _transform_data(df, dam_config, latest_ts=latest_ts)

    # 10:00(UTC 01:00) のデータは除外され、11:00と12:00の2件が残る
    assert len(records) == 2
    assert records[0]["timestamp"] == "2023-10-01T02:00:00+00:00"

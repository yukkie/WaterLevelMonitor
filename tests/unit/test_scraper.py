import pandas as pd

from src.scraper import _fetch_dam_data


def test_fetch_dam_data_dam(test_config, mock_requests_get):
    """
    ダムデータの取得とパースが正しく行われるかをテストする。
    HTTPリクエストはモック化されているため、fixtures/miyagase_dam.dat の内容が返る。
    """
    dam = test_config.sites["miyagase"].dam  # 宮ヶ瀬ダム
    df = _fetch_dam_data(dam)

    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    # DATファイルのヘッダー行が無視され、列名が文字列として割り当てられているか確認
    assert "0" in df.columns
    assert "1" in df.columns


def test_fetch_dam_data_rain(test_config, mock_requests_get):
    """
    雨量データの取得とパースが正しく行われるかをテストする。
    """
    rain = test_config.sites["miyagase"].rain  # 宮ヶ瀬及沢
    df = _fetch_dam_data(rain)

    assert isinstance(df, pd.DataFrame)
    assert not df.empty
    assert "0" in df.columns
    assert "1" in df.columns

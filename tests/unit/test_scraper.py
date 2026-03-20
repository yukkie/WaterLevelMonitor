import pandas as pd

from src.converter import _transform_data
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


def test_fetch_dam_data_anomalous(test_config, mock_requests_get):
    """
    矢木沢ダムの異常データ（#フラグ・volume=0混在）が正しくパースされるかをテストする。
    - scraper はvolume=0 の行も含めて全行をそのまま返す（生データ保持）
    - converter はvolume=0 の行も DB に保存する（フィルタはplot層の責務）
    """
    dam = test_config.sites["yagisawa_anomalous"].dam
    df = _fetch_dam_data(dam)

    assert isinstance(df, pd.DataFrame)
    assert not df.empty

    # volume列(4)に0が含まれていること（生データが保持されている）
    volume_col = df["4"].astype(str).str.strip()
    assert (volume_col == "0").any(), "volume=0 の行が生データに含まれるはず"

    # volume列(4)に正常値も含まれていること
    assert (volume_col != "0").any(), "正常な volume の行も含まれるはず"

    # #フラグ列(5)が存在し、#を含む行があること
    assert "5" in df.columns
    flag_col = df["5"].astype(str).str.strip()
    assert (flag_col == "#").any(), "#フラグが属性列に含まれるはず"

    # converter はvolume=0 も含めて変換する（DBには生データとして保存）
    records = _transform_data(df, dam)
    volumes = [r["volume"] for r in records]
    assert 0 in volumes, "volume=0 のレコードもDBに保存されるはず"
    assert any(
        v > 0 for v in volumes if v is not None
    ), "正常な volume のレコードも保存されるはず"


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

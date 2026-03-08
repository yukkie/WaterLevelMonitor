import os
import sys
from unittest.mock import MagicMock, patch

import pytest

# プロジェクトルートを取得してsys.pathに追加
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from src.config import load_config  # noqa: E402


@pytest.fixture
def test_config():
    config_path = os.path.join(project_root, "dams.yaml")
    return load_config(config_path)


@pytest.fixture
def mock_requests_get():
    # requests.get を差し替えるモック関数
    class MockResponse:
        def __init__(self, text, encoding="utf-8"):
            self.text = text
            self.encoding = encoding
            self.apparent_encoding = encoding

        def raise_for_status(self):
            pass

    def side_effect(url, *args, **kwargs):
        fixtures_dir = os.path.join(project_root, "tests", "fixtures")

        # HTML内部のDATリンクにアクセスしたとき
        if url.endswith(".dat"):
            if "5313680" in url:  # miyagase_dam 向けリンクという想定 (適当な識別子)
                with open(
                    os.path.join(fixtures_dir, "miyagase_dam.dat"), encoding="utf-8"
                ) as f:
                    # Windows特有の \r\n -> \r\r\n の連続改行を吸収する
                    text = f.read().replace("\n\n", "\n")
                    return MockResponse(text)
            else:
                with open(
                    os.path.join(fixtures_dir, "miyagase_rain.dat"), encoding="utf-8"
                ) as f:
                    text = f.read().replace("\n\n", "\n")
                    return MockResponse(text)

        # URLにアクセスしてHTMLを取得したとき
        if "DspDamData.exe" in url:
            return MockResponse('<a href="dummy_5313680.dat">dummy</a>')
        elif "DspRainData.exe" in url:
            return MockResponse('<a href="dummy_rain.dat">dummy</a>')

        return MockResponse("")

    with patch("src.scraper.requests.get", side_effect=side_effect) as mock_get:
        yield mock_get


@pytest.fixture
def mock_supabase():
    # DB (Supabase) への書き込みを傍受するモック
    inserted_records = {"dam_data": [], "rain_data": []}

    class MockTable:
        def __init__(self, table_name):
            self.table_name = table_name

        def upsert(self, records):
            # pandas等のNA/NaNが入っているとJSON化でエラーになる可能性があるため、
            # NaNをNoneに変換してから格納する
            # （実際のSupabaseクライアントも似た挙動をする）
            clean_records = []
            for r in records:
                clean_r = {}
                for k, v in r.items():
                    # pandas.NA や float('nan') を判別して None にする
                    if v != v or v is None:
                        clean_r[k] = None
                    else:
                        clean_r[k] = v
                clean_records.append(clean_r)

            inserted_records[self.table_name].extend(clean_records)
            mock_execute = MagicMock()
            mock_execute.execute.return_value = mock_execute
            mock_execute.data = clean_records
            return mock_execute

        def select(self, *args, **kwargs):
            mock_select = MagicMock()

            # ページネーション対応のためにrangeを記録する
            mock_select.current_range = None

            def mock_range(start, end):
                mock_select.current_range = (start, end)
                return mock_select

            def mock_execute():
                data = inserted_records[self.table_name]
                if mock_select.current_range:
                    start, end = mock_select.current_range
                    # Supabaseのrangeはinclusiveなので端点を含む
                    mock_select.data = data[start : end + 1]
                else:
                    mock_select.data = data
                return mock_select

            mock_select.eq.return_value = mock_select
            mock_select.order.return_value = mock_select
            mock_select.limit.return_value = mock_select
            mock_select.range = mock_range
            mock_select.execute = mock_execute

            return mock_select

    class MockSupabaseClient:
        def table(self, table_name):
            return MockTable(table_name)

    with patch("src.storage._get_supabase_client", return_value=MockSupabaseClient()):
        yield inserted_records

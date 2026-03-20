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
            if "dummy_5313680.dat" in url:  # miyagase_dam 向けリンクという想定
                with open(
                    os.path.join(fixtures_dir, "miyagase_dam.dat"),
                    encoding="shift_jis",
                ) as f:
                    # Windows特有の \r\n -> \r\r\n の連続改行を吸収する
                    text = f.read().replace("\n\n", "\n")
                    return MockResponse(text, encoding="shift_jis")
            elif "dummy_yagisawa.dat" in url:
                with open(
                    os.path.join(fixtures_dir, "yagisawa_dam.dat"),
                    encoding="shift_jis",
                ) as f:
                    text = f.read().replace("\n\n", "\n")
                    return MockResponse(text, encoding="shift_jis")
            elif "dummy_yagisawa_anomalous.dat" in url:
                with open(
                    os.path.join(fixtures_dir, "yagisawa_dam_anomalous.dat"),
                    encoding="shift_jis",
                ) as f:
                    text = f.read().replace("\n\n", "\n")
                    return MockResponse(text, encoding="shift_jis")
            else:
                with open(
                    os.path.join(fixtures_dir, "miyagase_rain.dat"),
                    encoding="shift_jis",
                ) as f:
                    text = f.read().replace("\n\n", "\n")
                    return MockResponse(text, encoding="shift_jis")

        # URLにアクセスしてHTMLを取得したとき
        if "DspDamData.exe" in url:
            if "1368030375010" in url:
                return MockResponse('<a href="dummy_yagisawa.dat">dummy</a>')
            return MockResponse('<a href="dummy_5313680.dat">dummy</a>')
        elif "DspRainData.exe" in url:
            return MockResponse('<a href="dummy_rain.dat">dummy</a>')

        return MockResponse("")

    with patch("src.scraper.requests.get", side_effect=side_effect) as mock_get:
        yield mock_get


@pytest.fixture
def mock_requests_get_anomalous():
    """矢木沢ダムの異常データ（#フラグ・volume=0混在）を返すモック。"""

    class MockResponse:
        def __init__(self, text, encoding="utf-8"):
            self.text = text
            self.encoding = encoding
            self.apparent_encoding = encoding

        def raise_for_status(self):
            pass

    def side_effect(url, *args, **kwargs):
        fixtures_dir = os.path.join(project_root, "tests", "fixtures")
        if url.endswith(".dat"):
            with open(
                os.path.join(fixtures_dir, "yagisawa_dam_anomalous.dat"),
                encoding="shift_jis",
                errors="replace",
            ) as f:
                text = f.read().replace("\n\n", "\n")
                return MockResponse(text, encoding="shift_jis")
        if "DspDamData.exe" in url:
            return MockResponse('<a href="dummy_yagisawa_anomalous.dat">dummy</a>')
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
            from unittest.mock import create_autospec

            from postgrest import SyncSelectRequestBuilder

            # 1. 本物のクラス構造を持ったモックを作成
            # (存在しないメソッド呼び出しはエラーになる)
            mock_select = create_autospec(SyncSelectRequestBuilder, instance=True)

            # 状態を保持するためのカスタム属性
            mock_select.current_range = None
            mock_select.filters = []
            mock_select.order_by = None
            mock_select.limit_count = None

            # 各メソッドが呼ばれた際の処理（side_effect）を定義
            def mock_range(start, end):
                mock_select.current_range = (start, end)
                return mock_select

            def mock_eq(column, value):
                mock_select.filters.append((column, value))
                return mock_select

            def mock_order(column, desc=False, nullsfirst=False):
                # 実際の order のシグネチャに合わせて
                # nullsfirst 引数も受け取るようにする
                mock_select.order_by = (column, desc)
                return mock_select

            def mock_limit(size):
                mock_select.limit_count = size
                return mock_select

            def mock_execute():
                data = inserted_records[self.table_name]

                # 1. フィルタ適用 (.eq)
                for col, val in mock_select.filters:
                    data = [r for r in data if r.get(col) == val]

                # 2. ソート適用 (.order)
                if mock_select.order_by:
                    col, desc = mock_select.order_by
                    data.sort(key=lambda x: x.get(col, ""), reverse=desc)

                # 3. ページネーション適用 (.range)
                if mock_select.current_range:
                    start, end = mock_select.current_range
                    data = data[start : end + 1]

                # 4. リミット適用 (.limit)
                if mock_select.limit_count is not None:
                    data = data[: mock_select.limit_count]

                # execute() はデータを持つ別のオブジェクトを返す想定
                mock_result = MagicMock()
                mock_result.data = data
                return mock_result

            # side_effect に設定して、実際の中身を動かす
            mock_select.eq.side_effect = mock_eq
            mock_select.gte.side_effect = lambda col, val: mock_select
            mock_select.order.side_effect = mock_order
            mock_select.limit.side_effect = mock_limit
            mock_select.range.side_effect = mock_range
            mock_select.execute.side_effect = mock_execute

            return mock_select

    class MockSupabaseClient:
        def table(self, table_name):
            return MockTable(table_name)

    with patch("src.storage._get_supabase_client", return_value=MockSupabaseClient()):
        yield inserted_records

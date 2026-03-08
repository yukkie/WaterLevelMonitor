from streamlit.testing.v1 import AppTest

from src.pipeline import run_pipeline


def test_app_loads_empty_data(mock_supabase):
    """
    データが存在しない初期状態でアプリがクラッシュせず、
    警告メッセージが正しく表示されるかをテストする。
    """
    at = AppTest.from_file("src/app.py")
    at.run(timeout=10)

    # エラーが発生せずに起動すること
    assert not at.exception

    # タイトルが正しいこと
    assert at.title[0].value == "🌊 Water Level Monitor"

    # データがない場合は警告が表示されること
    assert len(at.warning) > 0
    assert "データが不足しているためグラフを描画できません" in at.warning[0].value


def test_app_loads_with_data(test_config, mock_supabase, mock_requests_get, mocker):
    """
    データが存在する状態でアプリを起動し、
    グラフ描画用のサブヘッダーが正しく表示されるかをテストする。
    """
    # 1. パイプラインを実行して、モックDBにデータを事前に注入する
    mocker.patch("src.pipeline.load_config", return_value=test_config)
    success = run_pipeline()
    assert success is True

    # 2. アプリを起動する
    at = AppTest.from_file("src/app.py")
    at.run(timeout=10)

    # エラーが発生せずに起動すること
    assert not at.exception

    # データがあるため警告は出ないはず
    assert len(at.warning) == 0

    # 対象ダムのサブヘッダーが表示されていること
    target_dam = test_config.sites["miyagase"].dam
    assert f"{target_dam.name} の状況" in at.subheader[0].value

import os
from unittest.mock import patch

import pytest

from src.main import main


def test_main_execution(test_config, mock_supabase, mock_requests_get, mocker):
    """
    main() を実行し、全ダムのプロット画像が生成されることを検証する。
    """
    # 1. 保存先のパスを特定
    # プロジェクトルートに保存される想定
    expected_files = []
    for site in test_config.sites.values():
        expected_files.append(f"plot_{site.dam.name}.png")

    # 念のため、既存のテストファイルを削除しておく
    for f in expected_files:
        if os.path.exists(f):
            os.remove(f)

    # 2. main() 内部で呼ばれる load_config をモック化
    # mocker.patch("src.main.load_config", return_value=test_config)

    # 3. plt.show() がブロックしないようにモック化
    # (plt.savefig は実際にファイルを生成させるためモックしない)
    with patch("matplotlib.pyplot.show"):
        try:
            main()
        except SystemExit as e:
            # sys.exit(0) は正常終了とみなす
            if e.code != 0:
                raise

    # 4. ファイルが生成されたかチェック
    for f in expected_files:
        assert os.path.exists(f), f"画像ファイルが生成されていません: {f}"

        # 後片付け（オプション: 残しておきたい場合はコメントアウト）
        # os.remove(f)


def test_main_error_handling(mocker):
    """
    設定読み込み失敗時に適切に例外終了するかを検証。
    """
    mocker.patch("src.main.load_config", side_effect=Exception("Config error"))

    with pytest.raises(SystemExit) as excinfo:
        main()

    assert excinfo.value.code == 1

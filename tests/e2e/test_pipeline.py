import json
import os

import pytest

from src.pipeline import run_pipeline


def _assert_snapshot(records, identifier):
    """
    レコードのリストをJSONスナップショットファイルと比較する。
    ファイルが存在しなければ新規作成する。
    """
    # プロジェクトルートを取得
    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    snapshot_path = os.path.join(
        project_root, "tests", "fixtures", f"expected_{identifier}.json"
    )

    if not os.path.exists(snapshot_path):
        # スナップショットが存在しない場合は作成（初回実行時）
        print(f"\n[{identifier}] スナップショットを新規作成します: {snapshot_path}")
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        return  # 初回はそのままパス

    # スナップショットが存在する場合は読み込んで比較
    with open(snapshot_path, encoding="utf-8") as f:
        expected_records = json.load(f)

    assert len(records) == len(expected_records), (
        f"レコード件数が異なります: "
        f"expected={len(expected_records)}, actual={len(records)}"
    )

    for i, (actual, expected) in enumerate(
        zip(records, expected_records, strict=False)
    ):
        assert (
            actual == expected
        ), f"{i}行目のデータが異なります\nExpected: {expected}\nActual: {actual}"


def test_run_pipeline(test_config, mock_requests_get, mock_supabase, mocker):
    # run_pipeline内部で呼ばれるload_configをモック化して、
    # conftestで用意した test_config を返すようにする
    mocker.patch("src.pipeline.load_config", return_value=test_config)

    target_site = test_config.sites["miyagase"]
    dam_target = target_site.dam
    rain_target = target_site.rain

    # 本番のパイプライン処理を実行
    success = run_pipeline()

    # 戻り値の確認
    if not success:
        # DBへの書き込み処理等のどこかでExceptionが起きた
        pytest.fail("run_pipeline() returned False. Check logs for details.")
    assert success is True

    # DBにUPSERTされていることを確認
    dam_records = mock_supabase[dam_target.db_table_name]
    assert len(dam_records) > 0, "ダムデータがUPSERTされていません"

    rain_records = mock_supabase[rain_target.db_table_name]
    assert len(rain_records) > 0, "雨量データがUPSERTされていません"

    # 完全一致スナップショット検証
    _assert_snapshot(dam_records, dam_target.id)
    _assert_snapshot(rain_records, rain_target.id)

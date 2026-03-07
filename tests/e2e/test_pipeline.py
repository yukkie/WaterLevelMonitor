import sys
import os
import json

# -----------------
# パスのセットアップ
# -----------------
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if os.path.join(project_root, 'src') not in sys.path:
    sys.path.append(os.path.join(project_root, 'src'))

from pipeline import fetch_and_store

def _assert_snapshot(records, identifier):
    """
    レコードのリストをJSONスナップショットファイルと比較する。
    ファイルが存在しなければ新規作成する。
    """
    snapshot_path = os.path.join(project_root, 'tests', 'fixtures', f"expected_{identifier}.json")
    
    if not os.path.exists(snapshot_path):
        # スナップショットが存在しない場合は作成（初回実行時）
        print(f"\n[{identifier}] スナップショットを新規作成します: {snapshot_path}")
        with open(snapshot_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        return # 初回はそのままパス

    # スナップショットが存在する場合は読み込んで比較
    with open(snapshot_path, "r", encoding="utf-8") as f:
        expected_records = json.load(f)
        
    assert len(records) == len(expected_records), f"レコード件数が異なります: expected={len(expected_records)}, actual={len(records)}"
    
    for i, (actual, expected) in enumerate(zip(records, expected_records)):
        assert actual == expected, f"{i}行目のデータが異なります\nExpected: {expected}\nActual: {actual}"


def test_fetch_and_store_dam(test_config, mock_requests_get, mock_supabase):
    dam_target = test_config.dams['miyagase']
    
    # 本番のパイプライン処理を実行
    fetch_and_store(dam_target, latest_ts=None)
    
    records = mock_supabase[dam_target.db_table_name]
    assert len(records) > 0, "データがUPSERTされていません"

    # 完全一致スナップショット検証
    _assert_snapshot(records, dam_target.id)


def test_fetch_and_store_rain(test_config, mock_requests_get, mock_supabase):
    rain_target = test_config.dams['miyagase_oizawa_rain']
    
    # 本番のパイプライン処理を実行
    fetch_and_store(rain_target, latest_ts=None)
    
    records = mock_supabase[rain_target.db_table_name]
    assert len(records) > 0, "雨量データがUPSERTされていません"
    
    # 完全一致スナップショット検証
    _assert_snapshot(records, rain_target.id)

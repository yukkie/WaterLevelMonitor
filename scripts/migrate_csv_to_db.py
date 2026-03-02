"""
既存CSVデータ → Supabase DB 移行スクリプト。
data/*.csv を読み込み、'-' 行スキップ・'$' を NULL に変換してバルク挿入する。

Usage:
    python scripts/migrate_csv_to_db.py

前提:
    - SUPABASE_URL / SUPABASE_KEY 環境変数が設定されていること
    - Supabase 上に dam_data / rain_data テーブルが作成済みであること
"""
import sys
import os

# プロジェクトルートの src/ を import パスに追加
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import pandas as pd
from config import load_config
from db import upsert_dam_data, upsert_rain_data


def migrate_csv(dam_id: str, dam_type: str, csv_path: str):
    """1つのCSVファイルをDBに移行する。"""
    print(f"\n{'='*60}")
    print(f"移行開始: {csv_path} (type={dam_type})")
    print(f"{'='*60}")

    df = pd.read_csv(csv_path)
    df.columns = df.columns.astype(str)
    print(f"CSV読み込み完了: {len(df)}行")

    if dam_type == "rain":
        count = upsert_rain_data(dam_id, df)
    else:
        count = upsert_dam_data(dam_id, df)

    print(f"移行完了: {count}件 UPSERT")


def main():
    # プロジェクトルートに移動（config読み込みのため）
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    config = load_config("dams.yaml")
    data_dir = os.path.join(project_root, "data")

    if not os.path.exists(data_dir):
        print(f"データディレクトリが見つかりません: {data_dir}")
        sys.exit(1)

    migrated = 0
    for key, dam in config.dams.items():
        csv_path = os.path.join(data_dir, f"{dam.id}.csv")
        if os.path.exists(csv_path):
            migrate_csv(dam.id, dam.type, csv_path)
            migrated += 1
        else:
            print(f"[スキップ] CSV未発見: {csv_path}")

    print(f"\n{'='*60}")
    print(f"全移行完了: {migrated}ファイル処理")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

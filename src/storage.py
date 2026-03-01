import pandas as pd
import os

def update_local_csv(dam_id: str, new_df: pd.DataFrame, data_dir="data") -> pd.DataFrame:
    """
    既存のCSVを読み込み、新しいデータをマージ（重複排除）して書き出す。
    """
    os.makedirs(data_dir, exist_ok=True)
    csv_path = os.path.join(data_dir, f"{dam_id}.csv")
    
    if os.path.exists(csv_path):
        # 既存データを読み込み
        # 既存データを読み込み、列名を新データに合わせるためstring型に統一
        existing_df = pd.read_csv(csv_path)
        existing_df.columns = existing_df.columns.astype(str)
        
        # 新旧データを結合し、日付(0列目)と時刻(1列目)で重複を排除
        # new_df（最新の取得データ）を優先するため、new_df をあとに結合し、keep='last' にする
        combined_df = pd.concat([existing_df, new_df])
        combined_df = combined_df.drop_duplicates(subset=['0', '1'], keep='last')
        combined_df = combined_df.sort_values(['0', '1']).reset_index(drop=True)
        print(f"既存のデータ({len(existing_df)}件)に新しいデータを合成・更新しました。合計: {len(combined_df)}件")
    else:
        combined_df = new_df
        print(f"新規CSVを作成しました: {len(combined_df)}件")
        
    # 保存
    combined_df.to_csv(csv_path, index=False)
    return combined_df

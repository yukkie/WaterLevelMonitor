import pandas as pd
import os

def update_local_csv(dam_id: str, new_df: pd.DataFrame, data_dir="data") -> pd.DataFrame:
    """
    既存のCSVを読み込み、新しいデータをマージ（重複排除）して書き出す。
    """
    # srcからの相対パスではなく、プロジェクトルート基準にするために親ディレクトリを探す
    if not os.path.exists(data_dir) and os.path.basename(os.getcwd()) == "src":
        data_dir = os.path.join("..", data_dir)
        
    os.makedirs(data_dir, exist_ok=True)
    csv_path = os.path.join(data_dir, f"{dam_id}.csv")
    
    if os.path.exists(csv_path):
        # 既存データを読み込み
        existing_df = pd.read_csv(csv_path)
        existing_df['timestamp'] = pd.to_datetime(existing_df['timestamp'])
        
        # 新旧データを結合し、timestamp基準で重複を排除してソート
        combined_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=['timestamp'])
        combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
        print(f"既存のデータ({len(existing_df)}件)に新しいデータを合成しました。合計: {len(combined_df)}件")
    else:
        combined_df = new_df
        print(f"新規CSVを作成しました: {len(combined_df)}件")
        
    # 保存
    combined_df.to_csv(csv_path, index=False)
    return combined_df

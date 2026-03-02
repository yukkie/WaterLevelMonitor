"""
データストレージ層。
DB (Supabase) への書き込みをメインに、CSVマージは互換用に残す。
"""
import pandas as pd
import os
from db import upsert_dam_data, upsert_rain_data


def save_to_db(dam_id: str, dam_type: str, df: pd.DataFrame) -> int:
    """
    DataFrameをSupabase DBに保存する（メインのストレージ経路）。
    """
    if dam_type == "rain":
        return upsert_rain_data(dam_id, df)
    else:
        return upsert_dam_data(dam_id, df)


# --- 以下はCSV互換用（隔離）---

def update_local_csv(dam_id: str, new_df: pd.DataFrame, data_dir="data") -> pd.DataFrame:
    """
    【互換用】既存のCSVを読み込み、新しいデータをマージ（重複排除）して書き出す。
    DB移行後も既存CSVのバックアップ用途として残す。
    """
    os.makedirs(data_dir, exist_ok=True)
    csv_path = os.path.join(data_dir, f"{dam_id}.csv")
    
    if os.path.exists(csv_path):
        existing_df = pd.read_csv(csv_path)
        existing_df.columns = existing_df.columns.astype(str)
        
        combined_df = pd.concat([existing_df, new_df])
        combined_df = combined_df.drop_duplicates(subset=['0', '1'], keep='last')
        combined_df = combined_df.sort_values(['0', '1']).reset_index(drop=True)
        print(f"既存のデータ({len(existing_df)}件)に新しいデータを合成・更新しました。合計: {len(combined_df)}件")
    else:
        combined_df = new_df
        print(f"新規CSVを作成しました: {len(combined_df)}件")
        
    combined_df.to_csv(csv_path, index=False)
    return combined_df

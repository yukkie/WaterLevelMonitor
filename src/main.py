from config import load_config
from scraper import fetch_dam_data
from storage import update_local_csv
from plot import plot_water_level
import sys

def main():
    try:
        # 設定の読み込み
        config = load_config()
        
        # とりあえず宮ヶ瀬ダムで実行
        target_dam = config.dams["miyagase"]
        
        # 1. データの取得
        new_data_df = fetch_dam_data(target_dam)
        
        # 2. ローカルCSVへの合成・保存
        final_df = update_local_csv(target_dam.id, new_data_df)
        
        # 3. グラフの表示
        plot_water_level(target_dam, final_df)
        
    except Exception as e:
        print(f"エラーが発生しました: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

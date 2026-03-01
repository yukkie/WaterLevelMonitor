from config import load_config
from pipeline import fetch_and_store
from plot import plot_water_level
import sys


def main():
    try:
        # 設定の読み込み
        config = load_config()

        # とりあえず宮ヶ瀬ダムと雨量を取得
        target_dam = config.dams["miyagase"]
        rain_station = config.dams["miyagase_oizawa_rain"]

        # 1. データの取得・保存
        final_dam_df = fetch_and_store(target_dam)
        final_rain_df = fetch_and_store(rain_station)

        # 2. グラフの表示
        fig = plot_water_level(target_dam, final_dam_df, rain_station, final_rain_df)

        # Matplotlibによる描画 (ローカル実行用)
        import matplotlib.pyplot as plt
        plt.savefig('test_plot.png')
        plt.show()

    except Exception as e:
        print(f"エラーが発生しました: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()

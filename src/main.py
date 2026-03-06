from config import load_config
from pipeline import check_and_fetch, load_data
from plot import plot_water_level
import sys


def main():
    try:
        # 設定の読み込み
        config = load_config()

        # とりあえず宮ヶ瀬ダムと雨量を取得
        target_dam = config.dams["miyagase"]
        rain_station = config.dams["miyagase_oizawa_rain"]

        # 1. データの取得・DB保存（10分ガード付き）
        check_and_fetch(target_dam)
        check_and_fetch(rain_station)

        # 2. DBからデータ読み込み
        dam_df = load_data(target_dam)
        rain_df = load_data(rain_station)

        # 3. グラフの表示
        fig = plot_water_level(target_dam, dam_df, rain_station, rain_df)

        import matplotlib.pyplot as plt
        plt.savefig('test_plot.png')
        print("グラフを test_plot.png に保存しました。")
        plt.show()

    except Exception as e:
        print(f"エラーが発生しました: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

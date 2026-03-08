import sys

import matplotlib.pyplot as plt

from src.config import load_config
from src.converter import refresh_data
from src.plot import plot_water_level
from src.storage import load_data


def main():
    try:
        # 設定の読み込み
        config = load_config()

        # とりあえず宮ヶ瀬ダムのサイトを取得
        target_site = config.sites["miyagase"]
        target_dam = target_site.dam
        rain_station = target_site.rain

        # 1. データの取得・DB保存（10分ガード付き）
        refresh_data(target_dam)
        if rain_station:
            refresh_data(rain_station)

        # 2. DBからデータ読み込み
        dam_df = load_data(target_dam.db_table_name, target_dam.id)
        rain_df = load_data(rain_station.db_table_name, rain_station.id)

        # 3. グラフの表示
        _ = plot_water_level(target_dam, dam_df, rain_station, rain_df)

        plt.savefig("test_plot.png")
        print("グラフを test_plot.png に保存しました。")
        plt.show()

    except Exception as e:
        import traceback

        print(f"エラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

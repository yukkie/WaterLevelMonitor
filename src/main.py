import argparse
import sys

import matplotlib.pyplot as plt
import pandas as pd

from src.config import load_config
from src.converter import refresh_data
from src.plot import plot_water_level
from src.storage import DisplayPeriod, load_data

# 表示期間のデフォルト値。コマンドライン引数がない場合はここを変更する。
# 選択肢: DisplayPeriod.TWO_WEEKS / DisplayPeriod.ONE_YEAR / DisplayPeriod.ALL
DISPLAY_PERIOD = DisplayPeriod.TWO_WEEKS


def main(period: DisplayPeriod = DISPLAY_PERIOD):
    try:
        # 設定の読み込み
        config = load_config()

        for site in config.sites.values():
            target_dam = site.dam
            rain_station = site.rain

            print(f"--- [{target_dam.name}] の処理を開始します ---")

            # 1. データの取得・DB保存（10分ガード付き）
            refresh_data(target_dam)
            # 1. ダムデータの読み込み
            dam_df = load_data(target_dam.db_table_name, target_dam.id, period)

            # 2. 雨量データの読み込み (Optional)
            if rain_station:
                refresh_data(rain_station)
                rain_df = load_data(rain_station.db_table_name, rain_station.id, period)
            else:
                rain_df = pd.DataFrame()

            # 3. グラフの生成
            fig = plot_water_level(target_dam, dam_df, rain_station, rain_df)

            # 画像として保存 (ダムIDをファイル名に含める)
            file_name = f"plot_{target_dam.name}.png"
            plt.savefig(file_name)
            print(f"グラフを {file_name} に保存しました。")

            # 手動実行時のみ表示（テスト等でバックエンドがない環境でも落ちないように）
            try:
                plt.show()
            except Exception:
                print(
                    "警告: グラフを表示できませんでした（バックエンド未設定）。"
                    "出力画像を確認してください。"
                )
            finally:
                plt.close(fig)

    except Exception as e:
        import traceback

        print(f"エラーが発生しました: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Water Level Monitor")
    parser.add_argument(
        "--period",
        choices=[p.value for p in DisplayPeriod],
        default=DISPLAY_PERIOD.value,
        help="表示期間 (2w: 2週間, 1y: 1年, all: 全部)",
    )
    args = parser.parse_args()
    main(period=DisplayPeriod(args.period))

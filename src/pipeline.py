"""
データ取得・変換(ETL)をUIから完全に分離し、定期実行するためのバッチモジュール。
将来的にGitHub Actionsなどで定期実行(cron)されることを想定している。
"""

import sys

from src.config import load_config
from src.converter import refresh_data


def run_pipeline() -> bool:
    """
    設定されたすべてのサイトのデータを取得・保存する。

    Returns:
        bool: 全ての処理が成功した場合はTrue、エラーが発生した場合はFalse
    """
    config = load_config()
    success = True

    for site in config.sites.items():
        target_dam = site.dam
        rain_station = site.rain

        try:
            print(f"[{target_dam.name}] データ取得を開始します...")
            refresh_data(target_dam)

            if rain_station:
                refresh_data(rain_station)

            print(f"[{target_dam.name}] データ取得が正常に完了しました。")
        except Exception as e:
            import traceback

            print(f"[{target_dam.name}] データ処理エラー: {e}", file=sys.stderr)
            traceback.print_exc()
            success = False

    return success


if __name__ == "__main__":
    if not run_pipeline():
        # GitHub Actions などで失敗を検知できるように異常な終了コードを返す
        sys.exit(1)

    # 成功時は通常通り終了(コード0)
    sys.exit(0)

import streamlit as st
import os
import time
import sys
import matplotlib.pyplot as plt

# プロジェクトルートディレクトリをsys.pathに追加してモジュールをインポート可能にする
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import load_config
from src.pipeline import resolve_data_dir, fetch_and_store, load_data
from src.plot import plot_water_level


def check_and_fetch_data(dam_config, data_dir="data", throttle_minutes=10):
    """
    データファイル（CSV）の更新日時を確認し、指定した時間（分）以上経過していれば新規データを取得する。
    Streamlit固有のUI表示を伴うラッパー。
    """
    data_dir = resolve_data_dir(data_dir)
    csv_path = os.path.join(data_dir, f"{dam_config.id}.csv")

    needs_fetch = True
    if os.path.exists(csv_path):
        mtime = os.path.getmtime(csv_path)
        current_time = time.time()
        elapsed_minutes = (current_time - mtime) / 60
        if elapsed_minutes < throttle_minutes:
            needs_fetch = False
            st.toast(f"[{dam_config.name}] 最終更新から {elapsed_minutes:.1f}分経過 (10分以内のためキャッシュ利用)")

    if needs_fetch:
        with st.spinner(f"[{dam_config.name}] 最新データを取得中..."):
            try:
                fetch_and_store(dam_config, data_dir=data_dir)
                st.toast(f"[{dam_config.name}] データ更新完了", icon="✅")
            except Exception as e:
                st.error(f"データ取得エラー: {e}")


def main():
    st.set_page_config(page_title="Water Level Monitor", page_icon="🌊", layout="wide")

    st.title("🌊 Water Level Monitor")
    st.markdown("国土交通省 川の防災情報のデータを利用してダムの水位や雨量を可視化します。")

    # configの読み込み (app.pyがsrc/内から実行されるか直下から実行されるかに対応)
    config_path = "dams.yaml"
    if not os.path.exists(config_path) and os.path.basename(os.getcwd()) == "src":
        config_path = os.path.join("..", "dams.yaml")
    config = load_config(config_path)

    # 対象ダムの選択（とりあえず宮ヶ瀬ダムのみの想定だが、拡張を見据えてセレクトボックス化）
    dam_options = {k: v.name for k, v in config.dams.items() if v.type != "rain"}
    selected_dam_key = st.selectbox("表示するダムを選択", options=list(dam_options.keys()), format_func=lambda x: dam_options[x])

    target_dam = config.dams[selected_dam_key]
    # 対象ダムに関連する雨量観測所を取得(宮ヶ瀬ダムの場合は"miyagase_oizawa_rain")
    rain_station_key = f"{selected_dam_key}_oizawa_rain" # 命名規則として仮定
    if rain_station_key not in config.dams:
        # 見つからなければ最初の雨量観測所を使用するか、雨量なしとする
        rain_station_keys = [k for k, v in config.dams.items() if v.type == "rain"]
        if rain_station_keys:
            rain_station_key = rain_station_keys[0]
        else:
            rain_station_key = None

    if rain_station_key:
        rain_station = config.dams[rain_station_key]
    else:
        st.warning("雨量観測所の設定が見つかりません。")
        return

    # 最新データの取得（10分ガード付き）
    check_and_fetch_data(target_dam)
    check_and_fetch_data(rain_station)

    # データの読み込み
    dam_df = load_data(target_dam)
    rain_df = load_data(rain_station)

    if not dam_df.empty and not rain_df.empty:
        st.subheader(f"{target_dam.name} の状況")

        # グラフの描画
        with st.spinner("グラフを描画中..."):
            fig = plot_water_level(target_dam, dam_df.copy(), rain_station, rain_df.copy())
            st.pyplot(fig)
            # st.pyplotに渡した後はメモリリークを防ぐためにclose
            plt.close(fig)

    else:
        st.warning("データが不足しているためグラフを描画できません。")

    # 免責事項の表示（控えめに）
    disclaimer_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "doc", "Disclaimer.md")
    if os.path.exists(disclaimer_path):
        with open(disclaimer_path, "r", encoding="utf-8") as f:
            st.caption(f.read())

if __name__ == "__main__":
    main()

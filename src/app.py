import streamlit as st
import os
import sys
import matplotlib.pyplot as plt

# プロジェクトルートディレクトリをsys.pathに追加してモジュールをインポート可能にする
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import load_config
from src.converter import fetch_and_store, check_and_fetch
from src.storage import load_data

from src.plot import plot_water_level


def check_and_fetch_data(dam_config, throttle_minutes=20):
    """
    converter.check_and_fetch を呼び出して Streamlit の UI（spinner/toast/error）を追加する薄いラッパー。
    ガードロジック本体は converter.py に一元化されているため、main.py からも同じ関数が使える。
    """
    with st.spinner(f"[{dam_config.name}] 最新データを確認中..."):
        try:
            fetched = check_and_fetch(dam_config, throttle_minutes)
            if fetched:
                st.toast(f"[{dam_config.name}] データ更新完了", icon="✅")
            else:
                st.toast(f"[{dam_config.name}] 最新データをキャッシュから利用")
            return fetched
        except Exception as e:
            st.error(f"データ取得エラー: {e}")
    return False


def main():
    st.set_page_config(page_title="Water Level Monitor", page_icon="🌊", layout="wide")

    st.title("🌊 Water Level Monitor")
    st.markdown("国土交通省 川の防災情報のデータを利用してダムの水位や雨量を可視化します。")

    # configの読み込み
    config_path = "dams.yaml"
    if not os.path.exists(config_path) and os.path.basename(os.getcwd()) == "src":
        config_path = os.path.join("..", "dams.yaml")
    config = load_config(config_path)

    # 対象ダムの選択
    dam_options = {k: v.name for k, v in config.dams.items() if v.type != "rain"}
    selected_dam_key = st.selectbox("表示するダムを選択", options=list(dam_options.keys()), format_func=lambda x: dam_options[x])

    target_dam = config.dams[selected_dam_key]
    # 対象ダムに関連する雨量観測所を取得
    rain_station_key = f"{selected_dam_key}_oizawa_rain"
    if rain_station_key not in config.dams:
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

    # データの読み込み（DBから）
    dam_df = load_data(target_dam.db_table_name, target_dam.id)
    rain_df = load_data(rain_station.db_table_name, rain_station.id)

    if not dam_df.empty and not rain_df.empty:
        st.subheader(f"{target_dam.name} の状況")

        # グラフの描画
        with st.spinner("グラフを描画中..."):
            fig = plot_water_level(target_dam, dam_df.copy(), rain_station, rain_df.copy())
            st.pyplot(fig)
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

import os
import sys

# プロジェクトルートを sys.path に追加 (Streamlit Cloud での ImportNotFoundError 対策)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from src.config import load_config
from src.plot import plot_water_level
from src.storage import load_data


def main():
    st.set_page_config(page_title="Water Level Monitor", page_icon="🌊", layout="wide")

    st.title("🌊 Water Level Monitor")
    st.markdown(
        "国土交通省 川の防災情報のデータを利用してダムの水位や雨量を可視化します。"
    )

    # configの読み込み
    config_path = "dams.yaml"
    if not os.path.exists(config_path) and os.path.basename(os.getcwd()) == "src":
        config_path = os.path.join("..", "dams.yaml")
    config = load_config(config_path)

    # 対象サイトの選択
    site_options = {k: v.name for k, v in config.sites.items()}
    selected_site_key = st.selectbox(
        "表示するダムを選択",
        options=list(site_options.keys()),
        format_func=lambda x: site_options[x],
    )

    target_site = config.sites[selected_site_key]
    target_dam = target_site.dam
    rain_station = target_site.rain

    # データの読み込み（DBから）
    rain_df = (
        load_data(rain_station.db_table_name, rain_station.id)
        if rain_station
        else pd.DataFrame()
    )
    dam_df = load_data(target_dam.db_table_name, target_dam.id)

    if not dam_df.empty:
        st.subheader(f"{target_dam.name} の状況")

        # グラフの描画
        with st.spinner("グラフを描画中..."):
            fig = plot_water_level(
                target_dam, dam_df.copy(), rain_station, rain_df.copy()
            )
            st.pyplot(fig)
            plt.close(fig)

    else:
        st.warning("データが不足しているためグラフを描画できません。")

    # 免責事項の表示（控えめに）
    disclaimer_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "doc",
        "Disclaimer.md",
    )
    if os.path.exists(disclaimer_path):
        with open(disclaimer_path, encoding="utf-8") as f:
            st.caption(f.read())


if __name__ == "__main__":
    main()

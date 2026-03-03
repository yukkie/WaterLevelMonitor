import pandas as pd
from config import DamConfig

def plot_water_level(dam: DamConfig, dam_df: pd.DataFrame, rain_station: DamConfig, rain_df: pd.DataFrame):
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import numpy as np
    import japanize_matplotlib

    # --- データ準備 ---
    for df in [rain_df, dam_df]:
        df['timestamp'] = pd.to_datetime(df['timestamp'])

    # --- データのパースと変換 ---

    # 雨量
    rain_df['rainfall_mm'] = pd.to_numeric(rain_df['rainfall'], errors='coerce')

    # ダムデータ
    # volume は千m³単位 → m³に変換
    dam_df['volume_m3'] = pd.to_numeric(dam_df['volume'], errors='coerce') * 1000
    dam_df['inflow_m3s'] = pd.to_numeric(dam_df['inflow'], errors='coerce').fillna(0)
    dam_df['outflow_m3s'] = pd.to_numeric(dam_df['outflow'], errors='coerce').fillna(0)
    
    # 欠損行はプロットから除外
    rain_df = rain_df.dropna(subset=['rainfall_mm'])
    dam_df = dam_df.dropna(subset=['volume_m3'])
    
    # 貯水率の計算
    dam_df['storage_rate'] = (dam_df['volume_m3'] / dam.capacity_m3) * 100
    
    # プロット作成 (上下2段のサブプロット, 高さ比率 5:1)
    fig, (ax1, ax3) = plt.subplots(2, 1, figsize=(10, 8), sharex=True, gridspec_kw={'height_ratios': [5, 1]})
    
    # --- 上段 (メイン): 貯水率と雨量 ---
    ax1.plot(dam_df['timestamp'], dam_df['storage_rate'], marker='o', linestyle='-', color='b', label='貯水率 (%)')
    ax1.set_ylabel("貯水率 (%)", color='b')
    ax1.tick_params(axis='y', labelcolor='b')
    ax1.grid(True)
    
    min_rate = dam_df['storage_rate'].min()
    max_rate = dam_df['storage_rate'].max()
    margin = (max_rate - min_rate) if (max_rate - min_rate) > 0 else 5
    ax1.set_ylim(min_rate - margin * 0.3, max_rate + margin * 0.1)
    
    ax2 = ax1.twinx()
    ax2.bar(rain_df['timestamp'], rain_df['rainfall_mm'], width=0.03, color='c', alpha=0.6, label='雨量 (mm/10min)')
    ax2.set_ylabel("雨量 (mm)", color='c')
    ax2.tick_params(axis='y', labelcolor='c')
    ax2.set_ylim(0, 20)
    
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='center left')
    
    # --- 下段 (サブ): 流入量と放流量 ---
    ax3.bar(dam_df['timestamp'], dam_df['inflow_m3s'], width=0.03, color='#8fce00', alpha=0.8, label='流入量 (m³/s)')
    ax3.bar(dam_df['timestamp'], -dam_df['outflow_m3s'], width=0.03, color='#ff6b6b', alpha=0.8, label='放流量 (m³/s)')
    
    ax3.axhline(0, color='gray', linewidth=0.8)
    ax3.set_ylabel("流量\n(m³/s)", fontsize=9)
    ax3.grid(True, axis='y', linestyle='--', alpha=0.5)
    ax3.legend(loc='lower left', fontsize=8)
    
    ax3.set_xlabel("日時")
    ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    fig.autofmt_xdate(rotation=45)
    
    plt.tight_layout()
    return fig

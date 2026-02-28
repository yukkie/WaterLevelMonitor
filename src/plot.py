import pandas as pd
from config import DamConfig

def plot_water_level(dam: DamConfig, dam_df: pd.DataFrame, rain_station: DamConfig, rain_df: pd.DataFrame):
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    import numpy as np
    
    # 日本語フォント対策（Windows等）
    plt.rcParams['font.family'] = 'Meiryo'
    
    # 貯水率の計算
    dam_df['storage_rate'] = (dam_df['volume_m3'] / dam.capacity_m3) * 100
    
    # プロット作成
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    # 1. 貯水率のプロット (左軸)
    ax1.plot(dam_df['timestamp'], dam_df['storage_rate'], marker='o', linestyle='-', color='b', label='貯水率 (%)')
    ax1.set_xlabel("日時")
    ax1.set_ylabel("貯水率 (%)", color='b')
    ax1.tick_params(axis='y', labelcolor='b')
    ax1.grid(True)
    
    # 貯水率のグラフを上部へ寄せるため、Y軸の下限値に余裕を持たせる
    min_rate = dam_df['storage_rate'].min()
    max_rate = dam_df['storage_rate'].max()
    margin = (max_rate - min_rate) if (max_rate - min_rate) > 0 else 5
    ax1.set_ylim(min_rate - margin * 0.3, max_rate + margin * 0.1)
    
    # 2. 雨量のプロット (右軸)
    ax2 = ax1.twinx()
    # 幅を太くする（ユーザー要望により、少々重なっても太く見せる）
    ax2.bar(rain_df['timestamp'], rain_df['rainfall_mm'], width=0.03, color='c', alpha=0.6, label='雨量 (mm/10min)')
    ax2.set_ylabel("雨量 (mm)", color='c')
    ax2.tick_params(axis='y', labelcolor='c')
    
    # 雨量は上限を20固定にする（ユーザー要望枠）
    ax2.set_ylim(0, 20)
    
    plt.title(f"{dam.name} 貯水率 と {rain_station.name} 雨量")
    
    # 凡例を統合して表示
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='center left')
    
    # X軸を日付で見やすく
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    fig.autofmt_xdate(rotation=45)
    
    plt.tight_layout()
    plt.savefig('test_plot.png')
    plt.show()

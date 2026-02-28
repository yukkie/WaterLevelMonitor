import pandas as pd
from config import DamConfig

def plot_water_level(dam: DamConfig, df: pd.DataFrame):
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    
    # 日本語フォント対策（Windows等）
    plt.rcParams['font.family'] = 'Meiryo'
    
    # 貯水率の計算
    df['storage_rate'] = (df['volume_m3'] / dam.capacity_m3) * 100
    
    plt.figure(figsize=(10, 5))
    plt.plot(df['timestamp'], df['storage_rate'], marker='o', linestyle='-', color='b')
    
    plt.title(f"{dam.name} の貯水率推移")
    plt.xlabel("日時")
    plt.ylabel("貯水率 (%)")
    plt.grid(True)
    
    # X軸を日付で見やすく
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    # 表示
    plt.show()

import requests
from bs4 import BeautifulSoup
import pandas as pd
import yaml
from pydantic import BaseModel
from typing import Dict
import os
from datetime import datetime

# ==========================================
# 1. 設定の読み込み (pydantic + yaml)
# ==========================================
class DamConfig(BaseModel):
    name: str
    id: str
    capacity_m3: int
    url_kind: str
    url_page: str

class AppConfig(BaseModel):
    dams: Dict[str, DamConfig]

def load_config(config_path="dams.yaml") -> AppConfig:
    with open(config_path, "r", encoding="utf-8") as f:
        raw_data = yaml.safe_load(f)
    return AppConfig(**raw_data)

# ==========================================
# 2. データ取得・解析 (Scraping)
# ==========================================
def fetch_dam_data(dam: DamConfig) -> pd.DataFrame:
    """
    指定されたダムの設定からURLを生成し、HTML内にあるDATファイルのリンクを取得して、
    その内部データをPandas DataFrameとして抽出する。
    """
    from bs4 import BeautifulSoup
    import urllib.parse
    import io
    
    url = f"https://www1.river.go.jp/cgi-bin/DspDamData.exe?ID={dam.id}&KIND={dam.url_kind}&PAGE={dam.url_page}"
    print(f"[{dam.name}] データ取得中: {url}")
    
    # HTTPアクセス (User-Agent偽装でアクセス制限を回避)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(url, headers=headers)
    response.encoding = response.apparent_encoding 
    
    # HTMLからDATファイルのダウンロードリンクを探す
    soup = BeautifulSoup(response.text, 'html.parser')
    links = soup.find_all('a', href=True)
    dat_link = next((link['href'] for link in links if link['href'].endswith('.dat')), None)
    
    if not dat_link:
        raise ValueError(f"[{dam.name}] DATファイルのリンクが見つかりませんでした")
        
    dat_url = urllib.parse.urljoin(url, dat_link)
    print(f"[{dam.name}] DATファイルをダウンロード中: {dat_url}")
    
    dat_res = requests.get(dat_url, headers=headers)
    dat_res.encoding = dat_res.apparent_encoding
    
    # DATファイルのパース (10行目から実データ)
    # 構造: 年/月/日, 時:分, 雨量, ... , 貯水量, ...など
    # 列仕様はダムによって多少異なる可能性があるが、標準ではインデックス4が貯水量の模様
    try:
        df = pd.read_csv(io.StringIO(dat_res.text), skiprows=9, header=None)
    except Exception as e:
        print(f"DATファイルのパースに失敗しました:\n{dat_res.text[:500]}")
        raise e
        
    # カラム名の手動割り当て（重要な時間と貯水量のみ）
    # 列0: 日付(YYYY/MM/DD)
    # 列1: 時刻(HH:MM)
    # 列4: 貯水量 (千m3 または m3) ※サイト仕様要確認だが、今回は扱いやすいよう数値化する
    parsed_df = pd.DataFrame()
    
    # 日付と時刻を取り出して、'24:00' の場合は '00:00' にして翌日にする
    date_series = pd.to_datetime(df[0])
    
    # 24:00を見つけるためのマスク
    is_2400 = df[1] == '24:00'
    
    # 時刻文字列を整形（24:00 は 00:00 に置換）
    time_series = df[1].replace('24:00', '00:00')
    
    # 日付と時刻を結合してdatetimeに
    parsed_df['timestamp'] = pd.to_datetime(date_series.dt.strftime('%Y-%m-%d') + ' ' + time_series)
    
    # 24:00だった行には1日分(24時間)を加算
    parsed_df.loc[is_2400, 'timestamp'] += pd.Timedelta(days=1)
    
    # 貯水量の抽出 ( '-' 等の欠損値を除外して数値化)
    # ※単位が千m3であれば1000をかける対応が必要だが、まずはそのまま取得してfloat変換
    parsed_df['volume_m3'] = pd.to_numeric(df[4], errors='coerce')
    
    # 欠損値(NaN)を含む行を削除
    parsed_df = parsed_df.dropna(subset=['volume_m3'])
    
    # 単位が「千m3」だと思われるため、1000を掛けてm3に変換
    parsed_df['volume_m3'] = parsed_df['volume_m3'] * 1000
    
    return parsed_df

# ==========================================
# 3. CSVへの保存・合成 (差分更新)
# ==========================================
def update_local_csv(dam_id: str, new_df: pd.DataFrame, data_dir="data"):
    """
    既存のCSVを読み込み、新しいデータをマージ（重複排除）して書き出す。
    """
    os.makedirs(data_dir, exist_ok=True)
    csv_path = os.path.join(data_dir, f"{dam_id}.csv")
    
    if os.path.exists(csv_path):
        # 既存データを読み込み
        existing_df = pd.read_csv(csv_path)
        existing_df['timestamp'] = pd.to_datetime(existing_df['timestamp'])
        
        # 新旧データを結合し、timestamp基準で重複を排除してソート
        combined_df = pd.concat([existing_df, new_df]).drop_duplicates(subset=['timestamp'])
        combined_df = combined_df.sort_values('timestamp').reset_index(drop=True)
        print(f"既存のデータ({len(existing_df)}件)に新しいデータを合成しました。合計: {len(combined_df)}件")
    else:
        combined_df = new_df
        print(f"新規CSVを作成しました: {len(combined_df)}件")
        
    # 保存
    combined_df.to_csv(csv_path, index=False)
    return combined_df

# ==========================================
# 4. グラフの描画 (Matplotlib)
# ==========================================
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

if __name__ == "__main__":
    # 設定の読み込み
    config = load_config()
    
    # とりあえず宮ヶ瀬ダムで実行
    target_dam = config.dams["miyagase"]
    
    # 1. データの取得
    new_data_df = fetch_dam_data(target_dam)
    
    # 2. ローカルCSVへの合成・保存
    final_df = update_local_csv(target_dam.id, new_data_df)
    
    # 3. グラフの表示
    plot_water_level(target_dam, final_df)

import requests
import pandas as pd
from bs4 import BeautifulSoup
import urllib.parse
import io
from config import DamConfig

def fetch_dam_data(dam: DamConfig) -> pd.DataFrame:
    """
    指定されたダムの設定からURLを生成し、HTML内にあるDATファイルのリンクを取得して、
    その内部データをPandas DataFrameとして抽出する。
    """
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
    try:
        df = pd.read_csv(io.StringIO(dat_res.text), skiprows=9, header=None)
    except Exception as e:
        print(f"DATファイルのパースに失敗しました:\n{dat_res.text[:500]}")
        raise e
        
    parsed_df = pd.DataFrame()
    
    # 日付と時刻を取り出して、'24:00' の場合は '00:00' にして翌日にする
    date_series = pd.to_datetime(df[0])
    is_2400 = df[1] == '24:00'
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

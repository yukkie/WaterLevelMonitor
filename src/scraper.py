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
    if dam.type == "rain":
        url = f"https://www1.river.go.jp/cgi-bin/DspRainData.exe?ID={dam.id}&KIND={dam.url_kind}&PAGE={dam.url_page}"
    else:
        url = f"https://www1.river.go.jp/cgi-bin/DspDamData.exe?ID={dam.id}&KIND={dam.url_kind}&PAGE={dam.url_page}"
        
    print(f"[{dam.name}] データ取得中: {url}")
    
    # HTTPアクセス (User-Agent偽装でアクセス制限を回避)
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    response = requests.get(url, headers=headers)
    
    # HTMLからDATファイルのダウンロードリンクを探す
    # 雨量ページはEUC-JP等の場合があるため、バイト列から正規表現で直接抜くかBeautifulSoupに任せる
    response.encoding = response.apparent_encoding 
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
    # 構造: 年/月/日, 時刻, 雨量 ... , 貯水量 ...など
    try:
        # header=Noneで読み込むと、列名は 0, 1, 2, ... となる
        # 余分なスペースによる列ズレを防ぐため skipinitialspace=True を指定
        df = pd.read_csv(io.StringIO(dat_res.text), skiprows=9, header=None, skipinitialspace=True)
    except Exception as e:
        print(f"DATファイルのパースに失敗しました:\n{dat_res.text[:500]}")
        raise e
        
    # 日付と時刻を取り出して、「24:00」の場合は「00:00」にして翌日として扱う
    date_series = pd.to_datetime(df[0])
    is_2400 = df[1] == '24:00'
    time_series = df[1].replace('24:00', '00:00')
    
    # 元のdfに 'timestamp' 列を追加
    df['timestamp'] = pd.to_datetime(date_series.dt.strftime('%Y-%m-%d') + ' ' + time_series)
    
    # 24:00だった行には1日分(24時間)を加算
    df.loc[is_2400, 'timestamp'] += pd.Timedelta(days=1)
    
    if dam.type == "rain":
        # 雨量抽出 (CSV 2列目)
        df['rainfall_mm'] = pd.to_numeric(df[2], errors='coerce')
        # 全データ残すが、雨量がNaNの行は（時刻行など不要行の可能性があるため）ドロップ
        df = df.dropna(subset=['rainfall_mm'])
    else:
        # 貯水量の抽出 (CSV 4列目)
        df['volume_m3'] = pd.to_numeric(df[4], errors='coerce')
        # skipinitialspace=True とカンマ区切りの仕様上、空の余白列がズレてパースされる
        # 流入量 (CSV 6列目), 放流量 (CSV 8列目) ※ 5, 7列目は空のパディング列
        df['inflow_m3s'] = pd.to_numeric(df[6], errors='coerce').fillna(0)
        df['outflow_m3s'] = pd.to_numeric(df[8], errors='coerce').fillna(0)
        
        # ダムのデータがない行はドロップ
        df = df.dropna(subset=['volume_m3'])
        # 単位が「千m3」だと思われるため、1000を掛けてm3に変換
        df['volume_m3'] = df['volume_m3'] * 1000
    
    # string型の列名をすべて string型 に統一する（Pandas警告対策）
    df.columns = df.columns.astype(str)
        
    return df

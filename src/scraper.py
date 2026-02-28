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
        # 余分なスペースによる列ズレを防ぐするため skipinitialspace=True を指定
        df = pd.read_csv(io.StringIO(dat_res.text), skiprows=9, header=None, skipinitialspace=True)
    except Exception as e:
        print(f"DATファイルのパースに失敗しました:\n{dat_res.text[:500]}")
        raise e
        
    if dam.type == "rain":
        # 雨量の列(CSV 2列目)がNaNの行は（時刻行など不要行の可能性があるため）ドロップ
        df = df.dropna(subset=[2])
    else:
        # 貯水量(CSV 4列目)のデータがない行は不要行としてドロップ
        df = df.dropna(subset=[4])
    
    # string型の列名をすべて string型 に統一する（Pandas警告対策）
    df.columns = df.columns.astype(str)
        
    return df

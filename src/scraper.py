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
    属性フィルタリング:
      - '-' (未受信) の行はスキップ
      - '$' (欠測) の値は NaN に変換
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
    try:
        # header=Noneで読み込むと、列名は 0, 1, 2, ... となる
        # 余分なスペースによる列ズレを防ぐするため skipinitialspace=True を指定
        df = pd.read_csv(io.StringIO(dat_res.text), skiprows=9, header=None, skipinitialspace=True)
    except Exception as e:
        print(f"DATファイルのパースに失敗しました:\n{dat_res.text[:500]}")
        raise e

    # string型の列名をすべて string型 に統一する（Pandas警告対策）
    df.columns = df.columns.astype(str)

    # --- 属性フィルタリング ---
    # '-' (未受信) / '$' (欠測) の処理
    if dam.type == "rain":
        # 雨量の列(2列目)で '-' または '$' が入っている行を処理
        # まず文字列として確認
        col2_str = df['2'].astype(str).str.strip()
        # '-' の行は未受信 → 除外
        df = df[col2_str != '-']
        # '$' の行は欠測 → NaN に変換
        df.loc[df['2'].astype(str).str.strip() == '$', '2'] = pd.NA
        # 数値変換できない行もドロップ（従来互換）
        df['2'] = pd.to_numeric(df['2'], errors='coerce')
        df = df.dropna(subset=['2'])
    else:
        # ダムデータ: 貯水量(4列目)で判定
        col4_str = df['4'].astype(str).str.strip()
        # '-' の行は未受信 → 除外
        df = df[col4_str != '-']
        # '$' のある値カラムを NaN に変換
        for col in ['2', '4', '6', '8', '10']:
            if col in df.columns:
                mask = df[col].astype(str).str.strip() == '$'
                df.loc[mask, col] = pd.NA
        # 貯水量が数値変換できない行は除外
        df['4'] = pd.to_numeric(df['4'], errors='coerce')
        df = df.dropna(subset=['4'])
        
    return df

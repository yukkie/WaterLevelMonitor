import io
import os
import urllib.parse

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .config import StationConfig


def _fetch_dam_data(dam: StationConfig) -> pd.DataFrame:
    """
    Extract層: 指定されたダムの設定からURLを生成し、
    HTML内にあるDATファイルのリンクを取得して、
    その内部データを純粋なPandas DataFrameとして抽出する（未加工RAWデータ）。
    """
    if dam.type == "rain":
        url = (
            "https://www1.river.go.jp/cgi-bin/DspRainData.exe?"
            f"ID={dam.id}&KIND={dam.url_kind}&PAGE={dam.url_page}"
        )
    else:
        url = (
            "https://www1.river.go.jp/cgi-bin/DspDamData.exe?"
            f"ID={dam.id}&KIND={dam.url_kind}&PAGE={dam.url_page}"
        )

    print(f"[{dam.name}] データ取得中: {url}")

    # HTTPアクセス (User-Agent偽装でアクセス制限を回避)
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(url, headers=headers)

    # HTMLからDATファイルのダウンロードリンクを探す
    response.encoding = response.apparent_encoding
    soup = BeautifulSoup(response.text, "html.parser")
    links = soup.find_all("a", href=True)
    dat_link = next(
        (link["href"] for link in links if link["href"].endswith(".dat")), None
    )

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
        df = pd.read_csv(
            io.StringIO(dat_res.text), skiprows=9, header=None, skipinitialspace=True
        )
    except Exception as e:
        print(f"DATファイルのパースに失敗しました:\n{dat_res.text[:500]}")
        raise e

    # string型の列名をすべて string型 に統一する（Pandas警告対策）
    df.columns = df.columns.astype(str)

    # --- RAWデータのバックアップ保存 ---
    os.makedirs("data", exist_ok=True)
    df.to_csv(f"data/raw_{dam.id}.csv", index=False)

    return df

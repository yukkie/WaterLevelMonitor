import sys
import os
import requests
import urllib.parse
from bs4 import BeautifulSoup

# パスを追加してsrcモジュールを読み込めるようにする
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(project_root, 'src'))

from config import load_config

def main():
    config_path = os.path.join(project_root, 'dams.yaml')
    config = load_config(config_path)
    
    targets = [
        (config.dams['miyagase'], 'miyagase_dam'),
        (config.dams['miyagase_oizawa_rain'], 'miyagase_rain')
    ]
    
    fixtures_dir = os.path.join(project_root, 'tests', 'fixtures')
    os.makedirs(fixtures_dir, exist_ok=True)
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    for target, name in targets:
        if target.type == "rain":
            base_url = "https://www1.river.go.jp/cgi-bin/DspRainData.exe"
        else:
            base_url = "https://www1.river.go.jp/cgi-bin/DspDamData.exe"
            
        url = f"{base_url}?ID={target.id}&KIND={target.url_kind}&PAGE={target.url_page}"
        print(f"[{name}] アクセス先: {url}")
        
        # HTMLからDATファイルのダウンロードリンクを探す
        response = requests.get(url, headers=headers)
        response.encoding = response.apparent_encoding 
        soup = BeautifulSoup(response.text, 'html.parser')
        links = soup.find_all('a', href=True)
        dat_link = next((link['href'] for link in links if link['href'].endswith('.dat')), None)
        
        if not dat_link:
            print(f"[{name}] DATファイルのリンクが見つかりませんでした")
            continue
            
        dat_url = urllib.parse.urljoin(url, dat_link)
        print(f"[{name}] DATファイルURL: {dat_url}")
        
        # 実際にダウンロード
        dat_res = requests.get(dat_url, headers=headers)
        dat_res.raise_for_status()
        dat_res.encoding = 'shift_jis' # 国交省サイトはShift-JIS
        
        filepath = os.path.join(fixtures_dir, f"{name}.dat")
        # 内部で扱いやすいようにUTF-8で保存しておく
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(dat_res.text)
            
        print(f"[{name}] 保存完了: {filepath}\n")

if __name__ == "__main__":
    main()

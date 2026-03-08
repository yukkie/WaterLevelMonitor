# WaterLevelMonitor

ダムの貯水位と雨量データを「川の防災情報」から取得し、可視化・蓄積するツールです。

## 公開サイト
デプロイ済みのアプリケーションは以下から確認できます：
👉 **[https://waterlevelmonitor.streamlit.app/](https://waterlevelmonitor.streamlit.app/)**

## 主な機能
- **自動データ収集**: 「川の防災情報」から最新の10分間隔データを取得し、データベース(Supabase)に蓄積します。
- **グラフ可視化**: 貯水率推移と雨量の相関を、見やすいグラフで表示します。
- **マルチデバイス対応**: Streamlit Cloud により、PCやスマホのブラウザからいつでも状況を確認可能です。

## クイックスタート
プロジェクトルートにあるランチャースクリプトを使用して、各機能を起動できます。
Windowsの場合は `.bat` または `.ps1`、Linux/macOSの場合は `.sh` を使用してください。

### 1. パイプラインの実行 (データの更新)
最新データを取得してDBに保存します。コマンド引数なしで実行します。
```bash
./run.sh
# または run.bat / ./run.ps1
```

### 2. Streamlit アプリの起動
ブラウザでダムのグラフを表示します。
```bash
./run.sh streamlit
```

### 3. テストの実行
ユニットテストおよびE2Eテストを実行し、レポートを生成します。
```bash
./run.sh test
```
生成される `report.html` や `htmlcov/index.html` で詳細な結果を確認できます。

## ドキュメント案内
詳細な仕様や設計については、以下のドキュメントを参照してください。

### システム設計・仕様
- [Architecture.md](./doc/Architecture.md): ETLアーキテクチャやモジュール構成の解説。
- [Diagram.md](./doc/Diagram.md): Mermaidによる設計図面。
- [Spec.md](./doc/Spec.md): 取得データ項目やDBスキーマの定義。
- [Disclaimer.md](./doc/Disclaimer.md): 利用上の注意点・免責事項。

### プロジェクト管理
- [Task.md](./doc/Task.md): 開発フェーズごとの進捗状況とToDoリスト。
- [TestStrategy.md](./tests/TestStrategy.md): 自動テストの戦略、対象範囲、および未テスト領域の宣言。

---
Developed for monitoring dam water levels and rainfall in Japan.

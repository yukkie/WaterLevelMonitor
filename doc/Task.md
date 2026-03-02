# WaterLevelMonitor 開発タスク一覧 (Task.md)

本プロジェクトの今後の拡張計画（Future Plans）と実装タスクを管理するためのドキュメントです。

## フェーズ 1: 基本機能の確立 (MVP) -> 完了 🎉
- [x] 指定したダム（例: 宮ヶ瀬ダム）のページから水位・貯水量データを取得する機能
- [x] 不安定なHTMLパースを避け、公式のDATファイル（CSV相当）を直接ダウンロードして解析する堅牢なロジックの実装
- [x] 取得元サイトの「過去1週間分」という表示制限を回避するため、ローカルのCSVファイルへ差分データを蓄積する機能
- [x] `dams.yaml` による対象ダムデータ（観測所ID、有効貯水容量など）の外部設定・管理
- [x] データの可視化（横軸: 時間、縦軸: 貯水率での折れ線グラフ描画機能: Matplotlib）
- [x] 将来の拡張性を見据えたソースコードのモジュール化 (`src/` ディレクトリ配下への機能分割)

## フェーズ 2: データの拡充と利便性向上
- [x] **雨量データの追加統合**
  - 流域平均雨量など、別のデータソース（気象庁APIなど）から降水量データを取得するモジュール (`src/rainfall_scraper.py` 等) の作成。
  - 取得した雨量データを既存の貯水量CSVと結合するか、別のローカルCSVとして蓄積・管理する。
  - グラフ描画モジュール (`src/plot.py`) を改修し、上段に「貯水率の折れ線グラフ」、下段（または2軸）に「雨量の棒グラフ」を重ねて表示し、相関を確認できるようにする。
- [x] **流入量・放流量データの追加パースと高度な可視化**
  - 既存のDATファイルパース処理 (`src/scraper.py`) を拡張し、貯水量だけでなく「流入量」「放流量」「水位」などの指標も同時に抽出・保存する。
  - 単位やスケールが全く異なる4つの指標（水位[m], 貯水率[%], 流入量[m³/s], 放流量[m³/s]）が1つの図で分かりにくくなるのを防ぐため、複数のサブプロット（上下分割）を用いたダッシュボード的なUIレイアウトを設計・実装する。
- [ ] **対象ダムの追加検証**
  - `dams.yaml` に他のダム（城山ダムなど）を追加し、複数ダムのデータ同時取得およびグラフの並列出力が行えるかテストする。

## フェーズ 3: Webアプリケーション化 (Streamlit)
- [x] **Streamlit によるWeb UI化**
  - `src/app.py` を新規作成し、既存の `plot.py` のグラフ描画ロジックを `st.pyplot(fig)` で表示するStreamlitアプリへ移行する。
  - ダム選択（`st.selectbox`）、表示期間の切り替え（`st.date_input`）などのインタラクティブUIを実装する。
  - ローカル確認: `streamlit run src/app.py` でブラウザ上で動作確認。
- [x] **オンデマンドデータ取得（10分ガード付き）**
  - Streamlitアプリでページを開いたときに自動でスクレイピングを実行し、最新データを取得・表示する。
  - ただし、データソースの更新頻度が10分ごとのため、前回取得から10分以内の場合はスクレイピングをスキップするガードを入れる。
  - 定期実行（Cron等）は不要。Streamlitアプリへのアクセス時にデータ蓄積も兼ねる。
- [x] **Streamlit Community Cloud へのデプロイ**
  - GitHubアカウントでログインし、本リポジトリを連携してデプロイする。
  - `requirements.txt` にStreamlit等の依存ライブラリを追加する。

## フェーズ 4: テストと CI/CD
- [ ] **pytest によるユニットテストの作成**
  - `tests/` ディレクトリを作成し、各モジュール (`scraper.py`, `storage.py`, `pipeline.py`, `plot.py`) のテストを実装する。
  - 外部サイトへのアクセスを伴うテストは `unittest.mock` でモック化する。
- [ ] **GitHub Actions による CI パイプラインの構築**
  - `.github/workflows/ci.yml` を作成し、push / PR 時に自動で pytest と lint (flake8等) を実行する。
  - Branch Protection Rules を設定し、テストが通らないコードの master マージを防止する。

## フェーズ 5: データ管理の改善 — Supabase (PostgreSQL) 移行 -> 完了 🎉
- [x] **Supabase プロジェクトのセットアップ**
  - `dam_data` / `rain_data` テーブルを作成する。
  - `service_role` キーと Project URL を Streamlit Secrets / 環境変数に設定する。
- [x] **`src/db.py` の新規作成 — DB接続・CRUD層**
  - `supabase-py` を使った接続、UPSERT、SELECT の共通関数を実装する。
- [x] **`src/scraper.py` の改修 — `$`/`-` 属性の処理**
  - `-`（未受信）の行をフィルタリング（INSERTしない）。
  - `$`（欠測）の値カラムを `NaN` (→DB上は NULL) に変換する。
- [x] **`src/storage.py` の改修 — CSV→DB書き込みへの切り替え**
  - `update_local_csv` を `upsert_to_db` に置き換える。CSVマージ処理は隔離して残す。
- [x] **`src/pipeline.py` / `src/app.py` の改修**
  - データフローを DB 経由に変更。`git_push` 呼び出しを削除。
- [x] **`src/git_push.py` の削除**
- [x] **`scripts/migrate_csv_to_db.py` の作成 — 既存CSV→DB移行スクリプト**
  - `data/*.csv` を読み込み、`-` 行スキップ・`$` を NULL に変換してバルク挿入する。
- [x] **`requirements.txt` の更新** — `supabase` パッケージ追加

## リファクタリング (技術的負債)
- [ ] **`src/plot.py` のリファクタリング — CSV/DB デュアル対応の解消**
  - 現在、DB由来（`timestamp`, `rainfall` 等の名前付きカラム）とCSV由来（`'0'`, `'2'` 等の数字カラム）の両方に対応する分岐がある。
  - DB移行完了後、CSV互換コードを削除し、DB由来のカラム名のみに統一する。
- [ ] **`src/main.py` の `plt.show()` が動作しない不具合の修正**
  - `FigureCanvasAgg is non-interactive` 警告が出てグラフウィンドウが表示されない。
  - `supabase` パッケージ追加後に matplotlib のバックエンド解決が変わった可能性あり。PNG保存は正常。
- [ ] **データ取得・UPSERT の高速化**
  - 毎回全件（2000件以上）をUPSERTしているため、Streamlit アプリの表示が遅い。
  - 差分のみUPSERTする仕組み（DBの最終タイムスタンプ以降のデータのみ挿入）を検討する。
- [ ] **`src/db.py` — Supabase SELECT の1000件制限対策**
  - Supabase REST API のデフォルト返却上限は1000行。データ蓄積でグラフが途中で切れる恐れあり。
  - ページネーションまたは `limit` 設定で全件取得できるようにする。
- [ ] **`src/db.py` — Supabase クライアントのキャッシュ化**
  - 現在、UPSERT/SELECT のたびに `create_client()` を呼んでいる。1セッション1インスタンスに。


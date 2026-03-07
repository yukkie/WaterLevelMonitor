# WaterLevelMonitor 開発タスク一覧 (Task.md)

本プロジェクトの今後の拡張計画（Future Plans）と実装タスクを管理するためのドキュメントです。

## フェーズ 1: 基本機能の確立 (MVP) -> 完了 🎉
- [x] 指定したダム（例: 宮ヶ瀬ダム）のページから水位・貯水量データを取得する機能
- [x] 不安定なHTMLパースを避け、公式のDATファイル（CSV相当）を直接ダウンロードして解析する堅牢なロジックの実装
- [x] 取得元サイトの「過去1週間分」という表示制限を回避するため、Supabase DBへ差分データを蓄積する機能
- [x] `dams.yaml` による対象ダムデータ（観測所ID、有効貯水容量など）の外部設定・管理
- [x] データの可視化（横軸: 時間、縦軸: 貯水率での折れ線グラフ描画機能: Matplotlib）
- [x] 将来の拡張性を見据えたソースコードのモジュール化 (`src/` ディレクトリ配下への機能分割)

## フェーズ 2: データの拡充と利便性向上
- [x] **雨量データの追加統合**
  - 流域平均雨量など、別のデータソース（気象庁APIなど）から降水量データを取得するモジュール (`src/rainfall_scraper.py` 等) の作成。
  - 取得した雨量データをDBに蓄積・管理する。
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
  - CSV互換コードを完全に削除し、DB書き込み専用に簡素化。
- [x] **`src/pipeline.py` / `src/app.py` の改修**
  - データフローを DB 経由に変更。`git_push` 呼び出しを削除。
- [x] **`src/git_push.py` の削除**
- [x] **`scripts/migrate_csv_to_db.py` の作成・実行・削除 — 既存CSV→DB移行**
  - 移行完了につき、スクリプトおよび `data/` フォルダを削除。
- [x] **`requirements.txt` の更新** — `supabase` パッケージ追加

## 雨量グラフの改善 — 積算雨量表示
- [x] **Step 1: 1時間積算雨量の導入**
  - 現状の10分雨量はほぼ0〜1mmで棒グラフが潰れて視認性が悪い。
  - `plot.py` で `resample('1h')` を使い、1時間ごとの積算雨量に集約して棒グラフ表示する。
  - Y軸ラベルを「雨量 (mm/h)」に変更。棒の幅も調整。
- [ ] **Step 2: 表示期間に応じた動的集約**
  - 将来、表示期間を選択するUI（`st.date_input` 等）を追加した際に、期間に応じて集約間隔を自動調整する。
  - 目安: ~1週間→1時間、~1ヶ月→6時間、~3ヶ月以上→1日。

## リファクタリング (技術的負債)
- [x] **`src/plot.py` のリファクタリング — CSV/DB デュアル対応の解消**
  - CSV互換コードを削除し、DB由来のカラム名のみに統一した。
- [x] **`src/main.py` の `plt.show()` が動作しない不具合の修正**
  - `FigureCanvasAgg is non-interactive` 警告が出てグラフウィンドウが表示されない。
  - `supabase` パッケージ追加後に matplotlib のバックエンド解決が変わった可能性あり。PNG保存は正常。
  - 調査結果: venv / システムPython ともにバックエンドは `tkagg`。`.env` + `python-dotenv` 対応後、`venv\Scripts\python.exe main.py` で正常動作を確認。
- [x] **`src/app.py` — 10分ガードが同一ユーザーでも効いていない不具合**
  - `st.session_state` ベースのガードがリロードのたびにリセットされるため機能しなかった。
  - `db.py` に `get_latest_timestamp()` を追加し、DBの最新タイムスタンプを取得して10分以内かどうかを判定する方式に変更。
- [x] **データ取得・UPSERT の高速化**
  - 毎回全件（2000件以上）をUPSERTしているため、Streamlit アプリの表示が遅い。
  - 差分のみUPSERTする仕組み（DBの最終タイムスタンプ以降のデータのみ挿入）を検討する。
- [x] **`src/db.py` — Supabase SELECT の1000件制限対策**
  - Supabase REST API のデフォルト返却上限は1000行。データ蓄積でグラフが途中で切れる恐れあり。
  - ページネーションまたは `limit` 設定で全件取得できるようにする。
- [x] **`src/db.py` — Supabase クライアントのキャッシュ化**
  - 現在、UPSERT/SELECT のたびに `create_client()` を呼んでいる。1セッション1インスタンスに。

## ETL分離にもとづくリファクタリング (アーキテクチャ改善)
現状、`db.py`（ロード層）がスクレイピング先のファイル形式に依存したドメイン知識（パース、マッピング、'$', '-'の処理など）を多く持ちすぎており、責務が混同している。
データの流れを **Extract (抽出) -> Transform (変換) -> Load (保存)** に明確に分離し、各層の責務を単一化する。

- [ ] **現状の分析と責務の再定義**
  - **【現在】**
    - `scraper.py`: URL生成、ダウンロード、CSV読み込み、一部の行フィルタリング（`-`, `$`の除外など）。**（EとTが混在）**
    - `pipeline.py`: 中継のみ。**（薄すぎる）**
    - `db.py`: 日時文字列のパース（JST→UTC）、列名のマッピング、行から辞書への変換処理。**（LなのにTをやっている）**
  - **【理想（ターゲットアーキテクチャ）】**
    - **Extract (`scraper.py`)**:
      - 責務: 外部サイトからRAWデータをダウンロードし、一切加工せずにPandas DataFrameとして取り出すことだけを行う。
    - **Transform (`pipeline.py` または 新設 `transformer.py`)**:
      - 責務: RAWデータをシステムのテーブルスキーマ（DBと1:1の形式）に変換する。
      - 処理: 日時文字列の結合とUTC変換（ベクトル演算）、異常値の処理、不要列の削除、カラム名のマッピング（例: `2` → `rainfall`）、`station_id` の付与。
    - **Load (`db.py` / `storage.py`)**:
      - 責務: 受け取った整形済みデータをDBにそのまま流し込む純粋なインフラ機能。
      - 処理: DataFrameの `to_dict('records')` を受け取って `upsert()` するだけ（パースやマッピングの知識は持たない）。

- [ ] **Step 1: Extract (scraper.py) の純粋化**
  - `scraper.py` で現在行っている `dropna` などのクレンジング処理を削除し、純粋にRAWデータをそのまま DataFrame として返す責務にする。
- [ ] **Step 2: Transform ロジックの移動と集約 (`pipeline.py`)**
  - `db.py` 内にある `_vectorized_parse_timestamp` や `col_mapping`、`_safe_float` などのパース・変換・抽出処理を `pipeline.py`（または専用モジュール）側に移動する。
  - `scraper` から受け取ったRAWデータを引数に取り、DBスキーマ構成と完全に一致するDataFrameを出力する関数を作る。
- [ ] **Step 3: Load (`db.py`) のシンプル化**
  - `db.py` の `_upsert_data` 内で行っているループ生成やマッピングロジックを全廃する。
  - 単純に `upsert(records)` を実行するだけの薄い共通関数 `upsert_records(table_name, records)` に置き換える。

## フェーズ 6: データ取得の定期実行とアーキテクチャ分離
- [ ] **GitHub Actions によるデータ定期取得 (Cron)**
  - 現在 Streamlit アプリへのアクセス時に行っているスクレイピング処理を、GitHub Actions のスケジュール実行 (Cron) に移行し、10〜20分間隔で自動収集する。
  - Webアプリ側（Streamlit）はスクレイピングを行わず、Supabase からデータを読み込んでグラフを表示するだけの役割に専念させ、ページロード時間とユーザー体験を劇的に向上させる。

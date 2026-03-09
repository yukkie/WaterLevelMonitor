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
- [x] **対象ダムの追加検証（利根川水系: 矢木沢ダムなど）**
  - `dams.yaml` に矢木沢ダムを追加し、正常に取得・表示できるか検証する。
  - **仕様変更の検討**: 利根川水系のダムはDATファイル内に「流域平均雨量」が含まれるため、個別の雨量観測所（`rain` 設定）を必要としないパターンの実装・動作確認を行う。
  - 複数ダムのデータ同時取得およびグラフの切り替えが正常に行えるかテストする。

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
- [x] **テストランナーと基本構成の導入 (pytest)**
  - `tests/` 下に `conftest.py` などの標準ディレクトリを切り、`pytest-mock` をセットアップした。
- [x] **E2E（End-to-End）スナップショットテストの作成**
  - アーキテクチャの大規模改修（ETL分離）を行う前に、既存システムが正常に出力する最終形式（SupabaseへのUPSERTレコード）を完全に保存する。
  - `tests/e2e/test_pipeline.py` を作成し、ローカルに保存した実際のDATファイル（Fixture）を入力として、出力結果が JSON スナップショットと完全に一致することを保証する仕組みを作った。
- [x] **リファクタリング後のユニットテストの作成**
  - [x] 何を単体テストとし、何を統合/E2Eテストとするかの方針をまとめた `tests/TestStrategy.md` を作成する。
  - [x] ETL分離が完了し、副作用を持たなくなった `scraper.py`, `converter.py`, `plot.py` のロジックに対して、より細粒度の単体テスト（Unit test）をあとで追加する。
  - [x] `pytest-cov`, `pytest-html` を導入し、カバレッジ（網羅率）とテスト結果のグラフィカルなHTMLレポートを出力できるようにする。
- [x] **Linter & Formatter (Ruff) の導入**
  - 未使用のインポートや命名規則違反の自動検知（Lint）、およびコードスタイルの統一（Format）を高速に行うため、Rust製の `ruff` を導入する。
  - **選定理由:** 従来の `flake8` + `black` + `isort` の組み合わせと比較して、単一のツールで完結するため設定が容易であり、実行速度が圧倒的に速いためCI/CDやローカルでの開発体験が大きく向上する。
  - [x] `pre-commit` を導入し、コミット時に自動で Ruff を実行する仕組みを構築する。
- [x] **GitHub Actions による CI パイプラインの構築**
  - `.github/workflows/ci.yml` を作成し、push / PR 時に自動で pytest と lint (Ruff) 実行を確認する。
  - 実DBへの接続を伴うテスト（将来用）を除外するためのマーカー (`-m "not remote_db"`) を導入した。

## フェーズ 5: プルリクエスト駆動開発 (PR Workflow) の導入 -> 完了 🎉
- [x] **GitHub の Branch Protection 導入手順の整理**
  - `master` ブランチへの直接 Push を禁止し、CI (pytest/ruff) のパスを必須とする設定手順をドキュメント化する。
- [x] **ローカル開発ワークフローの更新**
  - 今後の開発でブランチを切って PR を出す運用方法を `Architecture.md` などのドキュメントに追記・整理する。

## フェーズ 6: データ管理の改善 — Supabase (PostgreSQL) 移行 -> 完了 🎉
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

- [x] **現状の分析と責務の再定義**
  - **【現在】**
    - `scraper.py`: URL生成、ダウンロード、CSV読み込み、一部の行フィルタリング（`-`, `$`の除外など）。**（EとTが混在）**
    - `pipeline.py`: 中継のみ。**（薄すぎる）**
    - `db.py`: 日時文字列のパース（JST→UTC）、列名のマッピング、行から辞書への変換処理。**（LなのにTをやっている）**
    - **Extract (`scraper.py`)**:
      - 責務: 外部サイトからRAWデータをダウンロードし、一切加工せずにPandas DataFrameとして取り出すことだけを行う。
      - 処理: 単体試験やデバッグ容易性向上のため、取得したRAWデータをそのまま（未加工で）CSVファイルとしてローカル保存する機能を持たせる。
    - **Transform (`pipeline.py` または 新設 `transformer.py`)**:
      - 責務: RAWデータをシステムのテーブルスキーマ（DBと1:1の形式）に変換する。
      - 処理: 日時文字列の結合とUTC変換（ベクトル演算）、異常値の処理、不要列の削除、カラム名のマッピング（例: `2` → `rainfall`）、`station_id` の付与。
    - **Load (`db.py` / `storage.py`)**:
      - 責務: 受け取った整形済みデータをDBにそのまま流し込む純粋なインフラ機能。
      - 処理: DataFrameの `to_dict('records')` を受け取って `upsert()` するだけ（パースやマッピングの知識は持たない）。

- [x] **Step 1: Extract (scraper.py) の純粋化とバックアップ機能の追加**
  - `scraper.py` で現在行っている `dropna` などのクレンジング処理を削除し、純粋にRAWデータをそのまま DataFrame として返す責務にする。
  - 取得したPandas DataFrameを、加工する前にローカルにCSVファイルとして `to_csv` 保存する処理を追加する（単体試験・デバッグ用）。
- [x] **Step 2: Transform ロジックの移動と集約 (`pipeline.py`)**
  - `db.py` 内にある `_vectorized_parse_timestamp` や `col_mapping`、`_safe_float` などのパース・変換・抽出処理を `pipeline.py`（または専用モジュール）側に移動する。
  - `scraper` から受け取ったRAWデータを引数に取り、DBスキーマ構成と完全に一致するDataFrameを出力する関数を作る。
- [x] **Step 3: Load (`db.py`) のシンプル化**
  - `db.py` の `_upsert_data` 内で行っているループ生成やマッピングロジックを全廃する。
  - 単純に `upsert(records)` を実行するだけの薄い共通関数 `upsert_records(table_name, records)` に置き換える。

## フェーズ 7: データ取得の定期実行とアーキテクチャ分離 -> 完了 🎉
- [x] **ETLアーキテクチャの分離 (`pipeline.py` と `app.py` の分割)**
  - Webアプリ側（Streamlit `app.py`）から10分ガード付きスクレイピング処理を取り除き、Supabaseからデータを読み込んでグラフを表示するだけの役割に専念させ、ページロード時間を向上させた。
  - 別途、スタンドアローンのバッチスクリプトとして `src/pipeline.py` を新設し、データ収集処理を独立させた。
- [x] **Streamlit UIの自動テスト (`test_app.py`) の導入**
  - アーキテクチャ分離に伴い、UI側のE2Eテスト（`AppTest` 利用）とデータパイプライン側のE2Eテストに分割してシステム全体の堅牢性を高めた。
- [x] **GitHub Actions によるデータ定期取得 (Cron)**
  - `.github/workflows/cron.yml` を作成し、20分おきに `src/pipeline.py` を自動実行する設定を追加した。
  - **【運用上の注意点】**
    - 本設定を有効化させるには、GitHubの `Settings > Secrets and variables > Actions` にて、以下の Repository secrets を追加する必要がある。
      1. `SUPABASE_URL`
      2. `SUPABASE_KEY` (ローカルの `.env` と同値)

## 開発環境の改善 (Developer Experience)
- [x] **YAML スキーマの自動生成**
  - `src/config.py` の Pydantic モデルから JSON Schema を出力するスクリプトを作成する。
  - VS Code 等のエディタで `dams.yaml` 編集時にスキーマバリデーションと補完が効くように設定する。
- [ ] **YAML バリデーションの自動実行**
  - `dams.yaml` がスキーマ（Pydanticモデル）に準拠しているかを、テスト実行時やCIで自動検証する仕組みを導入する。
- [x] **Streamlit の起動不具合（インポートエラー）の修正**
  - 相対インポート (`from .xxx`) を絶対インポート (`from src.xxx`) に切り替えることで、`streamlit run src/app.py` で直接起動した際もパッケージとして認識を維持し、Cloud環境でも動作するようにした。

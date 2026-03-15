# WaterLevelMonitor アーキテクチャ設計書

本ドキュメントでは、各ダムの水位・貯水率データ監視アプリケーションの設計・構成について記述します。

## 1. ディレクトリ構成
将来的な機能追加（雨量データの取得、別ダムへの対応など）を見据え、機能をモジュール分割しています。

```text
WaterLevelMonitor/
├── .github/workflows/
│   ├── ci.yml             # Push/PR 時: ruff + pytest
│   └── cron.yml           # 20分おきに src/pipeline.py を自動実行
├── doc/                   # ドキュメント配置ディレクトリ
│   ├── Architecture.md    # 本ドキュメント
│   ├── Diagram.md         # Mermaid モジュール構成図
│   ├── Disclaimer.md      # 免責事項
│   ├── Spec.md            # 仕様書
│   ├── Task.md            # タスク管理
│   └── dams_schema.json   # dams.yaml の JSON Schema（Pydantic から自動生成）
├── scripts/
│   └── generate_schema.py # dams_schema.json を再生成するユーティリティ
├── src/                   # ソースコード配置ディレクトリ
│   ├── config.py          # 設定(YAML)の読み込みと型定義 (Pydantic)
│   ├── scraper.py         # Extract: HTTP取得→RAW DataFrame（未加工）
│   ├── converter.py       # Transform: RAW DataFrame→DBスキーマ形式・スロットリングガード
│   ├── storage.py         # Load: Supabase UPSERT / ページネーション SELECT
│   ├── plot.py            # グラフ描画ロジック (matplotlib Figure 生成)
│   ├── pipeline.py        # データ収集バッチ（GitHub Actions Cron から実行）
│   ├── main.py            # CLIエントリーポイント（ローカル実行・グラフ PNG 出力）
│   └── app.py             # Streamlit Webアプリのエントリーポイント（DB 表示専念）
├── tests/
│   ├── conftest.py
│   ├── e2e/
│   │   ├── test_pipeline.py  # パイプライン全体スナップショットテスト
│   │   ├── test_main.py
│   │   └── test_app.py
│   ├── unit/
│   │   ├── test_scraper.py
│   │   ├── test_converter.py
│   │   └── test_plot.py
│   ├── scripts/
│   │   └── fetch_fixtures.py # フィクスチャ取得ユーティリティ
│   ├── fixtures/             # ローカルの生 HTML / DAT ファイル
│   └── TestStrategy.md       # テスト方針ドキュメント
├── dams.yaml              # ダムの設定データ（マスターデータ）
└── requirements.txt       # 依存ライブラリ一覧
```

## 2. データ管理の設計方針 (ダム設定)

各対象ダムのURLパラメーター（観測所IDなど）や満水時の容量といった「マスターデータ」は、コード内にハードコーディングせず外部設定ファイル `dams.yaml` にて管理します。

### 採用技術: YAML + Pydantic
人間にとって読み書きしやすい **YAML形式** を採用し、Python側での読み込み時にはデータ検証ライブラリである **Pydantic** を用いて型チェックを行います。これにより以下のようなメリットがあります。
* 新しい観測対象が増えた際、Pythonコードを一切修正することなくYAMLファイルへの追記のみで対応可能です。
* 必須項目の設定漏れや、数値が入るべきところに文字列が入っている等のミスを事前にPydanticが検知し、安全に実行できます。

**設定ファイルの例 (`dams.yaml`):**
```yaml
sites:
  miyagase:
    name: "宮ヶ瀬ダム"
    dam:
      name: "宮ヶ瀬ダム"
      type: "dam"
      db_table_name: "dam_data"
      id: "1368030799020"    # URLのIDパラメータ
      capacity_m3: 183000000 # 有効貯水容量 (m³)
      url_kind: "3"
      url_page: "0"
    rain:                    # 雨量観測所（省略可。DATに内包される場合は不要）
      name: "宮ヶ瀬及沢"
      type: "rain"
      db_table_name: "rain_data"
      id: "103071283319020"
      url_kind: "9"
```

## 3. データ取得・蓄積のアーキテクチャ

* **データソースへのアクセス制限回避**: 
  * 国土交通省などのサイトはbotアクセスの制限がかかっている場合があるため、適切な `User-Agent` ヘッダーを付与してリクエストを行います。
* **生データの安定取得**:
  * 不安定なHTMLのページ上の表（Table）を直接パースするのではなく、ページ背後で提供されている **DATファイル（CSV互換）** をダウンロードしてPandas経由でパースすることで、堅牢なデータ取得を実現しています。
* **生データ保存ポリシー**:
  * DBには **DATファイルの主要列を意味あるカラム名で保存** し、加工済みの列（`volume_m3` 等）は一切持たない方針としています。
  * 貯水率・流入量・放流量などの変換処理は、グラフ描画時（`plot.py`）にオンザフライで実行します。
  * これにより、将来新たな指標を活用したくなった場合にも再取得が不要となります。
* **Supabase DBへの差分UPSERT**:
  * 取得元のシステムは過去1週間分などの表示制限があるため、取得した新しいデータはSupabase DBへUPSERTされます。
  * `station_id` + `timestamp` を主キーとし、重複を排除して新データを優先して上書きする設計としています。
  * 500件ずつバッチUPSERTを行い、APIのサイズ制限に対応しています。
  * SELECTでは1000件のデフォルト上限に対応するため、ページネーションで全件取得を行います。
* **ETL の制御 (`converter.py`)**:
  * Extract→Transform→Load の一連フローと**スロットリングガード**（後述）を `converter.py` の `refresh_data()` に集約しています。
  * バッチ実行 (`pipeline.py`) と CLI (`main.py`) の両エントリーポイントから呼び出すことで、ロジックの重複を排除しています。

## 4. Web UI の設計方針

### 採用技術: Streamlit + Streamlit Community Cloud
フェーズ3のWebアプリケーション化には **Streamlit** を採用し、`src/app.py` に実装しています。
現在、宮ヶ瀬ダム・矢木沢ダムに対応しており、プルダウン(SelectBox)でダムを切り替えられます。

**`app.py` は Supabase DB からの読み込みと表示に専念**しており、スクレイピングは行いません。
データ収集は `src/pipeline.py` が担当し、GitHub Actions の Cron（20分おき）によって自動実行されます。

**スロットリングガード (`converter.py`):**
`pipeline.py` や `main.py` から呼ばれる `refresh_data()` に実装されています。DB の最新タイムスタンプを確認し、**前回取得から20分以内の場合はスクレイピングをスキップ**します。

**選定理由:**
* **圧倒的に手っ取り早い**: Pythonのみで完結し、HTML/CSS/JavaScriptといったフロントエンドの知識が不要なため、MVP（最小限の実装）を最速で構築できる。
* `matplotlib` グラフを `st.pyplot(fig)` に置き換えるだけでWebアプリへ移行可能。
* **Streamlit Community Cloud** により、GitHubリポジトリ連携だけで無料デプロイ可能（GitHubアカウントのみで利用可、別途申請不要）。
* ダム選択やデータ期間指定等のインタラクティブUIも、Streamlitのウィジェット (`st.selectbox`, `st.date_input` 等) で簡潔に実装可能。

**今後の展望 (アクセス数増大時などの移行候補):**
現在は開発スピード・立ち上げの「手っ取り早さ」を優先してStreamlitを採用していますが、将来的にアクセス数が大幅に増大した場合や、より柔軟・リッチなUIが必要になった場合は、以下の構成への移行も視野に入れています（これらの案は将来構想として残しておきます）。
* **案2 (FastAPI + Vercel/Next.js 等)**: バックエンド(API)とフロントエンドを分離し、スケーラビリティとUIの自由度を高める構成。
* **案3 (Node.js フルスタック / Hono 等)**: TypeScript等で統一し、VercelやCloudflare Pages/Workersなどの強力なエッジ・無料枠を活用する構成。

## 5. 開発ワークフローとCI/CD

品質を担保するため、本プロジェクトでは**プルリクエスト駆動開発 (PR Workflow)** と自動化されたCIを利用します。

### 5.1 Branch Protection (masterの保護)
- `master` ブランチへの直接のプッシュ (`git push origin master`) は禁止されています。
- 全ての変更は作業ブランチ（例: `feature/xxx`, `fix/yyy`）からプルリクエスト (PR) を経由してマージする必要があります。
- マージには、GitHub Actions によるステータスチェック（Lint および Test）のパスが必須です。

### 5.2 CI (継続的インテグレーション)
GitHub Actions により、PR作成時およびPush時に以下のチェックが自動で実行されます。
- **Ruff**: 高速な Linter & Formatter。コーディング規約違反や未使用インポートを検知します。
- **pytest**: 単体テスト・E2Eテストを実行し、デグレ（機能退行）を防ぎます。特にグラフの日本語フォント（豆腐問題）などの環境依存エラーもここで捕捉します。

### 5.3 開発手順
1. `git checkout -b feature/your-feature-name` でブランチを作成
2. 開発を行い、ローカルでテスト (`ruff check .`, `pytest`)
3. コミット・プッシュし、GitHub 上で `master` 宛の PR を作成
4. CI の全パスを確認後、マージを実行

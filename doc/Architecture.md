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

選定理由・代替案・トレードオフの詳細は [ADR-001](#adr-001-フロントエンドフレームワークとして-streamlit-を採用) を参照。

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

---

## 6. アーキテクチャ上の意思決定記録 (ADR)

主要な設計判断を記録し、「なぜそうしたか」を残す。

---

### ADR-001: フロントエンドフレームワークとして Streamlit を採用

**状況**
MVP を最速で構築・公開する必要があった。データ取得・加工・グラフ描画はすでに Python で実装済みであり、それをそのまま活かせるフロントエンド手段を選定する必要があった。

**決定**
Streamlit を採用し、`src/app.py` として実装。Streamlit Community Cloud で無料デプロイ。

**理由**
- Python のみで完結し、HTML/CSS/JavaScript の知識が不要。MVP を最速で構築できる。
- `matplotlib` グラフを `st.pyplot(fig)` に置き換えるだけで Web UI へ移行可能。
- `st.selectbox` や `st.radio` 等のウィジェットでインタラクティブ UI を数行で実装できる。
- GitHub リポジトリ連携のみで無料デプロイ可能（別途申請不要）。

**検討した代替案**
- **FastAPI + Vercel/Next.js**: バックエンド/フロントエンド分離でスケーラブルだが、フロントエンドの学習コストが高い。
- **Node.js フルスタック（Hono 等）**: TypeScript で統一しエッジ環境で動作可能だが、Python 資産の書き直しコストが大きい。

**結果・トレードオフ**
- UI デザインの自由度はやや低い。
- アクセス数が大幅増大した場合や、リッチな UI が必要になった場合は FastAPI+Next.js または Node.js フルスタックへの移行を検討する。

---

### ADR-002: データ収集（ETL）と表示（UI）の分離 — `pipeline.py` と `app.py`

**状況**
当初の設計では `app.py`（Streamlit）がページアクセス時にスクレイピングを実行し、10分ガード付きでデータを取得・DBに保存する仕組みだった。

**問題**
1. **ガードが機能しない**: `st.session_state` ベースの10分ガードがリロードのたびにリセットされ、スロットリングが効かなかった。
2. **ページロードが遅い**: スクレイピング（HTTP取得・Transform・UPSERT）がページロードをブロックし、UX が悪化した。
3. **責務の混同**: UI レイヤーがデータ収集の副作用を持つことでテストが困難になった。

**決定**
- `src/app.py` は **Supabase DB からの読み込みと表示に専念**し、スクレイピング処理を完全に除去する。
- `src/pipeline.py` を独立したバッチスクリプトとして新設し、GitHub Actions Cron（20分おき）から自動実行する。
- スロットリングガードは `src/converter.py` の `refresh_data()` に実装し、`pipeline.py` と `main.py` の両エントリーポイントから呼び出す。

**理由**
- ページロード速度の大幅改善（スクレイピング待ちがなくなる）。
- UI / ETL の責務を分離することで、それぞれ独立してテスト可能になる（`test_app.py` / `test_pipeline.py`）。
- スロットリングをサーバーサイド（DBの最新タイムスタンプ比較）で制御することで、どのエントリーポイントからでも正確に機能する。

**結果・トレードオフ**
- GitHub Actions の Cron が停止すると（`SUPABASE_URL` / `SUPABASE_KEY` の Secrets 未設定など）、Web UI に表示されるデータが古くなる。Secrets の設定が正常稼働の前提条件となる。
- ローカル実行時（`main.py`）は引き続き `refresh_data()` を呼ぶためオンデマンドでデータ取得できる。

# WaterLevelMonitor — Claude 引き継ぎ資料

## プロジェクト概要
国土交通省「川の防災情報」からダム・観測所の水位データを取得し、時系列グラフで可視化する Streamlit Webアプリ。
データは Supabase (PostgreSQL) に蓄積し、取得元サイトの「過去1週間」制限を補う。

詳細: [doc/Spec.md](doc/Spec.md) / [doc/Architecture.md](doc/Architecture.md) / [doc/Diagram.md](doc/Diagram.md)

---

## アーキテクチャの核心

ETL を明確に分離している。

| 層 | ファイル | 責務 |
|---|---|---|
| Extract | `src/scraper.py` | DATファイルを HTTP 取得し、**未加工のまま** DataFrame で返す |
| Transform | `src/converter.py` | JST→UTC変換、カラムマッピング、`$`/`-` 処理、差分抽出・スロットリングガード |
| Load | `src/storage.py` | 整形済みデータを Supabase へ UPSERT / ページネーション取得 |

- `src/pipeline.py` — データ収集バッチ。GitHub Actions Cron（20分おき）から実行される
- `src/main.py` — CLI エントリーポイント。スクレイピング＋グラフ PNG 出力
- `src/app.py` — Supabase DB 読み込み・表示専念（スクレイピングなし）
- ダム設定は `dams.yaml` で管理（Pydantic 型検証）→ スキーマ: [doc/dams_schema.json](doc/dams_schema.json)

---

## 開発ルール

- `master` への直接 push は**禁止**。必ず `feature/xxx` ブランチ → PR → CI パス → マージ
- コミット前に `ruff check .` と `pytest` を実行（pre-commit でも自動実行）
- インポートは**絶対インポート** `from src.xxx` を使用（相対インポート不可・Streamlit Cloud 対応のため）

詳細: [doc/Architecture.md#5-開発ワークフローとcicd](doc/Architecture.md)

---

## テスト方針の要点

- `scraper.py`, `converter.py`, `plot.py` → 単体テスト対象
- `storage.py`, `app.py`, `main.py` → 単体テスト対象外（E2E でカバー）
- CI では `-m "not remote_db"` で実DB接続テストを除外

詳細: [tests/TestStrategy.md](tests/TestStrategy.md)

---

## 実装上の注意点（落とし穴）

- **タイムゾーン**: DB保存は UTC、グラフ表示直前に JST 変換
- **`24:00` 問題**: `converter.py` で翌日 `00:00` に繰り上げ処理あり
- **雨量集約**: 10分生データ → `resample('1h')` で1時間積算に変換して棒グラフ表示
- **GitHub Actions Secrets 必須**: `SUPABASE_URL`, `SUPABASE_KEY`（未設定だと cron が失敗）

---

## タスク・進捗管理

[doc/Task.md](doc/Task.md)

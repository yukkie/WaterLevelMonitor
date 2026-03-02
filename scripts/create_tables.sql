-- Supabase SQL Editor で実行するテーブル作成スクリプト
-- Supabase ダッシュボード → SQL Editor → New Query で実行してください

-- ダムデータテーブル
CREATE TABLE IF NOT EXISTS dam_data (
  station_id   TEXT NOT NULL,
  timestamp    TIMESTAMPTZ NOT NULL,
  rainfall     REAL,
  volume       REAL,
  inflow       REAL,
  outflow      REAL,
  storage_rate REAL,
  PRIMARY KEY (station_id, timestamp)
);

-- 雨量データテーブル
CREATE TABLE IF NOT EXISTS rain_data (
  station_id   TEXT NOT NULL,
  timestamp    TIMESTAMPTZ NOT NULL,
  rainfall     REAL,
  PRIMARY KEY (station_id, timestamp)
);

-- インデックス（時系列クエリの高速化）
CREATE INDEX IF NOT EXISTS idx_dam_data_station_time ON dam_data (station_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_rain_data_station_time ON rain_data (station_id, timestamp);

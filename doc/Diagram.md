# WaterLevelMonitor モジュール構成図

```mermaid
graph TD
    YAML["dams.yaml"]
    DB["Supabase DB"]
    WEB["川の防災情報サイト"]
    GRAPH["グラフ出力"]
    CRON["GitHub Actions Cron\n(20分おき)"]

    subgraph src
        CONFIG["config.py"]
        SCRAPER["scraper.py"]
        STORAGE["storage.py"]
        CONVERTER["converter.py"]
        PLOT["plot.py"]
        PIPELINE["pipeline.py"]
        MAIN["main.py"]
        APP["app.py"]
    end

    YAML -- "YAML読み込み" --> CONFIG
    CONFIG -- "StationConfig" --> PIPELINE
    CONFIG -- "StationConfig" --> MAIN
    CONFIG -- "StationConfig" --> APP

    CRON -- "定期実行" --> PIPELINE
    PIPELINE -- "refresh_data()" --> CONVERTER
    MAIN -- "refresh_data()" --> CONVERTER

    WEB -- "HTTP GET" --> SCRAPER
    SCRAPER -- "DataFrame（生データ）" --> CONVERTER
    CONVERTER -- "UPSERT" --> STORAGE
    STORAGE -- "DB読み書き" --> DB

    STORAGE -- "load_data()" --> MAIN
    STORAGE -- "load_data()" --> APP

    MAIN -- "StationConfig + DataFrame" --> PLOT
    APP -- "StationConfig + DataFrame" --> PLOT
    PLOT -- "matplotlib Figure" --> GRAPH

    style CONVERTER fill:#e8f5e9,stroke:#388e3c
    style PIPELINE fill:#f3e5f5,stroke:#6a1b9a
    style APP fill:#e3f2fd,stroke:#1565c0
    style MAIN fill:#fff3e0,stroke:#ef6c00
    style DB fill:#fce4ec,stroke:#c62828
```

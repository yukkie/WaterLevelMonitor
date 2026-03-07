import os

import yaml
from pydantic import BaseModel


class StationConfig(BaseModel):
    name: str
    id: str
    type: str = "dam"
    db_table_name: str = "dam_data"
    capacity_m3: int | None = None
    url_kind: str
    url_page: str | None = "0"


class SiteConfig(BaseModel):
    name: str
    dam: StationConfig
    rain: StationConfig | None = None


class AppConfig(BaseModel):
    sites: dict[str, SiteConfig]


def load_config(config_path="dams.yaml") -> AppConfig:
    """
    指定されたパスからYAML設定ファイルを読み込み、AppConfigオブジェクトとして返す。
    デフォルトはカレントディレクトリのdams.yamlを探す。
    """
    if not os.path.exists(config_path):
        # src直下から実行された場合などに備えて親ディレクトリも探す
        parent_path = os.path.join("..", config_path)
        if os.path.exists(parent_path):
            config_path = parent_path

    with open(config_path, encoding="utf-8") as f:
        raw_data = yaml.safe_load(f)
    return AppConfig(**raw_data)

import yaml
from pydantic import BaseModel
from typing import Dict, Optional
import os

class DamConfig(BaseModel):
    name: str
    id: str
    type: str = "water"
    capacity_m3: Optional[int] = None
    url_kind: str
    url_page: Optional[str] = "0"

class AppConfig(BaseModel):
    dams: Dict[str, DamConfig]

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
            
    with open(config_path, "r", encoding="utf-8") as f:
        raw_data = yaml.safe_load(f)
    return AppConfig(**raw_data)

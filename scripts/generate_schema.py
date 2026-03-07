import json
import os
import sys

# srcディレクトリをパスに追加してconfigをインポート可能にする
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.config import AppConfig


def generate_schema():
    # PydanticモデルからJSON Schemaを生成 (Pydantic v2)
    schema = AppConfig.model_json_schema()

    # 保存先パス
    output_path = os.path.join(
        os.path.dirname(__file__), "..", "doc", "dams_schema.json"
    )

    # docディレクトリがない場合は作成
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2, ensure_ascii=False)

    print(f"Schema generated successfully at {output_path}")


if __name__ == "__main__":
    generate_schema()

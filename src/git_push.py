import requests
import base64
import os

def _get_github_config():
    """
    GitHub設定を取得する。Streamlit Secrets または環境変数から読み込む。
    設定がない場合は None を返す（ローカル開発時はスキップ）。
    """
    token = None
    repo = None

    # Streamlit Secrets から取得を試みる
    try:
        import streamlit as st
        token = st.secrets.get("GITHUB_TOKEN")
        repo = st.secrets.get("GITHUB_REPO")
    except Exception:
        pass

    # 環境変数からのフォールバック
    if not token:
        token = os.environ.get("GITHUB_TOKEN")
    if not repo:
        repo = os.environ.get("GITHUB_REPO")

    if token and repo:
        return {"token": token, "repo": repo}
    return None


def commit_and_push(file_paths, message="Update data files"):
    """
    指定されたローカルファイルを GitHub リポジトリへ commit & push する。
    GitHub REST API (Contents API) を使用。

    Args:
        file_paths: コミットするファイルの絶対パスリスト
        message: コミットメッセージ

    Returns:
        True: 成功, False: スキップまたは失敗
    """
    config = _get_github_config()
    if not config:
        print("[git_push] GitHub設定が見つかりません。コミットをスキップします。")
        return False

    token = config["token"]
    repo = config["repo"]
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    api_base = f"https://api.github.com/repos/{repo}/contents"

    success_count = 0
    for file_path in file_paths:
        try:
            # ファイルのリポジトリ内相対パスを算出
            # プロジェクトルート = file_pathからdata/xxx.csvのような相対パスを得る
            repo_path = _to_repo_path(file_path)
            if not repo_path:
                print(f"[git_push] リポジトリパスを解決できません: {file_path}")
                continue

            # ファイル内容をBase64エンコード
            with open(file_path, "rb") as f:
                content_b64 = base64.b64encode(f.read()).decode("utf-8")

            # 既存ファイルのSHAを取得（更新時に必要）
            url = f"{api_base}/{repo_path}"
            get_resp = requests.get(url, headers=headers)

            payload = {
                "message": message,
                "content": content_b64,
            }
            if get_resp.status_code == 200:
                # 既存ファイルの更新 → SHA必須
                payload["sha"] = get_resp.json()["sha"]

            put_resp = requests.put(url, headers=headers, json=payload)
            if put_resp.status_code in (200, 201):
                print(f"[git_push] コミット成功: {repo_path}")
                success_count += 1
            else:
                print(f"[git_push] コミット失敗: {repo_path} ({put_resp.status_code}: {put_resp.text[:200]})")

        except Exception as e:
            print(f"[git_push] エラー ({file_path}): {e}")

    return success_count > 0


def _to_repo_path(file_path):
    """
    絶対パスからリポジトリ内の相対パスを推定する。
    data/ ディレクトリ配下のファイルを想定。
    """
    file_path = os.path.normpath(file_path)
    parts = file_path.replace("\\", "/").split("/")

    # "data" ディレクトリを見つけて、そこからの相対パスを返す
    for i, part in enumerate(parts):
        if part == "data":
            return "/".join(parts[i:])
    return None

from __future__ import annotations

import json
import platform
from pathlib import Path
from typing import Any


def get_config_path() -> Path:
    """設定ファイルの保存先を返す。"""
    return Path.home() / ".anju" / "config.json"


def get_default_base_dir() -> Path:
    """OSごとの標準保存先を返す。"""
    if platform.system() == "Windows":
        return Path(r"D:\Movies\anju")

    return Path.home() / "Movies" / "anju"


def create_default_config() -> dict[str, str]:
    """初期設定を作成する。"""
    return {
        "base_dir": str(get_default_base_dir()),
        "twitch_downloader_cli": "",
    }


def load_config() -> dict[str, Any]:
    """設定ファイルを読み込む。存在しなければ自動作成する。"""
    config_path = get_config_path()

    if not config_path.exists():
        config_path.parent.mkdir(parents=True, exist_ok=True)

        config = create_default_config()

        config_path.write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return config

    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise RuntimeError(
            f"設定ファイルを読み込めませんでした: {config_path}"
        ) from error
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"設定ファイルのJSON形式が不正です: {config_path}"
        ) from error

    if not isinstance(config, dict):
        raise RuntimeError(f"設定ファイルの内容が不正です: {config_path}")

    return config

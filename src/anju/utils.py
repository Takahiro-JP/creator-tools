from __future__ import annotations

import platform
import re
import subprocess
from pathlib import Path


def sanitize_filename(value: str) -> str:
    """WindowsとmacOSで使いにくい文字を置換する。"""
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", value)
    value = re.sub(r"\s+", " ", value)
    value = value.strip().rstrip(".")

    return value or "Untitled"


def format_upload_date(value: object) -> str:
    """20260622を2026-06-22へ変換する。"""
    text = str(value or "")

    if re.fullmatch(r"\d{8}", text):
        return f"{text[0:4]}-{text[4:6]}-{text[6:8]}"

    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d")


def open_folder(path: Path) -> None:
    """OS標準のファイル管理アプリでフォルダを開く。"""
    system = platform.system()

    try:
        if system == "Windows":
            subprocess.Popen(["explorer.exe", str(path)])
        elif system == "Darwin":
            subprocess.Popen(["open", str(path)])
        else:
            subprocess.Popen(["xdg-open", str(path)])
    except OSError:
        print(f"フォルダを自動で開けませんでした: {path}")

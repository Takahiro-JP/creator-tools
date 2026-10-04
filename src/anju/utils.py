from __future__ import annotations

import platform
import re
import subprocess
import unicodedata
from pathlib import Path


def sanitize_filename(value: str) -> str:
    """
    Windows / macOS / DaVinci Resolveで扱いやすい
    ファイル名へ変換する。

    日本語は維持しつつ、
    ファイル名に使用できない文字や絵文字を除去する。
    """

    # Unicode表現をNFCへ統一する。
    #
    # macOSでは同じ日本語でもUnicodeの表現方法が
    # 異なる場合があるため、ファイル名生成時に統一する。
    value = unicodedata.normalize("NFC", value)

    # Windows / macOSでファイル名として
    # 問題になりやすい文字を "_" に置換する。
    value = re.sub(
        r'[<>:"/\\|?*\x00-\x1f]',
        "_",
        value,
    )

    # DaVinci Resolveでファイル読み込み時に
    # 問題になる可能性がある絵文字を除去する。
    value = "".join(char for char in value if not _is_emoji(char))

    # 連続する空白を1個にまとめる。
    value = re.sub(r"\s+", " ", value)

    # 前後の空白と末尾の "." を除去する。
    value = value.strip().rstrip(".")

    return value or "Untitled"


def _is_emoji(char: str) -> bool:
    """絵文字として使われるUnicode文字か判定する。"""
    codepoint = ord(char)

    return (
        # Miscellaneous Symbols and Pictographs
        0x1F300 <= codepoint <= 0x1F5FF
        # Emoticons
        or 0x1F600 <= codepoint <= 0x1F64F
        # Transport and Map Symbols
        or 0x1F680 <= codepoint <= 0x1F6FF
        # Supplemental Symbols and Pictographs
        or 0x1F900 <= codepoint <= 0x1F9FF
        # Symbols and Pictographs Extended-A
        or 0x1FA70 <= codepoint <= 0x1FAFF
        # Miscellaneous Symbols
        or 0x2600 <= codepoint <= 0x26FF
        # Dingbats
        or 0x2700 <= codepoint <= 0x27BF
        # Variation Selectors
        or 0xFE00 <= codepoint <= 0xFE0F
        # Emoji skin tone modifiers
        or 0x1F3FB <= codepoint <= 0x1F3FF
    )


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

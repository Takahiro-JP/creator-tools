from __future__ import annotations

import platform
import shutil
import sys

from rich.console import Console

console = Console()


def command_exists(command: str) -> bool:
    """指定したコマンドが利用可能か確認する。"""
    return shutil.which(command) is not None


def run_doctor() -> None:
    """必要なツールと実行環境を表示する。"""
    console.print("[bold cyan]anju environment check[/bold cyan]")
    console.print("----------------------")

    commands = (
        ("yt-dlp", "yt-dlp"),
        ("ffmpeg", "ffmpeg"),
        ("TwitchDownloaderCLI", "TwitchDownloaderCLI"),
    )

    for command, display_name in commands:
        exists = command_exists(command)
        status = "OK" if exists else "NG"
        color = "green" if exists else "red"

        console.print(f"[{color}][{status}][/{color}] {display_name}")

    console.print(f"[blue][INFO][/blue] OS: {platform.system()}")
    console.print(f"[blue][INFO][/blue] Python: {sys.version.split()[0]}")

from __future__ import annotations

import platform
import shutil
import sys
from pathlib import Path

from rich.console import Console

from anju.config import (
    get_config_path,
    get_default_base_dir,
    load_config,
)
from anju.downloader import find_twitch_downloader

console = Console()


def command_exists(command: str) -> bool:
    """指定したコマンドが利用可能か確認する。"""
    return shutil.which(command) is not None


def print_status(
    name: str,
    available: bool,
) -> None:
    """OKまたはNGを表示する。"""
    status = "OK" if available else "NG"
    color = "green" if available else "red"

    console.print(
        f"[{color}][{status}][/{color}] {name}"
    )


def run_doctor() -> None:
    """必要なツール、設定、実行環境を表示する。"""
    config = load_config()
    cli_path = find_twitch_downloader(config)

    console.print(
        "[bold cyan]anju environment check[/bold cyan]"
    )
    console.print("----------------------")

    print_status(
        "yt-dlp",
        command_exists("yt-dlp"),
    )
    print_status(
        "ffmpeg",
        command_exists("ffmpeg"),
    )
    print_status(
        "TwitchDownloaderCLI",
        cli_path is not None,
    )

    if cli_path:
        console.print(
            f"[blue][INFO][/blue] "
            f"TwitchDownloaderCLI: {cli_path}"
        )

    base_dir = Path(
        str(
            config.get("base_dir")
            or get_default_base_dir()
        )
    ).expanduser()

    console.print(
        f"[blue][INFO][/blue] 保存先: {base_dir}"
    )
    console.print(
        f"[blue][INFO][/blue] "
        f"設定ファイル: {get_config_path()}"
    )
    console.print(
        f"[blue][INFO][/blue] OS: {platform.system()}"
    )
    console.print(
        f"[blue][INFO][/blue] "
        f"Python: {sys.version.split()[0]}"
    )

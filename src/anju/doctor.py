from __future__ import annotations

import platform
import shutil
import sys

import typer
from rich.console import Console

console = Console()


def _exists(command: str) -> bool:
    return shutil.which(command) is not None


def doctor() -> None:
    """開発環境を確認します。"""

    console.print("[bold cyan]anju environment check[/bold cyan]")
    console.print("----------------------")

    console.print(
        f"[{'green' if _exists('python3') else 'red'}]"
        f"{'OK' if _exists('python3') else 'NG'}[/] Python"
    )

    console.print(
        f"[{'green' if _exists('yt-dlp') else 'red'}]"
        f"{'OK' if _exists('yt-dlp') else 'NG'}[/] yt-dlp"
    )

    console.print(
        f"[{'green' if _exists('ffmpeg') else 'red'}]"
        f"{'OK' if _exists('ffmpeg') else 'NG'}[/] ffmpeg"
    )

    console.print(
        f"[{'green' if _exists('TwitchDownloaderCLI') else 'red'}]"
        f"{'OK' if _exists('TwitchDownloaderCLI') else 'NG'}[/] TwitchDownloaderCLI"
    )

    console.print(f"[blue]INFO[/] OS: {platform.system()}")
    console.print(f"[blue]INFO[/] Python: {sys.version.split()[0]}")

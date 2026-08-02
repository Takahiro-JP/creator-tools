from __future__ import annotations

import typer

from anju.commands.common import execute_command
from anju.downloader import download_video


def register(app: typer.Typer) -> None:
    """downloadコマンドを登録する。"""

    @app.command(name="download")
    def download_command(
        url: str = typer.Argument(
            ...,
            help="Twitch VOD URL",
        ),
    ) -> None:
        """Twitch VODをダウンロードします。"""
        execute_command(download_video, url)

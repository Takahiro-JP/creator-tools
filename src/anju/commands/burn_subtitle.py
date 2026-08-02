from __future__ import annotations

from pathlib import Path

import typer

from anju.commands.common import execute_command
from anju.subtitle_burner import burn_project_subtitles


def register(app: typer.Typer) -> None:
    """burn-subtitleコマンドを登録する。"""

    @app.command(name="burn-subtitle")
    def burn_subtitle_command(
        project_dir: Path = typer.Argument(
            ...,
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="字幕を焼き込むプロジェクトフォルダ",
        ),
        limit: int | None = typer.Option(
            None,
            "--limit",
            min=1,
            help="処理する動画の最大数",
        ),
        overwrite: bool = typer.Option(
            False,
            "--overwrite",
            help="既存の字幕焼き込み済み動画を上書きする",
        ),
        font_name: str = typer.Option(
            "Noto Sans CJK JP",
            "--font-name",
            help="字幕フォント名",
        ),
        font_size: int = typer.Option(
            28,
            "--font-size",
            min=1,
            help="字幕フォントサイズ",
        ),
        margin_v: int = typer.Option(
            40,
            "--margin-v",
            min=0,
            help="字幕下余白",
        ),
    ) -> None:
        """クリップ動画へSRT字幕を焼き込みます。"""
        execute_command(
            burn_project_subtitles,
            project_dir,
            limit=limit,
            overwrite=overwrite,
            font_name=font_name,
            font_size=font_size,
            margin_v=margin_v,
        )

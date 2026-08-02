from __future__ import annotations

from pathlib import Path

import typer

from anju.commands.common import execute_command
from anju.subtitle import generate_clip_subtitles


def register(app: typer.Typer) -> None:
    """subtitleコマンドを登録する。"""

    @app.command(name="subtitle")
    def subtitle_command(
        project_dir: Path = typer.Argument(
            ...,
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="字幕を生成するプロジェクトフォルダ",
        ),
        limit: int | None = typer.Option(
            None,
            "--limit",
            min=1,
            help="字幕を生成するクリップの最大数",
        ),
        overwrite: bool = typer.Option(
            False,
            "--overwrite",
            help="既存の字幕を上書きする",
        ),
    ) -> None:
        """各クリップに対応するSRT字幕を生成します。"""
        execute_command(
            generate_clip_subtitles,
            project_dir,
            limit=limit,
            overwrite=overwrite,
        )

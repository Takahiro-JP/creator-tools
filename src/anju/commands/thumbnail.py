from __future__ import annotations

from pathlib import Path

import typer

from anju.commands.common import execute_command
from anju.thumbnail import generate_thumbnail_ideas


def register(app: typer.Typer) -> None:
    """thumbnailコマンドを登録する。"""

    @app.command(name="thumbnail")
    def thumbnail_command(
        project_dir: Path = typer.Argument(
            ...,
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="サムネイル案を生成するプロジェクトフォルダ",
        ),
        model: str = typer.Option(
            "gemini-2.5-flash",
            "--model",
            "-m",
            help="使用するGeminiモデル",
        ),
        overwrite: bool = typer.Option(
            False,
            "--overwrite",
            help="既存のサムネイル案を上書きする",
        ),
    ) -> None:
        """見どころからサムネイル設計案を生成します。"""
        execute_command(
            generate_thumbnail_ideas,
            project_dir,
            model_name=model,
            overwrite=overwrite,
        )

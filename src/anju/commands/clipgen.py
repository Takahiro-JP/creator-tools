from __future__ import annotations

from pathlib import Path

import typer

from anju.clipgen import generate_project_clips
from anju.commands.common import execute_command


def register(app: typer.Typer) -> None:
    """clipgenコマンドを登録する。"""

    @app.command(name="clipgen")
    def clipgen_command(
        project_dir: Path = typer.Argument(
            ...,
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="切り抜きを生成するプロジェクトフォルダ",
        ),
        limit: int | None = typer.Option(
            None,
            "--limit",
            min=1,
            help="生成する切り抜きの最大数",
        ),
        overwrite: bool = typer.Option(
            False,
            "--overwrite",
            help="既存の動画を上書きする",
        ),
    ) -> None:
        """見どころ候補から切り抜き動画を生成します。"""
        execute_command(
            generate_project_clips,
            project_dir,
            limit=limit,
            overwrite=overwrite,
        )

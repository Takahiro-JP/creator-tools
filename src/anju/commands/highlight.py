from __future__ import annotations

from pathlib import Path

import typer

from anju.commands.common import execute_command
from anju.highlighter import highlight_project


def register(app: typer.Typer) -> None:
    """highlightコマンドを登録する。"""

    @app.command(name="highlight")
    def highlight_command(
        project_dir: Path = typer.Argument(
            ...,
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="見どころ抽出対象のプロジェクトフォルダ",
        ),
        model: str = typer.Option(
            "gemini-2.5-flash",
            "--model",
            "-m",
            help="使用するGeminiモデル",
        ),
        max_highlights: int = typer.Option(
            10,
            "--max",
            min=1,
            max=50,
            help="生成する見どころ候補の最大数",
        ),
        overwrite: bool = typer.Option(
            False,
            "--overwrite",
            help="既存の結果を上書きする",
        ),
        append: bool = typer.Option(
            False,
            "--append",
            help="既存の結果に新しい見どころ候補を追加する",
        ),
        chunk_minutes: int = typer.Option(
            120,
            "--chunk-minutes",
            min=1,
            max=240,
            help="1回に解析する字幕の時間（分）",
        ),
    ) -> None:
        """字幕から見どころ候補を抽出します。"""

        execute_command(
            highlight_project,
            project_dir,
            model_name=model,
            max_highlights=max_highlights,
            overwrite=overwrite,
            append=append,
            chunk_minutes=chunk_minutes,
        )

from __future__ import annotations

from pathlib import Path

import typer

from anju.commands.common import execute_command
from anju.transcriber import transcribe_project


def register(app: typer.Typer) -> None:
    """transcribeコマンドを登録する。"""

    @app.command(name="transcribe")
    def transcribe_command(
        project_dir: Path = typer.Argument(
            ...,
            exists=True,
            file_okay=False,
            dir_okay=True,
            readable=True,
            resolve_path=True,
            help="文字起こし対象のプロジェクトフォルダ",
        ),
        model: str = typer.Option(
            "small",
            "--model",
            "-m",
            help="Whisperモデル名",
        ),
        language: str = typer.Option(
            "ja",
            "--language",
            "-l",
            help="音声言語",
        ),
    ) -> None:
        """プロジェクト内の動画を文字起こしします。"""
        execute_command(
            transcribe_project,
            project_dir,
            model_size=model,
            language=language,
        )

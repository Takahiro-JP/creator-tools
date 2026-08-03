from __future__ import annotations

import typer

from anju.commands.common import execute_command
from anju.pipeline import run_pipeline


def register(app: typer.Typer) -> None:
    """pipelineコマンドを登録する。"""

    @app.command(name="pipeline")
    def pipeline_command(
        url: str = typer.Argument(
            ...,
            help="Twitch VOD URL",
        ),
        whisper_model: str = typer.Option(
            "small",
            "--whisper-model",
            help="使用するWhisperモデル",
        ),
        gemini_model: str = typer.Option(
            "gemini-2.5-flash",
            "--gemini-model",
            help="使用するGeminiモデル",
        ),
        language: str = typer.Option(
            "ja",
            "--language",
            "-l",
            help="音声言語",
        ),
        max_highlights: int = typer.Option(
            10,
            "--max-highlights",
            min=1,
            max=30,
            help="見どころ候補の最大数",
        ),
        clip_limit: int | None = typer.Option(
            None,
            "--clip-limit",
            min=1,
            help="生成するクリップの最大数",
        ),
        overwrite: bool = typer.Option(
            False,
            "--overwrite",
            help="既存成果物を上書きする",
        ),
        skip_burn_subtitle: bool = typer.Option(
            False,
            "--skip-burn-subtitle",
            help="字幕焼き込みをスキップする",
        ),
    ) -> None:
        """動画処理ワークフローを一括実行します。"""
        execute_command(
            run_pipeline,
            url,
            whisper_model=whisper_model,
            gemini_model=gemini_model,
            language=language,
            max_highlights=max_highlights,
            clip_limit=clip_limit,
            overwrite=overwrite,
            skip_burn_subtitle=skip_burn_subtitle,
        )

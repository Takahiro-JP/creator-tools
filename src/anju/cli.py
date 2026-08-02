from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console

from anju.clipgen import generate_project_clips
from anju.config import get_config_path, load_config
from anju.doctor import run_doctor
from anju.downloader import download_video
from anju.highlighter import highlight_project
from anju.transcriber import transcribe_project

app = typer.Typer(
    name="anju",
    help="AI-powered CLI toolkit for content creators.",
    no_args_is_help=True,
)

console = Console()


@app.callback()
def main() -> None:
    """Creator Tools CLI."""


@app.command()
def hello() -> None:
    """CLIの動作確認を行います。"""
    console.print("[bold green]Hello, Creator Tools![/bold green]")


@app.command(name="doctor")
def doctor_command() -> None:
    """必要なツールと実行環境を確認します。"""
    run_doctor()


@app.command(name="config")
def config_command() -> None:
    """現在の設定を表示します。"""
    config = load_config()

    console.print(f"[blue]設定ファイル:[/blue] {get_config_path()}")
    console.print()
    console.print_json(
        json.dumps(
            config,
            ensure_ascii=False,
            indent=2,
        )
    )


@app.command(name="download")
def download_command(
    url: str = typer.Argument(
        ...,
        help="Twitch VOD URL",
    ),
) -> None:
    """Twitch VODをダウンロードします。"""
    try:
        download_video(url)
    except (RuntimeError, ValueError) as error:
        console.print(f"[bold red]エラー:[/bold red] {error}")
        raise typer.Exit(code=1) from error
    except KeyboardInterrupt:
        console.print()
        console.print("処理を中断しました。")
        raise typer.Exit(code=130) from None


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
    try:
        transcribe_project(
            project_dir,
            model_size=model,
            language=language,
        )
    except (RuntimeError, ValueError) as error:
        console.print(f"[bold red]エラー:[/bold red] {error}")
        raise typer.Exit(code=1) from error
    except KeyboardInterrupt:
        console.print()
        console.print("処理を中断しました。")
        raise typer.Exit(code=130) from None


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
        max=30,
        help="生成する見どころ候補の最大数",
    ),
    overwrite: bool = typer.Option(
        False,
        "--overwrite",
        help="既存の結果を上書きする",
    ),
) -> None:
    """字幕から見どころ候補を抽出します。"""
    try:
        highlight_project(
            project_dir,
            model_name=model,
            max_highlights=max_highlights,
            overwrite=overwrite,
        )
    except (RuntimeError, ValueError) as error:
        console.print(f"[bold red]エラー:[/bold red] {error}")
        raise typer.Exit(code=1) from error
    except KeyboardInterrupt:
        console.print()
        console.print("処理を中断しました。")
        raise typer.Exit(code=130) from None


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
    try:
        generate_project_clips(
            project_dir,
            limit=limit,
            overwrite=overwrite,
        )
    except (RuntimeError, ValueError) as error:
        console.print(f"[bold red]エラー:[/bold red] {error}")
        raise typer.Exit(code=1) from error
    except KeyboardInterrupt:
        console.print()
        console.print("処理を中断しました。")
        raise typer.Exit(code=130) from None


if __name__ == "__main__":
    app()

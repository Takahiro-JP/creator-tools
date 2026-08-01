from __future__ import annotations

import json

import typer
from rich.console import Console

from anju.config import get_config_path, load_config
from anju.doctor import run_doctor

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


if __name__ == "__main__":
    app()

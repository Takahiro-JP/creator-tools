from __future__ import annotations

import typer
from rich.console import Console

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


if __name__ == "__main__":
    app()

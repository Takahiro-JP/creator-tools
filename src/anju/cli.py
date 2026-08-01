from __future__ import annotations

import typer
from rich.console import Console

from anju.doctor import doctor

app = typer.Typer(
    help="AI-powered CLI toolkit for content creators.",
    no_args_is_help=True,
)

console = Console()


@app.callback()
def main() -> None:
    """Creator Tools CLI."""


@app.command()
def hello() -> None:
    """動作確認。"""
    console.print("[bold green]Hello Creator Tools![/bold green]")


@app.command()
def doctor_command() -> None:
    """環境をチェックします。"""
    doctor()


if __name__ == "__main__":
    app()

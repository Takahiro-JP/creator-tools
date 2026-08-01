from __future__ import annotations

import typer
from rich.console import Console

app = typer.Typer(
    name="anju",
    help="Twitch切り抜き制作用CLIツール",
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


if __name__ == "__main__":
    app()

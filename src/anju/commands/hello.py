from __future__ import annotations

import typer
from rich.console import Console

console = Console()


def register(app: typer.Typer) -> None:
    """helloコマンドを登録する。"""

    @app.command(name="hello")
    def hello_command() -> None:
        """CLIの動作確認を行います。"""
        console.print("[bold green]Hello, Creator Tools![/bold green]")

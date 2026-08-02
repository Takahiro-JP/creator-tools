from __future__ import annotations

import json

import typer
from rich.console import Console

from anju.config import get_config_path, load_config

console = Console()


def register(app: typer.Typer) -> None:
    """configコマンドを登録する。"""

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

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import typer
from rich.console import Console

console = Console()


def execute_command(
    command: Callable[..., Any],
    /,
    *args: Any,
    **kwargs: Any,
) -> None:
    """サービス関数を実行し、CLI向けのエラー表示を行う。"""
    try:
        command(*args, **kwargs)
    except (RuntimeError, ValueError) as error:
        console.print(f"[bold red]エラー:[/bold red] {error}")
        raise typer.Exit(code=1) from error
    except KeyboardInterrupt:
        console.print()
        console.print("処理を中断しました。")
        raise typer.Exit(code=130) from None

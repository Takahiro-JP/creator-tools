from __future__ import annotations

import typer

from anju.doctor import run_doctor


def register(app: typer.Typer) -> None:
    """doctorコマンドを登録する。"""

    @app.command(name="doctor")
    def doctor_command() -> None:
        """必要なツールと実行環境を確認します。"""
        run_doctor()

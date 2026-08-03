from __future__ import annotations

import typer

from anju.commands import (
    burn_subtitle,
    clipgen,
    config,
    doctor,
    download,
    hello,
    highlight,
    subtitle,
    thumbnail,
    transcribe,
)

app = typer.Typer(
    name="anju",
    help="AI-powered CLI toolkit for content creators.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Creator Tools CLI."""


hello.register(app)
doctor.register(app)
config.register(app)
download.register(app)
transcribe.register(app)
highlight.register(app)
clipgen.register(app)
subtitle.register(app)
burn_subtitle.register(app)
thumbnail.register(app)


if __name__ == "__main__":
    app()

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from anju.clipgen import generate_project_clips
from anju.downloader import download_video
from anju.highlighter import highlight_project
from anju.subtitle import generate_clip_subtitles
from anju.subtitle_burner import burn_project_subtitles
from anju.thumbnail import generate_thumbnail_ideas
from anju.transcriber import transcribe_project

console = Console()


@dataclass(frozen=True)
class PipelineReport:
    """一括処理の実行結果。"""

    project_dir: Path
    completed: tuple[str, ...]
    skipped: tuple[str, ...]
    elapsed_seconds: float


def _format_elapsed_time(seconds: float) -> str:
    """処理時間を読みやすい形式へ変換する。"""
    total_seconds = max(0, round(seconds))

    minutes, secs = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours:
        return f"{hours}h {minutes}m {secs}s"

    if minutes:
        return f"{minutes}m {secs}s"

    return f"{seconds:.1f}s"


def print_pipeline_summary(
    report: PipelineReport,
) -> None:
    """Pipelineの実行結果を見やすく表示する。"""
    stage_table = Table(
        show_header=True,
        header_style="bold cyan",
        box=None,
        padding=(0, 2),
    )
    stage_table.add_column("Status", width=10)
    stage_table.add_column("Stage")

    for stage in report.completed:
        stage_table.add_row(
            "[bold green]✓ Done[/bold green]",
            stage,
        )

    for stage in report.skipped:
        stage_table.add_row(
            "[bold yellow]↷ Skip[/bold yellow]",
            stage,
        )

    summary_table = Table(
        show_header=False,
        box=None,
        padding=(0, 2),
    )
    summary_table.add_column(
        "Label",
        style="bold blue",
        no_wrap=True,
    )
    summary_table.add_column("Value")

    summary_table.add_row(
        "Project",
        str(report.project_dir),
    )
    summary_table.add_row(
        "Completed",
        str(len(report.completed)),
    )
    summary_table.add_row(
        "Skipped",
        str(len(report.skipped)),
    )
    summary_table.add_row(
        "Processing Time",
        _format_elapsed_time(report.elapsed_seconds),
    )

    content = Table.grid(
        padding=(1, 0),
    )
    content.add_row(
        Text(
            "Creator Tools Pipeline Complete",
            style="bold green",
            justify="center",
        )
    )
    content.add_row(stage_table)
    content.add_row(summary_table)

    console.print()
    console.print(
        Panel(
            content,
            title="[bold green]🎉 Success[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )


def _run_stage(
    name: str,
    *,
    already_completed: bool,
    overwrite: bool,
    action: Callable[[], None],
    completed: list[str],
    skipped: list[str],
) -> None:
    """1つの処理を実行、または既存成果物があればスキップする。"""
    if already_completed and not overwrite:
        console.print(f"[yellow][SKIP][/yellow] {name}")
        skipped.append(name)
        return

    console.print()
    console.print(f"[bold cyan][RUN][/bold cyan] {name}")

    action()

    completed.append(name)
    console.print(f"[green][OK][/green] {name}")


def _transcription_exists(project_dir: Path) -> bool:
    subtitles_dir = project_dir / "subtitles"

    return (subtitles_dir / "full.srt").is_file() and (
        subtitles_dir / "full.txt"
    ).is_file()


def _highlight_exists(project_dir: Path) -> bool:
    clips_dir = project_dir / "clips"

    return (clips_dir / "highlights.json").is_file() and (
        clips_dir / "highlights.md"
    ).is_file()


def _clips_exist(project_dir: Path) -> bool:
    clips_dir = project_dir / "clips"

    return any(
        path.is_file()
        and path.suffix.lower() == ".mp4"
        and not path.stem.endswith("_subtitled")
        for path in clips_dir.glob("*.mp4")
    )


def _clip_subtitles_exist(project_dir: Path) -> bool:
    return any(path.is_file() for path in (project_dir / "clips").glob("*.srt"))


def _burned_clips_exist(project_dir: Path) -> bool:
    return any(
        path.is_file() for path in (project_dir / "clips").glob("*_subtitled.mp4")
    )


def _thumbnail_ideas_exist(project_dir: Path) -> bool:
    thumbnail_dir = project_dir / "thumbnail"

    return (thumbnail_dir / "ideas.json").is_file() and (
        thumbnail_dir / "ideas.md"
    ).is_file()


def _prepare_transcription_overwrite(
    project_dir: Path,
) -> None:
    """Whisperの既存出力を削除して再生成可能にする。"""
    subtitles_dir = project_dir / "subtitles"

    for filename in ("full.srt", "full.txt"):
        path = subtitles_dir / filename

        if path.exists():
            path.unlink()


def run_pipeline(
    url: str,
    *,
    whisper_model: str = "small",
    gemini_model: str = "gemini-2.5-flash",
    language: str = "ja",
    max_highlights: int = 10,
    clip_limit: int | None = None,
    overwrite: bool = False,
    skip_burn_subtitle: bool = False,
) -> PipelineReport:
    """Twitch VODから字幕付き切り抜きとサムネ案まで生成する。"""
    if max_highlights < 1:
        raise ValueError("max_highlightsは1以上にしてください。")

    if clip_limit is not None and clip_limit < 1:
        raise ValueError("clip_limitは1以上にしてください。")

    started_at = perf_counter()
    completed: list[str] = []
    skipped: list[str] = []

    console.print("[bold cyan]Creator Tools Pipeline[/bold cyan]")
    console.print("────────────────────────────")

    project = download_video(
        url,
        overwrite=overwrite,
    )
    project_dir = project.root_dir
    completed.append("Download")

    if overwrite:
        _prepare_transcription_overwrite(project_dir)

    _run_stage(
        "Transcription",
        already_completed=_transcription_exists(project_dir),
        overwrite=overwrite,
        action=lambda: transcribe_project(
            project_dir,
            model_size=whisper_model,
            language=language,
        ),
        completed=completed,
        skipped=skipped,
    )

    _run_stage(
        "Highlight Detection",
        already_completed=_highlight_exists(project_dir),
        overwrite=overwrite,
        action=lambda: highlight_project(
            project_dir,
            model_name=gemini_model,
            max_highlights=max_highlights,
            overwrite=overwrite,
        ),
        completed=completed,
        skipped=skipped,
    )

    _run_stage(
        "Clip Generation",
        already_completed=_clips_exist(project_dir),
        overwrite=overwrite,
        action=lambda: generate_project_clips(
            project_dir,
            limit=clip_limit,
            overwrite=overwrite,
        ),
        completed=completed,
        skipped=skipped,
    )

    _run_stage(
        "Subtitle Generation",
        already_completed=_clip_subtitles_exist(project_dir),
        overwrite=overwrite,
        action=lambda: generate_clip_subtitles(
            project_dir,
            limit=clip_limit,
            overwrite=overwrite,
        ),
        completed=completed,
        skipped=skipped,
    )

    if skip_burn_subtitle:
        console.print("[yellow][SKIP][/yellow] Subtitle Burn-in")
        skipped.append("Subtitle Burn-in")
    else:
        _run_stage(
            "Subtitle Burn-in",
            already_completed=_burned_clips_exist(project_dir),
            overwrite=overwrite,
            action=lambda: burn_project_subtitles(
                project_dir,
                limit=clip_limit,
                overwrite=overwrite,
            ),
            completed=completed,
            skipped=skipped,
        )

    _run_stage(
        "Thumbnail Ideas",
        already_completed=_thumbnail_ideas_exist(project_dir),
        overwrite=overwrite,
        action=lambda: generate_thumbnail_ideas(
            project_dir,
            model_name=gemini_model,
            overwrite=overwrite,
        ),
        completed=completed,
        skipped=skipped,
    )

    elapsed_seconds = perf_counter() - started_at

    report = PipelineReport(
        project_dir=project_dir,
        completed=tuple(completed),
        skipped=tuple(skipped),
        elapsed_seconds=elapsed_seconds,
    )

    print_pipeline_summary(report)

    return report

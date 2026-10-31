from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from time import perf_counter

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from anju.clipgen import generate_project_clips
from anju.downloader import download_video
from anju.highlighter import (
    get_latest_end_time,
    get_subtitle_bounds,
    highlight_project,
    load_existing_highlights,
    load_highlight_state,
    resolve_highlight_paths,
    timestamp_to_seconds,
)
from anju.subtitle import generate_clip_subtitles
from anju.subtitle_burner import burn_project_subtitles
from anju.thumbnail import generate_thumbnail_ideas
from anju.transcriber import transcribe_project

console = Console()

DEFAULT_HIGHLIGHTS_PER_HOUR = 10
DEFAULT_HIGHLIGHT_CHUNK_MINUTES = 60


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


def print_pipeline_summary(report: PipelineReport) -> None:
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
        stage_table.add_row("[bold green]✓ Done[/bold green]", stage)

    for stage in report.skipped:
        stage_table.add_row("[bold yellow]↷ Skip[/bold yellow]", stage)

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

    summary_table.add_row("Project", str(report.project_dir))
    summary_table.add_row("Completed", str(len(report.completed)))
    summary_table.add_row("Skipped", str(len(report.skipped)))
    summary_table.add_row(
        "Processing Time",
        _format_elapsed_time(report.elapsed_seconds),
    )

    content = Table.grid(padding=(1, 0))
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
    """完了済みならスキップし、それ以外はステージを実行する。"""
    if already_completed and not overwrite:
        console.print(f"[yellow][SKIP][/yellow] {name}")
        skipped.append(name)
        return

    console.print(f"[bold cyan][RUN][/bold cyan] {name}")
    action()
    completed.append(name)


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


def _prepare_transcription_overwrite(project_dir: Path) -> None:
    """Whisperの既存出力を削除して再生成可能にする。"""
    subtitles_dir = project_dir / "subtitles"

    for filename in ("full.srt", "full.txt"):
        path = subtitles_dir / filename
        if path.exists():
            path.unlink()


def _run_highlight_to_end(
    project_dir: Path,
    *,
    model_name: str,
    highlights_per_hour: int = DEFAULT_HIGHLIGHTS_PER_HOUR,
    overwrite: bool = False,
) -> None:
    """字幕の時間範囲に基づき、見どころ抽出を最後まで自動実行する。"""
    if highlights_per_hour < 1:
        raise ValueError("highlights_per_hourは1以上にしてください。")

    paths = resolve_highlight_paths(project_dir)

    try:
        subtitles = paths.subtitles_path.read_text(encoding="utf-8")
    except OSError as error:
        raise RuntimeError(f"字幕を読み込めません: {paths.subtitles_path}") from error

    if not subtitles.strip():
        raise RuntimeError(f"字幕ファイルが空です: {paths.subtitles_path}")

    subtitle_start, subtitle_end = get_subtitle_bounds(subtitles)

    # SRTの表示は秒単位なので、内部時刻も秒単位の整数にそろえる。
    # 小数秒の差で、表示上同じ時刻の空チャンクを処理しないようにする。
    subtitle_start = int(round(subtitle_start))
    subtitle_end = int(round(subtitle_end))
    total_seconds = max(0, subtitle_end - subtitle_start)

    # 動画の長さに応じた全体の上限。端数時間は切り上げる。
    total_max = ceil(total_seconds / 3600 * highlights_per_hour)

    console.print(
        f"[cyan]字幕の時間範囲: "
        f"{subtitle_start / 3600:.2f}h ～ "
        f"{subtitle_end / 3600:.2f}h[/cyan]"
    )
    console.print(f"[cyan]字幕基準の長さ: {total_seconds / 3600:.2f}時間[/cyan]")
    console.print(
        f"[cyan]見どころ候補の上限: 最大{total_max}件 "
        f"（1時間あたり{highlights_per_hour}件）[/cyan]"
    )

    if overwrite:
        current_time = subtitle_start
        first_run = True
        append = False
        existing_count = 0
    else:
        state_time = load_highlight_state(paths.state_path)
        existing = load_existing_highlights(paths.json_path)

        if state_time is not None:
            current_time = state_time
        else:
            # 旧形式のプロジェクトは既存候補の最後を開始位置にする。
            latest_end = get_latest_end_time(existing)
            current_time = (
                timestamp_to_seconds(latest_end)
                if latest_end is not None
                else subtitle_start
            )

        first_run = True
        append = bool(existing)
        existing_count = len(existing)

    # 状態ファイルや既存候補由来の時刻も秒単位にそろえる。
    current_time = int(round(current_time))

    # 残り1秒以下はSRTの時刻精度では有効なチャンクとして扱わない。
    if subtitle_end - current_time <= 1:
        console.print("[green]字幕の最後まで処理済みです。[/green]")
        return

    if existing_count >= total_max:
        console.print(
            f"[yellow]既存候補が上限{total_max}件に達しているため、"
            "追加抽出を行いません。[/yellow]"
        )
        return

    chunk_seconds = DEFAULT_HIGHLIGHT_CHUNK_MINUTES * 60

    while subtitle_end - current_time > 1:
        if existing_count >= total_max:
            console.print(f"[yellow]全体の上限{total_max}件に達しました。[/yellow]")
            break

        chunk_end = min(
            current_time + chunk_seconds,
            subtitle_end,
        )

        # 丸めや時刻データの端数により空チャンクになった場合は終了する。
        if chunk_end - current_time <= 1:
            console.print("[green]字幕の最後まで処理済みです。[/green]")
            break

        chunk_duration = chunk_end - current_time

        # このチャンクの上限と、動画全体の残り上限の小さい方を使う。
        chunk_max = ceil(chunk_duration / 3600 * highlights_per_hour)
        remaining_slots = total_max - existing_count
        chunk_max = min(chunk_max, remaining_slots)

        console.print()
        console.print(
            f"[bold cyan]抽出範囲: "
            f"{current_time / 3600:.2f}h ～ "
            f"{chunk_end / 3600:.2f}h[/bold cyan]"
        )
        console.print(
            f"[cyan]このチャンクの上限: {chunk_max}件 / "
            f"残り上限: {remaining_slots}件[/cyan]"
        )

        # 最初のチャンクだけoverwriteを有効にする。
        # 2つ目以降は既存結果へ追加する。
        highlight_project(
            project_dir,
            model_name=model_name,
            max_highlights=chunk_max,
            overwrite=overwrite and first_run,
            append=append or not first_run,
            chunk_minutes=DEFAULT_HIGHLIGHT_CHUNK_MINUTES,
        )

        # highlight_projectがJSON/Markdown保存後に進捗を更新したことを確認。
        saved_time = load_highlight_state(paths.state_path)

        if saved_time is not None:
            saved_time = int(round(saved_time))

        if saved_time is None or saved_time <= current_time:
            raise RuntimeError(
                "見どころ抽出の進捗が更新されませんでした。"
                "APIエラーや保存エラーを確認してください。"
            )

        current_time = saved_time
        first_run = False
        append = True

        # 保存済みの候補数を読み直し、全体上限を厳守する。
        existing_count = len(load_existing_highlights(paths.json_path))
        console.print(f"[green]現在の候補数: {existing_count}/{total_max}件[/green]")

    console.print()
    console.print(
        f"[green bold]見どころ抽出処理を終了しました。"
        f"候補数: {existing_count}/{total_max}件[/green bold]"
    )


def run_pipeline(
    url: str,
    *,
    whisper_model: str = "small",
    gemini_model: str = "gemini-2.5-flash",
    language: str = "ja",
    max_highlights: int = DEFAULT_HIGHLIGHTS_PER_HOUR,
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

    # 進捗状態を確認する必要があるため、既存ファイルがあっても
    # ハイライト抽出関数を呼び出す。完了済みなら関数内で終了する。
    _run_stage(
        "Highlight Detection",
        already_completed=False,
        overwrite=overwrite,
        action=lambda: _run_highlight_to_end(
            project_dir,
            model_name=gemini_model,
            highlights_per_hour=max_highlights,
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

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from anju.clipgen import Clip, load_clips
from anju.utils import sanitize_filename

console = Console()


@dataclass(frozen=True)
class SubtitleEntry:
    """SRT字幕の1項目。"""

    start: float
    end: float
    text: str


@dataclass(frozen=True)
class SubtitlePaths:
    """字幕切り出しで使用するパス。"""

    project_dir: Path
    full_srt_path: Path
    highlights_path: Path
    clips_dir: Path


def parse_srt_timestamp(value: str) -> float:
    """SRT形式の時刻を秒数へ変換する。"""
    match = re.fullmatch(
        r"(?P<hours>\d{2,3}):"
        r"(?P<minutes>[0-5]\d):"
        r"(?P<seconds>[0-5]\d),"
        r"(?P<milliseconds>\d{3})",
        value.strip(),
    )

    if not match:
        raise ValueError(f"SRTの時刻形式が不正です: {value}")

    hours = int(match.group("hours"))
    minutes = int(match.group("minutes"))
    seconds = int(match.group("seconds"))
    milliseconds = int(match.group("milliseconds"))

    return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000


def format_srt_timestamp(seconds: float) -> str:
    """秒数をSRT形式へ変換する。"""
    total_milliseconds = max(0, round(seconds * 1000))

    hours, remainder = divmod(
        total_milliseconds,
        3_600_000,
    )
    minutes, remainder = divmod(
        remainder,
        60_000,
    )
    secs, milliseconds = divmod(
        remainder,
        1_000,
    )

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def parse_srt(content: str) -> list[SubtitleEntry]:
    """SRT本文を字幕項目へ変換する。"""
    normalized = content.replace("\r\n", "\n").strip()

    if not normalized:
        return []

    blocks = re.split(r"\n{2,}", normalized)
    entries: list[SubtitleEntry] = []

    for block in blocks:
        lines = block.splitlines()

        if len(lines) < 3:
            continue

        timestamp_line = lines[1].strip()

        if " --> " not in timestamp_line:
            continue

        start_text, end_text = timestamp_line.split(
            " --> ",
            maxsplit=1,
        )

        text = "\n".join(lines[2:]).strip()

        if not text:
            continue

        entries.append(
            SubtitleEntry(
                start=parse_srt_timestamp(start_text),
                end=parse_srt_timestamp(end_text),
                text=text,
            )
        )

    return entries


def extract_clip_subtitles(
    entries: list[SubtitleEntry],
    clip: Clip,
) -> list[SubtitleEntry]:
    """クリップ範囲と重なる字幕を抽出して時刻を補正する。"""
    extracted: list[SubtitleEntry] = []

    for entry in entries:
        if entry.end <= clip.start_seconds:
            continue

        if entry.start >= clip.end_seconds:
            continue

        adjusted_start = (
            max(
                entry.start,
                clip.start_seconds,
            )
            - clip.start_seconds
        )

        adjusted_end = (
            min(
                entry.end,
                clip.end_seconds,
            )
            - clip.start_seconds
        )

        if adjusted_end <= adjusted_start:
            continue

        extracted.append(
            SubtitleEntry(
                start=adjusted_start,
                end=adjusted_end,
                text=entry.text,
            )
        )

    return extracted


def render_srt(entries: list[SubtitleEntry]) -> str:
    """字幕項目をSRT本文へ変換する。"""
    lines: list[str] = []

    for index, entry in enumerate(entries, start=1):
        lines.extend(
            [
                str(index),
                (
                    f"{format_srt_timestamp(entry.start)}"
                    f" --> "
                    f"{format_srt_timestamp(entry.end)}"
                ),
                entry.text,
                "",
            ]
        )

    return "\n".join(lines)


def resolve_subtitle_paths(
    project_dir: Path,
) -> SubtitlePaths:
    """字幕切り出しに必要なパスを解決する。"""
    project_dir = project_dir.expanduser().resolve()

    if not project_dir.is_dir():
        raise RuntimeError(f"プロジェクトフォルダが見つかりません: {project_dir}")

    full_srt_path = project_dir / "subtitles" / "full.srt"

    if not full_srt_path.is_file():
        raise RuntimeError(
            "full.srtが見つかりません。\n"
            f"{full_srt_path}\n"
            "先に anju transcribe を実行してください。"
        )

    highlights_path = project_dir / "clips" / "highlights.json"

    if not highlights_path.is_file():
        raise RuntimeError(
            "highlights.jsonが見つかりません。\n"
            f"{highlights_path}\n"
            "先に anju highlight を実行してください。"
        )

    clips_dir = project_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    return SubtitlePaths(
        project_dir=project_dir,
        full_srt_path=full_srt_path,
        highlights_path=highlights_path,
        clips_dir=clips_dir,
    )


def build_subtitle_output_path(
    clips_dir: Path,
    clip: Clip,
) -> Path:
    """クリップ動画と対応する字幕ファイル名を作る。"""
    safe_title = sanitize_filename(clip.title)

    return clips_dir / (f"{clip.index:03d}_{clip.score:03d}_{safe_title}.srt")


def generate_clip_subtitles(
    project_dir: Path,
    *,
    limit: int | None = None,
    overwrite: bool = False,
) -> None:
    """各見どころに対応するSRT字幕を生成する。"""
    if limit is not None and limit < 1:
        raise ValueError("limitは1以上にしてください。")

    paths = resolve_subtitle_paths(project_dir)
    clips = load_clips(paths.highlights_path)

    if limit is not None:
        clips = clips[:limit]

    content = paths.full_srt_path.read_text(encoding="utf-8")
    entries = parse_srt(content)

    if not entries:
        raise RuntimeError(f"有効な字幕がありません: {paths.full_srt_path}")

    console.print("[cyan]クリップ用字幕を生成します。[/cyan]")
    console.print(f"字幕元: {paths.full_srt_path}")
    console.print(f"生成件数: {len(clips)}")
    console.print()

    generated: list[Path] = []

    for clip in clips:
        output_path = build_subtitle_output_path(
            paths.clips_dir,
            clip,
        )

        if output_path.exists() and not overwrite:
            raise RuntimeError(
                "字幕ファイルがすでに存在します。\n"
                f"{output_path}\n"
                "--overwrite を付けると上書きできます。"
            )

        clip_entries = extract_clip_subtitles(
            entries,
            clip,
        )

        if not clip_entries:
            console.print(f"[yellow]字幕なし:[/yellow] {clip.index:03d} {clip.title}")
            continue

        output_path.write_text(
            render_srt(clip_entries),
            encoding="utf-8",
        )

        generated.append(output_path)

        console.print(f"[green]作成:[/green] {output_path.name}")

    console.print()

    if not generated:
        raise RuntimeError("生成できるクリップ字幕がありませんでした。")

    console.print("[bold green]字幕の切り出しが完了しました。[/bold green]")

    for path in generated:
        console.print(path)

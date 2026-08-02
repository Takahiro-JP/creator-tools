from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from anju.utils import sanitize_filename

console = Console()


@dataclass(frozen=True)
class Clip:
    """1件の切り抜き情報。"""

    index: int
    title: str
    start_time: str
    end_time: str
    score: int

    @property
    def start_seconds(self) -> float:
        return parse_timestamp(self.start_time)

    @property
    def end_seconds(self) -> float:
        return parse_timestamp(self.end_time)

    @property
    def duration(self) -> float:
        return self.end_seconds - self.start_seconds


@dataclass(frozen=True)
class ClipgenPaths:
    """切り抜き生成で使用するパス。"""

    project_dir: Path
    source_video: Path
    highlights_path: Path
    clips_dir: Path


def parse_timestamp(value: str) -> float:
    """HH:MM:SS形式を秒数へ変換する。"""
    match = re.fullmatch(
        r"(?P<hours>\d{1,3}):"
        r"(?P<minutes>[0-5]\d):"
        r"(?P<seconds>[0-5]\d(?:\.\d+)?)",
        value.strip(),
    )

    if not match:
        raise ValueError(
            f"時刻形式が不正です: {value}\nHH:MM:SS形式で指定してください。"
        )

    hours = int(match.group("hours"))
    minutes = int(match.group("minutes"))
    seconds = float(match.group("seconds"))

    return hours * 3600 + minutes * 60 + seconds


def find_source_video(project_dir: Path) -> Path:
    """rawフォルダから元動画を取得する。"""
    raw_dir = project_dir / "raw"

    if not raw_dir.is_dir():
        raise RuntimeError(f"rawフォルダが見つかりません: {raw_dir}")

    videos = sorted(
        path
        for path in raw_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".mp4", ".mkv", ".mov", ".webm"}
    )

    if not videos:
        raise RuntimeError(f"元動画が見つかりません: {raw_dir}")

    if len(videos) > 1:
        raise RuntimeError(
            "rawフォルダ内に動画が複数あります。\n対象動画を1本だけ残してください。"
        )

    return videos[0]


def resolve_clipgen_paths(
    project_dir: Path,
) -> ClipgenPaths:
    """切り抜き生成に必要なパスを解決する。"""
    project_dir = project_dir.expanduser().resolve()

    if not project_dir.is_dir():
        raise RuntimeError(f"プロジェクトフォルダが見つかりません: {project_dir}")

    source_video = find_source_video(project_dir)
    highlights_path = project_dir / "clips" / "highlights.json"

    if not highlights_path.is_file():
        raise RuntimeError(
            "highlights.jsonが見つかりません。\n"
            f"{highlights_path}\n"
            "先に anju highlight を実行してください。"
        )

    clips_dir = project_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    return ClipgenPaths(
        project_dir=project_dir,
        source_video=source_video,
        highlights_path=highlights_path,
        clips_dir=clips_dir,
    )


def load_clips(highlights_path: Path) -> list[Clip]:
    """highlights.jsonをClip一覧へ変換する。"""
    try:
        data = json.loads(highlights_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise RuntimeError(
            f"highlights.jsonを読み込めません: {highlights_path}"
        ) from error
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"highlights.jsonの形式が不正です: {highlights_path}"
        ) from error

    highlights = data.get("highlights")

    if not isinstance(highlights, list):
        raise RuntimeError("highlights.jsonにhighlights配列がありません。")

    clips: list[Clip] = []

    for index, item in enumerate(highlights, start=1):
        if not isinstance(item, dict):
            continue

        try:
            clip = Clip(
                index=index,
                title=str(item["title"]),
                start_time=str(item["start_time"]),
                end_time=str(item["end_time"]),
                score=int(item.get("score", 0)),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise RuntimeError(f"{index}件目の見どころ情報が不正です。") from error

        if clip.duration <= 0:
            raise RuntimeError(f"{index}件目の終了時刻が開始時刻以前です。")

        clips.append(clip)

    if not clips:
        raise RuntimeError("有効な見どころ候補がありません。")

    return clips


def build_output_path(
    clips_dir: Path,
    clip: Clip,
) -> Path:
    """切り抜き動画の保存先を作る。"""
    safe_title = sanitize_filename(clip.title)
    filename = f"{clip.index:03d}_{clip.score:03d}_{safe_title}.mp4"

    return clips_dir / filename


def generate_clip(
    *,
    source_video: Path,
    output_path: Path,
    clip: Clip,
    overwrite: bool,
) -> None:
    """FFmpegで切り抜き動画を生成する。"""
    if output_path.exists() and not overwrite:
        raise RuntimeError(f"出力ファイルがすでに存在します: {output_path}")

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "warning",
    ]

    if overwrite:
        command.append("-y")
    else:
        command.append("-n")

    command.extend(
        [
            "-ss",
            str(clip.start_seconds),
            "-i",
            str(source_video),
            "-t",
            str(clip.duration),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output_path),
        ]
    )

    result = subprocess.run(command)

    if result.returncode != 0:
        raise RuntimeError(f"切り抜き生成に失敗しました: {output_path}")


def generate_project_clips(
    project_dir: Path,
    *,
    limit: int | None = None,
    overwrite: bool = False,
) -> None:
    """見どころ候補から切り抜き動画を生成する。"""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpegが見つかりません。")

    if limit is not None and limit < 1:
        raise ValueError("limitは1以上にしてください。")

    paths = resolve_clipgen_paths(project_dir)
    clips = load_clips(paths.highlights_path)

    if limit is not None:
        clips = clips[:limit]

    console.print("[cyan]切り抜き動画を生成します。[/cyan]")
    console.print(f"元動画: {paths.source_video}")
    console.print(f"生成件数: {len(clips)}")
    console.print()

    generated: list[Path] = []

    for clip in clips:
        output_path = build_output_path(
            paths.clips_dir,
            clip,
        )

        console.print(
            f"[bold]{clip.index:03d}[/bold] "
            f"{clip.start_time} - {clip.end_time} "
            f"{clip.title}"
        )

        generate_clip(
            source_video=paths.source_video,
            output_path=output_path,
            clip=clip,
            overwrite=overwrite,
        )

        generated.append(output_path)

    console.print()
    console.print("[bold green]切り抜き生成が完了しました。[/bold green]")

    for path in generated:
        console.print(path)

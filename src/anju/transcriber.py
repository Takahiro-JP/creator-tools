from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from faster_whisper import WhisperModel
from rich.console import Console

console = Console()


@dataclass(frozen=True)
class TranscriptionPaths:
    """文字起こしの入力・出力パス。"""

    project_dir: Path
    source_video: Path
    subtitles_dir: Path
    srt_path: Path
    text_path: Path


def load_metadata(project_dir: Path) -> dict[str, Any]:
    """プロジェクトのmetadata.jsonを読み込む。"""
    metadata_path = project_dir / "metadata.json"

    if not metadata_path.is_file():
        raise RuntimeError(f"metadata.jsonが見つかりません: {metadata_path}")

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise RuntimeError(f"metadata.jsonの形式が不正です: {metadata_path}") from error
    except OSError as error:
        raise RuntimeError(f"metadata.jsonを読み込めません: {metadata_path}") from error

    if not isinstance(metadata, dict):
        raise RuntimeError(f"metadata.jsonの内容が不正です: {metadata_path}")

    return metadata


def find_source_video(project_dir: Path) -> Path:
    """rawフォルダから元動画を1本取得する。"""
    raw_dir = project_dir / "raw"

    if not raw_dir.is_dir():
        raise RuntimeError(f"rawフォルダが見つかりません: {raw_dir}")

    candidates = sorted(
        path
        for path in raw_dir.iterdir()
        if path.is_file() and path.suffix.lower() in {".mp4", ".mkv", ".mov", ".webm"}
    )

    if not candidates:
        raise RuntimeError(f"文字起こし対象の動画が見つかりません: {raw_dir}")

    if len(candidates) > 1:
        raise RuntimeError(
            "rawフォルダ内に動画が複数あります。\n対象動画を1本だけ残してください。"
        )

    return candidates[0]


def resolve_paths(project_dir: Path) -> TranscriptionPaths:
    """文字起こしに必要なパスを組み立てる。"""
    project_dir = project_dir.expanduser().resolve()

    if not project_dir.is_dir():
        raise RuntimeError(f"プロジェクトフォルダが見つかりません: {project_dir}")

    load_metadata(project_dir)

    source_video = find_source_video(project_dir)
    subtitles_dir = project_dir / "subtitles"
    subtitles_dir.mkdir(parents=True, exist_ok=True)

    return TranscriptionPaths(
        project_dir=project_dir,
        source_video=source_video,
        subtitles_dir=subtitles_dir,
        srt_path=subtitles_dir / "full.srt",
        text_path=subtitles_dir / "full.txt",
    )


def format_srt_timestamp(seconds: float) -> str:
    """秒数をSRT形式の時刻へ変換する。"""
    milliseconds = max(0, round(seconds * 1000))

    hours, milliseconds = divmod(milliseconds, 3_600_000)
    minutes, milliseconds = divmod(milliseconds, 60_000)
    secs, milliseconds = divmod(milliseconds, 1_000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def transcribe_project(
    project_dir: Path,
    *,
    model_size: str = "small",
    language: str = "ja",
) -> None:
    """動画を文字起こしし、SRTとTXTを保存する。"""
    paths = resolve_paths(project_dir)

    if paths.srt_path.exists() or paths.text_path.exists():
        raise RuntimeError(
            f"文字起こし結果がすでに存在します。\n{paths.srt_path}\n{paths.text_path}"
        )

    console.print("[cyan]Whisperモデルを読み込んでいます...[/cyan]")
    console.print(f"モデル: {model_size}")
    console.print(f"動画: {paths.source_video}")
    console.print()

    model = WhisperModel(
        model_size,
        device="cpu",
        compute_type="int8",
    )

    segments, info = model.transcribe(
        str(paths.source_video),
        language=language,
        beam_size=5,
        vad_filter=True,
    )

    console.print(
        f"[blue]検出言語:[/blue] {info.language} ({info.language_probability:.2%})"
    )
    console.print("[cyan]文字起こし中...[/cyan]")

    srt_lines: list[str] = []
    text_lines: list[str] = []

    for index, segment in enumerate(segments, start=1):
        text = segment.text.strip()

        if not text:
            continue

        start = format_srt_timestamp(segment.start)
        end = format_srt_timestamp(segment.end)

        srt_lines.extend(
            [
                str(index),
                f"{start} --> {end}",
                text,
                "",
            ]
        )
        text_lines.append(text)

        console.print(f"[dim]{start}[/dim] {text}")

    if not text_lines:
        raise RuntimeError("音声を検出できず、文字起こし結果が空でした。")

    paths.srt_path.write_text(
        "\n".join(srt_lines),
        encoding="utf-8",
    )

    paths.text_path.write_text(
        "\n".join(text_lines) + "\n",
        encoding="utf-8",
    )

    console.print()
    console.print("[bold green]文字起こしが完了しました。[/bold green]")
    console.print(paths.srt_path)
    console.print(paths.text_path)

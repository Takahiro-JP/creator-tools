from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from faster_whisper import WhisperModel
from rich.console import Console
from rich.text import Text

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

    supported_extensions = {
        ".mp4",
        ".mkv",
        ".mov",
        ".webm",
    }

    try:
        candidates = sorted(
            path
            for path in raw_dir.iterdir()
            if path.is_file() and path.suffix.lower() in supported_extensions
        )
    except OSError as error:
        raise RuntimeError(f"rawフォルダを読み込めません: {raw_dir}") from error

    if not candidates:
        raise RuntimeError(f"文字起こし対象の動画が見つかりません: {raw_dir}")

    if len(candidates) > 1:
        video_list = "\n".join(f"- {path.name}" for path in candidates)

        raise RuntimeError(
            "rawフォルダ内に動画が複数あります。\n"
            "対象動画を1本だけ残してください。\n\n"
            f"{video_list}"
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

    try:
        subtitles_dir.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        raise RuntimeError(
            f"subtitlesフォルダを作成できません: {subtitles_dir}"
        ) from error

    return TranscriptionPaths(
        project_dir=project_dir,
        source_video=source_video,
        subtitles_dir=subtitles_dir,
        srt_path=subtitles_dir / "full.srt",
        text_path=subtitles_dir / "full.txt",
    )


def format_srt_timestamp(seconds: float) -> str:
    """秒数をSRT形式の時刻へ変換する。

    例:
        8426.530 -> 02:20:26,530
    """
    try:
        total_milliseconds = max(0, round(float(seconds) * 1000))
    except (TypeError, ValueError) as error:
        raise RuntimeError(f"時刻を秒数として処理できません: {seconds!r}") from error

    hours, remainder = divmod(total_milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, milliseconds = divmod(remainder, 1_000)

    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def print_segment(timestamp: str, text: str) -> None:
    """文字起こし結果を安全にコンソールへ表示する。"""
    line = Text()
    line.append(timestamp, style="dim")
    line.append(" ")
    line.append(text)

    console.print(line)


def write_transcription_files(
    paths: TranscriptionPaths,
    srt_lines: list[str],
    text_lines: list[str],
) -> None:
    """文字起こし結果をSRTとTXTへ保存する。"""
    srt_content = "\n".join(srt_lines).rstrip() + "\n"
    text_content = "\n".join(text_lines).rstrip() + "\n"

    try:
        paths.srt_path.write_text(
            srt_content,
            encoding="utf-8",
        )
    except OSError as error:
        raise RuntimeError(f"SRTファイルを書き込めません: {paths.srt_path}") from error

    try:
        paths.text_path.write_text(
            text_content,
            encoding="utf-8",
        )
    except OSError as error:
        # SRTだけが残る中途半端な状態を避ける
        try:
            paths.srt_path.unlink(missing_ok=True)
        except OSError:
            pass

        raise RuntimeError(
            f"テキストファイルを書き込めません: {paths.text_path}"
        ) from error


def transcribe_project(
    project_dir: Path,
    *,
    model_size: str = "small",
    language: str = "ja",
) -> None:
    """動画を文字起こしし、SRTとTXTを保存する。"""
    paths = resolve_paths(project_dir)

    existing_files = [
        path for path in (paths.srt_path, paths.text_path) if path.exists()
    ]

    if existing_files:
        existing_file_list = "\n".join(str(path) for path in existing_files)

        raise RuntimeError(f"文字起こし結果がすでに存在します。\n{existing_file_list}")

    console.print("[cyan]Whisperモデルを読み込んでいます...[/cyan]")
    console.print(f"モデル: {model_size}")
    console.print(f"動画: {paths.source_video}")
    console.print()

    try:
        model = WhisperModel(
            model_size,
            device="cpu",
            compute_type="int8",
        )
    except Exception as error:
        raise RuntimeError(f"Whisperモデルを読み込めません: {model_size}") from error

    try:
        segments, info = model.transcribe(
            str(paths.source_video),
            language=language,
            beam_size=5,
            vad_filter=True,
        )
    except Exception as error:
        raise RuntimeError(
            f"動画の文字起こしを開始できません: {paths.source_video}"
        ) from error

    console.print(
        f"[blue]検出言語:[/blue] {info.language} ({info.language_probability:.2%})"
    )
    console.print("[cyan]文字起こし中...[/cyan]")

    srt_lines: list[str] = []
    text_lines: list[str] = []

    subtitle_index = 1

    try:
        for segment in segments:
            text = segment.text.strip()

            if not text:
                continue

            start = format_srt_timestamp(segment.start)
            end = format_srt_timestamp(segment.end)

            srt_lines.extend(
                [
                    str(subtitle_index),
                    f"{start} --> {end}",
                    text,
                    "",
                ]
            )

            text_lines.append(text)
            print_segment(start, text)

            subtitle_index += 1
    except RuntimeError:
        raise
    except Exception as error:
        raise RuntimeError("文字起こし結果の処理中にエラーが発生しました。") from error

    if not text_lines:
        raise RuntimeError("音声を検出できず、文字起こし結果が空でした。")

    write_transcription_files(
        paths,
        srt_lines,
        text_lines,
    )

    console.print()
    console.print("[bold green]文字起こしが完了しました。[/bold green]")
    console.print(paths.srt_path)
    console.print(paths.text_path)

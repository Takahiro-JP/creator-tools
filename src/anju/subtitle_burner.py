from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

console = Console()


@dataclass(frozen=True)
class SubtitlePair:
    """字幕焼き込み対象の動画とSRT。"""

    video_path: Path
    subtitle_path: Path
    output_path: Path


def escape_subtitle_filter_path(path: Path) -> str:
    """FFmpegのsubtitlesフィルター用にパスをエスケープする。"""
    value = str(path.resolve())
    value = value.replace("\\", "\\\\")
    value = value.replace(":", r"\:")
    value = value.replace("'", r"\'")
    value = value.replace("[", r"\[")
    value = value.replace("]", r"\]")
    value = value.replace(",", r"\,")

    return value


def find_subtitle_pairs(
    project_dir: Path,
    *,
    overwrite: bool = False,
) -> list[SubtitlePair]:
    """clipsフォルダから同名のMP4とSRTを探す。"""
    project_dir = project_dir.expanduser().resolve()

    if not project_dir.is_dir():
        raise RuntimeError(f"プロジェクトフォルダが見つかりません: {project_dir}")

    clips_dir = project_dir / "clips"

    if not clips_dir.is_dir():
        raise RuntimeError(f"clipsフォルダが見つかりません: {clips_dir}")

    pairs: list[SubtitlePair] = []

    for video_path in sorted(clips_dir.glob("*.mp4")):
        if video_path.stem.endswith("_subtitled"):
            continue

        subtitle_path = video_path.with_suffix(".srt")

        if not subtitle_path.is_file():
            continue

        output_path = video_path.with_name(f"{video_path.stem}_subtitled.mp4")

        if output_path.exists() and not overwrite:
            continue

        pairs.append(
            SubtitlePair(
                video_path=video_path,
                subtitle_path=subtitle_path,
                output_path=output_path,
            )
        )

    return pairs


def burn_subtitle(
    pair: SubtitlePair,
    *,
    overwrite: bool,
    font_name: str,
    font_size: int,
    margin_v: int,
) -> None:
    """1本の動画へSRT字幕を焼き込む。"""
    escaped_srt = escape_subtitle_filter_path(pair.subtitle_path)

    force_style = (
        f"FontName={font_name},"
        f"FontSize={font_size},"
        "PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,"
        "BorderStyle=1,"
        "Outline=3,"
        "Shadow=1,"
        "Alignment=2,"
        f"MarginV={margin_v}"
    )

    subtitle_filter = f"subtitles='{escaped_srt}':force_style='{force_style}'"

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "warning",
    ]

    command.append("-y" if overwrite else "-n")

    command.extend(
        [
            "-i",
            str(pair.video_path),
            "-vf",
            subtitle_filter,
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-c:a",
            "copy",
            "-movflags",
            "+faststart",
            str(pair.output_path),
        ]
    )

    result = subprocess.run(command)

    if result.returncode != 0:
        raise RuntimeError(f"字幕焼き込みに失敗しました: {pair.video_path}")


def burn_project_subtitles(
    project_dir: Path,
    *,
    limit: int | None = None,
    overwrite: bool = False,
    font_name: str = "Noto Sans CJK JP",
    font_size: int = 28,
    margin_v: int = 40,
) -> None:
    """プロジェクト内の各クリップへ字幕を焼き込む。"""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpegが見つかりません。")

    if limit is not None and limit < 1:
        raise ValueError("limitは1以上にしてください。")

    if font_size < 1:
        raise ValueError("font_sizeは1以上にしてください。")

    if margin_v < 0:
        raise ValueError("margin_vは0以上にしてください。")

    pairs = find_subtitle_pairs(
        project_dir,
        overwrite=overwrite,
    )

    if limit is not None:
        pairs = pairs[:limit]

    if not pairs:
        raise RuntimeError(
            "字幕焼き込み対象がありません。\n"
            "同名のMP4とSRTがclipsフォルダにあるか確認してください。"
        )

    console.print("[cyan]字幕を動画へ焼き込みます。[/cyan]")
    console.print(f"対象件数: {len(pairs)}")
    console.print(f"フォント: {font_name}")
    console.print()

    generated: list[Path] = []

    for index, pair in enumerate(pairs, start=1):
        console.print(f"[bold]{index:03d}[/bold] {pair.video_path.name}")

        burn_subtitle(
            pair,
            overwrite=overwrite,
            font_name=font_name,
            font_size=font_size,
            margin_v=margin_v,
        )

        generated.append(pair.output_path)

    console.print()
    console.print("[bold green]字幕焼き込みが完了しました。[/bold green]")

    for path in generated:
        console.print(path)

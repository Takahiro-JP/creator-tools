from __future__ import annotations

import json
import platform
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from rich.console import Console

from anju.config import get_default_base_dir, load_config
from anju.project import Project, ProjectMetadata
from anju.utils import format_upload_date, open_folder, sanitize_filename

console = Console()


def extract_video_id(url: str) -> str:
    """Twitch VOD URLから動画IDを取得する。"""
    match = re.search(r"twitch\.tv/videos/(\d+)", url)

    if not match:
        raise ValueError(
            "Twitch VOD URLではありません。\n"
            "例: https://www.twitch.tv/videos/2803053225"
        )

    return match.group(1)


def find_twitch_downloader(
    config: dict[str, Any],
) -> Path | None:
    """設定、PATH、標準候補からTwitchDownloaderCLIを探す。"""
    configured_path = str(config.get("twitch_downloader_cli") or "").strip()

    if configured_path:
        path = Path(configured_path).expanduser()

        if path.is_file():
            return path

    for command_name in (
        "TwitchDownloaderCLI",
        "TwitchDownloaderCLI.exe",
    ):
        found = shutil.which(command_name)

        if found:
            return Path(found)

    if platform.system() == "Windows":
        candidates = (
            Path(
                r"D:\Tools\TwitchDownloader"
                r"\TwitchDownloaderCLI.exe"
            ),
            Path(
                r"C:\Tools\TwitchDownloader"
                r"\TwitchDownloaderCLI.exe"
            ),
        )
    else:
        candidates = (
            Path.home() / "Tools" / "TwitchDownloader" / "TwitchDownloaderCLI",
            Path.home() / "Downloads" / "TwitchDownloaderCLI" / "TwitchDownloaderCLI",
            Path("/opt/homebrew/bin/TwitchDownloaderCLI"),
            Path("/usr/local/bin/TwitchDownloaderCLI"),
        )

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return None


def get_video_metadata(url: str) -> dict[str, Any]:
    """yt-dlpでTwitch動画の情報を取得する。"""
    result = subprocess.run(
        [
            "yt-dlp",
            "-J",
            "--no-warnings",
            url,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        error_message = result.stderr.strip() or "不明なエラー"

        raise RuntimeError(f"動画情報の取得に失敗しました。\n{error_message}")

    try:
        metadata = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError("yt-dlpの出力を解析できませんでした。") from error

    if not isinstance(metadata, dict):
        raise RuntimeError("yt-dlpから予期しない形式の情報が返されました。")

    return metadata


def supports_h264_videotoolbox() -> bool:
    """FFmpegがh264_videotoolboxに対応しているか確認する。"""
    if platform.system() != "Darwin":
        return False

    if shutil.which("ffmpeg") is None:
        return False

    result = subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-encoders",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        return False

    return "h264_videotoolbox" in result.stdout


def convert_for_resolve(
    video_path: Path,
) -> Path:
    """DaVinci Resolve向けにH.264/AACへ再エンコードする。"""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpegが見つかりません。")

    converted_path = video_path.with_name(
        f"{video_path.stem}.resolve{video_path.suffix}"
    )

    if converted_path.exists():
        converted_path.unlink()

    console.print()
    console.print("[cyan]DaVinci Resolve向けに動画を変換しています...[/cyan]")

    if supports_h264_videotoolbox():
        console.print(
            "[green]VideoToolboxによるハードウェアエンコードを使用します。[/green]"
        )

        video_encoder_args = [
            "-c:v",
            "h264_videotoolbox",
            "-b:v",
            "12M",
            "-pix_fmt",
            "yuv420p",
        ]
    else:
        console.print(
            "[yellow]VideoToolboxを使用できないため、libx264で変換します。[/yellow]"
        )

        video_encoder_args = [
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
        ]

    console.print()

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(video_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0",
        *video_encoder_args,
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(converted_path),
    ]

    result = subprocess.run(command)

    if result.returncode != 0:
        if converted_path.exists():
            converted_path.unlink()

        raise RuntimeError("DaVinci Resolve向け動画の変換に失敗しました。")

    if not converted_path.exists():
        raise RuntimeError("変換後の動画ファイルが見つかりません。")

    return converted_path


def download_video(
    url: str,
    *,
    overwrite: bool = False,
) -> Project:
    """Twitch VODをダウンロードしてプロジェクトを作成する。"""
    config = load_config()
    cli_path = find_twitch_downloader(config)

    if cli_path is None:
        raise RuntimeError(
            "TwitchDownloaderCLIが見つかりません。\n"
            "設定ファイルの twitch_downloader_cli に"
            "実行ファイルのパスを指定してください。"
        )

    if shutil.which("yt-dlp") is None:
        raise RuntimeError("yt-dlpが見つかりません。")

    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpegが見つかりません。")

    video_id = extract_video_id(url)

    console.print("[cyan]動画情報を取得しています...[/cyan]")

    source_metadata = get_video_metadata(url)

    title = sanitize_filename(str(source_metadata.get("title") or "Untitled"))

    uploader = sanitize_filename(
        str(
            source_metadata.get("uploader")
            or source_metadata.get("channel")
            or "Twitch"
        )
    )

    date_text = format_upload_date(source_metadata.get("upload_date"))

    base_dir = Path(str(config.get("base_dir") or get_default_base_dir())).expanduser()

    project = Project.create(
        base_dir=base_dir,
        date_text=date_text,
        video_id=video_id,
    )

    metadata = ProjectMetadata.create(
        video_id=video_id,
        source_url=url,
        title=title,
        uploader=uploader,
        upload_date=date_text,
        duration=source_metadata.get("duration"),
    )

    project.save_metadata(metadata)

    video_extensions = {
        ".mp4",
        ".mkv",
        ".mov",
        ".webm",
    }

    existing_videos = sorted(
        path
        for path in project.raw_dir.iterdir()
        if (path.is_file() and path.suffix.lower() in video_extensions)
    )

    if existing_videos and not overwrite:
        console.print()
        console.print(
            "[yellow]"
            "元動画はすでに存在するため、"
            "ダウンロードをスキップします。"
            "[/yellow]"
        )
        console.print(existing_videos[0])

        return project

    if overwrite:
        for existing_video in existing_videos:
            existing_video.unlink()

    temporary_path = project.raw_dir / f"{video_id}.mp4"

    if temporary_path.exists():
        temporary_path.unlink()

    final_path = project.raw_dir / (f"{date_text}_{uploader}_{title}.mp4")

    if final_path.exists():
        final_path = project.raw_dir / (
            f"{date_text}_{uploader}_{title}_{video_id}.mp4"
        )

    console.print()
    console.print("[bold]ダウンロードを開始します。[/bold]")
    console.print(f"動画ID: {video_id}")
    console.print(f"一時保存先: {temporary_path}")
    console.print()

    result = subprocess.run(
        [
            str(cli_path),
            "videodownload",
            "--id",
            video_id,
            "--output",
            str(temporary_path),
        ]
    )

    if result.returncode != 0:
        raise RuntimeError("動画のダウンロードに失敗しました。")

    if not temporary_path.exists():
        raise RuntimeError(
            f"ダウンロード済みファイルが見つかりません。\n{temporary_path}"
        )

    console.print()
    console.print("[bold green]Twitch動画のダウンロードが完了しました。[/bold green]")

    converted_path = convert_for_resolve(temporary_path)

    # Resolve向け動画の生成に成功した後で、
    # TwitchDownloaderCLIが生成した元動画を削除する。
    temporary_path.unlink()

    # Resolve向け動画を正式な動画ファイル名に変更する。
    converted_path.rename(final_path)

    console.print()
    console.print(
        "[bold green]DaVinci Resolve向け動画の変換が完了しました。[/bold green]"
    )
    console.print(final_path)

    console.print()
    console.print("[blue]プロジェクト:[/blue]")
    console.print(project.root_dir)

    console.print()
    console.print("[blue]メタデータ:[/blue]")
    console.print(project.metadata_path)

    open_folder(project.root_dir)

    return project

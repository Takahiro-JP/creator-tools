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
    configured_path = str(
        config.get("twitch_downloader_cli") or ""
    ).strip()

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
            Path.home()
            / "Tools"
            / "TwitchDownloader"
            / "TwitchDownloaderCLI",
            Path.home()
            / "Downloads"
            / "TwitchDownloaderCLI"
            / "TwitchDownloaderCLI",
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

        raise RuntimeError(
            "動画情報の取得に失敗しました。\n"
            f"{error_message}"
        )

    try:
        metadata = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise RuntimeError(
            "yt-dlpの出力を解析できませんでした。"
        ) from error

    if not isinstance(metadata, dict):
        raise RuntimeError(
            "yt-dlpから予期しない形式の情報が返されました。"
        )

    return metadata


def create_project_directories(
    base_dir: Path,
    date_text: str,
) -> dict[str, Path]:
    """日付別の作業フォルダを作成する。"""
    root_dir = base_dir / date_text

    directories = {
        "root": root_dir,
        "video": root_dir / "video",
        "clips": root_dir / "clips",
        "subtitles": root_dir / "subtitles",
        "thumbnail": root_dir / "thumbnail",
        "project": root_dir / "project",
    }

    for directory in directories.values():
        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    return directories


def download_video(url: str) -> None:
    """Twitch VODをダウンロードして日付別に整理する。"""
    config = load_config()
    cli_path = find_twitch_downloader(config)

    if cli_path is None:
        raise RuntimeError(
            "TwitchDownloaderCLIが見つかりません。\n"
            "設定ファイルの twitch_downloader_cli に"
            "実行ファイルのパスを指定してください。"
        )

    if shutil.which("yt-dlp") is None:
        raise RuntimeError(
            "yt-dlpが見つかりません。"
        )

    video_id = extract_video_id(url)

    console.print(
        "[cyan]動画情報を取得しています...[/cyan]"
    )

    metadata = get_video_metadata(url)

    title = sanitize_filename(
        str(metadata.get("title") or "Untitled")
    )

    uploader = sanitize_filename(
        str(
            metadata.get("uploader")
            or metadata.get("channel")
            or "Twitch"
        )
    )

    date_text = format_upload_date(
        metadata.get("upload_date")
    )

    base_dir = Path(
        str(
            config.get("base_dir")
            or get_default_base_dir()
        )
    ).expanduser()

    directories = create_project_directories(
        base_dir=base_dir,
        date_text=date_text,
    )

    temporary_path = (
        directories["video"] / f"{video_id}.mp4"
    )

    final_filename = (
        f"{date_text}_{uploader}_{title}.mp4"
    )

    final_path = (
        directories["video"] / final_filename
    )

    if final_path.exists():
        final_path = directories["video"] / (
            f"{date_text}_{uploader}_{title}_"
            f"{video_id}.mp4"
        )

    console.print()
    console.print(
        "[bold]ダウンロードを開始します。[/bold]"
    )
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
        raise RuntimeError(
            "動画のダウンロードに失敗しました。"
        )

    if not temporary_path.exists():
        raise RuntimeError(
            "ダウンロード済みファイルが"
            "見つかりません。\n"
            f"{temporary_path}"
        )

    temporary_path.rename(final_path)

    console.print()
    console.print(
        "[bold green]ダウンロードが完了しました。[/bold green]"
    )
    console.print(final_path)
    console.print()
    console.print("[blue]作業フォルダ:[/blue]")
    console.print(directories["root"])

    open_folder(directories["root"])

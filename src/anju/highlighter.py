from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console

from anju.ai.client import generate_structured_content
from anju.ai.prompts import build_highlight_prompt
from anju.ai.schemas import HighlightItem, HighlightResponse

console = Console()

DEFAULT_CHUNK_MINUTES = 120


@dataclass(frozen=True)
class HighlightPaths:
    """見どころ抽出で使用するファイルパス."""

    project_dir: Path
    subtitles_path: Path
    clips_dir: Path
    json_path: Path
    markdown_path: Path
    state_path: Path


def resolve_highlight_paths(project_dir: Path) -> HighlightPaths:
    """見どころ抽出に必要なパスを解決する."""

    if not project_dir.is_dir():
        raise RuntimeError(f"プロジェクトフォルダが見つかりません: {project_dir}")

    metadata_path = project_dir / "metadata.json"

    if not metadata_path.is_file():
        raise RuntimeError(f"metadata.json が見つかりません: {metadata_path}")

    subtitles_path = project_dir / "subtitles" / "full.srt"

    if not subtitles_path.is_file():
        raise RuntimeError(f"字幕ファイルが見つかりません: {subtitles_path}")

    clips_dir = project_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    return HighlightPaths(
        project_dir=project_dir,
        subtitles_path=subtitles_path,
        clips_dir=clips_dir,
        json_path=clips_dir / "highlights.json",
        markdown_path=clips_dir / "highlights.md",
        state_path=clips_dir / "highlight_state.json",
    )


def load_project_metadata(project_dir: Path) -> dict[str, Any]:
    """metadata.jsonを読み込む."""

    metadata_path = project_dir / "metadata.json"

    try:
        return json.loads(metadata_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise RuntimeError(f"metadata.jsonを読み込めません: {metadata_path}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"metadata.jsonのJSON形式が不正です: {metadata_path}"
        ) from error


def load_existing_highlights(
    json_path: Path,
) -> list[HighlightItem]:
    """既存の見どころ候補を読み込む."""

    if not json_path.is_file():
        return []

    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise RuntimeError(
            f"既存の見どころ結果を読み込めません: {json_path}"
        ) from error
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"既存の見どころ結果のJSON形式が不正です: {json_path}"
        ) from error

    raw_highlights = data.get("highlights", [])

    if not isinstance(raw_highlights, list):
        raise RuntimeError(f"既存のhighlightsが不正です: {json_path}")

    try:
        return [HighlightItem.model_validate(item) for item in raw_highlights]
    except Exception as error:
        raise RuntimeError(
            f"既存の見どころデータを解析できません: {json_path}"
        ) from error


def timestamp_to_seconds(timestamp: str) -> float:
    """HH:MM:SS(.mmm)形式の時刻を秒に変換する."""

    normalized = timestamp.replace(",", ".")
    parts = normalized.split(":")

    if len(parts) != 3:
        raise ValueError(f"不正な時刻形式です: {timestamp}")

    hours, minutes, seconds = parts

    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def seconds_to_timestamp(seconds: float) -> str:
    """秒をHH:MM:SS形式へ変換する."""

    total_seconds = max(0, int(seconds))

    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def get_latest_end_time(
    highlights: list[HighlightItem],
) -> str | None:
    """既存候補の中で最も遅い終了時刻を返す."""

    if not highlights:
        return None

    latest = max(
        highlights,
        key=lambda item: timestamp_to_seconds(item.end_time),
    )

    return latest.end_time


def get_subtitle_bounds(
    subtitles: str,
) -> tuple[float, float]:
    """字幕全体の開始時刻と終了時刻を取得する."""

    starts: list[float] = []
    ends: list[float] = []

    for line in subtitles.splitlines():
        if "-->" not in line:
            continue

        parts = line.split("-->")

        if len(parts) != 2:
            continue

        try:
            start = timestamp_to_seconds(parts[0].strip())
            end = timestamp_to_seconds(parts[1].strip())
        except ValueError:
            continue

        starts.append(start)
        ends.append(end)

    if not starts or not ends:
        raise RuntimeError("字幕から時間情報を取得できませんでした。")

    return min(starts), max(ends)


def trim_subtitles_range(
    subtitles: str,
    start_seconds: float,
    end_seconds: float,
) -> str:
    """指定した時間範囲のSRT字幕だけを残す."""

    blocks = re.split(
        r"\n\s*\n",
        subtitles.strip(),
    )

    kept_blocks: list[str] = []

    for block in blocks:
        lines = block.splitlines()

        time_line = next(
            (line for line in lines if "-->" in line),
            None,
        )

        if time_line is None:
            continue

        parts = time_line.split("-->")

        if len(parts) != 2:
            continue

        try:
            subtitle_start = timestamp_to_seconds(parts[0].strip())
            subtitle_end = timestamp_to_seconds(parts[1].strip())
        except ValueError:
            continue

        # チャンクと少しでも重なる字幕を残す。
        if subtitle_end >= start_seconds and subtitle_start < end_seconds:
            kept_blocks.append(block)

    return "\n\n".join(kept_blocks)


def load_highlight_state(
    state_path: Path,
) -> float | None:
    """前回処理済みの時刻を読み込む."""

    if not state_path.is_file():
        return None

    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise RuntimeError(f"見どころ進捗を読み込めません: {state_path}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"見どころ進捗のJSON形式が不正です: {state_path}") from error

    last_processed_time = data.get("last_processed_time")

    if not isinstance(last_processed_time, str):
        raise RuntimeError("highlight_state.json の last_processed_time が不正です。")

    return timestamp_to_seconds(last_processed_time)


def save_highlight_state(
    state_path: Path,
    last_processed_seconds: float,
) -> None:
    """処理済みの時刻を保存する."""

    state = {"last_processed_time": seconds_to_timestamp(last_processed_seconds)}

    try:
        state_path.write_text(
            json.dumps(
                state,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError as error:
        raise RuntimeError(f"見どころ進捗を書き込めません: {state_path}") from error


def create_markdown(
    highlights: list[HighlightItem],
) -> str:
    """見どころ候補一覧のMarkdownを生成する."""

    lines = [
        "# 見どころ候補",
        "",
    ]

    for index, item in enumerate(
        highlights,
        start=1,
    ):
        lines.extend(
            [
                f"## {index}. {item.title}",
                "",
                f"- 開始: {item.start_time}",
                f"- 終了: {item.end_time}",
                f"- スコア: {item.score}",
                f"- 理由: {item.reason}",
                "",
            ]
        )

    return "\n".join(lines)


def highlight_project(
    project_dir: Path,
    *,
    model_name: str = "gemini-2.5-flash",
    max_highlights: int = 10,
    overwrite: bool = False,
    append: bool = False,
    chunk_minutes: int = DEFAULT_CHUNK_MINUTES,
) -> None:
    """字幕からGeminiで見どころ候補を抽出する."""

    if max_highlights < 1:
        raise RuntimeError("max_highlightsは1以上で指定してください。")

    if chunk_minutes < 1:
        raise RuntimeError("chunk_minutesは1以上で指定してください。")

    if overwrite and append:
        raise RuntimeError("--overwrite と --append は同時に指定できません。")

    paths = resolve_highlight_paths(project_dir)

    if paths.markdown_path.is_file() and not paths.json_path.is_file() and append:
        raise RuntimeError(
            "highlights.md は存在しますが "
            "highlights.json がありません。"
            "追加生成するにはhighlights.jsonが必要です。"
        )

    existing_highlights: list[HighlightItem] = []

    if append:
        existing_highlights = load_existing_highlights(paths.json_path)

    if (
        not overwrite
        and not append
        and (paths.json_path.exists() or paths.markdown_path.exists())
    ):
        raise RuntimeError(
            "既に見どころ抽出結果が存在します。"
            "--overwrite で上書きするか、"
            "--append で続きを追加してください。"
        )

    metadata = load_project_metadata(project_dir)

    try:
        full_subtitles = paths.subtitles_path.read_text(encoding="utf-8")
    except OSError as error:
        raise RuntimeError(f"字幕を読み込めません: {paths.subtitles_path}") from error

    if not full_subtitles.strip():
        raise RuntimeError(f"字幕ファイルが空です: {paths.subtitles_path}")

    subtitle_start, subtitle_end = get_subtitle_bounds(full_subtitles)

    chunk_seconds = chunk_minutes * 60

    if append:
        state_start = load_highlight_state(paths.state_path)

        if state_start is not None:
            chunk_start = state_start
        else:
            # 旧バージョンとの互換性。
            # stateがまだない既存プロジェクトでは、
            # 既存候補の最後から続きを開始する。
            latest_end_time = get_latest_end_time(existing_highlights)

            if latest_end_time is not None:
                chunk_start = timestamp_to_seconds(latest_end_time)
            else:
                chunk_start = subtitle_start
    else:
        chunk_start = subtitle_start

    if chunk_start >= subtitle_end:
        raise RuntimeError("字幕の最後まで見どころ抽出済みです。")

    chunk_end = min(
        chunk_start + chunk_seconds,
        subtitle_end,
    )

    subtitles = trim_subtitles_range(
        full_subtitles,
        chunk_start,
        chunk_end,
    )

    if not subtitles.strip():
        raise RuntimeError("指定された時間範囲に字幕がありません。")

    console.print("[cyan]Geminiで見どころを抽出しています...[/cyan]")
    console.print(f"モデル: [bold]{model_name}[/bold]")
    console.print(f"字幕: {paths.subtitles_path}")

    if append:
        console.print(f"既存の見どころ候補: {len(existing_highlights)}件")
        console.print(f"追加生成する候補: 最大{max_highlights}件")
        console.print("モード: 追加生成")
    elif overwrite:
        console.print("モード: 上書き")
    else:
        console.print("モード: 新規生成")

    console.print(
        "[cyan]"
        f"抽出対象: "
        f"{seconds_to_timestamp(chunk_start)}"
        " ～ "
        f"{seconds_to_timestamp(chunk_end)}"
        f" ({chunk_minutes}分チャンク)"
        "[/cyan]"
    )

    prompt = build_highlight_prompt(
        metadata=metadata,
        subtitles=subtitles,
        max_highlights=max_highlights,
    )

    # ここでGeminiが429などで失敗した場合、
    # stateはまだ更新されない。
    parsed = generate_structured_content(
        model_name=model_name,
        prompt=prompt,
        response_model=HighlightResponse,
        temperature=0.3,
    )

    new_highlights = sorted(
        parsed.highlights,
        key=lambda item: timestamp_to_seconds(item.start_time),
    )[:max_highlights]

    # Geminiがチャンク外の時間を返した場合に備えて除外する。
    new_highlights = [
        item
        for item in new_highlights
        if (
            timestamp_to_seconds(item.start_time) >= chunk_start
            and timestamp_to_seconds(item.start_time) < chunk_end
        )
    ]

    if append:
        existing_ranges = {
            (
                item.start_time,
                item.end_time,
            )
            for item in existing_highlights
        }

        new_highlights = [
            item
            for item in new_highlights
            if (
                item.start_time,
                item.end_time,
            )
            not in existing_ranges
        ]

        highlights = existing_highlights + new_highlights
    else:
        highlights = new_highlights

    highlights = sorted(
        highlights,
        key=lambda item: timestamp_to_seconds(item.start_time),
    )

    result = HighlightResponse(highlights=highlights)

    try:
        paths.json_path.write_text(
            result.model_dump_json(indent=2),
            encoding="utf-8",
        )

        paths.markdown_path.write_text(
            create_markdown(highlights),
            encoding="utf-8",
        )
    except OSError as error:
        raise RuntimeError("見どころ抽出結果を書き込めません。") from error

    # JSON / Markdownの保存まで成功してから
    # 次回の開始地点を進める。
    save_highlight_state(
        paths.state_path,
        chunk_end,
    )

    console.print()
    console.print("[green bold]見どころ抽出が完了しました。[/green bold]")

    if append:
        console.print(f"追加: {len(new_highlights)}件")
        console.print(f"合計: {len(highlights)}件")
    else:
        console.print(f"生成: {len(highlights)}件")

    console.print(f"処理済み位置: {seconds_to_timestamp(chunk_end)}")
    console.print(f"JSON: {paths.json_path}")
    console.print(f"Markdown: {paths.markdown_path}")
    console.print(f"State: {paths.state_path}")

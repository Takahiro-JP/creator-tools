from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console

from anju.ai.client import generate_structured_content
from anju.ai.prompts import build_highlight_prompt
from anju.ai.schemas import HighlightItem, HighlightResponse

console = Console()


@dataclass(frozen=True)
class HighlightPaths:
    """見どころ抽出で使用するパス。"""

    project_dir: Path
    subtitles_path: Path
    clips_dir: Path
    json_path: Path
    markdown_path: Path


def resolve_highlight_paths(
    project_dir: Path,
) -> HighlightPaths:
    """見どころ抽出に必要なパスを解決する。"""
    project_dir = project_dir.expanduser().resolve()

    if not project_dir.is_dir():
        raise RuntimeError(f"プロジェクトフォルダが見つかりません: {project_dir}")

    metadata_path = project_dir / "metadata.json"

    if not metadata_path.is_file():
        raise RuntimeError(f"metadata.jsonが見つかりません: {metadata_path}")

    subtitles_path = project_dir / "subtitles" / "full.srt"

    if not subtitles_path.is_file():
        raise RuntimeError(
            "文字起こし結果が見つかりません。\n"
            f"{subtitles_path}\n"
            "先に anju transcribe を実行してください。"
        )

    clips_dir = project_dir / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    return HighlightPaths(
        project_dir=project_dir,
        subtitles_path=subtitles_path,
        clips_dir=clips_dir,
        json_path=clips_dir / "highlights.json",
        markdown_path=clips_dir / "highlights.md",
    )


def load_project_metadata(
    project_dir: Path,
) -> dict[str, Any]:
    """metadata.jsonを読み込む。"""
    metadata_path = project_dir / "metadata.json"

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise RuntimeError(f"metadata.jsonを読み込めません: {metadata_path}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(
            f"metadata.jsonのJSON形式が不正です: {metadata_path}"
        ) from error

    if not isinstance(metadata, dict):
        raise RuntimeError(f"metadata.jsonの内容が不正です: {metadata_path}")

    return metadata


def create_markdown(
    highlights: list[HighlightItem],
) -> str:
    """見どころ一覧のMarkdownを作成する。"""
    lines = [
        "# Highlight Candidates",
        "",
    ]

    for index, item in enumerate(highlights, start=1):
        lines.extend(
            [
                f"## {index}. {item.title}",
                "",
                f"- 時間: `{item.start_time}` ～ `{item.end_time}`",
                f"- スコア: `{item.score}`",
                f"- 要約: {item.summary}",
                f"- 選定理由: {item.reason}",
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
) -> None:
    """字幕からGeminiで見どころ候補を抽出する。"""
    if max_highlights < 1:
        raise ValueError("max_highlightsは1以上にしてください。")

    paths = resolve_highlight_paths(project_dir)

    if not overwrite:
        existing = [
            path
            for path in (
                paths.json_path,
                paths.markdown_path,
            )
            if path.exists()
        ]

        if existing:
            files = "\n".join(str(path) for path in existing)

            raise RuntimeError(
                "見どころ抽出結果がすでに存在します。\n"
                f"{files}\n"
                "--overwrite を付けると上書きできます。"
            )

    metadata = load_project_metadata(paths.project_dir)

    try:
        subtitles = paths.subtitles_path.read_text(encoding="utf-8")
    except OSError as error:
        raise RuntimeError(
            f"字幕ファイルを読み込めません: {paths.subtitles_path}"
        ) from error

    if not subtitles.strip():
        raise RuntimeError(f"字幕ファイルが空です: {paths.subtitles_path}")

    prompt = build_highlight_prompt(
        metadata=metadata,
        subtitles=subtitles,
        max_highlights=max_highlights,
    )

    console.print("[cyan]Geminiで見どころを抽出しています...[/cyan]")
    console.print(f"モデル: {model_name}")
    console.print(f"字幕: {paths.subtitles_path}")
    console.print()

    parsed = generate_structured_content(
        model_name=model_name,
        prompt=prompt,
        response_model=HighlightResponse,
        temperature=0.3,
    )

    highlights = sorted(
        parsed.highlights,
        key=lambda item: item.score,
        reverse=True,
    )[:max_highlights]

    if not highlights:
        raise RuntimeError("見どころ候補が生成されませんでした。")

    output = {
        "model": model_name,
        "source_subtitles": str(paths.subtitles_path),
        "highlights": [item.model_dump() for item in highlights],
    }

    paths.json_path.write_text(
        json.dumps(
            output,
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    paths.markdown_path.write_text(
        create_markdown(highlights),
        encoding="utf-8",
    )

    console.print("[bold green]見どころ抽出が完了しました。[/bold green]")
    console.print(paths.json_path)
    console.print(paths.markdown_path)

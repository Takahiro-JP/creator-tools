from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rich.console import Console

from anju.ai.client import generate_structured_content
from anju.ai.prompts import build_thumbnail_prompt
from anju.ai.schemas import ThumbnailIdea, ThumbnailResponse

console = Console()


@dataclass(frozen=True)
class ThumbnailPaths:
    """サムネイル案生成で使用するパス。"""

    project_dir: Path
    metadata_path: Path
    highlights_path: Path
    output_dir: Path
    json_path: Path
    markdown_path: Path


def resolve_thumbnail_paths(
    project_dir: Path,
) -> ThumbnailPaths:
    """サムネイル案生成に必要なパスを解決する。"""
    project_dir = project_dir.expanduser().resolve()

    if not project_dir.is_dir():
        raise RuntimeError(f"プロジェクトフォルダが見つかりません: {project_dir}")

    metadata_path = project_dir / "metadata.json"

    if not metadata_path.is_file():
        raise RuntimeError(f"metadata.jsonが見つかりません: {metadata_path}")

    highlights_path = project_dir / "clips" / "highlights.json"

    if not highlights_path.is_file():
        raise RuntimeError(
            "highlights.jsonが見つかりません。\n"
            f"{highlights_path}\n"
            "先に anju highlight を実行してください。"
        )

    output_dir = project_dir / "thumbnail"
    output_dir.mkdir(parents=True, exist_ok=True)

    return ThumbnailPaths(
        project_dir=project_dir,
        metadata_path=metadata_path,
        highlights_path=highlights_path,
        output_dir=output_dir,
        json_path=output_dir / "ideas.json",
        markdown_path=output_dir / "ideas.md",
    )


def load_json_object(path: Path) -> dict[str, Any]:
    """JSONファイルを辞書として読み込む。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise RuntimeError(f"ファイルを読み込めません: {path}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"JSON形式が不正です: {path}") from error

    if not isinstance(data, dict):
        raise RuntimeError(f"JSONの内容がオブジェクトではありません: {path}")

    return data


def normalize_highlights(
    data: dict[str, Any],
) -> list[dict[str, Any]]:
    """highlights.jsonから見どころ一覧を取得する。"""
    highlights = data.get("highlights")

    if not isinstance(highlights, list):
        raise RuntimeError("highlights.jsonにhighlights配列がありません。")

    normalized: list[dict[str, Any]] = []

    for index, item in enumerate(highlights, start=1):
        if not isinstance(item, dict):
            continue

        normalized.append(
            {
                "clip_index": index,
                "title": str(item.get("title") or "Untitled"),
                "summary": str(item.get("summary") or ""),
                "reason": str(item.get("reason") or ""),
                "score": item.get("score"),
                "start_time": str(item.get("start_time") or ""),
                "end_time": str(item.get("end_time") or ""),
            }
        )

    if not normalized:
        raise RuntimeError("有効な見どころ候補がありません。")

    return normalized


def create_thumbnail_markdown(
    ideas: list[ThumbnailIdea],
) -> str:
    """サムネイル案一覧のMarkdownを作成する。"""
    lines = [
        "# Thumbnail Ideas",
        "",
    ]

    for idea in ideas:
        lines.extend(
            [
                f"## Clip {idea.clip_index}: {idea.clip_title}",
                "",
                "### Main Text",
                "",
                idea.main_text,
                "",
                "### Sub Text",
                "",
                idea.sub_text or "なし",
                "",
                "### Emotion",
                "",
                idea.emotion,
                "",
                "### Composition",
                "",
                idea.composition,
                "",
                "### Color Palette",
                "",
            ]
        )

        lines.extend(f"- {color}" for color in idea.color_palette)

        lines.extend(
            [
                "",
                "### Visual Notes",
                "",
            ]
        )

        lines.extend(f"- {note}" for note in idea.visual_notes)

        lines.extend(
            [
                "",
                "### Reason",
                "",
                idea.reason,
                "",
            ]
        )

    return "\n".join(lines)


def generate_thumbnail_ideas(
    project_dir: Path,
    *,
    model_name: str = "gemini-2.5-flash",
    overwrite: bool = False,
) -> None:
    """見どころ情報からサムネイル案を生成する。"""
    paths = resolve_thumbnail_paths(project_dir)

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
                "サムネイル案がすでに存在します。\n"
                f"{files}\n"
                "--overwrite を付けると上書きできます。"
            )

    metadata = load_json_object(paths.metadata_path)
    highlights_data = load_json_object(paths.highlights_path)
    highlights = normalize_highlights(highlights_data)

    prompt = build_thumbnail_prompt(
        metadata=metadata,
        highlights=highlights,
    )

    console.print("[cyan]Geminiでサムネイル案を生成しています...[/cyan]")
    console.print(f"モデル: {model_name}")
    console.print(f"見どころ件数: {len(highlights)}")
    console.print()

    response = generate_structured_content(
        model_name=model_name,
        prompt=prompt,
        response_model=ThumbnailResponse,
        temperature=0.5,
    )

    ideas = sorted(
        response.ideas,
        key=lambda item: item.clip_index,
    )

    if not ideas:
        raise RuntimeError("サムネイル案が生成されませんでした。")

    output = {
        "model": model_name,
        "source_highlights": str(paths.highlights_path),
        "ideas": [item.model_dump() for item in ideas],
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
        create_thumbnail_markdown(ideas),
        encoding="utf-8",
    )

    console.print("[bold green]サムネイル案の生成が完了しました。[/bold green]")
    console.print(paths.json_path)
    console.print(paths.markdown_path)

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from rich.console import Console

console = Console()


class HighlightResponse(BaseModel):
    """Geminiから受け取る見どころ候補一覧。"""

    highlights: list[HighlightItem]


class HighlightItem(BaseModel):
    """Geminiから受け取る見どころ候補。"""

    start_time: str = Field(description="開始時刻。HH:MM:SS形式")
    end_time: str = Field(description="終了時刻。HH:MM:SS形式")
    title: str = Field(description="短い見どころタイトル")
    summary: str = Field(description="何が面白いのかを説明する短い要約")
    reason: str = Field(description="切り抜き候補として選んだ理由")
    score: int = Field(ge=1, le=100, description="見どころとしての評価。1から100")


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


def build_prompt(
    *,
    metadata: dict[str, Any],
    subtitles: str,
    max_highlights: int,
) -> str:
    """Geminiへ送信するプロンプトを作成する。"""
    title = metadata.get("title") or "不明"
    uploader = metadata.get("uploader") or "不明"

    return f"""
あなたはゲーム配信の切り抜き動画を企画する編集者です。

以下はTwitch配信のSRT字幕です。
YouTubeの横動画またはショート動画に向く見どころを、
最大{max_highlights}件選んでください。

配信者: {uploader}
配信タイトル: {title}

選定基準:
- 驚き、悲鳴、笑い、失敗、予想外の出来事
- 視聴者が状況を理解しやすい
- 前後を含めて30秒から120秒程度で成立する
- 同じ場面を重複して選ばない
- 内容が薄い場面は無理に選ばない
- 開始時刻と終了時刻はSRTの時間を根拠にする
- 前後の文脈が必要なら少し広めに時間を取る
- 日本語で回答する

SRT字幕:
{subtitles}
""".strip()


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
    api_key = os.environ.get("GEMINI_API_KEY")

    if not api_key:
        raise RuntimeError("GEMINI_API_KEYが設定されていません。")

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
    subtitles = paths.subtitles_path.read_text(encoding="utf-8")

    if not subtitles.strip():
        raise RuntimeError(f"字幕ファイルが空です: {paths.subtitles_path}")

    prompt = build_prompt(
        metadata=metadata,
        subtitles=subtitles,
        max_highlights=max_highlights,
    )

    console.print("[cyan]Geminiで見どころを抽出しています...[/cyan]")
    console.print(f"モデル: {model_name}")
    console.print(f"字幕: {paths.subtitles_path}")
    console.print()

    client = genai.Client(api_key=api_key)

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.3,
                response_mime_type="application/json",
                response_schema=HighlightResponse,
            ),
        )
    except Exception as error:
        raise RuntimeError(f"Gemini APIの呼び出しに失敗しました: {error}") from error

    parsed = response.parsed

    if not isinstance(parsed, HighlightResponse):
        raise RuntimeError("Geminiの応答を解析できませんでした。")

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

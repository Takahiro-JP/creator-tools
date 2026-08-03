from pathlib import Path

import pytest

from anju.ai.prompts import build_highlight_prompt
from anju.ai.schemas import HighlightItem
from anju.highlighter import (
    create_markdown,
    resolve_highlight_paths,
)


def test_resolve_highlight_paths(
    tmp_path: Path,
) -> None:
    (tmp_path / "metadata.json").write_text(
        "{}",
        encoding="utf-8",
    )

    subtitles_dir = tmp_path / "subtitles"
    subtitles_dir.mkdir()

    (subtitles_dir / "full.srt").write_text(
        "1\n00:00:00,000 --> 00:00:02,000\nテスト\n",
        encoding="utf-8",
    )

    paths = resolve_highlight_paths(tmp_path)

    assert paths.subtitles_path.exists()
    assert paths.clips_dir.exists()
    assert paths.json_path.name == "highlights.json"
    assert paths.markdown_path.name == "highlights.md"


def test_resolve_highlight_paths_without_srt(
    tmp_path: Path,
) -> None:
    (tmp_path / "metadata.json").write_text(
        "{}",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError):
        resolve_highlight_paths(tmp_path)


def test_build_prompt() -> None:
    prompt = build_highlight_prompt(
        metadata={
            "title": "Test title",
            "uploader": "Test uploader",
        },
        subtitles="字幕本文",
        max_highlights=5,
    )

    assert "Test title" in prompt
    assert "Test uploader" in prompt
    assert "最大5件" in prompt
    assert "字幕本文" in prompt


def test_create_markdown() -> None:
    item = HighlightItem(
        start_time="00:01:00",
        end_time="00:02:00",
        title="テスト場面",
        summary="面白い場面",
        reason="リアクションが大きい",
        score=90,
    )

    markdown = create_markdown([item])

    assert "テスト場面" in markdown
    assert "00:01:00" in markdown
    assert "90" in markdown

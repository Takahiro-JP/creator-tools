from pathlib import Path

import pytest

from anju.ai.schemas import ThumbnailIdea
from anju.thumbnail import (
    create_thumbnail_markdown,
    normalize_highlights,
    resolve_thumbnail_paths,
)


def test_resolve_thumbnail_paths(
    tmp_path: Path,
) -> None:
    (tmp_path / "metadata.json").write_text(
        "{}",
        encoding="utf-8",
    )

    clips_dir = tmp_path / "clips"
    clips_dir.mkdir()

    (clips_dir / "highlights.json").write_text(
        '{"highlights": []}',
        encoding="utf-8",
    )

    paths = resolve_thumbnail_paths(tmp_path)

    assert paths.output_dir.exists()
    assert paths.json_path.name == "ideas.json"
    assert paths.markdown_path.name == "ideas.md"


def test_resolve_thumbnail_paths_without_highlights(
    tmp_path: Path,
) -> None:
    (tmp_path / "metadata.json").write_text(
        "{}",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError):
        resolve_thumbnail_paths(tmp_path)


def test_normalize_highlights() -> None:
    highlights = normalize_highlights(
        {
            "highlights": [
                {
                    "title": "テスト場面",
                    "summary": "驚いた場面",
                    "reason": "反応が大きい",
                    "score": 90,
                    "start_time": "00:01:00",
                    "end_time": "00:01:30",
                }
            ]
        }
    )

    assert len(highlights) == 1
    assert highlights[0]["clip_index"] == 1
    assert highlights[0]["title"] == "テスト場面"


def test_normalize_highlights_missing() -> None:
    with pytest.raises(RuntimeError):
        normalize_highlights({})


def test_create_thumbnail_markdown() -> None:
    idea = ThumbnailIdea(
        clip_index=1,
        clip_title="テスト場面",
        main_text="怖すぎる！",
        sub_text="逃げ場なし",
        emotion="panic",
        composition="人物を左、敵を右に配置",
        color_palette=["yellow", "red"],
        visual_notes=[
            "背景を暗くする",
            "文字を大きくする",
        ],
        reason="状況と感情が一目で伝わる",
    )

    markdown = create_thumbnail_markdown([idea])

    assert "テスト場面" in markdown
    assert "怖すぎる！" in markdown
    assert "yellow" in markdown
    assert "状況と感情が一目で伝わる" in markdown

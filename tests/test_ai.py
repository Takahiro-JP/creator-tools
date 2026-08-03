from anju.ai.prompts import (
    build_highlight_prompt,
    build_thumbnail_prompt,
)


def test_build_highlight_prompt() -> None:
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


def test_build_thumbnail_prompt() -> None:
    prompt = build_thumbnail_prompt(
        metadata={
            "title": "Test title",
            "uploader": "Test uploader",
        },
        highlights=[
            {
                "clip_index": 1,
                "title": "驚いた場面",
            }
        ],
    )

    assert "Test title" in prompt
    assert "Test uploader" in prompt
    assert "驚いた場面" in prompt

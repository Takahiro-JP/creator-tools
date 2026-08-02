import json
from pathlib import Path

import pytest

from anju.clipgen import (
    build_output_path,
    load_clips,
    parse_timestamp,
)


def test_parse_timestamp() -> None:
    assert parse_timestamp("00:00:10") == 10
    assert parse_timestamp("00:01:30") == 90
    assert parse_timestamp("01:02:03.5") == 3723.5


def test_parse_timestamp_invalid() -> None:
    with pytest.raises(ValueError):
        parse_timestamp("1:2:3")


def test_load_clips(tmp_path: Path) -> None:
    path = tmp_path / "highlights.json"

    path.write_text(
        json.dumps(
            {
                "highlights": [
                    {
                        "title": "テスト",
                        "start_time": "00:01:00",
                        "end_time": "00:01:30",
                        "score": 95,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    clips = load_clips(path)

    assert len(clips) == 1
    assert clips[0].duration == 30
    assert clips[0].score == 95


def test_build_output_path(tmp_path: Path) -> None:
    clips_path = tmp_path / "clips"

    clip_path = build_output_path(
        clips_path,
        load_clips_from_data(tmp_path)[0],
    )

    assert clip_path.name == "001_095_テスト.mp4"


def load_clips_from_data(tmp_path: Path):
    path = tmp_path / "highlights.json"

    path.write_text(
        json.dumps(
            {
                "highlights": [
                    {
                        "title": "テスト",
                        "start_time": "00:01:00",
                        "end_time": "00:01:30",
                        "score": 95,
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    return load_clips(path)

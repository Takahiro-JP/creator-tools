from pathlib import Path

import pytest

from anju.transcriber import (
    find_source_video,
    format_srt_timestamp,
)


def test_format_srt_timestamp() -> None:
    assert format_srt_timestamp(0) == "00:00:00,000"
    assert format_srt_timestamp(65.432) == "00:01:05,432"
    assert format_srt_timestamp(3661.001) == "01:01:01,001"


def test_find_source_video(tmp_path: Path) -> None:
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()

    video = raw_dir / "source.mp4"
    video.touch()

    assert find_source_video(tmp_path) == video


def test_find_source_video_missing(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError):
        find_source_video(tmp_path)

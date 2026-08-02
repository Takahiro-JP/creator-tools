from pathlib import Path

from anju.subtitle_burner import (
    escape_subtitle_filter_path,
    find_subtitle_pairs,
)


def test_escape_subtitle_filter_path(
    tmp_path: Path,
) -> None:
    path = tmp_path / "test:file.srt"

    escaped = escape_subtitle_filter_path(path)

    assert r"\:" in escaped


def test_find_subtitle_pairs(
    tmp_path: Path,
) -> None:
    clips_dir = tmp_path / "clips"
    clips_dir.mkdir()

    video = clips_dir / "001_test.mp4"
    subtitle = clips_dir / "001_test.srt"

    video.touch()
    subtitle.touch()

    pairs = find_subtitle_pairs(tmp_path)

    assert len(pairs) == 1
    assert pairs[0].video_path == video
    assert pairs[0].subtitle_path == subtitle
    assert pairs[0].output_path.name == ("001_test_subtitled.mp4")


def test_ignore_video_without_subtitle(
    tmp_path: Path,
) -> None:
    clips_dir = tmp_path / "clips"
    clips_dir.mkdir()

    (clips_dir / "001_test.mp4").touch()

    assert find_subtitle_pairs(tmp_path) == []

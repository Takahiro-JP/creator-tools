from anju.clipgen import Clip
from anju.subtitle import (
    SubtitleEntry,
    extract_clip_subtitles,
    format_srt_timestamp,
    parse_srt,
    parse_srt_timestamp,
    render_srt,
)


def test_parse_srt_timestamp() -> None:
    assert parse_srt_timestamp("00:00:10,500") == 10.5
    assert parse_srt_timestamp("01:02:03,250") == 3723.25


def test_format_srt_timestamp() -> None:
    assert format_srt_timestamp(0) == "00:00:00,000"
    assert format_srt_timestamp(65.432) == "00:01:05,432"


def test_parse_srt() -> None:
    content = """1
00:00:10,000 --> 00:00:12,000
テスト字幕

2
00:00:13,000 --> 00:00:15,000
次の字幕
"""

    entries = parse_srt(content)

    assert len(entries) == 2
    assert entries[0].text == "テスト字幕"
    assert entries[1].start == 13


def test_extract_clip_subtitles() -> None:
    entries = [
        SubtitleEntry(
            start=10,
            end=12,
            text="最初",
        ),
        SubtitleEntry(
            start=14,
            end=16,
            text="次",
        ),
    ]

    clip = Clip(
        index=1,
        title="テスト",
        start_time="00:00:11",
        end_time="00:00:15",
        score=90,
    )

    extracted = extract_clip_subtitles(entries, clip)

    assert len(extracted) == 2
    assert extracted[0].start == 0
    assert extracted[0].end == 1
    assert extracted[1].start == 3
    assert extracted[1].end == 4


def test_render_srt() -> None:
    content = render_srt(
        [
            SubtitleEntry(
                start=0,
                end=2.5,
                text="テスト",
            )
        ]
    )

    assert "00:00:00,000 --> 00:00:02,500" in content
    assert "テスト" in content

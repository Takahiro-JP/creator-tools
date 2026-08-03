from pathlib import Path
from types import SimpleNamespace

from anju.pipeline import run_pipeline


def test_run_pipeline(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_dir = tmp_path / "project"

    for directory in (
        project_dir / "raw",
        project_dir / "subtitles",
        project_dir / "clips",
        project_dir / "thumbnail",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    calls: list[str] = []

    monkeypatch.setattr(
        "anju.pipeline.download_video",
        lambda url, overwrite=False: SimpleNamespace(root_dir=project_dir),
    )

    monkeypatch.setattr(
        "anju.pipeline.transcribe_project",
        lambda *args, **kwargs: calls.append("transcribe"),
    )
    monkeypatch.setattr(
        "anju.pipeline.highlight_project",
        lambda *args, **kwargs: calls.append("highlight"),
    )
    monkeypatch.setattr(
        "anju.pipeline.generate_project_clips",
        lambda *args, **kwargs: calls.append("clipgen"),
    )
    monkeypatch.setattr(
        "anju.pipeline.generate_clip_subtitles",
        lambda *args, **kwargs: calls.append("subtitle"),
    )
    monkeypatch.setattr(
        "anju.pipeline.burn_project_subtitles",
        lambda *args, **kwargs: calls.append("burn"),
    )
    monkeypatch.setattr(
        "anju.pipeline.generate_thumbnail_ideas",
        lambda *args, **kwargs: calls.append("thumbnail"),
    )

    report = run_pipeline(
        "https://www.twitch.tv/videos/123456789",
    )

    assert calls == [
        "transcribe",
        "highlight",
        "clipgen",
        "subtitle",
        "burn",
        "thumbnail",
    ]

    assert report.project_dir == project_dir
    assert "Download" in report.completed


def test_pipeline_can_skip_burn_subtitle(
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_dir = tmp_path / "project"

    for directory in (
        project_dir / "raw",
        project_dir / "subtitles",
        project_dir / "clips",
        project_dir / "thumbnail",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    calls: list[str] = []

    monkeypatch.setattr(
        "anju.pipeline.download_video",
        lambda url, overwrite=False: SimpleNamespace(root_dir=project_dir),
    )

    for target in (
        "transcribe_project",
        "highlight_project",
        "generate_project_clips",
        "generate_clip_subtitles",
        "generate_thumbnail_ideas",
    ):
        monkeypatch.setattr(
            f"anju.pipeline.{target}",
            lambda *args, **kwargs: None,
        )

    monkeypatch.setattr(
        "anju.pipeline.burn_project_subtitles",
        lambda *args, **kwargs: calls.append("burn"),
    )

    report = run_pipeline(
        "https://www.twitch.tv/videos/123456789",
        skip_burn_subtitle=True,
    )

    assert calls == []
    assert "Subtitle Burn-in" in report.skipped

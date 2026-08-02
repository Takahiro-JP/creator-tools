from pathlib import Path

from anju.project import Project, ProjectMetadata


def test_project_create(
    tmp_path: Path,
) -> None:
    project = Project.create(
        base_dir=tmp_path,
        date_text="2026-06-22",
        video_id="2803053225",
    )

    assert project.root_dir.exists()
    assert project.raw_dir.exists()
    assert project.clips_dir.exists()
    assert project.subtitles_dir.exists()
    assert project.thumbnail_dir.exists()
    assert project.exports_dir.exists()
    assert project.davinci_dir.exists()


def test_save_metadata(
    tmp_path: Path,
) -> None:
    project = Project.create(
        base_dir=tmp_path,
        date_text="2026-06-22",
        video_id="2803053225",
    )

    metadata = ProjectMetadata.create(
        video_id="2803053225",
        source_url=("https://www.twitch.tv/videos/2803053225"),
        title="Test title",
        uploader="Test uploader",
        upload_date="2026-06-22",
        duration=120,
    )

    project.save_metadata(metadata)

    content = project.metadata_path.read_text(encoding="utf-8")

    assert '"video_id": "2803053225"' in content
    assert '"duration": 120.0' in content

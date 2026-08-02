from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ProjectMetadata:
    """動画プロジェクトの基本情報。"""

    project_version: int
    video_id: str
    source_url: str
    title: str
    uploader: str
    upload_date: str
    duration: float | None
    created_at: str
    updated_at: str

    @classmethod
    def create(
        cls,
        *,
        video_id: str,
        source_url: str,
        title: str,
        uploader: str,
        upload_date: str,
        duration: Any,
    ) -> ProjectMetadata:
        """動画情報から新しいメタデータを作成する。"""
        now = datetime.now().astimezone().isoformat(timespec="seconds")

        parsed_duration: float | None

        try:
            parsed_duration = float(duration) if duration is not None else None
        except (TypeError, ValueError):
            parsed_duration = None

        return cls(
            project_version=1,
            video_id=video_id,
            source_url=source_url,
            title=title,
            uploader=uploader,
            upload_date=upload_date,
            duration=parsed_duration,
            created_at=now,
            updated_at=now,
        )


@dataclass(frozen=True)
class Project:
    """1本の配信動画に対応する作業プロジェクト。"""

    root_dir: Path
    raw_dir: Path
    clips_dir: Path
    subtitles_dir: Path
    thumbnail_dir: Path
    exports_dir: Path
    davinci_dir: Path
    metadata_path: Path

    @classmethod
    def create(
        cls,
        *,
        base_dir: Path,
        date_text: str,
        video_id: str,
    ) -> Project:
        """プロジェクト用フォルダを作成する。"""
        root_dir = base_dir / date_text / video_id

        project = cls(
            root_dir=root_dir,
            raw_dir=root_dir / "raw",
            clips_dir=root_dir / "clips",
            subtitles_dir=root_dir / "subtitles",
            thumbnail_dir=root_dir / "thumbnail",
            exports_dir=root_dir / "exports",
            davinci_dir=root_dir / "project",
            metadata_path=root_dir / "metadata.json",
        )

        project.create_directories()

        return project

    def create_directories(self) -> None:
        """プロジェクト内の作業フォルダを作成する。"""
        directories = (
            self.root_dir,
            self.raw_dir,
            self.clips_dir,
            self.subtitles_dir,
            self.thumbnail_dir,
            self.exports_dir,
            self.davinci_dir,
        )

        for directory in directories:
            directory.mkdir(
                parents=True,
                exist_ok=True,
            )

    def save_metadata(
        self,
        metadata: ProjectMetadata,
    ) -> None:
        """metadata.jsonを保存する。"""
        self.metadata_path.write_text(
            json.dumps(
                asdict(metadata),
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

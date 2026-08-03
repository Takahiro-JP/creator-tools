from __future__ import annotations

from pydantic import BaseModel, Field


class HighlightItem(BaseModel):
    """Geminiが生成する見どころ候補。"""

    start_time: str = Field(description="開始時刻。HH:MM:SS形式")
    end_time: str = Field(description="終了時刻。HH:MM:SS形式")
    title: str = Field(description="短い見どころタイトル")
    summary: str = Field(description="見どころの短い要約")
    reason: str = Field(description="切り抜き候補として選んだ理由")
    score: int = Field(ge=1, le=100, description="見どころとしての評価")


class HighlightResponse(BaseModel):
    """Geminiが生成する見どころ候補一覧。"""

    highlights: list[HighlightItem]


class ThumbnailIdea(BaseModel):
    """Geminiが生成するサムネイル案。"""

    clip_index: int = Field(
        ge=1,
        description="対象クリップの番号",
    )
    clip_title: str
    main_text: str = Field(
        description="サムネイルで最も目立たせる短い文言",
    )
    sub_text: str = Field(
        description="補助的な短い文言",
    )
    emotion: str = Field(
        description="伝える感情",
    )
    composition: str = Field(
        description="人物、敵、背景、文字の配置案",
    )
    color_palette: list[str] = Field(
        description="推奨する色の一覧",
    )
    visual_notes: list[str] = Field(
        description="画像編集時の注意点",
    )
    reason: str = Field(
        description="クリックされやすいと考える理由",
    )


class ThumbnailResponse(BaseModel):
    """Geminiが生成するサムネイル案一覧。"""

    ideas: list[ThumbnailIdea]

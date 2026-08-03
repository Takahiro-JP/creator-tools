from __future__ import annotations

from typing import Any


def build_highlight_prompt(
    *,
    metadata: dict[str, Any],
    subtitles: str,
    max_highlights: int,
) -> str:
    """見どころ抽出用プロンプトを作成する。"""
    title = metadata.get("title") or "不明"
    uploader = metadata.get("uploader") or "不明"

    return f"""
あなたはゲーム配信の切り抜き動画を企画する編集者です。

以下はTwitch配信のSRT字幕です。
YouTubeの横動画またはショート動画に向く見どころを、
最大{max_highlights}件選んでください。

配信者: {uploader}
配信タイトル: {title}

選定基準:
- 驚き、悲鳴、笑い、失敗、予想外の出来事
- 視聴者が状況を理解しやすい
- 前後を含めて30秒から120秒程度で成立する
- 同じ場面を重複して選ばない
- 内容が薄い場面は無理に選ばない
- 開始時刻と終了時刻はSRTを根拠にする
- 必要なら前後の文脈を少し広めに含める
- 日本語で回答する

SRT字幕:
{subtitles}
""".strip()


def build_thumbnail_prompt(
    *,
    metadata: dict[str, Any],
    highlights: list[dict[str, Any]],
) -> str:
    """サムネイル案生成用プロンプトを作成する。"""
    title = metadata.get("title") or "不明"
    uploader = metadata.get("uploader") or "不明"

    return f"""
あなたはYouTubeのゲーム動画に詳しいサムネイルデザイナーです。

各見どころについて、内容を誇張しすぎず、
一目で状況と感情が伝わるサムネイル案を作成してください。

配信者: {uploader}
配信タイトル: {title}

要件:
- main_textは短く、読みやすい日本語にする
- sub_textは必要最低限にする
- 文字を多くしすぎない
- 強い感情や状況が伝わる構図にする
- 背景、人物、敵、文字の配置を具体的に示す
- 推奨色を具体的に示す
- 既存キャラクターの見た目を過度に変更しない
- 各案がどのクリップに対応するか明記する

見どころ一覧:
{highlights}
""".strip()

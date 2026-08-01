# creator-tools

AI-powered CLI toolkit for content creators.

Twitch動画のダウンロード、文字起こし、見どころ抽出、切り抜き生成などを自動化するためのCLIツールです。

## Planned features

- Twitch VOD download
- Date-based project organization
- Whisper transcription
- Gemini highlight detection
- Automatic clip generation with ffmpeg
- DaVinci Resolve workflow support

## Requirements

- Python 3.11 or newer
- yt-dlp
- ffmpeg
- TwitchDownloaderCLI

## Development setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"




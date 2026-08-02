# Creator Tools

> AI-powered CLI toolkit for content creators.

Creator Tools automates repetitive video production tasks such as Twitch VOD downloading, transcription, AI-powered highlight detection, clip generation, and subtitle processing.

The goal is to let creators spend more time creating content and less time on repetitive editing tasks.

## Why Creator Tools?

Video editing involves many repetitive tasks:
downloading VODs, transcription, highlight selection,
clip creation, subtitle generation, and publishing.

Creator Tools automates these repetitive workflows with AI,
allowing creators to focus on creating content instead of manual editing.

## ✨ Features

- 🎬 Download Twitch VODs
- 📁 Automatic project organization
- 🎙️ Whisper transcription
- 🤖 Gemini highlight detection
- ✂️ Automatic clip generation
- 💬 Clip subtitle generation
- 🔥 Burn subtitles into videos
- ✅ GitHub Actions CI
- 🧹 pre-commit hooks

## Workflow

```text
Twitch VOD
     │
     ▼
download
     ▼
transcribe (Whisper)
     ▼
highlight (Gemini)
     ▼
clipgen (FFmpeg)
     ▼
subtitle
     ▼
burn-subtitle
```

## Installation

```bash
git clone https://github.com/Takahiro-JP/creator-tools.git

cd creator-tools

python -m venv .venv

source .venv/bin/activate

python -m pip install -e ".[dev]"
```

## Quick Start

```bash
anju doctor

anju download https://www.twitch.tv/videos/123456789

anju transcribe PROJECT

anju highlight PROJECT

anju clipgen PROJECT

anju subtitle PROJECT

anju burn-subtitle PROJECT
```

## Commands

| Command         | Description                      |
| --------------- | -------------------------------- |
| `doctor`        | Check environment                |
| `config`        | Show configuration               |
| `download`      | Download Twitch VOD              |
| `transcribe`    | Generate transcript with Whisper |
| `highlight`     | Detect highlights using Gemini   |
| `clipgen`       | Generate video clips             |
| `subtitle`      | Generate clip subtitles          |
| `burn-subtitle` | Burn subtitles into clips        |

## Project Structure

```
creator-tools/

.github/
docs/
tests/

src/
└── anju/
    ├── commands/
    ├── downloader.py
    ├── transcriber.py
    ├── highlighter.py
    ├── clipgen.py
    ├── subtitle.py
    └── subtitle_burner.py
```

## Development

```bash
pre-commit run --all-files

pytest
```

## Roadmap

v0.2
* ✅ Download
* ✅ Whisper
* ✅ Gemini
* ✅ Clip generation
* ✅ Subtitle generation

### v0.3

- Thumbnail suggestions
- YouTube title and description generation
- Improved project management

### v0.4

- Automatic YouTube upload
- DaVinci Resolve integration

### v1.0

Complete AI-powered workflow for content creators.
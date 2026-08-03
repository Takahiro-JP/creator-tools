# Creator Tools

> AI-powered CLI toolkit for content creators.

![Creator Tools Pipeline](docs/images/pipeline-demo.png)

Creator Tools automates repetitive video production tasks for creators.

Starting from a Twitch VOD, it can download the source video, transcribe audio, detect highlights with AI, generate clips, create subtitles, burn subtitles into videos, and suggest thumbnail ideas.

Run the complete workflow with a single command:

```bash
anju pipeline https://www.twitch.tv/videos/123456789
```

The goal is simple:

> Spend more time creating content and less time editing.

## ✨ Features

- 🎬 Twitch VOD download
- 📁 Automatic project organization
- 🎙 Whisper transcription
- 🤖 Gemini highlight detection
- ✂ Automatic clip generation with FFmpeg
- 💬 Clip-specific subtitle generation
- 🔥 Subtitle burn-in
- 🖼 Thumbnail idea generation
- 🚀 End-to-end pipeline
- ✅ GitHub Actions CI
- 🧹 pre-commit hooks
- 🧪 Pytest test suite

## Workflow

```text
            Twitch VOD
                 │
                 ▼
          anju pipeline
                 │
                 ▼
            Download
                 │
                 ▼
     Transcription (Whisper)
                 │
                 ▼
 Highlight Detection (Gemini)
                 │
                 ▼
   Clip Generation (FFmpeg)
                 │
                 ▼
      Subtitle Generation
                 │
                 ▼
        Subtitle Burn-in
                 │
                 ▼
 Thumbnail Idea Generation
```

## Requirements

- Python 3.13
- yt-dlp
- FFmpeg
- TwitchDownloaderCLI
- Gemini API key

## Installation

Clone the repository:

```bash
git clone git@github.com:Takahiro-JP/creator-tools.git
cd creator-tools
```

Create and activate a virtual environment:

```bash
python3.13 -m venv .venv
source .venv/bin/activate
```

Install the project and development tools:

```bash
python -m pip install -e ".[dev]"
```

## Configuration

The configuration file is created at:

```text
~/.anju/config.json
```

Example for macOS:

```json
{
  "base_dir": "/Users/your-name/Movies/anju",
  "twitch_downloader_cli": "/Users/your-name/Tools/TwitchDownloader/TwitchDownloaderCLI"
}
```

Set the Gemini API key:

```bash
export GEMINI_API_KEY="your-api-key"
```

To persist it on macOS:

```bash
echo 'export GEMINI_API_KEY="your-api-key"' >> ~/.zshrc
source ~/.zshrc
```

Do not commit your API key to Git.

## Quick Start

Check the environment:

```bash
anju doctor
```

Run the complete workflow:

```bash
anju pipeline \
  "https://www.twitch.tv/videos/123456789"
```

Run a smaller test pipeline:

```bash
anju pipeline \
  "https://www.twitch.tv/videos/123456789" \
  --whisper-model base \
  --max-highlights 3 \
  --clip-limit 1
```

Rebuild existing outputs:

```bash
anju pipeline \
  "https://www.twitch.tv/videos/123456789" \
  --overwrite
```

## Individual Commands

Each stage can also be executed independently.

```bash
anju download URL
anju transcribe PROJECT_DIR
anju highlight PROJECT_DIR
anju clipgen PROJECT_DIR
anju subtitle PROJECT_DIR
anju burn-subtitle PROJECT_DIR
anju thumbnail PROJECT_DIR
```

## Commands

| Command | Description |
|---|---|
| `anju doctor` | Check required tools and configuration |
| `anju config` | Display the current configuration |
| `anju download URL` | Download and organize a Twitch VOD |
| `anju transcribe PROJECT_DIR` | Generate `full.srt` and `full.txt` with Whisper |
| `anju highlight PROJECT_DIR` | Detect highlight candidates with Gemini |
| `anju clipgen PROJECT_DIR` | Generate MP4 clips with FFmpeg |
| `anju subtitle PROJECT_DIR` | Generate clip-specific SRT files |
| `anju burn-subtitle PROJECT_DIR` | Burn subtitles into generated clips |
| `anju thumbnail PROJECT_DIR` | Generate thumbnail design ideas |
| `anju pipeline URL` | Run the full creator workflow |

Use `--help` to view command-specific options:

```bash
anju pipeline --help
anju transcribe --help
anju highlight --help
```

## Generated Project

A downloaded Twitch VOD is organized into a project directory:

```text
~/Movies/anju/
└── 2026-06-22/
    └── 2803053225/
        ├── metadata.json
        ├── raw/
        │   └── source-video.mp4
        ├── subtitles/
        │   ├── full.srt
        │   └── full.txt
        ├── clips/
        │   ├── highlights.json
        │   ├── highlights.md
        │   ├── 001_095_example.mp4
        │   ├── 001_095_example.srt
        │   └── 001_095_example_subtitled.mp4
        ├── thumbnail/
        │   ├── ideas.json
        │   └── ideas.md
        ├── exports/
        └── project/
```

## Project Structure

```text
creator-tools/
├── .github/
│   └── workflows/
├── docs/
│   └── images/
├── src/
│   └── anju/
│       ├── ai/
│       │   ├── client.py
│       │   ├── prompts.py
│       │   └── schemas.py
│       ├── commands/
│       ├── cli.py
│       ├── clipgen.py
│       ├── config.py
│       ├── doctor.py
│       ├── downloader.py
│       ├── highlighter.py
│       ├── pipeline.py
│       ├── project.py
│       ├── subtitle.py
│       ├── subtitle_burner.py
│       ├── thumbnail.py
│       ├── transcriber.py
│       └── utils.py
├── tests/
├── CHANGELOG.md
├── README.md
└── pyproject.toml
```

## Development

Activate the virtual environment:

```bash
source .venv/bin/activate
```

Run every pre-commit check:

```bash
pre-commit run --all-files
```

Run tests:

```bash
pytest
```

Run Ruff manually:

```bash
ruff format --check src tests
ruff check src tests
```

Install the Git hook:

```bash
pre-commit install
```

## Roadmap

### v0.3

- ✅ Thumbnail idea generation
- ✅ End-to-end pipeline
- ✅ Improved pipeline summary

### v0.4

- 🎯 YouTube title generation
- 📝 Description generation
- 🏷 Hashtag generation
- ⏱ Chapter generation

### v0.5

- 📤 YouTube upload support
- 📅 Publish scheduling
- 📊 Analytics support

### v1.0

A complete AI-powered creator workflow:

```text
Twitch VOD
      │
      ▼
Creator Tools
      │
      ├── Download
      ├── Transcribe
      ├── Highlight Detection
      ├── Clip Generation
      ├── Subtitle Generation
      ├── Thumbnail Ideas
      ├── Title Ideas
      ├── Description
      ├── Hashtags
      └── Chapters
      │
      ▼
Creator Review
      │
      ▼
YouTube
```

## License

MIT
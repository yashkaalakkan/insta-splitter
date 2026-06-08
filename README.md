# 🎬 Instagram Video Splitter

Automatically cuts a long video into parts, adds a **"Part N"** text overlay to each clip, and posts them to Instagram as Reels — one by one, with a delay between each post.

**100% free. No developer token needed.**

---

## How It Works

```
your_video.mp4
      │
      ▼
  [ffmpeg] cuts into 60s clips
      │
      ▼
  [ffmpeg] burns "Part 1", "Part 2"... text onto each clip
      │
      ▼
  [instagrapi] logs into Instagram with your username/password
      │
      ▼
  Posts each clip as a Reel (with delay between posts)
```

---

## Quick Start (Local)

### 1. Install dependencies

```bash
# ffmpeg (video processing)
# macOS:
brew install ffmpeg

# Ubuntu/Debian:
sudo apt install ffmpeg

# Windows: download from https://ffmpeg.org/download.html

# Python library for Instagram
pip install -r requirements.txt
```

### 2. Configure your credentials

```bash
python splitter.py configure
```

This will ask for:
- Instagram username & password
- Clip duration (seconds per part, max 90 for Reels)
- Delay between posts
- Caption text
- Text position (top / center / bottom)

Settings are saved to `config.json`.

### 3. Run

```bash
# Full pipeline: split + overlay + post to Instagram
python splitter.py run my_video.mp4

# Test run (no posting — just saves the processed clips)
python splitter.py run my_video.mp4 --dry-run

# Only split + add text (manual posting)
python splitter.py split-only my_video.mp4
```

---

## Run on GitHub Actions (Free Cloud Automation)

This lets you trigger the pipeline from anywhere — no local machine needed.

### Setup

1. **Fork or push this repo to GitHub**

2. **Add secrets** (Settings → Secrets and variables → Actions):
   - `INSTAGRAM_USERNAME` — your Instagram handle
   - `INSTAGRAM_PASSWORD` — your Instagram password

3. **Trigger the workflow**:
   - Go to Actions → "Instagram Video Pipeline" → "Run workflow"
   - Paste a direct download URL to your video (Google Drive, Dropbox, etc.)
   - Set clip duration and caption
   - Hit "Run workflow"

> 💡 For Google Drive: share the file publicly, then use a direct link like:
> `https://drive.google.com/uc?export=download&id=YOUR_FILE_ID`

---

## Configuration Reference (`config.json`)

| Key | Default | Description |
|-----|---------|-------------|
| `instagram_username` | `""` | Your Instagram handle |
| `instagram_password` | `""` | Your Instagram password |
| `clip_duration` | `60` | Seconds per clip (max 90 for Reels) |
| `post_delay` | `300` | Seconds between posts (5 min) |
| `caption_template` | See below | Use `{n}` for part number, `{base_caption}` |
| `base_caption` | `""` | Text inserted into every caption |
| `font_size` | `72` | Text overlay size in pixels |
| `font_color` | `"white"` | Text color (any CSS/ffmpeg color name) |
| `font_outline_color` | `"black"` | Outline color for readability |
| `text_position` | `"top"` | `top`, `center`, or `bottom` |
| `output_dir` | `"output"` | Where final clips are saved |
| `clips_dir` | `"clips"` | Where raw cuts are saved |

### Caption template example
```
Part {n} 🎬

Follow for more! 🔥

#reels #part{n} #series
```

---

## File Structure

```
insta-splitter/
├── splitter.py              # Main script
├── config.json              # Your settings (gitignored for credentials)
├── requirements.txt
├── clips/                   # Raw cut clips (auto-created)
├── output/                  # Final clips with text overlay (auto-created)
└── .github/
    └── workflows/
        └── post_reels.yml   # GitHub Actions workflow
```

---

## ⚠️  Important Notes

- **`instagrapi`** uses Instagram's private API (reverse engineered). It works without a developer token, but technically violates Instagram's ToS — use it for your own account and personal automation only.
- Keep `post_delay` at **300s (5 min) or more** to avoid triggering Instagram's rate limits.
- A session file (`.session_<username>.json`) is saved locally so you don't have to log in every time.
- Add `config.json` and `.session_*.json` to `.gitignore` before pushing to GitHub — never commit credentials.

---

## .gitignore

```
config.json
.session_*.json
clips/
output/
*.mp4
```

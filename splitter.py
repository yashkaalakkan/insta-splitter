"""
Video Splitter + Instagram Auto-Poster
--------------------------------------
Cuts a video into parts, overlays "Part N" text, and posts to Instagram.
Uses: ffmpeg (video processing) + instagrapi (Instagram login, no dev token needed)
"""

import os
import sys
import json
import time
import subprocess
import argparse
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

# ── CONFIG ──────────────────────────────────────────────────────────────────

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "instagram_username": "",
    "instagram_password": "",
    "clip_duration": 60,          # seconds per part (max 90 for Reels)
    "post_delay": 300,            # seconds between posts (5 min default)
    "caption_template": "Part {n} 🎬\n\n{base_caption}\n\n#reels #part{n}",
    "base_caption": "",
    "font_size": 72,
    "font_color": "white",
    "font_outline_color": "black",
    "text_position": "top",       # top | bottom | center
    "output_dir": "output",
    "clips_dir": "clips",
}

# ── HELPERS ──────────────────────────────────────────────────────────────────

def load_config():
    if Path(CONFIG_FILE).exists():
        with open(CONFIG_FILE) as f:
            cfg = json.load(f)
        # merge with defaults so new keys are always present
        return {**DEFAULT_CONFIG, **cfg}
    return DEFAULT_CONFIG.copy()


def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)
    print(f"✅  Config saved to {CONFIG_FILE}")


def run(cmd, label=""):
    """Run a shell command and stream output."""
    print(f"\n▶  {label or cmd[:80]}")
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌  Error:\n{result.stderr}")
        raise RuntimeError(f"Command failed: {cmd}")
    return result.stdout.strip()


def get_video_duration(path):
    """Return video duration in seconds using ffprobe."""
    cmd = (
        f'ffprobe -v error -show_entries format=duration '
        f'-of default=noprint_wrappers=1:nokey=1 "{path}"'
    )
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {path}:\n{result.stderr}")
    return float(result.stdout.strip())

# ── STEP 1: SPLIT VIDEO ──────────────────────────────────────────────────────

def split_video(video_path, clip_duration, clips_dir, cfg):
    """Split input video into clips of clip_duration seconds."""
    Path(clips_dir).mkdir(exist_ok=True)
    total = get_video_duration(video_path)
    n_parts = int(total // clip_duration) + (1 if total % clip_duration > 1 else 0)
    
    print(f"\n📹  Video: {video_path}")
    print(f"⏱   Duration: {total:.1f}s → {n_parts} parts × {clip_duration}s each\n")
    
    clips = []
    start_offset = cfg.get("start_time", 0)
    end_offset = cfg.get("end_time", 0)
    effective_end = end_offset if end_offset > 0 else total
    effective_duration = effective_end - start_offset
    n_parts = int(effective_duration // clip_duration) + (1 if effective_duration % clip_duration > 1 else 0)
    for i in range(n_parts):
        start = start_offset + (i * clip_duration)
        out = Path(clips_dir) / f"clip_{i+1:03d}.mp4"
        cmd = (
            f'ffmpeg -y -ss {start} -i "{video_path}" '
            f'-t {clip_duration} -c:v libx264 '
            f'-map 0:v:0 -map 0:a:{cfg.get("audio_track", 1)} -c:a aac '
            f'-movflags +faststart "{out}" 2>&1'
        )
        run(cmd, f"Cutting part {i+1}/{n_parts}")
        clips.append(str(out))
    
    print(f"\n✅  Split into {len(clips)} clips → {clips_dir}/")
    return clips

# ── STEP 2: ADD TEXT OVERLAY ─────────────────────────────────────────────────

def add_text_overlay(clip_path, part_number, output_dir, cfg):
    """Add black padding below video and burn 'Part N' text into it."""
    Path(output_dir).mkdir(exist_ok=True)
    
    label = f"Part {part_number}"
    size  = cfg["font_size"]
    color = cfg["font_color"]
    outline = cfg["font_outline_color"]
    
    out_path = Path(output_dir) / Path(clip_path).name.replace("clip_", "final_")
    
    # Add 200px black bar at bottom, then burn text into that bar
    drawtext = (
        f"drawtext=text='{label}':"
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"fontsize={size}:"
        f"fontcolor={color}:"
        f"bordercolor={outline}:"
        f"borderw=3:"
        f"x=(w-text_w)/2:"
        f"y=h-150"
    )
    
    cmd = (
        f'ffmpeg -y -i "{clip_path}" '
        f'-vf "pad=iw:ih+200:0:0:black,{drawtext}" '
        f'-c:v libx264 -c:a copy '
        f'-movflags +faststart "{out_path}" 2>&1'
    )
    run(cmd, f"Adding 'Part {part_number}' overlay")
    return str(out_path)

def create_cover_image(cover_path, part_number, output_dir, cfg):
    """Burn 'Part - N' text onto the center of the cover image using Pillow."""
    Path(output_dir).mkdir(exist_ok=True)
    out_path = Path(output_dir) / f"cover_{part_number:03d}.jpg"

    img = Image.open(cover_path).convert("RGB")
    img = img.resize((1080, 1920), Image.LANCZOS)

    draw = ImageDraw.Draw(img)
    text = f"Part - {part_number}"

    font_size = 90
    try:
        for font_name in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
            "/Library/Fonts/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]:
            if Path(font_name).exists():
                font = ImageFont.truetype(font_name, font_size)
                break
        else:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = (1080 - text_w) / 2
    y = (1920 - text_h) / 2 - 20

    outline_range = 3
    for dx in range(-outline_range, outline_range + 1):
        for dy in range(-outline_range, outline_range + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), text, font=font, fill="black")

    draw.text((x, y), text, font=font, fill="black")

    img.save(str(out_path), quality=95)
    print(f"✅  Cover saved: {out_path}")
    return str(out_path)

# ── STEP 3: POST TO INSTAGRAM ────────────────────────────────────────────────

def post_to_instagram(video_path, caption, cfg):
    """Upload a video as an Instagram Reel using instagrapi."""
    try:
        from instagrapi import Client
    except ImportError:
        print("❌  instagrapi not installed. Run: pip install instagrapi")
        sys.exit(1)
    
    username = cfg["instagram_username"]
    password = cfg["instagram_password"]
    
    if not username or not password:
        raise ValueError(
            "Instagram credentials missing. "
            "Run: python splitter.py configure"
        )
    
    session_file = "session.json" if Path("session.json").exists() else f".session_{username}.json"
    cl = Client()
    cl.delay_range = [2, 5]  # polite random delay between API calls
    
    # Reuse existing session to avoid repeated logins (reduces ban risk)
    if Path(session_file).exists():
        print("♻️   Loading saved session…")
        cl.load_settings(session_file)
        try:
            cl.get_timeline_feed()  # test if session still valid
        except Exception:
            print("⚠️   Session expired, logging in fresh…")
            cl.login(username, password)
    else:
        print("🔐  Logging in to Instagram…")
        cl.login(username, password)
    
    cl.dump_settings(session_file)
    print(f"✅  Logged in as @{username}")
    
    print(f"📤  Uploading {video_path} as Reel…")
    cover = cfg.get("cover_image")
    media = cl.clip_upload(
        Path(video_path),
        caption=caption,
        thumbnail=Path(cover) if cover and Path(cover).exists() else None,
    )
    print(f"🎉  Posted! instagram.com/p/{media.code}/")
    return media

# ── FULL PIPELINE ─────────────────────────────────────────────────────────────

def run_pipeline(video_path, cfg, dry_run=False):
    start_time = datetime.now()
    print(f"\n{'='*55}")
    print(f"  🎬  Instagram Video Splitter Pipeline")
    print(f"  Input : {video_path}")
    print(f"  Parts : ~{cfg['clip_duration']}s each")
    print(f"  Delay : {cfg['post_delay']}s between posts")
    print(f"{'='*55}\n")
    
    # 1. Split
    clips = split_video(video_path, cfg["clip_duration"], cfg["clips_dir"], cfg)
    
    # 2. Overlay + (3) Post
    start = cfg.get("start_part", 1)
    for loop_idx, (part_num, clip) in enumerate(zip(range(start, start + len(clips)), clips)):
        final_clip = add_text_overlay(clip, part_num, cfg["output_dir"], cfg)
        original_cover = cfg.get("original_cover_image", cfg["cover_image"])
        cfg["original_cover_image"] = original_cover
        cover = create_cover_image(original_cover, part_num, cfg["output_dir"], cfg)
        cfg["cover_image"] = cover
        
        caption = cfg["caption_template"].format(
            n=part_num,
            base_caption=cfg["base_caption"],
        )
        
        if dry_run:
            print(f"\n[DRY RUN] Would post: {final_clip}")
            print(f"[DRY RUN] Caption:\n{caption}\n")
        else:
            post_to_instagram(final_clip, caption, cfg)
            
            if loop_idx < len(clips) - 1:
                delay = cfg["post_delay"]
                print(f"\n⏳  Waiting {delay}s before next post ({loop_idx+1}/{len(clips)})…")
                time.sleep(delay)
    
    elapsed = (datetime.now() - start_time).seconds
    print(f"\n🏁  Done! {len(clips)} parts processed in {elapsed}s")
    if dry_run:
        print(f"    Final clips saved to: {cfg['output_dir']}/")

# ── CLI ───────────────────────────────────────────────────────────────────────

def cmd_configure(args):
    cfg = load_config()
    print("\n⚙️   Interactive Configuration\n")
    
    cfg["instagram_username"] = input(f"Instagram username [{cfg['instagram_username']}]: ").strip() or cfg["instagram_username"]
    cfg["instagram_password"] = input(f"Instagram password (input hidden) : ").strip() or cfg["instagram_password"]
    
    dur = input(f"Clip duration in seconds [{cfg['clip_duration']}]: ").strip()
    if dur:
        cfg["clip_duration"] = int(dur)
    
    delay = input(f"Delay between posts in seconds [{cfg['post_delay']}]: ").strip()
    if delay:
        cfg["post_delay"] = int(delay)
    
    caption = input(f"Base caption (added to every post) [{cfg['base_caption']}]: ").strip()
    if caption:
        cfg["base_caption"] = caption
    
    pos = input(f"Text position top/center/bottom [{cfg['text_position']}]: ").strip()
    if pos in ("top", "center", "bottom"):
        cfg["text_position"] = pos
    
    save_config(cfg)


def cmd_run(args):
    cfg = load_config()
    if not Path(args.video).exists():
        print(f"❌  File not found: {args.video}")
        sys.exit(1)
    run_pipeline(args.video, cfg, dry_run=args.dry_run)


def cmd_split_only(args):
    """Just split + overlay, no posting."""
    cfg = load_config()
    clips = split_video(args.video, cfg["clip_duration"], cfg["clips_dir"], cfg)
    for i, clip in enumerate(clips, 1):
        add_text_overlay(clip, i, cfg["output_dir"], cfg)
    print(f"\n✅  All clips with overlays saved to: {cfg['output_dir']}/")


def main():
    parser = argparse.ArgumentParser(
        description="Split a video into parts and post to Instagram"
    )
    sub = parser.add_subparsers(dest="command")
    
    # configure
    sub.add_parser("configure", help="Set up credentials and settings")
    
    # run
    p_run = sub.add_parser("run", help="Split + overlay + post to Instagram")
    p_run.add_argument("video", help="Path to input video file")
    p_run.add_argument("--dry-run", action="store_true",
                       help="Process but do NOT post (saves clips only)")
    
    # split-only
    p_split = sub.add_parser("split-only", help="Split + overlay only (no posting)")
    p_split.add_argument("video", help="Path to input video file")
    
    args = parser.parse_args()
    
    if args.command == "configure":
        cmd_configure(args)
    elif args.command == "run":
        cmd_run(args)
    elif args.command == "split-only":
        cmd_split_only(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

"""
ZENIX Bot - Universal Download Command (-dl <url>)
Downloads videos from YouTube, Instagram, Facebook, and other platforms.
- YouTube: Android UA, NO cookies, 1080p max
- Instagram: Uses IG cookies
- Everything else: Uses FB cookies
- FFmpeg: imageio_ffmpeg bundled binary
- Format: bestvideo[height<=1080]+bestaudio/best[height<=1080]/best
- Fragment retries: 5, concurrent fragments: 8
"""

import asyncio
import os
import sys
import tempfile
import traceback
from pathlib import Path
from urllib.parse import urlparse

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.parent.parent

sys.path.insert(0, str(BASE_DIR))
from utils import log

# Get ffmpeg path from imageio_ffmpeg
try:
    import imageio_ffmpeg
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG_PATH = "ffmpeg"

ANDROID_UA = "com.google.android.youtube/19.09.37 (Linux; U; Android 12; M2102J20SG Build/V417IR) gzip"
CHROME_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

FB_COOKIES_PATH = "data/facebook_cookies.txt"
IG_COOKIES_PATH = "data/instagram_cookies.txt"


def get_ydl_opts(url):
    """Get yt-dlp options based on URL."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()

    opts = {
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "merge_output_format": "mp4",
        "outtmpl": os.path.join(tempfile.gettempdir(), "zenix_dl_%(id)s.%(ext)s"),
        "ffmpeg_location": FFMPEG_PATH,
        "fragment_retries": 5,
        "concurrent_fragment_downloads": 8,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }

    # YouTube - Android UA, NO cookies
    if "youtube.com" in domain or "youtu.be" in domain:
        opts["extractor_args"] = {"youtube": {"player_client": ["android"]}}
        opts["http_headers"] = {"User-Agent": ANDROID_UA}
        # NO cookies for YouTube

    # Instagram - use IG cookies
    elif "instagram.com" in domain:
        cookie_path = str(BASE_DIR / IG_COOKIES_PATH)
        if os.path.exists(cookie_path):
            opts["cookiefile"] = cookie_path
        opts["http_headers"] = {"User-Agent": CHROME_UA}

    # Everything else - use FB cookies
    else:
        cookie_path = str(BASE_DIR / FB_COOKIES_PATH)
        if os.path.exists(cookie_path):
            opts["cookiefile"] = cookie_path
        opts["http_headers"] = {"User-Agent": CHROME_UA}

    return opts


async def download_video(url):
    """Download a video and return the file path."""
    import yt_dlp

    opts = get_ydl_opts(url)

    def _download():
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info:
                filename = ydl.prepare_filename(info)
                # Handle merged output
                base, _ = os.path.splitext(filename)
                mp4_path = base + ".mp4"
                if os.path.exists(mp4_path):
                    return mp4_path, info.get("title", "Video")
                if os.path.exists(filename):
                    return filename, info.get("title", "Video")
            return None, None

    loop = asyncio.get_event_loop()
    filepath, title = await loop.run_in_executor(None, _download)
    return filepath, title


async def handle(event, api, msg, args, config):
    """Handle -dl <url> command."""
    thread_id = event.get("threadID", "")
    sender_id = event.get("senderID", "")

    if not args:
        await msg.send_text(thread_id, "Usage: -dl <url>\nSupports: YouTube, Instagram, Facebook, Twitter, TikTok, etc.")
        return

    url = args.strip().split()[0]

    # Validate URL
    if not url.startswith("http"):
        url = "https://" + url

    await msg.react(event.get("messageID", ""), "⏳")
    await msg.send_text(thread_id, "Downloading... ⬇️")

    try:
        filepath, title = await download_video(url)

        if filepath and os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            size_mb = file_size / (1024 * 1024)

            if size_mb > 25:
                await msg.send_text(thread_id, f"File too large ({size_mb:.1f}MB). Max 25MB for Messenger.")
                os.remove(filepath)
                return

            await msg.send_attachment(thread_id, filepath, f"🎬 {title}")
            await msg.react(event.get("messageID", ""), "✅")

            # Cleanup
            os.remove(filepath)
        else:
            await msg.send_text(thread_id, "Download failed ❌ Link might be invalid or restricted.")
            await msg.react(event.get("messageID", ""), "❌")

    except Exception as e:
        log(f"DL error: {e}", "error")
        traceback.print_exc()
        await msg.send_text(thread_id, f"Download error: {str(e)[:100]}")
        await msg.react(event.get("messageID", ""), "❌")

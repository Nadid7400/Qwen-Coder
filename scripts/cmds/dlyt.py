"""
ZENIX Bot - YouTube Search & Download (-dlyt <query>)
- Search: No cookies (yt-dlp search doesn't need cookies)
- Download: Android UA, NO cookies, concurrent fragments 8
- FFmpeg: imageio_ffmpeg bundled binary
"""

import asyncio
import os
import sys
import tempfile
import traceback
from pathlib import Path

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.parent.parent

sys.path.insert(0, str(BASE_DIR))
from utils import log

try:
    import imageio_ffmpeg
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG_PATH = "ffmpeg"

ANDROID_UA = "com.google.android.youtube/19.09.37 (Linux; U; Android 12; M2102J20SG Build/V417IR) gzip"


async def search_youtube(query, max_results=5):
    """Search YouTube and return video info list."""
    import yt_dlp

    opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "default_search": "ytsearch",
    }

    def _search():
        with yt_dlp.YoutubeDL(opts) as ydl:
            results = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)
            if results and "entries" in results:
                return [
                    {
                        "title": entry.get("title", "Unknown"),
                        "url": entry.get("url", ""),
                        "id": entry.get("id", ""),
                        "duration": entry.get("duration", 0),
                    }
                    for entry in results["entries"]
                    if entry
                ]
        return []

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _search)


async def download_youtube(url_or_id):
    """Download a YouTube video."""
    import yt_dlp

    if not url_or_id.startswith("http"):
        url_or_id = f"https://www.youtube.com/watch?v={url_or_id}"

    opts = {
        "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best",
        "merge_output_format": "mp4",
        "outtmpl": os.path.join(tempfile.gettempdir(), "zenix_yt_%(id)s.%(ext)s"),
        "ffmpeg_location": FFMPEG_PATH,
        "fragment_retries": 5,
        "concurrent_fragment_downloads": 8,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "extractor_args": {"youtube": {"player_client": ["android"]}},
        "http_headers": {"User-Agent": ANDROID_UA},
    }

    def _download():
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url_or_id, download=True)
            if info:
                filename = ydl.prepare_filename(info)
                base, _ = os.path.splitext(filename)
                mp4_path = base + ".mp4"
                if os.path.exists(mp4_path):
                    return mp4_path, info.get("title", "Video")
                if os.path.exists(filename):
                    return filename, info.get("title", "Video")
        return None, None

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _download)


async def handle(event, api, msg, args, config):
    """Handle -dlyt <query> command."""
    thread_id = event.get("threadID", "")

    if not args:
        await msg.send_text(thread_id, "Usage: -dlyt <search query>\nSearches YouTube and downloads the first result.")
        return

    query = args.strip()
    await msg.react(event.get("messageID", ""), "🔍")
    await msg.send_text(thread_id, f"Searching YouTube: {query} 🔎")

    try:
        results = await search_youtube(query, max_results=1)

        if not results:
            await msg.send_text(thread_id, "No results found ❌")
            await msg.react(event.get("messageID", ""), "❌")
            return

        video = results[0]
        await msg.send_text(thread_id, f"Downloading: {video['title']} ⬇️")

        video_url = video["url"] or f"https://www.youtube.com/watch?v={video['id']}"
        filepath, title = await download_youtube(video_url)

        if filepath and os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            size_mb = file_size / (1024 * 1024)

            if size_mb > 25:
                await msg.send_text(thread_id, f"Video too large ({size_mb:.1f}MB). Try a shorter video.")
                os.remove(filepath)
                return

            await msg.send_attachment(thread_id, filepath, f"🎵 {title}")
            await msg.react(event.get("messageID", ""), "✅")
            os.remove(filepath)
        else:
            await msg.send_text(thread_id, "Download failed ❌")
            await msg.react(event.get("messageID", ""), "❌")

    except Exception as e:
        log(f"DLYT error: {e}", "error")
        traceback.print_exc()
        await msg.send_text(thread_id, f"Error: {str(e)[:100]}")
        await msg.react(event.get("messageID", ""), "❌")

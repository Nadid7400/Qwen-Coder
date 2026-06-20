"""
ZENIX Bot - PornHub Search & Download (-dlp <query>)
- Search: requests with Chrome UA, no cookies
- Download: yt-dlp with Chrome UA, no cookies
- Admin only (role 2)
- NOTE: PH search is often IP-blocked
"""

import asyncio
import os
import re
import sys
import tempfile
import traceback
from pathlib import Path
from urllib.parse import quote_plus

import aiohttp

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.parent.parent

sys.path.insert(0, str(BASE_DIR))
from utils import log, load_json

try:
    import imageio_ffmpeg
    FFMPEG_PATH = imageio_ffmpeg.get_ffmpeg_exe()
except ImportError:
    FFMPEG_PATH = "ffmpeg"

CHROME_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
SEARCH_URL = "https://www.pornhub.com/video/search?search={query}"


def check_permission(sender_id, thread_id, config):
    """Check if user has dlp permission (admin only)."""
    admins = config.get("adminBot", []) + config.get("owner", [])
    if sender_id in admins:
        return True

    permissions = load_json("data/permissions.json", {})
    thread_perms = permissions.get(thread_id, {})
    return sender_id in thread_perms.get("dlp", [])


async def search_ph(query):
    """Search PornHub for videos."""
    url = SEARCH_URL.format(query=quote_plus(query))
    headers = {"User-Agent": CHROME_UA}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return []
                html = await resp.text()

        # Parse video URLs from search results
        pattern = r'<a href="(/view_video\.php\?viewkey=[^"]+)"[^>]*>.*?<span class="title"[^>]*>([^<]+)</span>'
        matches = re.findall(pattern, html, re.DOTALL)

        results = []
        for path, title in matches[:5]:
            results.append({
                "url": f"https://www.pornhub.com{path}",
                "title": title.strip()
            })
        return results

    except Exception as e:
        log(f"PH search error: {e}", "error")
        return []


async def download_ph(url):
    """Download a PornHub video."""
    import yt_dlp

    opts = {
        "format": "best[height<=720]/best",
        "merge_output_format": "mp4",
        "outtmpl": os.path.join(tempfile.gettempdir(), "zenix_ph_%(id)s.%(ext)s"),
        "ffmpeg_location": FFMPEG_PATH,
        "quiet": True,
        "no_warnings": True,
        "http_headers": {"User-Agent": CHROME_UA},
    }

    def _download():
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
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
    """Handle -dlp <query> command."""
    thread_id = event.get("threadID", "")
    sender_id = event.get("senderID", "")

    # Permission check
    if not check_permission(sender_id, thread_id, config):
        await msg.send_text(thread_id, "You don't have permission for this command 🚫")
        return

    if not args:
        await msg.send_text(thread_id, "Usage: -dlp <search query>")
        return

    query = args.strip()
    await msg.react(event.get("messageID", ""), "🔍")

    try:
        results = await search_ph(query)

        if not results:
            await msg.send_text(thread_id, "No results found (might be IP-blocked) ❌")
            return

        # Download first result
        video = results[0]
        await msg.send_text(thread_id, f"Downloading: {video['title'][:50]}... ⬇️")

        filepath, title = await download_ph(video["url"])

        if filepath and os.path.exists(filepath):
            file_size = os.path.getsize(filepath)
            size_mb = file_size / (1024 * 1024)

            if size_mb > 25:
                await msg.send_text(thread_id, f"Video too large ({size_mb:.1f}MB)")
                os.remove(filepath)
                return

            await msg.send_attachment(thread_id, filepath, f"🎬 {title[:50]}")
            await msg.react(event.get("messageID", ""), "✅")
            os.remove(filepath)
        else:
            await msg.send_text(thread_id, "Download failed ❌")

    except Exception as e:
        log(f"DLP error: {e}", "error")
        await msg.send_text(thread_id, f"Error: {str(e)[:100]}")

"""
ZENIX Bot - Auto Download Manager
Automatically detects URLs in messages and downloads them.
- YouTube: Android UA, NO cookies
- Instagram: IG cookies
- Everything else: FB cookies
"""

import asyncio
import os
import re
import sys
import traceback
from pathlib import Path

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.parent.parent

sys.path.insert(0, str(BASE_DIR))
from utils import log

# URL detection pattern
URL_PATTERN = re.compile(
    r'https?://(?:www\.)?'
    r'(?:youtube\.com/watch\?v=|youtu\.be/|'
    r'instagram\.com/(?:p|reel|tv)/|'
    r'facebook\.com/.*/videos/|fb\.watch/|'
    r'tiktok\.com/@.*/video/|vm\.tiktok\.com/|'
    r'twitter\.com/.*/status/|x\.com/.*/status/)'
    r'[^\s<>\'"]+',
    re.IGNORECASE
)

# State
auto_dl_enabled = {}  # thread_id -> bool


async def handle(event, api, msg, args, config):
    """Handle -autodl command (on/off/status)."""
    thread_id = event.get("threadID", "")
    subcmd = args.strip().lower() if args else ""

    if subcmd == "on":
        auto_dl_enabled[thread_id] = True
        await msg.send_text(thread_id, "Auto-download enabled! 🔥 Send any supported link and I'll download it.")
    elif subcmd == "off":
        auto_dl_enabled[thread_id] = False
        await msg.send_text(thread_id, "Auto-download disabled. ❌")
    elif subcmd == "status":
        status = "enabled ✅" if auto_dl_enabled.get(thread_id) else "disabled ❌"
        await msg.send_text(thread_id, f"Auto-download: {status}")
    else:
        await msg.send_text(
            thread_id,
            "Usage: -autodl on/off/status\n"
            "When enabled, I'll auto-download any YouTube/IG/FB/TikTok/Twitter link."
        )


async def check_auto_dl(event, api, msg, config):
    """Check if message contains a URL and auto-download is enabled."""
    thread_id = event.get("threadID", "")
    body = event.get("body", "")

    if not auto_dl_enabled.get(thread_id):
        return False

    urls = URL_PATTERN.findall(body)
    if not urls:
        return False

    # Import dl module for download
    try:
        from scripts.cmds.dl import download_video

        for url in urls[:3]:  # Max 3 URLs per message
            try:
                await msg.react(event.get("messageID", ""), "⬇️")
                filepath, title = await download_video(url)

                if filepath and os.path.exists(filepath):
                    file_size = os.path.getsize(filepath)
                    size_mb = file_size / (1024 * 1024)

                    if size_mb <= 25:
                        await msg.send_attachment(thread_id, filepath, f"🎬 {title}")
                    else:
                        await msg.send_text(thread_id, f"Too large ({size_mb:.1f}MB)")

                    os.remove(filepath)
            except Exception as e:
                log(f"AutoDL error for {url}: {e}", "error")

    except ImportError:
        log("Could not import dl module for autodl", "error")

    return True

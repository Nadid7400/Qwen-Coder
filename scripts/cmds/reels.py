"""
ZENIX Bot - Instagram Reels Auto-Sender (-reels on/off/session/status/clear)
- Uses session ID + full IG cookies from instagram_cookies.txt
- Fetches from 20+ popular accounts
- Sends random reel every 15 seconds when active
"""

import asyncio
import json
import os
import random
import sys
import traceback
from pathlib import Path

import aiohttp

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.parent.parent

sys.path.insert(0, str(BASE_DIR))
from utils import log, load_json, load_cookies

IG_COOKIES_PATH = "data/instagram_cookies.txt"
IG_SESSION_PATH = "data/instagram_session.json"
REELS_INTERVAL = 15  # seconds

# Popular Instagram accounts for reels
POPULAR_ACCOUNTS = [
    "instagram", "cristiano", "leomessi", "therock", "kyliejenner",
    "selenagomez", "kimkardashian", "beyonce", "justinbieber",
    "kendalljenner", "natgeo", "nike", "neymarjr", "khloekardashian",
    "jlo", "mileycyrus", "katyperry", "kevinhart4real", "theellenshow",
    "nickiminaj"
]

# State
reels_tasks = {}  # thread_id -> asyncio.Task
sent_reels = {}  # thread_id -> set of reel IDs


def get_ig_headers():
    """Get Instagram API headers with session."""
    session_data = load_json(IG_SESSION_PATH, {})
    session_id = session_data.get("session_id", "")

    cookies = load_cookies(IG_COOKIES_PATH)
    cookie_str = "; ".join([f"{c['name']}={c['value']}" for c in cookies])

    return {
        "User-Agent": "Instagram 275.0.0.27.98 Android (33/13; 420dpi; 1080x2400; samsung; SM-G991B; o1s; exynos2100; en_US; 458229258)",
        "Cookie": cookie_str,
        "X-IG-App-ID": "936619743392459",
    }


async def fetch_reels(account=None):
    """Fetch reels from Instagram."""
    headers = get_ig_headers()

    if not account:
        account = random.choice(POPULAR_ACCOUNTS)

    # Use Instagram's web API to get reels
    url = f"https://www.instagram.com/api/v1/clips/user/"

    try:
        async with aiohttp.ClientSession() as session:
            # First get user ID
            user_url = f"https://www.instagram.com/api/v1/users/web_profile_info/?username={account}"
            async with session.get(user_url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 429:
                    log("Instagram rate limited (429)", "warning")
                    return []
                if resp.status != 200:
                    return []
                data = await resp.json()

            user_id = data.get("data", {}).get("user", {}).get("id", "")
            if not user_id:
                return []

            # Fetch reels
            reels_url = f"https://www.instagram.com/api/v1/clips/user/"
            payload = {
                "target_user_id": user_id,
                "page_size": 12,
                "max_id": None,
            }

            async with session.post(
                reels_url, headers=headers, json=payload,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()

            items = data.get("items", [])
            reels = []
            for item in items:
                media = item.get("media", {})
                video_versions = media.get("video_versions", [])
                if video_versions:
                    reels.append({
                        "id": media.get("pk", ""),
                        "url": video_versions[0].get("url", ""),
                        "caption": media.get("caption", {}).get("text", "")[:100] if media.get("caption") else "",
                    })
            return reels

    except Exception as e:
        log(f"Fetch reels error: {e}", "error")
        return []


async def reels_loop(thread_id, api, msg):
    """Background loop that sends reels every REELS_INTERVAL seconds."""
    if thread_id not in sent_reels:
        sent_reels[thread_id] = set()

    while True:
        try:
            reels = await fetch_reels()

            if reels:
                # Filter already sent
                new_reels = [r for r in reels if r["id"] not in sent_reels[thread_id]]
                if not new_reels:
                    sent_reels[thread_id].clear()
                    new_reels = reels

                reel = random.choice(new_reels)
                sent_reels[thread_id].add(reel["id"])

                caption = reel.get("caption", "")
                text = f"🎬 Random Reel\n{caption}" if caption else "🎬 Random Reel"
                await msg.send_text(thread_id, f"{text}\n{reel['url']}")

            await asyncio.sleep(REELS_INTERVAL)

        except asyncio.CancelledError:
            break
        except Exception as e:
            log(f"Reels loop error: {e}", "error")
            await asyncio.sleep(REELS_INTERVAL)


async def handle(event, api, msg, args, config):
    """Handle -reels on/off/session/status/clear command."""
    thread_id = event.get("threadID", "")
    subcmd = args.strip().lower() if args else ""

    if subcmd == "on":
        if thread_id in reels_tasks and not reels_tasks[thread_id].done():
            await msg.send_text(thread_id, "Reels already running! 🎬")
            return

        task = asyncio.create_task(reels_loop(thread_id, api, msg))
        reels_tasks[thread_id] = task
        await msg.send_text(thread_id, f"Reels started! 🎬 Sending every {REELS_INTERVAL}s\nUse -reels off to stop.")

    elif subcmd == "off":
        if thread_id in reels_tasks:
            reels_tasks[thread_id].cancel()
            del reels_tasks[thread_id]
            await msg.send_text(thread_id, "Reels stopped! ⏹️")
        else:
            await msg.send_text(thread_id, "Reels not running.")

    elif subcmd == "status":
        running = thread_id in reels_tasks and not reels_tasks[thread_id].done()
        sent_count = len(sent_reels.get(thread_id, set()))
        status = "running 🟢" if running else "stopped 🔴"
        await msg.send_text(thread_id, f"Reels: {status}\nSent this session: {sent_count}")

    elif subcmd == "clear":
        sent_reels.pop(thread_id, None)
        await msg.send_text(thread_id, "Reels history cleared! 🧹")

    elif subcmd == "session":
        session_data = load_json(IG_SESSION_PATH, {})
        sid = session_data.get("session_id", "Not set")
        await msg.send_text(thread_id, f"IG Session: {sid[:20]}...")

    else:
        await msg.send_text(
            thread_id,
            "Usage: -reels on/off/status/clear/session\n"
            "• on - Start sending random reels\n"
            "• off - Stop sending reels\n"
            "• status - Check if reels are running\n"
            "• clear - Clear sent history\n"
            "• session - Show IG session info"
        )

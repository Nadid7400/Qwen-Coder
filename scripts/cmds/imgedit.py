"""
ZENIX Bot - AI Image Edit (-imgedit <prompt>)
Uses Pollinations AI + SiliconFlow for image editing.
Reply to an image with -imgedit <prompt> to edit it.
"""

import asyncio
import base64
import os
import sys
import tempfile
import traceback
from pathlib import Path
from urllib.parse import quote

import aiohttp

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.parent.parent

sys.path.insert(0, str(BASE_DIR))
from utils import log, load_commands_config

SILICONFLOW_URL = "https://api.siliconflow.cn/v1/images/generations"
SILICONFLOW_MODEL = "black-forest-labs/FLUX.1-schnell"


async def download_image(url):
    """Download an image from URL."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    filepath = os.path.join(tempfile.gettempdir(), f"zenix_edit_input_{hash(url) % 100000}.png")
                    with open(filepath, "wb") as f:
                        f.write(content)
                    return filepath
    except Exception as e:
        log(f"Image download error: {e}", "error")
    return None


async def edit_with_siliconflow(prompt, image_path=None):
    """Edit/generate image using SiliconFlow API."""
    cmd_config = load_commands_config()
    api_key = cmd_config.get("mimoApiKey", "")

    if not api_key:
        return None

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": SILICONFLOW_MODEL,
        "prompt": prompt,
        "image_size": "1024x1024",
        "num_inference_steps": 4,
    }

    # If we have an input image, encode it
    if image_path and os.path.exists(image_path):
        with open(image_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")
        payload["image"] = f"data:image/png;base64,{img_b64}"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                SILICONFLOW_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    images = data.get("images", []) or data.get("data", [])
                    if images:
                        img_data = images[0]
                        # Handle URL or base64 response
                        if isinstance(img_data, dict):
                            img_url = img_data.get("url", "")
                            if img_url:
                                return await download_image(img_url)
                            b64 = img_data.get("b64_json", "")
                            if b64:
                                filepath = os.path.join(tempfile.gettempdir(), f"zenix_edit_out_{hash(prompt) % 100000}.png")
                                with open(filepath, "wb") as f:
                                    f.write(base64.b64decode(b64))
                                return filepath
                else:
                    log(f"SiliconFlow error: HTTP {resp.status}", "error")
    except Exception as e:
        log(f"SiliconFlow error: {e}", "error")

    return None


async def edit_with_pollinations(prompt, width=1024, height=1024):
    """Generate edited image using Pollinations."""
    url = f"https://image.pollinations.ai/prompt/{quote(prompt)}?width={width}&height={height}&model=flux&nologo=true&enhance=true"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    filepath = os.path.join(tempfile.gettempdir(), f"zenix_edit_poll_{hash(prompt) % 100000}.png")
                    with open(filepath, "wb") as f:
                        f.write(content)
                    return filepath
    except Exception as e:
        log(f"Pollinations edit error: {e}", "error")

    return None


async def handle(event, api, msg, args, config):
    """Handle -imgedit <prompt> command. Reply to an image to edit it."""
    thread_id = event.get("threadID", "")

    if not args:
        await msg.send_text(
            thread_id,
            "Usage: -imgedit <prompt>\n"
            "Reply to an image with this command to edit it.\n"
            "Or just use it standalone to generate an edited concept."
        )
        return

    prompt = args.strip()
    await msg.react(event.get("messageID", ""), "🎨")
    await msg.send_text(thread_id, "Editing image... 🖌️")

    # Check if replying to an image
    reply_attachment = event.get("messageReply", {}).get("attachments", [])
    input_image = None

    if reply_attachment:
        for att in reply_attachment:
            if att.get("type") in ["photo", "image"]:
                img_url = att.get("url", "") or att.get("largePreviewUrl", "")
                if img_url:
                    input_image = await download_image(img_url)
                    break

    try:
        # Try SiliconFlow first
        filepath = await edit_with_siliconflow(prompt, input_image)

        # Fallback to Pollinations
        if not filepath:
            filepath = await edit_with_pollinations(prompt)

        if filepath and os.path.exists(filepath):
            await msg.send_attachment(thread_id, filepath, f"🖼️ {prompt[:50]}")
            await msg.react(event.get("messageID", ""), "✅")
            os.remove(filepath)
        else:
            await msg.send_text(thread_id, "Image edit failed ❌")
            await msg.react(event.get("messageID", ""), "❌")

    except Exception as e:
        log(f"ImgEdit error: {e}", "error")
        await msg.send_text(thread_id, f"Error: {str(e)[:100]}")
    finally:
        # Cleanup input image
        if input_image and os.path.exists(input_image):
            os.remove(input_image)

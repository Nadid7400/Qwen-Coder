"""
ZENIX Bot - AI Image Generation (-genimg <prompt>)
Uses Pollinations AI (free, no API key required).
Models: flux, flux-realism, flux-anime, flux-3d, any-dark, flux-pro, turbo
"""

import asyncio
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
from utils import log

POLLINATIONS_URL = "https://image.pollinations.ai/prompt/{prompt}?width={width}&height={height}&model={model}&nologo=true&enhance=true"
DEFAULT_MODEL = "flux"
DEFAULT_WIDTH = 1024
DEFAULT_HEIGHT = 1024

AVAILABLE_MODELS = ["flux", "flux-realism", "flux-anime", "flux-3d", "any-dark", "flux-pro", "turbo"]


async def generate_image(prompt, model=None, width=None, height=None):
    """Generate an image using Pollinations AI."""
    model = model or DEFAULT_MODEL
    width = width or DEFAULT_WIDTH
    height = height or DEFAULT_HEIGHT

    url = POLLINATIONS_URL.format(
        prompt=quote(prompt),
        width=width,
        height=height,
        model=model
    )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                if resp.status == 200:
                    content = await resp.read()
                    filepath = os.path.join(tempfile.gettempdir(), f"zenix_img_{hash(prompt) % 100000}.png")
                    with open(filepath, "wb") as f:
                        f.write(content)
                    return filepath
                else:
                    log(f"Image generation failed: HTTP {resp.status}", "error")
                    return None
    except Exception as e:
        log(f"Image generation error: {e}", "error")
        return None


async def handle(event, api, msg, args, config):
    """Handle -genimg <prompt> [--model <model>] [--size <WxH>] command."""
    thread_id = event.get("threadID", "")

    if not args:
        models_list = ", ".join(AVAILABLE_MODELS)
        await msg.send_text(
            thread_id,
            f"Usage: -genimg <prompt> [--model <model>] [--size <WxH>]\n"
            f"Models: {models_list}\n"
            f"Example: -genimg a cat in space --model flux-anime"
        )
        return

    # Parse arguments
    model = DEFAULT_MODEL
    width = DEFAULT_WIDTH
    height = DEFAULT_HEIGHT
    prompt_parts = []

    parts = args.split()
    i = 0
    while i < len(parts):
        if parts[i] == "--model" and i + 1 < len(parts):
            model = parts[i + 1]
            if model not in AVAILABLE_MODELS:
                await msg.send_text(thread_id, f"Invalid model. Available: {', '.join(AVAILABLE_MODELS)}")
                return
            i += 2
        elif parts[i] == "--size" and i + 1 < len(parts):
            try:
                w, h = parts[i + 1].lower().split("x")
                width = int(w)
                height = int(h)
                width = max(256, min(2048, width))
                height = max(256, min(2048, height))
            except ValueError:
                pass
            i += 2
        else:
            prompt_parts.append(parts[i])
            i += 1

    prompt = " ".join(prompt_parts)
    if not prompt:
        await msg.send_text(thread_id, "Please provide a prompt!")
        return

    await msg.react(event.get("messageID", ""), "🎨")
    await msg.send_text(thread_id, f"Generating image... 🎨\nModel: {model}")

    try:
        filepath = await generate_image(prompt, model, width, height)

        if filepath and os.path.exists(filepath):
            await msg.send_attachment(thread_id, filepath, f"🖼️ {prompt[:50]}")
            await msg.react(event.get("messageID", ""), "✅")
            os.remove(filepath)
        else:
            await msg.send_text(thread_id, "Image generation failed ❌")
            await msg.react(event.get("messageID", ""), "❌")

    except Exception as e:
        log(f"GenImg error: {e}", "error")
        await msg.send_text(thread_id, f"Error: {str(e)[:100]}")

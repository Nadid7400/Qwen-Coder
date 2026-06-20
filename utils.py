"""
ZENIX Bot - Utilities Module
Provides logging, configuration loading, and message helper utilities.
"""

import json
import os
import sys
import time
import logging
from datetime import datetime
from pathlib import Path

# Base directory (handles both script and frozen exe)
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent

# Logging setup
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("ZENIX")


def log(message, level="info"):
    """Log a message with the specified level."""
    getattr(logger, level.lower(), logger.info)(message)


def load_json(filepath, default=None):
    """Load a JSON file, returning default if it doesn't exist or fails."""
    try:
        full_path = BASE_DIR / filepath
        if full_path.exists():
            with open(full_path, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        log(f"Error loading {filepath}: {e}", "error")
    return default if default is not None else {}


def save_json(filepath, data):
    """Save data to a JSON file."""
    try:
        full_path = BASE_DIR / filepath
        full_path.parent.mkdir(parents=True, exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except IOError as e:
        log(f"Error saving {filepath}: {e}", "error")
        return False


def load_config():
    """Load the main bot configuration."""
    return load_json("config.json", {})


def load_commands_config():
    """Load the commands configuration (API keys, etc.)."""
    return load_json("configCommands.json", {})


def load_cookies(filepath):
    """Load cookies from a Netscape cookie file."""
    cookies = []
    full_path = BASE_DIR / filepath
    if not full_path.exists():
        return cookies
    try:
        with open(full_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("\t")
                if len(parts) >= 7:
                    cookies.append({
                        "domain": parts[0],
                        "httpOnly": parts[1].upper() == "TRUE",
                        "path": parts[2],
                        "secure": parts[3].upper() == "TRUE",
                        "expires": int(parts[4]) if parts[4] != "0" else None,
                        "name": parts[5],
                        "value": parts[6]
                    })
    except IOError as e:
        log(f"Error loading cookies from {filepath}: {e}", "error")
    return cookies


def get_timestamp():
    """Get current timestamp string."""
    return datetime.now().strftime(DATE_FORMAT)


class MessageHelper:
    """Helper class for formatting and sending messages via FCA API."""

    def __init__(self, api):
        self.api = api

    async def send_text(self, thread_id, text, message_id=None):
        """Send a text message to a thread."""
        msg = {"body": text}
        if message_id:
            msg["messageID"] = message_id
        try:
            await self.api.send_message(msg, thread_id)
        except Exception as e:
            log(f"Error sending message to {thread_id}: {e}", "error")

    async def send_attachment(self, thread_id, attachment_path, text=""):
        """Send a file attachment to a thread."""
        try:
            msg = {"body": text}
            await self.api.send_message(msg, thread_id, attachment_path=attachment_path)
        except Exception as e:
            log(f"Error sending attachment to {thread_id}: {e}", "error")

    async def reply(self, thread_id, text, message_id):
        """Reply to a specific message."""
        await self.send_text(thread_id, text, message_id)

    async def react(self, message_id, reaction):
        """React to a message."""
        try:
            await self.api.set_message_reaction(reaction, message_id)
        except Exception as e:
            log(f"Error reacting to message: {e}", "error")

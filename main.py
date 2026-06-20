"""
ZENIX Bot - Main Entry Point
Facebook Messenger bot built on ws3_fca (fcaApi) in Python.
Prefix: -
Timezone: Asia/Dhaka
"""

import asyncio
import importlib
import os
import sys
import traceback
from pathlib import Path

# Ensure base directory is in path
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from utils import log, load_config, load_commands_config, MessageHelper
from bot.login.login import get_login_credentials, save_updated_cookies
from bot.login.fcaApi import FcaApi

# Global state
bot_api = None
msg_helper = None
loaded_commands = {}


def load_all_commands():
    """Auto-load all command scripts from scripts/cmds/."""
    global loaded_commands
    cmds_dir = BASE_DIR / "scripts" / "cmds"

    if not cmds_dir.exists():
        log("scripts/cmds/ directory not found!", "error")
        return

    for file in cmds_dir.glob("*.py"):
        if file.name.startswith("_"):
            continue
        module_name = file.stem
        try:
            spec = importlib.util.spec_from_file_location(
                f"scripts.cmds.{module_name}", str(file)
            )
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            loaded_commands[module_name] = module
            log(f"Loaded command: {module_name}")
        except Exception as e:
            log(f"Error loading command {module_name}: {e}", "error")
            traceback.print_exc()


async def handle_event(event):
    """Main event handler for all incoming messages/events."""
    global bot_api, msg_helper

    if not event:
        return

    event_type = event.get("type", "")

    # Handle message events
    if event_type == "message":
        await handle_message(event)
    elif event_type == "event":
        # Group events (member join/leave, etc.)
        pass


async def handle_message(event):
    """Handle incoming messages and route to commands."""
    global loaded_commands, msg_helper

    config = load_config()
    prefix = config.get("prefix", "-")
    body = event.get("body", "").strip()
    sender_id = event.get("senderID", "")
    thread_id = event.get("threadID", "")
    message_id = event.get("messageID", "")
    is_group = event.get("isGroup", False)

    # Self-filter: skip bot's own messages if selfListen handles it
    bot_id = config.get("facebookAccount", {}).get("i_user", "")

    if not body:
        return

    # Check for "zenix" trigger (AI chat)
    if "zenix" in body.lower() or body.lower().startswith(prefix + "zenix"):
        if "zenix" in loaded_commands:
            module = loaded_commands["zenix"]
            if hasattr(module, "handle"):
                await module.handle(
                    event=event,
                    api=bot_api,
                    msg=msg_helper,
                    config=config
                )
            return

    # Check for prefix commands
    if body.startswith(prefix):
        cmd_text = body[len(prefix):].strip()
        parts = cmd_text.split(None, 1)
        if not parts:
            return

        cmd_name = parts[0].lower()
        cmd_args = parts[1] if len(parts) > 1 else ""

        # Route to command module
        if cmd_name in loaded_commands:
            module = loaded_commands[cmd_name]
            if hasattr(module, "handle"):
                try:
                    await module.handle(
                        event=event,
                        api=bot_api,
                        msg=msg_helper,
                        args=cmd_args,
                        config=config
                    )
                except Exception as e:
                    log(f"Command {cmd_name} error: {e}", "error")
                    traceback.print_exc()
                    await msg_helper.send_text(
                        thread_id,
                        f"Error executing command: {cmd_name}"
                    )
        # Also check for special commands like "slum", "tord"
        elif cmd_name == "slum" and "zenix" in loaded_commands:
            module = loaded_commands["zenix"]
            if hasattr(module, "handle_slum"):
                await module.handle_slum(event, bot_api, msg_helper, cmd_args, config)
        elif cmd_name == "tord" and "zenix" in loaded_commands:
            module = loaded_commands["zenix"]
            if hasattr(module, "handle_tord"):
                await module.handle_tord(event, bot_api, msg_helper, config)
    else:
        # Check if user replied to bot's message (reply-based chat)
        if "zenix" in loaded_commands:
            module = loaded_commands["zenix"]
            if hasattr(module, "handle_reply"):
                await module.handle_reply(event, bot_api, msg_helper, config)


async def main():
    """Main bot startup."""
    global bot_api, msg_helper

    log("=" * 50)
    log("ZENIX Bot Starting...")
    log("=" * 50)

    # Load configuration
    config = load_config()
    cmd_config = load_commands_config()

    if not config:
        log("FATAL: config.json not found or invalid!", "error")
        return

    if not cmd_config:
        log("WARNING: configCommands.json not found. Some features won't work.", "warning")

    # Get login credentials
    credentials = get_login_credentials()
    if not credentials:
        log("FATAL: Cannot obtain login credentials!", "error")
        return

    # Initialize FCA API
    bot_api = FcaApi(credentials)
    success = await bot_api.login()

    if not success:
        log("FATAL: Login failed!", "error")
        return

    # Initialize message helper
    msg_helper = MessageHelper(bot_api)

    # Send friend request on start if configured
    friend_target = config.get("facebookAccount", {}).get("friendRequestOnStart", "")
    if friend_target:
        await bot_api.send_friend_request(friend_target)

    # Load all command scripts
    auto_load = config.get("autoLoadScripts", {}).get("enable", True)
    if auto_load:
        load_all_commands()
        log(f"Loaded {len(loaded_commands)} commands")

    # Register reply tracking: when bot sends a message, track its ID
    if "zenix" in loaded_commands and hasattr(loaded_commands["zenix"], "track_bot_message"):
        msg_helper.on_message_sent(loaded_commands["zenix"].track_bot_message)

    # Register event handler
    bot_api.on_message(handle_event)

    # Start listening
    log("ZENIX Bot is now online!")
    log(f"Prefix: {config.get('prefix', '-')}")
    log(f"Loaded commands: {list(loaded_commands.keys())}")

    try:
        await bot_api.listen()
    except KeyboardInterrupt:
        log("Bot stopped by user.")
    finally:
        await bot_api.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("Bot terminated.")
    except Exception as e:
        log(f"Fatal error: {e}", "error")
        traceback.print_exc()

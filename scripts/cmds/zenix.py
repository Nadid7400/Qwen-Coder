"""
ZENIX Bot - AI Chat Module v5.0
Features:
- Trigger: message contains "zenix" (case-insensitive)
- Reply system: Bot responds when user replies to bot's message
- Language: Banglish + English ONLY (no Hindi/Hinglish)
- Talks like a real human friend, NOT AI
- Memory: Permanent until -memclear
- Active user tracking
- Deduplication: Bot self-filter, prefix skip
- Truth or Dare via -tord
- Commands: -zenix status/clear/memclear/lang, -slum, -tord
"""

import asyncio
import json
import time
import traceback
import aiohttp
from pathlib import Path
import sys

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.parent.parent

sys.path.insert(0, str(BASE_DIR))
from utils import log, load_json, save_json, load_commands_config

# Constants
AI_TIMEOUT = 15  # seconds per provider call
MEMORY_FILE = "data/ai_memory.json"

# State tracking
bot_message_ids = set()  # Track bot's own message IDs for reply detection
last_provider = None  # Cache last working provider

# System prompt for ZENIX personality
SYSTEM_PROMPT = """You are ZENIX, a fun and friendly chat bot in a Facebook Messenger group.
Rules:
- Talk in Banglish (Bengali written in English letters) and English ONLY
- NEVER use Hindi or Hinglish
- Talk like a real human friend, use slang, be casual and fun
- You are NOT an AI - you are ZENIX, a cool friend
- Keep responses short and punchy unless asked for details
- Use emojis naturally but don't overdo it
- Remember things users tell you (their name, facts, etc.)
- Be helpful but also funny and sarcastic sometimes
- If someone asks who made you, say "NADID made me bro 😎"
"""

GREETING_EMOJIS = (
    "😎🔥💀😂🤣🙏💯✨🎯👑🫡😈🤙💪🗿👀🎶💫⚡"
    "🌟🎉🥶🤝😤🫠🥴🤯😵💀🔥✅❌🎵🎮🏆🍕🌈🦾"
    "🧠💡🎭🎪🎨🎬🎤🎧🎸🎹🎺🎻🎼🎵🎶🎷🪘🥁"
    "🎲🎯🎳🎰🎨🖌️🎭🎪🎠🎡🎢🎪🏟️🎆🎇🧨🎈"
    "🎀🎁🎗️🎟️🎫🎖️🏅🥇🥈🥉🏆🏈⚽🏀🎾🏐"
)


def load_memory():
    """Load AI memory from file."""
    return load_json(MEMORY_FILE, {})


def save_memory(memory):
    """Save AI memory to file."""
    save_json(MEMORY_FILE, memory)


def get_user_memory(user_id):
    """Get memory facts for a specific user."""
    memory = load_memory()
    user_mem = memory.get(user_id, {"facts": [], "reminders": []})
    return user_mem


def add_memory_fact(user_id, fact_text):
    """Add a fact to user's memory."""
    memory = load_memory()
    if user_id not in memory:
        memory[user_id] = {"facts": [], "reminders": []}
    memory[user_id]["facts"].append({
        "text": fact_text,
        "time": time.time()
    })
    save_memory(memory)


def clear_memory(user_id=None):
    """Clear memory for a user or all."""
    if user_id:
        memory = load_memory()
        if user_id in memory:
            del memory[user_id]
            save_memory(memory)
    else:
        save_memory({})


async def _call_ai_inner(prompt, user_memory_context=""):
    """Call AI providers with fallback chain."""
    global last_provider

    cmd_config = load_commands_config()
    puter_token = cmd_config.get("puter_token", "")
    mimo_key = cmd_config.get("mimoApiKey", "")
    opencode_key = cmd_config.get("opencodeZenKey", "")
    deepseek_key = cmd_config.get("deepseekApiKey", "")
    gemini_key1 = cmd_config.get("geminiApiKey", "")
    gemini_key2 = cmd_config.get("geminiApiKey2", "")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + user_memory_context},
        {"role": "user", "content": prompt}
    ]

    providers = []

    # 1. Puter API
    if puter_token:
        puter_models = [
            "deepseek-v4-flash", "deepseek-v4-pro", "deepseek-v3.2",
            "deepseek-chat", "gpt-4o-mini", "claude-3.5-sonnet",
            "gemini-2.0-flash", "llama-3.3-70b", "qwen3-32b"
        ]
        for model in puter_models:
            providers.append({
                "name": f"puter/{model}",
                "url": "https://api.puter.com/puterai/openai/v1/chat/completions",
                "headers": {
                    "Authorization": f"Bearer {puter_token}",
                    "Content-Type": "application/json"
                },
                "body": {"model": model, "messages": messages}
            })

    # 2. SiliconFlow (Mimo)
    if mimo_key:
        for model in ["opencode/mimo-v2-free", "Qwen/Qwen2.5-72B-Instruct"]:
            providers.append({
                "name": f"siliconflow/{model}",
                "url": "https://api.siliconflow.cn/v1/chat/completions",
                "headers": {
                    "Authorization": f"Bearer {mimo_key}",
                    "Content-Type": "application/json"
                },
                "body": {"model": model, "messages": messages}
            })

    # 3. OpenCode Zen
    if opencode_key:
        for model in ["opencode/mimo-v2-free", "opencode/gemini-2.5-flash"]:
            providers.append({
                "name": f"opencode/{model}",
                "url": "https://opencode.ai/zen/v1/chat/completions",
                "headers": {
                    "Authorization": f"Bearer {opencode_key}",
                    "Content-Type": "application/json"
                },
                "body": {"model": model, "messages": messages}
            })

    # 4. DeepSeek
    if deepseek_key:
        providers.append({
            "name": "deepseek/deepseek-chat",
            "url": "https://api.deepseek.com/v1/chat/completions",
            "headers": {
                "Authorization": f"Bearer {deepseek_key}",
                "Content-Type": "application/json"
            },
            "body": {"model": "deepseek-chat", "messages": messages}
        })

    # 5. Gemini Key 1
    if gemini_key1:
        providers.append({
            "name": "gemini/gemini-2.0-flash",
            "url": f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key1}",
            "headers": {"Content-Type": "application/json"},
            "body": {
                "contents": [{"parts": [{"text": SYSTEM_PROMPT + user_memory_context + "\n\nUser: " + prompt}]}]
            },
            "is_gemini": True
        })

    # 6. Gemini Key 2
    if gemini_key2:
        providers.append({
            "name": "gemini2/gemini-2.0-flash",
            "url": f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key2}",
            "headers": {"Content-Type": "application/json"},
            "body": {
                "contents": [{"parts": [{"text": SYSTEM_PROMPT + user_memory_context + "\n\nUser: " + prompt}]}]
            },
            "is_gemini": True
        })

    # Try last working provider first
    if last_provider:
        matching = [p for p in providers if p["name"] == last_provider]
        if matching:
            providers.remove(matching[0])
            providers.insert(0, matching[0])

    # Try each provider
    async with aiohttp.ClientSession() as session:
        for provider in providers:
            try:
                async with session.post(
                    provider["url"],
                    headers=provider["headers"],
                    json=provider["body"],
                    timeout=aiohttp.ClientTimeout(total=AI_TIMEOUT)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()

                        # Parse response based on provider type
                        if provider.get("is_gemini"):
                            text = data.get("candidates", [{}])[0].get(
                                "content", {}
                            ).get("parts", [{}])[0].get("text", "")
                        else:
                            text = data.get("choices", [{}])[0].get(
                                "message", {}
                            ).get("content", "")

                        if text:
                            last_provider = provider["name"]
                            log(f"AI response from: {provider['name']}")
                            return text.strip()

            except (asyncio.TimeoutError, aiohttp.ClientError) as e:
                continue
            except Exception as e:
                continue

    return None


async def call_ai(prompt, user_id=""):
    """Call AI with user memory context."""
    # Build memory context
    user_memory_context = ""
    if user_id:
        user_mem = get_user_memory(user_id)
        if user_mem.get("facts"):
            facts_text = "\n".join([f"- {f['text']}" for f in user_mem["facts"][-20:]])
            user_memory_context = f"\n\nMemory about this user:\n{facts_text}"

    response = await _call_ai_inner(prompt, user_memory_context)
    return response


def track_bot_message(message_id):
    """Track a message ID as sent by the bot."""
    bot_message_ids.add(message_id)
    # Keep set size manageable (last 1000 messages)
    if len(bot_message_ids) > 1000:
        # Remove oldest entries (convert to list, trim, convert back)
        excess = len(bot_message_ids) - 1000
        for _ in range(excess):
            bot_message_ids.pop()


def is_reply_to_bot(event):
    """Check if a message is a reply to one of the bot's messages."""
    message_reply = event.get("messageReply", {})
    if not message_reply:
        return False

    # Check if the replied-to message's ID is in our tracked bot messages
    reply_msg_id = message_reply.get("messageID", "")
    if reply_msg_id in bot_message_ids:
        return True

    # Also check by senderID of the replied message (bot's own ID)
    reply_sender = message_reply.get("senderID", "")
    from utils import load_config
    config = load_config()
    bot_user_id = config.get("facebookAccount", {}).get("i_user", "")
    if bot_user_id and reply_sender == bot_user_id:
        return True

    return False


async def handle(event, api, msg, config):
    """Handle zenix trigger or -zenix commands."""
    body = event.get("body", "").strip()
    sender_id = event.get("senderID", "")
    thread_id = event.get("threadID", "")
    prefix = config.get("prefix", "-")

    # Check for -zenix subcommands
    if body.lower().startswith(prefix + "zenix"):
        subcmd = body[len(prefix) + 5:].strip().lower()

        if subcmd == "status":
            tracked = len(bot_message_ids)
            await msg.send_text(thread_id, f"ZENIX active! Reply to my messages to chat. Tracking {tracked} messages.")
            return

        elif subcmd == "clear":
            bot_message_ids.clear()
            await msg.send_text(thread_id, "ZENIX message tracking cleared! 👋")
            return

        elif subcmd == "memclear":
            admins = config.get("adminBot", []) + config.get("owner", [])
            if sender_id in admins:
                clear_memory(sender_id)
                await msg.send_text(thread_id, "Memory cleared! 🧹")
            else:
                await msg.send_text(thread_id, "Only admins can clear memory bro 😤")
            return

        elif subcmd == "lang":
            await msg.send_text(thread_id, "Language: Banglish + English ONLY 🇧🇩")
            return

    # Check if first message (greeting)
    user_mem = get_user_memory(sender_id)
    if not user_mem.get("facts"):
        greeting = f"Yo! ZENIX here! 🔥 Ki khobor bro? 😎\n\n{GREETING_EMOJIS}"
        await msg.send_text(thread_id, greeting)

    # Get AI response
    # Remove "zenix" from the query
    query = body.lower().replace("zenix", "").strip()
    if not query:
        query = "Someone just said hi to you, greet them in Banglish"

    response = await call_ai(query, sender_id)
    if response:
        await msg.send_text(thread_id, response)

        # Extract and store facts from conversation
        if any(word in body.lower() for word in ["my name", "i am", "ami", "amar nam"]):
            add_memory_fact(sender_id, body)
    else:
        await msg.send_text(thread_id, "Bro ektu wait koro, brain lag khacche 🧠💤")


async def handle_reply(event, api, msg, config):
    """Handle reply-to-bot messages. Bot only responds when user replies to its message."""
    thread_id = event.get("threadID", "")
    sender_id = event.get("senderID", "")
    body = event.get("body", "").strip()

    if not body or body.startswith(config.get("prefix", "-")):
        return

    # Only respond if this message is a reply to one of the bot's messages
    if not is_reply_to_bot(event):
        return

    # User replied to bot's message - respond to them
    response = await call_ai(body, sender_id)
    if response:
        await msg.send_text(thread_id, response)

        # Store facts
        if any(word in body.lower() for word in ["my name", "i am", "ami", "amar nam"]):
            add_memory_fact(sender_id, body)
    else:
        await msg.send_text(thread_id, "Bro ektu wait koro, brain lag khacche 🧠💤")


async def handle_slum(event, api, msg, args, config):
    """Handle -slum command (talk/insult mode)."""
    thread_id = event.get("threadID", "")
    sender_id = event.get("senderID", "")

    if not args:
        await msg.send_text(thread_id, "Ki bolbo bro? -slum er por kichu lekho 😂")
        return

    prompt = f"Respond to this in a funny, savage Banglish way (like roasting a friend playfully): {args}"
    response = await call_ai(prompt, sender_id)
    if response:
        await msg.send_text(thread_id, response)
    else:
        await msg.send_text(thread_id, "Brain hang hoye geche 💀")


async def handle_tord(event, api, msg, config):
    """Handle -tord (Truth or Dare) command."""
    thread_id = event.get("threadID", "")
    sender_id = event.get("senderID", "")

    prompt = (
        "Generate one Truth or Dare question in Banglish. "
        "Make it fun, spicy but not too inappropriate. "
        "Format: 'Truth: ...' or 'Dare: ...' (randomly pick one). "
        "Keep it short and fun for a group chat."
    )

    response = await call_ai(prompt, sender_id)
    if response:
        await msg.send_text(thread_id, f"🎲 TRUTH OR DARE 🎲\n\n{response}")
    else:
        await msg.send_text(thread_id, "Bro TORD generate korte parlam na 😩")

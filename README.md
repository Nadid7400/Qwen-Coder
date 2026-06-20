# ZENIX Bot

Facebook Messenger bot built on ws3_fca (fcaApi) in Python.

## Features

- **AI Chat** - Powered by multiple AI providers with automatic fallback (Puter, SiliconFlow, OpenCode, DeepSeek, Gemini)
- **Video Downloads** - Universal downloader supporting YouTube, Instagram, Facebook, Twitter, TikTok
- **YouTube Search** - Search and download YouTube videos by query
- **Instagram Reels** - Auto-send random reels from popular accounts
- **AI Image Generation** - Generate images using Pollinations AI (7 models)
- **AI Image Editing** - Edit images using SiliconFlow + Pollinations
- **Permission System** - Per-thread command permissions
- **Truth or Dare** - AI-generated Banglish questions

## Commands

| Command | Description |
|---------|-------------|
| `-dl <url>` | Download video from any supported URL |
| `-dlyt <query>` | Search & download from YouTube |
| `-dlp <query>` | Search & download (admin only) |
| `-dlx <query>` | Search & download (admin only) |
| `-autodl on/off` | Auto-download links |
| `-reels on/off/status` | Instagram reels auto-sender |
| `-genimg <prompt>` | Generate AI image |
| `-imgedit <prompt>` | Edit image (reply to image) |
| `-perm add/remove/list` | Manage permissions |
| `-zenix status/clear/memclear` | AI chat controls |
| `-slum <text>` | Savage Banglish roast |
| `-tord` | Truth or Dare |
| Say "zenix" | Activate AI chat mode (10min TTL) |

## Setup

### Prerequisites
- Python 3.11+
- Windows 10/11

### Installation

```bash
pip install -r requirements.txt
```

### Configuration

1. Copy `configCommands.example.json` to `configCommands.json` and fill in your API keys
2. Put your Facebook cookies in `account.txt` (Netscape cookie format)
3. Put Instagram cookies in `data/instagram_cookies.txt`
4. Put Instagram session in `data/instagram_session.json`
5. Edit `config.json` with your admin IDs and settings

### Running

```bash
python main.py
```

### Building Executable

```bash
pyinstaller zenix.spec
```

Output: `dist/zenix.exe`

## Project Structure

```
Zenix/
├── main.py                     # Entry point
├── utils.py                    # Utilities, logging, MessageHelper
├── config.json                 # Bot configuration
├── configCommands.example.json # API keys template
├── requirements.txt            # Python dependencies
├── zenix.spec                  # PyInstaller build spec
├── bot/
│   └── login/
│       ├── login.py            # Cookies-only Facebook login
│       └── fcaApi.py           # Facebook MQTT API wrapper
├── scripts/
│   └── cmds/
│       ├── zenix.py            # AI chat v5.0
│       ├── dl.py               # Universal video downloader
│       ├── dlyt.py             # YouTube search & download
│       ├── dlp.py              # Search & download (admin)
│       ├── dlx.py              # Search & download (admin)
│       ├── autodl.py           # Auto download manager
│       ├── reels.py            # Instagram reels auto-sender
│       ├── perm.py             # Permission system
│       ├── genimg.py           # AI image generation
│       └── imgedit.py          # AI image editing
└── data/                       # Runtime data (gitignored)
    ├── ai_memory.json
    ├── permissions.json
    ├── user_data.json
    ├── facebook_cookies.txt
    ├── instagram_cookies.txt
    └── instagram_session.json
```

## AI Providers (Fallback Order)

1. **Puter API** - Multiple models (deepseek, gpt-4o-mini, claude, gemini, llama, qwen)
2. **SiliconFlow** - mimo-v2-free, Qwen2.5-72B
3. **OpenCode Zen** - mimo-v2-free, gemini-2.5-flash
4. **DeepSeek** - deepseek-chat
5. **Gemini** - gemini-2.0-flash (2 keys)

## Important Notes

- YouTube downloads use Android User-Agent WITHOUT cookies
- Facebook login uses ONLY cookies (no email/password)
- MQTT restarts every 5 minutes (configurable)
- Auto-reconnect is enabled by default
- Bot speaks Banglish (Bengali in English letters), never Hindi
- All user memory is permanent until `-memclear`

## License

Private project by NADID.

"""
ZENIX Bot - Facebook Login Module
Handles cookies-only login (no email/password, no Graph API).
"""

import json
import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.parent.parent

from utils import log, load_cookies, load_config


def parse_account_cookies(cookie_file="account.txt"):
    """Parse Facebook cookies from the account.txt Netscape cookie file."""
    cookies = load_cookies(cookie_file)
    if not cookies:
        log("No cookies found in account.txt! Bot cannot login.", "error")
        return None

    # Convert to the format expected by ws3_fca
    appstate = []
    for cookie in cookies:
        appstate.append({
            "key": cookie["name"],
            "value": cookie["value"],
            "domain": cookie["domain"],
            "path": cookie["path"],
            "hostOnly": not cookie["domain"].startswith("."),
            "creation": "",
            "lastAccessed": ""
        })

    return appstate


def get_login_credentials():
    """
    Get login credentials for Facebook.
    Uses cookies-only approach (no email/password login).
    Returns appstate for ws3_fca.
    """
    config = load_config()
    fb_config = config.get("facebookAccount", {})

    # Parse cookies from account.txt
    appstate = parse_account_cookies("account.txt")
    if not appstate:
        log("FATAL: Cannot login - no valid cookies in account.txt", "error")
        return None

    log(f"Loaded {len(appstate)} cookies from account.txt")

    return {
        "appState": appstate,
        "options": config.get("optionsFca", {
            "forceLogin": True,
            "listenEvents": True,
            "updatePresence": True,
            "listenTyping": True,
            "logLevel": "error",
            "selfListen": True,
            "selfListenEvent": True,
            "autoMarkDelivery": False,
            "autoReconnect": True
        }),
        "userAgent": fb_config.get(
            "userAgent",
            "Mozilla/5.0 (Linux; Android 12; M2102J20SG) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/101.0.0.0 Mobile Safari/537.36"
        )
    }


def save_updated_cookies(appstate, cookie_file="account.txt"):
    """Save updated cookies back to account.txt in Netscape format."""
    try:
        filepath = BASE_DIR / cookie_file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("# Netscape HTTP Cookie File\n")
            for cookie in appstate:
                domain = cookie.get("domain", ".facebook.com")
                flag = "TRUE" if domain.startswith(".") else "FALSE"
                path = cookie.get("path", "/")
                secure = "TRUE"
                expires = "0"
                name = cookie.get("key", "")
                value = cookie.get("value", "")
                f.write(f"{domain}\t{flag}\t{path}\t{secure}\t{expires}\t{name}\t{value}\n")
        log("Updated cookies saved to account.txt")
    except IOError as e:
        log(f"Error saving cookies: {e}", "error")

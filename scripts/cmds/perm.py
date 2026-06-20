"""
ZENIX Bot - Permission System (-perm)
Manages per-thread command permissions.
- -perm add <command> <userID> - Grant permission
- -perm remove <command> <userID> - Revoke permission
- -perm list - Show permissions for this thread
- -perm check <command> <userID> - Check if user has permission
Note: -perm add auto-enables permission check for that command
"""

import sys
from pathlib import Path

if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).parent.parent.parent

sys.path.insert(0, str(BASE_DIR))
from utils import log, load_json, save_json

PERMISSIONS_FILE = "data/permissions.json"


def load_permissions():
    """Load permissions data."""
    return load_json(PERMISSIONS_FILE, {})


def save_permissions(data):
    """Save permissions data."""
    save_json(PERMISSIONS_FILE, data)


def has_permission(sender_id, thread_id, command, config):
    """Check if a user has permission for a command in a thread."""
    # Admins/owners always have permission
    admins = config.get("adminBot", []) + config.get("owner", [])
    if sender_id in admins:
        return True

    permissions = load_permissions()
    thread_perms = permissions.get(thread_id, {})

    # If command has no permission list, it's open to everyone
    if command not in thread_perms:
        return True

    return sender_id in thread_perms[command]


async def handle(event, api, msg, args, config):
    """Handle -perm command."""
    thread_id = event.get("threadID", "")
    sender_id = event.get("senderID", "")

    # Only admins can manage permissions
    admins = config.get("adminBot", []) + config.get("owner", [])
    if sender_id not in admins:
        await msg.send_text(thread_id, "Only admins can manage permissions 🚫")
        return

    if not args:
        await msg.send_text(
            thread_id,
            "Usage:\n"
            "-perm add <cmd> <userID>\n"
            "-perm remove <cmd> <userID>\n"
            "-perm list\n"
            "-perm check <cmd> <userID>"
        )
        return

    parts = args.strip().split()
    subcmd = parts[0].lower()

    if subcmd == "add" and len(parts) >= 3:
        command = parts[1].lower()
        user_id = parts[2]

        permissions = load_permissions()
        if thread_id not in permissions:
            permissions[thread_id] = {}
        if command not in permissions[thread_id]:
            permissions[thread_id][command] = []

        if user_id not in permissions[thread_id][command]:
            permissions[thread_id][command].append(user_id)
            save_permissions(permissions)
            await msg.send_text(thread_id, f"✅ Permission granted: {user_id} -> {command}")
        else:
            await msg.send_text(thread_id, f"User already has {command} permission.")

    elif subcmd == "remove" and len(parts) >= 3:
        command = parts[1].lower()
        user_id = parts[2]

        permissions = load_permissions()
        if thread_id in permissions and command in permissions[thread_id]:
            if user_id in permissions[thread_id][command]:
                permissions[thread_id][command].remove(user_id)
                save_permissions(permissions)
                await msg.send_text(thread_id, f"✅ Permission revoked: {user_id} -x- {command}")
            else:
                await msg.send_text(thread_id, "User doesn't have that permission.")
        else:
            await msg.send_text(thread_id, "No permissions set for that command.")

    elif subcmd == "list":
        permissions = load_permissions()
        thread_perms = permissions.get(thread_id, {})

        if not thread_perms:
            await msg.send_text(thread_id, "No permissions set for this thread.")
            return

        text = "📋 Permissions:\n"
        for cmd, users in thread_perms.items():
            text += f"\n{cmd}: {', '.join(users)}"
        await msg.send_text(thread_id, text)

    elif subcmd == "check" and len(parts) >= 3:
        command = parts[1].lower()
        user_id = parts[2]
        has_perm = has_permission(user_id, thread_id, command, config)
        status = "✅ Has permission" if has_perm else "❌ No permission"
        await msg.send_text(thread_id, f"{user_id} -> {command}: {status}")

    else:
        await msg.send_text(thread_id, "Invalid usage. Try: -perm add/remove/list/check")

"""
ZENIX Bot - Facebook Chat API (FCA) Wrapper
Wraps ws3_fca with auto-reconnect, MQTT restart, and event handling.
"""

import asyncio
import time
import traceback

from utils import log, load_config

# Socket and keepalive settings
SOCKET_TIMEOUT = 120  # seconds
KEEPALIVE_INTERVAL = 20  # seconds


class FcaApi:
    """Facebook Chat API wrapper with auto-reconnect and MQTT restart."""

    def __init__(self, credentials):
        self.credentials = credentials
        self.api = None
        self.listener = None
        self.is_connected = False
        self.last_reconnect = 0
        self.event_handlers = []
        self.config = load_config()
        self.mqtt_config = self.config.get("restartListenMqtt", {})
        self._stop_event = asyncio.Event()

    async def login(self):
        """Login to Facebook using ws3_fca."""
        try:
            import ws3_fca

            appstate = self.credentials.get("appState", [])
            options = self.credentials.get("options", {})

            log("Logging in to Facebook via ws3_fca...")
            self.api = await ws3_fca.login(appstate, options=options)

            if self.api:
                self.is_connected = True
                log("Successfully logged in to Facebook!")
                return True
            else:
                log("Login failed - no API object returned", "error")
                return False

        except ImportError:
            log("ws3_fca module not found! Install with: pip install ws3-fca", "error")
            return False
        except Exception as e:
            log(f"Login error: {e}", "error")
            traceback.print_exc()
            return False

    def on_message(self, handler):
        """Register a message event handler."""
        self.event_handlers.append(handler)

    async def send_message(self, msg, thread_id, attachment_path=None):
        """Send a message to a thread."""
        if not self.api:
            log("Cannot send message - not connected", "error")
            return

        try:
            if attachment_path:
                await self.api.sendMessage(
                    msg, thread_id,
                    attachment=attachment_path
                )
            else:
                await self.api.sendMessage(msg, thread_id)
        except Exception as e:
            log(f"Send message error: {e}", "error")

    async def set_message_reaction(self, reaction, message_id):
        """Set a reaction on a message."""
        if not self.api:
            return
        try:
            await self.api.setMessageReaction(reaction, message_id)
        except Exception as e:
            log(f"Reaction error: {e}", "error")

    async def listen(self):
        """Start listening for events with auto-reconnect."""
        if not self.api:
            log("Cannot listen - not logged in", "error")
            return

        restart_interval = self.mqtt_config.get("timeRestart", 300000) / 1000
        delay_after_stop = self.mqtt_config.get("delayAfterStopListening", 2000) / 1000
        enable_restart = self.mqtt_config.get("enable", True)
        log_noti = self.mqtt_config.get("logNoti", True)

        while not self._stop_event.is_set():
            try:
                if log_noti:
                    log("Starting MQTT listener...")

                listen_task = asyncio.create_task(self._listen_loop())

                if enable_restart:
                    await asyncio.sleep(restart_interval)
                    listen_task.cancel()
                    if log_noti:
                        log("Restarting MQTT listener (scheduled restart)...")
                    await asyncio.sleep(delay_after_stop)
                else:
                    await listen_task

            except asyncio.CancelledError:
                break
            except Exception as e:
                log(f"Listen error: {e}", "error")
                if self.config.get("optionsFca", {}).get("autoReconnect", True):
                    log("Auto-reconnecting in 5 seconds...")
                    await asyncio.sleep(5)
                    await self.login()
                else:
                    break

    async def _listen_loop(self):
        """Internal listen loop that processes events."""
        try:
            async for event in self.api.listen():
                if self._stop_event.is_set():
                    break
                for handler in self.event_handlers:
                    try:
                        await handler(event)
                    except Exception as e:
                        log(f"Event handler error: {e}", "error")
                        traceback.print_exc()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log(f"Listen loop error: {e}", "error")

    async def stop(self):
        """Stop the listener."""
        self._stop_event.set()
        self.is_connected = False
        log("FCA API stopped.")

    async def get_user_info(self, user_id):
        """Get user info by ID."""
        if not self.api:
            return {}
        try:
            return await self.api.getUserInfo(user_id)
        except Exception as e:
            log(f"Get user info error: {e}", "error")
            return {}

    async def get_thread_info(self, thread_id):
        """Get thread info by ID."""
        if not self.api:
            return {}
        try:
            return await self.api.getThreadInfo(thread_id)
        except Exception as e:
            log(f"Get thread info error: {e}", "error")
            return {}

    async def add_user_to_group(self, user_id, thread_id):
        """Add a user to a group thread."""
        if not self.api:
            return
        try:
            await self.api.addUserToGroup(user_id, thread_id)
        except Exception as e:
            log(f"Add user error: {e}", "error")

    async def send_friend_request(self, user_id):
        """Send a friend request."""
        if not self.api:
            return
        try:
            await self.api.sendFriendRequest(user_id)
            log(f"Friend request sent to {user_id}")
        except Exception as e:
            log(f"Friend request error: {e}", "error")

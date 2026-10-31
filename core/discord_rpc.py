import os
import time
import threading


DEFAULT_CLIENT_ID = os.environ.get("LOWCORE_DISCORD_CLIENT_ID", "1565068642587123922").strip()


class DiscordRPCManager:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, client_id: str = None):
        self.client_id = (client_id or DEFAULT_CLIENT_ID).strip()
        self.enabled = self.client_id.isdigit()
        self.rpc = None
        self.connected = False
        self.start_time = None
        if self.enabled:
            self._init_connection()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = DiscordRPCManager()
            return cls._instance

    def _init_connection(self):
        def connect():
            try:
                from pypresence import Presence
                self.rpc = Presence(self.client_id)
                self.rpc.connect()
                self.connected = True
                self.set_menu_presence()
            except Exception:
                self.connected = False

        t = threading.Thread(target=connect, daemon=True)
        t.start()

    def set_menu_presence(self):
        if not self.enabled or not self.connected or not self.rpc:
            return
        try:
            self.rpc.update(
                state="Browsing Instances",
                details="Main Menu",
                large_image="logo",
                large_text="LowCore Launcher"
            )
        except Exception:
            pass

    def set_game_presence(self, version: str, loader: str, instance_name: str):
        if not self.enabled or not self.connected or not self.rpc:
            return
        try:
            self.start_time = int(time.time())
            self.rpc.update(
                state=f"Playing {instance_name}",
                details=f"Minecraft {version} ({loader})",
                start=self.start_time,
                large_image="logo",
                large_text="LowCore Launcher"
            )
        except Exception:
            pass
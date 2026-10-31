import os
import copy
import json
from typing import Any, Dict

try:  # optional: pip install keyring  (tokens then live in Windows Credential Manager / Keychain)
    import keyring
except Exception:
    keyring = None


class ConfigManager:
    KEYRING_SERVICE = "LowCoreLauncher"
    SECRET_FIELDS = ("access_token", "refresh_token")

    def __init__(self):
        user_home = os.path.expanduser("~")
        self.config_dir = os.path.join(user_home, ".lowcorelauncher")
        self.config_file = os.path.join(self.config_dir, "launcher_config.json")
        os.makedirs(self.config_dir, exist_ok=True)
        self._kr_cache: Dict[str, str] = {}
        self._known_accounts = set()
        self.data = self._load()
        self._known_accounts = set((self.data.get("accounts") or {}).keys())

    def _default_config(self) -> Dict[str, Any]:
        user_home = os.path.expanduser("~")
        return {
            "game_dir": os.path.join(user_home, ".lowcoreclient"),
            "allocated_ram_mb": 4096,
            "theme_name": "Dark Mode",
            "active_account": "",
            "accounts": {}
        }

    # ------------------------------------------------------------------ keyring helpers

    def _kr_store(self, acc_id: str, field: str, value: str) -> bool:
        key = f"{acc_id}:{field}"
        if self._kr_cache.get(key) == value:
            return True
        try:
            keyring.set_password(self.KEYRING_SERVICE, key, value)
            self._kr_cache[key] = value
            return True
        except Exception:
            return False  # e.g. value too large for the OS vault: keep it in the file instead

    def _kr_fetch(self, acc_id: str, field: str):
        try:
            value = keyring.get_password(self.KEYRING_SERVICE, f"{acc_id}:{field}")
            if value:
                self._kr_cache[f"{acc_id}:{field}"] = value
            return value
        except Exception:
            return None

    def _kr_forget(self, acc_id: str):
        for field in self.SECRET_FIELDS:
            try:
                keyring.delete_password(self.KEYRING_SERVICE, f"{acc_id}:{field}")
            except Exception:
                pass
            self._kr_cache.pop(f"{acc_id}:{field}", None)

    def _hydrate_secrets(self, data: Dict[str, Any]):
        if keyring is None:
            return
        for acc_id, acc in (data.get("accounts") or {}).items():
            if acc.get("type") != "ms":
                continue
            for field in self.SECRET_FIELDS:
                if not acc.get(field):
                    value = self._kr_fetch(acc_id, field)
                    if value:
                        acc[field] = value

    # ------------------------------------------------------------------ load / save

    def _load(self) -> Dict[str, Any]:
        if not os.path.exists(self.config_file):
            default = self._default_config()
            self._save(default)
            return default
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            defaults = self._default_config()
            for k, v in defaults.items():
                if k not in loaded:
                    loaded[k] = v
            self._hydrate_secrets(loaded)
            return loaded
        except Exception:
            # Keep the unreadable file instead of silently overwriting the user's accounts/settings.
            try:
                os.replace(self.config_file, self.config_file + ".corrupt")
            except OSError:
                pass
            return self._default_config()

    def _atomic_write(self, payload: Dict[str, Any]):
        tmp_path = self.config_file + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, self.config_file)

    def _save(self, data: Dict[str, Any]) -> None:
        try:
            payload = copy.deepcopy(data)
            accounts = payload.get("accounts") or {}

            if keyring is not None:
                for acc_id, acc in accounts.items():
                    if acc.get("type") != "ms":
                        continue
                    for field in self.SECRET_FIELDS:
                        value = acc.get(field)
                        if value and self._kr_store(acc_id, field, value):
                            acc[field] = ""  # secret lives in the OS vault, not in the JSON file
                for removed in self._known_accounts - set(accounts.keys()):
                    self._kr_forget(removed)
                self._known_accounts = set(accounts.keys())

            self._atomic_write(payload)
        except Exception as e:
            print(f"[Config Save Error] {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self.data[key] = value
        self._save(self.data)
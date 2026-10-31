import os
import sys
import uuid
import hashlib
import subprocess
import threading
import minecraft_launcher_lib

NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def _library_version_fallback() -> str:
    """Version string for minecraft_launcher_lib when its version.txt is not available."""
    try:
        from importlib.metadata import version
        return version("minecraft-launcher-lib")
    except Exception:
        return "unknown"


def _ensure_launcher_lib_data():
    """
    Packaged builds (PyInstaller etc.) can miss minecraft_launcher_lib's version.txt, which makes
    get_minecraft_command() fail with "[Errno 2] No such file or directory: ...\\version.txt".
    If the file is missing, try to recreate it, and if that is not possible make the library's
    version lookup return a fallback instead of crashing. Does nothing when the file exists.
    """
    try:
        pkg_dir = os.path.dirname(os.path.abspath(minecraft_launcher_lib.__file__))
        version_file = os.path.join(pkg_dir, "version.txt")
        if os.path.exists(version_file):
            return

        fallback = _library_version_fallback()
        try:
            with open(version_file, "w", encoding="utf-8") as f:
                f.write(fallback)
            return
        except OSError:
            pass  # install folder is read-only: patch the lookup instead

        for name, module in list(sys.modules.items()):
            if (name == "minecraft_launcher_lib" or name.startswith("minecraft_launcher_lib.")) \
                    and module is not None and hasattr(module, "get_library_version"):
                setattr(module, "get_library_version", lambda: fallback)
    except Exception:
        pass  # never block a launch because of this safety net


class GameLauncher:
    def __init__(self, base_dir: str, log_callback=None):
        self.base_dir = base_dir
        self.log_callback = log_callback

    def sanitize_uuid(self, account: dict) -> str:
        raw_id = str(account.get("id", "")).strip().replace("-", "")
        uname = account.get("name", "Player")

        if len(raw_id) == 32:
            return f"{raw_id[:8]}-{raw_id[8:12]}-{raw_id[12:16]}-{raw_id[16:20]}-{raw_id[20:]}"

        original_id = str(account.get("id", "")).strip()
        if len(original_id) == 36 and original_id.count("-") == 4:
            return original_id

        return str(uuid.UUID(bytes=hashlib.md5(f"OfflinePlayer:{uname}".encode("utf-8")).digest()[:16]))

    def launch(
        self,
        version_id: str,
        account: dict,
        jvm_args: list,
        instance_dir: str,
        java_bin: str = "java",
        custom_res: dict = None
    ):
        clean_uuid = self.sanitize_uuid(account)
        access_token = account.get("access_token")

        if account.get("type") == "offline" or not access_token:
            access_token = "0"

        options = {
            "username": account.get("name", "Player"),
            "uuid": clean_uuid,
            "token": access_token,
            "gameDirectory": instance_dir,
            "jvmArguments": jvm_args
        }

        # Window size from Settings (main_window passes {"width": .., "height": ..})
        if custom_res and custom_res.get("width") and custom_res.get("height"):
            options["customResolution"] = True
            options["resolutionWidth"] = str(int(custom_res["width"]))
            options["resolutionHeight"] = str(int(custom_res["height"]))

        _ensure_launcher_lib_data()

        cmd = minecraft_launcher_lib.command.get_minecraft_command(
            version=version_id,
            minecraft_directory=self.base_dir,
            options=options
        )

        if java_bin and java_bin != "java":
            cmd[0] = java_bin

        # "Start Fullscreen" checkbox in Settings
        if custom_res and custom_res.get("fullscreen"):
            cmd.append("--fullscreen")

        if self.log_callback:
            self.log_callback(f"[CLIENT] Launching version: {version_id}")
            self.log_callback(f"[CLIENT] Instance Isolated Dir: {instance_dir}")
            self.log_callback(f"[CLIENT] Shared Assets/Libs Dir: {self.base_dir}")
            self.log_callback(f"[CLIENT] Normalized Player UUID: {clean_uuid}")
            self.log_callback(f"[CLIENT] Starting process with {len(cmd)} arguments...")

        process = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,   # a windowed .exe has no console stdin: without this Popen raises WinError 6
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=instance_dir,
            creationflags=NO_WINDOW
        )

        def stream_logs():
            for line in iter(process.stdout.readline, ''):
                if self.log_callback:
                    self.log_callback(line.rstrip())
            process.stdout.close()

        t = threading.Thread(target=stream_logs, daemon=True)
        t.start()

        return process
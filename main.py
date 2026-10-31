import sys
import os
import platform
import getpass
import subprocess
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from core.config import ConfigManager
from ui.main_window import MainWindow


def instance_key() -> str:
    """Per-user name of the local socket used to detect an already-running launcher."""
    try:
        user = getpass.getuser()
    except Exception:
        user = "user"
    safe = "".join(c for c in user if c.isalnum() or c in "-_") or "user"
    return f"lowcore-launcher-{safe}"


def notify_running_instance(key: str) -> bool:
    """If a launcher is already running, ask it to show itself and return True."""
    sock = QLocalSocket()
    sock.connectToServer(key)
    if not sock.waitForConnected(500):
        return False

    if platform.system() == "Windows":
        try:
            import ctypes
            # Let the running launcher take the foreground (Windows blocks background focus steals).
            ctypes.windll.user32.AllowSetForegroundWindow(-1)
        except Exception:
            pass

    sock.write(b"show")
    sock.flush()
    sock.waitForBytesWritten(500)
    # The running launcher closes the connection after it has raised its window.
    sock.waitForDisconnected(1500)
    return True


def main():
    # Keep the official App ID so Windows binds the taskbar icon cleanly
    if platform.system() == "Windows":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("lowcore.launcher.client.v1")
        except Exception:
            pass

    # Qt6 handles High-DPI scaling automatically (the Qt5 AA_* attributes no longer exist).

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # ---- Single instance: a second launch just brings the first window back ----
    key = instance_key()
    if notify_running_instance(key):
        sys.exit(0)

    state = {"window": None, "pending_show": False}
    server = QLocalServer()
    server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
    QLocalServer.removeServer(key)  # clears a stale socket left behind by a crash

    def show_existing_window():
        window = state["window"]
        if window is None:
            state["pending_show"] = True  # still starting up: show as soon as it exists
        else:
            window.show_from_tray()

    def on_new_connection():
        conn = server.nextPendingConnection()
        if conn is None:
            return
        show_existing_window()
        conn.disconnected.connect(conn.deleteLater)
        conn.disconnectFromServer()

    server.newConnection.connect(on_new_connection)
    server.listen(key)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    ico_path = os.path.join(base_dir, "assets", "logo.ico")
    png_path = os.path.join(base_dir, "assets", "logo.png")

    target_icon = ico_path if os.path.exists(ico_path) else png_path
    if os.path.exists(target_icon):
        app.setWindowIcon(QIcon(target_icon))

    config = ConfigManager()
    window = MainWindow(config)
    state["window"] = window

    # Let Qt handle taskbar assignment natively without Win32 SetClassLong pointer manipulation
    if os.path.exists(target_icon):
        window.setWindowIcon(QIcon(target_icon))

    window.show()
    if state["pending_show"]:
        window.show_from_tray()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
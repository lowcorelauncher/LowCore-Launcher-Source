import os
import sys
import json
import time
import shutil
import webbrowser
import subprocess
import psutil
import requests
import ctypes
import html
from PyQt6 import sip
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QPlainTextEdit, QLineEdit, QListWidget, QListWidgetItem,
    QProgressBar, QFrame, QMessageBox, QDialog, QRadioButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSpinBox,
    QFileDialog, QInputDialog, QGraphicsOpacityEffect, QStackedWidget,
    QSystemTrayIcon, QMenu, QCheckBox, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import (
    Qt, QRunnable, QThreadPool, pyqtSignal, QObject, QSize,
    QPropertyAnimation, QEasingCurve, QRect, QPoint, QTimer, pyqtProperty, QEvent
)
from PyQt6.QtGui import QPixmap, QImage, QIcon, QKeyEvent, QAction, QTextCursor
from PyQt6.QtNetwork import QNetworkProxy

from core.config import ConfigManager
from core.auth_service import AuthService
from core.version_downloader import VersionDownloader
from core.optimization import OptimizationEngine
from core.game_launcher import GameLauncher
from core.theme_manager import ThemeManager
from core.instance_manager import InstanceManager
from core.modrinth_service import ModrinthService
from core.avatar_service import AvatarService
from core.java_manager import JavaManager
from core.discord_rpc import DiscordRPCManager


if sys.platform == "win32":
    try:
        myappid = "lowcore.launcher.client.beta"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass


ICON_SESSION = requests.Session()
ICON_SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 LowCoreLauncher/1.0"
})
ICON_CACHE = {}


def crop_transparent_padding(pixmap: QPixmap) -> QPixmap:
    """Trims transparent border pixels so the icon fills 100% of the system tray slot."""
    if pixmap.isNull():
        return pixmap
    img = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    w, h = img.width(), img.height()
    min_x, min_y, max_x, max_y = w, h, -1, -1

    for y in range(h):
        for x in range(w):
            if img.pixelColor(x, y).alpha() > 15:
                if x < min_x:
                    min_x = x
                if x > max_x:
                    max_x = x
                if y < min_y:
                    min_y = y
                if y > max_y:
                    max_y = y

    if max_x >= min_x and max_y >= min_y:
        bw = max_x - min_x + 1
        bh = max_y - min_y + 1
        side = max(bw, bh)
        cx = min_x + bw // 2
        cy = min_y + bh // 2
        x0 = max(0, cx - side // 2)
        y0 = max(0, cy - side // 2)
        side = min(side, w - x0, h - y0)
        return pixmap.copy(x0, y0, side, side)
    return pixmap


TRANSLATIONS = {
    "en": {
        "tab_play": "Play",
        "tab_mods": "Content Browser",
        "tab_settings": "Settings",
        "tab_console": "Console Log",
        "kill_mc": "Kill Minecraft",
        "active_inst": "Active Isolated Instance",
        "account": "Account",
        "ram_alloc": "Global High-Performance Memory Allocation",
        "play": "PLAY",
        "ready": "Ready to launch",
        "search_mods": "Search Mods, Resource Packs & Shaders...",
        "search": "Search",
        "download_mod": "Download to Selected Instance",
        "client_theme": "Client Theme",
        "folders": "Folders",
        "browse": "Browse",
        "language": "Language",
        "accounts_mgmt": "Accounts Management",
        "proxy_title": "Launcher Proxy Settings",
        "proxy_notice": "This only applies to the launcher. Minecraft does not accept proxy settings.",
        "apply_proxy": "Apply Proxy Settings",
        "new_instance": "+ New Instance",
        "add_offline": "+ Offline",
        "add_ms": "+ Microsoft",
        "remove": "Remove"
    },
    "ar": {
        "tab_play": "تشغيل",
        "tab_mods": "متصفح الإضافات",
        "tab_settings": "الإعدادات",
        "tab_console": "سجل الأوامر",
        "kill_mc": "إغلاق اللعبة إجبارياً",
        "active_inst": "النسخة الحالية المعزولة",
        "account": "الحساب",
        "ram_alloc": "تخصيص الرام عالي الأداء",
        "play": "ابدأ اللعب",
        "ready": "جاهز للتشغيل",
        "search_mods": "ابحث عن المودات، الحزم والمؤثرات...",
        "search": "بحث",
        "download_mod": "تحميل للنسخة المحددة",
        "client_theme": "سمة المظهر",
        "folders": "المجلدات",
        "browse": "استعراض",
        "language": "اللغة",
        "accounts_mgmt": "إدارة الحسابات",
        "proxy_title": "إعدادات البروكسي للمشغل",
        "proxy_notice": "هذا ينطبق فقط على المشغل. ماينكرافت لا تدعم البروكسي.",
        "apply_proxy": "تطبيق إعدادات البروكسي",
        "new_instance": "+ نسخة جديدة",
        "add_offline": "+ أوفلاين",
        "add_ms": "+ مايكروسوفت",
        "remove": "حذف"
    },
    "de": {
        "tab_play": "Spielen",
        "tab_mods": "Content-Browser",
        "tab_settings": "Einstellungen",
        "tab_console": "Konsole",
        "kill_mc": "Minecraft beenden",
        "active_inst": "Aktive Instanz",
        "account": "Konto",
        "ram_alloc": "Globale RAM-Zuweisung",
        "play": "SPIELEN",
        "ready": "Bereit zum Starten",
        "search_mods": "Suche nach Mods, Resource Packs & Shadern...",
        "search": "Suchen",
        "download_mod": "In ausgewählte Instanz herunterladen",
        "client_theme": "Erscheinungsbild",
        "folders": "Ordner",
        "browse": "Durchsuchen",
        "language": "Sprache",
        "accounts_mgmt": "Kontoverwaltung",
        "proxy_title": "Proxy-Einstellungen",
        "proxy_notice": "Gilt nur für den Launcher. Minecraft unterstützt keine Proxys.",
        "apply_proxy": "Proxy anwenden",
        "new_instance": "+ Neue Instanz",
        "add_offline": "+ Offline",
        "add_ms": "+ Microsoft",
        "remove": "Entfernen"
    }
}


class I18n:
    _current_lang = "en"

    @classmethod
    def set_language(cls, code: str):
        if code in TRANSLATIONS:
            cls._current_lang = code

    @classmethod
    def get_language(cls) -> str:
        return cls._current_lang

    @classmethod
    def t(cls, key: str) -> str:
        return TRANSLATIONS.get(cls._current_lang, {}).get(key, TRANSLATIONS["en"].get(key, key))


class AnimatedButton(QPushButton):
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class ClickableLetterLabel(QLabel):
    clicked = pyqtSignal(str)

    def __init__(self, char: str, parent=None):
        super().__init__(char, parent)
        self.char = char
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.char.lower())
        super().mousePressEvent(event)


class ScalingLogoLabel(QLabel):
    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.original_pixmap = pixmap
        self._target_size = 140
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background: transparent; border: none;")

    @pyqtProperty(int)
    def target_size(self) -> int:
        return self._target_size

    @target_size.setter
    def target_size(self, size: int):
        self._target_size = size
        self.setFixedSize(size, size)
        scaled = self.original_pixmap.scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(scaled)


def format_log_line_html(line: str, theme_name: str = "Dark Mode") -> str:
    escaped = html.escape(line)
    upper = line.upper()
    light = ThemeManager.is_light(theme_name)

    if any(k in upper for k in ["[ERROR]", "ERROR", "FATAL", "EXCEPTION", "CRASH", "FAILED", "OS::COMMIT_MEMORY"]):
        color = "#C62828" if light else "#FF5555"
    elif any(k in upper for k in ["[WARN]", "[WARNING]", "WARN"]):
        color = "#B26A00" if light else "#FFB86C"
    elif any(k in upper for k in ["[AUTH]", "[CLIENT]", "[LAUNCH]"]):
        color = "#1E8E3E" if light else "#50FA7B"
    elif any(k in upper for k in ["[DEBUG]", "FINE", "TRACE"]):
        color = "#8A909E"
    else:
        color = "#1A1B1E" if light else "#F8F8F2"

    return f'<span style="color: {color}; font-family: Consolas, monospace; font-size: 12px; line-height: 1.4;">{escaped}</span><br>'


def format_playtime(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    rem_min = minutes % 60
    return f"{hours}h {rem_min}m"


def format_last_played(timestamp) -> str:
    if not timestamp:
        return "Never"
    try:
        delta = time.time() - float(timestamp)
    except (TypeError, ValueError):
        return "Never"
    if delta < 60:
        return "Just now"
    if delta < 3600:
        return f"{int(delta // 60)}m ago"
    if delta < 86400:
        return f"{int(delta // 3600)}h ago"
    days = int(delta // 86400)
    if days == 1:
        return "Yesterday"
    if days < 30:
        return f"{days}d ago"
    return time.strftime("%b %d, %Y", time.localtime(float(timestamp)))


class ModManagerDialog(QDialog):
    def __init__(self, mods_dir: str, theme_name: str, parent=None):
        super().__init__(parent)
        self.mods_dir = mods_dir
        self.theme_name = theme_name
        self.setWindowTitle("Manage Installed Mods - LowCore Launcher")
        self.resize(560, 480)

        t = ThemeManager.get_theme_data(theme_name)
        self.setStyleSheet(f"""
            {ThemeManager.get_style(theme_name)}
            QDialog {{ background-color: {t['card_bg']}; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        header = QLabel("Installed Mods (Check to enable, uncheck to disable)")
        header.setObjectName("SectionLabel")
        layout.addWidget(header)

        self.list_widget = QListWidget()
        self.list_widget.setObjectName("ModsList")
        layout.addWidget(self.list_widget)

        self.load_mods()

        footer = QHBoxLayout()
        footer.addStretch()

        btn_close = AnimatedButton("Done")
        btn_close.setObjectName("PlayButton")
        btn_close.setFixedWidth(100)
        btn_close.clicked.connect(self.accept)
        footer.addWidget(btn_close)
        layout.addLayout(footer)

    def load_mods(self):
        self.list_widget.clear()
        if not os.path.exists(self.mods_dir):
            return

        t = ThemeManager.get_theme_data(self.theme_name)
        files = sorted(os.listdir(self.mods_dir))
        for filename in files:
            if not (filename.endswith(".jar") or filename.endswith(".jar.disabled")):
                continue

            is_enabled = filename.endswith(".jar")
            display_name = filename.replace(".disabled", "")

            item = QListWidgetItem(self.list_widget)
            item.setSizeHint(QSize(self.list_widget.width() - 20, 42))

            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(8, 4, 8, 4)

            chk = QCheckBox(display_name)
            chk.setChecked(is_enabled)
            chk.setCursor(Qt.CursorShape.PointingHandCursor)
            chk.setStyleSheet(f"""
                QCheckBox {{
                    color: {t['text']};
                    font-size: 13px;
                    font-weight: 600;
                    spacing: 8px;
                    background: transparent;
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    border: 1px solid {t['border']};
                    border-radius: 4px;
                    background-color: {t['pill_bg']};
                }}
                QCheckBox::indicator:hover {{
                    border-color: {t['accent']};
                    background-color: {t['pill_hover']};
                }}
                QCheckBox::indicator:checked {{
                    background-color: {t['accent']};
                    border-color: {t['accent']};
                }}
            """)
            chk.toggled.connect(lambda state, fn=filename: self.toggle_mod(fn, state))
            row_layout.addWidget(chk)
            row_layout.addStretch()

            self.list_widget.setItemWidget(item, row_widget)

    def toggle_mod(self, original_filename: str, enable: bool):
        cur_path = os.path.join(self.mods_dir, original_filename)
        if enable and original_filename.endswith(".disabled"):
            new_name = original_filename.replace(".disabled", "")
            new_path = os.path.join(self.mods_dir, new_name)
            if os.path.exists(cur_path):
                os.rename(cur_path, new_path)
        elif not enable and not original_filename.endswith(".disabled"):
            new_name = original_filename + ".disabled"
            new_path = os.path.join(self.mods_dir, new_name)
            if os.path.exists(cur_path):
                os.rename(cur_path, new_path)
        self.load_mods()


class LogViewerDialog(QDialog):
    def __init__(self, log_lines: list, theme_name: str, app_icon: QIcon = None, parent=None):
        super().__init__(parent)
        self.theme_name = theme_name
        self.raw_logs = list(log_lines)
        self.setWindowTitle("Minecraft Execution Log - LowCore Launcher")
        self.resize(780, 520)
        if app_icon:
            self.setWindowIcon(app_icon)

        t = ThemeManager.get_theme_data(theme_name)
        base_style = ThemeManager.get_style(theme_name)
        self.setStyleSheet(f"""
            {base_style}
            QDialog {{ background-color: {t['card_bg']}; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)

        title_label = QLabel("Game Execution & Crash Log")
        title_label.setObjectName("SectionLabel")
        header_layout.addWidget(title_label)
        header_layout.addStretch()

        self.btn_copy = AnimatedButton("Copy Log")
        self.btn_copy.setObjectName("PillButton")
        self.btn_copy.setMinimumWidth(110)
        self.btn_copy.setStyleSheet("padding: 5px 14px;")
        self.btn_copy.clicked.connect(self.copy_log)
        header_layout.addWidget(self.btn_copy)

        self.btn_save = AnimatedButton("Save to File")
        self.btn_save.setObjectName("PillButton")
        self.btn_save.setMinimumWidth(110)
        self.btn_save.setStyleSheet("padding: 5px 14px;")
        self.btn_save.clicked.connect(self.save_log)
        header_layout.addWidget(self.btn_save)

        layout.addLayout(header_layout)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)

        self.search_filter = QLineEdit()
        self.search_filter.setPlaceholderText("Filter lines (e.g. error, sodium, memory)...")
        self.search_filter.textChanged.connect(self.refresh_display)
        filter_row.addWidget(self.search_filter, stretch=2)

        self.btn_filter_all = AnimatedButton("All")
        self.btn_filter_all.setObjectName("PillButton")
        self.btn_filter_all.setMinimumWidth(60)
        self.btn_filter_all.setStyleSheet("padding: 4px 10px;")
        self.btn_filter_all.clicked.connect(lambda: self.set_severity_filter("ALL"))
        filter_row.addWidget(self.btn_filter_all)

        self.btn_filter_err = AnimatedButton("Errors")
        self.btn_filter_err.setObjectName("PillButton")
        self.btn_filter_err.setMinimumWidth(75)
        self.btn_filter_err.setStyleSheet("color: #FF5555; border: 1px solid rgba(255, 85, 85, 0.4); padding: 4px 10px;")
        self.btn_filter_err.clicked.connect(lambda: self.set_severity_filter("ERRORS"))
        filter_row.addWidget(self.btn_filter_err)

        self.btn_filter_warn = AnimatedButton("Warnings")
        self.btn_filter_warn.setObjectName("PillButton")
        self.btn_filter_warn.setMinimumWidth(85)
        self.btn_filter_warn.setStyleSheet("color: #FFB86C; border: 1px solid rgba(255, 184, 108, 0.4); padding: 4px 10px;")
        self.btn_filter_warn.clicked.connect(lambda: self.set_severity_filter("WARNS"))
        filter_row.addWidget(self.btn_filter_warn)

        layout.addLayout(filter_row)

        self.current_severity = "ALL"
        self.text_edit = QPlainTextEdit()
        self.text_edit.setObjectName("ConsoleLog")
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

        footer_layout = QHBoxLayout()
        footer_layout.addStretch()

        btn_close = AnimatedButton("Close")
        btn_close.setObjectName("PlayButton")
        btn_close.setFixedWidth(110)
        btn_close.clicked.connect(self.accept)
        footer_layout.addWidget(btn_close)

        layout.addLayout(footer_layout)
        self.refresh_display()

    def set_severity_filter(self, mode: str):
        self.current_severity = mode
        self.refresh_display()

    def refresh_display(self):
        query = self.search_filter.text().strip().lower()
        self.text_edit.clear()
        html_chunks = []

        for line in self.raw_logs:
            lower_line = line.lower()
            if query and query not in lower_line:
                continue

            upper = line.upper()
            if self.current_severity == "ERRORS":
                if not any(k in upper for k in ["[ERROR]", "ERROR", "FATAL", "EXCEPTION", "CRASH", "FAILED", "OS::COMMIT_MEMORY"]):
                    continue
            elif self.current_severity == "WARNS":
                if not any(k in upper for k in ["[WARN]", "[WARNING]", "WARN"]):
                    continue

            html_chunks.append(format_log_line_html(line, self.theme_name))

        self.text_edit.appendHtml("".join(html_chunks))
        self.text_edit.moveCursor(QTextCursor.MoveOperation.End)

    def copy_log(self):
        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(self.raw_logs))
        self.btn_copy.setText("Copied!")
        QTimer.singleShot(1500, lambda: self.btn_copy.setText("Copy Log"))

    def save_log(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Minecraft Log", os.path.expanduser("~/minecraft_log.txt"), "Text Files (*.txt);;All Files (*)"
        )
        if file_path:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("\n".join(self.raw_logs))
            self.btn_save.setText("Saved!")
            QTimer.singleShot(1500, lambda: self.btn_save.setText("Save to File"))


class ModItemCard(QFrame):
    def __init__(self, item_data: dict, theme_data: dict, parent=None):
        super().__init__(parent)
        self.setObjectName("ModItemCard")
        self.item_data = item_data
        self.theme_data = theme_data
        self.is_selected = False
        self.setFixedHeight(68)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 14, 8)
        layout.setSpacing(14)

        self.icon_label = QLabel()
        self.icon_label.setFixedSize(44, 44)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setStyleSheet("background-color: rgba(255, 255, 255, 0.05); border-radius: 8px; border: none;")
        layout.addWidget(self.icon_label)

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)

        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        self.title_label = QLabel(item_data.get("title", "Unknown Mod"))
        self.title_label.setStyleSheet(f"font-size: 14px; font-weight: 800; color: {self.theme_data['text']}; border: none; background: transparent;")
        top_row.addWidget(self.title_label)

        author = item_data.get("author", "")
        if author:
            self.author_label = QLabel(f"by {author}")
            self.author_label.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {self.theme_data['text_sub']}; border: none; background: transparent;")
            top_row.addWidget(self.author_label)

        top_row.addStretch()

        downloads = item_data.get("downloads", 0)
        if downloads:
            d_str = f"{downloads:,}" if downloads < 1000 else f"{downloads // 1000}k"
            self.dl_label = QLabel(f"↓ {d_str}")
            self.dl_label.setStyleSheet(f"font-size: 11px; font-weight: 700; color: {self.theme_data['accent']}; border: none; background: transparent;")
            top_row.addWidget(self.dl_label)

        info_layout.addLayout(top_row)

        desc_text = item_data.get("description", "").strip()
        if len(desc_text) > 85:
            desc_text = desc_text[:85] + "..."
        self.desc_label = QLabel(desc_text)
        self.desc_label.setStyleSheet(f"font-size: 12px; font-weight: 500; color: {self.theme_data['text_sub']}; border: none; background: transparent;")
        info_layout.addWidget(self.desc_label)

        layout.addLayout(info_layout, stretch=1)
        self.update_appearance()

    def set_selected_state(self, selected: bool):
        self.is_selected = selected
        self.update_appearance()

    def update_appearance(self):
        t = self.theme_data
        if self.is_selected:
            self.setStyleSheet(f"""
                QFrame#ModItemCard {{
                    background-color: {t['item_hover']};
                    border: 1px solid {t['accent']};
                    border-left: 4px solid {t['accent']};
                    border-radius: 8px;
                }}
                QLabel {{ border: none; background: transparent; }}
            """)
        else:
            self.setStyleSheet(f"""
                QFrame#ModItemCard {{
                    background-color: {t['pill_bg']};
                    border: 1px solid {t['border']};
                    border-left: 1px solid {t['border']};
                    border-radius: 8px;
                }}
                QFrame#ModItemCard:hover {{
                    background-color: {t['pill_hover']};
                    border-color: {t['text_sub']};
                }}
                QLabel {{ border: none; background: transparent; }}
            """)

    def set_thumbnail(self, pixmap: QPixmap):
        if sip.isdeleted(self) or sip.isdeleted(self.icon_label):
            return
        if not pixmap.isNull():
            scaled = pixmap.scaled(44, 44, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            self.icon_label.setPixmap(scaled)
            self.icon_label.setStyleSheet("border-radius: 8px; border: none; background: transparent;")


class IconDownloadSignals(QObject):
    loaded = pyqtSignal(bytes)


class ModIconLoader(QRunnable):
    def __init__(self, icon_url: str):
        super().__init__()
        self.icon_url = icon_url
        self.signals = IconDownloadSignals()

    def run(self):
        if not self.icon_url:
            return
        if self.icon_url in ICON_CACHE:
            self.signals.loaded.emit(ICON_CACHE[self.icon_url])
            return
        try:
            res = ICON_SESSION.get(self.icon_url, timeout=5)
            if res.status_code == 200 and res.content:
                ICON_CACHE[self.icon_url] = res.content
                self.signals.loaded.emit(res.content)
        except Exception:
            pass


class ContentTypeBar(QWidget):
    type_changed = pyqtSignal(str)

    def __init__(self, theme_data: dict, parent=None):
        super().__init__(parent)
        self.theme_data = theme_data
        self.setFixedHeight(34)
        self.types = [("Mods", "mod"), ("Resource Packs", "resourcepack"), ("Shaders", "shader")]
        self.buttons = []
        self.current_idx = 0

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        for idx, (label, val) in enumerate(self.types):
            btn = QPushButton(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, i=idx: self.select_index(i))
            layout.addWidget(btn)
            self.buttons.append(btn)

        self.apply_styles()

    def select_index(self, idx: int):
        self.current_idx = idx
        self.apply_styles()
        self.type_changed.emit(self.types[idx][1])

    def get_selected_type(self) -> str:
        return self.types[self.current_idx][1]

    def apply_styles(self):
        t = self.theme_data
        for i, btn in enumerate(self.buttons):
            if i == self.current_idx:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {t['accent']};
                        color: {t.get('accent_text', '#FFFFFF')};
                        font-size: 11px;
                        font-weight: 800;
                        padding: 6px 10px;
                        border: none;
                        border-radius: 6px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {t['pill_bg']};
                        color: {t['text_sub']};
                        font-size: 11px;
                        font-weight: 700;
                        padding: 6px 10px;
                        border: 1px solid {t['border']};
                        border-radius: 6px;
                    }}
                    QPushButton:hover {{
                        color: {t['text']};
                        background-color: {t['pill_hover']};
                    }}
                """)


class DropdownItemWidget(QFrame):
    row_clicked = pyqtSignal(int)
    delete_clicked = pyqtSignal(int)

    def __init__(self, index: int, text: str, icon: QPixmap = None, enable_delete: bool = False, theme_data: dict = None, parent=None):
        super().__init__(parent)
        self.index = index
        self.enable_delete = enable_delete
        self.setObjectName("DropdownRowWidget")
        self.setFixedHeight(38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        t_data = theme_data or ThemeManager.get_theme_data("Dark Mode")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 2, 8, 2)
        layout.setSpacing(8)

        if icon:
            icon_lbl = QLabel()
            icon_lbl.setFixedSize(22, 22)
            icon_lbl.setPixmap(icon.scaled(22, 22, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            icon_lbl.setStyleSheet("background: transparent; border: none;")
            layout.addWidget(icon_lbl)

        self.text_lbl = QLabel(text)
        self.text_lbl.setStyleSheet(f"font-size: 13px; font-weight: 600; color: {t_data['text']}; background: transparent; border: none;")
        layout.addWidget(self.text_lbl, stretch=1)

        if self.enable_delete:
            self.del_btn = QPushButton("🗑")
            self.del_btn.setObjectName("DropdownDeleteBtn")
            self.del_btn.setFixedSize(28, 28)
            self.del_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self.del_btn.clicked.connect(lambda: self.delete_clicked.emit(self.index))
            layout.addWidget(self.del_btn)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.row_clicked.emit(self.index)
        super().mousePressEvent(event)


class DropdownPopup(QWidget):
    item_selected = pyqtSignal(int)
    item_deleted = pyqtSignal(int)
    closed = pyqtSignal()

    MAX_VISIBLE_ROWS = 7  # longer lists (e.g. the theme picker) scroll instead of running off screen

    def __init__(self, items: list, width: int, enable_delete: bool = False, theme_data: dict = None, parent=None, current_index: int = -1):
        super().__init__(parent, Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        self._owner = parent
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        popup_width = max(width, 360) if enable_delete else width
        self.setFixedWidth(popup_width)

        t_data = theme_data or ThemeManager.get_theme_data("Dark Mode")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.container = QFrame()
        self.container.setObjectName("DropdownPopupFrame")
        c_layout = QVBoxLayout(self.container)
        c_layout.setContentsMargins(4, 4, 4, 4)
        c_layout.setSpacing(2)

        self._scroll = None
        self._row_widgets = []
        self._focus_idx = current_index
        if len(items) > self.MAX_VISIBLE_ROWS:
            self._scroll = QScrollArea()
            self._scroll.setFrameShape(QFrame.Shape.NoFrame)
            self._scroll.setWidgetResizable(True)
            self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            self._scroll.viewport().setAutoFillBackground(False)
            self._scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
            rows_host = QWidget()
            rows_host.setObjectName("DropdownRows")
            rows_host.setStyleSheet("QWidget#DropdownRows { background: transparent; }")
            rows_layout = QVBoxLayout(rows_host)
            rows_layout.setContentsMargins(0, 0, 0, 0)
            rows_layout.setSpacing(2)
            self._scroll.setWidget(rows_host)
            # QScrollArea.setWidget() switches autoFillBackground back ON (grey box), so turn it off AFTER.
            rows_host.setAutoFillBackground(False)
            self._scroll.viewport().setAutoFillBackground(False)
            self._scroll.setFixedHeight(self.MAX_VISIBLE_ROWS * 38 + (self.MAX_VISIBLE_ROWS - 1) * 2)
            c_layout.addWidget(self._scroll)
            rows_parent = rows_host
        else:
            rows_layout = c_layout
            rows_parent = self.container

        for idx, entry in enumerate(items):
            text = entry[0] if isinstance(entry, (tuple, list)) else entry
            icon = entry[2] if isinstance(entry, (tuple, list)) and len(entry) > 2 else None

            row_widget = DropdownItemWidget(
                idx, text, icon=icon,
                enable_delete=enable_delete,
                theme_data=t_data,
                parent=rows_parent
            )
            row_widget.row_clicked.connect(self.on_item_chosen)
            row_widget.delete_clicked.connect(self.on_item_delete_req)
            rows_layout.addWidget(row_widget)
            self._row_widgets.append(row_widget)

        layout.addWidget(self.container)
        self.adjustSize()

    def showEvent(self, event):
        super().showEvent(event)
        QApplication.instance().installEventFilter(self)
        if self._scroll is not None and 0 <= self._focus_idx < len(self._row_widgets):
            QTimer.singleShot(0, self._reveal_current)

    def _reveal_current(self):
        try:
            self._scroll.ensureWidgetVisible(self._row_widgets[self._focus_idx], 0, 6)
        except RuntimeError:
            pass  # popup already closed

    def hideEvent(self, event):
        QApplication.instance().removeEventFilter(self)
        super().hideEvent(event)
        self.closed.emit()

    def eventFilter(self, obj, event):
        t = event.type()
        if t == QEvent.Type.MouseButtonPress:
            gp = event.globalPosition().toPoint()
            if not self.frameGeometry().contains(gp):
                owner = self._owner
                on_owner = owner is not None and owner.rect().contains(owner.mapFromGlobal(gp))
                self.close()
                if on_owner:
                    return True
        elif t == QEvent.Type.ApplicationDeactivate:
            self.close()
        elif t == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape:
            self.close()
            return True
        return False

    def on_item_chosen(self, idx: int):
        self._dismiss_then(self.item_selected, idx)

    def on_item_delete_req(self, idx: int):
        self._dismiss_then(self.item_deleted, idx)

    def _dismiss_then(self, signal, idx: int):
        # Hide now, emit on the next tick, and only THEN close (WA_DeleteOnClose):
        # closing first could delete the popup before the deferred emit ran.
        self.hide()

        def fire():
            signal.emit(idx)
            self.close()

        QTimer.singleShot(0, fire)


class CustomDropdown(QPushButton):
    currentIndexChanged = pyqtSignal(int)
    deleteRequested = pyqtSignal(int)

    def __init__(self, enable_delete: bool = False, parent=None):
        super().__init__(parent)
        self.setObjectName("CustomCombo")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.items = []
        self.current_idx = -1
        self.is_placeholder_mode = False
        self.enable_delete = enable_delete
        self.popup = None

        self.clicked.connect(self.show_dropdown)

    def set_placeholder_mode(self, enabled: bool):
        self.is_placeholder_mode = enabled

    def clear(self):
        self.items.clear()
        self.current_idx = -1
        self.setText("")
        self.setIcon(QIcon())

    def addItem(self, text: str, userData=None, icon: QPixmap = None):
        self.items.append((text, userData, icon))
        if self.current_idx == -1:
            self.setCurrentIndex(0)

    def addItems(self, texts: list):
        for t in texts:
            self.addItem(t, userData=t)

    def count(self) -> int:
        return len(self.items)

    def currentText(self) -> str:
        if 0 <= self.current_idx < len(self.items):
            return self.items[self.current_idx][0]
        return ""

    def currentData(self):
        if 0 <= self.current_idx < len(self.items):
            return self.items[self.current_idx][1]
        return None

    def setCurrentIndex(self, index: int):
        if 0 <= index < len(self.items):
            self.current_idx = index
            item_text = self.items[index][0]
            item_icon = self.items[index][2]

            self.setText(f"{item_text}   ▾")
            if item_icon:
                self.setIcon(QIcon(item_icon))
            else:
                self.setIcon(QIcon())
            self.currentIndexChanged.emit(index)

    def setCurrentText(self, text: str):
        for idx, (t, _, _) in enumerate(self.items):
            if t == text:
                self.setCurrentIndex(idx)
                break

    def itemData(self, index: int):
        if 0 <= index < len(self.items):
            return self.items[index][1]
        return None

    def show_dropdown(self):
        if self.is_placeholder_mode:
            p = self.window()
            if hasattr(p, "prompt_new_instance"):
                p.prompt_new_instance()
            return

        if not self.items:
            return

        main_win = self.window()
        cur_theme = getattr(main_win, "current_theme", "Dark Mode")
        theme_data = ThemeManager.get_theme_data(cur_theme)

        self.popup = DropdownPopup(
            self.items,
            self.width(),
            enable_delete=self.enable_delete,
            theme_data=theme_data,
            parent=self,
            current_index=self.current_idx
        )
        self.popup.setStyleSheet(ThemeManager.get_style(cur_theme))
        self.popup.item_selected.connect(self.setCurrentIndex)
        self.popup.item_deleted.connect(lambda idx: self.deleteRequested.emit(idx))
        self.popup.closed.connect(lambda: setattr(self, "popup", None))

        pos = self.mapToGlobal(QPoint(0, self.height() + 4))
        screen = self.screen()
        if screen is not None:
            popup_h = self.popup.sizeHint().height()
            if pos.y() + popup_h > screen.availableGeometry().bottom():
                pos = self.mapToGlobal(QPoint(0, -popup_h - 4))  # not enough room below: open upwards
        self.popup.move(pos)
        self.popup.show()


class AnimatedNavBar(QWidget):
    tab_changed = pyqtSignal(int)

    def __init__(self, tabs: list, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.buttons = []
        self.current_index = 0
        self.active_color = "#FFFFFF"
        self.inactive_color = "#8A909E"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(24)

        for idx, title in enumerate(tabs):
            btn = QPushButton(title)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, i=idx: self.select_tab(i))
            layout.addWidget(btn)
            self.buttons.append(btn)

        layout.addStretch()

        self.indicator = QFrame(self)
        self.indicator.setFixedHeight(3)
        self.indicator.setStyleSheet("background-color: #E85A52; border-radius: 1.5px;")
        self.anim = None

    def set_theme_colors(self, active_color: str, inactive_color: str = "#8A909E", accent_color: str = "#E85A52"):
        self.active_color = active_color
        self.inactive_color = inactive_color
        self.indicator.setStyleSheet(f"background-color: {accent_color}; border-radius: 1.5px;")
        self.refresh_styles()

    def refresh_styles(self):
        for i, btn in enumerate(self.buttons):
            if i == self.current_index:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        border: none;
                        color: {self.active_color};
                        font-size: 14px;
                        font-weight: 800;
                        padding: 8px 4px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: transparent;
                        border: none;
                        color: {self.inactive_color};
                        font-size: 14px;
                        font-weight: 700;
                        padding: 8px 4px;
                    }}
                    QPushButton:hover {{
                        color: {self.active_color};
                    }}
                """)

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_styles()
        self.update_indicator_position(instant=True)

    def select_tab(self, index: int):
        if index < 0 or index >= len(self.buttons):
            return
        self.current_index = index
        self.tab_changed.emit(index)
        self.refresh_styles()
        self.update_indicator_position()

    def update_indicator_position(self, instant=False):
        if not self.buttons:
            return
        btn = self.buttons[self.current_index]
        target_x = btn.x()
        target_w = btn.width()
        target_rect = QRect(target_x, self.height() - 3, target_w, 3)

        if instant:
            self.indicator.setGeometry(target_rect)
        else:
            self.anim = QPropertyAnimation(self.indicator, b"geometry")
            self.anim.setDuration(240)
            self.anim.setStartValue(self.indicator.geometry())
            self.anim.setEndValue(target_rect)
            self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.anim.start()


class WorkerSignals(QObject):
    progress = pyqtSignal(str, int, int)
    log = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)


class ModSearchSignals(QObject):
    results_ready = pyqtSignal(list)
    error = pyqtSignal(str)


class ModInstallSignals(QObject):
    status = pyqtSignal(str)
    completed = pyqtSignal(list)
    error = pyqtSignal(str)


class ModInstallWorker(QRunnable):
    def __init__(self, project_id: str, version: str, loader: str, target_dir: str):
        super().__init__()
        self.project_id = project_id
        self.version = version
        self.loader = loader
        self.target_dir = target_dir
        self.signals = ModInstallSignals()

    def run(self):
        try:
            installed = ModrinthService.download_with_dependencies(
                self.project_id,
                self.version,
                self.loader,
                self.target_dir,
                progress_cb=lambda msg: self.signals.status.emit(msg)
            )
            self.signals.completed.emit(installed)
        except Exception as e:
            self.signals.error.emit(str(e))


class ModSearchWorker(QRunnable):
    def __init__(self, query: str, version: str, loader: str, p_type: str):
        super().__init__()
        self.query = query
        self.version = version
        self.loader = loader
        self.p_type = p_type
        self.signals = ModSearchSignals()

    def run(self):
        try:
            hits = ModrinthService.search_content(self.query, version=self.version, loader=self.loader, project_type=self.p_type)
            self.signals.results_ready.emit(hits)
        except Exception as e:
            self.signals.error.emit(str(e))


class LaunchWorker(QRunnable):
    def __init__(self, inst_mgr: InstanceManager, root_dir: str, instance_dir: str, version_id: str, loader: str, account: dict, ram_mb: int, custom_res: dict = None, parent_win=None):
        super().__init__()
        self.inst_mgr = inst_mgr
        self.root_dir = root_dir
        self.instance_dir = instance_dir
        self.version_id = version_id.strip()
        self.loader = loader
        self.account = account
        self.ram_mb = ram_mb
        self.custom_res = custom_res or {}
        self.parent_win = parent_win
        self.signals = WorkerSignals()

    TOKEN_FRESH_SECONDS = 12 * 3600   # Minecraft tokens last ~24h: reuse them instead of 5 web requests per launch
    TOKEN_USABLE_SECONDS = 23 * 3600

    def run(self):
        t_start = time.time()
        timings = []

        def mark(label: str, since: float):
            timings.append(f"{label} {time.time() - since:.1f}s")

        try:
            t_stage = time.time()
            if self.account.get("type") == "ms":
                token_age = time.time() - float(self.account.get("token_time", 0) or 0)
                has_token = bool(self.account.get("access_token")) and self.account.get("access_token") != "0"
                if has_token and token_age < self.TOKEN_FRESH_SECONDS:
                    self.signals.log.emit(f"[AUTH] Microsoft session still valid ({int(token_age // 60)} min old), refresh skipped")
                elif self.account.get("refresh_token"):
                    self.signals.progress.emit("Validating Microsoft session...", 0, 1)
                    try:
                        fresh_account = AuthService.refresh_microsoft_token(self.account["refresh_token"])
                        fresh_account["token_time"] = time.time()
                        self.account.update(fresh_account)
                        if self.parent_win and hasattr(self.parent_win, "config"):
                            accs = self.parent_win.config.get("accounts", {})
                            accs[self.account["id"]] = self.account
                            self.parent_win.config.set("accounts", accs)
                        self.signals.log.emit(f"[AUTH] Successfully refreshed Microsoft session for {self.account['name']}")
                    except Exception as auth_err:
                        self.signals.log.emit(f"[AUTH ERROR] Token refresh failed: {auth_err}")
                        if has_token and token_age < self.TOKEN_USABLE_SECONDS:
                            self.signals.log.emit("[AUTH] Using the saved session instead (it is still valid, e.g. you are offline)")
                        else:
                            raise RuntimeError(f"Microsoft session expired. Please re-add your account in Settings: {auth_err}")
                else:
                    raise RuntimeError("No refresh token stored. Please re-authenticate your Microsoft account in Settings.")
            mark("auth", t_stage)

            target_version = self.version_id

            t_stage = time.time()
            java_bin = JavaManager.ensure_java_runtime(
                target_version,
                self.root_dir,
                status_cb=lambda desc, cur, tot: self.signals.progress.emit(desc, cur, tot)
            )
            mark("java", t_stage)

            t_stage = time.time()
            downloader = VersionDownloader(
                self.root_dir,
                progress_callback=lambda desc, cur, tot: self.signals.progress.emit(desc, cur, tot)
            )
            downloader.install_version(target_version)
            mark("game files", t_stage)

            t_stage = time.time()
            self.signals.progress.emit(f"Preparing {self.loader} profile...", 0, 100)
            launch_version = self.inst_mgr.prepare_instance_loader(
                self.instance_dir, target_version, self.loader,
                status_cb=lambda desc, cur, tot: self.signals.progress.emit(desc, cur, tot)
            )

            if launch_version != target_version:
                downloader.install_version(launch_version)
            mark("loader", t_stage)

            jvm_flags = OptimizationEngine.build_high_tier_jvm_args(self.ram_mb)

            # Timing of the game process itself (launcher-side messages start with "[CLIENT]")
            proc_clock = {"start": None, "first_seen": False}

            def on_game_line(line: str):
                if proc_clock["start"] and not proc_clock["first_seen"] and not line.startswith("[CLIENT]"):
                    proc_clock["first_seen"] = True
                    self.signals.log.emit(f"[LAUNCH] Java printed its first line {time.time() - proc_clock['start']:.1f}s after starting")
                self.signals.log.emit(line)

            launcher = GameLauncher(self.root_dir, log_callback=on_game_line)
            self.signals.progress.emit("Launching Minecraft Engine...", 1, 1)
            self.signals.log.emit(f"[LAUNCH] Preparation took {time.time() - t_start:.1f}s ({', '.join(timings)})")

            DiscordRPCManager.get_instance().set_game_presence(
                version=target_version,
                loader=self.loader,
                instance_name=os.path.basename(self.instance_dir)
            )

            start_timestamp = time.time()
            proc_clock["start"] = start_timestamp

            proc = launcher.launch(
                version_id=launch_version,
                account=self.account,
                jvm_args=jvm_flags,
                instance_dir=self.instance_dir,
                java_bin=java_bin,
                custom_res=self.custom_res
            )

            if self.parent_win and proc:
                self.parent_win.active_process = proc
                self.signals.finished.emit()

            ret = proc.wait()
            elapsed_seconds = int(time.time() - start_timestamp)
            self._record_playtime(elapsed_seconds)

            DiscordRPCManager.get_instance().set_menu_presence()

            if ret != 0:
                self.signals.error.emit(f"Minecraft exited with error code {ret}. Check Console Log.")
            else:
                self.signals.progress.emit("Minecraft closed cleanly.", 0, 0)
        except Exception as e:
            DiscordRPCManager.get_instance().set_menu_presence()
            self.signals.error.emit(str(e))

    def _record_playtime(self, elapsed_sec: int):
        meta_file = os.path.join(self.instance_dir, "instance.json")
        data = {}
        if os.path.exists(meta_file):
            try:
                with open(meta_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass
        current_time = data.get("playtime_seconds", 0)
        data["playtime_seconds"] = current_time + elapsed_sec
        data["last_played"] = int(time.time())
        try:
            with open(meta_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception:
            pass


class DeviceAuthWorker(QRunnable):
    def __init__(self, device_code: str, interval: int, expires_in: int):
        super().__init__()
        self.device_code = device_code
        self.interval = interval
        self.expires_in = expires_in
        self.signals = WorkerSignals()
        self.account_data = None

    def run(self):
        try:
            self.account_data = AuthService.poll_for_login(
                self.device_code,
                self.interval,
                self.expires_in,
                status_cb=lambda msg: self.signals.progress.emit(msg, 0, 0)
            )
            self.signals.finished.emit()
        except Exception as e:
            self.signals.error.emit(str(e))


class NewInstanceDialog(QDialog):
    def __init__(self, all_versions: list, theme_name: str = "Dark Mode", parent=None):
        super().__init__(parent)
        self.current_theme = theme_name
        self.setWindowTitle("Create New Instance")
        self.setFixedSize(480, 440)
        self.all_versions = all_versions if all_versions else ["1.21.1", "1.20.4", "1.20.1", "1.19.4", "1.18.2", "1.16.5", "1.12.2", "1.8.9"]

        if parent and hasattr(parent, "app_icon") and not parent.app_icon.isNull():
            self.setWindowIcon(parent.app_icon)

        t = ThemeManager.get_theme_data(theme_name)
        self.setStyleSheet(f"""
            {ThemeManager.get_style(theme_name)}
            QDialog {{
                background-color: {t['card_bg']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        inst_label = QLabel("INSTANCE NAME:")
        inst_label.setObjectName("SectionLabel")
        layout.addWidget(inst_label)

        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. My Survival World, 1.8 PvP...")
        layout.addWidget(self.name_edit)

        v_label = QLabel("MINECRAFT VERSION (SEARCH OR TYPE ANY VERSION):")
        v_label.setObjectName("SectionLabel")
        layout.addWidget(v_label)

        self.filter_edit = QLineEdit()
        self.filter_edit.setPlaceholderText("Filter versions (e.g. 1.21.1, 1.20, 1.8.9)...")
        self.filter_edit.textChanged.connect(self.apply_version_filter)
        layout.addWidget(self.filter_edit)

        self.version_box = CustomDropdown(enable_delete=False, parent=self)
        self.version_box.addItem("Select a version...", userData=None)
        self.version_box.addItems(self.all_versions)
        layout.addWidget(self.version_box)

        l_label = QLabel("MOD LOADER:")
        l_label.setObjectName("SectionLabel")
        layout.addWidget(l_label)

        self.loader_box = CustomDropdown(enable_delete=False, parent=self)
        self.loader_box.addItem("Select a mod loader...", userData=None)
        self.loader_box.addItems(["Fabric", "Vanilla", "Forge", "NeoForge", "Quilt"])
        layout.addWidget(self.loader_box)

        layout.addStretch()

        btn_box = QHBoxLayout()
        self.cancel_btn = AnimatedButton("Cancel")
        self.cancel_btn.setObjectName("PillButton")
        self.cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(self.cancel_btn)

        self.create_btn = AnimatedButton("Create Instance")
        self.create_btn.setObjectName("PlayButton")
        self.create_btn.setFixedHeight(42)
        self.create_btn.clicked.connect(self.validate_and_submit)
        btn_box.addWidget(self.create_btn)
        layout.addLayout(btn_box)

    def apply_version_filter(self, query: str):
        query = query.strip().lower()
        self.version_box.clear()
        if not query:
            self.version_box.addItem("Select a version...", userData=None)
            self.version_box.addItems(self.all_versions)
        else:
            filtered = [v for v in self.all_versions if query in v.lower()]
            if query not in [v.lower() for v in self.all_versions]:
                filtered.insert(0, self.filter_edit.text().strip())
            self.version_box.addItem("Select a version...", userData=None)
            self.version_box.addItems(filtered)

    def validate_and_submit(self):
        name = self.name_edit.text().strip()
        version = self.version_box.currentData()
        loader = self.loader_box.currentData()

        if not name:
            QMessageBox.warning(self, "Missing Name", "Please add a name for your instance.")
            self.name_edit.setFocus()
            return

        if not version or version == "Select a version...":
            custom_v = self.filter_edit.text().strip()
            if custom_v:
                version = custom_v
            else:
                QMessageBox.warning(self, "Missing Version", "Please select or type a Minecraft version.")
                return

        if not loader or loader == "Select a mod loader...":
            QMessageBox.warning(self, "Missing Loader", "Please select a mod loader.")
            return

        self.chosen_version = version
        self.chosen_loader = loader
        self.chosen_name = name
        self.accept()

    def get_data(self):
        return {
            "name": getattr(self, "chosen_name", self.name_edit.text().strip()),
            "version": getattr(self, "chosen_version", self.version_box.currentText().strip().replace("   ▾", "")),
            "loader": getattr(self, "chosen_loader", self.loader_box.currentText().replace("   ▾", ""))
        }


class MainWindow(QMainWindow):
    def __init__(self, config: ConfigManager):
        super().__init__()
        self.config = config
        self.threadpool = QThreadPool()
        self.icon_pool = QThreadPool()
        self.icon_pool.setMaxThreadCount(2)

        self.active_process = None
        self.all_mojang_versions = []
        self.card_widgets = []
        self.log_history = []
        self.current_console_filter = "ALL"
        self.is_force_quitting = False
        self.has_shown_tray_notice = self.config.get("tray_notified", False)

        self.content_browser_user_overridden = False

        self.search_debounce_timer = QTimer(self)
        self.search_debounce_timer.setSingleShot(True)
        self.search_debounce_timer.setInterval(350)
        self.search_debounce_timer.timeout.connect(self.run_mod_search)

        self.setWindowTitle("LowCore Launcher Beta")
        self.setFixedSize(720, 640)

        self.easter_egg_buffer = ""

        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.logo_path = os.path.join(self.base_dir, "assets", "logo.png")
        self.app_icon = QIcon()
        self.trimmed_logo_pix = QPixmap()
        if os.path.exists(self.logo_path):
            raw_pix = QPixmap(self.logo_path)
            self.trimmed_logo_pix = crop_transparent_padding(raw_pix)
            for s in [16, 20, 24, 32, 40, 48, 64, 128, 256]:
                self.app_icon.addPixmap(
                    self.trimmed_logo_pix.scaled(s, s, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                )
            self.setWindowIcon(self.app_icon)

        self.inst_mgr = InstanceManager(self.config.get("game_dir"))
        self.purge_residual_default_instances()

        self.current_theme = self.config.get("theme_name", "Dark Mode")
        if not ThemeManager.is_valid(self.current_theme):
            self.current_theme = ThemeManager.DEFAULT_THEME

        saved_lang = self.config.get("language", "en")
        I18n.set_language(saved_lang)

        self.progress_anim = None

        self.init_ui()
        self.setup_tray_icon()
        self.apply_current_theme()
        self.fetch_all_versions()
        self.refresh_instances()
        self.refresh_accounts()
        self.retranslate_ui()

        DiscordRPCManager.get_instance()

        QTimer.singleShot(40, self.start_startup_sequence)

    def setup_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        if not self.trimmed_logo_pix.isNull():
            tray_qicon = QIcon()
            for sz in [16, 20, 24, 32, 48, 64]:
                tray_qicon.addPixmap(
                    self.trimmed_logo_pix.scaled(
                        sz, sz,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )
            self.tray_icon.setIcon(tray_qicon)
        elif not self.app_icon.isNull():
            self.tray_icon.setIcon(self.app_icon)
        else:
            self.tray_icon.setIcon(self.windowIcon())

        self.tray_icon.setToolTip("LowCore Launcher Beta")

        tray_menu = QMenu()
        theme_dict = ThemeManager.get_theme_data(self.current_theme)
        tray_menu.setStyleSheet(f"""
            QMenu {{
                background-color: {theme_dict['card_bg']};
                border: 1px solid {theme_dict['border']};
                border-radius: 8px;
                padding: 6px;
                color: {theme_dict['text']};
                font-size: 13px;
                font-weight: 600;
            }}
            QMenu::item {{
                padding: 8px 16px;
                border-radius: 6px;
            }}
            QMenu::item:selected {{
                background-color: {theme_dict['accent']};
                color: {theme_dict['accent_text']};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {theme_dict['border']};
                margin: 4px 6px;
            }}
        """)

        action_show = QAction("Open LowCore Launcher", self)
        action_show.triggered.connect(self.show_from_tray)
        tray_menu.addAction(action_show)

        tray_menu.addSeparator()

        action_exit = QAction("Exit Completely", self)
        action_exit.triggered.connect(self.quit_application)
        tray_menu.addAction(action_exit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()

    def on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_from_tray()

    def show_from_tray(self):
        self.show()
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized | Qt.WindowState.WindowActive)
        self.activateWindow()
        self.raise_()

    def closeEvent(self, event):
        if self.is_force_quitting:
            self.tray_icon.hide()
            event.accept()
        else:
            event.ignore()
            self.hide()
            if not self.has_shown_tray_notice:
                self.tray_icon.showMessage(
                    "LowCore Launcher",
                    "LowCore is running in the background for instant launch.",
                    QSystemTrayIcon.MessageIcon.Information,
                    2000
                )
                self.has_shown_tray_notice = True
                self.config.set("tray_notified", True)

    def quit_application(self):
        self.is_force_quitting = True
        if self.active_process:
            self.kill_active_instance()
        QApplication.quit()

    def keyPressEvent(self, event: QKeyEvent):
        key_char = event.text().lower()
        if key_char in ("g", "r", "u"):
            self.register_easter_egg_char(key_char)
        super().keyPressEvent(event)

    def register_easter_egg_char(self, char: str):
        if self.stack.currentIndex() != 0:
            self.easter_egg_buffer = ""
            return

        self.easter_egg_buffer += char
        target = "grug"
        if target.startswith(self.easter_egg_buffer):
            if self.easter_egg_buffer == target:
                self.easter_egg_buffer = ""
                self.trigger_grug_easter_egg()
        else:
            self.easter_egg_buffer = "g" if char == "g" else ""

    def trigger_grug_easter_egg(self):
        egg_box = QMessageBox(self)
        egg_box.setWindowTitle("CRITICAL SYSTEM ALERT")
        egg_box.setText("grug has hacked ur pc now he is installing 999gb of [REDACTED] stuff")
        egg_box.setIcon(QMessageBox.Icon.Critical)
        egg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        egg_box.setStyleSheet(ThemeManager.get_style(self.current_theme))
        egg_box.exec()

    def purge_residual_default_instances(self):
        legacy_dir = os.path.join(self.inst_mgr.instances_dir, "Default-1211")
        if os.path.exists(legacy_dir):
            try:
                shutil.rmtree(legacy_dir)
            except Exception:
                pass

    def apply_current_theme(self):
        style = ThemeManager.get_style(self.current_theme)
        self.setStyleSheet(style)
        theme_dict = ThemeManager.get_theme_data(self.current_theme)

        if hasattr(self, "nav_bar"):
            self.nav_bar.set_theme_colors(
                active_color=theme_dict["text"],
                inactive_color=theme_dict["text_sub"],
                accent_color=theme_dict["accent"]
            )

        if hasattr(self, "lbl_proxy_notice"):
            self.lbl_proxy_notice.setStyleSheet(f"font-size: 11px; font-weight: 600; color: {theme_dict['text_sub']}; border: none; background: transparent;")

        checkbox_style = f"""
            QCheckBox {{
                color: {theme_dict['text']};
                font-size: 13px;
                font-weight: 600;
                spacing: 8px;
                background: transparent;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 1px solid {theme_dict['border']};
                border-radius: 4px;
                background-color: {theme_dict['pill_bg']};
            }}
            QCheckBox::indicator:hover {{
                border-color: {theme_dict['accent']};
                background-color: {theme_dict['pill_hover']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {theme_dict['accent']};
                border-color: {theme_dict['accent']};
            }}
        """

        if hasattr(self, "chk_auto_log_window"):
            self.chk_auto_log_window.setStyleSheet(checkbox_style)

        if hasattr(self, "chk_fullscreen"):
            self.chk_fullscreen.setStyleSheet(checkbox_style)

        if hasattr(self, "chk_autoscroll"):
            self.chk_autoscroll.setStyleSheet(f"""
                QCheckBox {{
                    color: {theme_dict['text_sub']};
                    font-size: 11px;
                    font-weight: 600;
                    background: transparent;
                }}
                QCheckBox::indicator {{
                    width: 14px;
                    height: 14px;
                    border: 1px solid {theme_dict['border']};
                    border-radius: 3px;
                    background: {theme_dict['pill_bg']};
                }}
                QCheckBox::indicator:checked {{
                    background: {theme_dict['accent']};
                }}
            """)

    def init_ui(self):
        central = QWidget(self)
        central.setObjectName("CentralWidget")
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(28, 20, 28, 20)
        main_layout.setSpacing(12)

        header = QHBoxLayout()
        header.setSpacing(14)

        if os.path.exists(self.logo_path):
            self.header_logo = QLabel()
            self.header_logo.setFixedSize(62, 62)
            self.header_logo.setPixmap(
                QPixmap(self.logo_path).scaled(
                    62, 62, 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation
                )
            )
            self.header_logo.setStyleSheet("background: transparent; border: none; padding: 0px;")
            header.addWidget(self.header_logo, alignment=Qt.AlignmentFlag.AlignVCenter)

        brand_box = QVBoxLayout()
        brand_box.setSpacing(2)
        brand_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(0)

        title_text = "LOWCORE LAUNCHER"
        for ch in title_text:
            if ch == " ":
                sp = QLabel(" ")
                sp.setObjectName("BrandTitle")
                sp.setStyleSheet("border: none; background: transparent;")
                title_row.addWidget(sp)
            else:
                lbl = ClickableLetterLabel(ch)
                lbl.setObjectName("BrandTitle")
                lbl.setStyleSheet("border: none; background: transparent;")
                lbl.clicked.connect(self.register_easter_egg_char)
                title_row.addWidget(lbl)

        title_row.addSpacing(8)

        beta_badge = QLabel("BETA")
        beta_badge.setStyleSheet("""
            background-color: #E85A52;
            color: #FFFFFF;
            font-size: 9px;
            font-weight: 900;
            padding: 2px 6px;
            border-radius: 4px;
            border: none;
            letter-spacing: 1px;
        """)
        title_row.addWidget(beta_badge, alignment=Qt.AlignmentFlag.AlignVCenter)
        title_row.addStretch()

        brand_box.addLayout(title_row)

        slogan_row = QHBoxLayout()
        slogan_row.setContentsMargins(0, 0, 0, 0)
        slogan_row.setSpacing(0)

        slogan_text = "EVERYTHING IN ONE"
        for ch in slogan_text:
            if ch == " ":
                sp = QLabel(" ")
                sp.setObjectName("BrandSlogan")
                sp.setStyleSheet("border: none; background: transparent;")
                slogan_row.addWidget(sp)
            else:
                lbl = ClickableLetterLabel(ch)
                lbl.setObjectName("BrandSlogan")
                lbl.setStyleSheet("border: none; background: transparent;")
                lbl.clicked.connect(self.register_easter_egg_char)
                slogan_row.addWidget(lbl)

        slogan_row.addStretch()
        brand_box.addLayout(slogan_row)

        header.addLayout(brand_box)
        header.addStretch()

        self.kill_btn = AnimatedButton("Kill Minecraft")
        self.kill_btn.setObjectName("PillButton")
        self.kill_btn.setStyleSheet("color: #FF5555; border: 1px solid rgba(255, 85, 85, 0.4);")
        self.kill_btn.clicked.connect(self.kill_active_instance)
        header.addWidget(self.kill_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        main_layout.addLayout(header)

        self.nav_bar = AnimatedNavBar(["Play", "Content Browser", "Settings", "Console Log"])
        self.nav_bar.tab_changed.connect(self.on_tab_switch)
        main_layout.addWidget(self.nav_bar)

        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # ================= VIEW 1: PLAY =================
        dash = QWidget()
        dash_layout = QVBoxLayout(dash)
        dash_layout.setSpacing(10)
        dash_layout.setContentsMargins(0, 8, 0, 0)

        self.play_card = QFrame()
        self.play_card.setObjectName("Card")
        card_layout = QVBoxLayout(self.play_card)
        card_layout.setContentsMargins(20, 18, 20, 18)
        card_layout.setSpacing(14)

        self.inst_label = QLabel("Active Isolated Instance")
        self.inst_label.setObjectName("SectionLabel")
        card_layout.addWidget(self.inst_label)

        inst_bar = QHBoxLayout()
        inst_bar.setSpacing(8)

        self.instance_box = CustomDropdown(enable_delete=True, parent=self)
        self.instance_box.currentIndexChanged.connect(self.on_instance_changed)
        self.instance_box.deleteRequested.connect(self.delete_instance_by_index)
        inst_bar.addWidget(self.instance_box, stretch=4)

        self.btn_open_folder = AnimatedButton("⋮")
        self.btn_open_folder.setToolTip("Instance Options & Folders")
        self.btn_open_folder.setObjectName("PillButton")
        self.btn_open_folder.setFixedWidth(46)
        self.btn_open_folder.setFixedHeight(40)
        self.btn_open_folder.setStyleSheet("font-size: 22px; font-weight: 900; padding: 0px;")
        self.btn_open_folder.clicked.connect(self.show_instance_options_menu)
        inst_bar.addWidget(self.btn_open_folder)

        self.btn_new_inst = AnimatedButton("+ New Instance")
        self.btn_new_inst.setObjectName("PillButton")
        self.btn_new_inst.setFixedHeight(40)
        self.btn_new_inst.clicked.connect(self.prompt_new_instance)
        inst_bar.addWidget(self.btn_new_inst, stretch=1)
        card_layout.addLayout(inst_bar)

        self.acc_title = QLabel("Account")
        self.acc_title.setObjectName("SectionLabel")
        card_layout.addWidget(self.acc_title)

        acc_bar = QHBoxLayout()
        acc_bar.setSpacing(8)

        self.account_box = CustomDropdown(enable_delete=True, parent=self)
        self.account_box.currentIndexChanged.connect(self.on_account_changed)
        self.account_box.deleteRequested.connect(self.delete_account_by_index)
        acc_bar.addWidget(self.account_box, stretch=3)

        self.btn_offline = AnimatedButton("+ Offline")
        self.btn_offline.setObjectName("PillButton")
        self.btn_offline.clicked.connect(self.add_offline_account)
        acc_bar.addWidget(self.btn_offline, stretch=1)

        self.btn_ms = AnimatedButton("+ Microsoft")
        self.btn_ms.setObjectName("PillButton")
        self.btn_ms.clicked.connect(self.add_microsoft_account)
        acc_bar.addWidget(self.btn_ms, stretch=1)
        card_layout.addLayout(acc_bar)

        self.ram_title = QLabel("Global High-Performance Memory Allocation")
        self.ram_title.setObjectName("SectionLabel")
        card_layout.addWidget(self.ram_title)

        self.ram_dropdown = CustomDropdown(enable_delete=False, parent=self)
        self.ram_options = [
            ("2048 MB (2 GB)", 2048),
            ("3072 MB (3 GB)", 3072),
            ("4096 MB (4 GB - Recommended)", 4096),
            ("6144 MB (6 GB)", 6144),
            ("8192 MB (8 GB - High End)", 8192),
            ("12288 MB (12 GB)", 12288),
            ("16384 MB (16 GB)", 16384),
        ]
        current_ram = self.config.get("allocated_ram_mb", 4096)
        sel_idx = 2
        for idx, (lbl, val) in enumerate(self.ram_options):
            self.ram_dropdown.addItem(lbl, userData=val)
            if val == current_ram:
                sel_idx = idx
        self.ram_dropdown.setCurrentIndex(sel_idx)
        self.ram_dropdown.currentIndexChanged.connect(self.on_ram_changed)
        card_layout.addWidget(self.ram_dropdown)

        dash_layout.addWidget(self.play_card)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(0)
        self.progress_bar.setTextVisible(False)
        dash_layout.addWidget(self.progress_bar)

        self.status_lbl = QLabel("Ready to launch")
        self.status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_lbl.setObjectName("StatusLabel")  # colour comes from the theme
        self.status_lbl.setStyleSheet("""
            font-size: 12px;
            font-weight: 700;
            letter-spacing: 0.8px;
            padding: 4px;
        """)
        self.status_lbl.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        dash_layout.addWidget(self.status_lbl)

        self.launch_btn = AnimatedButton("PLAY")
        self.launch_btn.setObjectName("PlayButton")
        self.launch_btn.setFixedHeight(50)
        self.launch_btn.clicked.connect(self.handle_launch)
        dash_layout.addWidget(self.launch_btn)

        def make_stat_tile(caption: str):
            tile = QFrame()
            tile.setObjectName("StatTile")
            tile.setFixedHeight(58)
            tile_layout = QVBoxLayout(tile)
            tile_layout.setContentsMargins(14, 8, 14, 8)
            tile_layout.setSpacing(2)
            cap_lbl = QLabel(caption)
            cap_lbl.setObjectName("SectionLabel")
            val_lbl = QLabel("—")
            val_lbl.setObjectName("StatValue")
            tile_layout.addWidget(cap_lbl)
            tile_layout.addWidget(val_lbl)
            return tile, val_lbl

        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)
        playtime_tile, self.stat_playtime_val = make_stat_tile("PLAYTIME")
        mods_tile, self.stat_mods_val = make_stat_tile("MODS")
        last_tile, self.stat_last_val = make_stat_tile("LAST PLAYED")
        for tile in (playtime_tile, mods_tile, last_tile):
            stats_row.addWidget(tile, 1)
        dash_layout.addLayout(stats_row)

        dash_layout.addStretch(1)
        self.stack.addWidget(dash)

        # ================= VIEW 2: CONTENT BROWSER =================
        mod_tab = QWidget()
        m_layout = QVBoxLayout(mod_tab)
        m_layout.setSpacing(10)

        m_card = QFrame()
        m_card.setObjectName("Card")
        m_card_layout = QVBoxLayout(m_card)
        m_card_layout.setSpacing(12)

        target_row = QHBoxLayout()
        target_row.setSpacing(10)

        t_lbl = QLabel("TARGET INSTANCE:")
        t_lbl.setObjectName("SectionLabel")
        target_row.addWidget(t_lbl)

        self.browser_target_inst = CustomDropdown(enable_delete=False, parent=self)
        self.browser_target_inst.setFixedWidth(240)
        self.browser_target_inst.currentIndexChanged.connect(self.on_browser_instance_changed)
        target_row.addWidget(self.browser_target_inst)

        target_row.addStretch()

        theme_dict = ThemeManager.get_theme_data(self.current_theme)
        self.content_type_bar = ContentTypeBar(theme_dict, self)
        self.content_type_bar.type_changed.connect(lambda _: self.run_mod_search())
        target_row.addWidget(self.content_type_bar)

        m_card_layout.addLayout(target_row)

        search_bar = QHBoxLayout()
        self.mod_search_input = QLineEdit()
        self.mod_search_input.setPlaceholderText("Search Mods, Resource Packs & Shaders on Modrinth...")
        self.mod_search_input.returnPressed.connect(self.run_mod_search)
        self.mod_search_input.textChanged.connect(self.on_search_text_changed)
        search_bar.addWidget(self.mod_search_input)

        self.btn_search = AnimatedButton("Search")
        self.btn_search.setObjectName("PillButton")
        self.btn_search.clicked.connect(self.run_mod_search)
        search_bar.addWidget(self.btn_search)
        m_card_layout.addLayout(search_bar)

        self.mod_results_list = QListWidget()
        self.mod_results_list.setObjectName("ModsList")
        self.mod_results_list.currentRowChanged.connect(self.on_mod_selection_changed)
        m_card_layout.addWidget(self.mod_results_list)

        self.btn_install_mod = AnimatedButton("Download to Selected Instance")
        self.btn_install_mod.setObjectName("PlayButton")
        self.btn_install_mod.setFixedHeight(42)
        self.btn_install_mod.clicked.connect(self.install_selected_mod)
        m_card_layout.addWidget(self.btn_install_mod)

        m_layout.addWidget(m_card)
        self.stack.addWidget(mod_tab)

        # ================= VIEW 3: SETTINGS =================
        settings_widget = QWidget()
        s_layout = QVBoxLayout(settings_widget)
        s_layout.setContentsMargins(0, 8, 0, 0)

        s_card = QFrame()
        s_card.setObjectName("Card")
        s_card_layout = QHBoxLayout(s_card)
        s_card_layout.setContentsMargins(16, 16, 16, 16)
        s_card_layout.setSpacing(16)

        self.settings_sidebar = QListWidget()
        self.settings_sidebar.setObjectName("SettingsSidebar")
        self.settings_sidebar.setFixedWidth(140)
        self.settings_sidebar.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.settings_subpages = QStackedWidget()
        self.settings_subpages.addWidget(self._build_general_settings_page())
        self.settings_subpages.addWidget(self._build_instance_settings_page())
        self.settings_subpages.addWidget(self._build_accounts_settings_page())
        self.settings_subpages.addWidget(self._build_language_settings_page())
        self.settings_subpages.addWidget(self._build_proxy_settings_page())

        for tab_name in ["General", "Instances", "Accounts", "Language", "Proxy"]:
            item = QListWidgetItem(tab_name)
            item.setSizeHint(QSize(120, 38))
            self.settings_sidebar.addItem(item)

        self.settings_sidebar.currentRowChanged.connect(self.settings_subpages.setCurrentIndex)
        self.settings_sidebar.setCurrentRow(0)

        s_card_layout.addWidget(self.settings_sidebar)
        s_card_layout.addWidget(self.settings_subpages, stretch=1)
        s_layout.addWidget(s_card)
        self.stack.addWidget(settings_widget)

        # ================= VIEW 4: CONSOLE LOG =================
        console_widget = QWidget()
        c_layout = QVBoxLayout(console_widget)
        c_layout.setContentsMargins(0, 8, 0, 0)
        c_layout.setSpacing(8)

        ctrl_bar = QHBoxLayout()
        ctrl_bar.setSpacing(8)

        self.console_search = QLineEdit()
        self.console_search.setPlaceholderText("Filter current logs in realtime...")
        self.console_search.textChanged.connect(self.refresh_main_console_display)
        ctrl_bar.addWidget(self.console_search, stretch=3)

        self.btn_c_all = AnimatedButton("All")
        self.btn_c_all.setObjectName("PillButton")
        self.btn_c_all.setMinimumWidth(60)
        self.btn_c_all.setStyleSheet("padding: 4px 12px;")
        self.btn_c_all.clicked.connect(lambda: self.set_main_console_filter("ALL"))
        ctrl_bar.addWidget(self.btn_c_all)

        self.btn_c_err = AnimatedButton("Errors")
        self.btn_c_err.setObjectName("PillButton")
        self.btn_c_err.setMinimumWidth(75)
        self.btn_c_err.setStyleSheet("color: #FF5555; border: 1px solid rgba(255, 85, 85, 0.4); padding: 4px 12px;")
        self.btn_c_err.clicked.connect(lambda: self.set_main_console_filter("ERRORS"))
        ctrl_bar.addWidget(self.btn_c_err)

        self.btn_c_warn = AnimatedButton("Warns")
        self.btn_c_warn.setObjectName("PillButton")
        self.btn_c_warn.setMinimumWidth(75)
        self.btn_c_warn.setStyleSheet("color: #FFB86C; border: 1px solid rgba(255, 184, 108, 0.4); padding: 4px 12px;")
        self.btn_c_warn.clicked.connect(lambda: self.set_main_console_filter("WARNS"))
        ctrl_bar.addWidget(self.btn_c_warn)

        self.btn_c_copy = AnimatedButton("Copy")
        self.btn_c_copy.setObjectName("PillButton")
        self.btn_c_copy.setMinimumWidth(82)
        self.btn_c_copy.setStyleSheet("padding: 4px 14px;")
        self.btn_c_copy.clicked.connect(self.copy_main_console)
        ctrl_bar.addWidget(self.btn_c_copy)

        self.btn_c_clear = AnimatedButton("Clear")
        self.btn_c_clear.setObjectName("PillButton")
        self.btn_c_clear.setMinimumWidth(82)
        self.btn_c_clear.setStyleSheet("padding: 4px 14px;")
        self.btn_c_clear.clicked.connect(self.clear_main_console)
        ctrl_bar.addWidget(self.btn_c_clear)

        self.chk_autoscroll = QCheckBox("Auto-scroll")
        self.chk_autoscroll.setChecked(True)
        self.chk_autoscroll.setCursor(Qt.CursorShape.PointingHandCursor)
        ctrl_bar.addWidget(self.chk_autoscroll)

        c_layout.addLayout(ctrl_bar)

        self.console = QPlainTextEdit()
        self.console.setObjectName("ConsoleLog")
        self.console.setReadOnly(True)
        c_layout.addWidget(self.console)
        self.stack.addWidget(console_widget)

        # ================= STARTUP OVERLAY =================
        self.splash_overlay = QWidget(self)
        self.splash_overlay.setGeometry(0, 0, 720, 640)
        self.splash_overlay.setObjectName("SplashOverlay")

        self.splash_overlay.setStyleSheet(f"""
            QWidget#SplashOverlay {{
                background-color: {theme_dict['bg']};
            }}
        """)

        splash_layout = QVBoxLayout(self.splash_overlay)
        splash_layout.setContentsMargins(0, 0, 0, 0)
        splash_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        splash_center = QWidget()
        splash_center_layout = QVBoxLayout(splash_center)
        splash_center_layout.setSpacing(14)
        splash_center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.splash_logo_anim = None
        if os.path.exists(self.logo_path):
            logo_pix = QPixmap(self.logo_path)
            self.splash_logo = ScalingLogoLabel(logo_pix)
            self.splash_logo.target_size = 50
            splash_center_layout.addWidget(self.splash_logo, alignment=Qt.AlignmentFlag.AlignCenter)

        self.splash_title = QLabel("LOWCORE LAUNCHER")
        self.splash_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.splash_title.setStyleSheet(f"""
            font-size: 26px;
            font-weight: 900;
            color: {theme_dict['text']};
            letter-spacing: 3px;
            background: transparent;
        """)
        splash_center_layout.addWidget(self.splash_title)

        self.splash_status = QLabel("Loading client resources...")
        self.splash_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.splash_status.setStyleSheet(f"""
            font-size: 12px;
            font-weight: 600;
            color: {theme_dict['text_sub']};
            letter-spacing: 0.5px;
            background: transparent;
        """)
        splash_center_layout.addWidget(self.splash_status)

        self.splash_bar = QProgressBar()
        self.splash_bar.setFixedSize(240, 5)
        self.splash_bar.setTextVisible(False)
        self.splash_bar.setRange(0, 3000)
        self.splash_bar.setValue(0)
        self.splash_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {theme_dict['pill_bg']};
                border: none;
                border-radius: 2.5px;
            }}
            QProgressBar::chunk {{
                background-color: {theme_dict['accent']};
                border-radius: 2.5px;
            }}
        """)
        splash_center_layout.addWidget(self.splash_bar, alignment=Qt.AlignmentFlag.AlignCenter)

        splash_layout.addWidget(splash_center)
        self.splash_overlay.raise_()

    def show_instance_options_menu(self):
        inst_data = self.instance_box.currentData()
        if not inst_data or not inst_data.get("path"):
            return

        base_path = inst_data["path"]
        menu = QMenu(self)
        
        t = ThemeManager.get_theme_data(self.current_theme)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {t['card_bg']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                padding: 6px;
                color: {t['text']};
                font-size: 13px;
                font-weight: 600;
            }}
            QMenu::item {{
                padding: 7px 22px 7px 12px;
                border-radius: 6px;
                background-color: transparent;
                color: {t['text']};
            }}
            QMenu::item:selected {{
                background-color: {t['pill_hover']};
                color: {t['accent']};
            }}
            QMenu::separator {{
                height: 1px;
                background-color: {t['border']};
                margin: 4px 6px;
            }}
        """)

        total_sec = inst_data.get("playtime_seconds", 0)
        action_time = QAction(f"⏱ Total Playtime: {format_playtime(total_sec)}", self)
        action_time.setEnabled(False)
        menu.addAction(action_time)

        menu.addSeparator()

        action_clone = QAction("📋 Clone Instance (Create Copy)", self)
        action_clone.triggered.connect(lambda: self.clone_instance(inst_data))
        menu.addAction(action_clone)

        action_manage_mods = QAction("🧩 Manage Installed Mods", self)
        action_manage_mods.triggered.connect(lambda: self.open_mods_manager(os.path.join(base_path, "mods")))
        menu.addAction(action_manage_mods)

        menu.addSeparator()

        action_root = QAction("📁 Open Instance Root", self)
        action_root.triggered.connect(lambda: self._open_dir(base_path))
        menu.addAction(action_root)

        action_mods = QAction("📂 Open Mods Folder", self)
        action_mods.triggered.connect(lambda: self._open_dir(os.path.join(base_path, "mods")))
        menu.addAction(action_mods)

        action_rp = QAction("🎨 Open Resource Packs", self)
        action_rp.triggered.connect(lambda: self._open_dir(os.path.join(base_path, "resourcepacks")))
        menu.addAction(action_rp)

        action_shaders = QAction("✨ Open Shader Packs", self)
        action_shaders.triggered.connect(lambda: self._open_dir(os.path.join(base_path, "shaderpacks")))
        menu.addAction(action_shaders)

        action_saves = QAction("🌍 Open Saves / Worlds", self)
        action_saves.triggered.connect(lambda: self._open_dir(os.path.join(base_path, "saves")))
        menu.addAction(action_saves)

        action_screenshots = QAction("📸 Open Screenshots", self)
        action_screenshots.triggered.connect(lambda: self._open_dir(os.path.join(base_path, "screenshots")))
        menu.addAction(action_screenshots)

        action_cfg = QAction("⚙ Open Configs", self)
        action_cfg.triggered.connect(lambda: self._open_dir(os.path.join(base_path, "config")))
        menu.addAction(action_cfg)

        pos = self.btn_open_folder.mapToGlobal(QPoint(0, self.btn_open_folder.height() + 4))
        menu.exec(pos)

    def open_mods_manager(self, mods_dir: str):
        os.makedirs(mods_dir, exist_ok=True)
        dlg = ModManagerDialog(mods_dir, self.current_theme, self)
        dlg.exec()

    def clone_instance(self, source_inst: dict):
        new_name, ok = QInputDialog.getText(
            self, "Clone Instance", f"Clone '{source_inst['name']}' as:", text=f"{source_inst['name']} (Copy)"
        )
        if not ok or not new_name.strip():
            return

        new_name = new_name.strip()
        safe_folder = "".join(c for c in new_name if c.isalnum() or c in ("-", "_")).rstrip()
        target_path = os.path.join(self.inst_mgr.instances_dir, safe_folder)

        if os.path.exists(target_path):
            self.show_alert("Folder Exists", "An instance with a similar folder name already exists.", is_error=True)
            return

        try:
            shutil.copytree(source_inst["path"], target_path)
            meta_path = os.path.join(target_path, "instance.json")
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                meta["name"] = new_name
                meta["created_at"] = time.time()
                meta["playtime_seconds"] = 0
                with open(meta_path, "w", encoding="utf-8") as f:
                    json.dump(meta, f, indent=4)

            self.refresh_instances()
            self.show_alert("Cloned", f"Instance cloned successfully as '{new_name}'.")
        except Exception as e:
            self.show_alert("Clone Failed", f"Could not duplicate instance:\n{e}", is_error=True)

    def _open_dir(self, path: str):
        os.makedirs(path, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])

    def set_main_console_filter(self, mode: str):
        self.current_console_filter = mode
        self.refresh_main_console_display()

    def refresh_main_console_display(self):
        query = self.console_search.text().strip().lower()
        self.console.clear()
        chunks = []

        for line in self.log_history:
            if query and query not in line.lower():
                continue
            upper = line.upper()
            if self.current_console_filter == "ERRORS":
                if not any(k in upper for k in ["[ERROR]", "ERROR", "FATAL", "EXCEPTION", "CRASH", "FAILED", "OS::COMMIT_MEMORY"]):
                    continue
            elif self.current_console_filter == "WARNS":
                if not any(k in upper for k in ["[WARN]", "[WARNING]", "WARN"]):
                    continue

            chunks.append(format_log_line_html(line, self.current_theme))

        self.console.appendHtml("".join(chunks))
        if self.chk_autoscroll.isChecked():
            self.console.moveCursor(QTextCursor.MoveOperation.End)

    def append_log_line(self, line: str):
        self.log_history.append(line)
        query = self.console_search.text().strip().lower()

        if query and query not in line.lower():
            return

        upper = line.upper()
        if self.current_console_filter == "ERRORS":
            if not any(k in upper for k in ["[ERROR]", "ERROR", "FATAL", "EXCEPTION", "CRASH", "FAILED", "OS::COMMIT_MEMORY"]):
                return
        elif self.current_console_filter == "WARNS":
            if not any(k in upper for k in ["[WARN]", "[WARNING]", "WARN"]):
                return

        self.console.appendHtml(format_log_line_html(line, self.current_theme))
        if self.chk_autoscroll.isChecked():
            self.console.moveCursor(QTextCursor.MoveOperation.End)

    def clear_main_console(self):
        self.log_history.clear()
        self.console.clear()

    def copy_main_console(self):
        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(self.log_history))
        self.btn_c_copy.setText("Copied!")
        QTimer.singleShot(1500, lambda: self.btn_c_copy.setText("Copy"))

    def _build_general_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 2, 4, 4)
        layout.setSpacing(10)

        self.lbl_client_theme = QLabel(I18n.t("client_theme"))
        self.lbl_client_theme.setObjectName("SectionLabel")
        layout.addWidget(self.lbl_client_theme)

        self.theme_dropdown = CustomDropdown(enable_delete=False, parent=self)
        self.theme_dropdown.addItems(ThemeManager.get_theme_names())
        self.theme_dropdown.setCurrentText(self.current_theme)
        self.theme_dropdown.currentIndexChanged.connect(
            lambda: self.on_theme_changed(self.theme_dropdown.currentText().replace("   ▾", ""))
        )
        layout.addWidget(self.theme_dropdown)

        lbl_res = QLabel("MINECRAFT WINDOW RESOLUTION")
        lbl_res.setObjectName("SectionLabel")
        layout.addWidget(lbl_res)

        res_box = QHBoxLayout()
        res_box.setSpacing(10)

        lbl_w = QLabel("Width:")
        lbl_w.setObjectName("SettingsItemLabel")
        lbl_w.setFixedWidth(50)
        self.spin_res_w = QSpinBox()
        self.spin_res_w.setRange(640, 7680)
        self.spin_res_w.setValue(self.config.get("res_width", 1280))
        self.spin_res_w.valueChanged.connect(lambda val: self.config.set("res_width", val))

        lbl_h = QLabel("Height:")
        lbl_h.setObjectName("SettingsItemLabel")
        lbl_h.setFixedWidth(50)
        self.spin_res_h = QSpinBox()
        self.spin_res_h.setRange(480, 4320)
        self.spin_res_h.setValue(self.config.get("res_height", 720))
        self.spin_res_h.valueChanged.connect(lambda val: self.config.set("res_height", val))

        self.chk_fullscreen = QCheckBox("Start Fullscreen")
        self.chk_fullscreen.setChecked(self.config.get("fullscreen", False))
        self.chk_fullscreen.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_fullscreen.toggled.connect(lambda val: self.config.set("fullscreen", val))

        res_box.addWidget(lbl_w)
        res_box.addWidget(self.spin_res_w)
        res_box.addWidget(lbl_h)
        res_box.addWidget(self.spin_res_h)
        res_box.addWidget(self.chk_fullscreen)
        layout.addLayout(res_box)

        self.lbl_log_section = QLabel("CRASH & CONSOLE LOGGING")
        self.lbl_log_section.setObjectName("SectionLabel")
        layout.addWidget(self.lbl_log_section)

        self.chk_auto_log_window = QCheckBox("Open separate Log Viewer window when game closes or crashes")
        self.chk_auto_log_window.setObjectName("SettingsCheckBox")
        self.chk_auto_log_window.setCursor(Qt.CursorShape.PointingHandCursor)
        self.chk_auto_log_window.setChecked(self.config.get("show_log_on_exit", True))
        self.chk_auto_log_window.toggled.connect(lambda val: self.config.set("show_log_on_exit", val))
        layout.addWidget(self.chk_auto_log_window)

        self.btn_open_log_window = AnimatedButton("View Current Log in Separate Window")
        self.btn_open_log_window.setObjectName("PillButton")
        self.btn_open_log_window.clicked.connect(self.open_standalone_log_dialog)
        layout.addWidget(self.btn_open_log_window)

        self.lbl_folders = QLabel(I18n.t("folders"))
        self.lbl_folders.setObjectName("SectionLabel")
        layout.addWidget(self.lbl_folders)

        folders = [
            ("Instances:", os.path.join(self.config.get("game_dir"), "instances")),
            ("Shared Libs:", self.config.get("game_dir")),
            ("Auto Java:", os.path.join(self.config.get("game_dir"), "java")),
            ("Downloads:", os.path.expanduser("~/Downloads"))
        ]

        self.folder_browse_buttons = []
        for lbl_name, default_dir in folders:
            row = QHBoxLayout()
            row.setSpacing(10)

            lbl = QLabel(lbl_name)
            lbl.setObjectName("SettingsItemLabel")
            lbl.setFixedWidth(110)

            inp = QLineEdit(default_dir)

            btn = AnimatedButton(I18n.t("browse"))
            btn.setObjectName("PillButton")
            btn.setFixedWidth(84)
            btn.clicked.connect(lambda _, target=inp: self._browse_folder(target))
            self.folder_browse_buttons.append(btn)

            row.addWidget(lbl)
            row.addWidget(inp)
            row.addWidget(btn)
            layout.addLayout(row)

        layout.addStretch()
        return page

    def open_standalone_log_dialog(self):
        dlg = LogViewerDialog(self.log_history, self.current_theme, app_icon=self.app_icon, parent=self)
        dlg.exec()

    def _browse_folder(self, target_input):
        chosen = QFileDialog.getExistingDirectory(self, "Select Directory", target_input.text())
        if chosen:
            target_input.setText(chosen)

    def _build_instance_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 2, 4, 4)
        layout.setSpacing(10)

        lbl = QLabel("INSTANCE MANAGER")
        lbl.setObjectName("SectionLabel")
        layout.addWidget(lbl)

        box = QHBoxLayout()
        box.setSpacing(12)

        self.settings_inst_table = QTableWidget(0, 4)
        self.settings_inst_table.setObjectName("SettingsTable")
        self.settings_inst_table.setHorizontalHeaderLabels(["Instance Name", "Version", "Loader", "Time Played"])
        self.settings_inst_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.settings_inst_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.settings_inst_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.settings_inst_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.settings_inst_table.verticalHeader().setVisible(False)
        self.settings_inst_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.settings_inst_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        box.addWidget(self.settings_inst_table)

        btn_vbox = QVBoxLayout()
        btn_vbox.setSpacing(8)

        btn_add = AnimatedButton("+ New Instance")
        btn_add.setObjectName("PillButton")
        btn_add.clicked.connect(self.prompt_new_instance)

        btn_open = AnimatedButton("Open Folder")
        btn_open.setObjectName("PillButton")
        btn_open.clicked.connect(self.open_selected_settings_instance_folder)

        btn_del = AnimatedButton("Delete Selected")
        btn_del.setObjectName("PillButton")
        btn_del.setStyleSheet("color: #FF5555; border: 1px solid rgba(255, 85, 85, 0.4);")
        btn_del.clicked.connect(self.delete_selected_settings_instance)

        for b in [btn_add, btn_open, btn_del]:
            b.setFixedWidth(138)
            btn_vbox.addWidget(b)
        btn_vbox.addStretch()

        box.addLayout(btn_vbox)
        layout.addLayout(box)
        return page

    def _build_accounts_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 2, 4, 4)
        layout.setSpacing(10)

        self.lbl_accounts_mgmt = QLabel(I18n.t("accounts_mgmt"))
        self.lbl_accounts_mgmt.setObjectName("SectionLabel")
        layout.addWidget(self.lbl_accounts_mgmt)

        acc_box = QHBoxLayout()
        acc_box.setSpacing(12)

        self.settings_acc_table = QTableWidget(0, 3)
        self.settings_acc_table.setObjectName("SettingsTable")
        self.settings_acc_table.setHorizontalHeaderLabels(["Username", "Type", "Status"])
        self.settings_acc_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.settings_acc_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.settings_acc_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.settings_acc_table.verticalHeader().setVisible(False)
        self.settings_acc_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.settings_acc_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        acc_box.addWidget(self.settings_acc_table)

        btn_vbox = QVBoxLayout()
        btn_vbox.setSpacing(8)

        self.btn_s_ms = AnimatedButton(I18n.t("add_ms"))
        self.btn_s_ms.setObjectName("PillButton")
        self.btn_s_ms.clicked.connect(self.add_microsoft_account)

        self.btn_s_off = AnimatedButton(I18n.t("add_offline"))
        self.btn_s_off.setObjectName("PillButton")
        self.btn_s_off.clicked.connect(self.add_offline_account)

        self.btn_s_rem = AnimatedButton(I18n.t("remove"))
        self.btn_s_rem.setObjectName("PillButton")
        self.btn_s_rem.setStyleSheet("color: #FF5555; border: 1px solid rgba(255, 85, 85, 0.4);")
        self.btn_s_rem.clicked.connect(self.delete_current_account)

        for b in [self.btn_s_ms, self.btn_s_off, self.btn_s_rem]:
            b.setFixedWidth(115)
            btn_vbox.addWidget(b)
        btn_vbox.addStretch()

        acc_box.addLayout(btn_vbox)
        layout.addLayout(acc_box)
        return page

    def _build_language_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 2, 4, 4)
        layout.setSpacing(10)

        self.lbl_lang_header = QLabel(I18n.t("language"))
        self.lbl_lang_header.setObjectName("SectionLabel")
        layout.addWidget(self.lbl_lang_header)

        self.lang_list = QListWidget()
        self.lang_list.setObjectName("SettingsSidebar")
        self.lang_list.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        languages = [
            ("American English", "en"),
            ("Arabic (العربية)", "ar"),
            ("Deutsch", "de")
        ]

        current_code = I18n.get_language()
        active_row = 0

        for row, (display_name, code) in enumerate(languages):
            item = QListWidgetItem(f"   {display_name}")
            item.setData(Qt.ItemDataRole.UserRole, code)
            item.setSizeHint(QSize(100, 42))
            self.lang_list.addItem(item)
            if code == current_code:
                active_row = row

        self.lang_list.setCurrentRow(active_row)
        self.lang_list.currentRowChanged.connect(self.on_language_selected)
        layout.addWidget(self.lang_list)
        return page

    def on_language_selected(self, row: int):
        item = self.lang_list.item(row)
        if item:
            lang_code = item.data(Qt.ItemDataRole.UserRole)
            I18n.set_language(lang_code)
            self.config.set("language", lang_code)
            self.retranslate_ui()

    def retranslate_ui(self):
        tab_titles = [
            I18n.t("tab_play"),
            I18n.t("tab_mods"),
            I18n.t("tab_settings"),
            I18n.t("tab_console")
        ]
        for i, btn in enumerate(self.nav_bar.buttons):
            btn.setText(tab_titles[i])

        self.kill_btn.setText(I18n.t("kill_mc"))
        self.launch_btn.setText(I18n.t("play"))
        if self.status_lbl.text() in ["Ready to launch", "جاهز للتشغيل", "Bereit zum Starten"]:
            self.status_lbl.setText(I18n.t("ready"))

        self.inst_label.setText(I18n.t("active_inst"))
        self.acc_title.setText(I18n.t("account"))
        self.ram_title.setText(I18n.t("ram_alloc"))
        self.btn_new_inst.setText(I18n.t("new_instance"))
        self.btn_offline.setText(I18n.t("add_offline"))
        self.btn_ms.setText(I18n.t("add_ms"))

        self.mod_search_input.setPlaceholderText(I18n.t("search_mods"))
        self.btn_search.setText(I18n.t("search"))
        self.btn_install_mod.setText(I18n.t("download_mod"))

        if hasattr(self, "lbl_client_theme"):
            self.lbl_client_theme.setText(I18n.t("client_theme"))
        if hasattr(self, "lbl_folders"):
            self.lbl_folders.setText(I18n.t("folders"))
        if hasattr(self, "lbl_lang_header"):
            self.lbl_lang_header.setText(I18n.t("language"))
        if hasattr(self, "lbl_accounts_mgmt"):
            self.lbl_accounts_mgmt.setText(I18n.t("accounts_mgmt"))
        if hasattr(self, "lbl_proxy_title"):
            self.lbl_proxy_title.setText(I18n.t("proxy_title"))
        if hasattr(self, "lbl_proxy_notice"):
            self.lbl_proxy_notice.setText(I18n.t("proxy_notice"))
        if hasattr(self, "btn_apply_proxy"):
            self.btn_apply_proxy.setText(I18n.t("apply_proxy"))

        if hasattr(self, "folder_browse_buttons"):
            for b in self.folder_browse_buttons:
                b.setText(I18n.t("browse"))

    def _build_proxy_settings_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(4, 2, 4, 4)
        layout.setSpacing(12)

        self.lbl_proxy_title = QLabel(I18n.t("proxy_title"))
        self.lbl_proxy_title.setObjectName("SectionLabel")
        layout.addWidget(self.lbl_proxy_title)

        self.lbl_proxy_notice = QLabel(I18n.t("proxy_notice"))
        self.lbl_proxy_notice.setObjectName("MutedLabel")
        layout.addWidget(self.lbl_proxy_notice)

        self.rb_no_proxy = QRadioButton("None")
        self.rb_socks5 = QRadioButton("SOCKS5")
        self.rb_http = QRadioButton("HTTP")
        self.rb_no_proxy.setChecked(True)

        layout.addWidget(self.rb_no_proxy)
        layout.addWidget(self.rb_socks5)
        layout.addWidget(self.rb_http)

        host_row = QHBoxLayout()
        host_row.setSpacing(10)
        self.proxy_host = QLineEdit("127.0.0.1")
        self.proxy_port = QSpinBox()
        self.proxy_port.setRange(1, 65535)
        self.proxy_port.setValue(8080)
        self.proxy_port.setFixedWidth(90)
        host_row.addWidget(self.proxy_host)
        host_row.addWidget(self.proxy_port)
        layout.addLayout(host_row)

        self.btn_apply_proxy = AnimatedButton(I18n.t("apply_proxy"))
        self.btn_apply_proxy.setObjectName("PlayButton")
        self.btn_apply_proxy.setFixedHeight(40)
        self.btn_apply_proxy.clicked.connect(self.apply_proxy)
        layout.addWidget(self.btn_apply_proxy)

        layout.addStretch()
        return page

    def apply_proxy(self):
        if self.rb_no_proxy.isChecked():
            QNetworkProxy.setApplicationProxy(QNetworkProxy(QNetworkProxy.ProxyType.NoProxy))
            self.show_alert("Proxy", "Proxy disabled.")
        elif self.rb_http.isChecked():
            QNetworkProxy.setApplicationProxy(
                QNetworkProxy(QNetworkProxy.ProxyType.HttpProxy, self.proxy_host.text(), self.proxy_port.value())
            )
            self.show_alert("Proxy", f"HTTP Proxy set to {self.proxy_host.text()}:{self.proxy_port.value()}")
        elif self.rb_socks5.isChecked():
            QNetworkProxy.setApplicationProxy(
                QNetworkProxy(QNetworkProxy.ProxyType.Socks5Proxy, self.proxy_host.text(), self.proxy_port.value())
            )
            self.show_alert("Proxy", f"SOCKS5 Proxy set to {self.proxy_host.text()}:{self.proxy_port.value()}")

    def on_browser_instance_changed(self, index: int = -1):
        if self.sender() == self.browser_target_inst:
            self.content_browser_user_overridden = True

        if self.stack.currentIndex() == 1:
            self.run_mod_search()

    def open_current_instance_folder(self):
        inst_data = self.instance_box.currentData()
        if inst_data and inst_data.get("path"):
            path = inst_data["path"]
            if os.path.exists(path):
                self._open_dir(path)

    def open_selected_settings_instance_folder(self):
        curr = self.settings_inst_table.currentRow()
        if curr >= 0:
            name_item = self.settings_inst_table.item(curr, 0)
            if name_item:
                target_name = name_item.text().strip()
                instances = self.inst_mgr.list_instances()
                inst = next((i for i in instances if i.get("name") == target_name), None)
                if inst and os.path.exists(inst["path"]):
                    self._open_dir(inst["path"])

    def delete_instance_by_index(self, index: int):
        inst_data = self.instance_box.itemData(index)
        if not inst_data:
            return

        name = inst_data.get("name", "Unknown")
        path = inst_data.get("path")

        confirm = QMessageBox(self)
        confirm.setWindowTitle("Delete Instance")
        confirm.setText(f"Are you sure you want to delete instance '{name}'?\n\nThis will permanently remove its mods, saves, and configs.")
        confirm.setIcon(QMessageBox.Icon.Warning)
        confirm.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        confirm.setDefaultButton(QMessageBox.StandardButton.No)
        confirm.setStyleSheet(ThemeManager.get_style(self.current_theme))

        if confirm.exec() == QMessageBox.StandardButton.Yes:
            if self.inst_mgr.delete_instance(path):
                self.content_browser_user_overridden = False
                self.refresh_instances()
                self.show_alert("Deleted", f"Instance '{name}' was deleted.")
            else:
                self.show_alert("Error", f"Failed to delete directory: {path}", is_error=True)

    def delete_account_by_index(self, index: int):
        acc_id = self.account_box.itemData(index)
        if not acc_id:
            return

        accs = self.config.get("accounts", {})
        acc_data = accs.get(acc_id, {})
        uname = acc_data.get("name", "Account")

        confirm = QMessageBox(self)
        confirm.setWindowTitle("Remove Account")
        confirm.setText(f"Remove account '{uname}' from LowCore Launcher?")
        confirm.setIcon(QMessageBox.Icon.Question)
        confirm.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        confirm.setStyleSheet(ThemeManager.get_style(self.current_theme))

        if confirm.exec() == QMessageBox.StandardButton.Yes:
            if acc_id in accs:
                del accs[acc_id]
                self.config.set("accounts", accs)
                if self.config.get("active_account") == acc_id:
                    self.config.set("active_account", list(accs.keys())[0] if accs else "")
                self.refresh_accounts()
                self.show_alert("Removed", f"Account '{uname}' removed.")

    def delete_selected_settings_instance(self):
        curr = self.settings_inst_table.currentRow()
        if curr >= 0:
            name_item = self.settings_inst_table.item(curr, 0)
            if name_item:
                target_name = name_item.text().strip()
                instances = self.inst_mgr.list_instances()
                target_inst = next((i for i in instances if i.get("name") == target_name), None)
                if target_inst:
                    confirm = QMessageBox(self)
                    confirm.setWindowTitle("Delete Instance")
                    confirm.setText(f"Permanently delete instance '{target_name}'?")
                    confirm.setIcon(QMessageBox.Icon.Warning)
                    confirm.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    confirm.setStyleSheet(ThemeManager.get_style(self.current_theme))
                    if confirm.exec() == QMessageBox.StandardButton.Yes:
                        self.inst_mgr.delete_instance(target_inst["path"])
                        self.content_browser_user_overridden = False
                        self.refresh_instances()

    def delete_current_account(self):
        acc_id = self.account_box.currentData()
        if not acc_id:
            curr = self.settings_acc_table.currentRow()
            if curr >= 0:
                user_item = self.settings_acc_table.item(curr, 0)
                if user_item:
                    acc_name = user_item.text().replace("✔  ", "").strip()
                    accs = self.config.get("accounts", {})
                    acc_id = next((k for k, v in accs.items() if v.get("name") == acc_name), None)

        if not acc_id:
            self.show_alert("No Account", "No account selected to delete.", is_error=True)
            return

        accs = self.config.get("accounts", {})
        acc_data = accs.get(acc_id, {})
        uname = acc_data.get("name", "Account")

        confirm = QMessageBox(self)
        confirm.setWindowTitle("Remove Account")
        confirm.setText(f"Remove account '{uname}' from LowCore Launcher?")
        confirm.setIcon(QMessageBox.Icon.Question)
        confirm.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        confirm.setStyleSheet(ThemeManager.get_style(self.current_theme))

        if confirm.exec() == QMessageBox.StandardButton.Yes:
            if acc_id in accs:
                del accs[acc_id]
                self.config.set("accounts", accs)
                if self.config.get("active_account") == acc_id:
                    self.config.set("active_account", list(accs.keys())[0] if accs else "")
                self.refresh_accounts()
                self.show_alert("Removed", f"Account '{uname}' removed.")

    def start_startup_sequence(self):
        if hasattr(self, "splash_logo") and self.splash_logo:
            self.splash_logo_anim = QPropertyAnimation(self.splash_logo, b"target_size")
            self.splash_logo_anim.setDuration(950)
            self.splash_logo_anim.setStartValue(50)
            self.splash_logo_anim.setEndValue(140)
            self.splash_logo_anim.setEasingCurve(QEasingCurve.Type.OutBack)
            self.splash_logo_anim.start()

        self.startup_anim = QPropertyAnimation(self.splash_bar, b"value")
        self.startup_anim.setDuration(3000)
        self.startup_anim.setStartValue(0)
        self.startup_anim.setEndValue(3000)
        self.startup_anim.setEasingCurve(QEasingCurve.Type.Linear)

        QTimer.singleShot(750, lambda: self.splash_status.setText("Initializing client modules..."))
        QTimer.singleShot(1650, lambda: self.splash_status.setText("Checking installation environment..."))
        QTimer.singleShot(2550, lambda: self.splash_status.setText("Ready!"))

        self.startup_anim.finished.connect(self.fade_out_splash)
        self.startup_anim.start()

    def fade_out_splash(self):
        fade = QGraphicsOpacityEffect(self.splash_overlay)
        self.splash_overlay.setGraphicsEffect(fade)
        self.fade_anim = QPropertyAnimation(fade, b"opacity")
        self.fade_anim.setDuration(320)
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_anim.finished.connect(self.splash_overlay.deleteLater)
        self.fade_anim.start()

    def on_tab_switch(self, index: int):
        self.stack.setCurrentIndex(index)
        self.easter_egg_buffer = ""
        if index == 0:
            self.update_instance_info()
        elif index == 1:
            self.run_mod_search()
        elif index == 3:
            self.refresh_main_console_display()

    def animate_progress_bar(self, expand: bool):
        self.progress_anim = QPropertyAnimation(self.progress_bar, b"maximumHeight")
        self.progress_anim.setDuration(220)
        self.progress_anim.setStartValue(self.progress_bar.height())
        self.progress_anim.setEndValue(8 if expand else 0)
        self.progress_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.progress_anim.start()

    def show_alert(self, title: str, text: str, is_error: bool = False):
        msg = QMessageBox(self)
        msg.setWindowTitle(title)
        msg.setText(text)
        msg.setIcon(QMessageBox.Icon.Critical if is_error else QMessageBox.Icon.Information)
        msg.setStyleSheet(ThemeManager.get_style(self.current_theme))
        msg.exec()

    def fetch_all_versions(self):
        def fetch():
            try:
                downloader = VersionDownloader(self.config.get("game_dir"))
                manifest = downloader.fetch_manifest()
                releases = [v["id"] for v in manifest["versions"] if v.get("type") == "release"]
                if releases:
                    self.all_mojang_versions = releases
            except Exception:
                pass
        self.threadpool.start(fetch)

    def refresh_instances(self):
        self.instance_box.clear()
        self.browser_target_inst.clear()
        if hasattr(self, "settings_inst_table"):
            self.settings_inst_table.setRowCount(0)

        instances = [inst for inst in self.inst_mgr.list_instances() if inst.get("name") != "Default-1211"]
        saved_active = self.config.get("active_instance", "")
        target_idx = 0

        if not instances:
            self.instance_box.addItem("Get started by making a new instance ➔", userData=None)
            self.instance_box.set_placeholder_mode(True)
            self.status_lbl.setText("No active instance. Click + New Instance.")
        else:
            self.instance_box.set_placeholder_mode(False)
            for idx, inst in enumerate(instances):
                total_played = format_playtime(inst.get("playtime_seconds", 0))
                
                play_display = f"{inst['name']}  ·  {inst.get('loader', 'Fabric')} {inst['version']}  ({total_played})"
                self.instance_box.addItem(play_display, userData=inst)

                browser_display = f"{inst['name']}  ·  {inst.get('loader', 'Fabric')} {inst['version']}"
                self.browser_target_inst.addItem(browser_display, userData=inst)

                inst_folder = os.path.basename(inst["path"])
                if inst_folder == saved_active or inst["name"] == saved_active:
                    target_idx = idx

                if hasattr(self, "settings_inst_table"):
                    row = self.settings_inst_table.rowCount()
                    self.settings_inst_table.insertRow(row)
                    self.settings_inst_table.setItem(row, 0, QTableWidgetItem(inst["name"]))
                    self.settings_inst_table.setItem(row, 1, QTableWidgetItem(inst["version"]))
                    self.settings_inst_table.setItem(row, 2, QTableWidgetItem(inst.get("loader", "Fabric")))
                    self.settings_inst_table.setItem(row, 3, QTableWidgetItem(total_played))

            self.instance_box.setCurrentIndex(target_idx)
            if not self.content_browser_user_overridden:
                self.browser_target_inst.setCurrentIndex(target_idx)

        self.update_instance_info()

    def update_instance_info(self):
        if not hasattr(self, "stat_playtime_val"):
            return

        inst = self.instance_box.currentData()
        path = inst.get("path") if isinstance(inst, dict) else None
        if not path:
            for lbl in (self.stat_playtime_val, self.stat_mods_val, self.stat_last_val):
                lbl.setText("—")
            return

        meta = inst
        try:
            with open(os.path.join(path, "instance.json"), "r", encoding="utf-8") as f:
                meta = json.load(f)
        except Exception:
            pass

        self.stat_playtime_val.setText(format_playtime(int(meta.get("playtime_seconds", 0))))
        self.stat_last_val.setText(format_last_played(meta.get("last_played")))

        if str(meta.get("loader", inst.get("loader", ""))).strip().lower() == "vanilla":
            self.stat_mods_val.setText("—")
        else:
            try:
                count = sum(1 for f in os.listdir(os.path.join(path, "mods")) if f.lower().endswith(".jar"))
            except OSError:
                count = 0
            self.stat_mods_val.setText(str(count))

    def on_instance_changed(self, index: int):
        inst_data = self.instance_box.currentData()
        if inst_data and inst_data.get("path"):
            folder_name = os.path.basename(inst_data["path"])
            self.config.set("active_instance", folder_name)

            if not self.content_browser_user_overridden:
                for b_idx in range(self.browser_target_inst.count()):
                    b_data = self.browser_target_inst.itemData(b_idx)
                    if b_data and os.path.basename(b_data.get("path", "")) == folder_name:
                        self.browser_target_inst.setCurrentIndex(b_idx)
                        break

        self.update_instance_info()

    def prompt_new_instance(self):
        dlg = NewInstanceDialog(self.all_mojang_versions, self.current_theme, self)
        if dlg.exec():
            data = dlg.get_data()
            new_inst = self.inst_mgr.create_instance(
                name=data["name"],
                version=data["version"],
                loader=data["loader"]
            )
            self.content_browser_user_overridden = False
            self.config.set("active_instance", os.path.basename(new_inst["path"]))
            self.refresh_instances()
            self.status_lbl.setText(I18n.t("ready"))

    def on_search_text_changed(self, text: str):
        self.search_debounce_timer.start()

    def run_mod_search(self):
        self.search_debounce_timer.stop()
        query = self.mod_search_input.text().strip()
        inst_data = self.browser_target_inst.currentData() or self.instance_box.currentData() or {}
        ver = inst_data.get("version", "1.21.1")
        
        p_type = self.content_type_bar.get_selected_type()
        loader = inst_data.get("loader", "fabric").lower() if p_type == "mod" else None

        self.mod_results_list.clear()
        self.card_widgets.clear()

        label_type = "Resource Pack" if p_type == "resourcepack" else p_type.capitalize()
        loading_item = QListWidgetItem(f"Searching {label_type}s on Modrinth...")
        loading_item.setFlags(Qt.ItemFlag.NoItemFlags)
        self.mod_results_list.addItem(loading_item)

        worker = ModSearchWorker(query, ver, loader, p_type)
        worker.signals.results_ready.connect(self.display_mod_results)
        worker.signals.error.connect(lambda err: self.display_mod_results([]))
        self.threadpool.start(worker)

    def display_mod_results(self, hits: list):
        self.mod_results_list.clear()
        self.card_widgets.clear()

        if not hits:
            empty_item = QListWidgetItem("No compatible assets found for this search.")
            empty_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.mod_results_list.addItem(empty_item)
            return

        theme_data = ThemeManager.get_theme_data(self.current_theme)

        for item in hits:
            list_item = QListWidgetItem()
            list_item.setSizeHint(QSize(self.mod_results_list.width() - 32, 72))
            list_item.setData(Qt.ItemDataRole.UserRole, (item.get("project_id", ""), item.get("title", "Unknown")))

            card = ModItemCard(item, theme_data, parent=self.mod_results_list)
            self.mod_results_list.addItem(list_item)
            self.mod_results_list.setItemWidget(list_item, card)
            self.card_widgets.append(card)

            icon_url = item.get("icon_url")
            if icon_url:
                loader = ModIconLoader(icon_url)
                loader.signals.loaded.connect(lambda data, c=card: self._apply_loaded_thumbnail(data, c))
                self.icon_pool.start(loader)

        if self.mod_results_list.count() > 0:
            self.mod_results_list.setCurrentRow(0)

    def _apply_loaded_thumbnail(self, data: bytes, card: ModItemCard):
        if sip.isdeleted(card):
            return
        pix = QPixmap()
        if pix.loadFromData(data):
            card.set_thumbnail(pix)

    def on_mod_selection_changed(self, row: int):
        for idx, card in enumerate(self.card_widgets):
            if not sip.isdeleted(card):
                card.set_selected_state(idx == row)

    def install_selected_mod(self):
        item = self.mod_results_list.currentItem()
        if not item or not item.data(Qt.ItemDataRole.UserRole):
            self.show_alert("No Selection", "Please select a valid item from the list.", is_error=True)
            return

        project_id, mod_title = item.data(Qt.ItemDataRole.UserRole)
        target_inst = self.browser_target_inst.currentData() or self.instance_box.currentData()
        if not target_inst:
            self.show_alert("No Instance", "Please create an instance before downloading content.", is_error=True)
            return

        target_dir = target_inst.get("path")
        chosen_version = target_inst.get("version", "1.21.1")
        chosen_loader = target_inst.get("loader", "Fabric").lower()
        p_type = self.content_type_bar.get_selected_type()

        if p_type == "shader":
            sub_folder = "shaderpacks"
        elif p_type == "resourcepack":
            sub_folder = "resourcepacks"
        else:
            sub_folder = "mods"

        final_dest = os.path.join(target_dir, sub_folder)
        self.btn_install_mod.setEnabled(False)
        self.btn_install_mod.setText("Resolving dependencies & downloading...")

        worker = ModInstallWorker(project_id, chosen_version, chosen_loader, final_dest)

        def on_done(installed_files):
            self.btn_install_mod.setEnabled(True)
            self.btn_install_mod.setText(I18n.t("download_mod"))
            files_str = "\n• " + "\n• ".join(installed_files)
            self.show_alert(
                "Installed",
                f"Successfully installed into {target_inst['name']}/{sub_folder}:{files_str}"
            )

        def on_err(err_msg):
            self.btn_install_mod.setEnabled(True)
            self.btn_install_mod.setText(I18n.t("download_mod"))
            self.show_alert("Download Failed", f"Could not download asset:\n{err_msg}", is_error=True)

        worker.signals.status.connect(lambda txt: self.btn_install_mod.setText(txt))
        worker.signals.completed.connect(on_done)
        worker.signals.error.connect(on_err)
        self.threadpool.start(worker)

    def kill_active_instance(self):
        if self.active_process:
            try:
                proc = psutil.Process(self.active_process.pid)
                for child in proc.children(recursive=True):
                    child.kill()
                proc.kill()
                self.status_lbl.setText("Game terminated.")
                self.launch_btn.setEnabled(True)
                self.animate_progress_bar(expand=False)
                DiscordRPCManager.get_instance().set_menu_presence()
                self.show_alert("Terminated", "Minecraft process was force-closed.")
            except Exception as e:
                self.show_alert("Error", f"Could not kill process: {e}", is_error=True)

    def on_theme_changed(self, theme_name: str):
        self.current_theme = theme_name
        self.config.set("theme_name", theme_name)
        self.apply_current_theme()
        if hasattr(self, "content_type_bar"):
            self.content_type_bar.theme_data = ThemeManager.get_theme_data(theme_name)
            self.content_type_bar.apply_styles()
        self.run_mod_search()
        self.refresh_main_console_display()

    def on_ram_changed(self, index: int):
        val = self.ram_dropdown.itemData(index)
        if val:
            self.config.set("allocated_ram_mb", val)

    def refresh_accounts(self):
        self.account_box.clear()
        if hasattr(self, "settings_acc_table"):
            self.settings_acc_table.setRowCount(0)

        accounts = self.config.get("accounts", {})
        active = self.config.get("active_account", "")

        idx = 0
        target = 0
        for acc_id, acc in accounts.items():
            avatar = AvatarService.get_avatar(acc, size=24)
            acc_type_str = "Offline" if acc["type"] == "offline" else "Microsoft"
            label = f"{acc['name']}  ·  {acc_type_str}"
            self.account_box.addItem(label, userData=acc_id, icon=avatar)

            if hasattr(self, "settings_acc_table"):
                row = self.settings_acc_table.rowCount()
                self.settings_acc_table.insertRow(row)
                prefix = "✔  " if acc_id == active else "    "
                self.settings_acc_table.setItem(row, 0, QTableWidgetItem(f"{prefix}{acc['name']}"))
                self.settings_acc_table.setItem(row, 1, QTableWidgetItem(acc_type_str))
                self.settings_acc_table.setItem(row, 2, QTableWidgetItem("Ready"))

            if acc_id == active:
                target = idx
            idx += 1

        if self.account_box.count() > 0:
            self.account_box.setCurrentIndex(target)

    def on_account_changed(self, index: int):
        acc_id = self.account_box.itemData(index)
        if acc_id:
            self.config.set("active_account", acc_id)

    def add_offline_account(self):
        name, ok = QInputDialog.getText(self, "New Offline Player", "Username (3–16 characters):")
        if not ok or not name.strip():
            return

        cleaned_name = name.strip()
        
        # Validate username length (Min 3, Max 16) and characters (letters, numbers, underscores)
        if not (3 <= len(cleaned_name) <= 16) or not all(c.isalnum() or c == '_' for c in cleaned_name):
            self.show_alert(
                "Invalid Username",
                "Minecraft offline usernames must be between **3 and 16 characters** long and can only contain letters, numbers, and underscores (_).",
                is_error=True
            )
            return

        acc = AuthService.create_offline_account(cleaned_name)
        accs = self.config.get("accounts", {})
        accs[acc["id"]] = acc
        self.config.set("accounts", accs)
        self.config.set("active_account", acc["id"])
        self.refresh_accounts()

    def add_microsoft_account(self):
        try:
            device_info = AuthService.start_device_code_flow()
            user_code = device_info["user_code"]
            verification_uri = device_info.get("verification_uri", "https://microsoft.com/link")
            device_code = device_info["device_code"]
            interval = device_info.get("interval", 5)
            expires_in = device_info.get("expires_in", 900)

            webbrowser.open(verification_uri)

            dialog = QDialog(self)
            dialog.setWindowTitle("Microsoft Sign-In")
            dialog.setFixedSize(400, 220)
            theme_dict = ThemeManager.get_theme_data(self.current_theme)
            dialog.setStyleSheet(f"""
                {ThemeManager.get_style(self.current_theme)}
                QDialog {{ background-color: {theme_dict['card_bg']}; }}
            """)

            d_layout = QVBoxLayout(dialog)
            d_layout.setContentsMargins(24, 20, 24, 20)
            d_layout.setSpacing(10)

            instruct = QLabel("Go to <b>microsoft.com/link</b> and enter this code:")
            instruct.setAlignment(Qt.AlignmentFlag.AlignCenter)
            instruct.setStyleSheet(f"font-size: 13px; color: {theme_dict['text_sub']}; border: none; background: transparent;")
            d_layout.addWidget(instruct)

            code_lbl = QLabel(user_code)
            code_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            code_lbl.setStyleSheet(f"""
                font-size: 26px;
                font-weight: 900;
                color: {theme_dict['accent']};
                letter-spacing: 3px;
                padding: 10px;
                background-color: {theme_dict['input_bg']};
                border: 1px dashed {theme_dict['accent']};
                border-radius: 8px;
            """)
            d_layout.addWidget(code_lbl)

            status = QLabel("Waiting for authorization in your browser...")
            status.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status.setStyleSheet(f"font-size: 11px; color: {theme_dict['text_sub']}; border: none; background: transparent;")
            d_layout.addWidget(status)

            cancel_btn = AnimatedButton("Cancel")
            cancel_btn.setObjectName("PillButton")
            cancel_btn.clicked.connect(dialog.reject)
            d_layout.addWidget(cancel_btn)

            worker = DeviceAuthWorker(device_code, interval, expires_in)

            def on_success():
                acc = worker.account_data
                accs = self.config.get("accounts", {})
                accs[acc["id"]] = acc
                self.config.set("accounts", accs)
                self.config.set("active_account", acc["id"])
                self.refresh_accounts()
                dialog.accept()
                self.show_alert("Welcome", f"Logged in successfully as {acc['name']}!")

            def on_failure(err_msg):
                dialog.reject()
                self.show_alert("Sign-In Failed", str(err_msg), is_error=True)

            worker.signals.progress.connect(lambda msg, cur, tot: status.setText(msg))
            worker.signals.finished.connect(on_success)
            worker.signals.error.connect(on_failure)

            self.threadpool.start(worker)
            dialog.exec()

        except Exception as e:
            self.show_alert("Error", f"Failed to start device sign-in: {e}", is_error=True)

    def handle_launch(self):
        inst_data = self.instance_box.currentData()
        if not inst_data:
            self.prompt_new_instance()
            return

        active_id = self.config.get("active_account")
        account = self.config.get("accounts", {}).get(active_id)
        if not account:
            self.show_alert("No Account", "Create an Offline or Microsoft account first.", is_error=True)
            return

        if account.get("type") == "offline":
            confirm = QMessageBox(self)
            confirm.setWindowTitle("Account Offline Warning")
            confirm.setText(
                "Warning: Your Minecraft account is logged in as offline, not online.\n\n"
                "You will not be able to join premium online-mode servers (HTTP 401).\n\n"
                "Are you sure you want to continue?"
            )
            confirm.setIcon(QMessageBox.Icon.Warning)
            confirm.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            confirm.setDefaultButton(QMessageBox.StandardButton.No)
            confirm.setStyleSheet(ThemeManager.get_style(self.current_theme))
            res = confirm.exec()
            if res != QMessageBox.StandardButton.Yes:
                return

        version = inst_data.get("version", "1.21.1")
        loader = inst_data.get("loader", "Fabric")
        instance_dir = inst_data.get("path")
        root_dir = self.config.get("game_dir")
        selected_ram = self.ram_dropdown.currentData() or 4096

        custom_res = {
            "width": self.config.get("res_width", 1280),
            "height": self.config.get("res_height", 720),
            "fullscreen": self.config.get("fullscreen", False)
        }

        self.clear_main_console()
        self.launch_btn.setEnabled(False)
        self.animate_progress_bar(expand=True)

        worker = LaunchWorker(
            inst_mgr=self.inst_mgr,
            root_dir=root_dir,
            instance_dir=instance_dir,
            version_id=version,
            loader=loader,
            account=account,
            ram_mb=selected_ram,
            custom_res=custom_res,
            parent_win=self
        )
        worker.signals.progress.connect(self.on_progress)
        worker.signals.log.connect(self.append_log_line)
        worker.signals.finished.connect(self.on_finished)
        worker.signals.error.connect(self.on_error)
        self.threadpool.start(worker)

    def on_progress(self, desc: str, cur: int, tot: int):
        self.status_lbl.setText(desc)
        if desc.startswith("Minecraft closed"):
            self.update_instance_info()
        if tot > 0:
            self.progress_bar.setMaximum(tot)
            self.progress_bar.setValue(cur)
        else:
            self.progress_bar.setMaximum(0)

    def on_finished(self):
        self.status_lbl.setText("Minecraft is running")
        self.animate_progress_bar(expand=False)
        self.launch_btn.setEnabled(True)
        self.refresh_instances()
        self.nav_bar.select_tab(3)

    def on_error(self, err: str):
        self.append_log_line(f"[LAUNCH ERROR] {err}")  # previously the reason was lost when the log window opened
        self.status_lbl.setText("Launch failed / Game closed")
        self.animate_progress_bar(expand=False)
        self.launch_btn.setEnabled(True)
        self.refresh_instances()

        if self.config.get("show_log_on_exit", True):
            QTimer.singleShot(100, self.open_standalone_log_dialog)
        else:
            self.show_alert("Launch Notice", str(err), is_error=True)
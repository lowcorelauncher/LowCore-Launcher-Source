class ThemeManager:
    THEMES = {
        "Dark Mode": {
            "bg": "#121316",
            "card_bg": "#1A1B20",
            "border": "#282A30",
            "text": "#FFFFFF",
            "text_sub": "#8A909E",
            "accent": "#E85A52",
            "accent_hover": "#D14A43",
            "pill_bg": "#22242B",
            "pill_hover": "#2B2E37",
            "input_bg": "#141518",
            "dropdown_popup_bg": "#1A1B20",
            "item_hover": "#262833",
            "status_text": "#C5CBD6",
            "accent_text": "#FFFFFF",
            "is_light": False
        },
        "OLED Black": {
            "bg": "#000000",
            "card_bg": "#08080A",
            "border": "#1A1B1E",
            "text": "#FFFFFF",
            "text_sub": "#9EA4B0",
            "accent": "#E85A52",
            "accent_hover": "#FF6B63",
            "pill_bg": "#101114",
            "pill_hover": "#1C1D22",
            "input_bg": "#050506",
            "dropdown_popup_bg": "#08080A",
            "item_hover": "#16181F",
            "status_text": "#C5CBD6",
            "accent_text": "#FFFFFF",
            "is_light": False
        },
        "Light Mode": {
            "bg": "#F5F6F8",
            "card_bg": "#FFFFFF",
            "border": "#E2E5EA",
            "text": "#1A1C20",
            "text_sub": "#636975",
            "accent": "#E85A52",
            "accent_hover": "#D14A43",
            "pill_bg": "#EBEDF2",
            "pill_hover": "#E0E3EA",
            "input_bg": "#F0F2F5",
            "dropdown_popup_bg": "#FFFFFF",
            "item_hover": "#E2E6EE",
            "status_text": "#4A5060",
            "accent_text": "#FFFFFF",
            "is_light": True
        },
        "Catppuccin Mocha": {
            "bg": "#11111B",
            "card_bg": "#181825",
            "border": "#313244",
            "text": "#CDD6F4",
            "text_sub": "#A6ADC8",
            "accent": "#CBA6F7",
            "accent_hover": "#D1B1F8",
            "pill_bg": "#1E1E2E",
            "pill_hover": "#313244",
            "input_bg": "#11111B",
            "dropdown_popup_bg": "#181825",
            "item_hover": "#313244",
            "status_text": "#BAC2DE",
            "accent_text": "#181825",
            "is_light": False
        },
        "Catppuccin Macchiato": {
            "bg": "#181926",
            "card_bg": "#1E2030",
            "border": "#363A4F",
            "text": "#CAD3F5",
            "text_sub": "#A5ADCB",
            "accent": "#C6A0F6",
            "accent_hover": "#CDABF7",
            "pill_bg": "#24273A",
            "pill_hover": "#363A4F",
            "input_bg": "#181926",
            "dropdown_popup_bg": "#1E2030",
            "item_hover": "#363A4F",
            "status_text": "#B8C0E0",
            "accent_text": "#1E2030",
            "is_light": False
        },
        "Catppuccin Latte": {
            "bg": "#DCE0E8",
            "card_bg": "#EFF1F5",
            "border": "#CCD0DA",
            "text": "#4C4F69",
            "text_sub": "#6C6F85",
            "accent": "#8839EF",
            "accent_hover": "#7832D2",
            "pill_bg": "#E6E9EF",
            "pill_hover": "#CCD0DA",
            "input_bg": "#E6E9EF",
            "dropdown_popup_bg": "#EFF1F5",
            "item_hover": "#CCD0DA",
            "status_text": "#5C5F77",
            "accent_text": "#FFFFFF",
            "is_light": True
        },
        "Rose Pine": {
            "bg": "#191724",
            "card_bg": "#1F1D2E",
            "border": "#26233A",
            "text": "#E0DEF4",
            "text_sub": "#908CAA",
            "accent": "#C4A7E7",
            "accent_hover": "#CBB2EA",
            "pill_bg": "#26233A",
            "pill_hover": "#403D52",
            "input_bg": "#191724",
            "dropdown_popup_bg": "#1F1D2E",
            "item_hover": "#2A2740",
            "status_text": "#E0DEF4",
            "accent_text": "#1F1D2E",
            "is_light": False
        },
        "Rose Pine Dawn": {
            "bg": "#FAF4ED",
            "card_bg": "#FFFAF3",
            "border": "#DFDAD9",
            "text": "#575279",
            "text_sub": "#797593",
            "accent": "#B4637A",
            "accent_hover": "#9E576B",
            "pill_bg": "#F2E9E1",
            "pill_hover": "#EBE2DA",
            "input_bg": "#F4EDE8",
            "dropdown_popup_bg": "#FFFAF3",
            "item_hover": "#F2E9E1",
            "status_text": "#575279",
            "accent_text": "#FFFFFF",
            "is_light": True
        },
        "Tokyo Night": {
            "bg": "#16161E",
            "card_bg": "#1A1B26",
            "border": "#292E42",
            "text": "#C0CAF5",
            "text_sub": "#7982A9",
            "accent": "#7AA2F7",
            "accent_hover": "#8AADF8",
            "pill_bg": "#24283B",
            "pill_hover": "#2F3549",
            "input_bg": "#16161E",
            "dropdown_popup_bg": "#1A1B26",
            "item_hover": "#292E42",
            "status_text": "#A9B1D6",
            "accent_text": "#1A1B26",
            "is_light": False
        },
        "Dracula": {
            "bg": "#21222C",
            "card_bg": "#282A36",
            "border": "#44475A",
            "text": "#F8F8F2",
            "text_sub": "#9AA3CF",
            "accent": "#BD93F9",
            "accent_hover": "#C5A0FA",
            "pill_bg": "#2F3240",
            "pill_hover": "#44475A",
            "input_bg": "#21222C",
            "dropdown_popup_bg": "#282A36",
            "item_hover": "#44475A",
            "status_text": "#CFCFE0",
            "accent_text": "#282A36",
            "is_light": False
        },
        "Nord": {
            "bg": "#272C36",
            "card_bg": "#2E3440",
            "border": "#3B4252",
            "text": "#ECEFF4",
            "text_sub": "#9AA5BC",
            "accent": "#88C0D0",
            "accent_hover": "#96C8D6",
            "pill_bg": "#3B4252",
            "pill_hover": "#434C5E",
            "input_bg": "#272C36",
            "dropdown_popup_bg": "#2E3440",
            "item_hover": "#434C5E",
            "status_text": "#D8DEE9",
            "accent_text": "#2E3440",
            "is_light": False
        },
        "Gruvbox Dark": {
            "bg": "#1D2021",
            "card_bg": "#282828",
            "border": "#504945",
            "text": "#EBDBB2",
            "text_sub": "#A89984",
            "accent": "#FE8019",
            "accent_hover": "#FE8F35",
            "pill_bg": "#32302F",
            "pill_hover": "#3C3836",
            "input_bg": "#1D2021",
            "dropdown_popup_bg": "#282828",
            "item_hover": "#3C3836",
            "status_text": "#D5C4A1",
            "accent_text": "#282828",
            "is_light": False
        },
        "Solarized Dark": {
            "bg": "#00212B",
            "card_bg": "#002B36",
            "border": "#0F4452",
            "text": "#A3B1B1",
            "text_sub": "#83979C",
            "accent": "#268BD2",
            "accent_hover": "#4099D7",
            "pill_bg": "#073642",
            "pill_hover": "#0E4756",
            "input_bg": "#00212B",
            "dropdown_popup_bg": "#002B36",
            "item_hover": "#073642",
            "status_text": "#A3B1B1",
            "accent_text": "#002B36",
            "is_light": False
        },
        "Solarized Light": {
            "bg": "#EEE8D5",
            "card_bg": "#FDF6E3",
            "border": "#DDD6C1",
            "text": "#475D64",
            "text_sub": "#66797E",
            "accent": "#268BD2",
            "accent_hover": "#217AB9",
            "pill_bg": "#EEE8D5",
            "pill_hover": "#E3DCC6",
            "input_bg": "#F5EED9",
            "dropdown_popup_bg": "#FDF6E3",
            "item_hover": "#EEE8D5",
            "status_text": "#475D64",
            "accent_text": "#1A1C20",
            "is_light": True
        }
    }

    DEFAULT_THEME = "Dark Mode"

    @classmethod
    def get_theme_names(cls) -> list:
        """All theme names in display order (used to fill the Settings dropdown)."""
        return list(cls.THEMES.keys())

    @classmethod
    def is_valid(cls, theme_name: str) -> bool:
        return theme_name in cls.THEMES

    @classmethod
    def is_light(cls, theme_name: str) -> bool:
        return bool(cls.get_theme_data(theme_name).get("is_light", False))

    @classmethod
    def get_theme_data(cls, theme_name: str) -> dict:
        data = dict(cls.THEMES.get(theme_name, cls.THEMES[cls.DEFAULT_THEME]))
        data.setdefault("accent_text", "#FFFFFF")          # text colour on accent-coloured buttons
        data.setdefault("status_text", data["text_sub"])   # launch status line
        data.setdefault("is_light", False)
        return data

    @classmethod
    def get_style(cls, theme_name: str) -> str:
        t = cls.get_theme_data(theme_name)
        return f"""
            QWidget#CentralWidget {{
                background-color: {t['bg']};
            }}

            QDialog {{
                background-color: {t['card_bg']};
            }}

            QToolTip {{
                background-color: {t['card_bg']};
                color: {t['text']};
                border: 1px solid {t['border']};
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 12px;
                font-weight: 600;
            }}

            QLabel {{
                color: {t['text']};
                font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            }}

            QLabel#BrandTitle {{
                font-size: 20px;
                font-weight: 900;
                color: {t['text']};
            }}

            QLabel#BrandSlogan {{
                font-size: 11px;
                font-weight: 700;
                color: {t['accent']};
            }}

            QLabel#SectionLabel {{
                font-size: 11px;
                font-weight: 800;
                color: {t['text_sub']};
            }}

            QLabel#SettingsItemLabel {{
                font-size: 13px;
                font-weight: 700;
                color: {t['text']};
            }}

            QLabel#MutedLabel {{
                font-size: 11px;
                font-weight: 600;
                color: {t['text_sub']};
            }}

            QLabel#StatusLabel {{
                color: {t['status_text']};
            }}

            QFrame#Card {{
                background-color: {t['card_bg']};
                border: 1px solid {t['border']};
                border-radius: 12px;
            }}

            QFrame#StatTile {{
                background-color: {t['card_bg']};
                border: 1px solid {t['border']};
                border-radius: 10px;
            }}

            QLabel#StatValue {{
                font-size: 15px;
                font-weight: 800;
                color: {t['text']};
                background: transparent;
            }}

            QPushButton#PlayButton {{
                background-color: {t['accent']};
                color: {t['accent_text']};
                font-size: 15px;
                font-weight: 900;
                border: none;
                border-radius: 10px;
            }}
            QPushButton#PlayButton:hover {{
                background-color: {t['accent_hover']};
            }}
            QPushButton#PlayButton:disabled {{
                background-color: {t['border']};
                color: {t['text_sub']};
            }}

            QPushButton#PillButton {{
                background-color: {t['pill_bg']};
                color: {t['text']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
                padding: 8px 12px;
            }}
            QPushButton#PillButton:hover {{
                background-color: {t['pill_hover']};
            }}

            QPushButton#CustomCombo {{
                background-color: {t['pill_bg']};
                color: {t['text']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                font-size: 13px;
                font-weight: 700;
                padding: 10px 14px;
                text-align: left;
            }}
            QPushButton#CustomCombo:hover {{
                background-color: {t['pill_hover']};
            }}

            QFrame#DropdownPopupFrame {{
                background-color: {t['dropdown_popup_bg']};
                border: 1px solid {t['border']};
                border-radius: 10px;
            }}

            QFrame#DropdownRowWidget {{
                background-color: transparent;
                border-radius: 6px;
            }}
            QFrame#DropdownRowWidget:hover {{
                background-color: {t['item_hover']};
            }}

            QPushButton#DropdownDeleteBtn {{
                background: transparent;
                border: none;
                color: {t['text_sub']};
                font-size: 15px;
                border-radius: 4px;
            }}
            QPushButton#DropdownDeleteBtn:hover {{
                color: #FF5555;
                background-color: rgba(255, 85, 85, 0.25);
            }}

            QLineEdit {{
                background-color: {t['input_bg']};
                color: {t['text']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                padding: 9px 12px;
                font-size: 13px;
                font-weight: 600;
            }}
            QLineEdit:focus {{
                border: 1px solid {t['accent']};
            }}

            QSpinBox {{
                background-color: {t['input_bg']};
                color: {t['text']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                padding: 6px;
                font-size: 13px;
                font-weight: 600;
            }}

            QRadioButton {{
                color: {t['text']};
                font-size: 13px;
                font-weight: 600;
                spacing: 8px;
                background: transparent;
            }}
            QRadioButton::indicator {{
                width: 14px;
                height: 14px;
                border-radius: 8px;
                border: 2px solid {t['text_sub']};
                background: transparent;
            }}
            QRadioButton::indicator:hover {{
                border-color: {t['accent']};
            }}
            QRadioButton::indicator:checked {{
                border: 2px solid {t['accent']};
                background: {t['accent']};
            }}

            QPlainTextEdit#ConsoleLog {{
                background-color: {t['input_bg']};
                color: #A0C080;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 12px;
                border: 1px solid {t['border']};
                border-radius: 10px;
                padding: 12px;
            }}

            QListWidget#ModsList, QListWidget#SettingsSidebar {{
                background-color: {t['input_bg']};
                border: 1px solid {t['border']};
                border-radius: 10px;
                outline: none;
                padding: 6px;
            }}
            QListWidget#SettingsSidebar::item {{
                color: {t['text_sub']};
                font-size: 13px;
                font-weight: 700;
                padding: 10px 14px;
                border-radius: 6px;
                margin-bottom: 2px;
            }}
            QListWidget#SettingsSidebar::item:hover {{
                background-color: {t['pill_hover']};
                color: {t['text']};
            }}
            QListWidget#SettingsSidebar::item:selected {{
                background-color: {t['pill_bg']};
                color: {t['text']};
                border-left: 3px solid {t['accent']};
            }}

            QListWidget#ModsList::item {{
                background: transparent;
                border-radius: 8px;
                padding: 2px;
                margin-bottom: 6px;
                border: none;
            }}
            QListWidget#ModsList::item:hover, QListWidget#ModsList::item:selected {{
                background: transparent;
            }}

            QScrollBar:vertical {{
                border: none;
                background-color: transparent;
                width: 8px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background-color: {t['border']};
                min-height: 24px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical:hover {{
                background-color: {t['text_sub']};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}

            QTableWidget#SettingsTable {{
                background-color: {t['input_bg']};
                color: {t['text']};
                border: 1px solid {t['border']};
                border-radius: 8px;
                gridline-color: {t['border']};
                outline: none;
            }}
            QTableWidget#SettingsTable::item {{
                padding: 8px 10px;
                color: {t['text']};
            }}
            QTableWidget#SettingsTable::item:selected {{
                background-color: {t['item_hover']};
                color: {t['text']};
                border: none;
            }}
            QHeaderView::section {{
                background-color: {t['pill_bg']};
                color: {t['text_sub']};
                border: none;
                padding: 8px;
                font-weight: 800;
                font-size: 11px;
            }}

            QMessageBox {{
                background-color: {t['card_bg']};
                border: 1px solid {t['border']};
                border-radius: 10px;
            }}
            QMessageBox QLabel {{
                color: {t['text']};
                font-size: 13px;
                font-weight: 600;
                background: transparent;
            }}
            QMessageBox QPushButton {{
                background-color: {t['pill_bg']};
                color: {t['text']};
                border: 1px solid {t['border']};
                border-radius: 6px;
                font-size: 13px;
                font-weight: 700;
                padding: 6px 16px;
                min-width: 65px;
            }}
            QMessageBox QPushButton:hover {{
                background-color: {t['pill_hover']};
            }}
            QMessageBox QPushButton:focus {{
                border: 1px solid {t['accent']};
            }}

            QProgressBar {{
                background-color: {t['pill_bg']};
                border: none;
                border-radius: 4px;
                text-align: center;
                color: transparent;
            }}
            QProgressBar::chunk {{
                background-color: {t['accent']};
                border-radius: 4px;
            }}
        """
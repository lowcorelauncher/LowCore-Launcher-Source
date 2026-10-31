# Lightweight, zero-overhead localization system for LowCore Launcher

TRANSLATIONS = {
    "en": {
        "tab_play": "Play",
        "tab_mods": "Mods Browser",
        "tab_settings": "Settings",
        "tab_console": "Console Log",
        "kill_mc": "Kill Minecraft",
        "active_inst": "Active Isolated Instance",
        "account": "Account",
        "ram_alloc": "Global High-Performance Memory Allocation",
        "play": "PLAY",
        "ready": "Ready to launch",
        "search_mods": "Search mods on Modrinth...",
        "search": "Search",
        "download_mod": "Download Selected Mod",
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
        "tab_mods": "متصفح المودات",
        "tab_settings": "الإعدادات",
        "tab_console": "سجل الأوامر",
        "kill_mc": "إغلاق اللعبة إجبارياً",
        "active_inst": "النسخة الحالية المعزولة",
        "account": "الحساب",
        "ram_alloc": "تخصيص الرام عالي الأداء",
        "play": "ابدأ اللعب",
        "ready": "جاهز للتشغيل",
        "search_mods": "ابحث عن المودات في Modrinth...",
        "search": "بحث",
        "download_mod": "تحميل المود المحدد",
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
        "tab_mods": "Mod-Browser",
        "tab_settings": "Einstellungen",
        "tab_console": "Konsole",
        "kill_mc": "Minecraft beenden",
        "active_inst": "Aktive Instanz",
        "account": "Konto",
        "ram_alloc": "Globale RAM-Zuweisung",
        "play": "SPIELEN",
        "ready": "Bereit zum Starten",
        "search_mods": "Suche nach Mods auf Modrinth...",
        "search": "Suchen",
        "download_mod": "Ausgewählte Mod herunterladen",
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
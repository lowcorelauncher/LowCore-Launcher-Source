import os
import sys
import json
import shutil
import zipfile
import platform
import tarfile
import requests

MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"
ADOPTIUM_LTS = (8, 11, 17, 21, 25)


class JavaManager:
    """
    Automatically detects the required Java major version for any Minecraft release
    and downloads portable OpenJDK runtimes from Adoptium API if missing.
    """

    _remote_cache = {}

    @staticmethod
    def _to_available(major: int) -> int:
        """Adoptium only ships LTS builds; round odd majors (e.g. 16) up to the next LTS."""
        for lts in ADOPTIUM_LTS:
            if major <= lts:
                return lts
        return major

    @staticmethod
    def _local_java_major(mc_version: str, base_dir: str, depth: int = 0):
        if not base_dir or depth > 3:
            return None
        path = os.path.join(base_dir, "versions", mc_version, f"{mc_version}.json")
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return None
        major = (data.get("javaVersion") or {}).get("majorVersion")
        if major:
            return int(major)
        parent = data.get("inheritsFrom")
        if parent:
            return JavaManager._local_java_major(parent, base_dir, depth + 1)
        return None

    @staticmethod
    def _remote_java_major(mc_version: str):
        if mc_version in JavaManager._remote_cache:
            return JavaManager._remote_cache[mc_version]
        major = None
        try:
            manifest = requests.get(MANIFEST_URL, timeout=10).json()
            entry = next((v for v in manifest.get("versions", []) if v.get("id") == mc_version), None)
            if entry:
                data = requests.get(entry["url"], timeout=10).json()
                major = (data.get("javaVersion") or {}).get("majorVersion")
                major = int(major) if major else None
        except Exception:
            major = None
        JavaManager._remote_cache[mc_version] = major
        return major

    @staticmethod
    def _fallback_java_major(mc_version: str) -> int:
        clean = mc_version.strip().lower()
        parts = clean.split(".")
        try:
            first = int(parts[0])
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
        except ValueError:
            return 21

        # New year-based versioning (26.x and later): best guess, the version JSON normally decides.
        if first >= 26:
            return 25
        # 1.20.5+ -> Java 21
        if (minor == 20 and patch >= 5) or minor >= 21:
            return 21
        # 1.17 - 1.20.4 -> Java 17 (1.17 asks for 16, 17 is compatible)
        if minor >= 17:
            return 17
        # 1.16.5 and older (1.12.2, 1.8.9, 1.7.10) -> Java 8
        return 8

    @staticmethod
    def get_required_java_version(mc_version: str, base_dir: str = None) -> int:
        """Reads javaVersion from the version JSON (local first, then Mojang); falls back to a table."""
        major = JavaManager._local_java_major(mc_version, base_dir)
        if major is None:
            major = JavaManager._remote_java_major(mc_version)
        if major is None:
            major = JavaManager._fallback_java_major(mc_version)
        return JavaManager._to_available(major)

    @staticmethod
    def ensure_java_runtime(mc_version: str, base_dir: str, status_cb=None) -> str:
        required_major = JavaManager.get_required_java_version(mc_version, base_dir)
        java_root = os.path.join(base_dir, "java", f"java-{required_major}")
        bin_dir = "bin"
        exe_name = "java.exe" if platform.system() == "Windows" else "java"

        # Check standard runtime directory structure
        for root, dirs, files in os.walk(java_root):
            if exe_name in files and os.path.basename(root) == bin_dir:
                return os.path.join(root, exe_name)

        if status_cb:
            status_cb(f"Downloading OpenJDK {required_major} runtime...", 0, 100)

        os.makedirs(java_root, exist_ok=True)
        os_name = "windows" if platform.system() == "Windows" else ("mac" if platform.system() == "Darwin" else "linux")
        arch = "x64" if platform.machine() in ["AMD64", "x86_64"] else "aarch64"

        # Adoptium Temurin API endpoint for automated binary download
        api_url = f"https://api.adoptium.net/v3/binary/latest/{required_major}/ga/{os_name}/{arch}/jdk/hotspot/normal/eclipse"

        archive_path = os.path.join(base_dir, "java", f"temp_jdk_{required_major}.zip" if os_name == "windows" else f"temp_jdk_{required_major}.tar.gz")

        res = requests.get(api_url, stream=True, timeout=30)
        res.raise_for_status()

        total_size = int(res.headers.get("content-length", 0))
        downloaded = 0

        with open(archive_path, "wb") as f:
            for chunk in res.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if status_cb and total_size > 0:
                        status_cb(f"Downloading Java {required_major}...", downloaded, total_size)

        if status_cb:
            status_cb(f"Extracting Java {required_major} runtime...", 0, 0)

        if zipfile.is_zipfile(archive_path):
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                zip_ref.extractall(java_root)
        elif tarfile.is_tarfile(archive_path):
            with tarfile.open(archive_path, "r:*") as tar_ref:
                try:
                    tar_ref.extractall(java_root, filter="data")
                except TypeError:  # Python without extraction filters
                    tar_ref.extractall(java_root)

        if os.path.exists(archive_path):
            os.remove(archive_path)

        for root, dirs, files in os.walk(java_root):
            if exe_name in files and os.path.basename(root) == bin_dir:
                target_exe = os.path.join(root, exe_name)
                if platform.system() != "Windows":
                    os.chmod(target_exe, 0o755)
                return target_exe

        # Fallback to system java binary if automatic unpack fails
        if status_cb:
            status_cb(f"Could not unpack Java {required_major}; falling back to system Java.", 0, 0)
        return "java"
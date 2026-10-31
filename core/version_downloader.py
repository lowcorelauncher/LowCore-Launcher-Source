import os
import sys
import json
import hashlib
import time
import platform
import zipfile
import shutil
import threading
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Callable, Optional, Tuple

MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest_v2.json"


class VersionDownloader:
    def __init__(self, game_dir: str, progress_callback: Optional[Callable[[str, int, int], None]] = None):
        self.game_dir = game_dir
        self.progress_callback = progress_callback
        self.os_name = self._resolve_os()
        self.arch_tag = self._resolve_arch()
        self.arch_bits = "64" if sys.maxsize > 2 ** 32 else "32"

        self.session = requests.Session()
        retries = Retry(
            total=5,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            raise_on_status=False
        )
        adapter = HTTPAdapter(max_retries=retries, pool_connections=16, pool_maxsize=16)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # Verification cache: a file is SHA-1 hashed once; later launches trust (size, mtime).
        self._vcache_path = os.path.join(game_dir, ".lowcore_verified.json")
        self._vcache = None
        self._vdirty = False
        self._vlock = threading.Lock()
        self._done = set()  # versions already installed/verified during this launch

    @staticmethod
    def _resolve_os() -> str:
        sys_name = platform.system().lower()
        if "windows" in sys_name:
            return "windows"
        elif "darwin" in sys_name:
            return "osx"
        return "linux"

    @staticmethod
    def _resolve_arch() -> str:
        machine = platform.machine().lower()
        if machine in ("arm64", "aarch64"):
            return "arm64"
        if machine in ("x86", "i386", "i686"):
            return "x86"
        return "x86_64"

    def _rules_allow(self, rules: Optional[list]) -> bool:
        if not rules:
            return True
        allowed = False
        for rule in rules:
            if "features" in rule:
                continue
            cond = rule.get("os")
            matches = True
            if cond:
                if cond.get("name") and cond["name"] != self.os_name:
                    matches = False
                if cond.get("arch") and cond["arch"] != self.arch_tag:
                    matches = False
            if matches:
                allowed = rule.get("action") == "allow"
        return allowed

    def fetch_manifest(self) -> Dict[str, Any]:
        res = self.session.get(MANIFEST_URL, timeout=15)
        res.raise_for_status()
        return res.json()

    def get_version_json(self, version_id: str) -> Dict[str, Any]:
        version_dir = os.path.join(self.game_dir, "versions", version_id)
        local_json = os.path.join(version_dir, f"{version_id}.json")

        if os.path.exists(local_json):
            try:
                with open(local_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if data:
                        return data
            except Exception:
                pass

        manifest = self.fetch_manifest()
        target_entry = next((v for v in manifest["versions"] if v["id"] == version_id), None)

        if not target_entry:
            raise ValueError(f"Minecraft version '{version_id}' was not found in Mojang's version manifest.")

        os.makedirs(version_dir, exist_ok=True)
        res = self.session.get(target_entry["url"], timeout=20)
        res.raise_for_status()
        v_data = res.json()

        with open(local_json, "w", encoding="utf-8") as f:
            json.dump(v_data, f, indent=2)

        return v_data

    @staticmethod
    def verify_sha1(file_path: str, expected_sha1: str) -> bool:
        if not os.path.exists(file_path):
            return False
        if os.path.getsize(file_path) == 0:
            return False
        if not expected_sha1:
            return True
        h = hashlib.sha1()
        with open(file_path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return h.hexdigest().lower() == expected_sha1.lower()

    # ---- verification cache -------------------------------------------------
    def _vc_load(self):
        if self._vcache is not None:
            return
        try:
            with open(self._vcache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._vcache = data if isinstance(data, dict) else {}
        except Exception:
            self._vcache = {}

    def _vc_hit(self, path: str, sha1: str) -> bool:
        with self._vlock:
            self._vc_load()
            entry = self._vcache.get(path)
        if not entry:
            return False
        try:
            st = os.stat(path)
        except OSError:
            return False
        return entry == [st.st_size, st.st_mtime_ns, sha1.lower()]

    def _vc_record(self, path: str, sha1: str):
        if not sha1:
            return
        try:
            st = os.stat(path)
        except OSError:
            return
        with self._vlock:
            self._vc_load()
            self._vcache[path] = [st.st_size, st.st_mtime_ns, sha1.lower()]
            self._vdirty = True

    def _save_vcache(self):
        with self._vlock:
            if not self._vdirty or self._vcache is None:
                return
            tmp = self._vcache_path + ".tmp"
            try:
                os.makedirs(os.path.dirname(self._vcache_path), exist_ok=True)
                with open(tmp, "w", encoding="utf-8") as f:
                    json.dump(self._vcache, f)
                os.replace(tmp, self._vcache_path)
                self._vdirty = False
            except Exception:
                pass

    def download_file(self, url: str, dest_path: str, sha1: str = "", max_attempts: int = 4) -> bool:
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
            if not sha1 or self._vc_hit(dest_path, sha1):
                return True
            if self.verify_sha1(dest_path, sha1):
                self._vc_record(dest_path, sha1)
                return True

        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        temp_path = f"{dest_path}.tmp"

        for attempt in range(max_attempts):
            try:
                res = self.session.get(url, stream=True, timeout=25)
                res.raise_for_status()
                with open(temp_path, "wb") as f:
                    for chunk in res.iter_content(chunk_size=32768):
                        if chunk:
                            f.write(chunk)

                if sha1 and not self.verify_sha1(temp_path, sha1):
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    continue

                os.replace(temp_path, dest_path)
                self._vc_record(dest_path, sha1)
                return True
            except Exception:
                if os.path.exists(temp_path):
                    try:
                        os.remove(temp_path)
                    except OSError:
                        pass
                time.sleep(1 + attempt)

        return False

    @staticmethod
    def maven_to_path(name: str) -> str:
        ext = "jar"
        if "@" in name:
            name, ext = name.split("@", 1)
        parts = name.split(":")
        group = parts[0].replace(".", os.sep)
        artifact = parts[1]
        version = parts[2]
        classifier = f"-{parts[3]}" if len(parts) > 3 else ""
        return os.path.join(group, artifact, version, f"{artifact}-{version}{classifier}.{ext}")

    def _plan_libraries(self, v_data: Dict[str, Any]) -> Tuple[List[tuple], List[tuple]]:
        tasks: Dict[str, tuple] = {}
        natives: List[tuple] = []

        for lib in v_data.get("libraries", []):
            if not self._rules_allow(lib.get("rules")):
                continue

            name = lib.get("name")
            downloads = lib.get("downloads", {})
            artifact = downloads.get("artifact")

            if artifact:
                rel_path = (artifact.get("path") or "").replace("/", os.sep)
                if not rel_path and name:
                    rel_path = self.maven_to_path(name)
                dest = os.path.join(self.game_dir, "libraries", rel_path)
                tasks[dest] = (artifact.get("url") or "", dest, artifact.get("sha1", ""))
            elif name and not downloads:
                base_url = lib.get("url", "https://maven.fabricmc.net/")
                rel_path = self.maven_to_path(name)
                url = f"{base_url.rstrip('/')}/{rel_path.replace(os.sep, '/')}"
                dest = os.path.join(self.game_dir, "libraries", rel_path)
                tasks[dest] = (url, dest, "")

            native_key = (lib.get("natives") or {}).get(self.os_name)
            if native_key:
                classifier = native_key.replace("${arch}", self.arch_bits)
                native = (downloads.get("classifiers") or {}).get(classifier)
                if native:
                    rel_path = (native.get("path") or "").replace("/", os.sep)
                    dest = os.path.join(self.game_dir, "libraries", rel_path)
                    tasks[dest] = (native.get("url") or "", dest, native.get("sha1", ""))
                    natives.append((dest, (lib.get("extract") or {}).get("exclude", [])))

        return list(tasks.values()), natives

    @staticmethod
    def _extract_natives(native_jars: List[tuple], natives_dir: str):
        os.makedirs(natives_dir, exist_ok=True)
        root = os.path.realpath(natives_dir)
        for jar_path, excludes in native_jars:
            if not os.path.exists(jar_path):
                continue
            try:
                with zipfile.ZipFile(jar_path, "r") as z:
                    for member in z.namelist():
                        if member.endswith("/") or any(member.startswith(ex) for ex in excludes):
                            continue
                        target = os.path.realpath(os.path.join(natives_dir, member))
                        if not target.startswith(root + os.sep):
                            continue
                        os.makedirs(os.path.dirname(target), exist_ok=True)
                        if not os.path.exists(target):
                            with z.open(member) as src, open(target, "wb") as out:
                                out.write(src.read())
            except zipfile.BadZipFile:
                continue

    def install_version(self, version_id: str):
        # Modded profiles inherit from a vanilla version that was just installed:
        # don't walk the same libraries/assets twice in one launch.
        if version_id in self._done:
            return
        try:
            self._install_version_impl(version_id)
            self._done.add(version_id)
        finally:
            self._save_vcache()

    def _install_version_impl(self, version_id: str):
        v_data = self.get_version_json(version_id)
        version_dir = os.path.join(self.game_dir, "versions", version_id)

        parent_natives: List[tuple] = []
        inherits_from = v_data.get("inheritsFrom")
        if inherits_from:
            self.install_version(inherits_from)
            _, parent_natives = self._plan_libraries(self.get_version_json(inherits_from))

            parent_jar = os.path.join(self.game_dir, "versions", inherits_from, f"{inherits_from}.jar")
            target_jar = os.path.join(version_dir, f"{version_id}.jar")
            if os.path.exists(parent_jar) and not os.path.exists(target_jar):
                try:
                    shutil.copy2(parent_jar, target_jar)
                except Exception:
                    pass

        client_info = v_data.get("downloads", {}).get("client", {})
        if client_info:
            client_jar = os.path.join(version_dir, f"{version_id}.jar")
            if not self.download_file(client_info.get("url"), client_jar, client_info.get("sha1", "")):
                raise ConnectionError(f"Failed to download client.jar for {version_id}.")

        tasks, natives = self._plan_libraries(v_data)
        downloadable = [t for t in tasks if t[0]]
        total = len(downloadable)
        completed = 0
        failed: List[str] = []

        with ThreadPoolExecutor(max_workers=6) as executor:
            future_to_task = {
                executor.submit(self.download_file, url, dest, sha): dest
                for url, dest, sha in downloadable
            }
            for future in as_completed(future_to_task):
                completed += 1
                try:
                    ok = future.result()
                except Exception:
                    ok = False
                if not ok:
                    failed.append(os.path.basename(future_to_task[future]))
                if self.progress_callback and total > 0:
                    self.progress_callback(f"Downloading Libraries ({completed}/{total})", completed, total)

        if failed:
            shown = ", ".join(failed[:3]) + ("..." if len(failed) > 3 else "")
            raise ConnectionError(f"Failed to download {len(failed)} libraries for {version_id}: {shown}")

        all_natives = natives + parent_natives
        if all_natives:
            self._extract_natives(all_natives, os.path.join(version_dir, "natives"))

        asset_index_info = v_data.get("assetIndex")
        if asset_index_info:
            idx_id = asset_index_info.get("id")
            idx_url = asset_index_info.get("url")
            idx_path = os.path.join(self.game_dir, "assets", "indexes", f"{idx_id}.json")

            if self.download_file(idx_url, idx_path, asset_index_info.get("sha1", "")):
                with open(idx_path, "r", encoding="utf-8") as f:
                    index_data = json.load(f)

                objects = index_data.get("objects", {})
                obj_tasks = []
                for _, info in objects.items():
                    h = info["hash"]
                    prefix = h[:2]
                    obj_url = f"https://resources.download.minecraft.net/{prefix}/{h}"
                    obj_dest = os.path.join(self.game_dir, "assets", "objects", prefix, h)
                    expected_size = info.get("size")
                    if os.path.exists(obj_dest) and os.path.getsize(obj_dest) > 0 and (expected_size is None or os.path.getsize(obj_dest) == expected_size):
                        continue
                    obj_tasks.append((obj_url, obj_dest, h))

                if obj_tasks:
                    obj_total = len(obj_tasks)
                    obj_done = 0
                    obj_failed = 0
                    with ThreadPoolExecutor(max_workers=8) as executor:
                        future_to_obj = {
                            executor.submit(self.download_file, url, dest, sha): dest
                            for url, dest, sha in obj_tasks
                        }
                        for future in as_completed(future_to_obj):
                            obj_done += 1
                            try:
                                ok = future.result()
                            except Exception:
                                ok = False
                            if not ok:
                                obj_failed += 1
                            if self.progress_callback and obj_done % 25 == 0:
                                self.progress_callback(f"Downloading Assets ({obj_done}/{obj_total})", obj_done, obj_total)

                    if self.progress_callback:
                        if obj_failed:
                            self.progress_callback(f"Warning: {obj_failed} assets failed to download", obj_total, obj_total)
                        else:
                            self.progress_callback(f"Downloading Assets ({obj_total}/{obj_total})", obj_total, obj_total)
import os
import json
import uuid
import time
import shutil
import subprocess
import xml.etree.ElementTree as ET
import requests

from core.java_manager import JavaManager

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
INSTALL_MARKER = ".lowcore_installed"


class LoaderError(RuntimeError):
    """Raised when a mod loader cannot be prepared (instead of silently launching vanilla)."""


class InstanceManager:
    def __init__(self, base_dir: str):
        self.base_dir = base_dir
        self.instances_dir = os.path.join(base_dir, "instances")
        os.makedirs(self.instances_dir, exist_ok=True)

    def list_instances(self) -> list:
        instances = []
        if not os.path.exists(self.instances_dir):
            return instances

        for item in os.listdir(self.instances_dir):
            inst_path = os.path.join(self.instances_dir, item)
            config_file = os.path.join(inst_path, "instance.json")
            if os.path.isdir(inst_path) and os.path.exists(config_file):
                try:
                    with open(config_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        data["path"] = inst_path
                        instances.append(data)
                except Exception:
                    continue
        return instances

    def create_instance(self, name: str, version: str, loader: str = "Vanilla") -> dict:
        folder_name = "".join([c for c in name if c.isalnum() or c in (" ", "-", "_")]).strip()
        folder_name = folder_name.replace(" ", "_")
        inst_path = os.path.join(self.instances_dir, folder_name)

        counter = 1
        orig_name = folder_name
        while os.path.exists(inst_path):
            folder_name = f"{orig_name}_{counter}"
            inst_path = os.path.join(self.instances_dir, folder_name)
            counter += 1

        os.makedirs(inst_path, exist_ok=True)
        os.makedirs(os.path.join(inst_path, "mods"), exist_ok=True)
        os.makedirs(os.path.join(inst_path, "resourcepacks"), exist_ok=True)
        os.makedirs(os.path.join(inst_path, "shaderpacks"), exist_ok=True)

        config_data = {
            "name": name,
            "version": version,
            "loader": loader,
            "path": inst_path
        }

        with open(os.path.join(inst_path, "instance.json"), "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4)

        return config_data

    def delete_instance(self, inst_path: str) -> bool:
        if os.path.exists(inst_path):
            try:
                shutil.rmtree(inst_path)
                return True
            except Exception:
                return False
        return False

    # ------------------------------------------------------------------ loaders

    def prepare_instance_loader(self, inst_path: str, mc_version: str, loader: str, status_cb=None, java_bin: str = None) -> str:
        """
        Returns the version id to launch. Raises LoaderError if the requested loader
        cannot be prepared, so the user sees the real reason instead of a vanilla launch.
        """
        loader_lower = loader.strip().lower()

        if loader_lower == "vanilla":
            return mc_version
        if loader_lower == "fabric":
            return self._prepare_fabric(mc_version, status_cb)
        if loader_lower == "quilt":
            return self._prepare_quilt(mc_version, status_cb)
        if loader_lower in ("neoforge", "neo-forge"):
            return self._prepare_neoforge(mc_version, status_cb, java_bin)
        if loader_lower == "forge":
            return self._prepare_forge(mc_version, status_cb, java_bin)

        raise LoaderError(f"Unknown mod loader '{loader}'.")

    def _write_profile(self, profile_id: str, profile_data: dict):
        versions_dir = os.path.join(self.base_dir, "versions", profile_id)
        os.makedirs(versions_dir, exist_ok=True)
        with open(os.path.join(versions_dir, f"{profile_id}.json"), "w", encoding="utf-8") as f:
            json.dump(profile_data, f, indent=4)

    LOADER_CACHE_TTL = 24 * 3600  # re-check for a newer loader once a day, not on every launch

    def _loader_cache_file(self) -> str:
        return os.path.join(self.base_dir, "loader_cache.json")

    def _loader_cache_get(self, key: str):
        try:
            with open(self._loader_cache_file(), "r", encoding="utf-8") as f:
                entry = (json.load(f) or {}).get(key)
        except Exception:
            return None
        if not entry:
            return None
        pid = entry.get("profile_id")
        if pid and os.path.exists(os.path.join(self.base_dir, "versions", pid, f"{pid}.json")):
            return entry
        return None

    def _loader_cache_put(self, key: str, profile_id: str):
        try:
            try:
                with open(self._loader_cache_file(), "r", encoding="utf-8") as f:
                    data = json.load(f) or {}
            except Exception:
                data = {}
            data[key] = {"profile_id": profile_id, "time": time.time()}
            tmp = self._loader_cache_file() + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, self._loader_cache_file())
        except Exception:
            pass

    def _prepare_meta_loader(self, label: str, meta_base: str, id_prefix: str, mc_version: str, status_cb=None) -> str:
        cache_key = f"{label}:{mc_version}"
        cached = self._loader_cache_get(cache_key)
        if cached and time.time() - cached.get("time", 0) < self.LOADER_CACHE_TTL:
            return cached["profile_id"]  # no network round-trips on repeat launches

        try:
            if status_cb:
                status_cb(f"Fetching {label} Loader metadata...", 0, 100)
            res = requests.get(f"{meta_base}/versions/loader/{mc_version}", timeout=10)
            res.raise_for_status()
            data = res.json()
            if not data:
                raise LoaderError(f"{label} does not support Minecraft {mc_version}.")

            entry = next((d for d in data if d.get("loader", {}).get("stable")), data[0])
            loader_version = entry["loader"]["version"]
            profile_id = f"{id_prefix}-loader-{loader_version}-{mc_version}"

            profile_url = f"{meta_base}/versions/loader/{mc_version}/{loader_version}/profile/json"
            prof_res = requests.get(profile_url, timeout=10)
            prof_res.raise_for_status()
            self._write_profile(profile_id, prof_res.json())
            self._loader_cache_put(cache_key, profile_id)
            return profile_id
        except LoaderError:
            raise
        except Exception as e:
            if cached:  # offline / metadata server down: the profile we already have still works
                if status_cb:
                    status_cb(f"{label} metadata unreachable, using the saved profile", 0, 0)
                return cached["profile_id"]
            raise LoaderError(f"{label} setup failed for Minecraft {mc_version}: {e}") from e

    def _prepare_fabric(self, mc_version: str, status_cb=None) -> str:
        return self._prepare_meta_loader("Fabric", "https://meta.fabricmc.net/v2", "fabric", mc_version, status_cb)

    def _prepare_quilt(self, mc_version: str, status_cb=None) -> str:
        return self._prepare_meta_loader("Quilt", "https://meta.quiltmc.org/v3", "quilt", mc_version, status_cb)

    # ---- Forge / NeoForge: run the official installer headlessly ----

    def _ensure_launcher_profiles(self):
        path = os.path.join(self.base_dir, "launcher_profiles.json")
        if os.path.exists(path):
            return
        os.makedirs(self.base_dir, exist_ok=True)
        stub = {
            "profiles": {},
            "selectedProfile": "",
            "clientToken": str(uuid.uuid4()),
            "authenticationDatabase": {},
            "launcherVersion": {"name": "lowcore", "format": 21, "profilesFormat": 2},
            "settings": {}
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(stub, f, indent=2)

    def _is_installed(self, profile_id: str) -> bool:
        vdir = os.path.join(self.base_dir, "versions", profile_id)
        return os.path.exists(os.path.join(vdir, f"{profile_id}.json")) and os.path.exists(os.path.join(vdir, INSTALL_MARKER))

    def _list_version_ids(self) -> set:
        vdir = os.path.join(self.base_dir, "versions")
        return set(os.listdir(vdir)) if os.path.isdir(vdir) else set()

    def _run_installer(self, label: str, installer_url: str, expected_id: str, id_token: str, mc_version: str, status_cb=None, java_bin: str = None) -> str:
        if self._is_installed(expected_id):
            return expected_id

        installers_dir = os.path.join(self.base_dir, "installers")
        os.makedirs(installers_dir, exist_ok=True)
        jar_path = os.path.join(installers_dir, f"{label.lower()}-{expected_id}-installer.jar")

        try:
            if status_cb:
                status_cb(f"Downloading {label} installer...", 0, 100)
            res = requests.get(installer_url, stream=True, timeout=30)
            res.raise_for_status()
            with open(jar_path, "wb") as f:
                for chunk in res.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)

            self._ensure_launcher_profiles()
            java = java_bin or JavaManager.ensure_java_runtime(mc_version, self.base_dir, status_cb)
            before = self._list_version_ids()

            if status_cb:
                status_cb(f"Installing {label} (this can take a few minutes)...", 0, 0)
            proc = subprocess.run(
                [java, "-jar", jar_path, "--installClient", self.base_dir],
                stdin=subprocess.DEVNULL, capture_output=True, text=True, encoding="utf-8", errors="replace",
                timeout=1200, cwd=installers_dir, creationflags=NO_WINDOW
            )
            if proc.returncode != 0:
                tail = "\n".join((proc.stdout + "\n" + proc.stderr).strip().splitlines()[-12:])
                raise LoaderError(f"{label} installer failed (exit {proc.returncode}):\n{tail}")

            created = [
                v for v in self._list_version_ids() - before
                if id_token in v.lower() and os.path.exists(os.path.join(self.base_dir, "versions", v, f"{v}.json"))
            ]
            profile_id = expected_id if os.path.exists(os.path.join(self.base_dir, "versions", expected_id, f"{expected_id}.json")) else (created[0] if created else None)
            if not profile_id:
                raise LoaderError(f"{label} installer finished but no version profile was created.")

            with open(os.path.join(self.base_dir, "versions", profile_id, INSTALL_MARKER), "w", encoding="utf-8") as f:
                f.write("ok")
            return profile_id
        except LoaderError:
            raise
        except subprocess.TimeoutExpired as e:
            raise LoaderError(f"{label} installer timed out.") from e
        except Exception as e:
            raise LoaderError(f"{label} setup failed for Minecraft {mc_version}: {e}") from e
        finally:
            if os.path.exists(jar_path):
                try:
                    os.remove(jar_path)
                except OSError:
                    pass

    def _prepare_neoforge(self, mc_version: str, status_cb=None, java_bin: str = None) -> str:
        if status_cb:
            status_cb("Resolving NeoForge release...", 0, 100)

        parts = mc_version.strip().split(".")
        # NeoForge drops the leading '1.' (1.21.1 -> 21.1.x, 1.21 -> 21.0.x). Trailing '.' avoids 21.1 matching 21.10.
        if len(parts) >= 2 and parts[0] == "1":
            patch = parts[2] if len(parts) > 2 else "0"
            prefix = f"{parts[1]}.{patch}."
        else:
            prefix = mc_version.strip() + "."

        try:
            res = requests.get("https://maven.neoforged.net/releases/net/neoforged/neoforge/maven-metadata.xml", timeout=10)
            res.raise_for_status()
            root = ET.fromstring(res.content)
            versioning = root.find("versioning")
            versions = [v.text for v in versioning.find("versions").findall("version") if v.text]
        except Exception as e:
            raise LoaderError(f"Could not read NeoForge metadata: {e}") from e

        matching = [v for v in versions if v.startswith(prefix)]
        stable = [v for v in matching if "-beta" not in v and "-alpha" not in v]
        chosen = (stable or matching)
        if not chosen:
            raise LoaderError(f"No NeoForge build found for Minecraft {mc_version}.")

        ver = chosen[-1]
        url = f"https://maven.neoforged.net/releases/net/neoforged/neoforge/{ver}/neoforge-{ver}-installer.jar"
        return self._run_installer("NeoForge", url, f"neoforge-{ver}", "neoforge", mc_version, status_cb, java_bin)

    def _prepare_forge(self, mc_version: str, status_cb=None, java_bin: str = None) -> str:
        if status_cb:
            status_cb("Checking Forge metadata...", 0, 100)
        try:
            res = requests.get("https://files.minecraftforge.net/net/minecraftforge/forge/promotions_slim.json", timeout=10)
            res.raise_for_status()
            promos = res.json().get("promos", {})
        except Exception as e:
            raise LoaderError(f"Could not read Forge metadata: {e}") from e

        build = promos.get(f"{mc_version}-recommended") or promos.get(f"{mc_version}-latest")
        if not build:
            raise LoaderError(f"No Forge build found for Minecraft {mc_version}.")

        full = f"{mc_version}-{build}"
        url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{full}/forge-{full}-installer.jar"
        return self._run_installer("Forge", url, f"{mc_version}-forge-{build}", "forge", mc_version, status_cb, java_bin)
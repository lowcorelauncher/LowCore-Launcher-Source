import os
import json
import hashlib
import requests

MODRINTH_API = "https://api.modrinth.com/v2"
USER_AGENT = "LowCoreLauncher/1.0 (Minecraft Client Manager; support@lowcore.client)"

# "Loaders" Modrinth uses for resource packs / shader packs / datapacks (they are not mod loaders).
PACK_LOADERS = {"minecraft", "iris", "optifine", "canvas", "vanilla", "datapack"}
_TYPE_RANK = {"release": 0, "beta": 1, "alpha": 2}


class ModrinthService:
    @staticmethod
    def _headers() -> dict:
        return {
            "User-Agent": USER_AGENT
        }

    @staticmethod
    def search_content(query: str, version: str = None, loader: str = None, project_type: str = "mod") -> list:
        """
        Searches Modrinth projects matching game version, loader, and project type.
        """
        facets = []
        if project_type:
            facets.append([f"project_type:{project_type}"])
        if version:
            facets.append([f"versions:{version}"])
        if loader and project_type == "mod":
            # Modrinth categorizes loaders under categories
            facets.append([f"categories:{loader.lower()}"])

        params = {
            "query": query,
            "limit": 25,
            "index": "relevance"
        }
        if facets:
            params["facets"] = json.dumps(facets)

        try:
            resp = requests.get(
                f"{MODRINTH_API}/search",
                params=params,
                headers=ModrinthService._headers(),
                timeout=10
            )
            if resp.status_code == 200:
                return resp.json().get("hits", [])
        except Exception:
            pass
        return []

    @staticmethod
    def _fetch_versions(project_id: str, params: dict) -> list:
        res = requests.get(
            f"{MODRINTH_API}/project/{project_id}/version",
            params=params,
            headers=ModrinthService._headers(),
            timeout=10
        )
        res.raise_for_status()
        return res.json()

    @staticmethod
    def _prefer_release(versions: list) -> dict:
        # API returns newest first; a stable sort keeps that order inside each release channel.
        return sorted(versions, key=lambda v: _TYPE_RANK.get(v.get("version_type"), 3))[0]

    @staticmethod
    def get_best_version(project_id: str, version: str, loader: str) -> dict:
        """
        Returns the newest compatible version for the exact Minecraft version + loader.
        It never falls back to a different Minecraft version, so a mod built for another
        game version (or another loader) is never installed.
        """
        params = {}
        if version:
            params["game_versions"] = json.dumps([version])
        if loader:
            params["loaders"] = json.dumps([loader.lower()])

        versions = ModrinthService._fetch_versions(project_id, params)
        if versions:
            return ModrinthService._prefer_release(versions)

        # Resource packs / shaders are tagged with "minecraft", "iris", ... instead of a mod loader,
        # so retry on game version only, but accept ONLY pack-type entries (never a mod for another loader).
        if version:
            by_version = ModrinthService._fetch_versions(project_id, {"game_versions": json.dumps([version])})
            packs = [
                v for v in by_version
                if v.get("loaders") and {l.lower() for l in v["loaders"]} <= PACK_LOADERS
            ]
            if packs:
                return ModrinthService._prefer_release(packs)

        raise RuntimeError(f"No compatible release found for {loader} {version} on project '{project_id}'.")

    @staticmethod
    def _download_file(url: str, out_path: str, sha1: str = ""):
        tmp_path = out_path + ".part"
        resp = requests.get(url, headers=ModrinthService._headers(), stream=True, timeout=25)
        resp.raise_for_status()
        digest = hashlib.sha1()
        try:
            with open(tmp_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=16384):
                    if chunk:
                        f.write(chunk)
                        digest.update(chunk)
            if sha1 and digest.hexdigest().lower() != sha1.lower():
                raise RuntimeError(f"Checksum mismatch for {os.path.basename(out_path)}")
            os.replace(tmp_path, out_path)
        finally:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass

    @staticmethod
    def download_with_dependencies(project_id: str, version: str, loader: str, target_dir: str, downloaded_set: set = None, progress_cb=None) -> list:
        """
        Recursively resolves declared 'required' dependencies and downloads all needed JARs.
        Returns a list of downloaded filenames. A failing dependency is reported through
        progress_cb and skipped; a failure on the requested project itself raises.
        """
        if downloaded_set is None:
            downloaded_set = set()

        if project_id in downloaded_set:
            return []
        downloaded_set.add(project_id)  # mark early so dependency cycles cannot recurse forever

        os.makedirs(target_dir, exist_ok=True)
        ver_data = ModrinthService.get_best_version(project_id, version, loader)

        files = ver_data.get("files", [])
        if not files:
            raise RuntimeError(f"Version object has no downloadable files for project '{project_id}'.")

        primary_file = next((f for f in files if f.get("primary")), files[0])
        file_url = primary_file["url"]
        file_name = os.path.basename(primary_file["filename"])
        file_sha1 = (primary_file.get("hashes") or {}).get("sha1", "")
        out_path = os.path.join(target_dir, file_name)

        installed_files = [file_name]

        already_ok = os.path.exists(out_path) and os.path.getsize(out_path) > 0
        if not already_ok:
            if progress_cb:
                progress_cb(f"Downloading {file_name}...")
            ModrinthService._download_file(file_url, out_path, file_sha1)

        for dep in ver_data.get("dependencies", []):
            if dep.get("dependency_type") != "required":
                continue

            dep_proj_id = dep.get("project_id")
            dep_ver_id = dep.get("version_id")

            try:
                if not dep_proj_id and dep_ver_id:
                    v_res = requests.get(
                        f"{MODRINTH_API}/version/{dep_ver_id}",
                        headers=ModrinthService._headers(),
                        timeout=10
                    )
                    v_res.raise_for_status()
                    dep_proj_id = v_res.json().get("project_id")

                if dep_proj_id and dep_proj_id not in downloaded_set:
                    installed_files.extend(
                        ModrinthService.download_with_dependencies(
                            dep_proj_id, version, loader, target_dir, downloaded_set, progress_cb
                        )
                    )
            except Exception as e:
                if progress_cb:
                    progress_cb(f"Skipped dependency {dep_proj_id or dep_ver_id}: {e}")

        return list(dict.fromkeys(installed_files))

    # Backwards-compatible name used by optimization.py
    download_mod_with_dependencies = download_with_dependencies
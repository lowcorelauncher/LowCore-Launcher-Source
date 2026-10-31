"""Reads what is REALLY inside a mod jar (Fabric / Quilt / Forge / NeoForge) - no network needed."""
import os
import re
import json
import zipfile
from collections import Counter
from typing import Dict, List, Optional, Tuple

_VERSION_TOKEN = re.compile(r"\d+\.\d+(?:\.\d+)?")


def _first_version(text: str) -> Optional[str]:
    m = _VERSION_TOKEN.search(text or "")
    return m.group(0) if m else None


def read_mod_info(jar_path: str) -> Optional[dict]:
    """{"loader": "fabric"|"quilt"|"forge"|"neoforge", "id": str, "mc_range": str|None} or None."""
    try:
        with zipfile.ZipFile(jar_path) as z:
            names = set(z.namelist())

            if "fabric.mod.json" in names:
                data = json.loads(z.read("fabric.mod.json").decode("utf-8", "replace"))
                dep = (data.get("depends") or {}).get("minecraft")
                if isinstance(dep, list):
                    dep = " ".join(str(x) for x in dep)
                return {"loader": "fabric", "id": data.get("id"), "mc_range": dep}

            if "quilt.mod.json" in names:
                data = json.loads(z.read("quilt.mod.json").decode("utf-8", "replace"))
                ql = data.get("quilt_loader") or {}
                mc_range = None
                deps = ql.get("depends") or []
                if isinstance(deps, dict):
                    deps = [dict(id=k, versions=v) for k, v in deps.items()]
                for d in deps:
                    if isinstance(d, dict) and d.get("id") == "minecraft":
                        v = d.get("versions")
                        mc_range = " ".join(v) if isinstance(v, list) else (json.dumps(v) if isinstance(v, dict) else str(v or ""))
                return {"loader": "quilt", "id": ql.get("id"), "mc_range": mc_range}

            for toml, loader in (("META-INF/neoforge.mods.toml", "neoforge"), ("META-INF/mods.toml", "forge")):
                if toml in names:
                    text = z.read(toml).decode("utf-8", "replace")
                    cut = text.find("[[dependencies")  # dependency tables also contain modId lines
                    head = text if cut < 0 else text[:cut]
                    ids = re.findall(r"""^\s*modId\s*=\s*["']([^"']+)["']""", head, re.M)
                    rng = re.search(r"""modId\s*=\s*["']minecraft["'][^\[]*?versionRange\s*=\s*["']([^"']+)["']""", text)
                    return {"loader": loader, "id": ids[0] if ids else None, "mc_range": rng.group(1) if rng else None}
    except Exception:
        return None
    return None


def read_mod_ids(jar_path: str) -> List[str]:
    info = read_mod_info(jar_path)
    return [info["id"]] if info and info.get("id") else []


def scan_mod_ids(mods_dir: str) -> Dict[str, List[str]]:
    result: Dict[str, List[str]] = {}
    if not os.path.isdir(mods_dir):
        return result
    for fn in os.listdir(mods_dir):
        if fn.endswith(".jar"):
            result[fn] = read_mod_ids(os.path.join(mods_dir, fn))
    return result


def disable_duplicate_mods(mods_dir: str) -> List[Tuple[str, str]]:
    """
    Two jars with the same mod id make Fabric/Forge refuse to start. Keep the newest file of each
    id and rename the others to *.jar.disabled. Returns [(disabled_file, kept_file), ...].
    """
    by_id: Dict[str, List[str]] = {}
    for fn, ids in scan_mod_ids(mods_dir).items():
        if ids:
            by_id.setdefault(ids[0], []).append(fn)

    disabled = []
    for files in by_id.values():
        if len(files) < 2:
            continue
        files.sort(key=lambda f: os.path.getmtime(os.path.join(mods_dir, f)), reverse=True)
        keep = files[0]
        for old in files[1:]:
            src = os.path.join(mods_dir, old)
            dst = src + ".disabled"
            try:
                if os.path.exists(dst):
                    os.remove(dst)
                os.replace(src, dst)
                disabled.append((old, keep))
            except OSError:
                pass
    return disabled


def guess_loader_and_version(mods_dir: str, limit: int = 80) -> Tuple[Optional[str], Optional[str]]:
    """
    Best guess of (loader, minecraft version) from the mods folder: the loader most jars are built for,
    and the Minecraft version most of them ask for. Only a GUESS - callers should let the user confirm.
    """
    if not os.path.isdir(mods_dir):
        return None, None
    loaders: Counter = Counter()
    versions: Counter = Counter()
    jars = [f for f in os.listdir(mods_dir) if f.endswith(".jar")][:limit]
    for fn in jars:
        info = read_mod_info(os.path.join(mods_dir, fn))
        if not info:
            continue
        loaders[info["loader"]] += 1
        v = _first_version(info.get("mc_range") or "")
        if v:
            versions[v] += 1

    loader = None
    if loaders:
        # Quilt runs Fabric mods, so a mixed folder is far more likely a Fabric one
        loader = "neoforge" if loaders["neoforge"] and loaders["neoforge"] >= loaders["forge"] else None
        if loader is None:
            loader = max(loaders, key=lambda k: (loaders[k], k == "fabric"))
    version = None
    if versions:
        version = max(versions, key=lambda k: (versions[k], tuple(int(x) for x in k.split("."))))
    return loader, version
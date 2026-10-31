"""
Bring instances over from other launchers. Nothing here touches the original files: everything is COPIED.

Supported: official Minecraft Launcher (+ TLauncher / SKLauncher profiles), Prism / PolyMC / MultiMC,
CurseForge app, Modrinth App, ATLauncher, GDLauncher - plus "any folder" with a best-effort guess.
"""
import os
import re
import json
import time
import shutil
import sqlite3
import tempfile
from typing import Callable, Dict, List, Optional, Set, Tuple

from core.modinfo import guess_loader_and_version

LOADER_NAMES = {"fabric": "Fabric", "quilt": "Quilt", "forge": "Forge", "neoforge": "NeoForge",
                "neo-forge": "NeoForge", "vanilla": "Vanilla"}

_MC_RELEASE = re.compile(r"^\d+\.\d+(?:\.\d+)?$")
_MC_SNAPSHOT = re.compile(r"^\d{2}w\d{2}[a-z]$")
_MC_PRE = re.compile(r"^\d+\.\d+(?:\.\d+)?-(?:pre|rc)\d+$")
_MC_AT_END = re.compile(r"(\d+\.\d+(?:\.\d+)?(?:-(?:pre|rc)\d+)?|\d{2}w\d{2}[a-z])$")

# Things that belong to the OTHER launcher / are rebuilt by LowCore: never copied.
EXCLUDE_TOP = {
    "logs", "crash-reports", "versions", "libraries", "assets", "runtime", "natives", "webcache", "webcache2",
    "cache", ".fabric", ".mixin.out", "downloads", ".git",
    "launcher_profiles.json", "launcher_accounts.json", "launcher_msa_credentials.bin", "launcher_settings.json",
    "launcher_log.txt", "launcher_ui_state.json", "launcher_gamer_pics.json", "launcher_entitlements.json",
    "launcher_cef_log.txt", "usercache.json", "usernamecache.json", "tlauncherprofiles.json",
    "tlauncher_profiles.json", "tlauncher-library", "tlauncher",
    # metadata of other launchers (copying it would even overwrite LowCore's own instance.json)
    "instance.json", "instance.cfg", "mmc-pack.json", "minecraftinstance.json", "profile.json", "config.json",
    ".lowcore_managed.json",
}


# ------------------------------------------------------------------ small helpers

def looks_like_mc_version(v: str) -> bool:
    v = (v or "").strip()
    return bool(_MC_RELEASE.match(v) or _MC_SNAPSHOT.match(v) or _MC_PRE.match(v))


def _vtuple(v: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", v))


def _read_json(path: str):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return None


def _parse_cfg(path: str) -> Dict[str, str]:
    out: Dict[str, str] = {}
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith(("[", "#", ";")) or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    except OSError:
        pass
    return out


def _norm_loader(name: str) -> str:
    return LOADER_NAMES.get((name or "").strip().lower(), "Vanilla")


def format_size(n: int) -> str:
    size = float(n)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{n} B"


def _entry(source: str, name: str, mc: Optional[str], loader: str, game_dir: str, **extra) -> dict:
    e = {"source": source, "name": name, "mc_version": mc, "loader": loader, "game_dir": game_dir,
         "loader_version": None, "note": "", "guessed": False, "size": 0}
    e.update({k: v for k, v in extra.items() if v is not None})
    return e


# ------------------------------------------------------------------ official launcher (and TLauncher / SKLauncher)

def parse_version_id(version_id: str, versions_dir: Optional[str] = None) -> Tuple[Optional[str], str, Optional[str], str]:
    """Official-launcher version id -> (minecraft version, loader, loader version, note)."""
    vid = (version_id or "").strip()

    if versions_dir:
        data = _read_json(os.path.join(versions_dir, vid, f"{vid}.json"))
        if isinstance(data, dict):
            libs = [str(l.get("name", "")) for l in data.get("libraries", []) if isinstance(l, dict)]
            for prefix, loader in (("net.fabricmc:fabric-loader", "Fabric"), ("org.quiltmc:quilt-loader", "Quilt"),
                                   ("net.neoforged:neoforge", "NeoForge"), ("net.neoforged.fancymodloader", "NeoForge"),
                                   ("net.minecraftforge:forge", "Forge"), ("net.minecraftforge:fmlloader", "Forge")):
                hit = next((l for l in libs if l.startswith(prefix)), None)
                if hit:
                    parts = hit.split(":")
                    mc = data.get("inheritsFrom")
                    return (mc if looks_like_mc_version(mc or "") else None), loader, (parts[2] if len(parts) > 2 else None), ""

    m = re.match(r"^(?:fabric|quilt)-loader-(?P<lv>.+?)-(?P<mc>.+)$", vid)
    if m and _MC_AT_END.search(m.group("mc")):
        loader = "Fabric" if vid.startswith("fabric") else "Quilt"
        return _MC_AT_END.search(m.group("mc")).group(1), loader, m.group("lv"), ""

    m = re.match(r"^(?P<mc>\d+\.\d+(?:\.\d+)?)-forge-?(?P<fv>.+)$", vid, re.I)
    if m:
        return m.group("mc"), "Forge", m.group("fv"), ""

    m = re.match(r"^neoforge-(?P<nv>\d+)\.(?P<minor>\d+)\.", vid, re.I)
    if m:
        major, minor = m.group("nv"), int(m.group("minor"))
        mc = f"1.{major}.{minor}" if minor else f"1.{major}"
        return mc, "NeoForge", vid.split("-", 1)[1], ""

    m = re.match(r"^(?P<mc>\d+\.\d+(?:\.\d+)?)-OptiFine", vid, re.I)
    if m:
        return m.group("mc"), "Vanilla", None, "OptiFine is not a mod loader: imported as Vanilla (Sodium + Iris on Fabric replace it)."

    if looks_like_mc_version(vid):
        return vid, "Vanilla", None, ""
    return None, "Vanilla", None, ""


def _latest_installed(versions_dir: str, snapshots: bool) -> Optional[str]:
    best = None
    try:
        names = os.listdir(versions_dir)
    except OSError:
        return None
    for n in names:
        if not os.path.isfile(os.path.join(versions_dir, n, f"{n}.json")):
            continue
        ok = _MC_RELEASE.match(n) or (snapshots and (_MC_SNAPSHOT.match(n) or _MC_PRE.match(n)))
        if ok and (best is None or _vtuple(n) > _vtuple(best)):
            best = n
    return best


def detect_official(root: str, source: str = "Minecraft Launcher") -> List[dict]:
    out, seen = [], set()
    versions_dir = os.path.join(root, "versions")
    for fname in ("launcher_profiles.json", "TlauncherProfiles.json", "tlauncher_profiles.json"):
        data = _read_json(os.path.join(root, fname))
        if not isinstance(data, dict):
            continue
        label = source if fname == "launcher_profiles.json" else "TLauncher"
        for prof in (data.get("profiles") or {}).values():
            if not isinstance(prof, dict):
                continue
            vid = (prof.get("lastVersionId") or "").strip()
            if vid.startswith("latest"):
                vid = _latest_installed(versions_dir, "snapshot" in vid) or ""
            if not vid:
                continue
            game_dir = prof.get("gameDir") or root
            if not os.path.isdir(game_dir):
                continue
            key = (vid, os.path.normcase(os.path.abspath(game_dir)))
            if key in seen:
                continue
            seen.add(key)
            mc, loader, lv, note = parse_version_id(vid, versions_dir)
            name = (prof.get("name") or "").strip() or (f"{loader} {mc}" if mc else vid)
            out.append(_entry(label, name, mc, loader, game_dir, loader_version=lv, note=note))
    return out


# ------------------------------------------------------------------ Prism / PolyMC / MultiMC

_PRISM_LOADERS = {"net.fabricmc.fabric-loader": "Fabric", "org.quiltmc.quilt-loader": "Quilt",
                  "net.minecraftforge": "Forge", "net.neoforged": "NeoForge"}


def parse_prism_instance(inst_dir: str, source: str = "Prism Launcher") -> Optional[dict]:
    pack = _read_json(os.path.join(inst_dir, "mmc-pack.json"))
    cfg = _parse_cfg(os.path.join(inst_dir, "instance.cfg"))
    if not isinstance(pack, dict) and not cfg:
        return None
    mc, loader, lv = None, "Vanilla", None
    for comp in (pack or {}).get("components", []):
        if not isinstance(comp, dict):
            continue
        uid, ver = comp.get("uid"), comp.get("version") or comp.get("cachedVersion")
        if uid == "net.minecraft":
            mc = ver
        elif uid in _PRISM_LOADERS:
            loader, lv = _PRISM_LOADERS[uid], ver
    game_dir = next((os.path.join(inst_dir, d) for d in ("minecraft", ".minecraft") if os.path.isdir(os.path.join(inst_dir, d))), None)
    if not game_dir:
        return None
    extra = {}
    try:
        secs = int(cfg.get("totalTimePlayed", 0))
        if secs > 0:
            extra["playtime_seconds"] = secs
        last = int(cfg.get("lastLaunchTime", 0))
        if last > 0:
            extra["last_played"] = last // 1000
    except ValueError:
        pass
    return _entry(source, cfg.get("name") or os.path.basename(inst_dir), mc, loader, game_dir, loader_version=lv, **extra)


def _prism_label(root: str) -> str:
    base = os.path.basename(os.path.normpath(root)).lower()
    return "PolyMC" if "polymc" in base else ("MultiMC" if "multimc" in base else "Prism Launcher")


def prism_instances_dir(root: str) -> str:
    for cfg_name in ("prismlauncher.cfg", "polymc.cfg", "multimc.cfg"):
        d = _parse_cfg(os.path.join(root, cfg_name)).get("InstanceDir")
        if d:
            return d if os.path.isabs(d) else os.path.join(root, d)
    return os.path.join(root, "instances")


def detect_prism_like(instances_dir: str, source: str = "Prism Launcher") -> List[dict]:
    out = []
    if not os.path.isdir(instances_dir):
        return out
    for d in sorted(os.listdir(instances_dir)):
        p = os.path.join(instances_dir, d)
        if d.startswith(("_", ".")) or not os.path.isdir(p):
            continue
        e = parse_prism_instance(p, source)
        if e:
            out.append(e)
    return out


# ------------------------------------------------------------------ CurseForge app

def parse_curseforge_instance(inst_dir: str) -> Optional[dict]:
    data = _read_json(os.path.join(inst_dir, "minecraftinstance.json"))
    if not isinstance(data, dict):
        return None
    base = data.get("baseModLoader") or {}
    bname = str(base.get("name") or "").lower()
    loader, lv = "Vanilla", None
    for prefix, name in (("neoforge-", "NeoForge"), ("forge-", "Forge"), ("fabric-", "Fabric"), ("quilt-", "Quilt")):
        if bname.startswith(prefix):
            loader, lv = name, bname[len(prefix):]
            break
    if loader == "Vanilla" and base:
        loader = {1: "Forge", 4: "Fabric", 5: "Quilt", 6: "NeoForge"}.get(base.get("type"), "Vanilla")
    mc = data.get("gameVersion") or base.get("minecraftVersion")
    return _entry("CurseForge", data.get("name") or os.path.basename(inst_dir), mc, loader, inst_dir, loader_version=lv)


def detect_curseforge(instances_dir: str) -> List[dict]:
    out = []
    if os.path.isdir(instances_dir):
        for d in sorted(os.listdir(instances_dir)):
            p = os.path.join(instances_dir, d)
            e = parse_curseforge_instance(p) if os.path.isdir(p) else None
            if e:
                out.append(e)
    return out


# ------------------------------------------------------------------ Modrinth App

def _read_modrinth_db(db_path: str) -> Dict[str, dict]:
    rows: Dict[str, dict] = {}

    def query(path: str, uri: bool) -> None:
        con = sqlite3.connect(path, uri=uri)
        try:
            cols = {r[1] for r in con.execute("PRAGMA table_info(profiles)")}
            want = [c for c in ("path", "name", "game_version", "mod_loader", "mod_loader_version") if c in cols]
            if "path" not in want or "game_version" not in want:
                return
            for r in con.execute(f"SELECT {', '.join(want)} FROM profiles"):
                rec = dict(zip(want, r))
                rows[str(rec["path"])] = rec
        finally:
            con.close()

    try:
        query("file:" + db_path.replace("\\", "/") + "?mode=ro", True)
    except Exception:
        tmp = tempfile.mkdtemp()  # app running / locked: read a private copy instead
        try:
            for suffix in ("", "-wal", "-shm"):
                if os.path.exists(db_path + suffix):
                    shutil.copy2(db_path + suffix, os.path.join(tmp, "app.db" + suffix))
            query(os.path.join(tmp, "app.db"), False)
        except Exception:
            pass
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    return rows


def detect_modrinth_app(root: str) -> List[dict]:
    profiles_dir = os.path.join(root, "profiles")
    if not os.path.isdir(profiles_dir):
        return []
    rows = _read_modrinth_db(os.path.join(root, "app.db")) if os.path.isfile(os.path.join(root, "app.db")) else {}
    out = []
    for d in sorted(os.listdir(profiles_dir)):
        p = os.path.join(profiles_dir, d)
        if not os.path.isdir(p):
            continue
        row = rows.get(d)
        if row and row.get("game_version"):
            out.append(_entry("Modrinth App", row.get("name") or d, row["game_version"], _norm_loader(row.get("mod_loader")), p,
                              loader_version=row.get("mod_loader_version")))
        else:
            e = parse_loose_game_dir(p, "Modrinth App")
            if e:
                out.append(e)
    return out


# ------------------------------------------------------------------ ATLauncher / GDLauncher

def parse_atlauncher_instance(inst_dir: str) -> Optional[dict]:
    data = _read_json(os.path.join(inst_dir, "instance.json"))
    if not isinstance(data, dict) or not isinstance(data.get("launcher"), dict):
        return None  # (LowCore's own instance.json has no "launcher" block)
    launcher = data["launcher"]
    m = re.match(r"^\d+\.\d+(?:\.\d+)?", str(data.get("id") or ""))
    mc = m.group(0) if m else None
    lv = launcher.get("loaderVersion") if isinstance(launcher.get("loaderVersion"), dict) else {}
    return _entry("ATLauncher", launcher.get("name") or os.path.basename(inst_dir), mc, _norm_loader(lv.get("type")), inst_dir,
                  loader_version=lv.get("version"))


def parse_gdlauncher_instance(inst_dir: str) -> Optional[dict]:
    data = _read_json(os.path.join(inst_dir, "config.json"))
    loader = data.get("loader") if isinstance(data, dict) else None
    if not isinstance(loader, dict) or not loader.get("mcVersion"):
        return None
    return _entry("GDLauncher", os.path.basename(inst_dir), loader.get("mcVersion"), _norm_loader(loader.get("loaderType")), inst_dir,
                  loader_version=loader.get("loaderVersion"))


def _detect_children(instances_dir: str, parsers) -> List[dict]:
    out = []
    if os.path.isdir(instances_dir):
        for d in sorted(os.listdir(instances_dir)):
            p = os.path.join(instances_dir, d)
            if os.path.isdir(p):
                for parse in parsers:
                    e = parse(p)
                    if e:
                        out.append(e)
                        break
    return out


# ------------------------------------------------------------------ any folder (best effort)

def parse_loose_game_dir(path: str, source: str = "Folder") -> Optional[dict]:
    has_game_files = any(os.path.isdir(os.path.join(path, x)) for x in ("mods", "saves", "resourcepacks", "config")) \
        or os.path.isfile(os.path.join(path, "options.txt"))
    if not has_game_files:
        return None
    loader, mc = guess_loader_and_version(os.path.join(path, "mods"))
    return _entry(source, os.path.basename(os.path.normpath(path)) or "Imported", mc, _norm_loader(loader or "vanilla"), path,
                  guessed=True)


# ------------------------------------------------------------------ discovery

def default_sources() -> List[Tuple[str, str]]:
    """(kind, folder) pairs worth checking on this computer."""
    home = os.path.expanduser("~")
    srcs: List[Tuple[str, str]] = []
    if os.name == "nt":
        appdata = os.environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
        srcs += [("official", os.path.join(appdata, ".minecraft")),
                 ("prism", os.path.join(appdata, "PrismLauncher")), ("prism", os.path.join(appdata, "PolyMC")),
                 ("prism", os.path.join(appdata, "MultiMC")),
                 ("curseforge", os.path.join(home, "curseforge", "minecraft", "Instances")),
                 ("curseforge", os.path.join(home, "Documents", "curseforge", "minecraft", "Instances")),
                 ("modrinth", os.path.join(appdata, "ModrinthApp")), ("modrinth", os.path.join(appdata, "com.modrinth.theseus")),
                 ("atlauncher", os.path.join(appdata, "ATLauncher", "instances")),
                 ("gdlauncher", os.path.join(appdata, "gdlauncher_next", "instances"))]
    else:
        share = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
        mac = os.path.join(home, "Library", "Application Support")
        srcs += [("official", os.path.join(home, ".minecraft")), ("official", os.path.join(mac, "minecraft")),
                 ("prism", os.path.join(share, "PrismLauncher")), ("prism", os.path.join(share, "PolyMC")),
                 ("prism", os.path.join(home, ".var", "app", "org.prismlauncher.PrismLauncher", "data", "PrismLauncher")),
                 ("prism", os.path.join(mac, "PrismLauncher")),
                 ("modrinth", os.path.join(share, "ModrinthApp")), ("modrinth", os.path.join(mac, "ModrinthApp")),
                 ("atlauncher", os.path.join(share, "ATLauncher", "instances")),
                 ("curseforge", os.path.join(home, "curseforge", "minecraft", "Instances"))]
    return srcs


def _run_source(kind: str, path: str) -> List[dict]:
    if not os.path.isdir(path):
        return []
    try:
        if kind == "official":
            return detect_official(path)
        if kind == "prism":
            return detect_prism_like(prism_instances_dir(path), _prism_label(path))
        if kind == "curseforge":
            return detect_curseforge(path)
        if kind == "modrinth":
            return detect_modrinth_app(path)
        if kind == "atlauncher":
            return _detect_children(path, [parse_atlauncher_instance])
        if kind == "gdlauncher":
            return _detect_children(path, [parse_gdlauncher_instance])
    except Exception:
        return []
    return []


def _finish(entries: List[dict], with_sizes: bool) -> List[dict]:
    seen, out = set(), []
    for e in entries:
        key = (os.path.normcase(os.path.abspath(e["game_dir"])), e["name"].lower(), e.get("mc_version"), e["loader"])
        if key in seen:
            continue
        seen.add(key)
        if with_sizes:
            e["size"] = dir_size(e["game_dir"], include_worlds=True)
        out.append(e)
    return sorted(out, key=lambda e: (e["source"], e["name"].lower()))


def scan_default(with_sizes: bool = True) -> List[dict]:
    entries: List[dict] = []
    for kind, path in default_sources():
        entries += _run_source(kind, path)
    return _finish(entries, with_sizes)


def scan_folder(path: str, with_sizes: bool = True) -> List[dict]:
    """Smart scan of a folder the user picked: a launcher folder, an instances folder or a single instance."""
    path = os.path.abspath(path)
    entries: List[dict] = []
    if not os.path.isdir(path):
        return entries

    single_parsers = [parse_prism_instance, parse_curseforge_instance, parse_atlauncher_instance, parse_gdlauncher_instance]
    names = set(os.listdir(path))

    if "launcher_profiles.json" in names or "TlauncherProfiles.json" in names or "versions" in names and "libraries" in names:
        entries += detect_official(path)
    for parse in single_parsers:
        e = parse(path)
        if e:
            entries.append(e)
            break
    if "profiles" in names and os.path.isdir(os.path.join(path, "profiles")):
        entries += detect_modrinth_app(path)
    for sub in ("instances", "Instances"):
        if sub in names:
            entries += detect_prism_like(os.path.join(path, sub), _prism_label(path))
            entries += detect_curseforge(os.path.join(path, sub))
            entries += _detect_children(os.path.join(path, sub), [parse_atlauncher_instance, parse_gdlauncher_instance])
    if not entries:  # the folder itself may be an "instances" folder
        entries += detect_prism_like(path, _prism_label(path))
        entries += detect_curseforge(path)
        entries += _detect_children(path, [parse_atlauncher_instance, parse_gdlauncher_instance])
    if not entries:
        for candidate in (os.path.join(path, "minecraft"), os.path.join(path, ".minecraft"), path):
            e = parse_loose_game_dir(candidate)
            if e:
                entries.append(e)
                break
    return _finish(entries, with_sizes)


# ------------------------------------------------------------------ copying

def _excluded(name: str, is_dir: bool, include_worlds: bool) -> bool:
    low = name.lower()
    if low in EXCLUDE_TOP or low.startswith("hs_err_pid") or low.endswith(".lock"):
        return True
    return is_dir and low == "saves" and not include_worlds


def _walk_files(src: str, include_worlds: bool):
    for root, dirs, files in os.walk(src):
        if os.path.normpath(root) == os.path.normpath(src):
            dirs[:] = [d for d in dirs if not _excluded(d, True, include_worlds)]
            files = [f for f in files if not _excluded(f, False, include_worlds)]
        for f in files:
            p = os.path.join(root, f)
            if not os.path.islink(p):
                yield p


def dir_size(path: str, include_worlds: bool = True) -> int:
    total = 0
    try:
        for p in _walk_files(path, include_worlds):
            try:
                total += os.path.getsize(p)
            except OSError:
                pass
    except OSError:
        pass
    return total


def copy_instance_files(src: str, dst: str, include_worlds: bool = True,
                        progress_cb: Optional[Callable[[int, int], None]] = None) -> List[str]:
    """Copies the game folder. Returns the list of files that could not be copied."""
    src, dst = os.path.abspath(src), os.path.abspath(dst)
    try:
        common = os.path.commonpath([src, dst])
    except ValueError:  # different drives: no overlap possible
        common = None
    if common in (src, dst):  # same folder, one inside the other: copying would loop or overwrite itself
        raise ValueError("The source folder and the new instance folder overlap.")

    files = list(_walk_files(src, include_worlds))
    sizes = {}
    for p in files:
        try:
            sizes[p] = os.path.getsize(p)
        except OSError:
            sizes[p] = 0
    total, done, failed, last_emit = sum(sizes.values()), 0, [], 0.0

    for p in files:
        rel = os.path.relpath(p, src)
        # never let a file land inside the instance's own metadata
        if rel.lower() == "instance.json":
            continue
        target = os.path.join(dst, rel)
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(p, target)
        except OSError as e:
            failed.append(f"{rel}: {e}")
        done += sizes[p]
        if progress_cb and time.time() - last_emit > 0.1:
            last_emit = time.time()
            progress_cb(done, total)
    if progress_cb:
        progress_cb(total, total)
    return failed


def _unique_name(name: str, taken: Set[str]) -> str:
    if name.lower() not in taken:
        return name
    n = 2
    while f"{name} ({n})".lower() in taken:
        n += 1
    return f"{name} ({n})"


def import_entry(entry: dict, inst_mgr, include_worlds: bool = True,
                 progress_cb: Optional[Callable[[int, int], None]] = None,
                 taken_names: Optional[Set[str]] = None) -> dict:
    """Creates a LowCore instance for `entry` and copies its files. Returns {"name","folder","failed_files"}."""
    mc = entry.get("mc_version")
    if not mc or not looks_like_mc_version(mc):
        raise ValueError("Minecraft version unknown")
    taken = set(taken_names or {i.get("name", "").lower() for i in inst_mgr.list_instances()})
    name = _unique_name(entry["name"], taken)

    inst = inst_mgr.create_instance(name, mc, entry.get("loader") or "Vanilla")
    try:
        failed = copy_instance_files(entry["game_dir"], inst["path"], include_worlds, progress_cb)
        meta_path = os.path.join(inst["path"], "instance.json")
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        meta["imported_from"] = entry.get("source", "")
        if entry.get("loader_version"):
            meta["loader_version"] = entry["loader_version"]
        if entry.get("playtime_seconds"):
            meta["playtime_seconds"] = int(entry["playtime_seconds"])
        if entry.get("last_played"):
            meta["last_played"] = int(entry["last_played"])
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=4)
    except Exception:
        inst_mgr.delete_instance(inst["path"])  # do not leave a half-imported instance behind
        raise
    return {"name": name, "folder": os.path.basename(inst["path"]), "failed_files": failed}
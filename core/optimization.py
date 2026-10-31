import os
import re
import json
from typing import List, Dict
from core.modrinth_service import ModrinthService

# ----------------- LOADER SPECIFIC MOD STACKS -----------------

FABRIC_OPTIMIZATION_MODS = [
    "fabric-api",
    "modmenu",
    "cloth-config",
    "sodium",
    "sodium-extra",
    "reeses-sodium-options",
    "lithium",
    "ferrite-core",
    "immediatelyfast",
    "moreculling",
    "krypton",
    "modernfix",
    "memoryleakfix",
    "clumps",
    "fastquit"
]

FORGE_OPTIMIZATION_MODS = [
    "embeddium",           # Official Forge/NeoForge Sodium performance rewrite (+200% FPS)
    "ferrite-core",        # Cuts RAM usage by ~45% (Universal on Forge & Fabric)
    "modernfix",           # Universal memory and launch time fix
    "immediatelyfast",     # HUD and entity immediate rendering fix
    "clumps",              # Clumps XP orbs to fix lag spikes
    "fastsuite",           # Optimizes recipe lookups on Forge
    "fast-load"            # Faster world load times
]

PVP_UTILITIES_FABRIC = [
    "ukulib",
    "appleskin",
    "gamma-utils",
    "betterhitreg",
    "betterhurtcam",
    "better-ping-display-fabric",
    "zoomify"
]

PVP_UTILITIES_FORGE = [
    "appleskin",
    "betterhurtcam",
    "rubidium-extra",
    "embeddium-extra"
]

BROKEN_LIBRARIES = [
    "entityculling",
    "trender",
    "transition",
    "dynamic_fps",
    "battery",
    "walksylib",
    "marlow",
    "herosanchoroptimizer",
    "c2me"
]

MANAGED_MANIFEST = ".lowcore_managed.json"

# What may directly follow a mod's name inside a jar filename (loader tag, "mc1.21", a version number).
# Anything else ("sodium" + "extra") means it is a different mod.
_NEUTRAL_SUFFIXES = ("fabric", "quilt", "forge", "neoforge", "mc")


def _norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", text.lower())


def filename_matches_slug(filename: str, slug: str) -> bool:
    """True when `filename` is a jar of the mod `slug` (and not a longer-named sibling mod)."""
    fn = _norm(filename.rsplit(".", 1)[0] if "." in filename else filename)
    sl = _norm(slug)
    if not sl or not fn.startswith(sl):
        return False
    rest = fn[len(sl):]
    return rest == "" or rest[0].isdigit() or rest.startswith(_NEUTRAL_SUFFIXES)


class OptimizationEngine:
    @staticmethod
    def _memory_info():
        try:
            import psutil
            vm = psutil.virtual_memory()
            return vm.total // (1024 * 1024), vm.available // (1024 * 1024)
        except Exception:
            return None, None

    @staticmethod
    def build_high_tier_jvm_args(ram_mb: int) -> List[str]:
        cpu_count = os.cpu_count() or 4
        gc_threads = max(2, cpu_count - 1)

        total_mb, available_mb = OptimizationEngine._memory_info()
        if total_mb:
            # Never hand the game more than 75% of the machine's RAM.
            ram_mb = max(1024, min(ram_mb, int(total_mb * 0.75)))

        args = [
            f"-Xms{ram_mb}M",
            f"-Xmx{ram_mb}M",
            "-XX:+UnlockExperimentalVMOptions",
            "-XX:+UseG1GC",
            f"-XX:ParallelGCThreads={gc_threads}",
            f"-XX:ConcGCThreads={max(1, gc_threads // 2)}",
            "-XX:G1ReservePercent=15",
            "-XX:G1HeapRegionSize=32M",
            "-XX:InitiatingHeapOccupancyPercent=45",
            "-XX:G1MixedGCLiveThresholdPercent=85",
        ]

        # NOTE: -XX:+AlwaysPreTouch is intentionally NOT used: it touches the whole heap before the
        # game starts, adding seconds to every launch for a tiny gain in smoothness.

        args += [
            "-XX:+DisableExplicitGC",
            "-XX:+UseStringDeduplication",
            "-XX:MaxGCPauseMillis=20",
            "-Dsun.rmi.dgc.server.gcInterval=2147483646",
            "-Dsun.rmi.dgc.client.gcInterval=2147483646",
            "-Djdk.tls.client.protocols=TLSv1.2,TLSv1.3",
            "-Dlog4j2.formatMsgNoLookups=true"
        ]
        return args

    @classmethod
    def ensure_safe_configs(cls, instance_dir: str):
        config_dir = os.path.join(instance_dir, "config")
        os.makedirs(config_dir, exist_ok=True)

        sodium_cfg_path = os.path.join(config_dir, "sodium-options.json")
        if not os.path.exists(sodium_cfg_path):
            sodium_safe_defaults = {
                "quality": {"weather_quality": "FAST", "leaves_quality": "FAST", "enable_vignette": False},
                "advanced": {"enable_memory_tracing": False, "use_advanced_staging_buffers": False, "cpu_render_ahead_limit": 3},
                "performance": {
                    "chunk_builder_threads": 0,
                    "always_defer_chunk_updates": True,
                    "animate_only_visible_textures": True,
                    "use_entity_culling": True,
                    "use_fog_occlusion": True,
                    "use_block_face_culling": True,
                    "use_no_error_context": False
                }
            }
            try:
                with open(sodium_cfg_path, "w", encoding="utf-8") as f:
                    json.dump(sodium_safe_defaults, f, indent=2)
            except Exception:
                pass

        options_txt = os.path.join(instance_dir, "options.txt")
        if not os.path.exists(options_txt):
            try:
                with open(options_txt, "w", encoding="utf-8") as f:
                    f.write("gamma:100.0\nmaxFps:260\nenableVsync:false\n")
            except Exception:
                pass

    # ----------------- managed-mod manifest -----------------

    @classmethod
    def _load_manifest(cls, mods_dir: str) -> Dict[str, List[str]]:
        path = os.path.join(mods_dir, MANAGED_MANIFEST)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    @classmethod
    def _save_manifest(cls, mods_dir: str, manifest: Dict[str, List[str]]):
        try:
            with open(os.path.join(mods_dir, MANAGED_MANIFEST), "w", encoding="utf-8") as f:
                json.dump(manifest, f, indent=2)
        except Exception:
            pass

    @classmethod
    def _is_mod_installed(cls, slug: str, existing_files: List[str], manifest: Dict[str, List[str]] = None) -> bool:
        if manifest:
            recorded = manifest.get(slug, [])
            if recorded and any(name in existing_files for name in recorded):
                return True
        return any(filename_matches_slug(name, slug) for name in existing_files)

    @classmethod
    def purge_broken_libraries(cls, mods_dir: str):
        """Disables known-bad jars by renaming them to *.jar.disabled (nothing is deleted)."""
        if not os.path.exists(mods_dir):
            return
        for file in os.listdir(mods_dir):
            if not file.endswith(".jar"):
                continue
            if any(filename_matches_slug(file, bad) for bad in BROKEN_LIBRARIES):
                src = os.path.join(mods_dir, file)
                dst = src + ".disabled"
                try:
                    if not os.path.exists(dst):
                        os.replace(src, dst)
                except OSError:
                    pass

    @classmethod
    def provision_preset_mods(cls, instance_dir: str, version: str, loader: str, preset: str, status_cb=None) -> dict:
        """
        Installs the preset's mods. Returns {"installed": [...slugs], "failed": [(slug, error), ...]}.
        Failures are reported through status_cb instead of being swallowed.
        """
        result = {"installed": [], "failed": []}
        preset_lower = preset.lower()
        loader_lower = loader.lower()
        if "vanilla" in preset_lower or loader_lower == "vanilla":
            return result

        cls.ensure_safe_configs(instance_dir)

        mods_dir = os.path.join(instance_dir, "mods")
        os.makedirs(mods_dir, exist_ok=True)
        cls.purge_broken_libraries(mods_dir)

        target_mods = []
        is_forge_family = loader_lower in ("forge", "neoforge", "neo-forge")

        if "fully optimized" in preset_lower:
            target_mods.extend(FORGE_OPTIMIZATION_MODS if is_forge_family else FABRIC_OPTIMIZATION_MODS)

        if "utilities" in preset_lower or "pvp" in preset_lower:
            target_mods.extend(PVP_UTILITIES_FORGE if is_forge_family else PVP_UTILITIES_FABRIC)

        target_mods = list(dict.fromkeys(target_mods))

        existing_jars = [
            f for f in os.listdir(mods_dir)
            if f.endswith(".jar") and os.path.getsize(os.path.join(mods_dir, f)) > 0
        ]
        manifest = cls._load_manifest(mods_dir)

        missing_mods = [
            slug for slug in target_mods
            if not cls._is_mod_installed(slug, existing_jars, manifest)
        ]

        if not missing_mods:
            if status_cb:
                status_cb("All mods up to date. Ready to boot...", 1, 1)
            return result

        # Modrinth loader category. Quilt runs Fabric mods, so it uses the Fabric catalogue.
        mod_loader_query = "neoforge" if "neo" in loader_lower else ("forge" if "forge" in loader_lower else "fabric")

        total_missing = len(missing_mods)
        for idx, mod_slug in enumerate(missing_mods):
            if status_cb:
                status_cb(f"Installing {loader} mod: {mod_slug} ({idx + 1}/{total_missing})", idx + 1, total_missing)

            try:
                files = ModrinthService.download_with_dependencies(
                    mod_slug,
                    version,
                    mod_loader_query,
                    mods_dir,
                    progress_cb=(lambda msg: status_cb(msg, idx + 1, total_missing)) if status_cb else None
                )
                manifest[mod_slug] = files
                result["installed"].append(mod_slug)
            except Exception as e:
                result["failed"].append((mod_slug, str(e)))
                if status_cb:
                    status_cb(f"Could not install {mod_slug}: {e}", idx + 1, total_missing)

        cls._save_manifest(mods_dir, manifest)

        if result["failed"] and status_cb:
            status_cb(f"{len(result['failed'])} of {total_missing} mods could not be installed.", total_missing, total_missing)
        return result
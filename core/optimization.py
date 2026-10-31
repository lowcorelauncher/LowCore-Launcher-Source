import os
from typing import List


class OptimizationEngine:
    """JVM tuning for the game process."""

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
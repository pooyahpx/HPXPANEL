import math
import os
import platform
import secrets
import socket
import subprocess
import threading
import time
from dataclasses import dataclass
from functools import lru_cache

import psutil

_cpu_sample_lock = threading.Lock()


@dataclass
class MemoryStat:
    total: int
    used: int
    free: int


@dataclass
class CPUStat:
    cores: int
    percent: float


@dataclass
class DiskStat:
    total: int
    used: int
    free: int


@dataclass
class HostIdentity:
    hostname: str
    os_name: str | None
    os_version: str | None
    kernel: str | None
    cpu_model: str | None
    cpu_freq_mhz: float | None
    virtualization: str | None
    server_uptime_seconds: int


def cpu_usage() -> CPUStat:
    # interval=None measures from the previous process-wide call and produces
    # unstable spikes when several API/jobs poll concurrently. Serialize a
    # short fixed-window sample so every caller observes comparable data.
    with _cpu_sample_lock:
        percent = psutil.cpu_percent(interval=0.25)
    return CPUStat(cores=psutil.cpu_count(), percent=percent)


def memory_usage() -> MemoryStat:
    mem = psutil.virtual_memory()
    # Estimate active memory by excluding file cache when available.
    if hasattr(mem, "free") and hasattr(mem, "cached"):
        used = mem.total - mem.free - mem.cached
        # Guard against unexpected platform-specific values.
        if used < 0 or used > mem.total:
            used = mem.used
    else:
        used = mem.used

    return MemoryStat(total=mem.total, used=used, free=mem.available)


def disk_usage(path: str | None = None) -> DiskStat:
    usage_path = path or os.path.abspath(os.sep)
    try:
        disk = psutil.disk_usage(usage_path)
    except Exception:
        # Fallback to the current working directory if root path is unavailable.
        disk = psutil.disk_usage(".")

    return DiskStat(total=disk.total, used=disk.used, free=disk.free)


def get_uptime() -> int:
    """Panel process uptime (seconds since this Python process started)."""
    pid = os.getpid()
    process = psutil.Process(pid)
    create_time = process.create_time()
    return int(time.time() - create_time)


def get_server_uptime() -> int:
    """Host OS uptime since boot."""
    try:
        return max(0, int(time.time() - psutil.boot_time()))
    except Exception:
        return 0


def _read_os_release() -> tuple[str | None, str | None]:
    path = "/etc/os-release"
    if not os.path.isfile(path):
        return None, None
    data: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                data[key] = value.strip().strip('"')
    except OSError:
        return None, None
    name = data.get("NAME") or data.get("ID")
    version = data.get("VERSION") or data.get("VERSION_ID")
    return name, version


def _read_cpu_model() -> str | None:
    try:
        with open("/proc/cpuinfo", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if line.lower().startswith("model name") and ":" in line:
                    return line.split(":", 1)[1].strip() or None
    except OSError:
        pass
    return platform.processor() or None


def _detect_virtualization() -> str | None:
    try:
        result = subprocess.run(
            ["systemd-detect-virt"],
            capture_output=True,
            text=True,
            timeout=1.5,
            check=False,
        )
        value = (result.stdout or "").strip().lower()
        if value and value != "none":
            return value
        if value == "none":
            return None
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        pass

    for path in (
        "/sys/class/dmi/id/product_name",
        "/sys/class/dmi/id/sys_vendor",
        "/sys/devices/virtual/dmi/id/product_name",
    ):
        try:
            with open(path, encoding="utf-8", errors="ignore") as fh:
                text = fh.read().strip()
            if text and text.lower() not in {"none", "to be filled by o.e.m.", "default string"}:
                lowered = text.lower()
                for needle in ("kvm", "qemu", "vmware", "xen", "hyper-v", "virtualbox", "bhyve", "openvz", "lxc"):
                    if needle in lowered:
                        return needle
                return text
        except OSError:
            continue

    try:
        with open("/proc/cpuinfo", encoding="utf-8", errors="ignore") as fh:
            for line in fh:
                if line.lower().startswith("flags") and "hypervisor" in line.lower():
                    return "hypervisor"
    except OSError:
        pass
    return None


@lru_cache(maxsize=1)
def _cached_static_host_fields() -> tuple[str, str | None, str | None, str | None, str | None, str | None]:
    """Hostname/OS/kernel/cpu/virt change rarely — cache for process lifetime."""
    try:
        hostname = socket.gethostname() or platform.node() or "panel"
    except OSError:
        hostname = platform.node() or "panel"

    os_name, os_version = _read_os_release()
    if not os_name:
        os_name = platform.system() or None
    if not os_version:
        os_version = platform.release() or None

    uname = platform.uname()
    kernel = uname.release or None
    cpu_model = _read_cpu_model()
    virtualization = _detect_virtualization()
    return hostname, os_name, os_version, kernel, cpu_model, virtualization


def host_identity() -> HostIdentity:
    hostname, os_name, os_version, kernel, cpu_model, virtualization = _cached_static_host_fields()
    freq_mhz: float | None = None
    try:
        freq = psutil.cpu_freq()
        if freq is not None and freq.current:
            freq_mhz = float(freq.current)
    except Exception:
        freq_mhz = None

    return HostIdentity(
        hostname=hostname,
        os_name=os_name,
        os_version=os_version,
        kernel=kernel,
        cpu_model=cpu_model,
        cpu_freq_mhz=freq_mhz,
        virtualization=virtualization,
        server_uptime_seconds=get_server_uptime(),
    )


def random_password() -> str:
    return secrets.token_urlsafe(24)


def readable_size(size_bytes):
    if not size_bytes or size_bytes <= 0:
        return "0 B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = math.floor(math.log(size_bytes, 1024))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_name[i]}"


def readable_duration(seconds: float) -> str:
    """Format a duration (in seconds) as a human-readable string.

    Mirrors :func:`readable_size`: caller always passes seconds, this picks the
    largest natural unit (years, months, days, hours, minutes, seconds) and
    pluralizes correctly.
    """
    if not seconds or seconds <= 0:
        return "0 seconds"

    units = (
        ("year", 31_536_000),  # 365 days
        ("month", 2_592_000),  # 30 days
        ("day", 86_400),
        ("hour", 3_600),
        ("minute", 60),
        ("second", 1),
    )

    for label, factor in units:
        if seconds >= factor:
            amount = seconds / factor
            if amount % 1 == 0:
                amount_int = int(amount)
                return f"{amount_int} {label}" if amount_int == 1 else f"{amount_int} {label}s"
            return f"{amount:.2f} {label}s"

    return f"{seconds} seconds"

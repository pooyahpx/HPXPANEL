import asyncio
import json
import platform
import re
import shutil
from dataclasses import dataclass

from app.db.models import HpxTunnel, HpxTunnelRole, HpxTunnelStatus
from app.utils.logger import get_logger

logger = get_logger("hpx-tunnel-manager")

DEFAULT_IMAGE = "ghcr.io/pooyahpx/hpx-icmp:0.0.3"
_CONTAINER_PREFIX = "hpx_tunnel_"


@dataclass
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


@dataclass
class TunnelRuntimeStatus:
    container_running: bool
    interface_up: bool
    interface_ip: str | None
    bytes_up: int
    bytes_down: int
    uptime_seconds: int | None
    message: str | None


def container_name_for_tunnel(tunnel_id: int) -> str:
    return f"{_CONTAINER_PREFIX}{tunnel_id}"


def is_linux_host() -> bool:
    return platform.system().lower() == "linux"


async def run_command(*args: str, timeout: float = 30.0) -> CommandResult:
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except TimeoutError:
        proc.kill()
        await proc.communicate()
        return CommandResult(returncode=-1, stdout="", stderr="command timed out")

    return CommandResult(
        returncode=proc.returncode or 0,
        stdout=(stdout_bytes or b"").decode("utf-8", errors="replace").strip(),
        stderr=(stderr_bytes or b"").decode("utf-8", errors="replace").strip(),
    )


async def docker_available() -> bool:
    if not shutil.which("docker"):
        return False
    result = await run_command("docker", "info", "--format", "{{.ServerVersion}}", timeout=10)
    return result.returncode == 0


async def pull_image(image: str) -> tuple[bool, str | None]:
    result = await run_command("docker", "pull", image, timeout=300)
    if result.returncode != 0:
        return False, result.stderr or result.stdout or "docker pull failed"
    return True, None


async def container_is_running(container_name: str) -> bool:
    result = await run_command(
        "docker",
        "inspect",
        "-f",
        "{{.State.Running}}",
        container_name,
        timeout=10,
    )
    return result.returncode == 0 and result.stdout.strip().lower() == "true"


async def stop_container(container_name: str) -> tuple[bool, str | None]:
    if not await container_is_running(container_name):
        await run_command("docker", "rm", "-f", container_name, timeout=20)
        return True, None
    result = await run_command("docker", "rm", "-f", container_name, timeout=30)
    if result.returncode != 0:
        return False, result.stderr or result.stdout or "failed to stop container"
    return True, None


async def _assign_interface_ip(interface: str, local_ip: str, operating_mode: str | None) -> None:
    if operating_mode and operating_mode.startswith("ip:"):
        return
    cidr = local_ip if "/" in local_ip else f"{local_ip}/24"
    await run_command("ip", "addr", "add", cidr, "dev", interface, timeout=10)
    await run_command("ip", "link", "set", interface, "up", timeout=10)


async def _enable_ip_forward() -> None:
    await run_command("sysctl", "-w", "net.ipv4.ip_forward=1", timeout=5)


async def start_tunnel(tunnel: HpxTunnel, password: str) -> tuple[bool, str | None]:
    if not is_linux_host():
        return False, "HPX tunnel control requires a Linux host with Docker"
    if not await docker_available():
        return False, "Docker is not available on this host"

    container_name = tunnel.container_name or container_name_for_tunnel(tunnel.id)
    await stop_container(container_name)

    ok, err = await pull_image(tunnel.docker_image or DEFAULT_IMAGE)
    if not ok:
        return False, err

    env_args: list[str] = []
    for key, value in (
        ("INTERFACE", tunnel.interface),
        ("PASSWORD", password),
        ("KEEPALIVE", str(tunnel.keepalive)),
    ):
        env_args.extend(["-e", f"{key}={value}"])

    if tunnel.role == HpxTunnelRole.iran:
        env_args.extend(["-e", f"REMOTE_IP={tunnel.remote_ip}"])
        if tunnel.dscp_mark is not None:
            env_args.extend(["-e", f"DSCP_MARK={tunnel.dscp_mark}"])
    else:
        env_args.extend(["-e", f"SERVER={tunnel.server_listen or '0.0.0.0'}"])
        if tunnel.operating_mode:
            env_args.extend(["-e", f"OPERATING_MODE={tunnel.operating_mode}"])
        if tunnel.bandwidth_limit:
            env_args.extend(["-e", f"BANDWIDTH_LIMIT={tunnel.bandwidth_limit}"])

    if tunnel.mtu:
        env_args.extend(["-e", f"MTU={tunnel.mtu}"])

    cmd = [
        "docker",
        "run",
        "--cap-add=NET_ADMIN",
        "--device",
        "/dev/net/tun:/dev/net/tun",
        "--net=host",
        *env_args,
        "--restart",
        "unless-stopped",
        "--name",
        container_name,
        "-d",
        tunnel.docker_image or DEFAULT_IMAGE,
    ]
    result = await run_command(*cmd, timeout=60)
    if result.returncode != 0:
        return False, result.stderr or result.stdout or "docker run failed"

    await asyncio.sleep(2)
    await _enable_ip_forward()
    await _assign_interface_ip(tunnel.interface, tunnel.local_ip, tunnel.operating_mode)
    if tunnel.role == HpxTunnelRole.iran and tunnel.port_forwards:
        await apply_port_forwards(tunnel)

    if not await container_is_running(container_name):
        logs = await run_command("docker", "logs", "--tail", "20", container_name, timeout=10)
        detail = logs.stderr or logs.stdout or "container exited immediately"
        return False, detail

    return True, None


async def apply_port_forwards(tunnel: HpxTunnel) -> None:
    if tunnel.role != HpxTunnelRole.iran or not tunnel.port_forwards:
        return
    for rule in tunnel.port_forwards:
        external_port = rule.get("external_port")
        internal_ip = rule.get("internal_ip")
        internal_port = rule.get("internal_port")
        if not external_port or not internal_ip or not internal_port:
            continue
        check = await run_command(
            "iptables",
            "-t",
            "nat",
            "-C",
            "PREROUTING",
            "-p",
            "tcp",
            "--dport",
            str(external_port),
            "-j",
            "DNAT",
            "--to-destination",
            f"{internal_ip}:{internal_port}",
            timeout=5,
        )
        if check.returncode != 0:
            await run_command(
                "iptables",
                "-t",
                "nat",
                "-A",
                "PREROUTING",
                "-p",
                "tcp",
                "--dport",
                str(external_port),
                "-j",
                "DNAT",
                "--to-destination",
                f"{internal_ip}:{internal_port}",
                timeout=5,
            )


async def ping_host(host: str, count: int = 3) -> tuple[float | None, float | None]:
    if not host:
        return None, None
    result = await run_command("ping", "-c", str(count), "-W", "2", host, timeout=15)
    if result.returncode != 0:
        return None, 100.0

    loss_match = re.search(r"(\d+(?:\.\d+)?)% packet loss", result.stdout)
    rtt_match = re.search(r"rtt min/avg/max/mdev = [\d.]+/([\d.]+)/", result.stdout)
    latency = float(rtt_match.group(1)) if rtt_match else None
    loss = float(loss_match.group(1)) if loss_match else None
    return latency, loss


async def get_interface_ip(interface: str) -> str | None:
    result = await run_command("ip", "-4", "-o", "addr", "show", "dev", interface, timeout=5)
    if result.returncode != 0:
        return None
    match = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", result.stdout)
    return match.group(1) if match else None


async def get_interface_stats(interface: str) -> tuple[int, int, bool]:
    return await asyncio.to_thread(_read_interface_stats, interface)


def _read_interface_stats(interface: str) -> tuple[int, int, bool]:
    path = f"/sys/class/net/{interface}/statistics/rx_bytes"
    try:
        with open(path, encoding="utf-8") as rx_file:
            rx_bytes = int(rx_file.read().strip())
        with open(f"/sys/class/net/{interface}/statistics/tx_bytes", encoding="utf-8") as tx_file:
            tx_bytes = int(tx_file.read().strip())
        return tx_bytes, rx_bytes, True
    except OSError:
        return 0, 0, False


async def get_container_uptime(container_name: str) -> int | None:
    result = await run_command(
        "docker",
        "inspect",
        "-f",
        "{{.State.StartedAt}}",
        container_name,
        timeout=10,
    )
    if result.returncode != 0 or not result.stdout:
        return None
    from datetime import UTC, datetime as dt

    try:
        started = dt.fromisoformat(result.stdout)
        return max(0, int((dt.now(UTC) - started).total_seconds()))
    except ValueError:
        return None


async def inspect_runtime(tunnel: HpxTunnel) -> TunnelRuntimeStatus:
    container_name = tunnel.container_name or container_name_for_tunnel(tunnel.id)
    running = await container_is_running(container_name)
    interface_ip = await get_interface_ip(tunnel.interface)
    tx_bytes, rx_bytes, iface_ok = await get_interface_stats(tunnel.interface)
    uptime = await get_container_uptime(container_name) if running else None

    message = None
    if not running:
        message = "Container is not running"
    elif not iface_ok:
        message = f"Interface {tunnel.interface} is down"

    return TunnelRuntimeStatus(
        container_running=running,
        interface_up=iface_ok and interface_ip is not None,
        interface_ip=interface_ip,
        bytes_up=tx_bytes,
        bytes_down=rx_bytes,
        uptime_seconds=uptime,
        message=message,
    )


def derive_status(
    tunnel: HpxTunnel,
    runtime: TunnelRuntimeStatus,
    latency_ms: float | None,
    packet_loss_pct: float | None,
) -> HpxTunnelStatus:
    if not runtime.container_running:
        return HpxTunnelStatus.stopped if tunnel.status == HpxTunnelStatus.stopped else HpxTunnelStatus.error
    if packet_loss_pct is not None and packet_loss_pct >= 100:
        return HpxTunnelStatus.unhealthy
    if latency_ms is not None and latency_ms > 500:
        return HpxTunnelStatus.unhealthy
    if runtime.interface_up:
        return HpxTunnelStatus.running
    return HpxTunnelStatus.error


async def get_container_logs(container_name: str, tail: int = 50) -> str:
    result = await run_command("docker", "logs", "--tail", str(tail), container_name, timeout=10)
    return result.stdout or result.stderr or ""


def serialize_port_forwards(port_forwards: list | None) -> list[dict]:
    if not port_forwards:
        return []
    return [json.loads(json.dumps(item)) for item in port_forwards]

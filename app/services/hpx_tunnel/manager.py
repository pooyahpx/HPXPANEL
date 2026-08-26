import asyncio
import json
import platform
import re
import shutil
from dataclasses import dataclass

from app.db.models import HpxTunnel, HpxTunnelRole, HpxTunnelStatus
from app.utils.logger import get_logger

logger = get_logger("hpx-tunnel-manager")

# Local brand name only — no Docker Hub account / push required.
DEFAULT_IMAGE = "hpx-icmp:0.0.3"
# Upstream runtime (pulled automatically, then retagged as DEFAULT_IMAGE).
UPSTREAM_IMAGE = "stormotron/narnia:0.0.3"
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
    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        missing = args[0] if args else "command"
        return CommandResult(returncode=127, stdout="", stderr=f"{missing}: command not found")
    except OSError as exc:
        return CommandResult(returncode=1, stdout="", stderr=str(exc))

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


async def docker_unavailable_reason() -> str:
    if not shutil.which("docker"):
        return (
            "Docker CLI is missing inside the panel container. "
            "Update HPXPANEL and ensure /var/run/docker.sock is mounted."
        )
    result = await run_command("docker", "info", "--format", "{{.ServerVersion}}", timeout=10)
    if result.returncode != 0:
        return (
            "Cannot reach Docker daemon (is /var/run/docker.sock mounted into the panel?). "
            f"{(result.stderr or result.stdout or '').strip()}"
        ).strip()
    return "Docker is not available on this host"

async def pull_image(image: str) -> tuple[bool, str | None]:
    result = await run_command("docker", "pull", image, timeout=300)
    if result.returncode != 0:
        return False, result.stderr or result.stdout or "docker pull failed"
    return True, None


async def image_exists(image: str) -> bool:
    result = await run_command("docker", "image", "inspect", image, timeout=10)
    return result.returncode == 0


async def ensure_tunnel_image(wanted: str | None = None) -> tuple[str, str | None]:
    """
    Ensure a locally-named HPX image exists.

    Pulls upstream automatically and retags as hpx-icmp — no registry login/push.
    """
    # Always run under the local brand name; ignore remote registry paths from older configs.
    target = DEFAULT_IMAGE
    _ = wanted  # kept for API compatibility with callers

    if await image_exists(target):
        return target, None

    if await image_exists(UPSTREAM_IMAGE):
        await run_command("docker", "tag", UPSTREAM_IMAGE, target, timeout=30)
        return target, None

    logger.info("Pulling HPX tunnel runtime from upstream…")
    ok, err = await pull_image(UPSTREAM_IMAGE)
    if not ok:
        return target, (
            err
            or "failed to download tunnel runtime image. "
            "Check Docker Hub access on this server."
        )

    await run_command("docker", "tag", UPSTREAM_IMAGE, target, timeout=30)
    return target, None


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


async def stop_containers_using_interface(interface: str, keep_name: str | None = None) -> None:
    """Remove other hpx_tunnel_* containers that claim the same TAP INTERFACE."""
    listed = await run_command("docker", "ps", "-aq", "--filter", "name=hpx_tunnel", timeout=15)
    if listed.returncode != 0 or not listed.stdout.strip():
        return
    for cid in listed.stdout.split():
        inspect = await run_command(
            "docker",
            "inspect",
            "-f",
            "{{.Name}}\n{{range .Config.Env}}{{println .}}{{end}}",
            cid,
            timeout=10,
        )
        if inspect.returncode != 0:
            continue
        lines = [line for line in inspect.stdout.splitlines() if line.strip()]
        if not lines:
            continue
        name = lines[0].lstrip("/")
        if keep_name and name == keep_name:
            continue
        iface = None
        for line in lines[1:]:
            if line.startswith("INTERFACE="):
                iface = line.split("=", 1)[1].strip()
                break
        if iface and iface != interface:
            continue
        logger.warning("Removing conflicting tunnel container %s (interface %s)", name, interface)
        await run_command("docker", "rm", "-f", cid, timeout=30)

    still = await run_command("docker", "ps", "-q", "--filter", "name=hpx_tunnel", timeout=10)
    if not (still.stdout or "").strip():
        await run_command("ip", "link", "delete", interface, timeout=10)


async def wait_for_interface(interface: str, timeout: float = 20.0) -> bool:
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        link = await run_command("ip", "link", "show", "dev", interface, timeout=5)
        if link.returncode == 0:
            return True
        await asyncio.sleep(0.5)
    return False


async def _assign_interface_ip(
    interface: str,
    local_ip: str,
    operating_mode: str | None,
    mtu: int | None = None,
) -> str | None:
    if operating_mode and operating_mode.startswith("ip:"):
        return None
    if not await wait_for_interface(interface, timeout=20.0):
        return f"tunnel interface {interface} did not appear — check docker logs"

    cidr = local_ip if "/" in local_ip else f"{local_ip}/24"
    # Replace any previous address on this TAP, then add ours.
    await run_command("ip", "addr", "flush", "dev", interface, timeout=10)
    add = await run_command("ip", "addr", "add", cidr, "dev", interface, timeout=10)
    if add.returncode != 0 and "File exists" not in (add.stderr or ""):
        # Retry once without flush failure noise.
        add = await run_command("ip", "addr", "add", cidr, "dev", interface, timeout=10)
        if add.returncode != 0 and "File exists" not in (add.stderr or ""):
            return add.stderr or add.stdout or f"failed to assign {cidr} on {interface}"

    if mtu:
        await run_command("ip", "link", "set", "dev", interface, "mtu", str(mtu), timeout=10)
    await run_command("ip", "link", "set", interface, "up", timeout=10)

    assigned = await get_interface_ip(interface)
    if not assigned:
        return f"interface {interface} is up but has no IPv4 address"
    return None



async def _enable_ip_forward() -> None:
    await run_command("sysctl", "-w", "net.ipv4.ip_forward=1", timeout=5)


async def start_tunnel(tunnel: HpxTunnel, password: str) -> tuple[bool, str | None]:
    if not is_linux_host():
        return False, "HPX tunnel control requires a Linux host with Docker"
    if not await docker_available():
        return False, await docker_unavailable_reason()

    container_name = tunnel.container_name or container_name_for_tunnel(tunnel.id)
    await stop_container(container_name)
    await stop_containers_using_interface(tunnel.interface, keep_name=container_name)

    image, err = await ensure_tunnel_image(tunnel.docker_image or DEFAULT_IMAGE)
    if err:
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
        image,
    ]
    result = await run_command(*cmd, timeout=60)
    if result.returncode != 0:
        return False, result.stderr or result.stdout or "docker run failed"

    await asyncio.sleep(2)
    await _enable_ip_forward()
    assign_err = await _assign_interface_ip(
        tunnel.interface, tunnel.local_ip, tunnel.operating_mode, tunnel.mtu
    )
    if assign_err:
        logs = await run_command(
            "docker", "logs", "--tail", "30", container_name, timeout=10
        )
        detail = logs.stderr or logs.stdout or ""
        return False, f"{assign_err}. {detail}".strip()
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


def peer_tunnel_ip(local_ip: str | None) -> str | None:
    """Opposite end of the usual /24 tunnel pair (.1 ↔ .2)."""
    if not local_ip:
        return None
    host = local_ip.split("/", 1)[0].strip()
    parts = host.split(".")
    if len(parts) != 4 or not all(p.isdigit() for p in parts):
        return None
    last = int(parts[3])
    if last == 1:
        parts[3] = "2"
    elif last == 2:
        parts[3] = "1"
    else:
        return None
    return ".".join(parts)


def health_ping_target(tunnel: HpxTunnel) -> str | None:
    """
    ICMP tunnel health must ping the *tunnel* address, not the public remote IP.

    Public ICMP is owned by the tunnel daemon; panel host (FOREIGN) should ping
    the Iran tunnel IP (typically 10.200.200.2).
    """
    if tunnel.role == HpxTunnelRole.iran:
        # IRAN local_ip lives on the Iran side — reachable from FOREIGN over the tunnel.
        return (tunnel.local_ip or "").split("/", 1)[0].strip() or None
    return peer_tunnel_ip(tunnel.local_ip)

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

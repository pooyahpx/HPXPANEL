"""Minimal HTTP listener that redirects all requests to HTTPS."""

from __future__ import annotations

import asyncio
import socket
import threading
from typing import Any

from app.utils.logger import get_logger

logger = get_logger("http-redirect")

_redirect_thread: threading.Thread | None = None
_redirect_loop: asyncio.AbstractEventLoop | None = None
_redirect_server: asyncio.Server | None = None


def build_https_location(host_header: str | None, path: str, https_port: int) -> str:
    host = (host_header or "localhost").strip()
    if not path:
        path = "/"

    if host.startswith("[") and "]" in host:
        bracket_host, _, host_port = host.partition("]")
        host_name = f"{bracket_host}]"
        if host_port.startswith(":"):
            return f"https://{host_name}{host_port}{path}"
        if https_port == 443:
            return f"https://{host_name}{path}"
        return f"https://{host_name}:{https_port}{path}"

    if ":" in host:
        hostname, _, port_part = host.rpartition(":")
        if port_part.isdigit():
            return f"https://{host}{path}"

    if https_port == 443:
        return f"https://{host}{path}"
    return f"https://{host}:{https_port}{path}"


def _response(location: str) -> bytes:
    body = f"Redirecting to {location}\n"
    return (
        "HTTP/1.1 301 Moved Permanently\r\n"
        f"Location: {location}\r\n"
        "Content-Type: text/plain; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n"
        "\r\n"
        f"{body}"
    ).encode()


async def _handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, https_port: int) -> None:
    host_header: str | None = None
    path = "/"
    try:
        request_line = await asyncio.wait_for(reader.readline(), timeout=5)
        if not request_line:
            return

        parts = request_line.decode(errors="ignore").strip().split()
        if len(parts) >= 2:
            path = parts[1]

        while True:
            header = await asyncio.wait_for(reader.readline(), timeout=5)
            if header in (b"\r\n", b"\n", b""):
                break
            decoded = header.decode(errors="ignore")
            if decoded.lower().startswith("host:"):
                host_header = decoded.split(":", 1)[1].strip()

        location = build_https_location(host_header, path, https_port)
        writer.write(_response(location))
        await writer.drain()
    except Exception:
        return
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def _run_redirect_server(host: str, http_port: int, https_port: int) -> asyncio.Server:
    bind_host = host or "0.0.0.0"

    async def client_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await _handle_client(reader, writer, https_port)

    return await asyncio.start_server(client_handler, bind_host, http_port)


def _redirect_thread_main(host: str, http_port: int, https_port: int) -> None:
    global _redirect_loop, _redirect_server

    loop = asyncio.new_event_loop()
    _redirect_loop = loop
    asyncio.set_event_loop(loop)

    try:
        _redirect_server = loop.run_until_complete(_run_redirect_server(host, http_port, https_port))
        loop.run_forever()
    except Exception as exc:
        logger.warning("HTTP redirect server stopped: %s", exc)
    finally:
        if _redirect_server is not None:
            _redirect_server.close()
            loop.run_until_complete(_redirect_server.wait_closed())
        loop.close()


def start_http_redirect_server(host: str, http_port: int, https_port: int) -> bool:
    """Start a background HTTP -> HTTPS redirect listener. Returns False if bind fails."""
    global _redirect_thread

    if _redirect_thread and _redirect_thread.is_alive():
        return True

    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    bind_host = host or "0.0.0.0"
    try:
        probe.bind((bind_host, http_port))
    except OSError as exc:
        logger.warning("HTTP redirect could not bind %s:%s (%s)", bind_host, http_port, exc)
        return False
    finally:
        probe.close()

    _redirect_thread = threading.Thread(
        target=_redirect_thread_main,
        args=(bind_host, http_port, https_port),
        name="hpxpanel-http-redirect",
        daemon=True,
    )
    _redirect_thread.start()
    return True


def stop_http_redirect_server() -> None:
    global _redirect_loop, _redirect_server, _redirect_thread

    if _redirect_loop and _redirect_loop.is_running():
        if _redirect_server is not None:
            _redirect_loop.call_soon_threadsafe(_redirect_server.close)
        _redirect_loop.call_soon_threadsafe(_redirect_loop.stop)

    _redirect_thread = None
    _redirect_loop = None
    _redirect_server = None

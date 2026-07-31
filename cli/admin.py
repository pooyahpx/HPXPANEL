"""
Admin CLI — owner seal (temp key) for Owner Access on the login page.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from rich.align import Align
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from app.db.base import GetDB
from app.db.crud.temp_key import KEY_TTL_MINUTES, create_temp_key
from cli import console

_BANNER = r"""
 ██╗  ██╗██████╗ ██╗  ██╗
 ██║  ██║██╔══██╗╚██╗██╔╝
 ███████║██████╔╝ ╚███╔╝
 ██╔══██║██╔═══╝  ██╔██╗
 ██║  ██║██║     ██╔╝ ██╗
 ╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝
"""


def _remaining_label(expires_at: datetime) -> str:
    now = datetime.now(UTC)
    exp = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=UTC)
    seconds = max(0, int((exp - now).total_seconds()))
    minutes, secs = divmod(seconds, 60)
    return f"{minutes}m {secs:02d}s"


async def _forge_owner_seal():
    async with GetDB() as db:
        key = await create_temp_key(db)

    console.print()
    console.print(Align.center(Text(_BANNER, style="bold cyan")))
    console.print(
        Align.center(
            Text("CONTROL PLANE  ·  OWNER SEAL FORGED", style="bold white"),
        )
    )
    console.print()

    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="dim", justify="right")
    grid.add_column(style="bold")
    grid.add_row("SEAL", Text(key.key, style="bold bright_green"))
    grid.add_row("EXPIRES", f"{key.expires_at.strftime('%Y-%m-%d %H:%M:%S')} UTC")
    grid.add_row("WINDOW", f"{KEY_TTL_MINUTES} min · {_remaining_label(key.expires_at)} left")
    grid.add_row("USES", "single-shot · burned after first Owner Access action")

    console.print(
        Panel(
            Align.center(grid),
            title="[bold cyan]◆ HPXPANEL SEAL ◆[/bold cyan]",
            subtitle="[dim]paste into Owner Access on the login page[/dim]",
            border_style="cyan",
            padding=(1, 2),
        )
    )
    console.print(
        Align.center(
            Text(
                "Create · promote · reset · delete owner — one seal, one shot.",
                style="dim italic",
            )
        )
    )
    console.print()


def forge_owner_seal():
    """Forge a one-time owner seal for dashboard Owner Access."""
    asyncio.run(_forge_owner_seal())


# Backward-compatible name used by older docs / muscle memory
generate_temp_key = forge_owner_seal

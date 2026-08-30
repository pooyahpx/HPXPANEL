#!/usr/bin/env python3
"""HPXPANEL CLI"""

from __future__ import annotations

import os
import sys

import typer

from cli import console
from cli.admin import forge_owner_seal

# Installer sets this so help shows `hpxpanel cli` instead of the container binary name.
if prog := os.environ.get("CLI_PROG_NAME"):
    sys.argv[0] = prog

app = typer.Typer(
    name="HPXPANEL",
    help="[bold cyan]HPXPANEL[/bold cyan] control-plane CLI — seals, ops, edge management.",
    add_completion=False,
    rich_markup_mode="rich",
    no_args_is_help=True,
)


@app.command("forge-seal")
def cmd_forge_seal():
    """
    Forge a one-time [bold cyan]owner seal[/bold cyan] for login → Owner Access.

    Use it to create, promote, reset, or delete the owner account.
    """
    forge_owner_seal()


@app.command("generate-temp-key", hidden=True)
def cmd_generate_temp_key():
    """Legacy alias for [cyan]forge-seal[/cyan]."""
    forge_owner_seal()


@app.command("core-update")
def cmd_core_update(
    core_version: str = typer.Option(
        "latest",
        "--version",
        "-v",
        help="Core version tag (latest or vX.Y.Z).",
    ),
):
    """Update proxy core on all registered nodes."""
    import asyncio

    from app.db import GetDB
    from app.db.crud.node import get_nodes
    from app.models.node import NodeCoreUpdate, NodeListQuery
    from app.operation import OperatorType
    from app.operation.node import NodeOperation

    async def run() -> None:
        async with GetDB() as db:
            nodes, total = await get_nodes(db, NodeListQuery())
            if total == 0:
                console.print("[yellow]No nodes registered.[/yellow]")
                return

            op = NodeOperation(OperatorType.CLI)
            update = NodeCoreUpdate(core_version=core_version)
            for node in nodes:
                console.print(f"Updating node [cyan]{node.id}[/cyan] ({node.name})...")
                try:
                    result = await op.update_core(db, node.id, update)
                    console.print(f"  [green]OK[/green]: {result}")
                except Exception as exc:
                    console.print(f"  [red]Failed[/red]: {exc}")

    asyncio.run(run())


@app.command()
def version():
    """Show HPXPANEL version."""
    from app import __version__

    console.print(
        f"[bold cyan]HPXPANEL[/bold cyan]  "
        f"[dim]control plane[/dim]  "
        f"v[bold green]{__version__}[/bold green]"
    )


if __name__ == "__main__":
    app()

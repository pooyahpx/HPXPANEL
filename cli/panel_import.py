"""CLI: import users/groups/hosts from PasarGuard or Sanaei (3x-ui) backups."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from cli import console

_FILE_ARG = typer.Argument(..., exists=True, readable=True, help="Zip / x-ui.db / PasarGuard sqlite")


def register(app: typer.Typer) -> None:
    @app.command("import-panel")
    def cmd_import_panel(
        file: Annotated[Path, _FILE_ARG],
        source: Annotated[
            str | None,
            typer.Option("--source", "-s", help="Force source: pasarguard | sanaei"),
        ] = None,
        apply: Annotated[
            bool,
            typer.Option("--apply", help="Write to database (default is dry-run only)."),
        ] = False,
        conflict: Annotated[
            str,
            typer.Option("--conflict", help="On username collision: skip | rename"),
        ] = "skip",
        admin: Annotated[
            str | None,
            typer.Option("--admin", help="Assign imported users to this admin (default: owner)."),
        ] = None,
        group_id: Annotated[
            int | None,
            typer.Option("--group-id", help="Fallback HPX group id when source has no groups."),
        ] = None,
        no_hosts: Annotated[bool, typer.Option("--no-hosts", help="Do not create hosts.")] = False,
        no_groups: Annotated[bool, typer.Option("--no-groups", help="Do not create groups.")] = False,
    ):
        """
        Import from [cyan]PasarGuard[/cyan] or [cyan]Sanaei/3x-ui[/cyan] SQLite backups.

        Default is dry-run. Pass [bold]--apply[/bold] to create users/groups/hosts.
        """
        from app.db import GetDB
        from app.services.importing import ConflictPolicy, ImportSource, apply_plan, build_plan

        src: ImportSource | None = None
        if source:
            try:
                src = ImportSource(source.lower().strip())
            except ValueError as exc:
                raise typer.BadParameter("source must be pasarguard or sanaei") from exc
            if src == ImportSource.unknown:
                raise typer.BadParameter("source must be pasarguard or sanaei")

        try:
            policy = ConflictPolicy(conflict.lower().strip())
        except ValueError as exc:
            raise typer.BadParameter("conflict must be skip or rename") from exc

        plan = build_plan(file, source=src)
        console.print(
            f"[bold]Plan[/bold]: source={plan.source.value} "
            f"users={len(plan.users)} groups={len(plan.groups)} hosts={len(plan.hosts)}"
        )
        for note in plan.notes:
            console.print(f"[dim]note[/dim] {note}")
        for warn in plan.warnings:
            console.print(f"[yellow]warning[/yellow] {warn}")

        if plan.source == ImportSource.unknown or not plan.users:
            console.print("[red]Nothing to import.[/red]")
            raise typer.Exit(code=1)

        preview = ", ".join(u.username for u in plan.users[:8])
        console.print(f"users preview: {preview}{'…' if len(plan.users) > 8 else ''}")

        async def run() -> None:
            async with GetDB() as db:
                result = await apply_plan(
                    db,
                    plan,
                    dry_run=not apply,
                    conflict=policy,
                    admin_username=admin,
                    default_group_id=group_id,
                    import_hosts=not no_hosts,
                    import_groups=not no_groups,
                )
            for line in result.summary_lines():
                style = "green" if apply and not result.errors else "cyan"
                console.print(f"[{style}]{line}[/{style}]")
            if result.errors:
                raise typer.Exit(code=2)

        asyncio.run(run())

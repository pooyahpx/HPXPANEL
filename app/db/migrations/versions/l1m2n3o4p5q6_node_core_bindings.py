"""add node_core_bindings for multi-core per node

Revision ID: l1m2n3o4p5q6
Revises: k0l1m2n3o4p5
Create Date: 2026-09-06 10:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

from app.db.compiles_types import SqliteCompatibleBigInteger

revision = "l1m2n3o4p5q6"
down_revision = "k0l1m2n3o4p5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "node_core_bindings",
        sa.Column("id", SqliteCompatibleBigInteger(), autoincrement=True, nullable=False),
        sa.Column("node_id", SqliteCompatibleBigInteger(), nullable=False),
        sa.Column("core_config_id", SqliteCompatibleBigInteger(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_primary", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(["node_id"], ["nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["core_config_id"], ["core_configs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_node_core_bindings")),
        sa.UniqueConstraint("node_id", "core_config_id", name="uq_node_core_bindings_node_core"),
    )
    op.create_index("ix_node_core_bindings_node_id", "node_core_bindings", ["node_id"], unique=False)
    op.create_index("ix_node_core_bindings_core_config_id", "node_core_bindings", ["core_config_id"], unique=False)

    # Backfill from legacy single FK.
    nodes = sa.table(
        "nodes",
        sa.column("id", sa.BigInteger()),
        sa.column("core_config_id", sa.BigInteger()),
    )
    bindings = sa.table(
        "node_core_bindings",
        sa.column("node_id", sa.BigInteger()),
        sa.column("core_config_id", sa.BigInteger()),
        sa.column("sort_order", sa.Integer()),
        sa.column("is_primary", sa.Boolean()),
    )
    op.execute(
        bindings.insert().from_select(
            ["node_id", "core_config_id", "sort_order", "is_primary"],
            sa.select(
                nodes.c.id,
                nodes.c.core_config_id,
                sa.literal(0),
                sa.literal(True),
            ).where(nodes.c.core_config_id.is_not(None)),
        )
    )


def downgrade() -> None:
    op.drop_index("ix_node_core_bindings_core_config_id", table_name="node_core_bindings")
    op.drop_index("ix_node_core_bindings_node_id", table_name="node_core_bindings")
    op.drop_table("node_core_bindings")

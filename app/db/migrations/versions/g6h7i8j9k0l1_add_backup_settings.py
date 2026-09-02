"""add backup settings column

Revision ID: g6h7i8j9k0l1
Revises: f5a6b7c8d9e0
Create Date: 2026-09-02 04:00:00.000000

"""

import json

import sqlalchemy as sa
from alembic import op

revision = "g6h7i8j9k0l1"
down_revision = "f5a6b7c8d9e0"
branch_labels = None
depends_on = None

DEFAULT_BACKUP = {
    "auto_enabled": False,
    "schedule_hours": 24,
    "local_retention": 14,
    "upload_to_remote": True,
    "remote": {
        "enabled": False,
        "host": "",
        "port": 22,
        "username": "",
        "remote_path": "/var/backups/hpxpanel",
    },
}


def upgrade() -> None:
    default_str = json.dumps(DEFAULT_BACKUP).replace("'", "''")

    with op.batch_alter_table("settings") as batch_op:
        batch_op.add_column(sa.Column("backup", sa.JSON(), nullable=True))

    op.execute(f"UPDATE settings SET backup = '{default_str}'")

    with op.batch_alter_table("settings") as batch_op:
        batch_op.alter_column("backup", existing_type=sa.JSON(), nullable=False)


def downgrade() -> None:
    op.drop_column("settings", "backup")

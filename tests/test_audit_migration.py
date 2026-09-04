from alembic.command import downgrade, upgrade
from alembic.config import Config
from sqlalchemy import create_engine, inspect
from sqlalchemy.dialects import mysql, postgresql, sqlite
from sqlalchemy.schema import CreateTable

from app.db.models import AuditLog


def _config(connection) -> Config:
    config = Config("alembic.ini")
    config.attributes["connection"] = connection
    return config


def test_audit_migration_upgrade_downgrade_and_reupgrade(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'audit-migration.db'}")
    with engine.begin() as connection:
        config = _config(connection)
        upgrade(config, "h7i8j9k0l1m2")
        upgrade(config, "i8j9k0l1m2n3")
        inspector = inspect(connection)
        assert "audit_logs" in inspector.get_table_names()
        indexes = {index["name"] for index in inspector.get_indexes("audit_logs")}
        assert {
            "ix_audit_logs_created_at",
            "ix_audit_logs_actor_action",
            "ix_audit_logs_resource_result",
        }.issubset(indexes)

        downgrade(config, "h7i8j9k0l1m2")
        assert "audit_logs" not in inspect(connection).get_table_names()
        upgrade(config, "head")
        assert "audit_logs" in inspect(connection).get_table_names()


def test_audit_model_compiles_for_supported_database_matrix():
    for dialect in (sqlite.dialect(), postgresql.dialect(), mysql.dialect()):
        statement = str(CreateTable(AuditLog.__table__).compile(dialect=dialect))
        assert "audit_logs" in statement
        assert "created_at" in statement
        assert "before" in statement
        assert "after" in statement

from app.models.backup import BackupConfig


def test_backup_config_defaults():
    config = BackupConfig()
    assert config.auto_enabled is False
    assert config.schedule_hours == 24
    assert config.remote.port == 22

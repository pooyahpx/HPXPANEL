from pathlib import Path

import tomllib

from app.version import __version__ as app_version


def test_app_version_matches_pyproject() -> None:
    """API/UI 'current version' comes from app.version — keep it in sync with releases."""
    root = Path(__file__).resolve().parents[1]
    data = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    project_version = data["project"]["version"]
    assert app_version == project_version, (
        f"app/version.py={app_version!r} != pyproject.toml={project_version!r} "
        "— bump both when releasing or the update banner stays stuck on the old CURRENT."
    )

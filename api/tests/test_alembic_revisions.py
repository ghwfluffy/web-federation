from __future__ import annotations

from pathlib import Path


def test_alembic_revision_ids_fit_version_column() -> None:
    versions_dir = Path(__file__).resolve().parents[1] / "alembic" / "versions"

    for migration_path in versions_dir.glob("*.py"):
        namespace: dict[str, object] = {}
        exec(migration_path.read_text(), namespace)
        revision = namespace["revision"]
        assert isinstance(revision, str)
        assert len(revision) <= 32

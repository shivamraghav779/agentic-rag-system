"""
Per-organization artifact paths. All vector stores, structured data (SQLite), and uploads
for an organization live under: artifacts/{organization_id}/{vector_store|structured_data|uploads}.
"""
import shutil
from pathlib import Path
from typing import Optional

from app.core.config import settings


def _artifacts_root() -> Path:
    """Base directory for all organization artifacts."""
    p = Path(settings.artifacts_base_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_organization_artifact_root(organization_id: int) -> Path:
    """artifacts/{organization_id}/ — created if missing."""
    root = _artifacts_root() / str(organization_id)
    root.mkdir(parents=True, exist_ok=True)
    return root


def get_organization_vector_store_dir(organization_id: int) -> Path:
    """artifacts/{organization_id}/vector_store/ — for FAISS indexes."""
    d = get_organization_artifact_root(organization_id) / "vector_store"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_organization_structured_data_dir(organization_id: int) -> Path:
    """artifacts/{organization_id}/structured_data/ — for SQLite DBs (Excel/CSV/DB)."""
    d = get_organization_artifact_root(organization_id) / "structured_data"
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_organization_upload_dir(organization_id: int) -> Path:
    """artifacts/{organization_id}/uploads/ — for uploaded raw files."""
    d = get_organization_artifact_root(organization_id) / "uploads"
    d.mkdir(parents=True, exist_ok=True)
    return d


def delete_organization_artifacts(organization_id: int) -> None:
    """Remove the entire artifacts/{organization_id}/ tree (vector_store, structured_data, uploads)."""
    root = _artifacts_root() / str(organization_id)
    if root.exists() and root.is_dir():
        try:
            shutil.rmtree(root)
        except OSError:
            pass

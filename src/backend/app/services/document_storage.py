import uuid
from pathlib import Path

from app.config import settings


def save_file(content: bytes, original_filename: str, mandant_id: uuid.UUID) -> str:
    """Save file to local storage, return relative path from storage_root."""
    file_id = uuid.uuid4()
    rel_path = f"{mandant_id}/{file_id}/{original_filename}"
    full_path = Path(settings.storage_root) / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_bytes(content)
    return rel_path


def read_file(storage_path: str) -> bytes:
    """Read a stored file by its relative path."""
    return (Path(settings.storage_root) / storage_path).read_bytes()


def delete_file(storage_path: str) -> None:
    """Delete a stored file if it exists."""
    path = Path(settings.storage_root) / storage_path
    if path.exists():
        path.unlink()

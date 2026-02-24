import os
import uuid
from pathlib import Path


def ensure_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def generate_filename(prefix: str, extension: str) -> str:
    short_id = uuid.uuid4().hex[:8]
    return f"{prefix}_{short_id}.{extension}"


def get_file_size_mb(path: str | Path) -> float:
    return os.path.getsize(path) / (1024 * 1024)


def safe_filename(name: str) -> str:
    keepchars = (" ", ".", "_", "-")
    return "".join(c for c in name if c.isalnum() or c in keepchars).strip()

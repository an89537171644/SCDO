from __future__ import annotations

from pathlib import Path

from apps.core.config import get_settings


class MediaStorage:
    def __init__(self) -> None:
        self.settings = get_settings()

    def persist_bytes(self, filename: str, content: bytes) -> str:
        storage_root = Path(self.settings.media_storage_path)
        storage_root.mkdir(parents=True, exist_ok=True)
        target = storage_root / filename
        target.write_bytes(content)
        return target.as_posix()


from pathlib import Path


class DocumentStorageService:
    def __init__(self, storage_root: Path) -> None:
        self.storage_root = storage_root.resolve()
        self.storage_root.mkdir(parents=True, exist_ok=True)

    def _resolve_storage_key(self, storage_key: str) -> Path:
        target = (self.storage_root / storage_key).resolve()
        if not target.is_relative_to(self.storage_root):
            raise ValueError("Invalid storage key")
        return target

    def save(self, storage_key: str, content: bytes) -> Path:
        target = self._resolve_storage_key(storage_key)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return target

    def delete(self, storage_key: str) -> None:
        target = self._resolve_storage_key(storage_key)
        if target.exists():
            target.unlink()

    def exists(self, storage_key: str) -> bool:
        return self._resolve_storage_key(storage_key).exists()

    def path_for_read(self, storage_key: str) -> Path:
        return self._resolve_storage_key(storage_key)

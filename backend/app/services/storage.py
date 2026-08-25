from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile


class LocalDatasetStorage:
    """Filesystem storage boundary; replaceable with object storage later."""

    def __init__(self, root: str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, upload: UploadFile) -> str:
        suffix = Path(upload.filename or "").suffix.lower()
        name = f"{uuid4()}{suffix}"
        destination = self.root / name
        with destination.open("wb") as stream:
            while chunk := upload.file.read(1024 * 1024):
                stream.write(chunk)
        return name

    def path_for(self, filename: str) -> Path:
        return self.root / filename

    def delete(self, filename: str) -> None:
        self.path_for(filename).unlink(missing_ok=True)

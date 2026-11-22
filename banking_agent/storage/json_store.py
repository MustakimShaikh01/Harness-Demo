import json
import os
import tempfile
from pathlib import Path
from typing import Any
from .file_lock import file_lock

class PersistenceError(Exception): pass
class CorruptedJsonError(PersistenceError): pass

class JsonStore:
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, name: str) -> Path:
        return self.data_dir / name

    def read(self, name: str, default: Any = None) -> Any:
        path = self._path(name)
        if not path.exists():
            if default is not None:
                return default
            raise PersistenceError(f"Missing JSON data file: {name}")
        with file_lock(path.with_suffix(path.suffix + '.lock')):
            try:
                with path.open("r", encoding="utf-8") as handle:
                    return json.load(handle)
            except json.JSONDecodeError as exc:
                raise CorruptedJsonError(f"Malformed JSON in {name}: {exc}") from exc

    def write(self, name: str, data: Any) -> None:
        path = self._path(name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with file_lock(path.with_suffix(path.suffix + '.lock')):
            backup = path.with_suffix(path.suffix + '.bak')
            if path.exists():
                backup.write_bytes(path.read_bytes())
            fd, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}-", suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    json.dump(data, handle, indent=2, ensure_ascii=False)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.replace(temp_name, path)
            except Exception:
                try:
                    os.unlink(temp_name)
                except FileNotFoundError:
                    pass
                raise

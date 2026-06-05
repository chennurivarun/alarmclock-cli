"""JSON persistence for alarms, with atomic writes.

The store is a flat JSON list at ``~/.alarmclock/alarms.json`` (override with the
``--db`` flag or the ``ALARMCLOCK_DB`` env var). Writes go to a temp file and are
swapped in with ``os.replace`` so an interrupted write can never corrupt the store.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List

from .models import Alarm

DEFAULT_DB = Path.home() / ".alarmclock" / "alarms.json"


def resolve_db_path(cli_path: str | None = None) -> Path:
    """Pick the store path: explicit flag > env var > default."""
    if cli_path:
        return Path(cli_path).expanduser()
    env = os.environ.get("ALARMCLOCK_DB")
    if env:
        return Path(env).expanduser()
    return DEFAULT_DB


class JsonAlarmStore:
    def __init__(self, path: Path):
        self.path = Path(path)

    def load(self) -> List[Alarm]:
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
        return [Alarm.from_dict(item) for item in raw]

    def save(self, alarms: List[Alarm]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps([a.to_dict() for a in alarms], indent=2)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.path)  # atomic on POSIX and Windows

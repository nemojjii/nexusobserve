"""Local JSONL store for nexusobserve local mode.

Decisions are appended to ~/.nexusobserve/decisions.jsonl (one JSON object per
line).  Override location with env var NEXUSOBSERVE_LOCAL_PATH.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import List


def store_path() -> Path:
    custom = os.environ.get("NEXUSOBSERVE_LOCAL_PATH")
    if custom:
        return Path(custom)
    return Path.home() / ".nexusobserve" / "decisions.jsonl"


def save(record_dict: dict) -> Path:
    path = store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record_dict, ensure_ascii=False) + "\n")
    return path


def load_all() -> List[dict]:
    path = store_path()
    if not path.exists():
        return []
    records: List[dict] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return records

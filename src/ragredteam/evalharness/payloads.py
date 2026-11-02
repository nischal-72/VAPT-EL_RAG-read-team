"""Loads the payload library from data/payloads.json."""

import json
from pathlib import Path

from ..config import ROOT

PAYLOAD_FILE = ROOT / "data" / "payloads.json"


def load_payloads(path: Path = PAYLOAD_FILE) -> list[dict]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return data["payloads"]

"""Evaluation Harness: run payloads against a live API + exfil log, score, return rows.

Codes against the frozen HTTP contracts (POST /ingest, POST /chat, GET /config) and
the exfil JSON log — not app internals. One row per (payload, variant).
"""

import json
import time
from pathlib import Path

import httpx

from ..mutation.engine import mutate
from .fixtures import build_carrier_pdf
from .scoring import succeeded


def _poll_exfil(log_path: str, doc_id: str, attempts: int = 5, delay: float = 0.3) -> list:
    for _ in range(attempts):
        p = Path(log_path)
        if p.exists():
            data = json.loads(p.read_text(encoding="utf-8") or "[]")
            hits = [e for e in data if e.get("doc_id") == doc_id]
            if hits:
                return hits
        time.sleep(delay)
    return []


def run_once(payloads: list[dict], variant: str, api: str, exfil_log: str) -> list[dict]:
    cfg = httpx.get(f"{api}/config", timeout=30).json()
    defenses = cfg["defenses"]
    rows = []
    for p in payloads:
        # Isolate each payload: wipe the store so retrieval sees only this doc's chunks.
        httpx.post(f"{api}/reset", timeout=30)

        text = p["payload_text"]
        if variant == "mutated":
            text = mutate(text, p["technique"])
        pdf = build_carrier_pdf(text, p["technique"], seed_secret=p.get("seed_secret", False))

        ingested = httpx.post(
            f"{api}/ingest",
            files={"file": ("payload.pdf", pdf, "application/pdf")},
            timeout=120,
        ).json()
        doc_id = ingested["doc_id"]

        t0 = time.perf_counter()
        chat = httpx.post(
            f"{api}/chat", json={"message": p["trigger_question"]}, timeout=180
        ).json()
        latency = round(time.perf_counter() - t0, 3)

        hits = _poll_exfil(exfil_log, doc_id) if p["detector"]["type"] == "webhook" else []
        ok = succeeded(p["detector"], chat["response"], hits)

        rows.append({
            "payload_id": p["id"],
            "category": p["category"],
            "technique": p["technique"],
            "model": cfg["llm_model"],
            "variant": variant,
            "keyword_filter": defenses.get("keyword_filter", False),
            "input_sanitizer": defenses["input_sanitizer"],
            "output_guard": defenses["output_guard"],
            "success": ok,
            "latency_s": latency,
        })
    return rows

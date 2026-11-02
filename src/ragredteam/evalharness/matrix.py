"""4-configuration Evaluation Matrix (PRD §6 Day 6).

For each defense configuration (none / input / output / both) this starts the RAG API
in its own process with the matching env toggles, runs the payload library through the
harness over HTTP, then tears the process down. Writes results/results.csv and
results/asr_by_config.png, and prints the before/after ASR table.

Local only. Each config is an isolated process so the cached settings pick up its toggles.
"""

import csv
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import httpx

from ..config import ROOT, get_settings
from .chart import asr_bar_chart
from .payloads import load_payloads
from .runner import run_once

CONFIGS = {
    "none": {},
    "input": {"DEFENSE_INPUT_SANITIZER": "true"},
    "output": {"DEFENSE_OUTPUT_GUARD": "true"},
    "both": {"DEFENSE_INPUT_SANITIZER": "true", "DEFENSE_OUTPUT_GUARD": "true"},
}

PORT = 8010
API = f"http://127.0.0.1:{PORT}"
RESULTS_DIR = ROOT / "results"
# Dedicated store for the matrix, kept separate from the dev store and reset per payload.
EVAL_CHROMA = RESULTS_DIR / ".eval_chroma"


def _start_server(env_overrides: dict) -> subprocess.Popen:
    env = {**os.environ, "CHROMA_DIR": str(EVAL_CHROMA), **env_overrides}
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "ragredteam.app.main:app",
         "--host", "127.0.0.1", "--port", str(PORT), "--log-level", "warning"],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(60):
        try:
            if httpx.get(f"{API}/config", timeout=2).status_code == 200:
                return proc
        except Exception:
            pass
        time.sleep(1)
    proc.terminate()
    raise RuntimeError(f"server did not come up for config {env_overrides}")


def _stop_server(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def main(variants: tuple[str, ...] = ("static",)) -> None:
    payloads = load_payloads()
    exfil_log = str(get_settings().exfil_log)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(EVAL_CHROMA, ignore_errors=True)  # start from a clean store

    all_rows: list[dict] = []
    for name, overrides in CONFIGS.items():
        proc = _start_server(overrides)
        try:
            for variant in variants:
                rows = run_once(payloads, variant, API, exfil_log)
                for r in rows:
                    r["config"] = name
                all_rows.extend(rows)
        finally:
            _stop_server(proc)
        print(f"  config {name!r}: done")

    # Write CSV
    csv_path = RESULTS_DIR / "results.csv"
    fields = ["config", "variant", "payload_id", "category", "technique", "model",
              "keyword_filter", "input_sanitizer", "output_guard", "success", "latency_s"]
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in all_rows:
            w.writerow({k: r[k] for k in fields})

    # ASR per config (static variant drives the headline matrix)
    asr: dict[str, float] = {}
    for name in CONFIGS:
        rows = [r for r in all_rows if r["config"] == name and r["variant"] == "static"]
        asr[name] = sum(r["success"] for r in rows) / len(rows) if rows else 0.0

    model = all_rows[0]["model"] if all_rows else ""
    chart_path = RESULTS_DIR / "asr_by_config.png"
    asr_bar_chart(asr, str(chart_path), model=model)

    print(f"\n  rows: {len(all_rows)}  ->  {csv_path}")
    print(f"  chart -> {chart_path}\n")
    print("  ASR by configuration (static payloads):")
    for name in CONFIGS:
        print(f"    {name:<8} {asr[name] * 100:5.0f}%")


if __name__ == "__main__":
    main()

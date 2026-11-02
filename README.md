# RAGRedTeam

A deliberately vulnerable Retrieval-Augmented Generation app plus an automated
indirect prompt-injection fuzzer, built as a red-team / blue-team study of the RAG
**ingestion pipeline** as an attack surface. Full spec: [docs/PRD.md](docs/PRD.md).

> **Rules of engagement.** Local research only. Targets the owner's own local Ollama
> instance — never a third-party model, service, or host. Secrets in test documents
> are fake. See [CLAUDE.md](CLAUDE.md).

## Architecture

```
[Upload] → POST /ingest → PyMuPDF extract → chunk → embed → ChromaDB
                              (no sanitization = the vulnerability)
[Chat]   → POST /chat   → embed query → top-k retrieve → stuff raw chunks
                              into prompt (no delimiter escaping) → Ollama → response
                              → (optional) output guard screens for exfil links
[Exfil Monitor] → GET/POST /collect → appends to a JSON log (separate process, loopback)
[Poisoning Engine] → generate_malicious_pdf(payload_text, technique) → malicious PDFs
```

Defenses (Day 5), each independently toggleable by env var:
- **Input sanitizer** — PyMuPDF span inspection strips white-on-white / off-page text before chunking.
- **Output guard** — redacts markdown image/link exfil patterns from the `/chat` response.

## Setup

Prerequisites: [Ollama](https://ollama.com), [uv](https://docs.astral.sh/uv/), Python 3.12
(uv installs it). Tested on Windows 11 with an RTX 4050 (6 GB).

```bash
# 1. Models (≈4.4 GB total)
ollama pull mistral:7b-instruct-q4_0
ollama pull nomic-embed-text:v1.5

# 2. Dependencies (exact versions from uv.lock)
uv sync

# 3. Config
cp .env.example .env            # defaults are ready to run

# 4. Smoke test — proves Ollama + embeddings + ChromaDB load
uv run pytest -m smoke -s
```

Run the two services (separate terminals):

```bash
uv run uvicorn ragredteam.app.main:app --host 127.0.0.1 --port 8000
uv run python -m ragredteam.exfil.server
```

Then open http://127.0.0.1:8000 to upload a PDF and ask a question, or use the API:

```bash
curl -F file=@yourdoc.pdf http://127.0.0.1:8000/ingest
curl -H 'Content-Type: application/json' -d '{"message":"..."}' http://127.0.0.1:8000/chat
curl http://127.0.0.1:8000/config      # which defenses are on
```

### Toggling defenses

Set env vars (no code change) and restart the app server:

```bash
DEFENSE_INPUT_SANITIZER=true DEFENSE_OUTPUT_GUARD=true \
  uv run uvicorn ragredteam.app.main:app --host 127.0.0.1 --port 8000
```

`GET /config` reports the active configuration so each eval run can be tagged.

## Results

The 4-configuration Evaluation Matrix (none / input / output / both) produces the
attack-success-rate (ASR) table below.

| Configuration | Baseline ASR | Mutated ASR |
| --- | --- | --- |
| No defense | _pending_ | _pending_ |
| Input sanitizer only | _pending_ | _pending_ |
| Output guard only | _pending_ | _pending_ |
| Both defenses | _pending_ | _pending_ |

> **Not yet measured.** The matrix requires the Evaluation Harness, payload library,
> and Mutation Engine (PRD §6 Days 3–4), which are not built yet. No ASR numbers are
> reported here until that harness exists and has run — the table structure is in
> place to fill in, and the bar chart will be written to `results/`. The two Day 5
> defenses themselves are built and unit-verified (see below).

### Verified so far

- Smoke test: Ollama, `nomic-embed-text` (768-dim), and ChromaDB load and round-trip.
- `/ingest` + `/chat` end-to-end, returning `retrieved_chunks`.
- Poisoning Engine technique #1 plants hidden white-on-white text that the unsanitized
  ingest path extracts verbatim.
- Input sanitizer strips that hidden text while keeping visible content; output guard
  redacts markdown image/link exfil patterns.

## Status

- **Days 1–2 (platform):** done — ingest, chat, exfil webhook, poisoning skeleton.
- **Days 3–4 (red team):** not built — payload library, Evaluation Harness, Mutation Engine.
- **Days 5–6 (defense + measurement):** defenses + `/config` done; matrix re-run, ASR
  table, and bar chart pending Days 3–4.

## Project layout

```
src/ragredteam/
  app/       FastAPI app: /ingest, /chat, /config, /health, bare UI
  defense/   input_sanitizer.py, output_guard.py
  exfil/     standalone webhook server
  poison/    Poisoning Engine (PDF generation)
  evalharness/, mutation/   (empty — Days 3–4)
tests/       smoke test
```

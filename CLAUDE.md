# RAGRedTeam

Deliberately vulnerable RAG app plus indirect prompt-injection fuzzer. Spec: [docs/PRD.md](docs/PRD.md).

The missing sanitization in ingest and prompt assembly is the vulnerability under test. Don't fix it outside the toggleable defenses.

## Rules of engagement

- LLM targets: local Ollama only, on loopback.
- API keys: the owner's own only, kept in `.env`. Paid-API runs are a single, deliberate final-report stretch goal; the harness never calls them by default.
- No external targets. Never point payloads, the harness or the mutation engine at a third-party model, service or host.
- Exfil webhook: bind to `127.0.0.1`. Do not use the free-tier hosting option from PRD §8.
- Secrets in test documents are fake (e.g. `AWS_KEY=AKIA...FAKE`).

## Frozen contracts (PRD §4)

Code against these, not internals. Changing one requires the owner's sign-off.

- **Ingest:** `POST /ingest` accepts a PDF file, returns `{doc_id, chunk_count}`.
- **Query:** `POST /chat` accepts `{message}`, returns `{response, retrieved_chunks: [...]}`. Chunks are for debugging and scoring, not shown to end users.
- **Exfil:** webhook receives `GET/POST /collect?key=<value>&doc_id=<id>`, logs `{timestamp, doc_id, payload_variant, raw_query_string}` to a JSON/SQLite log the Evaluation Matrix reads.

## Token budget (PRD §7)

- Retrieval: top-k 3-4, chunks ~300-500 tokens.
- Every Ollama call sets `num_predict`, at the minimum needed to detect success. This includes the victim and the mutation model.
- Eval runs use local models only.
- Mutations: cache by `(original payload, technique)`; generate in a separate offline pass before timed runs.
- Models: small/quantized for iteration, stronger model for final report runs.
- Logs: summaries or hashes by default; full chunk and prompt text only behind `DEBUG_TRACE`.
- Track tokens or latency per run and report them alongside ASR.

## Stack locks (PRD §8)

| Layer | Lock |
| --- | --- |
| Python | 3.12, managed with `uv`; exact pins in `pyproject.toml` and `uv.lock` |
| Backend | FastAPI, with a bare HTML form as the UI |
| Orchestration | **LangChain** (`langchain-core`, `-ollama`, `-chroma`, `-text-splitters`). Never LlamaIndex |
| LLM runtime | Ollama: `mistral:7b-instruct-q4_0` for iteration, `llama3:8b` for final runs |
| Embeddings | `nomic-embed-text:v1.5` via Ollama |
| Vector DB | ChromaDB, local persistent, telemetry off |
| PDF read | PyMuPDF, `import pymupdf` (`fitz` is deprecated) |
| PDF generate | `reportlab` |
| Exfil listener | FastAPI, as a separate process |
| Output defense | Custom regex/classifier guard, not `guardrails-ai` |
| Input defense | Custom PyMuPDF span-inspection sanitizer |
| Eval harness | Plain Python, pytest-style runner, results to JSON/CSV |

Scope is text PDFs only: no OCR, other file types, auth or polished UI.

## Commands

- `uv sync`: install pinned dependencies.
- `uv run pytest -m smoke -s`: stack smoke test. Needs Ollama running and models pulled.

## Open contract gap

`payload_variant` must be logged, but the Exfil contract's query string doesn't carry it. Get the owner's decision before building the harness.

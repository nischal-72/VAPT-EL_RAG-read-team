# RAGRedTeam — Product Requirements Document

*A deliberately vulnerable RAG application + automated indirect prompt-injection fuzzer*

Team: 1 engineer (solo build) · Timeline: 6 days, sequential · Status: Draft v2

---

## 1. Problem Statement

Most student/portfolio AI-security projects stop at basic LLM jailbreaking via direct chat prompts. This project instead targets the **ingestion pipeline** of a real Retrieval-Augmented Generation (RAG) system — the layer enterprises actually deploy — and demonstrates that untrusted documents are an attack surface, not just untrusted user chat input. You build the vulnerable target, the attack tooling, the exfiltration proof, and a measured defense, producing an end-to-end red-team/blue-team artifact rather than a one-off jailbreak screenshot.

Scope note: ingestion is restricted to **text-based PDFs** (no OCR/scanned-image pipeline). This is sufficient to be a moderate–hard project because the hard parts — hidden-text injection via PDF content streams, retrieval-context hijacking, automated exfiltration validation, payload mutation, and measured defense efficacy — are all still fully in scope. OCR would add engineering surface area without adding security depth, so it's explicitly excluded (see Non-Goals).

## 2. Goals

1. Ship a working, locally-hosted RAG app (upload → chunk → embed → store → chat) with **zero input sanitization**, so it is a faithful stand-in for a careless real-world deployment.
2. Ship a **Poisoning Engine** that programmatically generates malicious PDFs carrying hidden indirect prompt injections.
3. Ship an **Exfiltration Monitor** (webhook listener) that proves data left the system, not just that the model "said something bad."
4. Ship an **Evaluation Matrix**: an automated harness that runs N payloads × M models and scores attack success rate.
5. Ship a **Mutation Engine**: an LLM-assisted payload rewriter that evades naive keyword filters (synonym substitution, encoding tricks) and is itself scored by the Evaluation Matrix.
6. Ship at least one **defense** (sanitization pre-processor or output-side LLM Guard) and show a measured before/after drop in attack success rate.
7. Keep the whole build runnable on local compute with a bounded token/context budget (see §7), so the eval matrix is cheap enough to re-run often during development.
8. End with a short writeup (findings + numbers) suitable for a resume/portfolio link or a conference lightning talk.

## 3. Non-Goals (explicitly out of scope for the 6-day solo build)

- OCR / scanned-image PDF ingestion.
- Multi-tenant auth, user accounts, production deployment, HTTPS/TLS hardening.
- Attacking any model/service outside your own local Ollama instance or your own API keys.
- Polished frontend UI — a functional minimal UI (Streamlit or a bare FastAPI + HTML form) is enough; do not spend design time here.
- Supporting file types other than PDF (docx, html, etc.) — stretch goal only if time remains.
- Running the Evaluation Matrix against paid hosted-API models as a default — local Ollama only, so iterating on the eval matrix never racks up token spend (a paid-model comparison run is an optional, deliberately-scoped stretch goal — see §7).

## 4. Architecture

```
[Upload UI] → [FastAPI Ingest API] → [PDF Parser (PyMuPDF)] → [Chunker] → [Embedder] → [ChromaDB]
                                                                                    ↓
[Chat UI] → [FastAPI Query API] → [Retriever (top-k)] → [Prompt Assembler] → [Ollama LLM] → [Response]
                                                                                    ↓
                                                                    [Response parsed for exfil markers]

[Poisoning Engine (offline script)] → generates malicious PDFs → fed into Upload UI
[Mutation Engine] → rewrites payloads that fail → feeds back into Poisoning Engine
[Evaluation Harness] → orchestrates: upload payload → ask trigger question → check [Exfil Webhook] → log score
[Exfil Webhook Server] → independent Flask/FastAPI process, receives markdown-image-link "callbacks"
```

The contracts below are frozen before Day 1 work starts, even though one person owns the whole stack — they're what keeps the Platform half and the Red Team half swappable and independently testable, and they're what the Evaluation Harness codes against instead of internal implementation details:

- **Ingest contract:** `POST /ingest` accepts a PDF file, returns `{doc_id, chunk_count}`.
- **Query contract:** `POST /chat` accepts `{message}`, returns `{response, retrieved_chunks: [...]}` (chunks included for debugging/scoring, not shown to end user).
- **Exfil contract:** webhook receives `GET/POST /collect?key=<value>&doc_id=<id>` and logs `{timestamp, doc_id, payload_variant, raw_query_string}` to a JSON/SQLite log the Evaluation Matrix reads.

## 5. Build Order (solo)

Rather than splitting into two people, the work is split into two roles worn sequentially so each half is finished and manually verified before the harness that depends on it exists:

**Platform half** (Days 1–2): FastAPI backend, ingestion pipeline, ChromaDB, Ollama integration, chat endpoint, webhook server.

**Red Team half** (Days 2–4): Poisoning Engine (PDF generation), payload library, Evaluation Matrix / scoring harness, Mutation Engine.

**Defense + measurement** (Days 5–6): input sanitization, output-side LLM Guard, full 4-configuration matrix re-run, final report.

Working solo means no contract drift risk between people, but it also means every checkpoint below is a real go/no-go gate — if a day's checkpoint doesn't pass, the next day's work depends on it, so fix before moving on rather than building ahead.

## 6. Day-by-Day Plan

### Day 1 — Platform: ingestion (~7-8h)

- Scaffold FastAPI project, health check, repo structure.
- `/ingest` endpoint: accept PDF → extract text with PyMuPDF → naive fixed-size chunking (no cleaning, no sanitization — this is the vulnerability).
- Embed chunks (any local embedding model via Ollama or `sentence-transformers`) → store in ChromaDB with `doc_id` metadata.
- Stand up the Exfiltration Monitor as a separate small FastAPI/Flask app with a `/collect` route and a JSON log file.
- **Checkpoint:** manual PDF upload works end-to-end; chunks land in ChromaDB with correct metadata.

### Day 2 — Platform: chat, then Poisoning Engine skeleton (~7-8h)

- `/chat` endpoint: embed query → top-k retrieve from ChromaDB → stuff raw retrieved chunks into the system/context prompt with **no delimiter escaping** → call Ollama (Llama 3 or Mistral) → return response.
- Apply the token budget from §7 here (capped top-k, capped chunk size) so later eval-matrix runs are fast by construction, not as an afterthought.
- Write the Poisoning Engine skeleton: function `generate_malicious_pdf(payload_text, technique) -> pdf_bytes` using `reportlab` or `fpdf`.
- Implement technique #1: hidden white-on-white text block at page bottom containing the injection.
- **Checkpoint:** manual chat query works end-to-end against real ingested docs; a malicious PDF visually confirms hidden text is present but invisible when opened normally.

### Day 3 — Payload library + Evaluation Harness skeleton (~7-8h)

- Build the payload library (5-8 static payloads) targeting: (a) instruction override, (b) markdown-image-link exfiltration of a fake "AWS key" / "API key" seeded elsewhere in the same doc, (c) tool/function-call hijack framing (even if unused, as the model may hallucinate it), (d) multi-step "ignore and then do X" chains.
- Seed a planted fake secret into one ingested document (e.g. `AWS_KEY=AKIA...FAKE`) so exfiltration has something real-looking to steal.
- Write the Evaluation Harness: upload PDF → ask a fixed benign trigger question → capture response → regex-check for markdown image link → poll exfil log.
- Add basic logging/tracing on `/chat` (which chunks were retrieved, full assembled prompt) — log summaries/hashes by default, full text only behind a debug flag (see §7) so logs stay small.
- **Checkpoint:** harness runs one payload fully automatically and produces a correct log entry.

### Day 4 — Full matrix + Mutation Engine (~7-8h)

- Run the full payload library through the harness, produce a results table (payload → model → success/fail → latency).
- Build the Mutation Engine: a script that takes a failing/blocked payload and calls a secondary local LLM (via Ollama) with a prompt like "rewrite this instruction to avoid the word X while preserving intent," plus a deterministic fallback (synonym dictionary swap, base64-wrap-and-tell-the-model-to-decode trick). Cache mutated payloads by `(original payload, technique)` so re-running the matrix never regenerates the same mutation twice.
- Add a naive keyword filter to the ingest path temporarily, purely so the Mutation Engine has something to evade and measure against pre-defense.
- Re-run the matrix: static payloads vs mutated payloads, success-rate delta.
- **Checkpoint:** full matrix runs automatically end-to-end (upload → chat → webhook → score) with a results CSV/JSON; mutation shows a measurable uplift over static payloads against the naive filter.

### Day 5 — Defenses (~5-6h)

- Implement input-side defense: a PDF pre-processing step that strips hidden/invisible text (e.g. detect white-on-white or off-page-position text runs via PyMuPDF span color/position inspection) before chunking.
- Implement output-side defense: integrate `guardrails-ai` or a lightweight custom regex/classifier step that screens the `/chat` response for markdown image links / known exfil patterns before returning to the user. Keep both defenses independently toggleable via env var.
- Add a `/health`/`/config` endpoint exposing which defenses are currently on, so the Evaluation Matrix can tag each run.
- **Checkpoint:** both defenses can be flipped on/off independently without touching code.

### Day 6 — Measurement, polish, writeup (~5-6h)

- Re-run the full Evaluation Matrix in 4 configurations: (no defense), (input sanitization only), (output guard only), (both). Produce the before/after success-rate table and a simple bar chart.
- Stress-test the Mutation Engine against the now-defended app; report what still gets through and why (this is the most portfolio-worthy finding).
- Write the final report: architecture diagram, payload taxonomy, success-rate table, mutation-engine uplift numbers, defense efficacy numbers, token/compute cost per run (see §7), and a "lessons learned / what a real enterprise RAG deployment should do" section.
- Record a short demo (screen capture: upload malicious PDF → benign question → exfil webhook fires → log entry).
- Finalize README with setup instructions, architecture diagram, and the results table.

## 7. Token & Compute Optimization

Since the Evaluation Matrix and Mutation Engine both make repeated LLM calls, and you're re-running them many times solo over 6 days, keep every call cheap by default:

- **Bounded retrieval context:** cap top-k retrieval to 3-4 chunks and cap chunk size (~300-500 tokens each) in the `/chat` prompt assembly. This isn't just a security-surface choice (smaller, more deterministic injected context) — it also keeps every eval-matrix call fast and cheap to re-run.
- **Local-only by default:** all eval-matrix runs target local Ollama models, not paid hosted APIs, so iterating on payloads/mutations during development never costs real token spend (see Non-Goals). A paid-API comparison run, if done at all, is a single final-report stretch goal, not something the harness calls repeatedly.
- **Mutation caching:** cache mutated payloads by `(original payload, technique)` key and run mutation generation as a separate offline pass before timed eval runs (already a risk mitigation in §9) — this means re-running the matrix after a defense change never re-pays the mutation LLM-call cost.
- **Capped generation length:** set `max_tokens`/`num_predict` on every Ollama call (both the victim `/chat` model and the Mutation Engine's rewrite model) to the minimum needed to detect success/failure — you're scoring for an exfil marker, not reading prose, so there's no reason to let the model ramble.
- **Small/quantized model first:** default to a smaller or quantized local model for day-to-day iteration (faster + lower compute per call) and reserve the stronger model for the final measured runs that go in the report, per the model-choice note in §9.
- **Lean logging:** log retrieved-chunk and assembled-prompt traces as summaries or content hashes by default; only write full raw text to disk behind a debug flag, so a full matrix run doesn't balloon log storage with duplicated chunk text.
- **Report compute cost:** track and report tokens-per-run (or latency-per-run as a proxy) alongside ASR numbers in the final writeup — "attacks per compute dollar" is itself a finding, not just an engineering nicety.

## 8. Tech Stack

| Layer | Choice |
| --- | --- |
| Backend | Python, FastAPI |
| Orchestration | LangChain or LlamaIndex (pick one, don't use both) |
| LLM runtime | Ollama, local (Llama 3 or Mistral) |
| Vector DB | ChromaDB (local, zero-infra) |
| PDF read | PyMuPDF (fitz) |
| PDF generate (malicious) | reportlab or fpdf |
| Webhook / exfil listener | Flask or FastAPI, local or free-tier host |
| Defense (output) | guardrails-ai or a lightweight custom regex/classifier guard |
| Defense (input) | custom PyMuPDF span-inspection sanitizer |
| Eval harness | plain Python + pytest-style runner, results to JSON/CSV |

## 9. Success Metrics

- **Coverage:** ≥8 distinct injection payload variants exercised.
- **Baseline ASR (attack success rate):** measured % of payloads that achieve exfiltration against the undefended app.
- **Mutation uplift:** measured ASR increase from mutated vs static payloads against a naive keyword filter.
- **Defense efficacy:** measured ASR drop, undefended → each defense configuration → both defenses combined.
- **Cost per run:** tokens or latency per eval-matrix run, tracked so re-runs stay cheap (see §7).
- **Reproducibility:** `docker-compose up` (or documented local setup) takes a fresh reviewer from clone to a working demo in <15 minutes.

## 10. Risks & Mitigations

| Risk | Mitigation |
| --- | --- |
| Local LLM (Llama 3/Mistral via Ollama) is less susceptible to injection than GPT-class models, deflating ASR numbers | Pick a smaller/less-aligned local model as one test subject alongside a stronger one; report both — the *contrast* is itself a finding |
| 6-day solo timeline slips because of environment setup (Ollama, ChromaDB) | Install and smoke-test the full stack in the first 1-2 hours of Day 1, before writing feature code |
| Switching between builder and attacker mindset across days causes integration blind spots | Contracts frozen explicitly in §4 before Day 1 work starts; each day ends on a concrete, manually-verified checkpoint before the next day begins |
| Mutation Engine's secondary LLM calls are slow and stall the eval matrix | Cache mutated payloads by (original payload, technique) key; run mutation generation as a separate offline pass before the timed eval runs; cap `max_tokens` on every call (§7) |
| Scope creep into a polished frontend | Explicitly out of scope (§3); minimal UI only |
| Repeated eval-matrix re-runs during iteration quietly burn time/compute | Keep retrieval context bounded, generation length capped, and local-model-only by default (§7) so re-running the matrix is always cheap |

## 11. Deliverables Checklist

- [ ] Vulnerable RAG app (ingest + chat) running locally
- [ ] Exfiltration webhook listener + log
- [ ] Poisoning Engine with ≥8 payload variants
- [ ] Mutation Engine with measured uplift (and caching, per §7)
- [ ] Evaluation Matrix harness + results table/chart, 4 defense configurations
- [ ] Input-side sanitization defense
- [ ] Output-side LLM Guard defense
- [ ] README with setup + architecture diagram
- [ ] Final writeup / results report, including token/compute cost per run
- [ ] Short demo recording

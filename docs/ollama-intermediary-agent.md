# Ollama Intermediary Agent

## Overview

This document defines the architecture for introducing a local Ollama-based intermediary
layer between the Telegram interface and the existing Claude/opencode backend.

**Primary goals:**

- Persistent memory across sessions (the main pain point today)
- Reduced token consumption via semantic caching and context compression
- Clear provenance tagging on every response (`from_cache`, `from_local`, `from_claude`)
- Full orchestration control in Python — no LLM driving the orchestrator

---

## Current State

```
Telegram
    │
    ▼
[main.py]  ──► opencode (systemd service)  ──► Claude (API, paid)
                  └── per-session memory only
```

Problems: no cross-session memory; every conversation re-reads repos and context from
scratch; all prompts go to Claude regardless of complexity.

---

## Target Architecture

```
Telegram
    │
    ▼
[Orchestrator — main.py evolved]   ← Python logic, not an LLM
    │
    ├──► [Memory Store]             ← ChromaDB (embedded) + nomic-embed-text
    │         ▲  │
    │         │  └── semantic search (RAG)
    │         │
    ├──► [Llama local — Ollama]     ← CPU-only, llama3.2:3b or llama3.1:8b
    │         │
    │         ├── classify intent: QUESTION | ACTION | ESCALATE
    │         ├── compress context before escalating
    │         └── rate own confidence (1–10); < 7 → escalate anyway
    │
    └──► [Claude / opencode]        ← only for complex reasoning and OS actions
```

> Every response from Claude or opencode is received by the **Orchestrator**, which
> embeds it and writes it into the Memory Store before returning it to Telegram.
> The diagram shows the dispatch flow only; the return path always goes through the Orchestrator.

**Separation of responsibilities:**

| Layer | Handles | Model |
|---|---|---|
| Memory Store | Persistence, RAG retrieval | nomic-embed-text (local) |
| Llama local | Intent classification, context compression | llama3.2:3b / llama3.1:8b |
| opencode | OS actions, file edits, code tasks | Claude (paid) |
| Claude direct | Deep reasoning, complex Q&A | Claude (paid) |

---

## Memory Store

The memory is **independent of any model**. Models are stateless; the store provides
continuity.

### Write path — Orchestrator, after every Claude or opencode response

```
[Orchestrator receives response]
    │
    ▼
nomic-embed-text  →  vector [0.21, -0.84, 0.03, ...]
    │
    ▼
ChromaDB.add(id, vector, question, {answer, source, timestamp, tokens_used})
```

### Read path — Orchestrator, before every prompt

```
[Orchestrator receives new user question]
    │
    ▼
nomic-embed-text  →  vector
    │
    ▼
ChromaDB.query(vector, n=3)   ← returns results with cosine scores
    │                            Orchestrator evaluates the scores
    ├── score ≥ 0.92  →  cache hit  →  return answer  (tag: from_cache)
    └── score < 0.92  →  inject top-3 as RAG context  →  continue to Llama/Claude
```

### Response metadata

Every answer carries:

```python
{
    "answer": "...",
    "source": "cache" | "local" | "claude",
    "confidence": 0.95,      # cosine similarity or Llama self-score
    "cache_hit_id": "uuid",  # populated when source == "cache"
    "original_query": "...", # matched question from store
    "tokens_used": 0,        # 0 for cache/local hits
    "timestamp": "2026-...",
}
```

Display in Telegram can be minimal (e.g. 🟢 cache · 🟡 local · 🔴 claude) or verbose
in debug mode.

---

## Confidence / Trust Layers

The orchestrator enforces the rules — Llama does not self-dispatch.

```
Layer 1 — Cache (highest trust)
────────────────────────────────
ChromaDB cosine score ≥ 0.92
→ return cached answer
→ tag: from_cache + source question + date

Layer 2 — Llama local (medium trust)
──────────────────────────────────────
Prompt forces: "Respond ONLY_IF_CERTAIN or ESCALATE"
If ESCALATE → pass to Claude
If responds → second prompt: "Rate confidence 1–10 and list assumptions"
Score < 7   → escalate anyway
→ tag: from_local + confidence score

Layer 3 — Claude (source of truth)
────────────────────────────────────
Orchestrator stores Claude's response in ChromaDB
→ tag: from_claude + tokens consumed
```

**Key insight:** Llama almost never answers autonomously. Its real value is:
1. Generating embeddings (via `nomic-embed-text`) — no substitute without paid API
2. Classifying intent cheaply and fast
3. Compressing context before escalating to reduce Claude tokens

---

## Intent Classification

The orchestrator classifies every incoming message into one of:

| Intent | Handler |
|---|---|
| `QUESTION` | Memory Store → Llama → Claude |
| `ACTION` | opencode with Claude (existing flow) |
| `ESCALATE` | Direct to Claude API |

Classification is done by Llama (`llama3.2:3b`) or, for simple cases, by deterministic
Python heuristics (keyword matching, presence of imperative verbs, etc.).

---

## Hardware Profile

Assessed on 21 March 2026:

| Resource | Value | Note |
|---|---|---|
| GPU | NVIDIA MX250, 2 GB VRAM | Too small — excluded from inference |
| RAM | 15 GB total, ~11 GB available | Main resource |
| CPU | 8 cores | Sufficient for CPU-only Ollama |

**Ollama runs CPU-only.** Model recommendations:

| Model | VRAM/RAM | Role |
|---|---|---|
| `llama3.2:3b` | ~2 GB | Intent classifier (low latency priority) |
| `llama3.1:8b` | ~5 GB | Context compressor, simple Q&A |
| `nomic-embed-text` | ~300 MB | Embeddings for Memory Store |

Start with `llama3.2:3b`; add `llama3.1:8b` once the pipeline is validated.

---

## Changes Required to Existing Code

### `telegram_reader/main.py`

- Remove the call to `ensure_opencode_server()` / `start_opencode_server()` from
  `__main__` — the server is already managed by systemd.
- Route each incoming message through the new `Orchestrator` class before forwarding to
  opencode.
- Keep `send_to_opencode()` for `ACTION`-classified messages.

### New modules to create

| Module | Responsibility |
|---|---|
| `telegram_reader/orchestrator.py` | Intent classification, routing, result tagging |
| `telegram_reader/memory_store.py` | ChromaDB wrapper: embed, store, query |
| `telegram_reader/ollama_client.py` | HTTP client for Ollama (`/api/generate`, `/api/embeddings`) |

### `opencode_client.py`

No changes needed for Phase 1. In Phase 2 (multi-agent), it may receive pre-enriched
prompts from the orchestrator.

---

## Full Request Flow (Phase 1)

```
User sends message via Telegram
    │
    ▼
Orchestrator receives message
    │
    ├─ embed message via nomic-embed-text (Ollama)
    │
    ├─ query ChromaDB
    │       ├── score ≥ 0.92  →  return cached answer  (🟢)
    │       └── score < 0.92  →  retrieve top-3 as context
    │
    ├─ classify intent via llama3.2:3b
    │       ├── ACTION   →  send to opencode (existing flow)
    │       └── QUESTION →  continue
    │
    ├─ compress context + inject RAG chunks into prompt
    │
    ├─ send to Claude API
    │
    ├─ receive answer
    ├─ embed answer + store in ChromaDB  (tag: from_claude)
    └─ return answer to Telegram  (🔴)
```

---

## Phase 2 — Multi-Agent Orchestration (future)

Once Phase 1 is stable, the orchestrator can dispatch parallel sub-agents:

```
Orchestrator  (Python DAG — not an LLM)
    │
    ├──► [Agent: Refactor]      →  opencode + Claude        ┐
    ├──► [Agent: Tests]         →  opencode + Claude        ├── parallel
    ├──► [Agent: Docs]          →  Llama local (sufficient) ┘
    │
    ├──► [Memory Store]         ←  shared context between agents
    │
    └──► [Agent: QA/Validator]  →  runs tests, reports back to orchestrator
```

Design constraints for Phase 2:
- The orchestrator must be deterministic Python — never an LLM making routing decisions
- `max_retries` on the QA loop to prevent infinite correction cycles
- Conflict resolution strategy for agents editing the same file in parallel

---

## Key Design Principles

1. **Memory lives outside every model.** ChromaDB is the single source of truth for
   continuity. Replacing or upgrading any model does not lose history.
2. **Always use the same embedding model for write and read.** Switching models
   invalidates the entire vector store (re-embedding required).
3. **Llama does not decide what it knows.** The orchestrator sets the rules;
   Llama executes within them.
4. **opencode stays strong.** Do not route OS/coding actions through Llama — it degrades
   the agent. Keep the separation: questions → Llama/cache/Claude; actions → opencode.
5. **Orchestrator is code, not a model.** Control and debuggability depend on it.

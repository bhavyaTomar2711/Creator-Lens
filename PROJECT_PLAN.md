# CreatorLens — RAG Chatbot for Creator Video Analysis

> **Goal:** Take a YouTube video + an Instagram Reel, pull transcripts & metadata, compute engagement,
> embed into a vector DB, and let a creator *chat* with both videos — streaming, cited, with memory.
>
> **Deadline:** 4 days, including today.
> Day 1 = Thu 2026-05-29 · Day 2 = Fri 2026-05-30 · Day 3 = Sat 2026-05-31 · Day 4 = Sun 2026-06-01.
>
> **Hard constraint:** LangChain / LangGraph is mandatory. Everything dynamic. Inputs may be hard-coded; outputs may not.

---

## 0. TL;DR — how this stands out

Most submissions will be a thin wrapper: `youtube-transcript-api` → OpenAI → a chat box. They will
break on Instagram (no public API), hallucinate the engagement numbers, and have no story for cost at scale.

CreatorLens wins on the three things the brief actually grades:

1. **Resourcefulness (the Instagram problem).** A layered ingestion pipeline with real fallbacks:
   `yt-dlp` metadata → audio extract → **Whisper transcription** → graceful manual-override so the
   *demo never dies on stage*. This is the part 80% of candidates fail.
2. **Correctness over vibes.** Engagement rate is **computed in code**, not asked of the LLM. The number
   is injected into context as a verified fact. The model reasons about *why*; it never invents a *what*.
3. **A real cost & scale answer.** A `url-hash` dedup cache + a per-session token/$ meter, plus an honest
   "what breaks at 10k users" section (yt-dlp IP blocks, Whisper throughput) with the fix for each.

Plus the LangGraph-native agent (tool nodes + checkpointed memory), chunk-level citations that **seek the
video to the cited timestamp**, and token streaming. That combination is what moves a candidate to "top 1%."

---

## 1. Requirements checklist (traceability — every line in the brief maps to a deliverable)

| # | Requirement | Where it's satisfied |
|---|-------------|----------------------|
| R1 | Two URLs as input (YouTube + Instagram Reel, **mandatory**) | Ingest form (Day 4 UI), `/ingest` endpoint |
| R2 | Pull transcript + metadata (views, likes, comments, creator, follower count, hashtags, upload date, duration) | Ingestion pipeline (Day 1–2) |
| R3 | Engagement rate = (likes + comments) / views × 100 | Computed **deterministically in code**, stored on video record |
| R4 | Chunk + embed transcripts → vector DB, tag every chunk with `video_id` (A/B) | Embedding pipeline → Qdrant, metadata `{video_id, session_id, chunk_index, start, end}` |
| R5 | RAG chat (LangChain/LangGraph) answering the 5 sample questions | LangGraph agent (Day 3) |
| R6 | Responses **stream**, **cite sources** (video + chunk), **maintain memory** | SSE streaming + citation payload + LangGraph checkpointer |
| R7 | Vibe-coded frontend: side-by-side video cards + chat panel; fast, not laggy | Next.js UI (Day 4) |
| R8 | Loom demo, clean GitHub repo, README, `.env.example`, multiple commits | Day 4 + commit hygiene throughout |
| R9 | Defend cost/quality at 1000 creators/day; name a better alternative if one exists | This doc §6 + README "Trade-offs" section |

**The 5 questions the chat must nail (acceptance test):**
1. Why did Video A get more engagement than Video B?
2. What's the engagement rate of each?
3. Compare the hooks in the first 5 seconds.
4. Who's the creator of Video B and what's their follower count?
5. Suggest improvements for B based on what worked in A.

---

## 2. Architecture & stack (with reasoning — this is what they grill on the call)

```
┌─────────────────────────────┐         ┌──────────────────────────────────────────┐
│  Next.js 16 (App Router)     │  HTTP   │  FastAPI (Python) backend                  │
│  - 2 video cards (metadata)  │ ──────▶ │  /ingest   → ingestion pipeline            │
│  - chat panel (SSE stream)   │ ◀────── │  /chat     → LangGraph agent (SSE stream)  │
│  - citation chips → seek     │   SSE   │  /session  → state                         │
└─────────────────────────────┘         └──────────────────┬─────────────────────────┘
                                                            │
                          ┌─────────────────────────────────┼───────────────────────────┐
                          ▼                                  ▼                           ▼
                   yt-dlp + ffmpeg               OpenAI text-embedding-3-small      Qdrant (vector DB)
                   + Whisper (Groq)              (1536-d, cheap)                    filter by session+video_id
                   + youtube-transcript-api                                         + url-hash dedup cache
```

### Why a Python FastAPI backend *and* a Next.js frontend (not Next-only)?
- The two hardest pieces — `yt-dlp` (Instagram download) and **Whisper** — are Python-native and battle-tested there. LangGraph's Python SDK is more mature than `langchain.js`.
- Next.js stays as the frontend + a thin proxy. We get React 19 streaming UI **and** the Python ML ecosystem. Clean separation, each tool doing what it's best at.
- **Defense for "why not all-Next?"**: you *can* do `langchain.js`, but you'd shell out to `yt-dlp`/`ffmpeg` and reimplement Whisper plumbing in a less-supported runtime. More risk, no upside. (The repo's own `node_modules/next/dist/docs/.../backend-for-frontend.md` blesses exactly this pattern.)

### Component choices

| Layer | Choice | Why this, defensibly | Cheaper/alt option |
|-------|--------|----------------------|--------------------|
| **Orchestration** | **LangGraph** (Python) | Explicit stateful graph: tool nodes (metadata, retrieval), conditional routing, built-in checkpointer for memory. More impressive & more controllable than a plain LangChain chain. | LangChain LCEL chain (simpler, less standout) |
| **Vector DB** | **Qdrant — local on-disk mode** (`QdrantClient(path=...)`, **no Docker, no server, no key**) | Fast (Rust), first-class **metadata filtering** (we filter by `session_id` + `video_id` constantly). Local mode = zero infra for dev/demo; lift-and-shift to Qdrant Cloud free tier for deploy. | **pgvector** if a Postgres already exists. ChromaDB for pure-local zero-setup. |
| **Embeddings** | **`fastembed` local — `BAAI/bge-small-en-v1.5`** (384-d, ONNX) | **$0, no API key**, runs on CPU, Qdrant-native integration. Strong for short-form retrieval. | OpenAI `text-embedding-3-small` (paid, marginally better) |
| **LLM** | **Groq `llama-3.3-70b-versatile`** (FREE tier) | Free, very fast inference, 70B quality is plenty for grounded RAG. Streams natively. | Groq `llama-3.1-8b-instant` for cheaper/faster simple queries; Gemini free tier as backup |
| **YouTube transcript** | **`youtube-transcript-api`** | Free, instant — reuses YouTube's own captions, **no transcription cost**. | yt-dlp audio → Whisper (fallback when captions are off) |
| **Instagram transcript** | **`yt-dlp` → ffmpeg audio → Whisper (Groq `whisper-large-v3-turbo`)** | No IG API exists. Groq Whisper is **free-tier**, fast; reels are <60s. | `faster-whisper` local = $0 fully-offline fallback (no network/key) |
| **Metadata** | `yt-dlp -J` (JSON) for both platforms | One tool, both platforms: views, likes, comments, uploader, follower count, description→hashtags, upload_date, duration. | IG oEmbed / Graph API (needs app review) |
| **Frontend** | Next.js 16 + Tailwind 4 (already scaffolded) | Already in repo; App Router streaming pairs naturally with SSE. | — |

> ⚠️ **Next.js 16 is modified in this repo** (AGENTS.md). Before writing any Next code, read the relevant
> guide under `node_modules/next/dist/docs/` (esp. `01-app/01-getting-started/15-route-handlers.md`,
> `16-proxy.md`, and `02-guides/backend-for-frontend.md`). Don't trust training-data Next conventions.

---

## 3. Data model

```jsonc
// Video record (one per URL, cached by url-hash)
{
  "video_id": "A",                 // A = YouTube, B = Instagram (UI label)
  "url_hash": "sha256(url)",       // dedup / cache key
  "platform": "youtube|instagram",
  "url": "...",
  "creator": "channel/handle",
  "follower_count": 123456,
  "title": "...",
  "upload_date": "2026-05-01",
  "duration_sec": 58,
  "views": 100000, "likes": 8000, "comments": 400,
  "engagement_rate": 8.4,          // (likes+comments)/views*100, computed in code
  "hashtags": ["#x", "#y"],
  "transcript": "...",
  "transcript_source": "captions|whisper|manual",
  "chunks": [ { "chunk_index": 0, "text": "...", "start": 0.0, "end": 7.2 } ]
}
```

Chunks are **timestamped** so "compare the hooks in the first 5 seconds" is a precise filter (`start < 5`),
and citation chips can **seek the video player** to the cited moment.

---

## 4. Chunking & retrieval strategy (defendable on the call)

- **Chunk size:** ~400–600 tokens, ~80-token overlap, split on sentence/caption boundaries.
  - *Why:* Reels are short (often <150 words → 1–3 chunks). YouTube can be long. A mid-size chunk keeps
    each citation meaningful without flooding the context. Overlap preserves cross-boundary context.
  - *What breaks if wrong:* too small → fragmented citations & more vectors; too big → vague citations,
    retrieval grabs irrelevant text.
- **Always tag** `{session_id, video_id, chunk_index, start, end}` for filtering + citations (R4).
- **Retrieval:** top-k per video (k≈4 each) so comparative questions always see *both* sides, not just the
  louder transcript. For "first 5s" questions, pre-filter `start < 5`. Engagement/metadata questions are
  answered from the **structured record via a tool**, not vector search (accuracy > recall).

---

## 5. The LangGraph agent (R5, R6)

```
START
  → classify_intent        (metadata-q | transcript-q | comparative-q)
  → route:
      ├─ metadata_tool      (reads structured video record: engagement, creator, followers)
      ├─ retrieve_chunks    (Qdrant, filtered by session + video_id, k per video)
      └─ both               (comparative questions need numbers AND transcript)
  → generate (LLM, streamed)   ← injects verified metadata + retrieved chunks + citations
  → END
checkpointer = memory across turns (R6)
```

- **Memory:** LangGraph checkpointer keyed by `session_id` (thread). Follow-ups like "and what about B?" work.
- **Streaming:** `astream_events` → SSE tokens to the browser (R6).
- **Citations:** each generation returns `sources: [{video_id, chunk_index, start, end}]`; UI renders chips.
- **No hallucinated stats:** engagement/follower numbers come from the `metadata_tool`, never the LLM's guess.

---

## 6. Cost & scalability — "1000 creators/day", "what breaks at 10k" (R9)

**The whole stack is free.** Every component is a free tier or local: YouTube captions ($0), Groq Whisper
+ Groq LLM (free tier), `fastembed` (local, $0), Qdrant local mode ($0). So the interesting question isn't
"what's the dollar cost" — it's **"what actually constrains you at scale, and what's the cheapest way past it?"**

**Marginal $ cost per comparison on this stack: ~$0.** The real currency is **API rate limits + local CPU time.**

| Resource | Cost on free stack | The real constraint |
|----------|-------------------|---------------------|
| YouTube transcript | $0 (captions) | none |
| Instagram transcript | $0 (Groq Whisper free tier) | **Groq free-tier rate limit** (req/min, audio-sec/day) |
| Embeddings | $0 (local fastembed) | CPU time (~ms/chunk, trivial) |
| Chat | $0 (Groq free tier) | **Groq free-tier tokens/min** |

**Does free scale to 1000 creators/day? Honestly: not on one free key.** ~1000 × (2 transcriptions + a
chat session) will hit Groq's free-tier rate limits. That's the key insight to say on the call — and here's
the cheapest path past it, in order:

1. **Cache first (free, biggest win).** `url-hash` dedup means a video is transcribed + embedded **once,
   ever**. Creators re-analyze their own / popular videos constantly → huge hit rate → most of the 1000/day
   never touch Whisper at all.
2. **Self-host the bottleneck for $0 marginal.** Swap Groq Whisper → **`faster-whisper` on one GPU box**, and
   Groq LLM → a local **Llama-3.3-70B / 8B** via vLLM. Embeddings are already local. Now you're rate-limit-free
   at the cost of *one machine*, not per-call fees. This is the lowest-cost-at-scale answer.
3. **Or pay-as-you-go Groq** — still extremely cheap (Whisper ≈ $0.04/audio-hr, reels <60s) and zero ops.
   Trade a few dollars/day for not running a GPU. Pick (2) vs (3) on whether you'd rather pay ops or invoices.

**Why this is the highest-quality / lowest-cost combination:** free YouTube captions avoid transcribing what's
already transcribed; local embeddings have no per-call fee and no key to rate-limit; Groq gives 70B-class
answers free for dev and pennies at scale; and dedup turns a recurring cost into a one-time one. A paid stack
(OpenAI embeddings + GPT-4o) buys marginal quality at real per-call cost we don't need for short-form RAG.

**What breaks at 10k users (honest answer):**
| Bottleneck | Symptom | Fix |
|-----------|---------|-----|
| Groq free-tier rate limits | 429s under load | self-host Whisper+LLM (#2 above) or move to paid Groq |
| `yt-dlp` IP rate-limits / IG blocks | downloads start failing | residential **proxy rotation**, cookie pool, retry/backoff, manual-override fallback |
| Whisper throughput | ingestion latency spikes | **job queue** (Redis/RQ or Celery) + autoscaled `faster-whisper` workers; ingestion is async & idempotent by url-hash |
| Synchronous ingest blocking API | timeouts | decouple: `/ingest` enqueues, UI polls/streams status |
| Vector DB | basically fine | Qdrant scales easily; move local-mode → server/Cloud, shard by tenant |

---

## 7. Risk register (retire the scary stuff first)

| Risk | Likelihood | Impact | Mitigation (and *when*) |
|------|-----------|--------|--------------------------|
| **Instagram download blocked / needs login** | High | High | ✅ **CONFIRMED Day 1.** Anonymous yt-dlp → blocked ("empty media response"). `--cookies-from-browser` Edge/Chrome → DPAPI decryption fails (yt-dlp #10927). **Fix: `cookies.txt` export** (extension) → `IG_COOKIES_FILE`; Firefox cookies-from-browser also works. Plus manual override field as last resort. |
| yt-dlp / ffmpeg not installed (confirmed missing) | Certain | High | Day 1 task #1: install + smoke-test both. |
| Modified Next.js 16 surprises | Med | Med | Read `node_modules/next/dist/docs` route-handler/proxy/BFF guides before coding UI (Day 4). |
| Whisper too slow locally on Windows | Med | Med | Use **Groq Whisper API** (no local GPU); faster-whisper as offline fallback. |
| YouTube video has no captions | Med | Low | Fall back to yt-dlp audio → Whisper (same path as IG). |
| Streaming + citations plumbing fiddly | Med | Med | Build streaming on Day 3 with a stub agent before wiring the full graph. |
| Live demo nerves / network | Med | High | Pre-ingest the two demo videos; cache hit makes the demo instant & deterministic. |

---

## 8. The 4-day plan

> Rhythm: **de-risk the impossible parts first** (Instagram, transcription), then the RAG core, then the
> UI, then polish + Loom. Commit in small, story-telling chunks every step (R8).

### Day 1 (Thu 05-29) — De-risk ingestion. *If Instagram works, the project works.*
- [ ] Install & smoke-test **yt-dlp** + **ffmpeg** on Windows. (`pip install yt-dlp`, ffmpeg via winget/choco.)
- [ ] Prove **YouTube**: `youtube-transcript-api` transcript + `yt-dlp -J` metadata on a real URL.
- [ ] Prove **Instagram**: `yt-dlp -J` metadata + download audio + **Whisper (Groq) transcript** on a real reel. Handle the login/cookie case.
- [ ] Lock the **video data model** (§3); write the deterministic **engagement-rate** function + unit test.
- [ ] Stand up **FastAPI** skeleton + `.env.example` (keys: OPENAI, GROQ, QDRANT).
- **Exit criteria:** one script ingests *both* real URLs into the data model, end to end, from the terminal.
- **Commits:** "feat: yt-dlp+whisper ingestion for YT & IG", "feat: engagement-rate calc + tests".

### Day 2 (Fri 05-30) — Embeddings + vector store + the `/ingest` API.
- [ ] Run **Qdrant** in Docker; create collection w/ payload schema.
- [ ] **Chunk** (timestamped, §4) → **embed** (`text-embedding-3-small`) → upsert with `{session_id, video_id, chunk_index, start, end}` (R4).
- [ ] **url-hash dedup cache** (skip re-transcribe/re-embed on repeat) — also the scale story.
- [ ] `POST /ingest` → returns both video records (metadata + engagement + chunk counts).
- **Exit criteria:** hit `/ingest` with 2 URLs, see both records + vectors queryable by `video_id`.
- **Commits:** "feat: qdrant store + timestamped chunking", "feat: /ingest endpoint + url-hash cache".

### Day 3 (Sat 05-31) — The brain: LangGraph agent, streaming, citations, memory.
- [ ] Build **LangGraph** graph (§5): intent classify → metadata_tool / retrieve_chunks → generate.
- [ ] **`metadata_tool`** answers engagement/creator/follower questions from the structured record (no hallucination).
- [ ] **Retrieval** filtered by session + video_id, k-per-video; `start < 5` filter for hook questions.
- [ ] **SSE streaming** of tokens (R6); **citations** payload `{video_id, chunk_index, start, end}`.
- [ ] **Checkpointer memory** across turns (R6).
- [ ] Validate against **all 5 acceptance questions** (§1) via curl/script.
- **Exit criteria:** all 5 questions answered correctly, streamed, cited, with a working follow-up.
- **Commits:** "feat: langgraph rag agent", "feat: streaming + citations", "feat: conversational memory".

### Day 4 (Sun 06-01) — Frontend, polish, README, Loom.
- [ ] Read the modified-Next route-handler/proxy docs first. Build **2 video cards** (thumbnail, creator, followers, views/likes/comments, **engagement rate**, hashtags, duration) + **chat panel**.
- [ ] Wire SSE streaming into the chat UI; render **citation chips** that **seek the video** to `start`.
- [ ] Loading/empty/error states (so it "ain't laggy"); pre-ingest demo videos for instant cache hit.
- [ ] Write a **human** README: architecture, setup, **trade-offs** (why Qdrant, why this chunk size, what breaks at 10k — §6), `.env.example`.
- [ ] Final pass on the 5 questions; record **Loom** start-to-finish with 2 real URLs (R8).
- **Exit criteria:** full demo, no bugs; repo clean; Loom recorded.
- **Commits:** "feat: side-by-side cards + chat UI", "feat: citation chips seek video", "docs: README + trade-offs".

### Buffer / stretch (only if ahead)
- Per-session **token/$ meter** in the UI (great cost-conversation prop).
- Model-escalation routing (mini → gpt-4o) on comparative questions.
- Deploy (Vercel frontend + Render/Fly backend + Qdrant Cloud) for a live Project URL.

---

## 9. Submission format (have this ready Day 4)
1. **Project URL** — (deployed, or localhost in Loom if not deployed)
2. **Project Description** — one paragraph: what it does + the standout (resourceful IG ingestion, computed engagement, scale story).
3. **Loom URL** — full demo, 2 real URLs, start to finish.
4. **GitHub repo** — clean, README, `.env.example`, multiple story-telling commits.

---

## 10. Definition of done
- [ ] Real YouTube **and** real Instagram Reel ingest dynamically (no hard-coded outputs).
- [ ] Engagement rate computed in code, shown per video, matches the formula.
- [ ] Chunks embedded in Qdrant, every chunk tagged with `video_id`.
- [ ] LangGraph chat answers all 5 questions: streamed, cited, with memory.
- [ ] Side-by-side cards + chat UI, responsive and fast.
- [ ] README defends every major trade-off; `.env.example` present; commits tell a story.
- [ ] Loom recorded; submission block filled in.
```

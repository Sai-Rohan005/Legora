# Gold-set workflow

The default target is **145 items**: 30 each from BNS, BNSS, BSA and the
Constitution (120), plus 15 multi-provision questions and 10 out-of-scope questions.
All Gemini output is draft material with `reviewed=false`, not verified gold.

Current checked-in `gold.jsonl`: **10 Gemini-generated out-of-scope drafts**.
The 135 provision-backed items have not been generated because the stored corpus
is unavailable following deletion of the database containers. No provision labels
or metrics were invented to fill that gap. Restore/re-ingest the corpus, or use
an existing stored-chunk export, before completing the remaining items.

## 1. Capture stored chunks

The tools use Python 3.11+ and the project's existing dependencies. Run from the
repository root. Evaluation settings are read centrally from `.env`/environment
variables and do not require Neo4j or Indian Kanoon credentials.

For the unified Qdrant collection:

```bash
python -m eval.sample --collection legal_rag
```

For separate collections:

```bash
python -m eval.sample --collection bns --collection bnss --collection bsa --collection constitution
```

For an existing JSON array, Qdrant `{"points": [...]}` object, or JSONL export:

```bash
python -m eval.sample --chunks /path/to/stored-chunks.jsonl
```

Export records may be payload dictionaries (`chunk_id`, `text`, ...) or objects
containing a `payload` dictionary. This must be real stored corpus data; the
parser test fixtures are not a substitute for the corpus. `QDRANT_URL` and an
optional `QDRANT_API_KEY` are needed only for live sampling.

The snapshot `eval/provisions.jsonl` retains every recognized source chunk for
review, including child chunks. Sampling uses 30 distinct section/article roots
per act, preferring full parent provisions to avoid overweighting sections with
many children. It is uniform within each act, reproducible with `--seed 42`, and
fails if any act has fewer than 30 distinct provisions. Chapter/preamble/schedule
records are not sampled. Existing snapshots are not silently overwritten.

## 2. Draft questions with Gemini

```bash
python -m eval.generate
# Optional: cap new items in a run, then resume with the same command/settings.
python -m eval.generate --limit 10
```

Requires `GEMINI_API_KEY`; uses `GEMINI_MODEL` and `EXTERNAL_TIMEOUT_SECONDS`.
No embedder, reranker, graph, or API server is needed to draft from the snapshot.
The output defaults to `eval/gold.jsonl`. Successful drafts are saved atomically
after each item. Existing items, including human edits/approvals, are preserved
on resume. `gold.manifest.json` binds full generation to the snapshot hash, seed,
and target counts. Use a new output path to build a different dataset.

Each source has a preferred intent cycling through punishment, definition,
procedure, evidence and rights. Gemini must choose a supported intent rather than
invent a punishment or right absent from the provision. Intent coverage therefore
needs human review; no unsupported per-act intent quota is forced.

Multi-provision prompts receive multiple sampled sources and must identify at
least two distinct supporting provisions. Unsupported combinations and unknown
IDs are rejected and retried up to three times. Generated notes explain source
support and ambiguity for the reviewer. Individual source text in prompts is
limited to 12,000 characters, while the review snapshot retains the full text.
Review long/truncated provisions carefully. Gemini grounding is not a legal
correctness guarantee.

The independent refusal items can be drafted without a corpus:

```bash
python -m eval.generate --out-of-scope-only
```

They use ordinary nonlegal topics (cooking, programming, astronomy, etc.), empty
supporting ID lists and `answerable=false`. They also require human review.

## 3. Review each item

```bash
python -m eval.review --list
python -m eval.review
# Inspect a specific item:
python -m eval.review --id oos-001
```

Interactive commands display sources, edit the question, intent, expected IDs,
acceptable alternate IDs or notes, skip an item, and approve it. Approval is an
explicit human action. Any subsequent edit resets `reviewed=false`. Answerable
items cannot be approved unless their expected and alternate IDs exist in the
snapshot. Single-act items must reference that act.

Noninteractive review is also supported (replace the example ID with an actual
stored ID supporting the displayed question):

```bash
python -m eval.review --id single-bns-001 --expected 'BNS-303(2)' --notes 'Reviewer explanation'
python -m eval.review --id single-bns-001 --approve
```

Every JSONL record has `id`, `question`, `intent`, `act`, `expected_chunk_ids`,
`acceptable_alternates`, `answerable`, `notes`, and `reviewed`. Acts are BNS,
BNSS, BSA, Constitution, MULTI, or OUT_OF_SCOPE. Questions with `act=MULTI`
need at least two expected IDs. Out-of-scope records must have no supporting IDs.

## 4. Predict and measure reviewed items only

Once the API and its dependencies are running:

```bash
python -m eval.predict
python -m eval.metrics --output eval/metrics.json
```

`predict` submits **only reviewed questions** to `API_BASE_URL`, with
`API_TIMEOUT_SECONDS`. It saves `eval/predictions.jsonl` only after all requests
succeed; transport failures do not become fabricated results. Predictions have
`id`, `retrieved_chunk_ids`, `score` (0–100), and `refused` (boolean).
You may supply an existing prediction file with `--predictions PATH` for offline
metrics. Recollect predictions after editing questions.

The API has no structured refusal field. `predict` recognizes only the pipeline's
canonical “The provided legal corpus does not contain sufficient information to
answer this question” sentence; other refusal wording needs an explicit human
`refused=true` label. Low confidence is independently measured using
`PASS_THRESHOLD` (override with `metrics --threshold`).

Metrics reject a dataset with zero reviewed records. Unreviewed predictions are
ignored before validation/scoring. Missing predictions for reviewed records count
as unsuccessful, not silently omitted. Reported metrics are retrieval hit rate,
all-required-provisions rate, mean provision recall, mean citation precision and
out-of-scope refusal/low-confidence success rate. Absent categories produce null.
They measure retrieval and scope handling, not legal answer correctness.

For single-provision questions, a reviewed alternate can satisfy the expected
source. For multi-provision questions, all expected IDs remain required for full
coverage; flat alternates count toward hit rate and precision but cannot represent
complete alternative multi-source sets. Edit the expected set during review if
the canonical multi-provision support changes.

```bash
python -m pytest tests/test_eval.py
```

These tests use synthetic sources only in temporary test files and mock the
Gemini boundary. Sampling, draft validation, resume, review and metric logic run
without network calls.

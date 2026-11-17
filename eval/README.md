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

## Retrieval ablation benchmark

```bash
python -m eval.run_retrieval_eval
# Evaluate a subset without loading unused dependencies:
python -m eval.run_retrieval_eval --configs A B C --seed 42
# Reuse cached analysis and forbid Gemini calls:
python -m eval.run_retrieval_eval --offline-analysis
```

`eval/run_retrieval_eval.py` accepts only `reviewed=true, answerable=true` items.
It refuses an empty eligible set before initializing clients or loading weights.
The current gold file has no eligible items, so the checked-in
`results/retrieval_ablation.csv` is header-only and the Markdown report says
“not run.” They contain no benchmark scores. An empty eligible set or a failed retrieval call does not
overwrite earlier completed reports.

Every preset uses the same retrieval path and feature switches:

| Preset | Features |
|---|---|
| A | Original question, dense search, no act filter or query analysis |
| B | A plus the primary-act filter from query analysis |
| C | B plus `build_retrieval_queries` expansion, retaining the original question |
| D | C plus BAAI/bge-reranker-large, without additive legal boosts |
| E | D plus the existing legal-boost heuristics |
| F | E plus graph expansion from the top 10 ranked results |
| G | E plus BM25/dense RRF (k=60) and explicit provision-ID lookup |

D and E use identical candidate pools and the existing analysis-enriched rerank
query; only the additive legal-boost switch differs. F preserves E's ranked list.
G keeps graph expansion off to isolate the new retrieval path against E.
Analysis receives only the question, never the expected IDs, gold act or intent.
An unknown primary act stays unfiltered, as in the production helper.

`--configs A B ...` selects presets. Individual switches can be overridden with
`--act-filter/--no-act-filter`, `--multi-query/--no-multi-query`,
`--rerank/--no-rerank`, `--legal-boost/--no-legal-boost` and
`--graph/--no-graph`. Legal boost requires reranking. For example:

```bash
python -m eval.run_retrieval_eval --configs E --no-legal-boost --no-graph
```

`--bm25/--no-bm25` and `--exact-id-lookup/--no-exact-id-lookup` control the
new stages independently. Compare E and G, or disable lookup to isolate BM25/RRF:

```bash
python -m eval.run_retrieval_eval --configs E G --offline-analysis
python -m eval.run_retrieval_eval --configs G --no-exact-id-lookup
```

G builds one BM25Okapi index by scrolling payloads from the same Qdrant collection,
without vectors. It searches the original question, applies the inferred act
filter, and fuses its ranked hits with the merged dense ranking using
`sum(1 / (60 + rank))`. Each ID receives at most one contribution per stream.
Only chunks with an overlapping query token enter the lexical ranking; negative
BM25 scores remain valid matches. Both streams are capped to the common candidate
budget, and fusion is capped again before reranking. The run manifest records
the RRF constant, lexical query choice, flags and rank-bm25 package version.

Explicit references such as `section 303 BNS`, `BNSS section 35`, and
`article 21 Constitution` trigger payload `chunk_id` equality lookups. A bare
`section 303` does not identify an act and causes no exact lookup. Qualified
multi-act references and existing legacy Constitution IDs are supported. Only
actual stored hits are prepended; nonexistent IDs are not synthesized. Exact
hits bypass a potentially wrong inferred act filter and are pinned after
reranking as well as before it, within the same candidate/output limits.

BM25 is **not enabled by default in production**. The current table marks G as
not evaluated because no reviewed, answerable gold items are available and the
database corpus was removed. There is no measured Recall@5/MRR improvement to
justify changing the default. Compare E/G on reviewed labels after restoring the
corpus; the script never edits production defaults automatically.

Overrides are recorded in the run manifest and the report's feature table, so a
customized preset is not mistaken for the default configuration.

`--candidates 50` is both the per-query search limit and the merged candidate
budget, with a minimum of 10. Multi-query hits are deduplicated by exact chunk ID,
keeping the highest dense score, then sorted by descending score and chunk ID and
capped to that common budget before reranking. Thus expansion does not also give
the reranker an unbounded larger budget. Dense search defaults to Qdrant exact
search for reproducibility; `--approximate-search` uses production ANN search.
Production retrieval defaults remain unchanged.

All models are loaded once per run. A needs only the embedder and Qdrant. B–G
need Gemini credentials only on a cache miss; only D–G load the reranker, and
graph-enabled configurations (F by default) need `NEO4J_*`. No Indian Kanoon
requests or answer-generation calls are made.
Use `--collection`, `--embedder-model` and `--reranker-model` to select a frozen
corpus and pinned/local model snapshots.

### Measures and confidence intervals

The report provides two independent scoring modes:

- **exact**: literal stored chunk ID equality;
- **root**: section/article identity, e.g. `BSA-115(2)(a)` → `BSA-115`,
  `BNSS-45-EXPL-1` → `BNSS-45`, and `article_21_clause_1` → `CONST-21`.

Recall@1/5/10 is the fraction of required targets recovered by that rank, macro
averaged over questions. MRR uses the first relevant result anywhere in the
retained candidate budget (default depth 50). nDCG@10 uses binary relevance and
the ideal ranking of the required targets. Repeated exact/root hits retain their
rank positions but receive credit only once. Root scoring collapses expected
chunks from the same provision to one target.

A reviewed single-provision alternate may satisfy that target. Flat alternates
do not specify which required source they replace in a multi-provision question,
so multi-provision ranking metrics use the canonical expected set only.

For F, **context recall** measures target coverage in actual returned graph nodes.
**combined context recall** measures coverage in graph nodes plus the top-10
retrieved chunks. Graph lookup keys, requested seed IDs and IDs merely mentioned
in source text do not count as returned graph evidence. Exact graph coverage uses
literal node/chunk IDs; root coverage handles graph/stored-ID format differences.
Graph columns are blank/dashes for presets that do not run graph expansion.

The default confidence intervals use 2,000 query-level bootstrap resamples and
the 2.5th/97.5th percentiles. Resample indices are seeded and paired across
configurations/scoring modes for the same question group. Per-intent intervals
resample within each observed intent. Singleton groups have degenerate intervals.
These intervals describe query-sample variation, not model/corpus drift or legal
answer correctness. Override the count with `--bootstrap-samples`.

### Caching, reproducibility and output

Query analyses are cached under `results/analysis_cache/` (ignored by Git). Keys
include the exact question, Gemini model, seed, analyser code/prompt fingerprint
and analysis schema. Cached records are schema-validated; a corrupt cache fails
instead of silently producing a new analysis. `--refresh-analysis` explicitly
replaces cached outputs, while `--offline-analysis` requires cache hits. Gold act,
intent and support labels are never sent to the analyser.

`--seed` seeds Python, NumPy, Torch and CUDA; query analysis uses temperature zero
and the seed, and its first response is then frozen in the cache. Torch inference
uses evaluation mode and deterministic algorithms; unsupported deterministic
operations fail rather than silently falling back. Stable tie-breaking and exact
dense search avoid dependence on set iteration or ANN ties. Identical reruns still
require unchanged corpus contents, model revisions, package versions and hardware.
Freeze the Qdrant/Neo4j data during evaluation. Cached Gemini output cannot make a
changed corpus or model checkpoint equivalent to an earlier run.

Completed runs write these files under `--output-dir` (default `results`):

- `retrieval_ablation.csv`: macro estimates and separate 95% interval bounds;
- `retrieval_ablation.md`: the table, feature flags, intent breakdown and worst 10;
- `retrieval_ablation_by_intent.csv`: the same metrics grouped by observed intent;
- `retrieval_ablation_worst10.json`: the worst query/configuration pairs with
  questions, expected/alternate IDs, ranked IDs and graph IDs;
- `retrieval_ablation_details.jsonl`: per-question retrieval outputs for auditing;
- `retrieval_ablation_run.json`: seed, gold-file hash, candidate/depth settings,
  model revisions when available, package versions, feature flags and cache usage.

Worst cases are sorted by ascending root Recall@10, root nDCG@10, exact Recall@10
and exact nDCG@10, then configuration and item ID. The same question can appear
under multiple failing configurations. Full Recall@10 with an imperfect nDCG@10
ranking is also included among failures. No incomplete query run is summarized as
a completed benchmark.

## Full-pipeline answer evaluation

```bash
python -m eval.run_answer_eval
python -m eval.run_answer_eval --gold eval/gold.jsonl --output-dir results
```

This runner loads one pipeline, runs all reviewed questions (including
out-of-scope items), and closes its clients after the batch. Unreviewed items
are excluded. An empty reviewed set stops before loading clients or weights;
failed batches produce no completed metrics. The current dataset has no reviewed
items, so `results/answer_eval.md` records **not run** without numerical scores.

Completed runs write `answer_eval.json`, `answer_eval.md`, and
`answer_eval_details.jsonl`. Details retain answers, expected IDs, citation checks,
attempts, evaluation scores, and refusal decisions for inspection.

The deterministic verifier recognizes section/article labels, common abbreviations,
act-first forms such as `BNSS 45(2)`, canonical chunk IDs, and legacy Constitution
IDs. It expands bounded numeric ranges. Unknown acts, ambiguous bare sections,
and invalid or excessively large ranges remain unsupported. A bare article maps
to the Constitution; a bare section may use the unique matching retrieved act.
Root citations can match descendant chunks. Specific subsections require an
appropriate chunk or subsection markers inside the retrieved parent passage.
Requested graph IDs, queries and discarded vector candidates are not evidence.
These checks establish citation presence, not legal-claim entailment.

Metrics use these denominators:

- Citation precision: supported citation occurrences / all citation occurrences.
  Repeated mentions count separately. Macro precision averages citation-bearing
  answers; answers without citations are counted separately, with null precision.
- Unsupported-citation rate: unsupported occurrences / all occurrences.
  Unsupported-answer rate is the fraction of answers with any unsupported citation.
- Answer-contains-expected-provision rate: answerable questions whose answers
  mention all expected root provisions / answerable questions. A reviewed alternate
  may substitute for a single expected ID. The supported counterpart additionally
  requires those mentions to pass the context check.
- Out-of-scope refusal rate: recognized refusals / reviewed out-of-scope questions.
  Canonical abstention and explicit inability/out-of-scope wording count; low
  confidence alone does not. Inspect the saved decisions for wording missed by
  this deterministic heuristic. Absent categories have null metrics.

In production, any unsupported citation prevents PASS. Its adjusted score is
the raw judge score multiplied by citation precision, capped at
`max(0, PASS_THRESHOLD - 1)`; the original score remains `llm_overall_score`.
The failure stage becomes `CITATION` and uses the existing retry budget. On
exhaustion, the best attempt retains its own citation report and warnings.
The `citation_check` stage is logged, and its duration contributes to API
`latency_ms.judge`.

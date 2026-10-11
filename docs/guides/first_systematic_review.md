# Your First Systematic Review with MedOrigin

*The complete workflow, stage by stage: what each command does, what it writes,
what it maps to in PRISMA 2020, and what you must never do. Read the
[Quick Start](research_quickstart.md) first for the fifteen-minute version.*

The pipeline you will walk:

```
Literature -> Import -> Deduplication -> Title/Abstract Screening
    -> Evidence Extraction -> Verification -> Snapshot -> (Benchmark) -> Reporting
```

Everything downstream of Import is driven by six commands: `screen`, `extract`,
`check`, `stats`, `snapshot`, `bench`. Everything they write is append-only or
content-addressed, so nothing you do can silently destroy earlier work.

---

The `medscale` commands below intentionally use the retained Python CLI name; the repository and public identity are **MedOrigin**.

## Stage 0 - Before you begin

```bash
uv run medscale --version     # record it: your methods section needs it
uv run medscale check         # must print CLEAN
git status                    # start from a committed tree
```

Decide your **reviewer id** now (e.g. your initials or ORCID fragment) and use it
consistently: it is written into every decision you make, forever.

## Stage 1 - Import (literature ingestion)

Ingestion is scripted, not interactive: queries are frozen in
`docs/execution/search_strategy.md` (Q1-Q10), and every API response is archived
verbatim with a manifest before any record is built:

```bash
uv run --with truststore python scripts/ingest_round.py   # needs network + API keys
```

Most researchers **never run this** - the repository already contains the ingested,
deduplicated corpus of round 1 (1,346 records). Re-running ingestion is a new
*round* with its own manifests; it never overwrites an earlier round's archives.

**PRISMA mapping:** *Identification.* The per-source retrieval counts live in the
run manifests under `data/litdb/manifests/`.

## Stage 2 - Deduplication

Automatic dedupe already ran (40 merges, lineage in `merge_log.jsonl`). What remains
for a human is the **uncertain groups** - papers that look like the same work but
the machine would not merge on its own (e.g. preprint vs published twins):

```bash
uv run medscale screen duplicates --reviewer <you>
```

Rules of the stage:

- Keeping one member marks the others `DUPLICATE_CONFIRMED` via ordinary review
  events - **the corpus itself is never rewritten** (that is the ADR-0017 identity
  contract; record ids must stay stable once decisions reference them).
- `screen status` will nag until this queue is empty, and duplicate-hint banners
  appear on affected records if you screen past them. Do this stage first.

**PRISMA mapping:** *records removed before screening* (duplicates).

## Stage 3 - Title/Abstract Screening

```bash
uv run medscale screen next --reviewer <you> --query Q2 --limit 25
```

What a decision means - **current semantics, read this carefully**:

- `INCLUDE` means *passes title/abstract screening*. It is **not** final inclusion
  in a synthesis: a distinct full-text eligibility stage is designed but not yet
  implemented (see the pending screening-semantics ADR). When in doubt at the
  abstract level, err toward INCLUDE or use `3` (maybe) - exclusion is the decision
  that removes a paper from everything downstream.
- `EXCLUDE` requires a reason from the fixed taxonomy - these become your PRISMA
  exclusion-breakdown numbers, so pick the *primary* reason honestly.
- `3` (maybe / UNCERTAIN) keeps the record in the queue for a later pass. Use it
  freely on a first pass; resolve them on a second.
- `5` (skip) records nothing at all - the record simply comes back next session.

Each decision is appended immediately to
`data/litdb/screening/review_log.jsonl` with your reviewer id, timestamp, software
version, and git commit. Ctrl+C loses nothing.

**Correcting mistakes** - any time, including long after the session:

```bash
uv run medscale screen amend --record <id-prefix> --reviewer <you>
```

The correction is a *new* event recording both the old and new decision plus your
stated reason; the original decision remains in the log. This is how a systematic
review is supposed to work: the audit trail shows the mistake *and* the fix. If the
record already has extracted evidence, `amend` warns you before you proceed.

**PRISMA mapping:** *Screening* (records screened / excluded, with reasons).
`uv run medscale stats` gives the counts at any moment.

## Stage 4 - Evidence Extraction

Once records are INCLUDEd:

```bash
uv run medscale extract --limit 5
```

For each included record you extract **atomic claims** - one falsifiable statement
at a time, optionally structured as PICO (population / intervention / comparator /
outcome) with an effect measure. Guidance:

- A claim should be quotable in a paper: *"Grammar-constrained decoding eliminated
  structural validity errors in generated FHIR resources"* - not a topic label.
- One record can yield several claims; press Enter on an empty claim to move to the
  next record.
- **Abstracts are what you currently have.** For claims that need full-text
  support, extract conservatively and note it - the full-text eligibility stage
  arrives before any synthesis-grade extraction campaign.

Every object is saved the moment you confirm it (a crash loses nothing) and is
immediately **rule-verified** - which is the next stage, happening inline.

## Stage 5 - Verification

You will see two checks run on every extraction:

```
[ok] source_reference: source record resolves in corpus
[ok] provenance_anchor: raw-response hash matches an archived payload
```

`source_verified` means the claim's source record exists in the corpus **and** its
provenance hash matches a verbatim archived API payload - the claim is anchored to
bytes that were actually retrieved, not to a memory of them. A failed check leaves
the object `unverified` (it is kept, honestly labeled, and `medscale check` will
keep you aware of it). No model, no heuristic, no judgment call participates in
verification - it either resolves mechanically or it does not.

## Stage 6 - Snapshot

At any citable milestone (end of screening, end of extraction, before a paper):

```bash
uv run medscale snapshot
```

This writes `data/litdb/snapshots/<id>.json` where `<id>` is a content hash of the
knowledge state: corpus, screening log, evidence store, resolutions. Capture time
and git commit are recorded but deliberately **excluded from the identity** - the
same knowledge state always hashes to the same id, on any machine, in any decade.

To prove a tree matches a published snapshot:

```bash
uv run medscale snapshot --verify data/litdb/snapshots/<id>.json
```

`VERIFIED` = byte-for-byte match. `MISMATCH` names exactly which artifact drifted -
which is *expected* if work happened since capture, and *alarming* only if nothing
should have changed. See [Troubleshooting](troubleshooting.md).

## Stage 7 - Benchmarks (optional, advanced)

When your extracted evidence is ready to ground a benchmark, a spec is created
against a **snapshot** (so the benchmark's knowledge state is frozen) with
human-annotated gold evidence. Then:

```bash
uv run medscale bench list
uv run medscale bench validate <benchmark-id>    # gold still resolves? snapshot intact?
uv run medscale bench run <benchmark-id> --system gold-oracle   # ceiling = 1.0
uv run medscale bench run <benchmark-id> --system empty         # floor  = 0.0
```

Benchmark creation is currently a library task (see `medscale.bench`), deliberately
not a prompt-driven CLI: gold sets deserve more care than an interactive loop.

## Stage 8 - Reporting

Everything a PRISMA flow diagram needs is machine-readable:

```bash
uv run medscale stats > artifacts/stats-$(date +%Y%m%d).json
```

- `screening.prisma.*` - identified / deduplicated / screened / included /
  excluded / pending, with the exclusion-reason breakdown.
- `corpus.*` - by source, year, tier, query, domain.
- `evidence.*` - objects by study type, verification state, coverage.

In your methods section, cite: the installed Python package version (`medscale --version`), the
snapshot id, and the git commit. Those three values let anyone reconstruct and
verify your exact evidence base.

---

## The contract you are working under

1. **Nothing under `data/litdb` is ever hand-edited.** The CLIs are the only
   writers; logs are append-only; stores are content-addressed.
2. **One reviewer writes at a time.** Multi-reviewer concurrency is a designed
   future stage, not a current capability.
3. **Corrections are events, not edits.** `amend`, never a text editor.
4. **Commit after every session** - `medscale check` before and after.
5. **When the tooling and this guide disagree, the tooling is right** - and please
   record the discrepancy as an issue; this guide is maintained with the code.

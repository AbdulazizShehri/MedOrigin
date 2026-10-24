# MedOrigin — pinned historical dataset compatibility replay

**Date:** 2026-10-24. **Result: persisted-format compatibility NOT established.**
This is a local synthetic engineering evidence receipt, not ADR-0044 acceptance,
a migration design, independent security review or release authorization.

## Scope

- **Historical source:** immutable `v0.2.0` target
  `d2e651a55c92f2218aca49acaa5b7bd18a75f096`.
- **Candidate source under test:** draft #598 commit
  `4a763f662ff3b82323da45ef0816e312a596207c`.
- **Environment:** isolated local Windows experiments on CPython
  3.11.15, 3.12.13 and 3.14.7, each running the same deterministic,
  **synthetic-only** one-record corpus and license policy.
- Source `src/medscale/` was exported directly from **two Git commit
  objects** and invoked via isolated `PYTHONPATH` subprocesses.
  Historical `v0.2.0`, protected `main`, frozen MRL-0809 project/lock
  files and all original research receipts were left untouched.

## Observed results — identical for all three Python interpreters

| Tested artifact | Freeze exit | v0.2 validator exit | Candidate validator exit | Manifest checksum |
| --- | ---: | ---: | ---: | --- |
| Historical `v0.2.0` synthetic output | 1 | 1 | 1 | **MISMATCH** |
| Candidate synthetic output | 0 | 1 | 0 | **MATCH** |

The historical validator reports both a missing `license.json` checksum
artifact and a `manifest.json` SHA-256 mismatch on its own output; the
candidate validator flags the historical manifest checksum mismatch. For
the candidate-created output, the historical validator reports its
`license.json` checksum expectation, while the candidate validator passes.
These are **specific tested validation behaviors**, not a universal
statement about all persisted formats or public CLI compatibility.

### Exact manifest-byte identities (same on 3.11, 3.12 and 3.14)

| Artifact | SHA-256 |
| --- | --- |
| Historical final `manifest.json` | `091a6bdff818d2feed2b4d964f53ddcdf2e0fdc39d39abc7be1918d2e56f7ef2` |
| Historical recorded `checksums/manifest.json.sha256` value | `07b83c008341c7724eb20e1d158d5e4a0877fbd694aa348d9a606636d3f263bf` |
| Candidate final `manifest.json` | `998b30ba87b850f5e6ff0a4ceb935d3f2a91177a646ca43ab77c9937230f167a` |
| Candidate recorded `checksums/manifest.json.sha256` value | `998b30ba87b850f5e6ff0a4ceb935d3f2a91177a646ca43ab77c9937230f167a` |

### Historical byte-preservation checks

Against both *historical-generated* and *candidate-generated* frozen
synthetic datasets, three commands through the **current** CLI:
`freeze`, `manifest --write`, and `init --write`, each returned exit
code **2**. Every resulting file-path/byte-hash snapshot remained
**identical before and after** all three attempts.

This proves only the tested protective behavior, not that a future data
migration would be correct. Existing historical bytes must never be
silently repaired, re-signed, or overwritten in place.

## Reproduce without a checkout switch or public release

From a repository clone containing the historical commit object:

```shell
python scripts/audit_historical_dataset_compatibility.py \
  --repo . \
  --json-out historical_synthetic_receipt.json
```

The command exports only pinned source trees from Git, constructs all
test datasets inside a temporary directory, executes isolated local
subprocesses, snapshots file SHA-256 values, and writes an inspectable
machine-readable JSON receipt. The CLI now reports
`KNOWN_INCOMPATIBILITY_REPRODUCED_ONLY` **only** when the documented
historical/current freeze, checksum, validator and immutable-writer matrix
matches its audited baseline; any missing evidence, changed exit code,
unexpected compatibility result or mutated dataset returns `BLOCKED` with a
nonzero exit code. The replay additionally binds the computed manifest digest
and the checksum-file digest to actual per-file SHA-256 snapshot values: a
self-consistent but forged checksum pair no longer passes simply because its
matching/nonmatching boolean remains unchanged. The checksum receipt check
accepts LF and historical CRLF file endings while still binding the exact
snapshot bytes; this prevents Windows/Linux newline differences from
masquerading as source or format compatibility. This is a **regression detector of known incompatibility**,
not a claim that old and new formats have become compatible. GitHub CI's
read-only static jobs rerun the comparison under Python 3.11 and 3.12 using
complete Git history; receipts stay in temporary runner storage. The command
does **not** install software, download data, modify an existing dataset, change tags, use patient/PHI data, or
publish any package. `historical_synthetic_receipt.json` is a local
output; do not confuse it with a project release or an independent review.

**Remaining release work:** owner decision on ADR-0044 versus
successor-root identity, independent source/artifact review
([#603](https://github.com/AbdulazizShehri/MedOrigin/issues/603)),
full public and persisted compatibility disposition/migration policy,
GitHub-native v-tag governance by an authorized administrator, and
a later explicit publication decision. The isolated Core package
remains an unpublished proposal under draft
[#598](https://github.com/AbdulazizShehri/MedOrigin/pull/598).

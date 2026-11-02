# MedOrigin D2 source boundary — aliased APIs and nested source layout

Date: 2026-11-02 (Asia/Riyadh). Experimental synthetic-only Rust D2, strictly nonpublishing.

## Exact parent and changed scope

- Parent Draft #754: `c8e2a8861304f337ae808b0e92bc1a20a829191a`.
- RED test-only commit: `68dd713d22d3c9d4c22e36ba050377c5dec088f1`; test file Git blob `c24e8b84f799b7a96b1ddbea3e86bd360b231fa8`.
- GREEN implementation commit: `48cdc7a5554fb194c45d92ae56d4f5fcd022b27b`.
- Initial CI workflow HEAD: `b4333a7e997de7ddbcff29648bb4b744b3e3f271`.
- Only test harness, read-only CI workflow and this evidence document changed. No product `src/`, Cargo.toml/lock, frozen Python research metadata, OS policies, release workflows or artifacts changed.

## Reproducer and fix

The original heuristic scanned only `std::net::` and root-level `.rs` files. The synthetic adversarial `use std::net;` import was not rejected. Brace-group aliases, `include!`, path-based module indirection and nested source directories also escaped the narrow source review gate.

The updated heuristic normalizes whitespace before testing selected forbidden APIs and refuses source inclusion/path directives. The source-layout gate requires exactly the three ordinary, non-symlink root files `app.rs`, `lib.rs`, `main.rs`; an extra nested directory or unreviewed file fails closed. A synthetic owned temporary nested-directory fixture verifies rejection, then deletes only that fixture. This conservative policy intentionally requires code review for new source layouts.

## Native test-first and hosted proof

- **RED:** authorized Windows 11, Rust 1.97.1, source fetched by exact Git commit; `git hash-object` matched the test blob `c24e8b84f799b7a96b1ddbea3e86bd360b231fa8`. Direct `rustc --edition=2024 --test` run of the adversarial test failed with `source-only guard missed dangerous indirection: use std::net;`, exit **101**, one failed.
- **GREEN:** authorized Windows, clean detached checkout at code SHA `48cdc7a5554fb194c45d92ae56d4f5fcd022b27b`; direct `rustc --edition=2024 --test` all **6 PASS**, 0 fail/ignored; `rustfmt --edition 2024 --check` exit 0.
- **Hosted exact workflow HEAD `b4333a7e997de7ddbcff29648bb4b744b3e3f271`:** [GitHub PR run 41370847214](https://github.com/AbdulazizShehri/MedOrigin/actions/runs/41370847214) **COMPLETED SUCCESS 2/2 jobs**. Raw Windows job 125040787977: **6/6 PASS**; raw Ubuntu job 125040788285: **6/6 PASS**. Both pinned Rust 1.97.1 and checked rustfmt; no skipped tests. Source-only; no GUI or network packet observation.
- This evidence document is a later append-only commit. Do **not** misattribute earlier native or hosted execution to the later document HEAD unless separately rerun.

## Security boundaries

This is a **conservative source-review tripwire**, not a full Rust parser, static analyzer, dependency audit, runtime sandbox or independent zero-egress proof. It cannot eliminate all alias/macro/FFI evasion; further code review is mandatory. D1 Windows #662 actual WebView2 network egress remains NO-GO; D2 Linux #673 zbus5 transitive maintenance notices remain unresolved. Mac spoken VoiceOver #676, Python optional extras #622, independent human security #603 and owner version/ADR/publication #574 remain open. No patient data, release, installer, registry upload, protected-main merge, security policy changes or approval bypass.

At verification, GitHub repository visibility was **public**, even though all changes remain Draft and unpublished as binaries. GitHub branch `main` was `dd84bb7b4177fbc169a04370772610ec66fa41df`, `protected=true`; detailed branch-protection API was inaccessible to the integration. No branch policy changed.

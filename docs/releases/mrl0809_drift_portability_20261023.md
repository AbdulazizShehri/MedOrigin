# MRL-0809 source-drift test portability qualification

**Date:** 2026-10-23
**Issue:** https://github.com/AbdulazizShehri/MedOrigin/issues/599
**Status:** Proposed test semantics correction; independent cross-platform checks required. No scientific or release authority.

## Observed Windows failure and its cause

The original regression expected aggregate machine-state generation to raise
MachineStateGenerationError when a test clone committed a one-newline change
to a Git source bound by the frozen MRL-0809 v1 static manifest. The Git blob
really changed, as established by distinct before/after SHA-256 values.

However, MRL-0800 is PLANNED, and MRL-0809 depends on it. The state projector
uses Python short-circuit evaluation for predecessor closure and the special
gate. When a predecessor is not closed, the special gate is not invoked;
MRL-0809 remains PLANNED, not ELIGIBLE or CLOSED_CANONICAL.

The direct validate_static_prerequisites(repo, changed_commit) call separately
raises MRL0809PrerequisiteGateError for the mismatched source file. The
original test therefore required an exception from a branch that was not
executed under the current state. This is not evidence that modified source
was accepted, but it exposes a gap between direct gate refusal and aggregate
projection exception expectations.

## Proposed stronger and precise negative-test contract

1. Prove unmodified committed source passes the frozen v1 static manifest
   and that the manifest bytes themselves have not been rewritten.
2. Prove the mutated source file changes the committed Git blob, not merely
   working-tree bytes or platform-dependent line endings.
3. Require direct static-prerequisite validation to raise the exact
   source-drift error against the mutated Git commit.
4. Require the aggregate machine state to remain MRL-0809 = PLANNED,
   without claiming that short-circuited validation was executed.
5. Check that behavior on hosted Linux and Windows, Python 3.11 and 3.12.

The test does not use xfail, skip, allow-failure, or platform exceptions.
The new read-only workflow uses a pinned checkout and uv setup and
does not carry release or write permissions.

## Scope and limits

This proposal changes only a test assertion, a new diagnostic workflow and
this explanatory document. It does not change existing source-gate code,
historical v1/v2 manifests, source-binding hashes, dependency locks, frozen
research records, trusted receipts, scientific claims, release flags or model
execution. No public distribution, tag, upload or clinical use is authorized.

The new test ensures direct source-integrity refusal and non-promotion under
today's incomplete predecessor. It does NOT establish unconditional static
validation on every aggregate projector call. If that behavior is required,
design and qualify a successor research identity rather than silently
editing sources that the historical v2 manifest binds by exact SHA-256.

Keep issue #599 open until independent review and hosted matrix evidence
are complete. Keep the software release tracker #574 NO-GO until its
remaining controls have been separately satisfied.

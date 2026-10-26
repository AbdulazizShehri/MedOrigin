# ADR-0045 cross-host archive comparison (read-only)

**Scope:** Unapproved synthetic-only Core *proposal*, not a publisher or an accepted ADR.
No tag, merge into protected main, package upload, clinical data, or release is authorized.

For two independently built distributions from the **same exact Git commit**, run:

```bash
python scripts/compare_medorigin_base_only_archives.py \
  --repo . \
  --left /path/to/windows-dist \
  --right /path/to/macos-dist
```

For two **independent builds on one canonical platform**, append
`--require-identical` to reject any outer-archive byte differences rather than
merely report them. The Linux nonpublishing PR rehearsal invokes this strict
mode on freshly staged independent builds, without uploading artifacts.

Each directory must contain exactly the qualified `medscale-0.3.0` Wheel and
sdist. The script first runs the strict source-to-Git verifier **on both
directories**, including exact committed bytes, dependency metadata,
RECORD, ZIP/TAR physical envelope limits, and the staged empty
`.gitignore` sentinel. An invalid artifact is **BLOCKED**, never compared
as evidence of safe packaging.

The report distinguishes:

- Full archive SHA-256 identity (Wheel and sdist separately).
- A canonical digest of sorted member names and uncompressed member bytes.
- ZIP creator-system, timestamp, file-mode, compression and other header
  differences; TAR member metadata changes; gzip fixed-header differences.
- Decompressed full TAR byte identity, including padding and raw member headers,
  to distinguish unchanged TAR data from OS-specific gzip compression.
- Exact compressed ZIP member-stream fingerprints, distinguishing unchanged
  Wheel payload files from different deflate outputs and ZIP creator metadata.

A passing member comparison **does not** imply byte-identical archives.
Where archives differ, investigate build toolchain, compression and header
serialization; never just post-process or rezip a candidate and treat old
source-bound receipts as applying to the new binary. Pin the exact toolchain,
run fresh Windows/macOS/Linux qualification, and obtain independent review.

Outputs always keep `publication_authorized=false`,
`adr_0045_accepted=false`, and `independent_review_complete=false`.

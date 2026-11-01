# D1 guarded MXC preview entrypoint qualification — 2026-11-01

**NONPUBLISHING / synthetic-only / NO PHI / release remains NO-GO.**
This is a candidate **developer invocation path**. It is NOT installed as
the mandatory application entrypoint, does not prevent someone directly
running the executable outside MXC, does not handle production signing and
does not establish Windows kernel packet-level/DNS confinement.

## Problem addressed

The existing native WebView2 qualification explicitly launched D1 using the
MXC SDK and proved four UIAutomation journeys and socket polling. The normal
desktop debug executable, however, remains directly runnable without MXC.
An operator may unintentionally bypass the isolation harness. The new
candidate entrypoint, `tests/windows-mxc-d1-guarded-preview-launch.mjs`,
**has no fallback to direct process spawning**. It refuses a launch unless
all of the following are true:

- The host is a stable Windows Node 24.21+ or 26.8+ runtime.
- The input is the expected named synthetic-only D1 preview executable at
  a canonical absolute path, with a complete user-supplied pinned SHA-256.
- Every path component can be resolved without symlinks/junctions;
  the executable is a regular nonempty file with matching SHA-256.
- The native MXC SDK is evaluated *after* successful admission;
  `getPlatformSupport()` supports ProcessContainer with zero reported
  isolation warnings.
- The native request explicitly uses `containment.type='process'`,
  deny-by-default egress and ingress, host loopback deny, UI containment,
  a read-only executable path, an isolated writable ephemeral scratch
  directory and a limited temporary environment.
- The binary's SHA-256 still matches just before launch and immediately
  after `run()` returns. MXC warnings or premature process exit fail closed.
  The GUI run uses a finite **35-second timeout**. This is a bounded
  preview observation: timeout is expected, not product shutdown proof.
- The scratch directory is removed on success or failure; cleanup
  problems force nonzero status. No data from the container is accepted as
  clinical evidence and nothing is released.

**Race/security caveat:** Two source hashes are not an immutable file
handle or code-signing attestation; same-user modification between the
last hash and OS image open remains possible. Node's path checks cover
ordinary symlinks and Windows junctions but do not claim exhaustive
NTFS reparse-point enforcement. A direct executable launch still
bypasses this optional wrapper. Production needs an accepted trusted
launch/bootstrap model and independent review.

## Actual Windows execution — source and native evidence

- Source held in stacked **Draft PR #797**, based on the previously
  qualified D1 MXC Node admission work. No protected-main change.
- Authorized interactive non-admin Windows desktop; supported local Node
  `v24.22.1`, SDK `@microsoft/mxc-sdk@1.0.1` installed **offline**
  from the existing local npm cache into a disposable D: QA folder.
- Reused the *older, separately approved, unpublished* synthetic D1 debug
  executable (NOT a newly rebuilt binary from this PR) with SHA-256
  `7eceea367a05ce60576d633ff48f593d8dbff9ed2a56ff227d37c2280759b74a`.
- Pure Node tests on Windows: initial **3/3 PASS** for pinned file,
  wrong hash, mutable/swap failure, wrong filename, real Windows
  Junction/symlink rejection and no direct uncontained fallback.
- Two negative real-process attempts:
  - system Node `v24.19.0` refused with
    `D1_MXC_NODE_RUNTIME_NO_GO`, exit **1** before native MXC import.
  - supported Node with intentionally incorrect SHA-256 refused with
    `D1_MXC_GUARDED_LAUNCH_NO_GO`, exit **1**.
- Native *guarded launcher* on supported Node + **correct pinned binary**
  returned `D1_GUARDED_UNPUBLISHED_MXC_TIMEOUT_OBSERVED_RELEASE_STILL_NO_GO`,
  exit **0**, with bounded sandbox runtime. This is launch-path evidence;
  **no UIAutomation was attached to this particular wrapper run**.
  Earlier real D1 GUI evidence in the separate MXC UIA test remains
  independent of this wrapper.
- First hosted Windows Actions CI on commit `c93b6534` correctly
  **failed** in the path admission test: the Windows hosted runner's
  temp-path canonical spelling differed from the syntactic input despite
  no symlink detected. This is a real portability defect in the new
  preflight, not a kernel-containment failure. Updated preflight at
  `ff549ef7` to accept Windows canonical aliases *only after checking
  each component for symlinks/junctions*, while still requiring the
  canonical target filename to be the expected D1 exe.
- Reran preflight after the correction on authorized Windows: **3/3 PASS**
  including actual junction rejection. Added a fourth child-process test
  at `bdf52435` ensuring invalid admission exits nonzero before
  optional MXC module resolution: latest **4/4 PASS**, zero skips/failures.
- Hosted CI source-contract verification for the exact latest head
  must be recorded separately once completed. Hosted CI does not
  launch native MXC or validate OS packet drops.

## Controlled usage

On an **authorized disposable Windows developer session only**, with
a supported Node and a locally installed MXC SDK in the module-resolution
path of this script:

```powershell
$exe = 'D:\\your-disposable-D1-preview\\medorigin-desktop-d1-preview.exe'
$sha = (Get-FileHash -Algorithm SHA256 -LiteralPath $exe).Hash.ToLowerInvariant()
& '<supported-node.exe>' 'experiments/desktop-d1-tauri/tests/windows-mxc-d1-guarded-preview-launch.mjs' $exe $sha
```

The operator must independently approve the executable SHA; deriving the
SHA from arbitrary untrusted bytes is a **test convenience only**, not
an integrity/authenticity claim. This script's SDK is intentionally NOT a
normal D1 product dependency or a distributed entrypoint yet.

## Remaining NO-GO release conditions

1. A reviewed **mandatory** trusted launcher that cannot be bypassed by
   invoking the raw GUI binary, with signed or owner-approved artifact
   identity and a race-safe path/open process.
2. Independently reviewed Windows/WFP packet-level TCP, UDP, DNS,
   IPv4/IPv6 and WebView2 descendant/service/broker egress-denial proof
   over cold start, repeated GUI use, shutdown, restart and upgrade.
3. Independent security review, dependency/license review, owner
   governance and release sign-off (#662, #603, #622, #574).

No PHI, clinical deployment, package publication, public release,
system-wide firewall/audit change, installer, signed artifact,
protected-main merge or remote inference.

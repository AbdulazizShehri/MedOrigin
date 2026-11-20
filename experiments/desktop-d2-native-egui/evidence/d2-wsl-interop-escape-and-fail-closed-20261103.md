# MedOrigin D2: WSL WindowsInterop escape and fail-closed correction (2026-11-03)

**Release state: NO-GO.** This finding corrects the inference in the earlier D2 Linux netns smoke evidence; it does not invalidate observed direct-Linux-socket denials, but it **does** invalidate any claim that a network namespace alone contains every process started by MedOrigin on WSL.

## Actual counterexample on an authorized Windows + Ubuntu/WSL2 host

Host: Windows PC with Ubuntu 26.04 WSL2, Linux kernel 6.18.33.1-microsoft-standard-WSL2.

1. Original host namespace was `net:[4026531833]`. Running `unshare --user --map-root-user --net` produced child `net:[4026532287]` with **zero IPv4 routes and zero IPv6 routes** and only loopback exposed through Linux Netlink.
2. Within the child, `/proc/sys/fs/binfmt_misc/WSLInterop` was still reported **enabled**, with interpreter `/init` and Windows PE magic `4d5a`. The Windows `cmd.exe` file was accessible through `/mnt/c`.
3. A **benign Windows-process startup control only** executed `/mnt/c/Windows/System32/cmd.exe /d /c echo MEDORIGIN_INTEROP_TEST_WINDOWS_PROCESS_STARTS` from that **route-less Linux child namespace**, and it **succeeded**, printing the marker. No remote website, DNS lookup, patient data, or external network request was involved.
4. Attempted unmount of binfmt_misc inside a separate disposable child user/mount/network namespace returned `umount: /proc/sys/fs/binfmt_misc: not mounted`; this does **not** establish that the Windows host broker is isolated or removable by this mechanism. No host-wide WSL configuration or firewall settings were modified.

**Consequence:** WSL Windows-process interop can leave the Linux process/network namespace and create a native Windows process. Even a perfect absence of direct Linux sockets cannot prove that a WSL-hosted app process tree is offline. Any previous MedOrigin WSL netns success report must be treated as **direct-socket-negative-controls only, NOT an OS-containment acceptance**.

## Source-controlled repair

- `tests/linux-private-netns-smoke.py` now invokes `host_windows_broker_preconditions()` immediately after verifying its private Linux netns and **before** SHA validation, socket negative controls, X11 window acceptance or native GUI launch. It refuses with `WSL_WINDOWS_PROCESS_INTEROP_UNCONFINED` whenever the kernel release contains `microsoft`, an inherited `WSL_INTEROP` marker exists, or the `WSLInterop` binfmt registration is present.
- `tests/linux-private-netns-smoke.sh` also refuses WSL **before launching** Xvfb or D-Bus and before running any test socket.
- `tests/test_linux_private_netns_host_interop.py` includes five zero-network unit regressions for Microsoft/WSL kernel, environment marker, registered binfmt handler, ordinary Linux without markers, and refusal before all socket/app operations.
- `tests/linux-wsl-interop-refusal-integration.sh` reproduces both early-rejection paths on an authorized WSL host without launching Windows executables or using any network.

The CI source validator workflow adds the five unit tests plus shell syntax checks. No successful hosted run at latest PR HEAD is claimed.

## Actually executed verification

- Actual Ubuntu/WSL Python unittest: **5/5 PASS**.
- Actual `unshare --user --map-root-user --net` invocation of the corrected Python probe with deliberate absent test binary and pinned host namespace: explicit structured JSON `decision=NO_GO`, `reason=WSL_WINDOWS_PROCESS_INTEROP_UNCONFINED`, `release_authorized=false`. No `negative_controls`, `binary_sha256` or `native_x11_window_seen` field appeared; the refusal occurred **before** sockets or GUI.
- Actual invocation of the shell runner on WSL: nonzero refusal at WSL preflight before any GUI/transport attempt.
- Source-controlled integration regression: **2/2 PASS**, marker `MEDORIGIN_WSL_INTEROP_TWO_INTEGRATION_GATES_PASS_NO_RELEASE`.

## Explicit limits and next qualification

This repairs the *trustworthiness of offline-evidence reporting*; it does NOT close OS isolation. Full acceptance needs a native non-WSL Linux host or a separately proven broker-confined environment, with real Linux GUI/process-tree and attributed DNS/TCP/UDP evidence, plus Windows-specific per-app WFP confinement. A program-independent Unix namespace cannot prove containment of WSL Windows-process interop merely by having no routes. D1 WebView2 blocker #662, Linux dependency #673, macOS spoken accessibility #676, independent security review #603, optional dependencies #622 and owner release/signing #574 remain open.

**No protected main merge, public release, installer, PHI or clinical readiness claim is authorized by this experiment.**

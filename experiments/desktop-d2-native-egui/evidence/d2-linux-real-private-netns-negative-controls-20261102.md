> **SECURITY CORRECTION — 2026-11-03 (supersedes all broad WSL isolation inferences below):** Actual WSL2 WindowsInterop executed `cmd.exe /d /c echo` successfully from inside an otherwise isolated Linux network namespace with no IPv4/IPv6 routes. This is a *host-process broker escape* from Linux namespace constraints. The eight socket-denial observations below remain true for **direct Linux sockets only**, but the previous `LINUX_NETNS_NEGATIVE_CONTROL_PASS_NOT_RELEASE` must **not** be treated as end-to-end MedOrigin offline containment. Updated source-controlled launcher and Python gate now **refuse WSL** with `WSL_WINDOWS_PROCESS_INTEROP_UNCONFINED` before network probes or GUI. New canonical proof: `evidence/d2-wsl-interop-escape-and-fail-closed-20261103.md`. Release stays **NO-GO**.

# MedOrigin D2 — real Linux network-namespace negative controls (2026-11-02)

**Scope: actual native Linux GUI inside WSL2 Ubuntu private user/network namespace. Qualified local experiment, not a release.**

## Source and binary

- Private repository: AbdulazizShehri/MedOrigin, stacked Draft PR #858. GUI source baseline commit: 2d2609b5f0efd9d95739a2ce70d17329f6dbc029. Later commits add scripts only.
- Host: Ubuntu 26.04 LTS on WSL2, Linux kernel 6.18.33.1-microsoft-standard-WSL2. Rust 1.97.1.
- Source-locked offline build: cargo build --offline --locked, PASS, no download.
- Native 64-bit Linux ELF SHA-256: 465f2383fdce9f1d52f244565bddfc0e06ca8713243a72b60723405fe4a0e246. This is a locally compiled, unsigned test executable, NOT a Windows or production artifact.
- Native Linux cargo test --offline --locked --all-targets: 12/12 PASS (six synthetic app tests and six browser/network source-boundary tests).

## OS-isolated real GUI smoke

Source-controlled tests:
- experiments/desktop-d2-native-egui/tests/linux-private-netns-smoke.sh
- experiments/desktop-d2-native-egui/tests/linux-private-netns-smoke.py
- experiments/desktop-d2-native-egui/tests/linux-private-netns-negative-gates.sh

The shell runner creates a new user/network namespace using unshare --user --map-root-user --net BEFORE starting Xvfb, private D-Bus, negative-control sockets and the actual native GUI. All probes refuse to run until host/guest namespace identifiers differ, Netlink shows precisely one DOWN loopback interface, and IPv4/IPv6 route tables have no entries. Important: /sys/class/net in this WSL setup still exposed the host eth0 in a new namespace, so link checks deliberately use ip Netlink, not the host-mounted sysfs listing.

Observed on the first real GUI run: host network namespace net:[4026531833], guest net:[4026532289]. On the repeated exact source run: host net:[4026531833], new guest net:[4026532287]. All checks confirmed a distinct guest, DOWN loopback only, zero IPv4 routes and zero IPv6 routes.

Real X11 window title starting "MedOrigin Native Rust" was detected using xwininfo -root -tree. Native application stayed running after detection; namespace constraints were rechecked; its owned process was terminated and reaped, with owned_app_process_stopped=true. This is a real GUI launch, not just compilation or a fake window.

## Actual kernel-denied negative controls

After verifying the isolated namespace and BEFORE launching the application:
- IPv4 TCP connect to documentation-reserved 192.0.2.7:9: denied errno 101 (ENETUNREACH).
- IPv4 UDP port 53 send to 192.0.2.7: denied errno 101.
- IPv6 TCP connect to documentation-reserved 2001:db8::7:9: denied errno 99 (EADDRNOTAVAIL).
- IPv6 UDP port 53 send to 2001:db8::7: denied errno 99.

After the native X11 window was visible and WHILE the actual MedOrigin process was still running, all four negative controls repeated and were refused with the SAME error codes. This is 8/8 socket denials. These are direct TCP/UDP transport tests only; UDP port 53 is a DNS-transport-like test, not independent monitoring of all OS resolver behavior. IPv6 errno 99 indicates unavailable source address, not observed dropped packets. No external socket attempt occurred outside the prevalidated private namespace.

The actual machine-readable test ended:
- decision: LINUX_NETNS_NEGATIVE_CONTROL_PASS_NOT_RELEASE
- native_x11_window_seen: true
- app_stayed_running: true
- owned_app_process_stopped: true
- release_authorized: false
- os_enforced_cross_platform_offline_proven: false
- clinical_data_used: false

## Test-first failure and private dependency repair

First attempt refused success because real GUI exited: missing runtime libxkbcommon-x11.so. Cached Ubuntu package archives for libxkbcommon-x11-0 and libxcb-xkb1 were already available. Both archives were unpacked into the disposable test directory using dpkg-deb -x and used only with test-specific LD_LIBRARY_PATH. No apt install, download, host firewall mutation or global library change was performed. The second test succeeded.

## Fail-closed regressions (4/4 PASS)

The source-controlled linux-private-netns-negative-gates.sh ran four actual refusal tests, all before any socket attempt:
1. Running in original host network namespace => NOT_IN_PRIVATE_NETWORK_NAMESPACE.
2. Omitting explicit opt-in => EXPLICIT_EXPERIMENT_OPT_IN_MISSING.
3. Adding a blackhole route ONLY inside a separate child namespace => UNEXPECTED_NETWORK_ROUTE.
4. Bringing loopback UP ONLY inside another child namespace => LOOPBACK_INTERFACE_UP.

All four returned NO_GO with nonzero status; no Windows host network state or global configuration was changed.

## Unresolved security scope and release blockers

This is a qualified LOCAL Linux direct-network-namespace negative-control experiment only. It is NOT packet capture, DNS/WFP audit, OS-wide descendant broker tracking, full 12-case keyboard/UI acceptance, Windows host interop escape confinement, independently reviewed Linux distribution packaging, D1 Windows WebView2 egress remediation (#662), macOS spoken VoiceOver (#676), Linux zbus5 dependency advisory remediation (#673), optional core extras #622, independent security signoff #603, or owner release approval #574.

Keep PR #858 as unmerged Draft, keep NO-GO for public/clinical use, and do not publish. Next qualifying work: independent packet and process attribution on actual supported platforms plus a controlled negative test, without treating this result as cross-platform zero-egress proof.

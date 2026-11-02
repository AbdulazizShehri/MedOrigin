# D1 synthetic preview: navigation and popup hardening (nonpublishing)

2026-11-02, source branch security/medorigin-d1-deny-external-navigation-20261102, stacked above private Draft #833. This protects *document navigation* inside the WebView; it is NOT an OS-enforced network isolation fix.

## Observed security gap and repair

Before this change, the bundled Tauri window was automatically created by configuration and had CSP restrictions, but no dedicated host-side navigation or popup-denial hook. A user-visible webview could be directed to a remote URL without an explicit local-origin decision at this layer.

The source-only test was first run on the exact clean parent and failed 2/2 (RED): automatic WebView creation remained enabled and the local navigation helper did not exist.

The repair changes the window configuration to create=false. The existing Windows primary AppContainer token prerequisite still runs before tauri::Builder::default. Tauri then creates exactly the configured main window in its setup callback with WebviewWindowBuilder::from_config, registering .on_navigation(allow_preview_navigation) and .on_new_window(NewWindowResponse::Deny) before .build().

The pure URL policy allows only the Tauri production origin http://tauri.localhost with no non-default port, the tauri://localhost app origin, and (only in debug builds) the configured development origin http://localhost:1420. It rejects external hosts, userinfo, unexpected ports, other schemes and external popups. It does not accept arbitrary 127.0.0.1 or remote HTTPS. URLs are never logged.

Source contract then passed 2/2 (GREEN), and the combined Windows source/AppContainer contract passed 7/7. Real Windows npm ci --no-audit --no-fund and npm run build completed successfully (Vite v8.3.5, 18 modules transformed). Native Rust cargo test --locked --lib built Tauri 2.12.5 and WebView2 dependencies and ran 4/4 genuine Rust unit tests successfully; one unused import warning from the first run was removed before final SHA qualification. cargo fmt -- --check also passed. The Windows hosted workflow is nonpublishing, requires a source-only contract and a native Rust compilation without application launch; exact final-head hosted checks must be read separately.

## Restrictions and genuine remaining blockers

The view navigation callback only governs navigations exposed to the host. It **cannot** intercept or prove denial of WebView2 Runtime broker traffic, browser background requests, DNS, TCP or UDP outside the webview's document navigation. It cannot replace an independent OS WFP or packet observer. Microsoft documents WebResourceRequested for a subset of resource requests, but that API is also not a global WebView2 broker network policy. Therefore the #662/G3 network denial gate remains BLOCKED, G4/G5 NOT_RUN, G7 BLOCKED. No production or clinical release claim follows from passing these source/native build tests.

No elevation, firewall/WFP/ETW/pktmon policy mutation, packet recording, patient data, frozen pyproject/uv.lock change, protected-main merge, tag, public release or installer is performed. Separate #574, #603, #622, #673, #676 remain unresolved.

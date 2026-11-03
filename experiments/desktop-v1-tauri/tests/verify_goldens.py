#!/usr/bin/env python3
"""Cross-check the four committed synthetic fixture files against the pinned
golden SHA-256 / byte_len values recorded in the spec (§B) and in
src/lib/ipc.ts (MOCK_FIXTURES, browser-mock only) and src-tauri/src/lib.rs
(unit-test drift guard). Fails closed on any mismatch."""

import hashlib
import pathlib
import sys

EXPECTED = {
    "fixture-patient-alpha.json": (425, "1761586b0d285d61b44c8ecd7f37fecac1f627b19cb65a7853ced1ba6b9fce3f"),
    "fixture-allergy-beta.json": (431, "e5719012514e6a858f238da9fcdd46cc61c04828af60c00c31a3887c8f8dddca"),
    "fixture-observation-gamma.json": (474, "b086dee0c87c59ea853a927eba928f9c06703ca14b4dda75e75f46a91511cfb5"),
    "fixture-bundle-delta.json": (533, "7971da4c949507fcfb6d3679f7a63ad2840c93206ea4749545b274f6ee49f399"),
}


def main() -> int:
    fixture_dir = pathlib.Path(__file__).resolve().parent.parent / "src-tauri" / "fixtures"
    failures = []
    if not fixture_dir.is_dir():
        print(f"FAIL: fixture directory missing: {fixture_dir}")
        return 1
    for name, (want_len, want_sha) in sorted(EXPECTED.items()):
        path = fixture_dir / name
        if not path.is_file():
            failures.append(f"{name}: missing")
            continue
        data = path.read_bytes()
        sha = hashlib.sha256(data).hexdigest()
        crlf = b"\r\n" in data
        ok = len(data) == want_len and sha == want_sha and not crlf
        status = "PASS" if ok else "FAIL"
        print(f"{status} {name}: {len(data)} bytes sha256={sha} crlf={crlf}")
        if not ok:
            failures.append(name)
    if failures:
        print(f"\nGOLDENS FAILED: {', '.join(failures)}")
        return 1
    print("\nGOLDENS OK: 4/4 fixtures match pinned SHA-256 and byte_len (LF-only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Static, dependency-free verification of the Inkling tooling handoff."""
from pathlib import Path
import re

root = Path(__file__).resolve().parent
required = {
    "TOOLCHAIN_AND_QUALITY_GATES.md": [
        "google/elephant-goldfish-model",
        "tester-army/e2e",
        "playwright.dev",
        "impeccable.style",
        "Paper Desktop MCP",
        "Alibaba Open Code Review",
        "PStack",
        "E2E_TELEMETRY_DISABLED=1",
        "DO_NOT_TRACK=1",
        "Goldfish",
        "UI Automation",
    ],
    "INKLING_MASTER_PROMPT.md": [
        "Elephant-Goldfish",
        "TesterArmy E2E",
        "Playwright Test",
        "Impeccable",
        "D1 Tauri",
        "D2 native",
        "Ink",
    ],
    "README.md": [
        "TOOLCHAIN_AND_QUALITY_GATES.md",
        "INKLING_MASTER_PROMPT.md",
    ],
    "INKLING_HANDOFF.md": [
        "TOOLCHAIN_AND_QUALITY_GATES.md",
        "INKLING_MASTER_PROMPT.md",
    ],
}
for filename, terms in required.items():
    text = (root / filename).read_text(encoding="utf-8")
    for term in terms:
        assert term in text, f"{filename}: required {term!r} absent"
for filename in ("README.md", "INKLING_HANDOFF.md"):
    text = (root / filename).read_text(encoding="utf-8")
    for relative in re.findall(r"\]\(([^)]+)\)", text):
        if relative.startswith("http") or relative.startswith("#") or "/" in relative and relative.startswith("sandbox:"):
            continue
        candidate = root / relative.split("#", 1)[0]
        assert candidate.is_file(), f"{filename}: missing local link {relative}"
print("PASS: Inkling toolchain, master prompt, and local Markdown targets")

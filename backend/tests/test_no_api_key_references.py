import re
from pathlib import Path

ALLOWED_FILES = {
    "backend/tests/test_no_api_key_references.py",
    # Historical planning/spec documents — read-only, not production code
    "docs/superpowers/plans/2026-04-13-auth-multi-user.md",
    "docs/superpowers/specs/2026-04-13-auth-multi-user-design.md",
}


def test_no_api_key_references() -> None:
    root = Path(__file__).resolve().parents[2]
    pattern = re.compile(r"\bAPI_KEY\b")
    offenders: list[str] = []
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {".git", "node_modules", ".next", "dist", ".venv", ".worktrees"} for part in path.parts):
            continue
        rel = path.relative_to(root).as_posix()
        if rel in ALLOWED_FILES:
            continue
        if path.suffix not in {".py", ".ts", ".tsx", ".js", ".md", ".example"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if pattern.search(text):
            offenders.append(rel)
    assert not offenders, f"stale API_KEY references: {offenders}"

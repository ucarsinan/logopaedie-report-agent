from pathlib import Path


def test_readme_mentions_new_auth_system() -> None:
    root = Path(__file__).resolve().parents[2]
    text = (root / "README.md").read_text(encoding="utf-8")
    for needle in ("JWT", "Resend", "BACKEND_URL", "2FA"):
        assert needle in text, f"README missing: {needle}"

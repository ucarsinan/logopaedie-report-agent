from pathlib import Path

REQUIRED = [
    "JWT_SECRET",
    "SERVICE_TOKEN",
    "RESEND_API_KEY",
    "RESEND_FROM_EMAIL",
    "BACKEND_URL",
    "SESSION_ENCRYPTION_KEY",
]


def test_env_example_lists_all_new_vars() -> None:
    root = Path(__file__).resolve().parents[2]
    content = (root / ".env.example").read_text()
    missing = [k for k in REQUIRED if k not in content]
    assert not missing, f"missing from .env.example: {missing}"

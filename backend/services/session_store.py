"""Redis-backed session store for managing anamnesis conversations."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid

from upstash_redis import Redis

from exceptions import SessionExpiredError, SessionNotFoundError
from models.schemas import ChatMessage, UploadedMaterial

logger = logging.getLogger(__name__)

_SESSION_TIMEOUT_SECONDS = 24 * 60 * 60  # 24 hours
_KEY_PREFIX = "session:"

# ── Optional Fernet encryption ───────────────────────────────────────────────
_fernet = None
_encryption_key = os.environ.get("SESSION_ENCRYPTION_KEY")
if _encryption_key:
    try:
        from cryptography.fernet import Fernet
        _fernet = Fernet(_encryption_key.encode() if isinstance(_encryption_key, str) else _encryption_key)
        logger.info("Session encryption enabled.")
    except Exception as e:
        logger.warning("SESSION_ENCRYPTION_KEY set but encryption init failed: %s. Continuing without encryption.", e)


def _encrypt(data: str) -> str:
    """Encrypt data if Fernet is configured, otherwise return as-is."""
    if _fernet is not None:
        return _fernet.encrypt(data.encode()).decode()
    return data


def _decrypt(data: str) -> str:
    """Decrypt data if Fernet is configured, otherwise return as-is."""
    if _fernet is not None:
        return _fernet.decrypt(data.encode()).decode()
    return data


def _get_redis() -> Redis:
    url = os.environ.get("KV_REST_API_URL") or os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("KV_REST_API_TOKEN") or os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    if not url or not token:
        raise RuntimeError(
            "KV_REST_API_URL and KV_REST_API_TOKEN (or UPSTASH_REDIS_REST_URL/TOKEN) must be set."
        )
    return Redis(url=url, token=token)


class Session:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.status: str = "anamnesis"
        self.report_type: str | None = None
        self.chat_history: list[ChatMessage] = []
        self.collected_data: dict = {}
        self.materials: list[UploadedMaterial] = []
        self.materials_consent: bool = False
        self.generated_report: dict | None = None
        self.therapy_plan_mode: bool = False
        self.created_at: float = time.time()
        self._version: int = 0

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > _SESSION_TIMEOUT_SECONDS

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "status": self.status,
            "report_type": self.report_type,
            "chat_history": [m.model_dump() for m in self.chat_history],
            "collected_data": self.collected_data,
            "materials": [m.model_dump() for m in self.materials],
            "materials_consent": self.materials_consent,
            "generated_report": self.generated_report,
            "therapy_plan_mode": self.therapy_plan_mode,
            "created_at": self.created_at,
            "_version": self._version,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Session:
        s = cls.__new__(cls)
        s.session_id = data["session_id"]
        s.status = data["status"]
        s.report_type = data.get("report_type")
        s.chat_history = [ChatMessage(**m) for m in data.get("chat_history", [])]
        s.collected_data = data.get("collected_data", {})
        s.materials = [UploadedMaterial(**m) for m in data.get("materials", [])]
        s.materials_consent = data.get("materials_consent", False)
        s.generated_report = data.get("generated_report")
        s.therapy_plan_mode = data.get("therapy_plan_mode", False)
        s.created_at = data.get("created_at", time.time())
        s._version = data.get("_version", 0)
        return s


class SessionStore:
    def create(self) -> Session:
        session_id = uuid.uuid4().hex[:12]
        session = Session(session_id)
        self._save(session)
        return session

    def get(self, session_id: str) -> Session | None:
        redis = _get_redis()
        raw = redis.get(f"{_KEY_PREFIX}{session_id}")
        if raw is None:
            return None
        decrypted = _decrypt(raw) if isinstance(raw, str) else json.dumps(raw)
        data = json.loads(decrypted) if isinstance(decrypted, str) else decrypted
        session = Session.from_dict(data)
        if session.is_expired:
            redis.delete(f"{_KEY_PREFIX}{session_id}")
            return None
        return session

    def get_or_raise(self, session_id: str) -> Session:
        """Get a session or raise SessionNotFoundError."""
        session = self.get(session_id)
        if session is None:
            raise SessionNotFoundError("Session nicht gefunden oder abgelaufen.")
        return session

    def save(self, session: Session) -> None:
        session._version += 1
        self._save(session)

    def _save(self, session: Session) -> None:
        redis = _get_redis()
        serialized = json.dumps(session.to_dict())
        encrypted = _encrypt(serialized)
        redis.set(
            f"{_KEY_PREFIX}{session.session_id}",
            encrypted,
            ex=_SESSION_TIMEOUT_SECONDS,
        )


# Singleton instance
store = SessionStore()

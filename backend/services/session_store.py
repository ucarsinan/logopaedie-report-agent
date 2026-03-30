"""Redis-backed session store for managing anamnesis conversations."""

from __future__ import annotations

import json
import os
import time
import uuid

from upstash_redis import Redis

from models.schemas import ChatMessage, UploadedMaterial

_SESSION_TIMEOUT_SECONDS = 2 * 60 * 60  # 2 hours
_KEY_PREFIX = "session:"


def _get_redis() -> Redis:
    url = os.environ["UPSTASH_REDIS_REST_URL"]
    token = os.environ["UPSTASH_REDIS_REST_TOKEN"]
    return Redis(url=url, token=token)


class Session:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.status: str = "anamnesis"
        self.report_type: str | None = None
        self.chat_history: list[ChatMessage] = []
        self.collected_data: dict = {}
        self.materials: list[UploadedMaterial] = []
        self.generated_report: dict | None = None
        self.created_at: float = time.time()

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
            "generated_report": self.generated_report,
            "created_at": self.created_at,
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
        s.generated_report = data.get("generated_report")
        s.created_at = data.get("created_at", time.time())
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
        data = json.loads(raw) if isinstance(raw, str) else raw
        session = Session.from_dict(data)
        if session.is_expired:
            redis.delete(f"{_KEY_PREFIX}{session_id}")
            return None
        return session

    def save(self, session: Session) -> None:
        self._save(session)

    def _save(self, session: Session) -> None:
        redis = _get_redis()
        redis.set(
            f"{_KEY_PREFIX}{session.session_id}",
            json.dumps(session.to_dict()),
            ex=_SESSION_TIMEOUT_SECONDS,
        )


# Singleton instance
store = SessionStore()

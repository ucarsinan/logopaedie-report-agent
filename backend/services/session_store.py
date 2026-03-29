"""In-memory session store for managing anamnesis conversations."""

from __future__ import annotations

import time
import uuid

from backend.models.schemas import ChatMessage, UploadedMaterial

_SESSION_TIMEOUT_SECONDS = 2 * 60 * 60  # 2 hours


class Session:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.status: str = "anamnesis"  # anamnesis | materials | generating | complete
        self.report_type: str | None = None
        self.chat_history: list[ChatMessage] = []
        self.collected_data: dict = {}
        self.materials: list[UploadedMaterial] = []
        self.generated_report: dict | None = None
        self.created_at: float = time.time()

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > _SESSION_TIMEOUT_SECONDS


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self) -> Session:
        self._cleanup_expired()
        session_id = uuid.uuid4().hex[:12]
        session = Session(session_id)
        self._sessions[session_id] = session
        return session

    def get(self, session_id: str) -> Session | None:
        session = self._sessions.get(session_id)
        if session is None or session.is_expired:
            self._sessions.pop(session_id, None)
            return None
        return session

    def _cleanup_expired(self) -> None:
        expired = [sid for sid, s in self._sessions.items() if s.is_expired]
        for sid in expired:
            del self._sessions[sid]


# Singleton instance
store = SessionStore()

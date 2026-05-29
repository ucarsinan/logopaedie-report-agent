"""Singleton service instances and FastAPI dependency providers."""

from dataclasses import dataclass
from functools import lru_cache
from uuid import UUID

from services.anamnesis_engine import AnamnesisEngine
from services.audit_service import AuditService
from services.email_service import EmailService
from services.encryption_service import EncryptionService
from services.groq_client import GroqService
from services.password_service import PasswordService
from services.patient_service import PatientService
from services.phonological_analyzer import PhonologicalAnalyzer
from services.report_comparator import ReportComparator
from services.report_generator import ReportGenerator
from services.soap_generator import SOAPGenerator
from services.text_suggester import TextSuggester
from services.therapy_planner import TherapyPlanner
from services.token_service import TokenService
from services.totp_service import TOTPService

# ── Singletons (instantiated once at import time) ─────────────────────────
groq_service = GroqService()
anamnesis_engine = AnamnesisEngine(groq_service)
report_generator = ReportGenerator(groq_service)
phonological_analyzer = PhonologicalAnalyzer(groq_service)
therapy_planner = TherapyPlanner(groq_service)
report_comparator = ReportComparator(groq_service)
text_suggester = TextSuggester(groq_service)
soap_generator = SOAPGenerator(groq_service)


# ── Depends() providers ───────────────────────────────────────────────────
def get_groq_service() -> GroqService:
    return groq_service


def get_anamnesis_engine() -> AnamnesisEngine:
    return anamnesis_engine


def get_report_generator() -> ReportGenerator:
    return report_generator


def get_phonological_analyzer() -> PhonologicalAnalyzer:
    return phonological_analyzer


def get_therapy_planner() -> TherapyPlanner:
    return therapy_planner


def get_report_comparator() -> ReportComparator:
    return report_comparator


def get_text_suggester() -> TextSuggester:
    return text_suggester


def get_soap_generator() -> SOAPGenerator:
    return soap_generator


# ── Auth service singletons (lru_cache — env vars must be set before first call) ─
@lru_cache(maxsize=1)
def get_password_service() -> PasswordService:
    return PasswordService()


@lru_cache(maxsize=1)
def get_token_service() -> TokenService:
    return TokenService()


@lru_cache(maxsize=1)
def get_totp_service() -> TOTPService:
    return TOTPService()


@lru_cache(maxsize=1)
def get_email_service() -> EmailService:
    return EmailService()


@lru_cache(maxsize=1)
def get_audit_service() -> AuditService:
    return AuditService()


@lru_cache(maxsize=1)
def get_encryption_service() -> EncryptionService:
    return EncryptionService()


@lru_cache(maxsize=1)
def get_patient_service() -> PatientService:
    return PatientService(get_encryption_service())


@lru_cache(maxsize=1)
def get_challenge_store():  # type: ignore[return]
    """Return a ChallengeStore backed by the standard Redis client."""
    from redis_client import get_redis
    from services.challenge_store import ChallengeStore

    return ChallengeStore(get_redis())


# ── Auth service wiring ────────────────────────────────────────────────────────

from fastapi import Depends, HTTPException, Request, status  # noqa: E402
from sqlmodel import Session, select  # noqa: E402

from database import get_db  # noqa: E402
from models.auth import User  # noqa: E402
from services.auth_service import AuthService  # noqa: E402


@lru_cache(maxsize=1)
def _auth_service_singleton() -> AuthService:
    import os

    return AuthService(
        password=get_password_service(),
        tokens=get_token_service(),
        email=get_email_service(),
        audit=get_audit_service(),
        totp=get_totp_service(),
        challenges=get_challenge_store(),
        auto_verify=not bool(os.getenv("RESEND_API_KEY")),
    )


def get_auth_service() -> AuthService:
    return _auth_service_singleton()


@dataclass(frozen=True, slots=True)
class AuthIdentity:
    """Lightweight authenticated caller built straight from the JWT payload.

    Used by endpoints that only need the user id (and optionally role / session
    hash) and would otherwise pay for a Postgres round-trip on every request.
    For endpoints that need the persisted ``User`` row (email, verification
    state, lock status, …) use ``get_current_user`` instead.
    """

    id: UUID
    role: str
    sid: str | None


def _identity_from_request(request: Request) -> AuthIdentity | None:
    """Build an ``AuthIdentity`` from the JWT payload populated by the
    ``JWTAuthMiddleware``. Returns ``None`` for anonymous callers and for
    payloads with a malformed ``sub`` claim."""
    state_user = getattr(request.state, "user", None)
    if not state_user:
        return None
    try:
        uid = UUID(state_user["id"])
    except (KeyError, TypeError, ValueError):
        return None
    return AuthIdentity(
        id=uid,
        role=state_user.get("role", "user"),
        sid=state_user.get("sid"),
    )


def get_optional_user(request: Request) -> AuthIdentity | None:
    """Optional auth dependency — no DB hit.

    The JWT signature and expiry were already validated by ``JWTAuthMiddleware``;
    the prior implementation additionally fetched the ``User`` row from Postgres
    on every authenticated request. None of the endpoints using this dependency
    (``backend/routers/sessions.py``) read anything beyond ``user.id``, and
    revocation / lock / verification checks live on the login path, not the
    request-time path. So the DB round-trip is pure overhead — skip it.
    """
    return _identity_from_request(request)


def get_current_user(
    identity: AuthIdentity | User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> User:
    """Required auth dependency — returns the persisted ``User`` row.

    Kept DB-backed because downstream routers (``auth``, ``patients``,
    ``reports``, ``soap``, ``exports``, ``therapy_plans``, ``admin``, …) read
    fields beyond ``id``/``role`` and some mutate the row directly.

    Composed on top of ``get_optional_user`` so that tests overriding the
    optional dep transparently override ``current_user`` as well. The override
    is allowed to hand back either an ``AuthIdentity`` (production path) or a
    ready-made ``User`` row (test convenience — many existing fixtures inject a
    ``User`` object directly into ``get_optional_user``).
    """
    if identity is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication_required")
    if isinstance(identity, User):
        return identity
    user = db.exec(select(User).where(User.id == identity.id)).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication_required")
    return user


def get_admin_user(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_only")
    return user

"""Singleton service instances and FastAPI dependency providers."""

from functools import lru_cache

from services.anamnesis_engine import AnamnesisEngine
from services.audit_service import AuditService
from services.email_service import EmailService
from services.groq_client import GroqService
from services.password_service import PasswordService
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

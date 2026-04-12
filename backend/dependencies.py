"""Singleton service instances and FastAPI dependency providers."""

from services.groq_client import GroqService
from services.anamnesis_engine import AnamnesisEngine
from services.report_generator import ReportGenerator
from services.phonological_analyzer import PhonologicalAnalyzer
from services.therapy_planner import TherapyPlanner
from services.report_comparator import ReportComparator
from services.text_suggester import TextSuggester
from services.soap_generator import SOAPGenerator

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

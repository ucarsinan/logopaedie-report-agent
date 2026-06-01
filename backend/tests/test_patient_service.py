from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from models.auth import User  # noqa: F401
from models.patient import Patient
from models.report_record import ReportRecord  # noqa: F401


@pytest.fixture
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(eng)
    yield eng
    SQLModel.metadata.drop_all(eng)


@pytest.fixture
def enc_svc(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setenv("PATIENT_ENCRYPTION_KEY", key)
    from services.encryption_service import EncryptionService

    return EncryptionService()


def test_generate_system_id_first_patient(engine, enc_svc):
    from services.patient_service import PatientService

    svc = PatientService(enc_svc)
    year = datetime.now(UTC).year
    with Session(engine) as db:
        sid = svc._next_system_id(db, year)
    assert sid == f"PAT-{year}-0001"


def test_generate_system_id_increments(engine, enc_svc):
    from services.patient_service import PatientService

    svc = PatientService(enc_svc)
    year = datetime.now(UTC).year
    user_id = uuid4()
    with Session(engine) as db:
        p = Patient(
            system_id=f"PAT-{year}-0001",
            pseudonym=f"PAT-{year}-0001",
            user_id=user_id,
            realname_enc=b"e",
            birthdate_enc=b"e",
        )
        db.add(p)
        db.commit()
        sid = svc._next_system_id(db, year)
    assert sid == f"PAT-{year}-0002"


def test_to_response_decrypts_pii(engine, enc_svc):
    from services.patient_service import PatientService

    svc = PatientService(enc_svc)
    user_id = uuid4()
    year = datetime.now(UTC).year
    with Session(engine) as db:
        p = Patient(
            system_id=f"PAT-{year}-0001",
            pseudonym="Sonnenschein",
            user_id=user_id,
            realname_enc=enc_svc.encrypt("Max Mustermann"),
            birthdate_enc=enc_svc.encrypt("2019-03-15"),
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        result = svc.to_response(p)
    assert result["realname"] == "Max Mustermann"
    assert result["birthdate"] == "2019-03-15"
    assert result["pseudonym"] == "Sonnenschein"


# ── I2 deferred: PatientService error-path coverage ──────────────────────────


def test_create_patient_exhausts_retries_when_system_id_always_collides(engine, enc_svc, monkeypatch):
    """If _next_system_id keeps returning a colliding id, create_patient must
    retry _MAX_RETRIES (5) times and then raise RuntimeError. The Patient
    model declares ``system_id`` as ``unique=True`` so the second insert
    triggers an IntegrityError that the service catches + retries.
    """
    from services.patient_service import PatientService

    svc = PatientService(enc_svc)
    year = datetime.now(UTC).year
    colliding = f"PAT-{year}-9999"

    # Pre-seed a patient with the id that the patched generator will keep returning
    with Session(engine) as db:
        db.add(
            Patient(
                system_id=colliding,
                pseudonym=colliding,
                user_id=uuid4(),
                realname_enc=enc_svc.encrypt("Existing"),
                birthdate_enc=enc_svc.encrypt("2000-01-01"),
            )
        )
        db.commit()

    monkeypatch.setattr(PatientService, "_next_system_id", lambda self, db, year: colliding)

    with pytest.raises(RuntimeError, match="Could not generate unique system_id"), Session(engine) as db:
        svc.create_patient(
            db,
            uuid4(),
            realname="Collider",
            birthdate="2010-01-01",
        )


def test_create_patient_retries_then_succeeds_after_single_collision(engine, enc_svc, monkeypatch):
    """One collision should NOT bubble up — the service rolls back and
    retries up to 5 times. Patch _next_system_id to yield the collider
    first, then a fresh id on the second call.
    """
    from services.patient_service import PatientService

    svc = PatientService(enc_svc)
    year = datetime.now(UTC).year
    colliding = f"PAT-{year}-0001"
    fresh = f"PAT-{year}-7777"

    with Session(engine) as db:
        db.add(
            Patient(
                system_id=colliding,
                pseudonym=colliding,
                user_id=uuid4(),
                realname_enc=enc_svc.encrypt("Existing"),
                birthdate_enc=enc_svc.encrypt("2000-01-01"),
            )
        )
        db.commit()

    seq = iter([colliding, fresh])
    monkeypatch.setattr(PatientService, "_next_system_id", lambda self, db, year: next(seq))

    with Session(engine) as db:
        p = svc.create_patient(db, uuid4(), realname="Resilient", birthdate="2010-01-01")
    assert p.system_id == fresh


def test_update_patient_does_not_enforce_ownership_contract(engine, enc_svc):
    """Contract documentation: ``PatientService.update_patient`` operates on
    the Patient object handed to it without any user_id check — ownership
    enforcement lives in the router (`routers/patients._get_active_or_404`).

    This test pins the contract so a future refactor that *adds* an
    ownership guard at the service level is recognized as a deliberate
    behavior change, not an accidental regression.
    """
    from services.patient_service import PatientService

    svc = PatientService(enc_svc)
    user_a = uuid4()
    with Session(engine) as db:
        p = svc.create_patient(db, user_a, realname="Owned By A", birthdate="2010-01-01")
        # Caller would normally check ``p.user_id == user_b`` BEFORE calling
        # the service. The service itself happily applies the update.
        updated = svc.update_patient(db, p, pseudonym="overwritten")
    assert updated.pseudonym == "overwritten"
    assert updated.user_id == user_a  # unchanged


def test_get_active_or_404_excludes_soft_deleted_patient(engine, enc_svc):
    """``_get_active_or_404`` (router helper) must NOT return a patient
    whose ``deleted_at`` is set. Drives the helper directly with an
    in-memory SQLite to avoid the FastAPI stack.
    """
    from fastapi import HTTPException

    from routers.patients import _get_active_or_404
    from services.patient_service import PatientService

    svc = PatientService(enc_svc)
    user_id = uuid4()
    with Session(engine) as db:
        p = svc.create_patient(db, user_id, realname="Soft Delete Me", birthdate="2010-01-01")
        p.deleted_at = datetime.now(UTC)
        db.add(p)
        db.commit()
        with pytest.raises(HTTPException) as exc:
            _get_active_or_404(p.id, user_id, db)
        assert exc.value.status_code == 404


def test_derive_age_group_future_birthdate_returns_kind(engine, enc_svc):
    """A date in the future yields a negative age, which the
    ``years < 13`` branch silently maps to "kind". Documenting the actual
    behavior — the function does NOT validate that dob <= today.
    """
    from services.patient_service import derive_age_group

    future = "2999-01-01"
    assert derive_age_group(future) == "kind"


def test_derive_age_group_pre_1900_returns_erwachsen(engine, enc_svc):
    """Very old birthdates parse fine and fall through to "erwachsen" —
    ``date.fromisoformat`` accepts years from 0001 upward. Pinning the
    contract: no exception, no None, just the adult bucket.
    """
    from services.patient_service import derive_age_group

    assert derive_age_group("1800-06-15") == "erwachsen"


def test_derive_age_group_empty_string_returns_none(engine, enc_svc):
    """Empty / blank inputs are unparseable (date.fromisoformat raises
    ValueError) and the service returns None per its except-clause.
    """
    from services.patient_service import derive_age_group

    assert derive_age_group("") is None
    assert derive_age_group("   ") is None

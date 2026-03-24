from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.core import services
from apps.db.models import Base
from tests.support import load_demo_bundle


SQLALCHEMY_TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)
def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_demo_observation_package_contains_engineering_blocks() -> None:
    session = TestingSessionLocal()
    try:
        object_id = load_demo_bundle(session)
        package = services.build_observation_package(session, object_id)
    finally:
        session.close()

    assert package.export_version == "v1.1"
    assert package.information_sufficiency_index.domain_scores.measurement_score > 0
    assert package.identification_readiness_report.geometry_ready in {
        "identifiable",
        "qualitative_only",
        "not_ready",
    }
    assert package.element_state_observation_records
    record = package.element_state_observation_records[0]
    assert "support_type" in record.boundary_conditions
    assert "material_grade_actual" in record.actual_material
    assert record.data_coverage.temporal_coverage >= 0
    assert isinstance(record.critical_missing_data_list, list)
    assert isinstance(record.test_history, list)
    assert record.role_criticality == "high"
    assert record.consequence_class == "CC3"
    assert record.identification_priority == "high"
    assert record.degradation_mechanisms == ["corrosion", "fatigue"]
    assert package.defects[0].material_family == "steel"
    assert package.defects[0].section_loss_percent == 4.5
    assert package.defects[0].bolt_condition == "minor corrosion"


def test_demo_information_sufficiency_golden_scores() -> None:
    session = TestingSessionLocal()
    try:
        object_id = load_demo_bundle(session)
        index = services.calculate_information_sufficiency(session, object_id)
    finally:
        session.close()

    assert round(index.total_score, 4) == 0.6722
    assert round(index.level_scores.identification_readiness_score, 4) == 0.6443
    assert round(index.domain_scores.structural_model_score, 4) == 0.8425
    assert round(index.domain_scores.measurement_score, 4) == 0.6159

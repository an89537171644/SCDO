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


def test_exported_element_state_contains_mechanics_ready_blocks() -> None:
    session = TestingSessionLocal()
    try:
        object_id = load_demo_bundle(session)
        package = services.build_observation_package(session, object_id)
    finally:
        session.close()

    record = next(item for item in package.element_state_observation_records if item.section_properties["section_name"])

    assert record.section_properties["section_name"] == "I-1600x450x20x32"
    assert record.section_properties["inertia_x"] == 0.182
    assert record.actual_material["steel_grade_actual"] == "C325"
    assert record.actual_material["corrosion_loss_mm"] == 1.2
    assert record.boundary_conditions["support_kz"] == 150000.0
    assert record.boundary_conditions["joint_flexibility_z"] == 0.008
    assert isinstance(record.critical_missing_data_by_element, list)

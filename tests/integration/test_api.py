from __future__ import annotations

from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.api.main import app
from apps.db.models import Base
from apps.db.session import get_db_session


SQLALCHEMY_TEST_DATABASE_URL = "sqlite+pysqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def override_get_db() -> Generator:
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


app.dependency_overrides[get_db_session] = override_get_db


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_full_api_flow_creates_bundle_and_exports_package() -> None:
    client = TestClient(app)

    object_response = client.post(
        "/objects",
        json={
            "object_code": "OBJ-API-1",
            "object_name": "API object",
            "function_type": "bridge",
            "current_operational_mode": "normal",
        },
    )
    assert object_response.status_code == 201
    object_id = object_response.json()["id"]

    element_response = client.post(
        "/elements",
        json={
            "object_id": object_id,
            "hierarchy_type": "element",
            "name": "Beam",
            "element_type": "beam",
            "length": 20.0,
            "coordinates_global": "0,0,0",
            "material_type": "steel",
            "material_grade_design": "C345",
            "support_type": "hinged"
        },
    )
    assert element_response.status_code == 201
    element_id = element_response.json()["id"]

    defect_response = client.post(
        "/defects",
        json={
            "object_id": object_id,
            "element_id": element_id,
            "defect_type": "corrosion",
            "location_on_element": "midspan",
            "detection_date": "2026-01-01T00:00:00Z"
        },
    )
    assert defect_response.status_code == 201

    channel_response = client.post(
        "/channels",
        json={
            "object_id": object_id,
            "element_id": element_id,
            "channel_code": "CH-1",
            "sensor_type": "LVDT",
            "measured_quantity": "deflection",
            "unit": "mm",
            "spatial_location": "midspan"
        },
    )
    assert channel_response.status_code == 201
    channel_id = channel_response.json()["id"]

    measurement_response = client.post(
        "/measurements",
        json={
            "object_id": object_id,
            "element_id": element_id,
            "channel_id": channel_id,
            "timestamp": "2026-01-01T01:00:00Z",
            "value": 3.4,
            "unit": "mm",
            "source_type": "monitoring"
        },
    )
    assert measurement_response.status_code == 201
    measurement_id = measurement_response.json()["id"]

    quality_response = client.post(
        "/quality-records",
        json={
            "object_id": object_id,
            "element_id": element_id,
            "entity_type": "measurement",
            "entity_id": measurement_id,
            "source_type": "monitoring",
            "traceability_score": 0.95
        },
    )
    assert quality_response.status_code == 201

    analytics_response = client.get(f"/analytics/objects/{object_id}/information-sufficiency")
    assert analytics_response.status_code == 200
    assert analytics_response.json()["p0_score"] >= 0.8

    package_response = client.get(f"/exports/objects/{object_id}/observation-package")
    assert package_response.status_code == 200
    package = package_response.json()
    assert package["object"]["id"] == object_id
    assert len(package["elements"]) == 1
    assert len(package["measurements"]) == 1
    assert "information_sufficiency_index" in package


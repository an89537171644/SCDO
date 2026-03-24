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


def setup_function() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def _create_object_element_channel(client: TestClient) -> tuple[str, str, str]:
    object_response = client.post(
        "/objects",
        json={
            "object_code": "OBJ-IMP-1",
            "object_name": "Import object",
            "function_type": "bridge",
        },
    )
    object_id = object_response.json()["id"]
    element_response = client.post(
        "/elements",
        json={
            "object_id": object_id,
            "hierarchy_type": "element",
            "name": "Beam",
            "structural_role": "primary",
            "element_type": "beam",
            "geometry_type": "line",
            "length": 12.0,
            "coordinates_global": "0,0,0",
            "material_type": "steel",
            "material_grade_design": "C345",
            "support_type": "hinged",
        },
    )
    element_id = element_response.json()["id"]
    channel_response = client.post(
        "/channels",
        json={
            "object_id": object_id,
            "element_id": element_id,
            "channel_code": "CH-IMP-1",
            "sensor_type": "LVDT",
            "measured_quantity": "deflection",
            "unit": "mm",
            "spatial_location": "midspan",
        },
    )
    channel_id = channel_response.json()["id"]
    return object_id, element_id, channel_id


def test_measurement_import_rejects_invalid_unit_for_profile() -> None:
    app.dependency_overrides[get_db_session] = override_get_db
    client = TestClient(app)
    try:
        object_id, element_id, channel_id = _create_object_element_channel(client)

        response = client.post(
            "/imports/measurements/json",
            json=[
                {
                    "object_id": object_id,
                    "element_id": element_id,
                    "channel_id": channel_id,
                    "timestamp": "2026-03-01T10:00:00Z",
                    "value": 4.2,
                    "unit": "kN",
                    "spatial_location": "midspan",
                }
            ],
        )

        assert response.status_code == 400
        assert "единица" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_db_session, None)


def test_measurement_import_rejects_duplicate_timestamps() -> None:
    app.dependency_overrides[get_db_session] = override_get_db
    client = TestClient(app)
    try:
        object_id, element_id, channel_id = _create_object_element_channel(client)

        response = client.post(
            "/imports/measurements/json",
            json=[
                {
                    "object_id": object_id,
                    "element_id": element_id,
                    "channel_id": channel_id,
                    "timestamp": "2026-03-01T10:00:00Z",
                    "value": 4.2,
                    "unit": "mm",
                    "spatial_location": "midspan",
                },
                {
                    "object_id": object_id,
                    "element_id": element_id,
                    "channel_id": channel_id,
                    "timestamp": "2026-03-01T10:00:00Z",
                    "value": 4.3,
                    "unit": "mm",
                    "spatial_location": "midspan",
                },
            ],
        )

        assert response.status_code == 400
        assert "дубликат" in response.json()["detail"].lower()
    finally:
        app.dependency_overrides.pop(get_db_session, None)

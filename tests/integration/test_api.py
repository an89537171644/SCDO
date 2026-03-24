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
            "address": "Test address",
            "function_type": "bridge",
            "responsibility_class": "KS-1",
            "design_service_life": 100,
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
            "structural_role": "primary",
            "role_criticality": "high",
            "consequence_class": "CC3",
            "identification_priority": "high",
            "degradation_mechanisms": ["corrosion", "fatigue"],
            "element_type": "beam",
            "geometry_type": "line",
            "section_name": "I-600",
            "section_family": "I-beam",
            "length": 20.0,
            "coordinates_global": "0,0,0",
            "material_type": "steel",
            "material_grade_design": "C345",
            "material_grade_actual": "C325",
            "steel_grade_design": "C345",
            "steel_grade_actual": "C325",
            "elastic_modulus_design": 210000.0,
            "elastic_modulus_actual": 205000.0,
            "strength_design": 345.0,
            "strength_actual": 330.0,
            "material_density": 7850.0,
            "support_type": "hinged",
            "support_stiffness": 5000.0,
            "support_kx": 1000.0,
            "support_ky": 1000.0,
            "support_kz": 2000.0,
            "joint_type": "bolted",
            "joint_flexibility": 0.02,
            "joint_flexibility_x": 0.01
        },
    )
    assert element_response.status_code == 201
    element_payload = element_response.json()
    assert element_payload["role_criticality"] == "high"
    assert element_payload["consequence_class"] == "CC3"
    assert element_payload["identification_priority"] == "high"
    assert element_payload["degradation_mechanisms"] == ["corrosion", "fatigue"]
    element_id = element_payload["id"]

    defect_response = client.post(
        "/defects",
        json={
            "object_id": object_id,
            "element_id": element_id,
            "defect_type": "corrosion",
            "material_family": "steel",
            "element_classifier": "beam",
            "location_on_element": "midspan",
            "detection_date": "2026-01-01T00:00:00Z",
            "corrosion_area": 1.0,
            "corrosion_depth": 1.5,
            "section_loss_percent": 4.0,
            "bolt_condition": "minor corrosion",
            "weld_damage_type": "surface indication",
            "damage_mechanism": "corrosion_fatigue",
            "severity_class": "S2",
            "face_or_zone": "web",
            "local_coordinate": "x=10m",
            "inspection_method": "visual+UT",
            "confidence_severity": 0.8,
            "local_buckling_flag": False,
            "source_type": "inspection"
        },
    )
    assert defect_response.status_code == 201
    defect_payload = defect_response.json()
    assert defect_payload["material_family"] == "steel"
    assert defect_payload["section_loss_percent"] == 4.0
    assert defect_payload["bolt_condition"] == "minor corrosion"

    channel_response = client.post(
        "/channels",
        json={
            "object_id": object_id,
            "element_id": element_id,
            "channel_code": "CH-1",
            "sensor_type": "LVDT",
            "measured_quantity": "deflection",
            "unit": "mm",
            "spatial_location": "midspan",
            "sampling_frequency": 1.0,
            "axis_direction": "Z",
            "sign_convention": "downward_positive",
            "load_case_reference": "traffic",
            "temperature_compensated": True,
            "aggregation_method": "mean_over_window",
            "device_id": "LVDT-1",
            "calibration_reference": "CAL-1",
            "source_type": "monitoring"
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
            "quality_flag": "validated",
            "source_type": "monitoring",
            "method_reference": "sensor-readout",
            "accuracy": 0.1,
            "spatial_location": "midspan",
            "axis_direction": "Z",
            "sign_convention": "downward_positive",
            "load_case_reference": "traffic",
            "temperature_compensated": True,
            "aggregation_method": "mean_over_window",
            "device_id": "LVDT-1",
            "calibration_reference": "CAL-1"
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
            "completeness_score": 0.95,
            "repeatability_score": 0.93,
            "traceability_score": 0.95,
            "identification_suitability_score": 0.9
        },
    )
    assert quality_response.status_code == 201

    analytics_response = client.get(f"/analytics/objects/{object_id}/information-sufficiency")
    assert analytics_response.status_code == 200
    analytics = analytics_response.json()
    assert analytics["p0_score"] >= 0.7
    assert analytics["domain_scores"]["measurement_score"] >= 0.6
    assert analytics["level_scores"]["identification_readiness_score"] >= 0.6
    assert analytics["coverage_by_parameter_group"]["geometry_and_scheme"] >= 0.5
    assert analytics["coverage_by_parameter_group"]["dynamic_response"] >= 0.5

    package_response = client.get(f"/exports/objects/{object_id}/observation-package")
    assert package_response.status_code == 200
    package = package_response.json()
    assert package["export_version"] == "v1.1"
    assert package["object"]["id"] == object_id
    assert len(package["elements"]) == 1
    assert len(package["measurements"]) == 1
    assert "information_sufficiency_index" in package
    element_state = package["element_state_observation_records"][0]
    exported_element = package["elements"][0]
    exported_defect = package["defects"][0]
    assert exported_element["role_criticality"] == "high"
    assert exported_element["consequence_class"] == "CC3"
    assert exported_defect["material_family"] == "steel"
    assert exported_defect["section_loss_percent"] == 4.0
    assert "boundary_conditions" in element_state
    assert "actual_material" in element_state
    assert "section_properties" in element_state
    assert "critical_missing_data_by_element" in element_state
    assert "critical_missing_data_list" in element_state
    assert element_state["role_criticality"] == "high"
    assert element_state["identification_priority"] == "high"
    assert element_state["section_properties"]["section_name"] == "I-600"
    assert element_state["actual_material"]["steel_grade_actual"] == "C325"
    assert element_state["boundary_conditions"]["support_kz"] == 2000.0

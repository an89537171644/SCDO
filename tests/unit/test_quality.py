from __future__ import annotations

from datetime import datetime
from datetime import timezone

from apps.core import quality
from apps.db import models


def test_information_sufficiency_returns_high_score_for_complete_bundle() -> None:
    asset_object = models.AssetObject(
        id="object-1",
        object_code="OBJ-1",
        object_name="Object",
        address="Test address",
        function_type="bridge",
        responsibility_class="KS-1",
        design_service_life=100,
        current_operational_mode="normal",
    )
    element = models.StructuralElement(
        id="element-1",
        object_id="obj",
        hierarchy_type="element",
        name="Beam",
        structural_role="primary",
        element_type="beam",
        geometry_type="line",
        length=12.0,
        coordinates_global="0,0,0",
        material_type="steel",
        material_grade_design="C345",
        material_grade_actual="C325",
        elastic_modulus_design=210000.0,
        elastic_modulus_actual=205000.0,
        strength_design=345.0,
        strength_actual=330.0,
        support_type="hinged",
        support_stiffness=5000.0,
        joint_type="bolted",
        joint_flexibility=0.02,
    )
    defect = models.Defect(
        id="defect-1",
        object_id="obj",
        element_id="element-1",
        defect_type="crack",
        location_on_element="midspan",
        detection_date=datetime.now(timezone.utc),
        crack_width=0.3,
        source_type="inspection",
    )
    channel = models.ObservationChannel(
        id="channel-1",
        object_id="obj",
        element_id="element-1",
        channel_code="CH-1",
        sensor_type="LVDT",
        measured_quantity="deflection",
        unit="mm",
        spatial_location="midspan",
        sampling_frequency=1.0,
        axis_direction="Z",
        sign_convention="downward_positive",
        load_case_reference="traffic",
        temperature_compensated=True,
        aggregation_method="mean_over_window",
        device_id="LVDT-1",
        calibration_reference="CAL-1",
        source_type="monitoring",
    )
    measurement_base_time = datetime.now(timezone.utc)
    measurements = [
        models.Measurement(
            id=f"measurement-{idx}",
            object_id="obj",
            element_id="element-1",
            channel_id="channel",
            timestamp=measurement_base_time.replace(hour=min(23, idx)),
            value=1.2 + (idx * 0.1),
            unit="mm",
            quality_flag="validated",
                source_type="monitoring",
                method_reference="sensor-readout",
                accuracy=0.05,
                spatial_location="midspan",
                axis_direction="Z",
                sign_convention="downward_positive",
                load_case_reference="traffic",
                temperature_compensated=True,
                aggregation_method="mean_over_window",
                device_id="LVDT-1",
                calibration_reference="CAL-1",
            )
        for idx in range(1, 5)
    ]
    environment = models.EnvironmentRecord(
        id="environment-1",
        object_id="obj",
        element_id="element-1",
        timestamp=datetime.now(timezone.utc),
        temperature=10.0,
        humidity=70.0,
        corrosion_aggressiveness="medium",
        load_summary="traffic",
        source_type="weather",
    )
    intervention = models.Intervention(
        id="intervention-1",
        object_id="obj",
        element_id="element-1",
        intervention_type="repair",
        date=datetime.now(timezone.utc),
        description="Protective repair",
        quality_of_execution="good",
        source_type="maintenance",
    )
    test_record = models.TestRecord(
        id="test-1",
        object_id="obj",
        element_id="element-1",
        test_type="UT",
        measured_property="thickness",
        test_value=10.0,
        unit="mm",
        method="UT",
        date=datetime.now(timezone.utc),
        source_type="ndt",
    )
    quality_record = models.DataQualityRecord(
        id="quality-1",
        object_id="obj",
        element_id="element-1",
        entity_type="measurement",
        entity_id="measurement",
        source_type="inspection",
        completeness_score=0.95,
        repeatability_score=0.92,
        traceability_score=0.9,
        identification_suitability_score=0.88,
    )

    index = quality.information_sufficiency_index(
        asset_object=asset_object,
            elements=[element],
            defects=[defect],
            channels=[channel],
            measurements=measurements,
            environment_records=[environment],
            interventions=[intervention],
            tests=[test_record],
            quality_records=[quality_record],
        )

    assert index.total_score >= 0.65
    assert index.level_scores.identification_readiness_score >= 0.65
    assert index.level_scores.identification_ready >= 0.65
    assert index.coverage_by_parameter_group["geometry_and_scheme"] >= 0.5
    assert index.coverage_by_parameter_group["dynamic_response"] >= 0.5
    assert index.quality_weighted_measurement_coverage >= 0.5
    assert index.missing_items == []


def test_identification_readiness_blocks_when_core_p0_fields_missing() -> None:
    asset_object = models.AssetObject(id="object-2", object_code="OBJ-2", object_name="Object")
    index = quality.information_sufficiency_index(
        asset_object=asset_object,
        elements=[],
        defects=[],
        channels=[],
        measurements=[],
        environment_records=[],
        interventions=[],
        tests=[],
        quality_records=[],
    )

    report = quality.identification_readiness(index=index, measurements=[], defects=[], tests=[])

    assert report.readiness_level == "not_ready"
    assert report.geometry_ready == "not_ready"
    assert report.geometry_and_scheme_ready == "not_ready"
    assert report.dynamic_response_ready == "not_ready"
    assert "element.geometry" in report.blocked_parameters


def test_new_criticality_fields_mark_element_as_critical() -> None:
    element = models.StructuralElement(
        id="element-2",
        object_id="obj",
        hierarchy_type="element",
        name="Main beam",
        role_criticality="high",
        consequence_class="CC3",
        identification_priority="high",
    )

    assert quality._is_critical_element(element) is True

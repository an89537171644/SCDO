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
        function_type="bridge",
        current_operational_mode="normal",
    )
    element = models.StructuralElement(
        id="element-1",
        object_id="obj",
        hierarchy_type="element",
        name="Beam",
        element_type="beam",
        length=12.0,
        coordinates_global="0,0,0",
        material_type="steel",
        material_grade_design="C345",
        support_type="hinged",
    )
    defect = models.Defect(
        id="defect-1",
        object_id="obj",
        element_id="elem",
        defect_type="crack",
        location_on_element="midspan",
        detection_date=datetime.now(timezone.utc),
    )
    channel = models.ObservationChannel(
        id="channel-1",
        object_id="obj",
        element_id="elem",
        channel_code="CH-1",
        sensor_type="LVDT",
        measured_quantity="deflection",
        unit="mm",
        spatial_location="midspan",
    )
    measurement = models.Measurement(
        id="measurement-1",
        object_id="obj",
        element_id="elem",
        channel_id="channel",
        timestamp=datetime.now(timezone.utc),
        value=1.2,
        unit="mm",
    )
    environment = models.EnvironmentRecord(
        id="environment-1",
        object_id="obj",
        element_id="elem",
        timestamp=datetime.now(timezone.utc),
        temperature=10.0,
    )
    intervention = models.Intervention(
        id="intervention-1",
        object_id="obj",
        element_id="elem",
        intervention_type="repair",
        date=datetime.now(timezone.utc),
    )
    test_record = models.TestRecord(
        id="test-1",
        object_id="obj",
        element_id="elem",
        test_type="UT",
        measured_property="thickness",
        test_value=10.0,
        unit="mm",
        date=datetime.now(timezone.utc),
    )
    quality_record = models.DataQualityRecord(
        id="quality-1",
        object_id="obj",
        element_id="elem",
        entity_type="measurement",
        entity_id="measurement",
        source_type="inspection",
        traceability_score=0.9,
    )

    index = quality.information_sufficiency_index(
        asset_object=asset_object,
        elements=[element],
        defects=[defect],
        channels=[channel],
        measurements=[measurement],
        environment_records=[environment],
        interventions=[intervention],
        tests=[test_record],
        quality_records=[quality_record],
    )

    assert index.total_score >= 0.95
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
    assert "element.geometry" in report.blocked_parameters

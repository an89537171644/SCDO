from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone

from apps.core import quality, schemas
from apps.db import models


ELEMENT_REQUIREMENT_CODES = {
    "element.geometry",
    "element.material",
    "defect.registry",
    "observation.measurements",
    "quality.traceability",
    "element.boundary_conditions",
    "environment.effects",
    "intervention.history",
    "tests.ndt",
    "measurement.channel_metadata",
}


def _latest_timestamp(*values: datetime | None) -> datetime:
    timestamps = [value for value in values if value is not None]
    return max(timestamps) if timestamps else datetime.now(timezone.utc)


def _build_element_missing_items(
    element: models.StructuralElement,
    *,
    defects: list[models.Defect],
    channels: list[models.ObservationChannel],
    measurements: list[models.Measurement],
    environment_records: list[models.EnvironmentRecord],
    interventions: list[models.Intervention],
    tests: list[models.TestRecord],
    quality_records: list[models.DataQualityRecord],
) -> list[schemas.MissingDataItem]:
    score_map = {
        "element.geometry": quality._element_geometry_score(element),
        "element.material": quality._element_material_score(element),
        "defect.registry": quality._defect_registry_score([element], defects),
        "observation.measurements": quality._measurement_score([element], channels, measurements),
        "quality.traceability": quality._quality_traceability_score(measurements, quality_records),
        "element.boundary_conditions": quality._element_boundary_score(element),
        "environment.effects": quality._environment_score([element], environment_records),
        "intervention.history": quality._intervention_score([element], interventions),
        "tests.ndt": quality._testing_score([element], tests),
        "measurement.channel_metadata": quality._avg(quality._channel_metadata_score(channel) for channel in channels),
    }
    items: list[schemas.MissingDataItem] = []
    for requirement in quality.OBJECT_REQUIREMENTS:
        if requirement.code not in ELEMENT_REQUIREMENT_CODES:
            continue
        coverage = quality._clamp(requirement.extractor(score_map))
        if coverage < requirement.threshold:
            items.append(
                schemas.MissingDataItem(
                    code=requirement.code,
                    priority=requirement.priority,
                    description=requirement.description,
                    rank_score=requirement.rank_score,
                    present=False,
                    coverage=coverage,
                    scope="element",
                    element_id=element.id,
                    element_name=element.name,
                )
            )
    return sorted(items, key=lambda item: (item.priority, -item.rank_score, item.code))


def _build_data_coverage(
    element: models.StructuralElement,
    *,
    defects: list[models.Defect],
    measurements: list[models.Measurement],
    quality_records: list[models.DataQualityRecord],
) -> schemas.DataCoverage:
    temporal_coverage = quality._series_completeness(measurements)
    spatial_coverage = quality._avg(
        [
            1.0 if quality._one_of_present(element.coordinates_global, element.coordinates_local) else 0.0,
            1.0 if any(quality._present(measurement.spatial_location) for measurement in measurements) else 0.0,
            1.0 if any(quality._present(defect.location_on_element) for defect in defects) else 0.0,
        ]
    )
    observation_density = quality._clamp(min((len(measurements) + len(defects)) / 10, 1.0))
    uncertainty_level = quality._clamp(1.0 - quality._quality_traceability_score(measurements, quality_records))
    return schemas.DataCoverage(
        temporal_coverage=temporal_coverage,
        spatial_coverage=spatial_coverage,
        observation_density=observation_density,
        uncertainty_level=uncertainty_level,
    )


def build_element_state_records(
    asset_object: models.AssetObject,
    elements: list[models.StructuralElement],
    defects: list[models.Defect],
    channels: list[models.ObservationChannel],
    measurements: list[models.Measurement],
    environment_records: list[models.EnvironmentRecord],
    interventions: list[models.Intervention],
    tests: list[models.TestRecord],
    quality_records: list[models.DataQualityRecord],
) -> list[schemas.ElementStateObservationRecord]:
    defects_by_element: dict[str, list[models.Defect]] = defaultdict(list)
    channels_by_element: dict[str, list[models.ObservationChannel]] = defaultdict(list)
    measurements_by_element: dict[str, list[models.Measurement]] = defaultdict(list)
    environment_by_element: dict[str, list[models.EnvironmentRecord]] = defaultdict(list)
    interventions_by_element: dict[str, list[models.Intervention]] = defaultdict(list)
    tests_by_element: dict[str, list[models.TestRecord]] = defaultdict(list)
    quality_by_element: dict[str, list[models.DataQualityRecord]] = defaultdict(list)

    for defect in defects:
        defects_by_element[defect.element_id].append(defect)
    for channel in channels:
        channels_by_element[channel.element_id].append(channel)
    for measurement in measurements:
        measurements_by_element[measurement.element_id].append(measurement)
    for environment_record in environment_records:
        if environment_record.element_id:
            environment_by_element[environment_record.element_id].append(environment_record)
    for intervention in interventions:
        interventions_by_element[intervention.element_id].append(intervention)
    for test in tests:
        tests_by_element[test.element_id].append(test)
    for quality_record in quality_records:
        if quality_record.element_id:
            quality_by_element[quality_record.element_id].append(quality_record)

    records: list[schemas.ElementStateObservationRecord] = []
    for element in elements:
        element_defects = defects_by_element[element.id]
        element_channels = channels_by_element[element.id]
        element_measurements = sorted(measurements_by_element[element.id], key=lambda item: item.timestamp)
        element_environment = sorted(environment_by_element[element.id], key=lambda item: item.timestamp)
        element_interventions = sorted(interventions_by_element[element.id], key=lambda item: item.date)
        element_tests = sorted(tests_by_element[element.id], key=lambda item: item.date)
        element_quality = quality_by_element[element.id]
        latest_timestamp = _latest_timestamp(
            element_measurements[-1].timestamp if element_measurements else None,
            element_environment[-1].timestamp if element_environment else None,
            element_interventions[-1].date if element_interventions else None,
            element_tests[-1].date if element_tests else None,
            max((item.detection_date for item in element_defects), default=None),
        )

        records.append(
            schemas.ElementStateObservationRecord(
                object_id=asset_object.id,
                element_id=element.id,
                timestamp=latest_timestamp,
                hierarchy_type=element.hierarchy_type,
                structural_role=element.structural_role,
                role_criticality=element.role_criticality,
                consequence_class=element.consequence_class,
                identification_priority=element.identification_priority,
                degradation_mechanisms=element.degradation_mechanisms,
                support_type=element.support_type,
                support_stiffness=element.support_stiffness,
                joint_type=element.joint_type,
                joint_flexibility=element.joint_flexibility,
                material_grade_actual=element.material_grade_actual,
                elastic_modulus_actual=element.elastic_modulus_actual,
                strength_actual=element.strength_actual,
                design_geometry={
                    "geometry_type": element.geometry_type,
                    "length": element.length,
                    "span": element.span,
                    "height": element.height,
                    "thickness": element.thickness,
                    "area": element.area,
                    "coordinates_global": element.coordinates_global,
                    "coordinates_local": element.coordinates_local,
                },
                design_material={
                    "material_type": element.material_type,
                    "material_grade_design": element.material_grade_design,
                    "concrete_class_design": element.concrete_class_design,
                    "steel_grade_design": element.steel_grade_design,
                    "elastic_modulus_design": element.elastic_modulus_design,
                    "strength_design": element.strength_design,
                },
                actual_material={
                    "material_type": element.material_type,
                    "material_grade_actual": element.material_grade_actual,
                    "concrete_class_actual": element.concrete_class_actual,
                    "steel_grade_actual": element.steel_grade_actual,
                    "rebar_class": element.rebar_class,
                    "cover_thickness": element.cover_thickness,
                    "reinforcement_ratio": element.reinforcement_ratio,
                    "rebar_area": element.rebar_area,
                    "carbonation_depth": element.carbonation_depth,
                    "chloride_exposure_class": element.chloride_exposure_class,
                    "weld_type": element.weld_type,
                    "bolt_class": element.bolt_class,
                    "corrosion_loss_mm": element.corrosion_loss_mm,
                    "elastic_modulus_actual": element.elastic_modulus_actual,
                    "strength_actual": element.strength_actual,
                    "material_density": element.material_density,
                },
                section_properties={
                    "section_name": element.section_name,
                    "section_family": element.section_family,
                    "inertia_x": element.inertia_x,
                    "inertia_y": element.inertia_y,
                    "section_modulus_x": element.section_modulus_x,
                    "section_modulus_y": element.section_modulus_y,
                    "torsion_constant": element.torsion_constant,
                    "buckling_length_x": element.buckling_length_x,
                    "buckling_length_y": element.buckling_length_y,
                },
                boundary_conditions={
                    "support_type": element.support_type,
                    "support_stiffness": element.support_stiffness,
                    "support_kx": element.support_kx,
                    "support_ky": element.support_ky,
                    "support_kz": element.support_kz,
                    "support_rx": element.support_rx,
                    "support_ry": element.support_ry,
                    "support_rz": element.support_rz,
                    "joint_type": element.joint_type,
                    "joint_flexibility": element.joint_flexibility,
                    "joint_flexibility_x": element.joint_flexibility_x,
                    "joint_flexibility_y": element.joint_flexibility_y,
                    "joint_flexibility_z": element.joint_flexibility_z,
                },
                data_coverage=_build_data_coverage(
                    element,
                    defects=element_defects,
                    measurements=element_measurements,
                    quality_records=element_quality,
                ),
                critical_missing_data_list=_build_element_missing_items(
                    element,
                    defects=element_defects,
                    channels=element_channels,
                    measurements=element_measurements,
                    environment_records=element_environment,
                    interventions=element_interventions,
                    tests=element_tests,
                    quality_records=element_quality,
                ),
                critical_missing_data_by_element=_build_element_missing_items(
                    element,
                    defects=element_defects,
                    channels=element_channels,
                    measurements=element_measurements,
                    environment_records=element_environment,
                    interventions=element_interventions,
                    tests=element_tests,
                    quality_records=element_quality,
                ),
                current_defects=[schemas.DefectRead.model_validate(item).model_dump() for item in element_defects],
                current_measurements=[schemas.MeasurementRead.model_validate(item).model_dump() for item in element_measurements],
                current_environment=[schemas.EnvironmentRecordRead.model_validate(item).model_dump() for item in element_environment],
                current_operation_mode=asset_object.current_operational_mode,
                intervention_history=[schemas.InterventionRead.model_validate(item).model_dump() for item in element_interventions],
                test_history=[schemas.TestRecordRead.model_validate(item).model_dump() for item in element_tests],
                quality_profile=[schemas.DataQualityRecordRead.model_validate(item).model_dump() for item in element_quality],
            )
        )
    return records


def build_observation_package(
    asset_object: models.AssetObject,
    elements: list[models.StructuralElement],
    defects: list[models.Defect],
    channels: list[models.ObservationChannel],
    measurements: list[models.Measurement],
    environment_records: list[models.EnvironmentRecord],
    interventions: list[models.Intervention],
    tests: list[models.TestRecord],
    media_assets: list[models.MediaAsset],
    quality_records: list[models.DataQualityRecord],
) -> schemas.ObservationPackage:
    index = quality.information_sufficiency_index(
        asset_object=asset_object,
        elements=elements,
        defects=defects,
        channels=channels,
        measurements=measurements,
        environment_records=environment_records,
        interventions=interventions,
        tests=tests,
        quality_records=quality_records,
    )
    readiness = quality.identification_readiness(
        index=index,
        elements=elements,
        measurements=measurements,
        defects=defects,
        tests=tests,
    )
    element_state_records = build_element_state_records(
        asset_object=asset_object,
        elements=elements,
        defects=defects,
        channels=channels,
        measurements=measurements,
        environment_records=environment_records,
        interventions=interventions,
        tests=tests,
        quality_records=quality_records,
    )
    return schemas.ObservationPackage(
        export_version="v1.1",
        object=schemas.AssetObjectRead.model_validate(asset_object),
        elements=[schemas.StructuralElementRead.model_validate(item) for item in elements],
        defects=[schemas.DefectRead.model_validate(item) for item in defects],
        channels=[schemas.ObservationChannelRead.model_validate(item) for item in channels],
        measurements=[schemas.MeasurementRead.model_validate(item) for item in measurements],
        environment_records=[schemas.EnvironmentRecordRead.model_validate(item) for item in environment_records],
        interventions=[schemas.InterventionRead.model_validate(item) for item in interventions],
        tests=[schemas.TestRecordRead.model_validate(item) for item in tests],
        media_assets=[schemas.MediaAssetRead.model_validate(item) for item in media_assets],
        quality_records=[schemas.DataQualityRecordRead.model_validate(item) for item in quality_records],
        element_state_observation_records=element_state_records,
        information_sufficiency_index=index,
        identification_readiness_report=readiness,
        critical_missing_data_list=index.missing_items,
    )

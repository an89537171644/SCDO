from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from datetime import timezone

from apps.core import schemas
from apps.core.quality import identification_readiness
from apps.core.quality import information_sufficiency_index
from apps.db import models


def build_element_state_records(
    asset_object: models.AssetObject,
    elements: list[models.StructuralElement],
    defects: list[models.Defect],
    measurements: list[models.Measurement],
    environment_records: list[models.EnvironmentRecord],
    interventions: list[models.Intervention],
    quality_records: list[models.DataQualityRecord],
) -> list[schemas.ElementStateObservationRecord]:
    defects_by_element: dict[str, list[models.Defect]] = defaultdict(list)
    measurements_by_element: dict[str, list[models.Measurement]] = defaultdict(list)
    environment_by_element: dict[str, list[models.EnvironmentRecord]] = defaultdict(list)
    interventions_by_element: dict[str, list[models.Intervention]] = defaultdict(list)
    quality_by_element: dict[str, list[models.DataQualityRecord]] = defaultdict(list)

    for defect in defects:
        defects_by_element[defect.element_id].append(defect)
    for measurement in measurements:
        measurements_by_element[measurement.element_id].append(measurement)
    for environment_record in environment_records:
        if environment_record.element_id:
            environment_by_element[environment_record.element_id].append(environment_record)
    for intervention in interventions:
        interventions_by_element[intervention.element_id].append(intervention)
    for quality in quality_records:
        if quality.element_id:
            quality_by_element[quality.element_id].append(quality)

    records: list[schemas.ElementStateObservationRecord] = []
    for element in elements:
        latest_timestamp = datetime.now(timezone.utc)
        if measurements_by_element[element.id]:
            latest_timestamp = max(item.timestamp for item in measurements_by_element[element.id])

        records.append(
            schemas.ElementStateObservationRecord(
                object_id=asset_object.id,
                element_id=element.id,
                timestamp=latest_timestamp,
                design_geometry={
                    "geometry_type": element.geometry_type,
                    "length": element.length,
                    "span": element.span,
                    "height": element.height,
                    "thickness": element.thickness,
                    "area": element.area,
                    "coordinates_global": element.coordinates_global,
                },
                design_material={
                    "material_type": element.material_type,
                    "material_grade_design": element.material_grade_design,
                    "material_grade_actual": element.material_grade_actual,
                    "elastic_modulus_design": element.elastic_modulus_design,
                    "strength_design": element.strength_design,
                },
                current_defects=[
                    schemas.DefectRead.model_validate(item).model_dump() for item in defects_by_element[element.id]
                ],
                current_measurements=[
                    schemas.MeasurementRead.model_validate(item).model_dump()
                    for item in sorted(
                        measurements_by_element[element.id], key=lambda measurement: measurement.timestamp
                    )
                ],
                current_environment=[
                    schemas.EnvironmentRecordRead.model_validate(item).model_dump()
                    for item in sorted(environment_by_element[element.id], key=lambda item: item.timestamp)
                ],
                current_operation_mode=asset_object.current_operational_mode,
                intervention_history=[
                    schemas.InterventionRead.model_validate(item).model_dump()
                    for item in sorted(interventions_by_element[element.id], key=lambda item: item.date)
                ],
                quality_profile=[
                    schemas.DataQualityRecordRead.model_validate(item).model_dump()
                    for item in quality_by_element[element.id]
                ],
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
    index = information_sufficiency_index(
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
    readiness = identification_readiness(index=index, measurements=measurements, defects=defects, tests=tests)
    element_state_records = build_element_state_records(
        asset_object=asset_object,
        elements=elements,
        defects=defects,
        measurements=measurements,
        environment_records=environment_records,
        interventions=interventions,
        quality_records=quality_records,
    )

    return schemas.ObservationPackage(
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


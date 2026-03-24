from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from apps.core import schemas
from apps.db import models


QUALITY_OK_FLAGS = {"ok", "validated", "accepted", "good", "trusted", "pass", "usable"}
RESPONSIBILITY_FACTORS = {"KS-3": 0.88, "CC3": 0.88, "KS-2": 0.94, "CC2": 0.94, "KS-1": 1.0, "CC1": 1.0}
STEEL_MATERIALS = {"steel", "metal"}
CONCRETE_MATERIALS = {"concrete", "reinforced_concrete", "rc", "железобетон", "бетон"}


@dataclass(frozen=True)
class Requirement:
    code: str
    priority: str
    description: str
    rank_score: float
    threshold: float
    extractor: Callable[[dict[str, float]], float]


def _present(value: Any) -> bool:
    return value not in (None, "", [], {}, ())


def _text(value: Any) -> str:
    return str(value).strip().lower() if _present(value) else ""


def _clamp(value: float) -> float:
    return round(min(max(value, 0.0), 1.0), 4)


def _avg(values: Iterable[float]) -> float:
    prepared = [float(value) for value in values]
    return _clamp(sum(prepared) / len(prepared)) if prepared else 0.0


def _ratio(numerator: int, denominator: int) -> float:
    return _clamp(numerator / denominator) if denominator else 0.0


def _one_of_present(*values: Any) -> bool:
    return any(_present(value) for value in values)


def _is_critical_element(element: models.StructuralElement) -> bool:
    if _text(element.role_criticality) in {"a", "1", "high", "critical", "p0"}:
        return True
    if _text(element.consequence_class) in {"ks-3", "cc3", "cc-3", "3", "high"}:
        return True
    if _text(element.identification_priority) in {"high", "critical", "p0", "required"}:
        return True
    return _text(element.criticality_group) in {"a", "1", "high", "critical"} or _text(element.structural_role) in {
        "primary",
        "main",
        "girder",
        "column",
        "truss",
        "support",
    }


def _critical_elements(elements: list[models.StructuralElement]) -> list[models.StructuralElement]:
    critical = [element for element in elements if _is_critical_element(element)]
    return critical or elements


def _responsibility_factor(asset_object: models.AssetObject) -> float:
    return RESPONSIBILITY_FACTORS.get((asset_object.responsibility_class or "").upper(), 1.0)


def _element_geometry_score(element: models.StructuralElement) -> float:
    dimension_score = min(
        sum(1 for value in (element.length, element.span, element.height, element.thickness, element.area) if _present(value)) / 2,
        1.0,
    )
    section_score = _avg(
        [
            1.0 if _present(element.section_name) else 0.0,
            1.0 if _present(element.section_family) else 0.0,
            1.0 if _one_of_present(element.inertia_x, element.inertia_y) else 0.0,
            1.0 if _one_of_present(element.section_modulus_x, element.section_modulus_y) else 0.0,
            1.0 if _present(element.torsion_constant) else 0.0,
            1.0 if _one_of_present(element.buckling_length_x, element.buckling_length_y) else 0.0,
        ]
    )
    return _avg(
        [
            1.0 if _present(element.hierarchy_type) else 0.0,
            1.0 if _present(element.name) else 0.0,
            1.0 if _present(element.element_type) else 0.0,
            1.0 if _present(element.geometry_type) else 0.0,
            dimension_score,
            section_score,
            1.0 if _one_of_present(element.coordinates_global, element.coordinates_local) else 0.0,
        ]
    )


def _element_material_score(element: models.StructuralElement) -> float:
    return _avg(
        [
            1.0 if _present(element.material_type) else 0.0,
            1.0 if _present(element.material_grade_design) else 0.0,
            1.0 if _one_of_present(element.elastic_modulus_design, element.strength_design) else 0.0,
            1.0 if _present(element.material_grade_actual) else 0.0,
            1.0 if _one_of_present(element.elastic_modulus_actual, element.strength_actual) else 0.0,
            1.0
            if _one_of_present(
                element.concrete_class_design,
                element.concrete_class_actual,
                element.rebar_class,
                element.cover_thickness,
                element.reinforcement_ratio,
                element.rebar_area,
                element.carbonation_depth,
                element.chloride_exposure_class,
                element.steel_grade_design,
                element.steel_grade_actual,
                element.weld_type,
                element.bolt_class,
                element.corrosion_loss_mm,
                element.material_density,
            )
            else 0.0,
        ]
    )


def _element_boundary_score(element: models.StructuralElement) -> float:
    return _avg(
        [
            1.0 if _present(element.support_type) else 0.0,
            1.0 if _present(element.support_stiffness) else 0.0,
            1.0 if _one_of_present(element.support_kx, element.support_ky, element.support_kz) else 0.0,
            1.0 if _one_of_present(element.support_rx, element.support_ry, element.support_rz) else 0.0,
            1.0 if _present(element.joint_type) else 0.0,
            1.0 if _present(element.joint_flexibility) else 0.0,
            1.0 if _one_of_present(element.joint_flexibility_x, element.joint_flexibility_y, element.joint_flexibility_z) else 0.0,
        ]
    )


def _tree_score(elements: list[models.StructuralElement]) -> float:
    if not elements:
        return 0.0
    with_parent = _ratio(sum(1 for element in elements if _present(element.parent_id)), max(len(elements) - 1, 1))
    return _clamp(
        (0.4 * _avg(1.0 if _present(element.hierarchy_type) else 0.0 for element in elements))
        + (0.35 * _avg(1.0 if _present(element.name) else 0.0 for element in elements))
        + (0.25 * (1.0 if len(elements) == 1 else with_parent))
    )


def _defect_completeness(defect: models.Defect) -> float:
    return _avg(
        [
            1.0 if _present(defect.defect_type) else 0.0,
            1.0 if _present(defect.location_on_element) else 0.0,
            1.0 if _present(defect.detection_date) else 0.0,
            1.0 if _one_of_present(defect.source_type, defect.source_document) else 0.0,
            1.0
            if _one_of_present(
                defect.crack_length,
                defect.crack_width,
                defect.corrosion_area,
                defect.corrosion_depth_or_loss,
                defect.section_loss_estimate,
                defect.material_family,
                defect.element_classifier,
                defect.corrosion_depth,
                defect.section_loss_percent,
                defect.weld_damage_type,
                defect.bolt_condition,
                defect.local_buckling_flag,
                defect.fatigue_crack_length,
                defect.crack_type,
                defect.cover_loss_area,
                defect.rebar_corrosion_class,
                defect.carbonation_depth,
                defect.bond_loss_flag,
                defect.damage_mechanism,
                defect.severity_class,
                defect.face_or_zone,
                defect.local_coordinate,
                defect.growth_rate_estimate,
                defect.inspection_method,
                defect.confidence_severity,
            )
            else 0.0,
        ]
    )


def _channel_metadata_score(channel: models.ObservationChannel) -> float:
    return _avg(
        [
            1.0 if _present(channel.sensor_type) else 0.0,
            1.0 if _present(channel.measured_quantity) else 0.0,
            1.0 if _present(channel.unit) else 0.0,
            1.0 if _present(channel.spatial_location) else 0.0,
            1.0 if _present(channel.axis_direction) else 0.0,
            1.0 if _present(channel.sign_convention) else 0.0,
            1.0 if _present(channel.load_case_reference) else 0.0,
            1.0 if _present(channel.aggregation_method) else 0.0,
            1.0 if _present(channel.device_id) else 0.0,
            1.0 if _present(channel.calibration_reference) else 0.0,
            1.0 if channel.temperature_compensated is not None else 0.0,
            1.0 if _one_of_present(channel.sampling_frequency, channel.source_type) else 0.0,
        ]
    )


def _measurement_metadata_score(measurement: models.Measurement) -> float:
    return _avg(
        [
            1.0 if _present(measurement.source_type) else 0.0,
            1.0 if _present(measurement.method_reference) else 0.0,
            1.0 if _present(measurement.accuracy) else 0.0,
            1.0 if _present(measurement.spatial_location) else 0.0,
            1.0 if _present(measurement.axis_direction) else 0.0,
            1.0 if _present(measurement.sign_convention) else 0.0,
            1.0 if _present(measurement.load_case_reference) else 0.0,
            1.0 if _present(measurement.aggregation_method) else 0.0,
            1.0 if _present(measurement.device_id) else 0.0,
            1.0 if _present(measurement.calibration_reference) else 0.0,
            1.0 if measurement.temperature_compensated is not None else 0.0,
        ]
    )


def _series_completeness(measurements: list[models.Measurement]) -> float:
    if not measurements:
        return 0.0
    timestamps = sorted(measurement.timestamp for measurement in measurements)
    unique_ratio = _ratio(len(set(timestamps)), len(timestamps))
    count_score = min(len(measurements) / 8, 1.0)
    span_score = 0.25 if len(timestamps) == 1 else min(max((timestamps[-1] - timestamps[0]).total_seconds() / 3600, 0.0) / 24, 1.0)
    return _clamp((0.45 * count_score) + (0.35 * span_score) + (0.20 * unique_ratio))


def _defect_registry_score(elements: list[models.StructuralElement], defects: list[models.Defect]) -> float:
    critical_elements = _critical_elements(elements)
    defects_by_element: dict[str, list[models.Defect]] = defaultdict(list)
    for defect in defects:
        defects_by_element[defect.element_id].append(defect)
    coverage = _avg(1.0 if defects_by_element[element.id] else 0.0 for element in critical_elements)
    completeness = _avg(_defect_completeness(defect) for defect in defects)
    return _clamp((0.6 * coverage) + (0.4 * completeness))


def _measurement_score(elements: list[models.StructuralElement], channels: list[models.ObservationChannel], measurements: list[models.Measurement]) -> float:
    critical_elements = _critical_elements(elements)
    measurements_by_element: dict[str, list[models.Measurement]] = defaultdict(list)
    for measurement in measurements:
        measurements_by_element[measurement.element_id].append(measurement)
    critical_coverage = _avg(1.0 if measurements_by_element[element.id] else 0.0 for element in critical_elements)
    quality_ratio = _ratio(sum(1 for measurement in measurements if _text(measurement.quality_flag) in QUALITY_OK_FLAGS), len(measurements))
    series_score = _avg(_series_completeness(records) for records in measurements_by_element.values())
    channel_metadata = _avg(_channel_metadata_score(channel) for channel in channels)
    return _clamp((0.35 * critical_coverage) + (0.25 * quality_ratio) + (0.25 * series_score) + (0.15 * channel_metadata))


def _environment_score(elements: list[models.StructuralElement], environment_records: list[models.EnvironmentRecord]) -> float:
    critical_elements = _critical_elements(elements)
    environment_by_element: dict[str, list[models.EnvironmentRecord]] = defaultdict(list)
    object_level_records = 0
    for record in environment_records:
        if record.element_id:
            environment_by_element[record.element_id].append(record)
        else:
            object_level_records += 1
    coverage = _avg(1.0 if (environment_by_element[element.id] or object_level_records) else 0.0 for element in critical_elements)
    completeness = _avg(
        _avg(
            [
                1.0 if _one_of_present(record.temperature, record.humidity) else 0.0,
                1.0 if _one_of_present(record.corrosion_aggressiveness, record.cyclicity, record.seasonality) else 0.0,
                1.0 if _one_of_present(record.load_summary, record.operation_mode) else 0.0,
                1.0 if _present(record.source_type) else 0.0,
            ]
        )
        for record in environment_records
    )
    return _clamp((0.6 * coverage) + (0.4 * completeness))


def _intervention_score(elements: list[models.StructuralElement], interventions: list[models.Intervention]) -> float:
    critical_elements = _critical_elements(elements)
    interventions_by_element: dict[str, list[models.Intervention]] = defaultdict(list)
    for intervention in interventions:
        interventions_by_element[intervention.element_id].append(intervention)
    coverage = _avg(1.0 if interventions_by_element[element.id] else 0.0 for element in critical_elements)
    completeness = _avg(
        _avg(
            [
                1.0 if _present(intervention.intervention_type) else 0.0,
                1.0 if _present(intervention.date) else 0.0,
                1.0 if _one_of_present(intervention.description, intervention.expected_effect_on_degradation_rate) else 0.0,
                1.0 if _one_of_present(intervention.quality_of_execution, intervention.source_type) else 0.0,
            ]
        )
        for intervention in interventions
    )
    return _clamp((0.55 * coverage) + (0.45 * completeness))


def _testing_score(elements: list[models.StructuralElement], tests: list[models.TestRecord]) -> float:
    critical_elements = _critical_elements(elements)
    tests_by_element: dict[str, list[models.TestRecord]] = defaultdict(list)
    for test in tests:
        tests_by_element[test.element_id].append(test)
    coverage = _avg(1.0 if tests_by_element[element.id] else 0.0 for element in critical_elements)
    completeness = _avg(
        _avg(
            [
                1.0 if _present(test.test_type) else 0.0,
                1.0 if _present(test.measured_property) else 0.0,
                1.0 if _present(test.test_value) else 0.0,
                1.0 if _present(test.unit) else 0.0,
                1.0 if _one_of_present(test.method, test.source_type) else 0.0,
            ]
        )
        for test in tests
    )
    return _clamp((0.55 * coverage) + (0.45 * completeness))


def _quality_traceability_score(measurements: list[models.Measurement], quality_records: list[models.DataQualityRecord]) -> float:
    record_score = _avg(
        _avg(value for value in (record.completeness_score, record.repeatability_score, record.traceability_score, record.identification_suitability_score) if value is not None)
        for record in quality_records
    )
    measurement_metadata = _avg(_measurement_metadata_score(measurement) for measurement in measurements)
    return _clamp((0.65 * record_score) + (0.35 * measurement_metadata))


def _score_map(asset_object: models.AssetObject, elements: list[models.StructuralElement], defects: list[models.Defect], channels: list[models.ObservationChannel], measurements: list[models.Measurement], environment_records: list[models.EnvironmentRecord], interventions: list[models.Intervention], tests: list[models.TestRecord], quality_records: list[models.DataQualityRecord]) -> dict[str, float]:
    critical_elements = _critical_elements(elements)
    return {
        "object.identity": _avg([1.0 if _present(asset_object.object_code) else 0.0, 1.0 if _present(asset_object.object_name) else 0.0, 1.0 if _one_of_present(asset_object.address, asset_object.coordinates) else 0.0]),
        "object.function_type": 1.0 if _present(asset_object.function_type) else 0.0,
        "element.tree": _tree_score(elements),
        "element.geometry": _avg(_element_geometry_score(element) for element in critical_elements),
        "element.material": _avg(_element_material_score(element) for element in critical_elements),
        "defect.registry": _defect_registry_score(elements, defects),
        "observation.measurements": _measurement_score(elements, channels, measurements),
        "quality.traceability": _quality_traceability_score(measurements, quality_records),
        "element.boundary_conditions": _avg(_element_boundary_score(element) for element in critical_elements),
        "environment.effects": _environment_score(elements, environment_records),
        "intervention.history": _intervention_score(elements, interventions),
        "tests.ndt": _testing_score(elements, tests),
        "measurement.channel_metadata": _avg(_channel_metadata_score(channel) for channel in channels),
    }


def _critical_element_coverages(
    elements: list[models.StructuralElement],
    defects: list[models.Defect],
    channels: list[models.ObservationChannel],
    measurements: list[models.Measurement],
) -> dict[str, float]:
    coverages: dict[str, float] = {}
    for element in _critical_elements(elements):
        element_defects = [item for item in defects if item.element_id == element.id]
        element_channels = [item for item in channels if item.element_id == element.id]
        element_measurements = [item for item in measurements if item.element_id == element.id]
        coverages[element.id] = _avg(
            [
                _element_geometry_score(element),
                _element_material_score(element),
                _element_boundary_score(element),
                _defect_registry_score([element], element_defects),
                _measurement_score([element], element_channels, element_measurements),
            ]
        )
    return coverages


def _parameter_group_coverage(score_map: dict[str, float]) -> dict[str, float]:
    return {
        "geometry_and_scheme": _clamp(_avg([score_map.get("element.tree", 0.0), score_map.get("element.geometry", 0.0)])),
        "materials": _clamp(score_map.get("element.material", 0.0)),
        "damage_state": _clamp(score_map.get("defect.registry", 0.0)),
        "boundary_conditions": _clamp(score_map.get("element.boundary_conditions", 0.0)),
        "dynamic_response": _clamp(
            _avg([score_map.get("observation.measurements", 0.0), score_map.get("measurement.channel_metadata", 0.0)])
        ),
        "prognosis_preconditions": _clamp(
            _avg(
                [
                    score_map.get("environment.effects", 0.0),
                    score_map.get("intervention.history", 0.0),
                    score_map.get("tests.ndt", 0.0),
                    score_map.get("quality.traceability", 0.0),
                ]
            )
        ),
    }


OBJECT_REQUIREMENTS: tuple[Requirement, ...] = (
    Requirement("object.identity", "P0", "Паспорт объекта должен содержать код, наименование и базовую привязку.", 0.95, 0.75, lambda scores: scores["object.identity"]),
    Requirement("object.function_type", "P0", "Нужно назначение объекта.", 0.85, 0.95, lambda scores: scores["object.function_type"]),
    Requirement("element.tree", "P0", "Нужна иерархия несущих систем и элементов.", 0.95, 0.70, lambda scores: scores["element.tree"]),
    Requirement("element.geometry", "P0", "Нужны тип элемента, геометрия и координаты.", 0.98, 0.65, lambda scores: scores["element.geometry"]),
    Requirement("element.material", "P0", "Нужны проектные и фактические материальные характеристики.", 0.92, 0.60, lambda scores: scores["element.material"]),
    Requirement("defect.registry", "P0", "Нужен реестр дефектов с локализацией и параметризацией.", 0.90, 0.45, lambda scores: scores["defect.registry"]),
    Requirement("observation.measurements", "P0", "Нужны инструментальные наблюдения с временной привязкой и приемлемым качеством.", 1.0, 0.55, lambda scores: scores["observation.measurements"]),
    Requirement("quality.traceability", "P0", "Нужны метаданные качества и трассируемости.", 0.90, 0.55, lambda scores: scores["quality.traceability"]),
    Requirement("element.boundary_conditions", "P1", "Желательны сведения о закреплениях и связях.", 0.72, 0.45, lambda scores: scores["element.boundary_conditions"]),
    Requirement("environment.effects", "P1", "Желательны параметры среды и эксплуатационных воздействий.", 0.66, 0.40, lambda scores: scores["environment.effects"]),
    Requirement("intervention.history", "P1", "Желательна история ремонтов и усилений.", 0.70, 0.35, lambda scores: scores["intervention.history"]),
    Requirement("tests.ndt", "P1", "Желательны результаты испытаний и НК.", 0.67, 0.35, lambda scores: scores["tests.ndt"]),
    Requirement("measurement.channel_metadata", "P1", "Желательны параметры каналов наблюдения.", 0.74, 0.55, lambda scores: scores["measurement.channel_metadata"]),
)


def _build_missing_items(requirements: tuple[Requirement, ...], score_map: dict[str, float]) -> list[schemas.MissingDataItem]:
    items: list[schemas.MissingDataItem] = []
    for requirement in requirements:
        coverage = _clamp(requirement.extractor(score_map))
        if coverage < requirement.threshold:
            items.append(
                schemas.MissingDataItem(
                    code=requirement.code,
                    priority=requirement.priority,
                    description=requirement.description,
                    rank_score=requirement.rank_score,
                    present=False,
                    coverage=coverage,
                    scope="object",
                )
            )
    return sorted(items, key=lambda item: (item.priority, -item.rank_score, item.code))


def information_sufficiency_index(asset_object: models.AssetObject, elements: list[models.StructuralElement], defects: list[models.Defect], channels: list[models.ObservationChannel], measurements: list[models.Measurement], environment_records: list[models.EnvironmentRecord], interventions: list[models.Intervention], tests: list[models.TestRecord], quality_records: list[models.DataQualityRecord]) -> schemas.InformationSufficiencyIndex:
    score_map = _score_map(asset_object, elements, defects, channels, measurements, environment_records, interventions, tests, quality_records)
    p0_keys = {"object.identity", "object.function_type", "element.tree", "element.geometry", "element.material", "defect.registry", "observation.measurements", "quality.traceability"}
    p1_keys = {"element.boundary_conditions", "environment.effects", "intervention.history", "tests.ndt", "measurement.channel_metadata"}
    p0_score = _avg(score_map[key] for key in p0_keys)
    p1_score = _avg(score_map[key] for key in p1_keys)
    object_passport_score = _avg([score_map["object.identity"], score_map["object.function_type"], 1.0 if _present(asset_object.responsibility_class) else 0.0, 1.0 if _one_of_present(asset_object.year_built, asset_object.year_commissioned) else 0.0, 1.0 if _present(asset_object.design_service_life) else 0.0, 1.0 if _present(asset_object.current_operational_mode) else 0.0])
    structural_model_score = _clamp((0.25 * score_map["element.tree"]) + (0.45 * score_map["element.geometry"]) + (0.30 * score_map["element.material"]))
    domain_scores = schemas.SufficiencyDomainScores(object_passport_score=object_passport_score, structural_model_score=structural_model_score, defect_registry_score=score_map["defect.registry"], measurement_score=score_map["observation.measurements"], boundary_conditions_score=score_map["element.boundary_conditions"], environment_score=score_map["environment.effects"], intervention_history_score=score_map["intervention.history"], testing_score=score_map["tests.ndt"], quality_traceability_score=score_map["quality.traceability"])
    descriptive_raw = _clamp((0.30 * domain_scores.object_passport_score) + (0.25 * domain_scores.structural_model_score) + (0.15 * domain_scores.defect_registry_score) + (0.15 * domain_scores.environment_score) + (0.15 * domain_scores.intervention_history_score))
    identification_raw = _clamp((0.22 * domain_scores.structural_model_score) + (0.22 * domain_scores.measurement_score) + (0.14 * domain_scores.boundary_conditions_score) + (0.12 * domain_scores.defect_registry_score) + (0.12 * domain_scores.testing_score) + (0.18 * domain_scores.quality_traceability_score))
    predictive_raw = _clamp((0.40 * identification_raw) + (0.20 * domain_scores.environment_score) + (0.15 * domain_scores.intervention_history_score) + (0.15 * domain_scores.testing_score) + (0.10 * domain_scores.quality_traceability_score))
    responsibility_factor = _responsibility_factor(asset_object)
    descriptive_score = _clamp(descriptive_raw * responsibility_factor)
    identification_score = _clamp(identification_raw * responsibility_factor)
    predictive_score = _clamp(predictive_raw * responsibility_factor)
    level_scores = schemas.SufficiencyLevelScores(
        descriptive_readiness_score=descriptive_score,
        identification_readiness_score=identification_score,
        predictive_readiness_score=predictive_score,
        descriptive_only=descriptive_score,
        identification_ready=identification_score,
        prediction_ready=predictive_score,
    )
    total_score = _clamp(_clamp((0.50 * identification_raw) + (0.30 * descriptive_raw) + (0.20 * predictive_raw)) * responsibility_factor)
    coverage_by_critical_elements = _critical_element_coverages(elements, defects, channels, measurements)
    coverage_by_parameter_group = _parameter_group_coverage(score_map)
    quality_weighted_measurement_coverage = _clamp(_avg([score_map["observation.measurements"], score_map["quality.traceability"]]))
    return schemas.InformationSufficiencyIndex(
        object_id=asset_object.id,
        total_score=total_score,
        p0_score=p0_score,
        p1_score=p1_score,
        missing_items=_build_missing_items(OBJECT_REQUIREMENTS, score_map),
        counts={"elements": len(elements), "critical_elements": len(_critical_elements(elements)), "defects": len(defects), "channels": len(channels), "measurements": len(measurements), "environment_records": len(environment_records), "interventions": len(interventions), "tests": len(tests), "quality_records": len(quality_records)},
        domain_scores=domain_scores,
        level_scores=level_scores,
        responsibility_factor=responsibility_factor,
        requirement_scores={key: _clamp(value) for key, value in score_map.items()},
        coverage_by_critical_elements=coverage_by_critical_elements,
        coverage_by_parameter_group=coverage_by_parameter_group,
        quality_weighted_measurement_coverage=quality_weighted_measurement_coverage,
    )


def _readiness_label(score: float) -> str:
    if score >= 0.75:
        return "identifiable"
    if score >= 0.45:
        return "qualitative_only"
    return "not_ready"


def _material_families(elements: list[models.StructuralElement]) -> set[str]:
    families: set[str] = set()
    for element in elements:
        material = _text(element.material_type)
        if material in STEEL_MATERIALS:
            families.add("steel")
        if material in CONCRETE_MATERIALS:
            families.add("concrete")
    return families


def identification_readiness(index: schemas.InformationSufficiencyIndex, elements: list[models.StructuralElement] | None = None, measurements: list[models.Measurement] | None = None, defects: list[models.Defect] | None = None, tests: list[models.TestRecord] | None = None) -> schemas.IdentificationReadinessReport:
    elements = elements or []
    measurements = measurements or []
    defects = defects or []
    tests = tests or []
    requirement_scores = index.requirement_scores
    task_scores = {
        "geometry_ready": _clamp(_avg([requirement_scores.get("element.tree", 0.0), requirement_scores.get("element.geometry", 0.0)])),
        "stiffness_ready": _clamp(_avg([requirement_scores.get("element.geometry", 0.0), requirement_scores.get("observation.measurements", 0.0), requirement_scores.get("element.boundary_conditions", 0.0)])),
        "damage_ready": _clamp(_avg([requirement_scores.get("defect.registry", 0.0), 1.0 if defects else 0.0, 1.0 if tests else 0.0])),
        "material_ready": _clamp(_avg([requirement_scores.get("element.material", 0.0), index.domain_scores.testing_score])),
        "boundary_ready": _clamp(requirement_scores.get("element.boundary_conditions", 0.0)),
    }
    overall = index.level_scores.identification_readiness_score
    identifiable_count = sum(1 for value in task_scores.values() if value >= 0.75)
    qualitative_count = sum(1 for value in task_scores.values() if 0.45 <= value < 0.75)
    readiness = "ready" if overall >= 0.75 and identifiable_count >= 3 else "partial" if overall >= 0.45 or identifiable_count or qualitative_count else "not_ready"
    recommended_parameters: list[str] = []
    if task_scores["geometry_ready"] >= 0.45:
        recommended_parameters.append("геометрия и расчётная схема")
    if task_scores["stiffness_ready"] >= 0.45 and measurements:
        recommended_parameters.append("жёсткостные параметры и отклик конструкции")
    if task_scores["damage_ready"] >= 0.45 and defects:
        recommended_parameters.append("дескрипторы повреждений и деградации")
    if task_scores["material_ready"] >= 0.45 and tests:
        recommended_parameters.append("фактические механические характеристики материала")
    if task_scores["boundary_ready"] >= 0.45:
        recommended_parameters.append("параметры закреплений и узлов")
    next_measurements: list[str] = []
    if task_scores["geometry_ready"] < 0.75:
        next_measurements.append("Уточнить геометрию элементов, пролёты и пространственную привязку")
    if task_scores["stiffness_ready"] < 0.75:
        next_measurements.append("Добавить временные ряды прогибов, деформаций или перемещений")
    if task_scores["boundary_ready"] < 0.75:
        next_measurements.append("Собрать данные о закреплениях, узлах и податливости связей")
    if task_scores["material_ready"] < 0.75:
        next_measurements.append("Подтвердить фактические свойства материала испытаниями или НК")
    if task_scores["damage_ready"] < 0.75:
        next_measurements.append("Параметризовать дефекты: размеры, локализацию, развитие во времени")
    if requirement_scores.get("quality.traceability", 0.0) < 0.75:
        next_measurements.append("Добавить источник, метод, точность и traceability metadata")
    material_families = _material_families(elements)
    if "steel" in material_families:
        next_measurements.extend(["Для стальных элементов собрать толщины, потери сечения, состояние узлов и карты коррозии", "Для стальных элементов уточнить повреждения сварных и болтовых соединений"])
    if "concrete" in material_families:
        next_measurements.extend(["Для железобетона собрать раскрытие трещин, защитный слой и НК бетона", "Для железобетона уточнить состояние арматуры и признаки потери сцепления"])
    return schemas.IdentificationReadinessReport(
        object_id=index.object_id,
        readiness_level=readiness,
        total_score=overall,
        recommended_parameters=sorted(set(recommended_parameters)),
        blocked_parameters=[item.code for item in index.missing_items],
        next_measurements=list(dict.fromkeys(next_measurements)),
        geometry_ready=_readiness_label(task_scores["geometry_ready"]),
        stiffness_ready=_readiness_label(task_scores["stiffness_ready"]),
        damage_ready=_readiness_label(task_scores["damage_ready"]),
        material_ready=_readiness_label(task_scores["material_ready"]),
        boundary_ready=_readiness_label(task_scores["boundary_ready"]),
        task_scores=task_scores,
    )


def identification_readiness(index: schemas.InformationSufficiencyIndex, elements: list[models.StructuralElement] | None = None, measurements: list[models.Measurement] | None = None, defects: list[models.Defect] | None = None, tests: list[models.TestRecord] | None = None) -> schemas.IdentificationReadinessReport:
    elements = elements or []
    measurements = measurements or []
    defects = defects or []
    tests = tests or []
    requirement_scores = index.requirement_scores
    group_scores = index.coverage_by_parameter_group

    geometry_score = _clamp(group_scores.get("geometry_and_scheme", 0.0))
    materials_score = _clamp(group_scores.get("materials", 0.0))
    damage_score = _clamp(group_scores.get("damage_state", 0.0))
    boundary_score = _clamp(group_scores.get("boundary_conditions", 0.0))
    dynamic_score = _clamp(group_scores.get("dynamic_response", 0.0))
    prognosis_score = _clamp(group_scores.get("prognosis_preconditions", 0.0))
    stiffness_score = _clamp(_avg([geometry_score, dynamic_score, boundary_score]))

    task_scores = {
        "geometry_and_scheme": geometry_score,
        "materials": materials_score,
        "damage_state": damage_score,
        "boundary_conditions": boundary_score,
        "dynamic_response": dynamic_score,
        "prognosis_preconditions": prognosis_score,
        "geometry_ready": geometry_score,
        "stiffness_ready": stiffness_score,
        "damage_ready": damage_score,
        "material_ready": materials_score,
        "boundary_ready": boundary_score,
    }
    overall = index.level_scores.identification_ready
    key_scores = (
        geometry_score,
        materials_score,
        damage_score,
        boundary_score,
        dynamic_score,
        prognosis_score,
    )
    identifiable_count = sum(1 for value in key_scores if value >= 0.75)
    qualitative_count = sum(1 for value in key_scores if 0.45 <= value < 0.75)
    readiness = "ready" if overall >= 0.75 and identifiable_count >= 4 else "partial" if overall >= 0.45 or identifiable_count or qualitative_count else "not_ready"

    recommended_parameters: list[str] = []
    if geometry_score >= 0.45:
        recommended_parameters.append("Геометрия и расчетная схема")
    if materials_score >= 0.45 and (tests or elements):
        recommended_parameters.append("Фактические характеристики материала")
    if damage_score >= 0.45 and defects:
        recommended_parameters.append("Дескрипторы повреждений и деградации")
    if boundary_score >= 0.45:
        recommended_parameters.append("Параметры закреплений и узлов")
    if dynamic_score >= 0.45 and measurements:
        recommended_parameters.append("Динамический или деформационный отклик конструкции")
    if prognosis_score >= 0.45:
        recommended_parameters.append("Условия для прогноза и сценарного анализа")

    next_measurements: list[str] = []
    if geometry_score < 0.75:
        next_measurements.append("Уточнить геометрию, сечение, пролеты и пространственную привязку элементов")
    if dynamic_score < 0.75:
        next_measurements.append("Добавить временные ряды прогибов, деформаций, перемещений или ускорений")
    if boundary_score < 0.75:
        next_measurements.append("Собрать данные о закреплениях, узлах и податливости связей")
    if materials_score < 0.75:
        next_measurements.append("Подтвердить фактические свойства материала испытаниями или НК")
    if damage_score < 0.75:
        next_measurements.append("Параметризовать дефекты: размеры, зона, тяжесть и развитие во времени")
    if prognosis_score < 0.75:
        next_measurements.append("Добавить среду, историю вмешательств, испытания и метрики качества данных")
    if requirement_scores.get("quality.traceability", 0.0) < 0.75:
        next_measurements.append("Добавить источник, метод, точность и traceability metadata")

    material_families = _material_families(elements)
    if "steel" in material_families:
        next_measurements.extend(
            [
                "Для стальных элементов собрать толщины, потери сечения, состояние узлов и карты коррозии",
                "Для стальных элементов уточнить повреждения сварных и болтовых соединений",
            ]
        )
    if "concrete" in material_families:
        next_measurements.extend(
            [
                "Для железобетона собрать раскрытие трещин, защитный слой и НК бетона",
                "Для железобетона уточнить состояние арматуры и признаки потери сцепления",
            ]
        )

    return schemas.IdentificationReadinessReport(
        object_id=index.object_id,
        readiness_level=readiness,
        total_score=overall,
        recommended_parameters=sorted(set(recommended_parameters)),
        blocked_parameters=[item.code for item in index.missing_items],
        next_measurements=list(dict.fromkeys(next_measurements)),
        geometry_ready=_readiness_label(geometry_score),
        stiffness_ready=_readiness_label(stiffness_score),
        damage_ready=_readiness_label(damage_score),
        material_ready=_readiness_label(materials_score),
        boundary_ready=_readiness_label(boundary_score),
        geometry_and_scheme_ready=_readiness_label(geometry_score),
        materials_ready=_readiness_label(materials_score),
        damage_state_ready=_readiness_label(damage_score),
        boundary_conditions_ready=_readiness_label(boundary_score),
        dynamic_response_ready=_readiness_label(dynamic_score),
        prognosis_preconditions_ready=_readiness_label(prognosis_score),
        task_scores=task_scores,
    )

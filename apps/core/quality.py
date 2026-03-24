from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Callable

from apps.core import schemas
from apps.db import models


@dataclass(frozen=True)
class Requirement:
    code: str
    priority: str
    description: str
    rank_score: float
    predicate: Callable[[dict[str, Any]], bool]


def _present(value: Any) -> bool:
    return value not in (None, "", [], {}, ())


P0_REQUIREMENTS: tuple[Requirement, ...] = (
    Requirement(
        code="object.identity",
        priority="P0",
        description="Паспорт объекта должен содержать код и наименование.",
        rank_score=0.95,
        predicate=lambda ctx: _present(ctx["object"].object_code) and _present(ctx["object"].object_name),
    ),
    Requirement(
        code="object.function_type",
        priority="P0",
        description="Нужно назначение объекта.",
        rank_score=0.85,
        predicate=lambda ctx: _present(ctx["object"].function_type),
    ),
    Requirement(
        code="element.tree",
        priority="P0",
        description="Нужна иерархия несущих систем и элементов.",
        rank_score=0.95,
        predicate=lambda ctx: bool(ctx["elements"]),
    ),
    Requirement(
        code="element.geometry",
        priority="P0",
        description="Нужны тип элемента, геометрия и координаты.",
        rank_score=0.98,
        predicate=lambda ctx: any(
            _present(element.element_type)
            and (_present(element.length) or _present(element.span) or _present(element.height))
            and _present(element.coordinates_global)
            for element in ctx["elements"]
        ),
    ),
    Requirement(
        code="element.material",
        priority="P0",
        description="Нужны материал и проектные характеристики.",
        rank_score=0.92,
        predicate=lambda ctx: any(
            _present(element.material_type) and _present(element.material_grade_design)
            for element in ctx["elements"]
        ),
    ),
    Requirement(
        code="defect.registry",
        priority="P0",
        description="Нужен реестр дефектов с локализацией и датой.",
        rank_score=0.9,
        predicate=lambda ctx: any(
            _present(defect.defect_type)
            and _present(defect.location_on_element)
            and _present(defect.detection_date)
            for defect in ctx["defects"]
        ),
    ),
    Requirement(
        code="observation.measurements",
        priority="P0",
        description="Нужны базовые инструментальные наблюдения с временной привязкой.",
        rank_score=1.0,
        predicate=lambda ctx: any(
            _present(measurement.timestamp) and _present(measurement.value) and _present(measurement.unit)
            for measurement in ctx["measurements"]
        ),
    ),
    Requirement(
        code="quality.traceability",
        priority="P0",
        description="Нужны метаданные качества и трассируемости.",
        rank_score=0.9,
        predicate=lambda ctx: any(
            _present(quality.source_type) and _present(quality.traceability_score)
            for quality in ctx["quality_records"]
        ),
    ),
)

P1_REQUIREMENTS: tuple[Requirement, ...] = (
    Requirement(
        code="element.boundary_conditions",
        priority="P1",
        description="Желательны сведения о закреплениях и связях.",
        rank_score=0.72,
        predicate=lambda ctx: any(
            _present(element.support_type) or _present(element.joint_type) for element in ctx["elements"]
        ),
    ),
    Requirement(
        code="environment.effects",
        priority="P1",
        description="Желательны параметры среды и эксплуатационных воздействий.",
        rank_score=0.66,
        predicate=lambda ctx: bool(ctx["environment_records"]),
    ),
    Requirement(
        code="intervention.history",
        priority="P1",
        description="Желательна история ремонтов и усилений.",
        rank_score=0.7,
        predicate=lambda ctx: bool(ctx["interventions"]),
    ),
    Requirement(
        code="tests.ndt",
        priority="P1",
        description="Желательны результаты испытаний и НК.",
        rank_score=0.67,
        predicate=lambda ctx: bool(ctx["tests"]),
    ),
    Requirement(
        code="measurement.channel_metadata",
        priority="P1",
        description="Желательны параметры каналов наблюдения.",
        rank_score=0.74,
        predicate=lambda ctx: any(
            _present(channel.sensor_type)
            and _present(channel.measured_quantity)
            and _present(channel.spatial_location)
            for channel in ctx["channels"]
        ),
    ),
)


def build_context(
    asset_object: models.AssetObject,
    elements: list[models.StructuralElement],
    defects: list[models.Defect],
    channels: list[models.ObservationChannel],
    measurements: list[models.Measurement],
    environment_records: list[models.EnvironmentRecord],
    interventions: list[models.Intervention],
    tests: list[models.TestRecord],
    quality_records: list[models.DataQualityRecord],
) -> dict[str, Any]:
    return {
        "object": asset_object,
        "elements": elements,
        "defects": defects,
        "channels": channels,
        "measurements": measurements,
        "environment_records": environment_records,
        "interventions": interventions,
        "tests": tests,
        "quality_records": quality_records,
    }


def evaluate_requirements(
    requirements: tuple[Requirement, ...],
    ctx: dict[str, Any],
) -> tuple[float, list[schemas.MissingDataItem]]:
    total = len(requirements) or 1
    satisfied = 0
    items: list[schemas.MissingDataItem] = []

    for requirement in requirements:
        present = requirement.predicate(ctx)
        if present:
            satisfied += 1
        items.append(
            schemas.MissingDataItem(
                code=requirement.code,
                priority=requirement.priority,
                description=requirement.description,
                rank_score=requirement.rank_score,
                present=present,
            )
        )

    return round(satisfied / total, 4), items


def information_sufficiency_index(
    asset_object: models.AssetObject,
    elements: list[models.StructuralElement],
    defects: list[models.Defect],
    channels: list[models.ObservationChannel],
    measurements: list[models.Measurement],
    environment_records: list[models.EnvironmentRecord],
    interventions: list[models.Intervention],
    tests: list[models.TestRecord],
    quality_records: list[models.DataQualityRecord],
) -> schemas.InformationSufficiencyIndex:
    ctx = build_context(
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
    p0_score, p0_items = evaluate_requirements(P0_REQUIREMENTS, ctx)
    p1_score, p1_items = evaluate_requirements(P1_REQUIREMENTS, ctx)
    total_score = round((0.7 * p0_score) + (0.3 * p1_score), 4)
    missing_items = sorted(
        [item for item in [*p0_items, *p1_items] if not item.present],
        key=lambda item: (item.priority, -item.rank_score),
    )
    return schemas.InformationSufficiencyIndex(
        object_id=asset_object.id,
        total_score=total_score,
        p0_score=p0_score,
        p1_score=p1_score,
        missing_items=missing_items,
        counts={
            "elements": len(elements),
            "defects": len(defects),
            "channels": len(channels),
            "measurements": len(measurements),
            "environment_records": len(environment_records),
            "interventions": len(interventions),
            "tests": len(tests),
            "quality_records": len(quality_records),
        },
    )


def identification_readiness(
    index: schemas.InformationSufficiencyIndex,
    measurements: list[models.Measurement],
    defects: list[models.Defect],
    tests: list[models.TestRecord],
) -> schemas.IdentificationReadinessReport:
    if index.total_score >= 0.85:
        readiness = "ready"
    elif index.total_score >= 0.6:
        readiness = "partial"
    else:
        readiness = "not_ready"

    recommended_parameters: list[str] = []
    if measurements:
        recommended_parameters.extend(["stiffness-forming parameters", "deformation response"])
    if defects:
        recommended_parameters.append("damage evolution descriptors")
    if tests:
        recommended_parameters.append("material actual properties")

    next_measurements: list[str] = []
    blocked = [item.code for item in index.missing_items]
    if "element.geometry" in blocked:
        next_measurements.append("Уточнить геометрию и координаты элементов")
    if "observation.measurements" in blocked:
        next_measurements.append("Добавить временные ряды прогибов/деформаций/перемещений")
    if "quality.traceability" in blocked:
        next_measurements.append("Добавить источник, метод и traceability metadata")
    if "environment.effects" in blocked:
        next_measurements.append("Собрать температуру, влажность и режимы эксплуатации")

    return schemas.IdentificationReadinessReport(
        object_id=index.object_id,
        readiness_level=readiness,
        total_score=index.total_score,
        recommended_parameters=sorted(set(recommended_parameters)),
        blocked_parameters=blocked,
        next_measurements=next_measurements,
    )


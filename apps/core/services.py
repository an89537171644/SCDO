from __future__ import annotations

from datetime import timezone
from typing import Any
from typing import Generic
from typing import TypeVar

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.core import exporters
from apps.core import quality
from apps.db import models


ModelT = TypeVar("ModelT", bound=models.Base)
CreateSchemaT = TypeVar("CreateSchemaT", bound=BaseModel)
UpdateSchemaT = TypeVar("UpdateSchemaT", bound=BaseModel)


def ensure_utc(value: Any) -> Any:
    if hasattr(value, "tzinfo") and value.tzinfo is not None:
        return value.astimezone(timezone.utc)
    return value


def normalize_payload(data: dict[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, str) and value == "":
            normalized[key] = None
        else:
            normalized[key] = ensure_utc(value)
    return normalized


def write_audit_log(
    session: Session,
    *,
    entity_type: str,
    entity_id: str,
    action: str,
    payload: dict[str, Any] | None = None,
    actor: str | None = "system",
) -> None:
    session.add(
        models.AuditLog(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor=actor,
            payload=payload,
        )
    )


class CRUDService(Generic[ModelT, CreateSchemaT, UpdateSchemaT]):
    def __init__(self, model: type[ModelT], entity_type: str) -> None:
        self.model = model
        self.entity_type = entity_type

    def list(self, session: Session, **filters: Any) -> list[ModelT]:
        stmt = select(self.model)
        object_id = filters.get("object_id")
        element_id = filters.get("element_id")
        channel_id = filters.get("channel_id")
        defect_type = filters.get("defect_type")
        date_from = filters.get("date_from")
        date_to = filters.get("date_to")

        if object_id and hasattr(self.model, "object_id"):
            stmt = stmt.where(getattr(self.model, "object_id") == object_id)
        if object_id and self.model is models.AssetObject:
            stmt = stmt.where(models.AssetObject.id == object_id)
        if element_id and hasattr(self.model, "element_id"):
            stmt = stmt.where(getattr(self.model, "element_id") == element_id)
        if channel_id and hasattr(self.model, "channel_id"):
            stmt = stmt.where(getattr(self.model, "channel_id") == channel_id)
        if defect_type and hasattr(self.model, "defect_type"):
            stmt = stmt.where(getattr(self.model, "defect_type") == defect_type)
        if date_from:
            for field_name in ("timestamp", "date", "detection_date"):
                if hasattr(self.model, field_name):
                    stmt = stmt.where(getattr(self.model, field_name) >= date_from)
                    break
        if date_to:
            for field_name in ("timestamp", "date", "detection_date"):
                if hasattr(self.model, field_name):
                    stmt = stmt.where(getattr(self.model, field_name) <= date_to)
                    break

        stmt = stmt.order_by(getattr(self.model, "created_at").desc())
        return list(session.scalars(stmt).all())

    def get(self, session: Session, entity_id: str) -> ModelT:
        instance = session.get(self.model, entity_id)
        if not instance:
            raise HTTPException(status_code=404, detail=f"{self.entity_type} {entity_id} not found")
        return instance

    def create(self, session: Session, payload: CreateSchemaT) -> ModelT:
        instance = self.model(**normalize_payload(payload.model_dump(exclude_none=True)))
        session.add(instance)
        session.flush()
        write_audit_log(
            session,
            entity_type=self.entity_type,
            entity_id=instance.id,
            action="create",
            payload=payload.model_dump(mode="json"),
        )
        session.commit()
        session.refresh(instance)
        return instance

    def bulk_create(self, session: Session, payloads: list[CreateSchemaT]) -> list[ModelT]:
        instances = [self.model(**normalize_payload(payload.model_dump(exclude_none=True))) for payload in payloads]
        session.add_all(instances)
        session.flush()
        for instance, payload in zip(instances, payloads):
            write_audit_log(
                session,
                entity_type=self.entity_type,
                entity_id=instance.id,
                action="import",
                payload=payload.model_dump(mode="json"),
            )
        session.commit()
        for instance in instances:
            session.refresh(instance)
        return instances

    def update(self, session: Session, entity_id: str, payload: UpdateSchemaT) -> ModelT:
        instance = self.get(session, entity_id)
        for key, value in normalize_payload(payload.model_dump(exclude_unset=True, exclude_none=True)).items():
            setattr(instance, key, value)
        session.add(instance)
        write_audit_log(
            session,
            entity_type=self.entity_type,
            entity_id=instance.id,
            action="update",
            payload=payload.model_dump(mode="json", exclude_none=True),
        )
        session.commit()
        session.refresh(instance)
        return instance

    def delete(self, session: Session, entity_id: str) -> None:
        instance = self.get(session, entity_id)
        write_audit_log(
            session,
            entity_type=self.entity_type,
            entity_id=instance.id,
            action="delete",
        )
        session.delete(instance)
        session.commit()


asset_object_service = CRUDService(models.AssetObject, "asset_object")
element_service = CRUDService(models.StructuralElement, "structural_element")
defect_service = CRUDService(models.Defect, "defect")
channel_service = CRUDService(models.ObservationChannel, "observation_channel")
measurement_service = CRUDService(models.Measurement, "measurement")
environment_service = CRUDService(models.EnvironmentRecord, "environment_record")
intervention_service = CRUDService(models.Intervention, "intervention")
test_service = CRUDService(models.TestRecord, "test_record")
media_service = CRUDService(models.MediaAsset, "media_asset")
quality_service = CRUDService(models.DataQualityRecord, "data_quality_record")


def get_object_bundle(session: Session, object_id: str) -> dict[str, Any]:
    asset_object = asset_object_service.get(session, object_id)
    return {
        "asset_object": asset_object,
        "elements": list(
            session.scalars(
                select(models.StructuralElement).where(models.StructuralElement.object_id == object_id)
            ).all()
        ),
        "defects": list(
            session.scalars(select(models.Defect).where(models.Defect.object_id == object_id)).all()
        ),
        "channels": list(
            session.scalars(
                select(models.ObservationChannel).where(models.ObservationChannel.object_id == object_id)
            ).all()
        ),
        "measurements": list(
            session.scalars(select(models.Measurement).where(models.Measurement.object_id == object_id)).all()
        ),
        "environment_records": list(
            session.scalars(
                select(models.EnvironmentRecord).where(models.EnvironmentRecord.object_id == object_id)
            ).all()
        ),
        "interventions": list(
            session.scalars(select(models.Intervention).where(models.Intervention.object_id == object_id)).all()
        ),
        "tests": list(
            session.scalars(select(models.TestRecord).where(models.TestRecord.object_id == object_id)).all()
        ),
        "media_assets": list(
            session.scalars(select(models.MediaAsset).where(models.MediaAsset.object_id == object_id)).all()
        ),
        "quality_records": list(
            session.scalars(
                select(models.DataQualityRecord).where(models.DataQualityRecord.object_id == object_id)
            ).all()
        ),
    }


def calculate_information_sufficiency(
    session: Session, object_id: str
) -> quality.schemas.InformationSufficiencyIndex:
    bundle = get_object_bundle(session, object_id)
    return quality.information_sufficiency_index(
        asset_object=bundle["asset_object"],
        elements=bundle["elements"],
        defects=bundle["defects"],
        channels=bundle["channels"],
        measurements=bundle["measurements"],
        environment_records=bundle["environment_records"],
        interventions=bundle["interventions"],
        tests=bundle["tests"],
        quality_records=bundle["quality_records"],
    )


def calculate_identification_readiness(
    session: Session, object_id: str
) -> quality.schemas.IdentificationReadinessReport:
    bundle = get_object_bundle(session, object_id)
    index = calculate_information_sufficiency(session, object_id)
    return quality.identification_readiness(
        index=index,
        measurements=bundle["measurements"],
        defects=bundle["defects"],
        tests=bundle["tests"],
    )


def build_observation_package(session: Session, object_id: str) -> quality.schemas.ObservationPackage:
    bundle = get_object_bundle(session, object_id)
    return exporters.build_observation_package(**bundle)


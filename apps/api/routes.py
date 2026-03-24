from datetime import datetime
from typing import Any
from typing import NamedTuple
from typing import Optional

from fastapi import APIRouter
from fastapi import Body
from fastapi import Depends
from fastapi import File
from fastapi import HTTPException
from fastapi import Query
from fastapi import UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.core import importers
from apps.core import measurement_profiles
from apps.core import schemas
from apps.core import services
from apps.core.storage import MediaStorage
from apps.db import models
from apps.db.session import get_db_session


router = APIRouter()


class EntityConfig(NamedTuple):
    service: services.CRUDService[Any, Any, Any]
    create_schema: type[Any]
    update_schema: type[Any]
    read_schema: type[Any]


ENTITY_CONFIGS: dict[str, EntityConfig] = {
    "objects": EntityConfig(
        services.asset_object_service,
        schemas.CreateAssetObject,
        schemas.UpdateAssetObject,
        schemas.AssetObjectRead,
    ),
    "elements": EntityConfig(
        services.element_service,
        schemas.CreateStructuralElement,
        schemas.UpdateStructuralElement,
        schemas.StructuralElementRead,
    ),
    "defects": EntityConfig(
        services.defect_service,
        schemas.CreateDefect,
        schemas.UpdateDefect,
        schemas.DefectRead,
    ),
    "channels": EntityConfig(
        services.channel_service,
        schemas.CreateObservationChannel,
        schemas.UpdateObservationChannel,
        schemas.ObservationChannelRead,
    ),
    "measurements": EntityConfig(
        services.measurement_service,
        schemas.CreateMeasurement,
        schemas.UpdateMeasurement,
        schemas.MeasurementRead,
    ),
    "environment-records": EntityConfig(
        services.environment_service,
        schemas.CreateEnvironmentRecord,
        schemas.UpdateEnvironmentRecord,
        schemas.EnvironmentRecordRead,
    ),
    "interventions": EntityConfig(
        services.intervention_service,
        schemas.CreateIntervention,
        schemas.UpdateIntervention,
        schemas.InterventionRead,
    ),
    "tests": EntityConfig(
        services.test_service,
        schemas.CreateTestRecord,
        schemas.UpdateTestRecord,
        schemas.TestRecordRead,
    ),
    "media-assets": EntityConfig(
        services.media_service,
        schemas.CreateMediaAsset,
        schemas.UpdateMediaAsset,
        schemas.MediaAssetRead,
    ),
    "quality-records": EntityConfig(
        services.quality_service,
        schemas.CreateDataQualityRecord,
        schemas.UpdateDataQualityRecord,
        schemas.DataQualityRecordRead,
    ),
}


def get_entity_config(entity_name: str) -> EntityConfig:
    if entity_name not in ENTITY_CONFIGS:
        raise HTTPException(status_code=404, detail=f"Unknown entity type: {entity_name}")
    return ENTITY_CONFIGS[entity_name]


def register_crud_routes(prefix: str, config: EntityConfig) -> None:
    @router.get(
        f"/{prefix}",
        response_model=list[config.read_schema],
        tags=[prefix],
        name=f"list_{prefix}",
    )
    def list_entities(
        object_id: Optional[str] = Query(default=None),
        element_id: Optional[str] = Query(default=None),
        channel_id: Optional[str] = Query(default=None),
        defect_type: Optional[str] = Query(default=None),
        date_from: Optional[datetime] = Query(default=None),
        date_to: Optional[datetime] = Query(default=None),
        session: Session = Depends(get_db_session),
    ) -> list[Any]:
        return config.service.list(
            session,
            object_id=object_id,
            element_id=element_id,
            channel_id=channel_id,
            defect_type=defect_type,
            date_from=date_from,
            date_to=date_to,
        )

    @router.post(
        f"/{prefix}",
        response_model=config.read_schema,
        status_code=201,
        tags=[prefix],
        name=f"create_{prefix}",
    )
    def create_entity(payload: config.create_schema, session: Session = Depends(get_db_session)) -> Any:
        return config.service.create(session, payload)

    @router.get(
        f"/{prefix}/{{entity_id}}",
        response_model=config.read_schema,
        tags=[prefix],
        name=f"get_{prefix}",
    )
    def get_entity(entity_id: str, session: Session = Depends(get_db_session)) -> Any:
        return config.service.get(session, entity_id)

    @router.patch(
        f"/{prefix}/{{entity_id}}",
        response_model=config.read_schema,
        tags=[prefix],
        name=f"update_{prefix}",
    )
    def update_entity(
        entity_id: str,
        payload: config.update_schema,
        session: Session = Depends(get_db_session),
    ) -> Any:
        return config.service.update(session, entity_id, payload)

    @router.delete(
        f"/{prefix}/{{entity_id}}",
        status_code=204,
        tags=[prefix],
        name=f"delete_{prefix}",
    )
    def delete_entity(entity_id: str, session: Session = Depends(get_db_session)) -> None:
        config.service.delete(session, entity_id)


for prefix, entity_config in ENTITY_CONFIGS.items():
    register_crud_routes(prefix, entity_config)


@router.get("/health", tags=["system"])
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/audit-logs", response_model=list[schemas.AuditLogRead], tags=["system"])
def list_audit_logs(
    entity_type: Optional[str] = Query(default=None),
    entity_id: Optional[str] = Query(default=None),
    session: Session = Depends(get_db_session),
) -> list[models.AuditLog]:
    stmt = select(models.AuditLog).order_by(models.AuditLog.created_at.desc())
    if entity_type:
        stmt = stmt.where(models.AuditLog.entity_type == entity_type)
    if entity_id:
        stmt = stmt.where(models.AuditLog.entity_id == entity_id)
    return list(session.scalars(stmt).all())


@router.post("/imports/{entity_name}/json", response_model=list[dict[str, Any]], tags=["imports"])
def import_json_records(
    entity_name: str,
    payload: Any = Body(...),
    session: Session = Depends(get_db_session),
) -> list[dict[str, Any]]:
    config = get_entity_config(entity_name)
    records = importers.normalize_records(payload)
    try:
        schemas_to_create = [config.create_schema.model_validate(record) for record in records]
        if entity_name == "measurements":
            measurement_profiles.validate_measurement_import(session, schemas_to_create)
    except measurement_profiles.MeasurementValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    created = config.service.bulk_create(session, schemas_to_create)
    return [config.read_schema.model_validate(item).model_dump() for item in created]


@router.post("/imports/{entity_name}/file", response_model=list[dict[str, Any]], tags=["imports"])
async def import_file_records(
    entity_name: str,
    file: UploadFile = File(...),
    session: Session = Depends(get_db_session),
) -> list[dict[str, Any]]:
    config = get_entity_config(entity_name)
    content = await file.read()
    records = importers.parse_upload(file.filename or "", content)
    try:
        schemas_to_create = [config.create_schema.model_validate(record) for record in records]
        if entity_name == "measurements":
            measurement_profiles.validate_measurement_import(session, schemas_to_create)
    except measurement_profiles.MeasurementValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    created = config.service.bulk_create(session, schemas_to_create)
    return [config.read_schema.model_validate(item).model_dump() for item in created]


@router.post("/media-assets/upload", response_model=schemas.MediaAssetRead, tags=["media-assets"])
async def upload_media_asset(
    object_id: str,
    file: UploadFile = File(...),
    element_id: Optional[str] = None,
    defect_id: Optional[str] = None,
    description: Optional[str] = None,
    source_type: Optional[str] = None,
    session: Session = Depends(get_db_session),
) -> models.MediaAsset:
    storage = MediaStorage()
    content = await file.read()
    storage_key = storage.persist_bytes(file.filename or "media.bin", content)
    payload = schemas.CreateMediaAsset(
        object_id=object_id,
        element_id=element_id,
        defect_id=defect_id,
        storage_key=storage_key,
        filename=file.filename or "media.bin",
        content_type=file.content_type,
        description=description,
        source_type=source_type,
    )
    return services.media_service.create(session, payload)


@router.get(
    "/analytics/objects/{object_id}/information-sufficiency",
    response_model=schemas.InformationSufficiencyIndex,
    tags=["analytics"],
)
def get_information_sufficiency(
    object_id: str, session: Session = Depends(get_db_session)
) -> schemas.InformationSufficiencyIndex:
    return services.calculate_information_sufficiency(session, object_id)


@router.get(
    "/analytics/objects/{object_id}/identification-readiness",
    response_model=schemas.IdentificationReadinessReport,
    tags=["analytics"],
)
def get_identification_readiness(
    object_id: str, session: Session = Depends(get_db_session)
) -> schemas.IdentificationReadinessReport:
    return services.calculate_identification_readiness(session, object_id)


@router.get(
    "/analytics/objects/{object_id}/missing-data",
    response_model=list[schemas.MissingDataItem],
    tags=["analytics"],
)
def get_missing_data(
    object_id: str, session: Session = Depends(get_db_session)
) -> list[schemas.MissingDataItem]:
    return services.calculate_information_sufficiency(session, object_id).missing_items


@router.get(
    "/exports/objects/{object_id}/observation-package",
    response_model=schemas.ObservationPackage,
    tags=["exports"],
)
def export_observation_package(
    object_id: str, session: Session = Depends(get_db_session)
) -> schemas.ObservationPackage:
    return services.build_observation_package(session, object_id)

from __future__ import annotations

from datetime import datetime
from datetime import timezone
from uuid import uuid4
from typing import Optional

from sqlalchemy import JSON
from sqlalchemy import Boolean
from sqlalchemy import DateTime
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    schema_version: Mapped[str] = mapped_column(String(16), default="v1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


class AssetObject(TimestampMixin, Base):
    __tablename__ = "asset_objects"

    object_code: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    object_name: Mapped[str] = mapped_column(String(255))
    address: Mapped[Optional[str]] = mapped_column(String(255))
    coordinates: Mapped[Optional[str]] = mapped_column(String(255))
    function_type: Mapped[Optional[str]] = mapped_column(String(128))
    responsibility_class: Mapped[Optional[str]] = mapped_column(String(64))
    year_built: Mapped[Optional[int]] = mapped_column(Integer)
    year_commissioned: Mapped[Optional[int]] = mapped_column(Integer)
    design_service_life: Mapped[Optional[int]] = mapped_column(Integer)
    current_operational_mode: Mapped[Optional[str]] = mapped_column(String(128))
    source_type: Mapped[Optional[str]] = mapped_column(String(64))

    elements: Mapped[list["StructuralElement"]] = relationship(back_populates="asset_object")
    defects: Mapped[list["Defect"]] = relationship(back_populates="asset_object")
    channels: Mapped[list["ObservationChannel"]] = relationship(back_populates="asset_object")
    measurements: Mapped[list["Measurement"]] = relationship(back_populates="asset_object")
    environment_records: Mapped[list["EnvironmentRecord"]] = relationship(
        back_populates="asset_object"
    )
    interventions: Mapped[list["Intervention"]] = relationship(back_populates="asset_object")
    tests: Mapped[list["TestRecord"]] = relationship(back_populates="asset_object")
    media_assets: Mapped[list["MediaAsset"]] = relationship(back_populates="asset_object")
    quality_records: Mapped[list["DataQualityRecord"]] = relationship(back_populates="asset_object")


class StructuralElement(TimestampMixin, Base):
    __tablename__ = "structural_elements"

    object_id: Mapped[str] = mapped_column(ForeignKey("asset_objects.id"), index=True)
    parent_id: Mapped[Optional[str]] = mapped_column(ForeignKey("structural_elements.id"), index=True)
    hierarchy_type: Mapped[str] = mapped_column(String(32), index=True)
    system_id: Mapped[Optional[str]] = mapped_column(String(64))
    subsystem_id: Mapped[Optional[str]] = mapped_column(String(64))
    element_id_code: Mapped[Optional[str]] = mapped_column(String(64))
    node_zone_id: Mapped[Optional[str]] = mapped_column(String(64))
    name: Mapped[str] = mapped_column(String(255))
    structural_role: Mapped[Optional[str]] = mapped_column(String(128))
    criticality_group: Mapped[Optional[str]] = mapped_column(String(64))
    role_criticality: Mapped[Optional[str]] = mapped_column(String(64))
    consequence_class: Mapped[Optional[str]] = mapped_column(String(64))
    identification_priority: Mapped[Optional[str]] = mapped_column(String(64))
    degradation_mechanisms: Mapped[Optional[list[str]]] = mapped_column(JSON)
    element_type: Mapped[Optional[str]] = mapped_column(String(128))
    geometry_type: Mapped[Optional[str]] = mapped_column(String(128))
    length: Mapped[Optional[float]] = mapped_column(Float)
    span: Mapped[Optional[float]] = mapped_column(Float)
    height: Mapped[Optional[float]] = mapped_column(Float)
    thickness: Mapped[Optional[float]] = mapped_column(Float)
    area: Mapped[Optional[float]] = mapped_column(Float)
    coordinates_local: Mapped[Optional[str]] = mapped_column(Text)
    coordinates_global: Mapped[Optional[str]] = mapped_column(Text)
    material_type: Mapped[Optional[str]] = mapped_column(String(128))
    material_grade_design: Mapped[Optional[str]] = mapped_column(String(128))
    material_grade_actual: Mapped[Optional[str]] = mapped_column(String(128))
    elastic_modulus_design: Mapped[Optional[float]] = mapped_column(Float)
    elastic_modulus_actual: Mapped[Optional[float]] = mapped_column(Float)
    strength_design: Mapped[Optional[float]] = mapped_column(Float)
    strength_actual: Mapped[Optional[float]] = mapped_column(Float)
    support_type: Mapped[Optional[str]] = mapped_column(String(128))
    support_stiffness: Mapped[Optional[float]] = mapped_column(Float)
    joint_type: Mapped[Optional[str]] = mapped_column(String(128))
    joint_flexibility: Mapped[Optional[float]] = mapped_column(Float)
    source_type: Mapped[Optional[str]] = mapped_column(String(64))

    asset_object: Mapped[AssetObject] = relationship(back_populates="elements")
    parent: Mapped[Optional["StructuralElement"]] = relationship(remote_side="StructuralElement.id")
    defects: Mapped[list["Defect"]] = relationship(back_populates="element")
    channels: Mapped[list["ObservationChannel"]] = relationship(back_populates="element")
    measurements: Mapped[list["Measurement"]] = relationship(back_populates="element")
    environment_records: Mapped[list["EnvironmentRecord"]] = relationship(back_populates="element")
    interventions: Mapped[list["Intervention"]] = relationship(back_populates="element")
    tests: Mapped[list["TestRecord"]] = relationship(back_populates="element")
    media_assets: Mapped[list["MediaAsset"]] = relationship(back_populates="element")
    quality_records: Mapped[list["DataQualityRecord"]] = relationship(back_populates="element")


class Defect(TimestampMixin, Base):
    __tablename__ = "defects"

    object_id: Mapped[str] = mapped_column(ForeignKey("asset_objects.id"), index=True)
    element_id: Mapped[str] = mapped_column(ForeignKey("structural_elements.id"), index=True)
    defect_type: Mapped[str] = mapped_column(String(128), index=True)
    defect_subtype: Mapped[Optional[str]] = mapped_column(String(128))
    location_on_element: Mapped[str] = mapped_column(String(255))
    detection_date: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    crack_length: Mapped[Optional[float]] = mapped_column(Float)
    crack_width: Mapped[Optional[float]] = mapped_column(Float)
    crack_orientation: Mapped[Optional[str]] = mapped_column(String(128))
    crack_density: Mapped[Optional[float]] = mapped_column(Float)
    corrosion_area: Mapped[Optional[float]] = mapped_column(Float)
    corrosion_depth_or_loss: Mapped[Optional[float]] = mapped_column(Float)
    section_loss_estimate: Mapped[Optional[float]] = mapped_column(Float)
    material_family: Mapped[Optional[str]] = mapped_column(String(64))
    element_classifier: Mapped[Optional[str]] = mapped_column(String(128))
    corrosion_depth: Mapped[Optional[float]] = mapped_column(Float)
    section_loss_percent: Mapped[Optional[float]] = mapped_column(Float)
    weld_damage_type: Mapped[Optional[str]] = mapped_column(String(128))
    bolt_condition: Mapped[Optional[str]] = mapped_column(String(128))
    local_buckling_flag: Mapped[Optional[bool]] = mapped_column(Boolean)
    fatigue_crack_length: Mapped[Optional[float]] = mapped_column(Float)
    crack_type: Mapped[Optional[str]] = mapped_column(String(128))
    cover_loss_area: Mapped[Optional[float]] = mapped_column(Float)
    rebar_corrosion_class: Mapped[Optional[str]] = mapped_column(String(128))
    carbonation_depth: Mapped[Optional[float]] = mapped_column(Float)
    bond_loss_flag: Mapped[Optional[bool]] = mapped_column(Boolean)
    confidence_localization: Mapped[Optional[float]] = mapped_column(Float)
    defect_status: Mapped[Optional[str]] = mapped_column(String(64))
    source_type: Mapped[Optional[str]] = mapped_column(String(64))
    source_document: Mapped[Optional[str]] = mapped_column(String(255))

    asset_object: Mapped[AssetObject] = relationship(back_populates="defects")
    element: Mapped[StructuralElement] = relationship(back_populates="defects")


class ObservationChannel(TimestampMixin, Base):
    __tablename__ = "observation_channels"

    object_id: Mapped[str] = mapped_column(ForeignKey("asset_objects.id"), index=True)
    element_id: Mapped[str] = mapped_column(ForeignKey("structural_elements.id"), index=True)
    channel_code: Mapped[str] = mapped_column(String(64), index=True)
    sensor_type: Mapped[Optional[str]] = mapped_column(String(128))
    measured_quantity: Mapped[str] = mapped_column(String(128))
    unit: Mapped[str] = mapped_column(String(64))
    measurement_class: Mapped[str] = mapped_column(String(32), default="raw")
    spatial_location: Mapped[Optional[str]] = mapped_column(String(255))
    sampling_frequency: Mapped[Optional[float]] = mapped_column(Float)
    source_type: Mapped[Optional[str]] = mapped_column(String(64))

    asset_object: Mapped[AssetObject] = relationship(back_populates="channels")
    element: Mapped[StructuralElement] = relationship(back_populates="channels")
    measurements: Mapped[list["Measurement"]] = relationship(back_populates="channel")


class Measurement(TimestampMixin, Base):
    __tablename__ = "measurements"

    object_id: Mapped[str] = mapped_column(ForeignKey("asset_objects.id"), index=True)
    element_id: Mapped[str] = mapped_column(ForeignKey("structural_elements.id"), index=True)
    channel_id: Mapped[str] = mapped_column(ForeignKey("observation_channels.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(64))
    quality_flag: Mapped[Optional[str]] = mapped_column(String(64))
    source_type: Mapped[Optional[str]] = mapped_column(String(64))
    method_reference: Mapped[Optional[str]] = mapped_column(String(255))
    accuracy: Mapped[Optional[float]] = mapped_column(Float)
    spatial_location: Mapped[Optional[str]] = mapped_column(String(255))

    asset_object: Mapped[AssetObject] = relationship(back_populates="measurements")
    element: Mapped[StructuralElement] = relationship(back_populates="measurements")
    channel: Mapped[ObservationChannel] = relationship(back_populates="measurements")


class EnvironmentRecord(TimestampMixin, Base):
    __tablename__ = "environment_records"

    object_id: Mapped[str] = mapped_column(ForeignKey("asset_objects.id"), index=True)
    element_id: Mapped[Optional[str]] = mapped_column(ForeignKey("structural_elements.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    temperature: Mapped[Optional[float]] = mapped_column(Float)
    humidity: Mapped[Optional[float]] = mapped_column(Float)
    corrosion_aggressiveness: Mapped[Optional[str]] = mapped_column(String(128))
    cyclicity: Mapped[Optional[str]] = mapped_column(String(128))
    seasonality: Mapped[Optional[str]] = mapped_column(String(128))
    load_summary: Mapped[Optional[str]] = mapped_column(Text)
    operation_mode: Mapped[Optional[str]] = mapped_column(String(128))
    source_type: Mapped[Optional[str]] = mapped_column(String(64))

    asset_object: Mapped[AssetObject] = relationship(back_populates="environment_records")
    element: Mapped[Optional[StructuralElement]] = relationship(back_populates="environment_records")


class Intervention(TimestampMixin, Base):
    __tablename__ = "interventions"

    object_id: Mapped[str] = mapped_column(ForeignKey("asset_objects.id"), index=True)
    element_id: Mapped[str] = mapped_column(ForeignKey("structural_elements.id"), index=True)
    intervention_type: Mapped[str] = mapped_column(String(128))
    description: Mapped[Optional[str]] = mapped_column(Text)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    expected_effect_on_degradation_rate: Mapped[Optional[str]] = mapped_column(String(255))
    as_built_documents: Mapped[Optional[str]] = mapped_column(String(255))
    quality_of_execution: Mapped[Optional[str]] = mapped_column(String(128))
    source_type: Mapped[Optional[str]] = mapped_column(String(64))

    asset_object: Mapped[AssetObject] = relationship(back_populates="interventions")
    element: Mapped[StructuralElement] = relationship(back_populates="interventions")


class TestRecord(TimestampMixin, Base):
    __tablename__ = "test_records"

    object_id: Mapped[str] = mapped_column(ForeignKey("asset_objects.id"), index=True)
    element_id: Mapped[str] = mapped_column(ForeignKey("structural_elements.id"), index=True)
    test_type: Mapped[str] = mapped_column(String(128))
    measured_property: Mapped[str] = mapped_column(String(128))
    test_value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(64))
    method: Mapped[Optional[str]] = mapped_column(String(255))
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    sampled_location: Mapped[Optional[str]] = mapped_column(String(255))
    confidence_interval: Mapped[Optional[str]] = mapped_column(String(128))
    source_type: Mapped[Optional[str]] = mapped_column(String(64))

    asset_object: Mapped[AssetObject] = relationship(back_populates="tests")
    element: Mapped[StructuralElement] = relationship(back_populates="tests")


class MediaAsset(TimestampMixin, Base):
    __tablename__ = "media_assets"

    object_id: Mapped[str] = mapped_column(ForeignKey("asset_objects.id"), index=True)
    element_id: Mapped[Optional[str]] = mapped_column(ForeignKey("structural_elements.id"), index=True)
    defect_id: Mapped[Optional[str]] = mapped_column(ForeignKey("defects.id"), index=True)
    storage_key: Mapped[str] = mapped_column(String(255))
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[Optional[str]] = mapped_column(String(128))
    description: Mapped[Optional[str]] = mapped_column(Text)
    captured_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    source_type: Mapped[Optional[str]] = mapped_column(String(64))

    asset_object: Mapped[AssetObject] = relationship(back_populates="media_assets")
    element: Mapped[Optional[StructuralElement]] = relationship(back_populates="media_assets")


class DataQualityRecord(TimestampMixin, Base):
    __tablename__ = "data_quality_records"

    object_id: Mapped[str] = mapped_column(ForeignKey("asset_objects.id"), index=True)
    element_id: Mapped[Optional[str]] = mapped_column(ForeignKey("structural_elements.id"), index=True)
    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    source_type: Mapped[str] = mapped_column(String(64))
    source_document: Mapped[Optional[str]] = mapped_column(String(255))
    author: Mapped[Optional[str]] = mapped_column(String(255))
    method_reference: Mapped[Optional[str]] = mapped_column(String(255))
    accuracy: Mapped[Optional[float]] = mapped_column(Float)
    completeness_score: Mapped[Optional[float]] = mapped_column(Float)
    repeatability_score: Mapped[Optional[float]] = mapped_column(Float)
    traceability_score: Mapped[Optional[float]] = mapped_column(Float)
    identification_suitability_score: Mapped[Optional[float]] = mapped_column(Float)
    remarks: Mapped[Optional[str]] = mapped_column(Text)

    asset_object: Mapped[AssetObject] = relationship(back_populates="quality_records")
    element: Mapped[Optional[StructuralElement]] = relationship(back_populates="quality_records")


class AuditLog(TimestampMixin, Base):
    __tablename__ = "audit_logs"

    entity_type: Mapped[str] = mapped_column(String(64), index=True)
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    action: Mapped[str] = mapped_column(String(32))
    actor: Mapped[Optional[str]] = mapped_column(String(255))
    payload: Mapped[Optional[dict]] = mapped_column(JSON)


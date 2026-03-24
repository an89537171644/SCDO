from __future__ import annotations

from datetime import datetime
from typing import Any
from typing import Optional

from pydantic import BaseModel
from pydantic import ConfigDict


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ReadMixin(ORMModel):
    id: str
    schema_version: str
    created_at: datetime
    updated_at: datetime


class AssetObjectBase(BaseModel):
    object_code: str
    object_name: str
    address: Optional[str] = None
    coordinates: Optional[str] = None
    function_type: Optional[str] = None
    responsibility_class: Optional[str] = None
    year_built: Optional[int] = None
    year_commissioned: Optional[int] = None
    design_service_life: Optional[int] = None
    current_operational_mode: Optional[str] = None
    source_type: Optional[str] = None


class CreateAssetObject(AssetObjectBase):
    pass


class UpdateAssetObject(BaseModel):
    object_code: Optional[str] = None
    object_name: Optional[str] = None
    address: Optional[str] = None
    coordinates: Optional[str] = None
    function_type: Optional[str] = None
    responsibility_class: Optional[str] = None
    year_built: Optional[int] = None
    year_commissioned: Optional[int] = None
    design_service_life: Optional[int] = None
    current_operational_mode: Optional[str] = None
    source_type: Optional[str] = None


class AssetObjectRead(ReadMixin, AssetObjectBase):
    pass


class StructuralElementBase(BaseModel):
    object_id: str
    parent_id: Optional[str] = None
    hierarchy_type: str
    system_id: Optional[str] = None
    subsystem_id: Optional[str] = None
    element_id_code: Optional[str] = None
    node_zone_id: Optional[str] = None
    name: str
    structural_role: Optional[str] = None
    criticality_group: Optional[str] = None
    element_type: Optional[str] = None
    geometry_type: Optional[str] = None
    length: Optional[float] = None
    span: Optional[float] = None
    height: Optional[float] = None
    thickness: Optional[float] = None
    area: Optional[float] = None
    coordinates_local: Optional[str] = None
    coordinates_global: Optional[str] = None
    material_type: Optional[str] = None
    material_grade_design: Optional[str] = None
    material_grade_actual: Optional[str] = None
    elastic_modulus_design: Optional[float] = None
    elastic_modulus_actual: Optional[float] = None
    strength_design: Optional[float] = None
    strength_actual: Optional[float] = None
    support_type: Optional[str] = None
    support_stiffness: Optional[float] = None
    joint_type: Optional[str] = None
    joint_flexibility: Optional[float] = None
    source_type: Optional[str] = None


class CreateStructuralElement(StructuralElementBase):
    pass


class UpdateStructuralElement(BaseModel):
    parent_id: Optional[str] = None
    hierarchy_type: Optional[str] = None
    system_id: Optional[str] = None
    subsystem_id: Optional[str] = None
    element_id_code: Optional[str] = None
    node_zone_id: Optional[str] = None
    name: Optional[str] = None
    structural_role: Optional[str] = None
    criticality_group: Optional[str] = None
    element_type: Optional[str] = None
    geometry_type: Optional[str] = None
    length: Optional[float] = None
    span: Optional[float] = None
    height: Optional[float] = None
    thickness: Optional[float] = None
    area: Optional[float] = None
    coordinates_local: Optional[str] = None
    coordinates_global: Optional[str] = None
    material_type: Optional[str] = None
    material_grade_design: Optional[str] = None
    material_grade_actual: Optional[str] = None
    elastic_modulus_design: Optional[float] = None
    elastic_modulus_actual: Optional[float] = None
    strength_design: Optional[float] = None
    strength_actual: Optional[float] = None
    support_type: Optional[str] = None
    support_stiffness: Optional[float] = None
    joint_type: Optional[str] = None
    joint_flexibility: Optional[float] = None
    source_type: Optional[str] = None


class StructuralElementRead(ReadMixin, StructuralElementBase):
    pass


class DefectBase(BaseModel):
    object_id: str
    element_id: str
    defect_type: str
    defect_subtype: Optional[str] = None
    location_on_element: str
    detection_date: datetime
    crack_length: Optional[float] = None
    crack_width: Optional[float] = None
    crack_orientation: Optional[str] = None
    crack_density: Optional[float] = None
    corrosion_area: Optional[float] = None
    corrosion_depth_or_loss: Optional[float] = None
    section_loss_estimate: Optional[float] = None
    confidence_localization: Optional[float] = None
    defect_status: Optional[str] = None
    source_type: Optional[str] = None
    source_document: Optional[str] = None


class CreateDefect(DefectBase):
    pass


class UpdateDefect(BaseModel):
    defect_type: Optional[str] = None
    defect_subtype: Optional[str] = None
    location_on_element: Optional[str] = None
    detection_date: Optional[datetime] = None
    crack_length: Optional[float] = None
    crack_width: Optional[float] = None
    crack_orientation: Optional[str] = None
    crack_density: Optional[float] = None
    corrosion_area: Optional[float] = None
    corrosion_depth_or_loss: Optional[float] = None
    section_loss_estimate: Optional[float] = None
    confidence_localization: Optional[float] = None
    defect_status: Optional[str] = None
    source_type: Optional[str] = None
    source_document: Optional[str] = None


class DefectRead(ReadMixin, DefectBase):
    pass


class ObservationChannelBase(BaseModel):
    object_id: str
    element_id: str
    channel_code: str
    sensor_type: Optional[str] = None
    measured_quantity: str
    unit: str
    measurement_class: str = "raw"
    spatial_location: Optional[str] = None
    sampling_frequency: Optional[float] = None
    source_type: Optional[str] = None


class CreateObservationChannel(ObservationChannelBase):
    pass


class UpdateObservationChannel(BaseModel):
    channel_code: Optional[str] = None
    sensor_type: Optional[str] = None
    measured_quantity: Optional[str] = None
    unit: Optional[str] = None
    measurement_class: Optional[str] = None
    spatial_location: Optional[str] = None
    sampling_frequency: Optional[float] = None
    source_type: Optional[str] = None


class ObservationChannelRead(ReadMixin, ObservationChannelBase):
    pass


class MeasurementBase(BaseModel):
    object_id: str
    element_id: str
    channel_id: str
    timestamp: datetime
    value: float
    unit: str
    quality_flag: Optional[str] = None
    source_type: Optional[str] = None
    method_reference: Optional[str] = None
    accuracy: Optional[float] = None
    spatial_location: Optional[str] = None


class CreateMeasurement(MeasurementBase):
    pass


class UpdateMeasurement(BaseModel):
    timestamp: Optional[datetime] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    quality_flag: Optional[str] = None
    source_type: Optional[str] = None
    method_reference: Optional[str] = None
    accuracy: Optional[float] = None
    spatial_location: Optional[str] = None


class MeasurementRead(ReadMixin, MeasurementBase):
    pass


class EnvironmentRecordBase(BaseModel):
    object_id: str
    element_id: Optional[str] = None
    timestamp: datetime
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    corrosion_aggressiveness: Optional[str] = None
    cyclicity: Optional[str] = None
    seasonality: Optional[str] = None
    load_summary: Optional[str] = None
    operation_mode: Optional[str] = None
    source_type: Optional[str] = None


class CreateEnvironmentRecord(EnvironmentRecordBase):
    pass


class UpdateEnvironmentRecord(BaseModel):
    timestamp: Optional[datetime] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    corrosion_aggressiveness: Optional[str] = None
    cyclicity: Optional[str] = None
    seasonality: Optional[str] = None
    load_summary: Optional[str] = None
    operation_mode: Optional[str] = None
    source_type: Optional[str] = None


class EnvironmentRecordRead(ReadMixin, EnvironmentRecordBase):
    pass


class InterventionBase(BaseModel):
    object_id: str
    element_id: str
    intervention_type: str
    description: Optional[str] = None
    date: datetime
    expected_effect_on_degradation_rate: Optional[str] = None
    as_built_documents: Optional[str] = None
    quality_of_execution: Optional[str] = None
    source_type: Optional[str] = None


class CreateIntervention(InterventionBase):
    pass


class UpdateIntervention(BaseModel):
    intervention_type: Optional[str] = None
    description: Optional[str] = None
    date: Optional[datetime] = None
    expected_effect_on_degradation_rate: Optional[str] = None
    as_built_documents: Optional[str] = None
    quality_of_execution: Optional[str] = None
    source_type: Optional[str] = None


class InterventionRead(ReadMixin, InterventionBase):
    pass


class TestRecordBase(BaseModel):
    object_id: str
    element_id: str
    test_type: str
    measured_property: str
    test_value: float
    unit: str
    method: Optional[str] = None
    date: datetime
    sampled_location: Optional[str] = None
    confidence_interval: Optional[str] = None
    source_type: Optional[str] = None


class CreateTestRecord(TestRecordBase):
    pass


class UpdateTestRecord(BaseModel):
    test_type: Optional[str] = None
    measured_property: Optional[str] = None
    test_value: Optional[float] = None
    unit: Optional[str] = None
    method: Optional[str] = None
    date: Optional[datetime] = None
    sampled_location: Optional[str] = None
    confidence_interval: Optional[str] = None
    source_type: Optional[str] = None


class TestRecordRead(ReadMixin, TestRecordBase):
    pass


class MediaAssetBase(BaseModel):
    object_id: str
    element_id: Optional[str] = None
    defect_id: Optional[str] = None
    storage_key: str
    filename: str
    content_type: Optional[str] = None
    description: Optional[str] = None
    captured_at: Optional[datetime] = None
    source_type: Optional[str] = None


class CreateMediaAsset(MediaAssetBase):
    pass


class UpdateMediaAsset(BaseModel):
    storage_key: Optional[str] = None
    filename: Optional[str] = None
    content_type: Optional[str] = None
    description: Optional[str] = None
    captured_at: Optional[datetime] = None
    source_type: Optional[str] = None


class MediaAssetRead(ReadMixin, MediaAssetBase):
    pass


class DataQualityRecordBase(BaseModel):
    object_id: str
    element_id: Optional[str] = None
    entity_type: str
    entity_id: str
    source_type: str
    source_document: Optional[str] = None
    author: Optional[str] = None
    method_reference: Optional[str] = None
    accuracy: Optional[float] = None
    completeness_score: Optional[float] = None
    repeatability_score: Optional[float] = None
    traceability_score: Optional[float] = None
    identification_suitability_score: Optional[float] = None
    remarks: Optional[str] = None


class CreateDataQualityRecord(DataQualityRecordBase):
    pass


class UpdateDataQualityRecord(BaseModel):
    source_type: Optional[str] = None
    source_document: Optional[str] = None
    author: Optional[str] = None
    method_reference: Optional[str] = None
    accuracy: Optional[float] = None
    completeness_score: Optional[float] = None
    repeatability_score: Optional[float] = None
    traceability_score: Optional[float] = None
    identification_suitability_score: Optional[float] = None
    remarks: Optional[str] = None


class DataQualityRecordRead(ReadMixin, DataQualityRecordBase):
    pass


class AuditLogRead(ReadMixin, ORMModel):
    entity_type: str
    entity_id: str
    action: str
    actor: Optional[str]
    payload: Optional[dict[str, Any]]


class ImportPayload(BaseModel):
    records: list[dict[str, Any]]


class MissingDataItem(BaseModel):
    code: str
    priority: str
    description: str
    rank_score: float
    present: bool = False


class InformationSufficiencyIndex(BaseModel):
    object_id: str
    total_score: float
    p0_score: float
    p1_score: float
    missing_items: list[MissingDataItem]
    counts: dict[str, int]


class IdentificationReadinessReport(BaseModel):
    object_id: str
    readiness_level: str
    total_score: float
    recommended_parameters: list[str]
    blocked_parameters: list[str]
    next_measurements: list[str]


class ElementStateObservationRecord(BaseModel):
    object_id: str
    element_id: str
    timestamp: datetime
    design_geometry: dict[str, Any]
    design_material: dict[str, Any]
    current_defects: list[dict[str, Any]]
    current_measurements: list[dict[str, Any]]
    current_environment: list[dict[str, Any]]
    current_operation_mode: Optional[str] = None
    intervention_history: list[dict[str, Any]]
    quality_profile: list[dict[str, Any]]


class ObservationPackage(BaseModel):
    object: AssetObjectRead
    elements: list[StructuralElementRead]
    defects: list[DefectRead]
    channels: list[ObservationChannelRead]
    measurements: list[MeasurementRead]
    environment_records: list[EnvironmentRecordRead]
    interventions: list[InterventionRead]
    tests: list[TestRecordRead]
    media_assets: list[MediaAssetRead]
    quality_records: list[DataQualityRecordRead]
    element_state_observation_records: list[ElementStateObservationRecord]
    information_sufficiency_index: InformationSufficiencyIndex
    identification_readiness_report: IdentificationReadinessReport
    critical_missing_data_list: list[MissingDataItem]


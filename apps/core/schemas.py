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
    role_criticality: Optional[str] = None
    consequence_class: Optional[str] = None
    identification_priority: Optional[str] = None
    degradation_mechanisms: Optional[list[str]] = None
    element_type: Optional[str] = None
    geometry_type: Optional[str] = None
    section_name: Optional[str] = None
    section_family: Optional[str] = None
    length: Optional[float] = None
    span: Optional[float] = None
    height: Optional[float] = None
    thickness: Optional[float] = None
    area: Optional[float] = None
    inertia_x: Optional[float] = None
    inertia_y: Optional[float] = None
    section_modulus_x: Optional[float] = None
    section_modulus_y: Optional[float] = None
    torsion_constant: Optional[float] = None
    buckling_length_x: Optional[float] = None
    buckling_length_y: Optional[float] = None
    coordinates_local: Optional[str] = None
    coordinates_global: Optional[str] = None
    material_type: Optional[str] = None
    material_grade_design: Optional[str] = None
    material_grade_actual: Optional[str] = None
    concrete_class_design: Optional[str] = None
    concrete_class_actual: Optional[str] = None
    rebar_class: Optional[str] = None
    cover_thickness: Optional[float] = None
    reinforcement_ratio: Optional[float] = None
    rebar_area: Optional[float] = None
    carbonation_depth: Optional[float] = None
    chloride_exposure_class: Optional[str] = None
    steel_grade_design: Optional[str] = None
    steel_grade_actual: Optional[str] = None
    weld_type: Optional[str] = None
    bolt_class: Optional[str] = None
    corrosion_loss_mm: Optional[float] = None
    elastic_modulus_design: Optional[float] = None
    elastic_modulus_actual: Optional[float] = None
    strength_design: Optional[float] = None
    strength_actual: Optional[float] = None
    material_density: Optional[float] = None
    support_type: Optional[str] = None
    support_stiffness: Optional[float] = None
    support_kx: Optional[float] = None
    support_ky: Optional[float] = None
    support_kz: Optional[float] = None
    support_rx: Optional[float] = None
    support_ry: Optional[float] = None
    support_rz: Optional[float] = None
    joint_type: Optional[str] = None
    joint_flexibility: Optional[float] = None
    joint_flexibility_x: Optional[float] = None
    joint_flexibility_y: Optional[float] = None
    joint_flexibility_z: Optional[float] = None
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
    role_criticality: Optional[str] = None
    consequence_class: Optional[str] = None
    identification_priority: Optional[str] = None
    degradation_mechanisms: Optional[list[str]] = None
    element_type: Optional[str] = None
    geometry_type: Optional[str] = None
    section_name: Optional[str] = None
    section_family: Optional[str] = None
    length: Optional[float] = None
    span: Optional[float] = None
    height: Optional[float] = None
    thickness: Optional[float] = None
    area: Optional[float] = None
    inertia_x: Optional[float] = None
    inertia_y: Optional[float] = None
    section_modulus_x: Optional[float] = None
    section_modulus_y: Optional[float] = None
    torsion_constant: Optional[float] = None
    buckling_length_x: Optional[float] = None
    buckling_length_y: Optional[float] = None
    coordinates_local: Optional[str] = None
    coordinates_global: Optional[str] = None
    material_type: Optional[str] = None
    material_grade_design: Optional[str] = None
    material_grade_actual: Optional[str] = None
    concrete_class_design: Optional[str] = None
    concrete_class_actual: Optional[str] = None
    rebar_class: Optional[str] = None
    cover_thickness: Optional[float] = None
    reinforcement_ratio: Optional[float] = None
    rebar_area: Optional[float] = None
    carbonation_depth: Optional[float] = None
    chloride_exposure_class: Optional[str] = None
    steel_grade_design: Optional[str] = None
    steel_grade_actual: Optional[str] = None
    weld_type: Optional[str] = None
    bolt_class: Optional[str] = None
    corrosion_loss_mm: Optional[float] = None
    elastic_modulus_design: Optional[float] = None
    elastic_modulus_actual: Optional[float] = None
    strength_design: Optional[float] = None
    strength_actual: Optional[float] = None
    material_density: Optional[float] = None
    support_type: Optional[str] = None
    support_stiffness: Optional[float] = None
    support_kx: Optional[float] = None
    support_ky: Optional[float] = None
    support_kz: Optional[float] = None
    support_rx: Optional[float] = None
    support_ry: Optional[float] = None
    support_rz: Optional[float] = None
    joint_type: Optional[str] = None
    joint_flexibility: Optional[float] = None
    joint_flexibility_x: Optional[float] = None
    joint_flexibility_y: Optional[float] = None
    joint_flexibility_z: Optional[float] = None
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
    material_family: Optional[str] = None
    element_classifier: Optional[str] = None
    corrosion_depth: Optional[float] = None
    section_loss_percent: Optional[float] = None
    weld_damage_type: Optional[str] = None
    bolt_condition: Optional[str] = None
    local_buckling_flag: Optional[bool] = None
    fatigue_crack_length: Optional[float] = None
    crack_type: Optional[str] = None
    cover_loss_area: Optional[float] = None
    rebar_corrosion_class: Optional[str] = None
    carbonation_depth: Optional[float] = None
    bond_loss_flag: Optional[bool] = None
    damage_mechanism: Optional[str] = None
    severity_class: Optional[str] = None
    face_or_zone: Optional[str] = None
    local_coordinate: Optional[str] = None
    growth_rate_estimate: Optional[float] = None
    inspection_method: Optional[str] = None
    confidence_severity: Optional[float] = None
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
    material_family: Optional[str] = None
    element_classifier: Optional[str] = None
    corrosion_depth: Optional[float] = None
    section_loss_percent: Optional[float] = None
    weld_damage_type: Optional[str] = None
    bolt_condition: Optional[str] = None
    local_buckling_flag: Optional[bool] = None
    fatigue_crack_length: Optional[float] = None
    crack_type: Optional[str] = None
    cover_loss_area: Optional[float] = None
    rebar_corrosion_class: Optional[str] = None
    carbonation_depth: Optional[float] = None
    bond_loss_flag: Optional[bool] = None
    damage_mechanism: Optional[str] = None
    severity_class: Optional[str] = None
    face_or_zone: Optional[str] = None
    local_coordinate: Optional[str] = None
    growth_rate_estimate: Optional[float] = None
    inspection_method: Optional[str] = None
    confidence_severity: Optional[float] = None
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
    axis_direction: Optional[str] = None
    sign_convention: Optional[str] = None
    load_case_reference: Optional[str] = None
    temperature_compensated: Optional[bool] = None
    aggregation_method: Optional[str] = None
    device_id: Optional[str] = None
    calibration_reference: Optional[str] = None
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
    axis_direction: Optional[str] = None
    sign_convention: Optional[str] = None
    load_case_reference: Optional[str] = None
    temperature_compensated: Optional[bool] = None
    aggregation_method: Optional[str] = None
    device_id: Optional[str] = None
    calibration_reference: Optional[str] = None
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
    axis_direction: Optional[str] = None
    sign_convention: Optional[str] = None
    load_case_reference: Optional[str] = None
    temperature_compensated: Optional[bool] = None
    aggregation_method: Optional[str] = None
    device_id: Optional[str] = None
    calibration_reference: Optional[str] = None


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
    axis_direction: Optional[str] = None
    sign_convention: Optional[str] = None
    load_case_reference: Optional[str] = None
    temperature_compensated: Optional[bool] = None
    aggregation_method: Optional[str] = None
    device_id: Optional[str] = None
    calibration_reference: Optional[str] = None


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
    coverage: Optional[float] = None
    scope: str = "object"
    element_id: Optional[str] = None
    element_name: Optional[str] = None


class SufficiencyDomainScores(BaseModel):
    object_passport_score: float
    structural_model_score: float
    defect_registry_score: float
    measurement_score: float
    boundary_conditions_score: float
    environment_score: float
    intervention_history_score: float
    testing_score: float
    quality_traceability_score: float


class SufficiencyLevelScores(BaseModel):
    descriptive_readiness_score: float
    identification_readiness_score: float
    predictive_readiness_score: float
    descriptive_only: float
    identification_ready: float
    prediction_ready: float


class DataCoverage(BaseModel):
    temporal_coverage: float
    spatial_coverage: float
    observation_density: float
    uncertainty_level: float


class InformationSufficiencyIndex(BaseModel):
    object_id: str
    total_score: float
    p0_score: float
    p1_score: float
    missing_items: list[MissingDataItem]
    counts: dict[str, int]
    domain_scores: SufficiencyDomainScores
    level_scores: SufficiencyLevelScores
    responsibility_factor: float
    requirement_scores: dict[str, float]
    coverage_by_critical_elements: dict[str, float]
    coverage_by_parameter_group: dict[str, float]
    quality_weighted_measurement_coverage: float


class IdentificationReadinessReport(BaseModel):
    object_id: str
    readiness_level: str
    total_score: float
    recommended_parameters: list[str]
    blocked_parameters: list[str]
    next_measurements: list[str]
    geometry_ready: str
    stiffness_ready: str
    damage_ready: str
    material_ready: str
    boundary_ready: str
    geometry_and_scheme_ready: str
    materials_ready: str
    damage_state_ready: str
    boundary_conditions_ready: str
    dynamic_response_ready: str
    prognosis_preconditions_ready: str
    task_scores: dict[str, float]


class ElementStateObservationRecord(BaseModel):
    object_id: str
    element_id: str
    timestamp: datetime
    hierarchy_type: str
    structural_role: Optional[str] = None
    role_criticality: Optional[str] = None
    consequence_class: Optional[str] = None
    identification_priority: Optional[str] = None
    degradation_mechanisms: Optional[list[str]] = None
    support_type: Optional[str] = None
    support_stiffness: Optional[float] = None
    joint_type: Optional[str] = None
    joint_flexibility: Optional[float] = None
    material_grade_actual: Optional[str] = None
    elastic_modulus_actual: Optional[float] = None
    strength_actual: Optional[float] = None
    design_geometry: dict[str, Any]
    design_material: dict[str, Any]
    actual_material: dict[str, Any]
    section_properties: dict[str, Any]
    boundary_conditions: dict[str, Any]
    data_coverage: DataCoverage
    critical_missing_data_list: list[MissingDataItem]
    critical_missing_data_by_element: list[MissingDataItem]
    current_defects: list[dict[str, Any]]
    current_measurements: list[dict[str, Any]]
    current_environment: list[dict[str, Any]]
    current_operation_mode: Optional[str] = None
    intervention_history: list[dict[str, Any]]
    test_history: list[dict[str, Any]]
    quality_profile: list[dict[str, Any]]


class ObservationPackage(BaseModel):
    export_version: str = "v1.1"
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


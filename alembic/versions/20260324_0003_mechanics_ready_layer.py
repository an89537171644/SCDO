"""Add mechanics-ready element, defect, and measurement metadata."""

from __future__ import annotations

from collections.abc import Iterable

from alembic import op
import sqlalchemy as sa


revision = "20260324_0003"
down_revision = "20260324_0002"
branch_labels = None
depends_on = None


STRUCTURAL_ELEMENT_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("section_name", sa.String(length=128)),
    ("section_family", sa.String(length=128)),
    ("inertia_x", sa.Float()),
    ("inertia_y", sa.Float()),
    ("section_modulus_x", sa.Float()),
    ("section_modulus_y", sa.Float()),
    ("torsion_constant", sa.Float()),
    ("buckling_length_x", sa.Float()),
    ("buckling_length_y", sa.Float()),
    ("concrete_class_design", sa.String(length=128)),
    ("concrete_class_actual", sa.String(length=128)),
    ("rebar_class", sa.String(length=128)),
    ("cover_thickness", sa.Float()),
    ("reinforcement_ratio", sa.Float()),
    ("rebar_area", sa.Float()),
    ("carbonation_depth", sa.Float()),
    ("chloride_exposure_class", sa.String(length=128)),
    ("steel_grade_design", sa.String(length=128)),
    ("steel_grade_actual", sa.String(length=128)),
    ("weld_type", sa.String(length=128)),
    ("bolt_class", sa.String(length=128)),
    ("corrosion_loss_mm", sa.Float()),
    ("material_density", sa.Float()),
    ("support_kx", sa.Float()),
    ("support_ky", sa.Float()),
    ("support_kz", sa.Float()),
    ("support_rx", sa.Float()),
    ("support_ry", sa.Float()),
    ("support_rz", sa.Float()),
    ("joint_flexibility_x", sa.Float()),
    ("joint_flexibility_y", sa.Float()),
    ("joint_flexibility_z", sa.Float()),
)

DEFECT_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("damage_mechanism", sa.String(length=128)),
    ("severity_class", sa.String(length=64)),
    ("face_or_zone", sa.String(length=128)),
    ("local_coordinate", sa.String(length=128)),
    ("growth_rate_estimate", sa.Float()),
    ("inspection_method", sa.String(length=128)),
    ("confidence_severity", sa.Float()),
)

OBSERVATION_CHANNEL_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("axis_direction", sa.String(length=32)),
    ("sign_convention", sa.String(length=64)),
    ("load_case_reference", sa.String(length=128)),
    ("temperature_compensated", sa.Boolean()),
    ("aggregation_method", sa.String(length=64)),
    ("device_id", sa.String(length=128)),
    ("calibration_reference", sa.String(length=255)),
)

MEASUREMENT_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("axis_direction", sa.String(length=32)),
    ("sign_convention", sa.String(length=64)),
    ("load_case_reference", sa.String(length=128)),
    ("temperature_compensated", sa.Boolean()),
    ("aggregation_method", sa.String(length=64)),
    ("device_id", sa.String(length=128)),
    ("calibration_reference", sa.String(length=255)),
)


def _existing_columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {column["name"] for column in inspector.get_columns(table_name)}


def _add_missing_columns(table_name: str, columns: Iterable[tuple[str, sa.types.TypeEngine]]) -> None:
    existing = _existing_columns(table_name)
    missing = [(name, column_type) for name, column_type in columns if name not in existing]
    if not missing:
        return
    with op.batch_alter_table(table_name) as batch_op:
        for name, column_type in missing:
            batch_op.add_column(sa.Column(name, column_type, nullable=True))


def _drop_present_columns(table_name: str, column_names: Iterable[str]) -> None:
    existing = _existing_columns(table_name)
    removable = [name for name in column_names if name in existing]
    if not removable:
        return
    with op.batch_alter_table(table_name) as batch_op:
        for name in removable:
            batch_op.drop_column(name)


def upgrade() -> None:
    _add_missing_columns("structural_elements", STRUCTURAL_ELEMENT_COLUMNS)
    _add_missing_columns("defects", DEFECT_COLUMNS)
    _add_missing_columns("observation_channels", OBSERVATION_CHANNEL_COLUMNS)
    _add_missing_columns("measurements", MEASUREMENT_COLUMNS)


def downgrade() -> None:
    _drop_present_columns("measurements", [name for name, _ in reversed(MEASUREMENT_COLUMNS)])
    _drop_present_columns("observation_channels", [name for name, _ in reversed(OBSERVATION_CHANNEL_COLUMNS)])
    _drop_present_columns("defects", [name for name, _ in reversed(DEFECT_COLUMNS)])
    _drop_present_columns("structural_elements", [name for name, _ in reversed(STRUCTURAL_ELEMENT_COLUMNS)])

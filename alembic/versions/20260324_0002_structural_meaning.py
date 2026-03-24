"""Add structural criticality and parameterized defect fields."""

from __future__ import annotations

from collections.abc import Iterable

from alembic import op
import sqlalchemy as sa


revision = "20260324_0002"
down_revision = "20260324_0001"
branch_labels = None
depends_on = None


STRUCTURAL_ELEMENT_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("role_criticality", sa.String(length=64)),
    ("consequence_class", sa.String(length=64)),
    ("identification_priority", sa.String(length=64)),
    ("degradation_mechanisms", sa.JSON()),
)

DEFECT_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    ("material_family", sa.String(length=64)),
    ("element_classifier", sa.String(length=128)),
    ("corrosion_depth", sa.Float()),
    ("section_loss_percent", sa.Float()),
    ("weld_damage_type", sa.String(length=128)),
    ("bolt_condition", sa.String(length=128)),
    ("local_buckling_flag", sa.Boolean()),
    ("fatigue_crack_length", sa.Float()),
    ("crack_type", sa.String(length=128)),
    ("cover_loss_area", sa.Float()),
    ("rebar_corrosion_class", sa.String(length=128)),
    ("carbonation_depth", sa.Float()),
    ("bond_loss_flag", sa.Boolean()),
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


def downgrade() -> None:
    _drop_present_columns("defects", [name for name, _ in reversed(DEFECT_COLUMNS)])
    _drop_present_columns("structural_elements", [name for name, _ in reversed(STRUCTURAL_ELEMENT_COLUMNS)])

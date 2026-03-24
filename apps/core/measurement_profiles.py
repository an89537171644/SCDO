from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from apps.core import schemas
from apps.db import models


class MeasurementValidationError(ValueError):
    pass


@dataclass(frozen=True)
class MeasurementProfile:
    code: str
    label_ru: str
    allowed_units: tuple[str, ...]
    unit_ranges: dict[str, tuple[float, float]]
    requires_spatial_location: bool
    sign_rule: str
    resampling_rule: str
    description: str
    example_value: float
    example_unit: str


MEASUREMENT_PROFILES: dict[str, MeasurementProfile] = {
    "deflection": MeasurementProfile(
        code="deflection",
        label_ru="Прогиб",
        allowed_units=("mm", "cm", "m"),
        unit_ranges={"mm": (-500.0, 500.0), "cm": (-50.0, 50.0), "m": (-0.5, 0.5)},
        requires_spatial_location=True,
        sign_rule="signed",
        resampling_rule="mean_over_window",
        description="Прогиб элемента относительно исходного положения.",
        example_value=4.2,
        example_unit="mm",
    ),
    "displacement": MeasurementProfile(
        code="displacement",
        label_ru="Перемещение",
        allowed_units=("mm", "cm", "m"),
        unit_ranges={"mm": (-1000.0, 1000.0), "cm": (-100.0, 100.0), "m": (-1.0, 1.0)},
        requires_spatial_location=True,
        sign_rule="signed",
        resampling_rule="linear_interpolation",
        description="Линейное перемещение точки конструкции.",
        example_value=2.8,
        example_unit="mm",
    ),
    "strain": MeasurementProfile(
        code="strain",
        label_ru="Деформация",
        allowed_units=("microstrain", "strain"),
        unit_ranges={"microstrain": (-10000.0, 10000.0), "strain": (-0.01, 0.01)},
        requires_spatial_location=True,
        sign_rule="signed",
        resampling_rule="mean_over_window",
        description="Относительная деформация материала или элемента.",
        example_value=120.0,
        example_unit="microstrain",
    ),
    "crack_width": MeasurementProfile(
        code="crack_width",
        label_ru="Ширина трещины",
        allowed_units=("mm",),
        unit_ranges={"mm": (0.0, 20.0)},
        requires_spatial_location=True,
        sign_rule="nonnegative",
        resampling_rule="keep_last",
        description="Ширина раскрытия трещины.",
        example_value=0.35,
        example_unit="mm",
    ),
    "settlement": MeasurementProfile(
        code="settlement",
        label_ru="Осадка",
        allowed_units=("mm", "cm"),
        unit_ranges={"mm": (0.0, 500.0), "cm": (0.0, 50.0)},
        requires_spatial_location=True,
        sign_rule="nonnegative",
        resampling_rule="linear_interpolation",
        description="Осадка точки или опоры.",
        example_value=3.0,
        example_unit="mm",
    ),
    "tilt": MeasurementProfile(
        code="tilt",
        label_ru="Наклон",
        allowed_units=("mrad", "deg"),
        unit_ranges={"mrad": (-50.0, 50.0), "deg": (-3.0, 3.0)},
        requires_spatial_location=True,
        sign_rule="signed",
        resampling_rule="linear_interpolation",
        description="Угол наклона элемента или опоры.",
        example_value=0.8,
        example_unit="mrad",
    ),
    "frequency": MeasurementProfile(
        code="frequency",
        label_ru="Частота",
        allowed_units=("Hz",),
        unit_ranges={"Hz": (0.0, 500.0)},
        requires_spatial_location=False,
        sign_rule="nonnegative",
        resampling_rule="mean_over_window",
        description="Собственная или рабочая частота отклика.",
        example_value=6.5,
        example_unit="Hz",
    ),
    "acceleration": MeasurementProfile(
        code="acceleration",
        label_ru="Ускорение",
        allowed_units=("m/s2", "g"),
        unit_ranges={"m/s2": (-100.0, 100.0), "g": (-10.0, 10.0)},
        requires_spatial_location=True,
        sign_rule="signed",
        resampling_rule="rms_or_peak",
        description="Ускорение отклика конструкции.",
        example_value=0.25,
        example_unit="g",
    ),
    "temperature": MeasurementProfile(
        code="temperature",
        label_ru="Температура",
        allowed_units=("C", "K"),
        unit_ranges={"C": (-80.0, 120.0), "K": (193.0, 393.0)},
        requires_spatial_location=False,
        sign_rule="signed",
        resampling_rule="mean_over_window",
        description="Температура среды или элемента.",
        example_value=18.0,
        example_unit="C",
    ),
    "humidity": MeasurementProfile(
        code="humidity",
        label_ru="Влажность",
        allowed_units=("%",),
        unit_ranges={"%": (0.0, 100.0)},
        requires_spatial_location=False,
        sign_rule="nonnegative",
        resampling_rule="mean_over_window",
        description="Относительная влажность среды.",
        example_value=65.0,
        example_unit="%",
    ),
}


def normalize_measurement_type(value: str) -> str:
    return (value or "").strip().lower().replace(" ", "_")


def list_measurement_profiles() -> list[MeasurementProfile]:
    return [MEASUREMENT_PROFILES[key] for key in sorted(MEASUREMENT_PROFILES.keys())]


def get_measurement_profile(measured_quantity: str) -> MeasurementProfile:
    normalized = normalize_measurement_type(measured_quantity)
    profile = MEASUREMENT_PROFILES.get(normalized)
    if profile is None:
        supported = ", ".join(sorted(MEASUREMENT_PROFILES.keys()))
        raise MeasurementValidationError(
            f"Тип измерения '{measured_quantity}' не поддерживается. Доступно: {supported}."
        )
    return profile


def build_template_csv(profile_code: str) -> str:
    profile = get_measurement_profile(profile_code)
    return "\n".join(
        [
            "timestamp,value,unit,spatial_location,source_type,quality_flag,axis_direction,load_case_reference,temperature_compensated,aggregation_method",
            f"2026-03-01T10:00:00Z,{profile.example_value},{profile.example_unit},midspan,monitoring,validated,Z,normal_operation,true,{profile.resampling_rule}",
            f"2026-03-01T11:00:00Z,{profile.example_value},{profile.example_unit},midspan,monitoring,validated,Z,normal_operation,true,{profile.resampling_rule}",
        ]
    )


def _group_by_channel(
    payloads: list[schemas.CreateMeasurement],
) -> dict[str, list[schemas.CreateMeasurement]]:
    grouped: dict[str, list[schemas.CreateMeasurement]] = {}
    for payload in payloads:
        grouped.setdefault(payload.channel_id, []).append(payload)
    return grouped


def _validate_units_and_ranges(
    payload: schemas.CreateMeasurement,
    channel: models.ObservationChannel,
    profile: MeasurementProfile,
) -> None:
    if payload.unit not in profile.allowed_units:
        allowed = ", ".join(profile.allowed_units)
        raise MeasurementValidationError(
            f"Канал '{channel.channel_code}': единица '{payload.unit}' недопустима для типа "
            f"'{profile.code}'. Разрешены: {allowed}."
        )
    min_value, max_value = profile.unit_ranges[payload.unit]
    if not (min_value <= payload.value <= max_value):
        raise MeasurementValidationError(
            f"Канал '{channel.channel_code}': значение {payload.value} {payload.unit} выходит за "
            f"допустимый диапазон [{min_value}, {max_value}] для типа '{profile.code}'."
        )
    if profile.sign_rule == "nonnegative" and payload.value < 0:
        raise MeasurementValidationError(
            f"Канал '{channel.channel_code}': для типа '{profile.code}' отрицательные значения недопустимы."
        )
    if profile.requires_spatial_location and not (payload.spatial_location or channel.spatial_location):
        raise MeasurementValidationError(
            f"Канал '{channel.channel_code}': нужна пространственная привязка "
            f"`spatial_location` для типа '{profile.code}'."
        )


def _validate_channel_binding(
    payload: schemas.CreateMeasurement,
    channel: models.ObservationChannel,
) -> None:
    if payload.object_id != channel.object_id:
        raise MeasurementValidationError(
            f"Канал '{channel.channel_code}' принадлежит другому объекту."
        )
    if payload.element_id != channel.element_id:
        raise MeasurementValidationError(
            f"Канал '{channel.channel_code}' привязан к другому элементу."
        )


def _validate_duplicate_timestamps(
    session: Session,
    channel: models.ObservationChannel,
    payloads: list[schemas.CreateMeasurement],
) -> None:
    timestamps = [payload.timestamp for payload in payloads]
    if len(timestamps) != len(set(timestamps)):
        raise MeasurementValidationError(
            f"Канал '{channel.channel_code}': в загружаемом наборе есть дубликаты timestamp."
        )

    existing = set(
        session.scalars(
            select(models.Measurement.timestamp).where(models.Measurement.channel_id == channel.id)
        ).all()
    )
    duplicates = sorted(timestamp.isoformat() for timestamp in timestamps if timestamp in existing)
    if duplicates:
        raise MeasurementValidationError(
            f"Канал '{channel.channel_code}': в базе уже есть измерения с timestamp: {', '.join(duplicates[:5])}."
        )


def _validate_time_gaps(channel: models.ObservationChannel, payloads: list[schemas.CreateMeasurement]) -> None:
    if len(payloads) < 4:
        return
    timestamps = sorted(payload.timestamp for payload in payloads)
    intervals = [
        (timestamps[index] - timestamps[index - 1]).total_seconds()
        for index in range(1, len(timestamps))
    ]
    positive_intervals = [interval for interval in intervals if interval > 0]
    if len(positive_intervals) < 2:
        return
    reference = median(positive_intervals)
    if reference <= 0:
        return
    if any(interval > reference * 4 for interval in positive_intervals):
        raise MeasurementValidationError(
            f"Канал '{channel.channel_code}': обнаружен крупный разрыв по времени. "
            f"Проверьте пропуски и правило ресемплинга '{get_measurement_profile(channel.measured_quantity).resampling_rule}'."
        )


def _validate_outliers(channel: models.ObservationChannel, payloads: list[schemas.CreateMeasurement]) -> None:
    if len(payloads) < 5:
        return
    values = [payload.value for payload in payloads]
    center = median(values)
    deviations = [abs(value - center) for value in values]
    mad = median(deviations)
    if mad == 0:
        return
    threshold = mad * 6
    if any(abs(value - center) > threshold for value in values):
        raise MeasurementValidationError(
            f"Канал '{channel.channel_code}': обнаружен грубый выброс в значениях ряда."
        )


def validate_measurement_import(
    session: Session,
    payloads: list[schemas.CreateMeasurement],
) -> None:
    if not payloads:
        return

    channel_ids = sorted({payload.channel_id for payload in payloads})
    channels = {
        channel.id: channel
        for channel in session.scalars(
            select(models.ObservationChannel).where(models.ObservationChannel.id.in_(channel_ids))
        ).all()
    }

    missing_channels = [channel_id for channel_id in channel_ids if channel_id not in channels]
    if missing_channels:
        raise MeasurementValidationError(
            f"Не найдены каналы измерений: {', '.join(missing_channels)}."
        )

    grouped = _group_by_channel(payloads)
    for channel_id, items in grouped.items():
        channel = channels[channel_id]
        profile = get_measurement_profile(channel.measured_quantity)
        for payload in items:
            _validate_channel_binding(payload, channel)
            _validate_units_and_ranges(payload, channel, profile)
        _validate_duplicate_timestamps(session, channel, items)
        _validate_time_gaps(channel, items)
        _validate_outliers(channel, items)

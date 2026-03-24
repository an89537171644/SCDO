from __future__ import annotations

from apps.core.measurement_profiles import build_template_csv
from apps.core.measurement_profiles import get_measurement_profile
from apps.core.measurement_profiles import list_measurement_profiles


def test_measurement_profiles_cover_expected_engineering_types() -> None:
    codes = {profile.code for profile in list_measurement_profiles()}
    assert {
        "deflection",
        "displacement",
        "strain",
        "crack_width",
        "settlement",
        "tilt",
        "frequency",
        "acceleration",
        "temperature",
        "humidity",
    }.issubset(codes)


def test_template_csv_contains_required_headers() -> None:
    profile = get_measurement_profile("deflection")
    template = build_template_csv(profile.code)

    assert "timestamp,value,unit,spatial_location,source_type,quality_flag" in template
    assert "monitoring" in template

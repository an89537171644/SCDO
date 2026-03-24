from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook

from apps.ui.import_utils import parse_measurement_file
from apps.ui.import_utils import prepare_measurement_records


def test_prepare_measurement_records_supports_semicolon_csv_and_comma_decimal() -> None:
    csv_bytes = (
        "timestamp;value;unit;accuracy;source_type\n"
        "2026-03-01T10:00:00Z;1,25;mm;0,05;monitoring\n"
    ).encode("utf-8")

    rows = parse_measurement_file("measurements.csv", csv_bytes)
    records = prepare_measurement_records(
        rows,
        object_id="object-1",
        element_id="element-1",
        channel_id="channel-1",
        default_unit="mm",
    )

    assert len(records) == 1
    assert records[0]["value"] == 1.25
    assert records[0]["accuracy"] == 0.05
    assert records[0]["unit"] == "mm"


def test_parse_measurement_file_reads_xlsx() -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["timestamp", "value", "unit"])
    sheet.append(["2026-03-01T10:00:00Z", 2.5, "mm"])

    buffer = BytesIO()
    workbook.save(buffer)

    rows = parse_measurement_file("measurements.xlsx", buffer.getvalue())

    assert rows == [{"timestamp": "2026-03-01T10:00:00Z", "value": 2.5, "unit": "mm"}]

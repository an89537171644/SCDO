from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.core import schemas
from apps.core import services
from apps.db.session import SessionLocal


DEMO_PATH = ROOT / "sample_data" / "demo_bundle.json"


def main() -> None:
    bundle = json.loads(DEMO_PATH.read_text(encoding="utf-8"))
    session = SessionLocal()
    try:
        asset_object = services.asset_object_service.create(
            session, schemas.CreateAssetObject.model_validate(bundle["object"])
        )

        element_id_by_key: dict[str, str] = {}
        pending_elements = list(bundle["elements"])
        while pending_elements:
            element_data = pending_elements.pop(0)
            parent_key = element_data.pop("parent_key", None)
            element_key = element_data.pop("key")
            if parent_key and parent_key not in element_id_by_key:
                pending_elements.append(element_data | {"key": element_key, "parent_key": parent_key})
                continue

            payload = schemas.CreateStructuralElement.model_validate(
                {
                    **element_data,
                    "object_id": asset_object.id,
                    "parent_id": element_id_by_key.get(parent_key),
                }
            )
            created = services.element_service.create(session, payload)
            element_id_by_key[element_key] = created.id

        channel_id_by_key: dict[str, str] = {}
        measurement_id_by_key: dict[str, str] = {}

        for defect_data in bundle["defects"]:
            payload = schemas.CreateDefect.model_validate(
                {
                    **{key: value for key, value in defect_data.items() if key != "element_key"},
                    "object_id": asset_object.id,
                    "element_id": element_id_by_key[defect_data["element_key"]],
                }
            )
            services.defect_service.create(session, payload)

        for channel_data in bundle["channels"]:
            channel_key = channel_data["key"]
            payload = schemas.CreateObservationChannel.model_validate(
                {
                    **{key: value for key, value in channel_data.items() if key not in {"key", "element_key"}},
                    "object_id": asset_object.id,
                    "element_id": element_id_by_key[channel_data["element_key"]],
                }
            )
            channel = services.channel_service.create(session, payload)
            channel_id_by_key[channel_key] = channel.id

        for measurement_data in bundle["measurements"]:
            measurement_key = measurement_data["key"]
            payload = schemas.CreateMeasurement.model_validate(
                {
                    **{
                        key: value
                        for key, value in measurement_data.items()
                        if key not in {"key", "element_key", "channel_key"}
                    },
                    "object_id": asset_object.id,
                    "element_id": element_id_by_key[measurement_data["element_key"]],
                    "channel_id": channel_id_by_key[measurement_data["channel_key"]],
                }
            )
            measurement = services.measurement_service.create(session, payload)
            measurement_id_by_key[measurement_key] = measurement.id

        for record in bundle["environment_records"]:
            payload = schemas.CreateEnvironmentRecord.model_validate(
                {
                    **{key: value for key, value in record.items() if key != "element_key"},
                    "object_id": asset_object.id,
                    "element_id": element_id_by_key[record["element_key"]],
                }
            )
            services.environment_service.create(session, payload)

        for record in bundle["interventions"]:
            payload = schemas.CreateIntervention.model_validate(
                {
                    **{key: value for key, value in record.items() if key != "element_key"},
                    "object_id": asset_object.id,
                    "element_id": element_id_by_key[record["element_key"]],
                }
            )
            services.intervention_service.create(session, payload)

        for record in bundle["tests"]:
            payload = schemas.CreateTestRecord.model_validate(
                {
                    **{key: value for key, value in record.items() if key != "element_key"},
                    "object_id": asset_object.id,
                    "element_id": element_id_by_key[record["element_key"]],
                }
            )
            services.test_service.create(session, payload)

        for record in bundle.get("media_assets", []):
            payload = schemas.CreateMediaAsset.model_validate(
                {
                    **{key: value for key, value in record.items() if key not in {"element_key", "defect_key"}},
                    "object_id": asset_object.id,
                    "element_id": element_id_by_key.get(record.get("element_key")),
                }
            )
            services.media_service.create(session, payload)

        for record in bundle["quality_records"]:
            payload = schemas.CreateDataQualityRecord.model_validate(
                {
                    **{
                        key: value
                        for key, value in record.items()
                        if key not in {"element_key", "entity_ref"}
                    },
                    "object_id": asset_object.id,
                    "element_id": element_id_by_key[record["element_key"]],
                    "entity_id": measurement_id_by_key.get(record["entity_ref"], record["entity_ref"]),
                }
            )
            services.quality_service.create(session, payload)

        print(f"Loaded demo dataset for object {asset_object.id}")
    finally:
        session.close()


if __name__ == "__main__":
    main()

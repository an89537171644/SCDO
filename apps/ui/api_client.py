from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from typing import Optional

import requests


class APIError(RuntimeError):
    pass


@dataclass
class APIClient:
    base_url: str
    timeout: int = 20

    def _full_url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def _extract_error(self, response: requests.Response) -> str:
        try:
            payload = response.json()
        except Exception:
            return f"Ошибка сервера: {response.status_code}"

        detail = payload.get("detail")
        if isinstance(detail, str):
            return detail
        if isinstance(detail, list):
            return "; ".join(str(item) for item in detail)
        return f"Ошибка сервера: {response.status_code}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json_data: Optional[Any] = None,
    ) -> Any:
        try:
            response = requests.request(
                method=method,
                url=self._full_url(path),
                params=params,
                json=json_data,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise APIError(self._extract_error(exc.response)) from exc
        except requests.RequestException as exc:
            raise APIError("Не удалось подключиться к API. Проверьте, что backend запущен.") from exc

        if not response.content:
            return None
        return response.json()

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def list_objects(self) -> list[dict[str, Any]]:
        return self._request("GET", "/objects")

    def create_object(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/objects", json_data=payload)

    def update_object(self, object_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("PATCH", f"/objects/{object_id}", json_data=payload)

    def list_elements(self, object_id: str) -> list[dict[str, Any]]:
        return self._request("GET", "/elements", params={"object_id": object_id})

    def create_element(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/elements", json_data=payload)

    def list_defects(self, object_id: str) -> list[dict[str, Any]]:
        return self._request("GET", "/defects", params={"object_id": object_id})

    def create_defect(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/defects", json_data=payload)

    def list_channels(self, object_id: str) -> list[dict[str, Any]]:
        return self._request("GET", "/channels", params={"object_id": object_id})

    def create_channel(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/channels", json_data=payload)

    def list_measurements(self, object_id: str) -> list[dict[str, Any]]:
        return self._request("GET", "/measurements", params={"object_id": object_id})

    def list_environment_records(self, object_id: str) -> list[dict[str, Any]]:
        return self._request("GET", "/environment-records", params={"object_id": object_id})

    def list_interventions(self, object_id: str) -> list[dict[str, Any]]:
        return self._request("GET", "/interventions", params={"object_id": object_id})

    def list_tests(self, object_id: str) -> list[dict[str, Any]]:
        return self._request("GET", "/tests", params={"object_id": object_id})

    def list_quality_records(self, object_id: str) -> list[dict[str, Any]]:
        return self._request("GET", "/quality-records", params={"object_id": object_id})

    def import_json(self, entity_name: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return self._request("POST", f"/imports/{entity_name}/json", json_data=records)

    def get_information_sufficiency(self, object_id: str) -> dict[str, Any]:
        return self._request("GET", f"/analytics/objects/{object_id}/information-sufficiency")

    def get_identification_readiness(self, object_id: str) -> dict[str, Any]:
        return self._request("GET", f"/analytics/objects/{object_id}/identification-readiness")

    def export_observation_package(self, object_id: str) -> dict[str, Any]:
        return self._request("GET", f"/exports/objects/{object_id}/observation-package")

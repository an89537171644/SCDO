from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


class _Response:
    def __init__(self, payload):
        self._payload = payload
        self.content = b"{}"

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


def _fake_request(method, url, params=None, json=None, timeout=None):  # noqa: ANN001
    if url.endswith("/objects"):
        return _Response([])
    if url.endswith("/health"):
        return _Response({"status": "ok"})
    return _Response([])


def test_streamlit_app_smoke() -> None:
    with patch("requests.request", side_effect=_fake_request):
        app = AppTest.from_file(str(Path("apps/ui/app.py")))
        app.run(timeout=10)

    assert not app.exception
    assert app.title
    assert app.title[0].value == "СКДО"

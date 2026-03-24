from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from apps.core import services
from apps.db.models import Base
from tests.support import load_demo_bundle


POSTGRES_TEST_URL = os.getenv("SKDO_TEST_POSTGRES_URL")


@pytest.mark.skipif(not POSTGRES_TEST_URL, reason="SKDO_TEST_POSTGRES_URL is not configured")
def test_postgres_demo_bundle_contract() -> None:
    engine = create_engine(POSTGRES_TEST_URL, future=True)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = Session(engine)
    try:
        object_id = load_demo_bundle(session)
        package = services.build_observation_package(session, object_id)
        assert package.export_version == "v1.1"
        assert package.information_sufficiency_index.total_score > 0
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)

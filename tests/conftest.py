from collections.abc import Iterator

import pytest

from dslam.client import VigorClient
from tests.fake_draytek import FakeDraytek


@pytest.fixture
def fake() -> Iterator[FakeDraytek]:
    server = FakeDraytek().start()
    yield server
    server.stop()


@pytest.fixture
def client(fake: FakeDraytek) -> VigorClient:
    return VigorClient(
        host=f"http://{fake.address}", user="admin", password="admin",
        timeout=2,
    )

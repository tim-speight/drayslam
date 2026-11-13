"""Presentation layers consume the same DSLAMStatus (p4p server + FastAPI)."""
from collections.abc import Iterator
from dataclasses import replace

import pytest

from dslam.alarm_engine import AlarmEngine
from dslam.model import DSLAMStatus

STATUS = AlarmEngine().apply(DSLAMStatus(
    timestamp="2026-11-13T12:00:00+00:00",
    device_up=True,
    state="SHOWTIME",
    profile="17A",
    upstream_kbps=9696,
    downstream_kbps=31010,
    snr_up=7.5,
    snr_down=10.0,
    overall_status="ONLINE",
))


def test_api_serves_status() -> None:
    pytest.importorskip("httpx")
    from fastapi.testclient import TestClient

    from api import server

    api = TestClient(server.app)
    server.update_status(STATUS)

    body = api.get("/api/status").json()
    assert body["downstream_kbps"] == 31010
    assert body["snr_up_alarm"] == "MINOR"
    assert api.get("/health").json()["have_status"] is True


@pytest.fixture
def pva() -> Iterator[object]:
    pytest.importorskip("p4p")
    from p4p.client.thread import Context

    from epics import pva_server

    server = pva_server.start(isolate=True)
    ctxt = Context("pva", conf=server.conf(), useenv=False)
    yield ctxt
    ctxt.close()
    pva_server.stop()


def test_pvs_published_with_alarm_severity(pva: object) -> None:
    from epics import pva_server

    pva_server.update(STATUS)

    snr_up = pva.get("DSLAM:SNR_UP")  # type: ignore[attr-defined]
    assert snr_up == 7.5
    assert snr_up.severity == 1  # MINOR from thresholds.json
    assert pva.get("DSLAM:DOWNSTREAM_KBPS") == 31010  # type: ignore[attr-defined]
    assert pva.get("DSLAM:SNR_DOWN").severity == 0  # type: ignore[attr-defined]


def test_device_down_marks_pvs_invalid(pva: object) -> None:
    from epics import pva_server

    down = AlarmEngine().apply(replace(
        STATUS, device_up=False, state="DOWN", overall_status="ONT_SYSDOWN"))
    pva_server.update(down)

    assert pva.get("DSLAM:SNR_DOWN").severity == 3  # type: ignore[attr-defined]
    assert pva.get("DSLAM:DEVICE_UP").severity == 3  # type: ignore[attr-defined]
    assert pva.get("DSLAM:STATUS") == "ONT_SYSDOWN"  # type: ignore[attr-defined]

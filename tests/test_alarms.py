from dataclasses import replace

import pytest

from dslam.alarm_engine import AlarmEngine
from dslam.model import DSLAMStatus

BASE = DSLAMStatus(
    timestamp="2026-11-13T12:00:00+00:00",
    device_up=True,
    state="SHOWTIME",
    profile="17A",
    upstream_kbps=9696,
    downstream_kbps=31010,
    snr_up=10.0,
    snr_down=10.0,
)


@pytest.fixture(scope="module")
def engine() -> AlarmEngine:
    return AlarmEngine()  # loads config/thresholds.json independent of cwd


@pytest.mark.parametrize("snr, expected", [
    (10.0, "NO_ALARM"), (8.0, "MINOR"), (6.0, "MAJOR"), (2.0, "INVALID"),
])
def test_snr_thresholds(engine: AlarmEngine, snr: float, expected: str) -> None:
    status = engine.apply(replace(BASE, snr_down=snr))
    assert status.snr_down_alarm == expected
    assert status.snr_up_alarm == "NO_ALARM"  # evaluated independently


def test_rate_thresholds(engine: AlarmEngine) -> None:
    status = engine.apply(replace(BASE, downstream_kbps=17000,
                                  upstream_kbps=5000))
    assert status.downstream_alarm == "MAJOR"
    assert status.upstream_alarm == "MINOR"


@pytest.mark.parametrize("change", [
    {"device_up": False, "state": "DOWN"},
    {"state": "TRAINING"},
])
def test_no_sync_marks_metrics_invalid(engine: AlarmEngine,
                                       change: dict[str, object]) -> None:
    status = engine.apply(replace(BASE, **change))
    assert {status.snr_up_alarm, status.snr_down_alarm,
            status.upstream_alarm, status.downstream_alarm} == {"INVALID"}

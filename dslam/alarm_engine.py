# File: dslam/alarm_engine.py
import json
from dataclasses import replace
from pathlib import Path

from dslam.model import DSLAMStatus

DEFAULT_THRESHOLDS = (
    Path(__file__).resolve().parent.parent / "config" / "thresholds.json"
)

# EPICS alarm severities (alarm_t): NO_ALARM=0, MINOR=1, MAJOR=2, INVALID=3
SEVERITY: dict[str, int] = {
    "NO_ALARM": 0,
    "MINOR": 1,
    "MAJOR": 2,
    "INVALID": 3,
}

# DSLAMStatus value field -> DSLAMStatus alarm field
ALARMED_SIGNALS: dict[str, str] = {
    "snr_up": "snr_up_alarm",
    "snr_down": "snr_down_alarm",
    "upstream_kbps": "upstream_alarm",
    "downstream_kbps": "downstream_alarm",
}


def severity_of(alarm: str) -> int:
    """Map an alarm string to an EPICS severity; unknown strings are INVALID."""
    return SEVERITY.get(alarm, SEVERITY["INVALID"])


class AlarmEngine:
    def __init__(self, path: Path | str | None = None) -> None:
        with open(path or DEFAULT_THRESHOLDS, "r", encoding="utf-8") as fp:
            self.thresholds: dict[str, dict[str, float]] = json.load(fp)

    def evaluate(self, signal: str, value: float) -> str:
        """Low-limit alarm: lower values are worse (SNR margin, sync rate)."""
        limits = self.thresholds.get(signal, {})

        for level in ("invalid", "major", "minor"):
            if level in limits and value <= limits[level]:
                return level.upper()

        return "NO_ALARM"

    def apply(self, status: DSLAMStatus) -> DSLAMStatus:
        """Return a copy of status with every alarm field populated."""
        if not status.device_up or status.state != "SHOWTIME":
            # Metrics are stale or meaningless without sync.
            return replace(
                status, **{f: "INVALID" for f in ALARMED_SIGNALS.values()}
            )

        return replace(
            status,
            **{
                alarm_field: self.evaluate(signal, getattr(status, signal))
                for signal, alarm_field in ALARMED_SIGNALS.items()
            },
        )

# File: dslam/model.py
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class DSLAMStatus:
    timestamp: str

    device_up: bool

    state: str
    profile: str

    upstream_kbps: int
    downstream_kbps: int

    snr_up: float
    snr_down: float

    uptime: str = ""

    attenuation_up: float = 0.0
    attenuation_down: float = 0.0

    overall_status: str = "UNKNOWN"

    snr_up_alarm: str = "NO_ALARM"
    snr_down_alarm: str = "NO_ALARM"
    upstream_alarm: str = "NO_ALARM"
    downstream_alarm: str = "NO_ALARM"

    last_event: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

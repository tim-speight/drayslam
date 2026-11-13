from datetime import datetime
from typing import Any

from p4p.nt import NTScalar
from p4p.server import Server
from p4p.server.thread import SharedPV

from dslam.alarm_engine import SEVERITY, severity_of
from dslam.model import DSLAMStatus

PREFIX = "DSLAM:"


def _pv(code: str, initial: Any, units: str | None = None) -> SharedPV:
    nt = NTScalar(code, display=units is not None)
    value: dict[str, Any] = {"value": initial}
    if units is not None:
        value["display"] = {"units": units}
    return SharedPV(nt=nt, initial=value)


PVS: dict[str, SharedPV] = {
    PREFIX + "DEVICE_UP": _pv("?", False),
    PREFIX + "STATE": _pv("s", "UNKNOWN"),
    PREFIX + "STATUS": _pv("s", "UNKNOWN"),
    PREFIX + "PROFILE": _pv("s", "UNKNOWN"),
    PREFIX + "UPSTREAM_KBPS": _pv("i", 0, "kbps"),
    PREFIX + "DOWNSTREAM_KBPS": _pv("i", 0, "kbps"),
    PREFIX + "SNR_UP": _pv("d", 0.0, "dB"),
    PREFIX + "SNR_DOWN": _pv("d", 0.0, "dB"),
    PREFIX + "SNR_UP_ALARM": _pv("s", "NO_ALARM"),
    PREFIX + "SNR_DOWN_ALARM": _pv("s", "NO_ALARM"),
    PREFIX + "ATTENUATION_UP": _pv("d", 0.0, "dB"),
    PREFIX + "ATTENUATION_DOWN": _pv("d", 0.0, "dB"),
    PREFIX + "UPTIME": _pv("s", ""),
    PREFIX + "LAST_EVENT": _pv("s", ""),
    PREFIX + "TIMESTAMP": _pv("s", ""),
}

SERVER: Server | None = None


def start(isolate: bool = False) -> Server:
    global SERVER

    if SERVER is None:
        # providers must be a list; a bare dict would be iterated as names.
        SERVER = Server(providers=[PVS], isolate=isolate)

    return SERVER


def stop() -> None:
    global SERVER

    if SERVER is not None:
        SERVER.stop()
        SERVER = None


def update(status: DSLAMStatus) -> None:
    ts = datetime.fromisoformat(status.timestamp).timestamp()

    # Without a reachable device every reading is stale -> INVALID.
    stale = SEVERITY["NO_ALARM"] if status.device_up else SEVERITY["INVALID"]
    link_sev = (
        SEVERITY["NO_ALARM"]
        if status.overall_status == "ONLINE"
        else SEVERITY["MAJOR"]
    )

    def post(name: str, value: Any, severity: int = 0, message: str = "") -> None:
        PVS[PREFIX + name].post(
            value,
            timestamp=ts,
            severity=max(severity, stale),
            message=message or ("" if status.device_up else "DEVICE_DOWN"),
        )

    def alarmed(name: str, value: Any, alarm: str) -> None:
        sev = severity_of(alarm)
        post(name, value, sev, "" if sev == 0 else alarm)

    post("DEVICE_UP", status.device_up,
         0 if status.device_up else SEVERITY["MAJOR"])
    post("STATE", status.state, link_sev)
    post("STATUS", status.overall_status, link_sev, status.overall_status
         if link_sev else "")
    post("PROFILE", status.profile)

    alarmed("UPSTREAM_KBPS", status.upstream_kbps, status.upstream_alarm)
    alarmed("DOWNSTREAM_KBPS", status.downstream_kbps, status.downstream_alarm)
    alarmed("SNR_UP", status.snr_up, status.snr_up_alarm)
    alarmed("SNR_DOWN", status.snr_down, status.snr_down_alarm)
    alarmed("SNR_UP_ALARM", status.snr_up_alarm, status.snr_up_alarm)
    alarmed("SNR_DOWN_ALARM", status.snr_down_alarm, status.snr_down_alarm)

    post("ATTENUATION_UP", status.attenuation_up)
    post("ATTENUATION_DOWN", status.attenuation_down)
    post("UPTIME", status.uptime)
    post("LAST_EVENT", status.last_event)
    post("TIMESTAMP", status.timestamp)

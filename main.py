#!/usr/bin/env python3
import logging
import os
import signal
import sys
import threading
import time
from collections.abc import Callable
from types import FrameType

import uvicorn
from dotenv import load_dotenv

from api.server import app, update_status
from dslam.alarm_engine import AlarmEngine
from dslam.client import VigorClient
from dslam.model import DSLAMStatus
from epics import pva_server

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

logger = logging.getLogger("drayslam")

Consumer = tuple[str, Callable[[DSLAMStatus], None]]


def next_delay(base: float, failures: int, cap: float) -> float:
    """Exponential backoff: base, 2*base, 4*base ... capped."""
    if failures <= 0:
        return base
    # Clamp exponent so a multi-day outage can't overflow the float.
    return min(base * (2 ** min(failures, 16)), cap)


def start_api(host: str, port: int) -> threading.Thread:
    server = uvicorn.Server(
        uvicorn.Config(app, host=host, port=port, log_level="warning")
    )
    thread = threading.Thread(target=server.run, name="fastapi", daemon=True)
    thread.start()
    return thread


def publish(status: DSLAMStatus, consumers: list[Consumer]) -> None:
    # Each consumer is isolated: an Influx outage must not stop PV updates.
    for name, consume in consumers:
        try:
            consume(status)
        except Exception:
            logger.exception("Publishing to %s failed", name)


def _terminate(signum: int, _frame: FrameType | None) -> None:
    # Turn systemd's SIGTERM into SystemExit so finally-blocks flush Influx.
    sys.exit(128 + signum)


def main() -> None:
    load_dotenv()
    signal.signal(signal.SIGTERM, _terminate)

    interval = float(os.getenv("DSLAM_POLL_INTERVAL", "30"))
    max_backoff = float(os.getenv("DSLAM_MAX_BACKOFF", "300"))

    logger.info("Starting DraySLAM collector (poll=%ss)", interval)

    collector = VigorClient()
    alarms = AlarmEngine()

    pva_server.start()
    start_api(
        os.getenv("DSLAM_API_HOST", "0.0.0.0"),
        int(os.getenv("DSLAM_API_PORT", "8000")),
    )

    consumers: list[Consumer] = [
        ("p4p", pva_server.update),
        ("fastapi", update_status),
    ]

    influx = None
    if os.getenv("INFLUX_URL"):
        from influx.writer import InfluxWriter

        influx = InfluxWriter()
        consumers.append(("influx", influx.write))
    else:
        logger.warning("INFLUX_URL not set; historian disabled")

    failures = 0

    try:
        while True:
            try:
                status = alarms.apply(collector.poll())
            except Exception:
                logger.exception("Poll cycle failed")
                failures += 1
                time.sleep(next_delay(interval, failures, max_backoff))
                continue

            publish(status, consumers)

            logger.info(
                "Status=%s State=%s Down=%sKbps Up=%sKbps "
                "SNR_Up=%s SNR_Down=%s Device=%s Event=%s",
                status.overall_status,
                status.state,
                status.downstream_kbps,
                status.upstream_kbps,
                status.snr_up,
                status.snr_down,
                status.device_up,
                status.last_event,
            )

            healthy = status.device_up and status.overall_status != "AUTH_FAILED"
            failures = 0 if healthy else failures + 1

            time.sleep(next_delay(interval, failures, max_backoff))

    finally:
        if influx is not None:
            influx.close()
        pva_server.stop()


if __name__ == "__main__":
    main()

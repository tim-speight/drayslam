#!/usr/bin/env python3
import socket

from dslam.client import VigorClient
from tests.fake_draytek import FakeDraytek


def test_poll_parses_dsl_table(fake: FakeDraytek, client: VigorClient) -> None:
    fake.line.up_kbps = 9696
    fake.line.down_kbps = 31010
    fake.line.snr = 9.5
    fake.line.loop_att = 14.2

    status = client.poll()

    assert status.device_up is True
    assert status.state == "SHOWTIME"
    assert status.profile == "17A"
    assert status.upstream_kbps == 9696
    assert status.downstream_kbps == 31010
    assert status.snr_up == status.snr_down == 9.5
    assert status.attenuation_down == 14.2
    assert status.uptime == "2:03:04:05"
    assert status.overall_status == "ONLINE"


def test_invalid_values_fall_back_to_defaults(
        fake: FakeDraytek, client: VigorClient) -> None:
    fake.line.state = "TRAINING"
    fake.line.randomise = False
    fake.line.row = lambda: ["35B", "TRAINING", "--", "n/a", "--", "--", ""]

    status = client.poll()

    assert status.upstream_kbps == 0
    assert status.downstream_kbps == 0
    assert status.snr_up == 0.0
    assert status.overall_status == "DSL_TRAINING"


def test_bad_credentials_reported_as_auth_failed(fake: FakeDraytek) -> None:
    client = VigorClient(host=f"http://{fake.address}", user="admin",
                         password="wrong", timeout=2)

    status = client.poll()

    # Modem answered (HTTP 200 + login form): reachable but not authenticated.
    assert status.device_up is True
    assert status.overall_status == "AUTH_FAILED"


def test_session_reused_and_relogin_after_drop(
        fake: FakeDraytek, client: VigorClient) -> None:
    client.poll()
    client.poll()
    assert fake.login_count == 1

    fake.expire_sessions()
    status = client.poll()

    assert fake.login_count == 2
    assert status.overall_status == "ONLINE"


def test_unreachable_modem_reported_as_down() -> None:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]  # closed once released -> refused

    client = VigorClient(host=f"http://127.0.0.1:{port}", user="admin",
                         password="admin", timeout=1)
    status = client.poll()

    assert status.device_up is False
    assert status.state == "DOWN"
    assert status.overall_status == "ONT_SYSDOWN"
    assert status.last_event == "DEVICE_DOWN"


def test_sync_events_fire_on_transitions(
        fake: FakeDraytek, client: VigorClient) -> None:
    assert client.poll().last_event == "DSL_RESYNC"
    assert client.poll().last_event == ""

    fake.line.state = "TRAINING"
    assert client.poll().last_event == "DSL_SYNC_LOST"
    assert client.poll().last_event == ""

    fake.line.state = "SHOWTIME"
    assert client.poll().last_event == "DSL_RESYNC"

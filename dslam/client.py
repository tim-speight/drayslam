#!/usr/bin/env python3
import base64
import logging
import os
import re
import secrets
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from dslam.model import DSLAMStatus

logger = logging.getLogger(__name__)

TOKEN_CHARS = (
    "ABCDEFGHJKMNPQRSTWXYZ"
    "abcdefhijkmnprstwxyz"
    "2345678"
)

DSL_HEADERS = (
    "Mode",
    "State",
    "Up Speed",
    "Down Speed",
    "SNR Margin",
    "Loop Att.",
    "Up Time",
)

_LOGIN_ACTION = re.compile(r"wlogin\.cgi", re.IGNORECASE)


class VigorAuthError(Exception):
    """Modem reachable but rejected the credentials / session."""


class VigorClient:
    def __init__(
        self,
        host: str | None = None,
        user: str | None = None,
        password: str | None = None,
        timeout: float | None = None,
    ) -> None:
        self.host = host or f"http://{os.environ['DSLAM_IP']}"
        self.user = user if user is not None else os.environ["DSLAM_USER"]
        self.password = (
            password if password is not None else os.environ["DSLAM_PASS"]
        )
        self.timeout = (
            timeout
            if timeout is not None
            else float(os.getenv("DSLAM_TIMEOUT", "10"))
        )

        self.device_up = False
        self.last_event = ""
        self.previous_state = "UNKNOWN"

        self.session = requests.Session()
        self._token: str | None = None

    # ------------------------------------------------------------------
    # Acquisition
    # ------------------------------------------------------------------
    def _generate_token(self) -> str:
        return "".join(secrets.choice(TOKEN_CHARS) for _ in range(15))

    @staticmethod
    def _is_login_page(html: str) -> bool:
        """The Vigor answers HTTP 200 with its login form when the
        credentials are wrong or the session has expired."""
        document = BeautifulSoup(html, "html.parser")
        return document.find("form", action=_LOGIN_ACTION) is not None

    def _login(self, token: str) -> requests.Response:
        payload = {
            "aa": base64.b64encode(self.user.encode()).decode(),
            "ab": base64.b64encode(self.password.encode()).decode(),
            "sFormAuthStr": token,
        }

        response = self.session.post(
            f"{self.host}/cgi-bin/wlogin.cgi",
            data=payload,
            allow_redirects=True,
            timeout=self.timeout,
        )

        if response.status_code != 200:
            raise requests.HTTPError(f"Login HTTP {response.status_code}")

        if self._is_login_page(response.text):
            raise VigorAuthError("Login rejected by modem")

        return response

    def _fetch_online_status(self, token: str) -> str:
        response = self.session.get(
            f"{self.host}/cgi-bin/v2x00.cgi",
            params={"fid": 168, "sFormAuthStr": token},
            timeout=self.timeout,
        )

        if response.status_code != 200:
            raise requests.HTTPError(f"Status HTTP {response.status_code}")

        return response.text

    def _acquire_status_page(self) -> str:
        """Reuse the existing session; log in again only if it dropped."""
        if self._token is not None:
            html = self._fetch_online_status(self._token)
            if not self._is_login_page(html):
                return html
            logger.info("Modem session expired; re-authenticating")

        self._token = None
        token = self._generate_token()
        self.session.cookies.clear()
        self._login(token)
        self._token = token

        html = self._fetch_online_status(token)
        if self._is_login_page(html):
            self._token = None
            raise VigorAuthError("Session rejected immediately after login")

        return html

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------
    @staticmethod
    def _parse_dsl_table(html: str) -> dict[str, str]:
        document = BeautifulSoup(html, "html.parser")

        for table in document.find_all("table"):
            strings = list(table.stripped_strings)

            if not all(h in strings for h in DSL_HEADERS[:4]):
                continue

            idx = strings.index("Mode")
            values = strings[
                idx + len(DSL_HEADERS): idx + 2 * len(DSL_HEADERS)
            ]

            if len(values) >= 5:
                return dict(zip(DSL_HEADERS, values))

        return {}

    @staticmethod
    def _to_int(value: str | None) -> int:
        try:
            return int(value) if value is not None else 0
        except ValueError:
            return 0

    @staticmethod
    def _to_float(value: str | None) -> float:
        try:
            return float(value) if value is not None else 0.0
        except ValueError:
            return 0.0

    @staticmethod
    def _determine_overall_status(device_up: bool, link_status: str) -> str:
        link_status = str(link_status).upper()

        if not device_up:
            return "ONT_SYSDOWN"

        if link_status == "SHOWTIME":
            return "ONLINE"

        if link_status == "TRAINING":
            return "DSL_TRAINING"

        if link_status == "DOWN":
            return "WAN_DOWN"

        return "UNKNOWN"

    def _track_event(self, link_status: str) -> str:
        if self.previous_state == "SHOWTIME" and link_status != "SHOWTIME":
            event = "DSL_SYNC_LOST"
        elif self.previous_state != "SHOWTIME" and link_status == "SHOWTIME":
            event = "DSL_RESYNC"
        else:
            event = ""

        self.previous_state = link_status
        self.last_event = event
        return event

    # ------------------------------------------------------------------
    # Public
    # ------------------------------------------------------------------
    def poll(self) -> DSLAMStatus:
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            html = self._acquire_status_page()

        except VigorAuthError as ex:
            logger.error("DrayTek authentication failed: %s", ex)
            self.device_up = True
            event = self._track_event("UNKNOWN")
            return DSLAMStatus(
                timestamp=timestamp,
                device_up=True,
                state="UNKNOWN",
                profile="N/A",
                upstream_kbps=0,
                downstream_kbps=0,
                snr_up=0.0,
                snr_down=0.0,
                overall_status="AUTH_FAILED",
                last_event=event or "AUTH_FAILED",
            )

        except requests.RequestException as ex:
            logger.error("DrayTek unavailable: %s", ex)
            self._token = None
            self.device_up = False
            self._track_event("DOWN")
            self.last_event = "DEVICE_DOWN"
            return DSLAMStatus(
                timestamp=timestamp,
                device_up=False,
                state="DOWN",
                profile="N/A",
                upstream_kbps=0,
                downstream_kbps=0,
                snr_up=0.0,
                snr_down=0.0,
                overall_status="ONT_SYSDOWN",
                last_event="DEVICE_DOWN",
            )

        self.device_up = True
        dsl = self._parse_dsl_table(html)
        if dsl:
            logger.debug("DSL Parsed: %s", dsl)
        else:
            logger.warning("DSL status table not found in fid=168 page")

        link_status = dsl.get("State", "UNKNOWN")

        # Firmware may expose a single SNR margin for both directions.
        snr_margin = self._to_float(dsl.get("SNR Margin"))
        loop_att = self._to_float(dsl.get("Loop Att."))

        return DSLAMStatus(
            timestamp=timestamp,
            device_up=True,
            state=link_status,
            profile=dsl.get("Mode", "UNKNOWN"),
            upstream_kbps=self._to_int(dsl.get("Up Speed")),
            downstream_kbps=self._to_int(dsl.get("Down Speed")),
            snr_up=snr_margin,
            snr_down=snr_margin,
            attenuation_up=loop_att,
            attenuation_down=loop_att,
            uptime=dsl.get("Up Time", ""),
            overall_status=self._determine_overall_status(True, link_status),
            last_event=self._track_event(link_status),
        )


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()
    logging.basicConfig(level=logging.DEBUG)
    print(VigorClient().poll())

#!/usr/bin/env python3
"""FakeDraytek: a minimal stand-in for the Vigor 166 CGI interface.

    POST /cgi-bin/wlogin.cgi   aa/ab = base64 user/pass, sFormAuthStr = token
    GET  /cgi-bin/v2x00.cgi    fid=168 & sFormAuthStr = token (+ session cookie)

Bad credentials or an unknown session return HTTP 200 with the login form,
as the real modem does.  Run standalone for local debugging:

    python -m tests.fake_draytek --port 8080
    DSLAM_IP=127.0.0.1:8080 DSLAM_USER=admin DSLAM_PASS=admin python main.py

NOTE: the fid=168 table layout mirrors what dslam/client.py parses; replace
it with an obfuscated capture of the real page when one is available.
"""
import argparse
import base64
import random
import secrets
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

LOGIN_PAGE = """<html><body>
<form name="login" method="post" action="/cgi-bin/wlogin.cgi">
<input type="text" name="aa"><input type="password" name="ab">
<input type="hidden" name="sFormAuthStr" value="">
</form></body></html>"""

MAIN_FRAME = "<html><frameset><frame name=main></frameset></html>"

HEADERS = ("Mode", "State", "Up Speed", "Down Speed",
           "SNR Margin", "Loop Att.", "Up Time")


@dataclass
class LineState:
    mode: str = "17A"
    state: str = "SHOWTIME"
    up_kbps: int | None = None
    down_kbps: int | None = None
    snr: float | None = None
    loop_att: float | None = None
    uptime: str = "2:03:04:05"
    randomise: bool = True

    def row(self) -> list[str]:
        r = random.Random() if self.randomise else random.Random(0)
        return [
            self.mode,
            self.state,
            str(self.up_kbps if self.up_kbps is not None
                else r.randint(6000, 10000)),
            str(self.down_kbps if self.down_kbps is not None
                else r.randint(25000, 40000)),
            str(self.snr if self.snr is not None
                else round(r.uniform(6.0, 12.0), 1)),
            str(self.loop_att if self.loop_att is not None
                else round(r.uniform(10.0, 25.0), 1)),
            self.uptime,
        ]


@dataclass
class FakeDraytek:
    user: str = "admin"
    password: str = "admin"
    host: str = "127.0.0.1"
    port: int = 0
    line: LineState = field(default_factory=LineState)
    sessions: dict[str, str] = field(default_factory=dict)  # cookie -> token
    login_count: int = 0

    def __post_init__(self) -> None:
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *_args: object) -> None:
                pass

            def _send(self, body: str, cookie: str | None = None) -> None:
                data = body.encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.send_header("Content-Length", str(len(data)))
                if cookie:
                    self.send_header(
                        "Set-Cookie", f"SESSION_ID_VIGOR={cookie}; Path=/")
                self.end_headers()
                self.wfile.write(data)

            def _cookie(self) -> str | None:
                for part in self.headers.get("Cookie", "").split(";"):
                    k, _, v = part.strip().partition("=")
                    if k == "SESSION_ID_VIGOR":
                        return v
                return None

            def do_POST(self) -> None:
                if urlparse(self.path).path != "/cgi-bin/wlogin.cgi":
                    self.send_error(404)
                    return
                length = int(self.headers.get("Content-Length", 0))
                form = parse_qs(self.rfile.read(length).decode())

                def b64(k: str) -> str:
                    try:
                        return base64.b64decode(form.get(k, [""])[0]).decode()
                    except ValueError:
                        return ""

                token = form.get("sFormAuthStr", [""])[0]
                fake.login_count += 1
                if (b64("aa"), b64("ab")) != (fake.user, fake.password) \
                        or not token:
                    self._send(LOGIN_PAGE)
                    return
                cookie = secrets.token_hex(8)
                fake.sessions[cookie] = token
                self._send(MAIN_FRAME, cookie)

            def do_GET(self) -> None:
                url = urlparse(self.path)
                if url.path != "/cgi-bin/v2x00.cgi":
                    self.send_error(404)
                    return
                query = parse_qs(url.query)
                token = query.get("sFormAuthStr", [""])[0]
                cookie = self._cookie()
                if cookie is None or fake.sessions.get(cookie) != token:
                    self._send(LOGIN_PAGE)
                    return
                if query.get("fid") != ["168"]:
                    self._send("<html><body>unsupported fid</body></html>")
                    return
                self._send(fake.status_page())

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self.port = self._server.server_address[1]
        self._thread = threading.Thread(
            target=self._server.serve_forever, daemon=True)

    @property
    def address(self) -> str:
        return f"{self.host}:{self.port}"

    def status_page(self) -> str:
        head = "".join(f"<th>{h}</th>" for h in HEADERS)
        cells = "".join(f"<td>{v}</td>" for v in self.line.row())
        return (
            "<html><body><table><tr><td>Physical Connection</td></tr></table>"
            f"<table><tr>{head}</tr><tr>{cells}</tr></table></body></html>"
        )

    def expire_sessions(self) -> None:
        self.sessions.clear()

    def start(self) -> "FakeDraytek":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--user", default="admin")
    parser.add_argument("--password", default="admin")
    args = parser.parse_args()

    fake = FakeDraytek(user=args.user, password=args.password,
                       host=args.host, port=args.port).start()
    print(f"FakeDraytek listening on http://{fake.address}  (Ctrl+C to stop)")
    try:
        fake._thread.join()
    except KeyboardInterrupt:
        fake.stop()


if __name__ == "__main__":
    main()

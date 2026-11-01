"""A loopback-only mock NTRIP caster.

Implements the NTRIP 2.0 conversation:
  - client GET /<mountpoint> with Basic auth
  - 401/403/404 error paths
  - SOURCETABLE response to GET /
  - GGA position upload from the client (VRS flow)
  - a synthetic RTCM 1005 correction stream as mountpoint data

Run:  python3 -m exercises.ntrip.caster   (binds 127.0.0.1 only)
"""

import base64
import socket
import socketserver
import threading
import time

from exercises.rtcm.generator import encode_1005

HOST = "127.0.0.1"
PORT = 2101

SOURCETABLE = [
    # name, identifier, format, format-details, carrier, nav, country, lat, lon, needs_gga
    ("HELSON", "Helsinki south", "RTCM 3.2", "1005(1),1074(1),1084(1)", "2",
     "GPS+GLO+GAL", "FIN", 60.1699, 24.9384, 1),
    ("TMPNOR", "Tampere north", "RTCM 3.2", "1005(1),1074(1),1084(1)", "2",
     "GPS+GLO+GAL", "FIN", 61.4981, 23.7610, 1),
]


class NtripError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def parse_gga(line: str):
    """Parse a $GPGGA sentence into a dict, or None if malformed."""
    fields = line.strip().split(",")
    if len(fields) < 6 or not fields[0].endswith("GGA"):
        return None
    try:
        lat = float(fields[2])
        lon = float(fields[4])
    except ValueError:
        return None
    lat = (lat // 100) + (lat % 100) / 60
    lon = (lon // 100) + (lon % 100) / 60
    if fields[3] == "S":
        lat = -lat
    if fields[5] == "W":
        lon = -lon
    return {"lat": lat, "lon": lon, "quality": fields[6]}


def parse_request(data: bytes):
    """Parse the client's HTTP-ish request head into (method, path, headers)."""
    head = data.split(b"\r\n\r\n", 1)[0].decode("utf-8", "replace")
    lines = head.split("\r\n")
    parts = lines[0].split(" ")
    if len(parts) < 2:
        raise NtripError(400, "Bad Request")
    method, path = parts[0], parts[1]
    headers = {}
    for line in lines[1:]:
        if ":" in line:
            key, value = line.split(":", 1)
            headers[key.strip().lower()] = value.strip()
    return method, path, headers


def check_auth(headers: dict, username: str, password: str):
    auth = headers.get("authorization", "")
    if not auth.startswith("Basic "):
        raise NtripError(401, "Unauthorized")
    try:
        user, _, pw = base64.b64decode(auth[6:]).decode("utf-8").partition(":")
    except Exception:
        raise NtripError(401, "Unauthorized")
    if user != username or pw != password:
        raise NtripError(401, "Unauthorized")


def sourcetable_text() -> str:
    lines = ["SOURCETABLE 200 OK"]
    for (name, ident, fmt, details, carrier, nav, country,
         lat, lon, needs_gga) in SOURCETABLE:
        lines.append(
            f"STR;{name};{ident};{fmt};{details};{carrier};{nav};0;"
            f"{country};{lat:.4f};{lon:.4f};1;{'B' if needs_gga else 'N'};none;"
            f"{'N' if needs_gga else 'N'};0;Bitstream")
    lines.append("ENDSOURCETABLE")
    return "\r\n".join(lines) + "\r\n"


def mountpoint_exists(path: str) -> bool:
    name = path.lstrip("/")
    return any(row[0] == name for row in SOURCETABLE)


class NtripCasterHandler(socketserver.BaseRequestHandler):
    username = "user"
    password = "pass"
    gga_seen = []

    def _send(self, text: str):
        self.request.sendall(text.encode("utf-8"))

    def handle(self):
        try:
            data = self._read_head()
            method, path, headers = parse_request(data)
            check_auth(headers, self.username, self.password)

            if path == "/" or path == "":
                self._send(sourcetable_text())
                return
            if method != "GET" or not mountpoint_exists(path):
                raise NtripError(404, "Not Found")

            self._send(
                "HTTP/1.1 200 OK\r\n"
                "Ntrip-Version: Ntrip/2.0\r\n"
                "Content-Type: gnss/data\r\n"
                "\r\n"
            )
            self._stream_corrections(data)
        except NtripError as err:
            self._send(
                f"HTTP/1.1 {err.status} {err.message}\r\n"
                "Ntrip-Version: Ntrip/2.0\r\n\r\n"
            )
        except ConnectionError:
            pass
        finally:
            try:
                self.request.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass

    def _read_head(self) -> bytes:
        buf = b""
        while b"\r\n\r\n" not in buf and len(buf) < 4096:
            chunk = self.request.recv(4096)
            if not chunk:
                break
            buf += chunk
        return buf

    def _stream_corrections(self, initial: bytes):
        """Stream synthetic RTCM frames, reading GGA lines the client sends.

        A real VRS-style caster uses the GGA position to tailor corrections;
        here we just record it and keep streaming.
        """
        self.request.settimeout(0.5)
        frame = encode_1005(1234, 2818063.0, 943760.0, 5532545.0)
        end = time.time() + 30
        while time.time() < end:
            self.request.sendall(frame)
            try:
                line = self.request.recv(4096)
                if not line:
                    return
                text = line.decode("ascii", "replace").strip()
                if text.startswith("$"):
                    gga = parse_gga(text)
                    if gga:
                        NtripCasterHandler.gga_seen.append(gga)
            except socket.timeout:
                continue
            except ConnectionError:
                return
            time.sleep(0.2)


class NtripCaster(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def serve(host=HOST, port=PORT, on_ready=None, stop_event=None):
    server = NtripCaster((host, port), NtripCasterHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    if on_ready:
        on_ready(server)
    try:
        if stop_event is not None:
            stop_event.wait()
        else:
            thread.join()
    finally:
        server.shutdown()
        server.server_close()
    return server


if __name__ == "__main__":
    print(f"mock NTRIP caster listening on {HOST}:{PORT} "
          f"(user/pass, mountpoints: HELSON, TMPNOR)")
    print("fetch the sourcetable: curl -s --user user:pass http://127.0.0.1:2101/")
    serve()

"""Minimal NTRIP client: request a mountpoint, print RTCM frames, send GGA."""

import base64
import socket
import sys

from exercises.rtcm.framing import scan_frames

HOST = "127.0.0.1"
PORT = 2101


def connect(host=HOST, port=PORT, mountpoint="HELSON",
            username="user", password="pass", gga=None, max_frames=5):
    """Connect to a caster, read `max_frames` RTCM frames, return them.

    `gga` is an optional NMEA GGA sentence sent upstream (the VRS flow).
    """
    request = (
        f"GET /{mountpoint} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Ntrip-Version: Ntrip/2.0\r\n"
        "User-Agent: NTRIP learningclient/1.0\r\n"
        "Authorization: Basic "
        + base64.b64encode(f"{username}:{password}".encode()).decode()
        + "\r\n\r\n"
    )
    frames = []
    with socket.create_connection((host, port), timeout=5) as sock:
        sock.sendall(request.encode("utf-8"))
        if gga:
            sock.sendall((gga + "\r\n").encode("utf-8"))
        sock.settimeout(5)
        buf = b""
        while len(frames) < max_frames:
            try:
                chunk = sock.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            buf += chunk
            new_frames = list(scan_frames(buf))
            if new_frames:
                frames.extend(new_frames)
                consumed = 0
                for _msg_type, payload in new_frames:
                    consumed += 3 + len(payload) + 3
                buf = buf[consumed:]
        return frames


def main():
    mountpoint = sys.argv[1] if len(sys.argv) > 1 else "HELSON"
    gga = ("$GPGGA,123519,6008.607,N,02457.551,E,1,08,0.9,45.4,M,46.9,M,,*55")
    print(f"connecting to {HOST}:{PORT} mountpoint {mountpoint}")
    frames = connect(mountpoint=mountpoint, gga=gga, max_frames=3)
    for msg_type, _payload in frames:
        print(f"received RTCM message type {msg_type}")
    if not frames:
        print("no frames received")
        sys.exit(1)


if __name__ == "__main__":
    main()

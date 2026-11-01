"""RTCM 3.x frame layer: 0xD3 framing with 24-bit CRC-Q."""

from .crc import crc24q

PREAMBLE = 0xD3


class FrameError(ValueError):
    pass


def encode_frame(payload: bytes) -> bytes:
    if len(payload) > 1023:
        raise FrameError("payload too long for RTCM3 frame")
    header = bytes([PREAMBLE, (len(payload) >> 8) & 0x03, len(payload) & 0xFF])
    return header + payload + crc24q(header + payload).to_bytes(3, "big")


def decode_frame(buf: bytes):
    """Decode one frame from the head of `buf`.

    Returns (message_type, payload_bytes, total_frame_length).
    Raises FrameError on invalid framing/CRC.
    """
    if len(buf) < 6:
        raise FrameError("buffer too short")
    if buf[0] != PREAMBLE:
        raise FrameError("bad preamble")
    if buf[1] & 0xFC:
        raise FrameError("reserved bits not zero")
    length = ((buf[1] & 0x03) << 8) | buf[2]
    total = 3 + length + 3
    if len(buf) < total:
        raise FrameError("incomplete frame")
    frame = buf[:total]
    expected = int.from_bytes(frame[-3:], "big")
    if crc24q(frame[:-3]) != expected:
        raise FrameError("CRC mismatch")
    if length < 2:
        raise FrameError("payload too short for type+station id")
    msg_type = (frame[3] << 4) | (frame[4] >> 4)
    return msg_type, frame[3:3 + length], total


def scan_frames(stream: bytes):
    """Split a raw byte stream into frames, resynchronizing on bad data.

    Yields (message_type, payload_bytes). Bytes before the first valid
    frame are skipped, mirroring how a real receiver acquires sync.
    """
    i = 0
    while i < len(stream):
        if stream[i] != PREAMBLE:
            i += 1
            continue
        try:
            msg_type, payload, total = decode_frame(stream[i:])
            yield msg_type, payload
            i += total
        except FrameError:
            i += 1

import pytest

from exercises.rtcm.crc import crc24q
from exercises.rtcm.framing import FrameError, decode_frame, encode_frame, scan_frames
from exercises.rtcm.generator import encode_1005
from exercises.rtcm.rtcm import BitReader, decode_1005


def test_crc24q_reference():
    # CRC24Q of ASCII "123456789", computed with the same bit algorithm
    assert crc24q(b"123456789") == 0xCDE703


def test_frame_roundtrip():
    payload = bytes([0x00, 0x8D, 0xEA, 0xDB, 0xEE, 0xF0])  # type 8 (type bits span payload[0:1])
    frame = encode_frame(payload)
    msg_type, decoded, total = decode_frame(frame)
    assert msg_type == 8  # type bits are top 12 of payload
    assert decoded == payload
    assert total == len(frame)


def test_bad_preamble_rejected():
    payload = bytes([0x00, 0x80, 0x00])
    frame = bytearray(encode_frame(payload))
    frame[0] = 0xD2
    with pytest.raises(FrameError):
        decode_frame(bytes(frame))


def test_corrupted_crc_rejected():
    payload = bytes([0x00, 0x80, 0x00, 0x01])
    frame = bytearray(encode_frame(payload))
    frame[4] ^= 0xFF
    with pytest.raises(FrameError):
        decode_frame(bytes(frame))


def test_scan_resynchronizes():
    payload = bytes([0x00, 0x81, 0x12, 0x20])
    frame = encode_frame(payload)
    noisy = b"\x01\x02\x03" + frame + b"garbage" + frame
    found = list(scan_frames(noisy))
    assert len(found) == 2
    assert all(msg_type == 8 for msg_type, _ in found)


def test_1005_roundtrip():
    frame = encode_1005(1234, 2818063.1234, 943760.5678, 5532545.9101)
    msg_type, payload, _ = decode_frame(frame)
    assert msg_type == 1005
    st = decode_1005(payload)
    assert st.station_id == 1234
    assert st.x == pytest.approx(2818063.1234, abs=1e-3)
    assert st.y == pytest.approx(943760.5678, abs=1e-3)
    assert st.z == pytest.approx(5532545.9101, abs=1e-3)


def test_bit_reader_signed():
    data = bytes([0xFF, 0xFF, 0xFF])
    r = BitReader(data)
    assert r.read_signed(24) == -1

"""CRC-24Q as used by RTCM 3.x frames (polynomial 0x1864CFB)."""

_POLY = 0x1864CFB


def crc24q(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc ^= byte << 16
        for _ in range(8):
            crc <<= 1
            if crc & 0x1000000:
                crc ^= _POLY
    return crc & 0xFFFFFF

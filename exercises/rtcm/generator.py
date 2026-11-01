"""Synthetic RTCM 1005 frame generation (used by the mock NTRIP caster)."""

from .framing import encode_frame


def encode_1005(station_id: int, x: float, y: float, z: float,
                itrf_year: int = 2020, arp_flag: bool = True) -> bytes:
    """Build a type-1005 payload and wrap it in an RTCM3 frame."""
    bits = ""

    def field(value: int, nbits: int):
        nonlocal bits
        bits += format(value & ((1 << nbits) - 1), f"0{nbits}b")

    def signed(value: float, scale: float, nbits: int):
        v = int(round(value / scale))
        if not -(1 << (nbits - 1)) <= v < (1 << (nbits - 1)):
            raise ValueError("value out of range")
        field(v, nbits)

    field(1005, 12)
    field(station_id, 12)
    field(itrf_year, 6)
    field(1 if arp_flag else 0, 1)
    field(0, 1)
    signed(x, 0.0001, 38)
    signed(y, 0.0001, 38)
    signed(z, 0.0001, 38)
    field(0, 6)  # pad to byte boundary (152-bit 1005 payload)

    payload = int(bits, 2).to_bytes(len(bits) // 8, "big")
    return encode_frame(payload)

"""Bit-level decoding helpers and an RTCM 1005 station-coordinate decoder."""


class BitReader:
    """MSB-first bit cursor over a bytes payload, as RTCM expects."""

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0  # bit position

    def read(self, nbits: int) -> int:
        value = 0
        for _ in range(nbits):
            byte_index = self.pos >> 3
            if byte_index >= len(self.data):
                raise ValueError("bit reader out of range")
            bit = (self.data[byte_index] >> (7 - (self.pos & 7))) & 1
            value = (value << 1) | bit
            self.pos += 1
        return value

    def read_signed(self, nbits: int) -> int:
        value = self.read(nbits)
        if value & (1 << (nbits - 1)):
            value -= 1 << nbits
        return value


class StationCoordinate:
    def __init__(self, station_id, x, y, z, itrf_year, arp_flag):
        self.station_id = station_id
        self.x = x
        self.y = y
        self.z = z
        self.itrf_year = itrf_year
        self.arp_flag = arp_flag

    def __repr__(self):
        return (
            f"StationCoordinate(id={self.station_id}, "
            f"X={self.x:.4f}, Y={self.y:.4f}, Z={self.z:.4f}, "
            f"ITRF{self.itrf_year}, arp={self.arp_flag})"
        )


def decode_1005(payload: bytes) -> StationCoordinate:
    """Decode RTCM3 message type 1005 (reference station coordinates)."""
    r = BitReader(payload)
    msg_type = r.read(12)
    if msg_type != 1005:
        raise ValueError(f"not a 1005 message: {msg_type}")
    station_id = r.read(12)
    itrf_year = r.read(6)
    arp_flag = r.read(1)
    r.read(1)  # reserved
    # 0.0001 m resolution, 38-bit signed integers
    x = r.read_signed(38) * 0.0001
    y = r.read_signed(38) * 0.0001
    z = r.read_signed(38) * 0.0001
    r.read(6)  # reserved padding to byte alignment
    return StationCoordinate(station_id, x, y, z, itrf_year, arp_flag)

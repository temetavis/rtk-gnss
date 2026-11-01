# RTCM Messages and Stream Framing

RTCM SC-104 defines the binary message format used for GNSS corrections.
Version 3.x is universal today (RTCM 3.2 / 3.3).

## Why "binary framing" matters

An RTCM stream is a serial byte stream with **no guaranteed packet
boundaries** from the transport. A parser must:

1. hunt for the **preamble byte** 0xD3,
2. verify the 6 reserved bits after it are zero,
3. read the 10-bit message length and check the 24-bit **CRC24Q** over
   header + payload,
4. dispatch by **message type** (12 bits in payload),
5. resume hunting if anything fails (resynchronization).

Only after CRC passes is a frame accepted — this makes the protocol
self-synchronizing and robust to mid-stream corruption.

## Frame layout (RTCM 3.x)

```
+--------+--------+--------+========...========+==========...==========+
| 0xD3   | 0000 + length(10b)  | payload (0..1023 bytes) | CRC24Q (3B) |
+--------+--------+--------+========...========+==========...==========+
                                          payload starts with:
                                          type(12b) | station id(12b)
```

## Messages you meet daily in network RTK

| Type | Name | Purpose |
|---|---|---|
| 1005 / 1006 | Station coordinates (with/without antenna height) | tells the rover where the (virtual) reference station is |
| 1071–1087 etc. | MSM4/5/6/7 satellite observations | the actual reference observations per constellation |
| 1019 / 1042 | GPS / BeiDou ephemeris | so rovers can work with decoded broadcast ephemeris |
| 1030–1037 | Network RTK residuals & ionosphere | network correction modeling (MAC/FKP era types) |
| 4076 | proprietary/vendor extensions | vendor-specific service info |
| 1230 | GLONASS biases | needed for GLONASS ambiguity resolution |

## Example: 1005 station coordinates

Payload (after type + station id) is a series of 24-bit bitfields:

```
ITRF realisation year (6b) | antenna ref point flag (1b) | reserved (1b) |
station ECEF X (38b, signed, 0.0001 m units) | Y (38b) | Z (38b)
```

The 1005 exercise decoder (`exercises/rtcm/rtcm.py:decode_1005`) shows the
bit-level gymnastics: signed 38-bit big-endian two's-complement fields packed
into a byte array. This is typical of RTCM — fixed-width bitfields, no
alignment.

## CRC24Q

Polynomial: `0x1864CFB`, initial value 0, no reflection, no final XOR
(the "Qualcomm CRC24"). Every frame carries it; decoding without checking
CRC is asking for garbage.

## Bit numbering

RTCM counts bits MSB-first from the start of the payload. Most decoders use a
small helper class that reads k bits from an offset and increments a cursor —
see `exercises/rtcm/rtcm.py:BitReader`.

## Exercise pointers

`exercises/rtcm/` contains:

- `crc.py` — CRC24Q implementation
- `framing.py` — encoder/decoder for the 0xD3 frame layer
- `rtcm.py` — BitReader and a full 1005 decoder
- `generator.py` — builds synthetic 1005 frames (used by the NTRIP caster)

`tests/test_rtcm.py` verifies round-trips and CRC rejection.

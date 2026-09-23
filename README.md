# Xiaomi-Scale-Unlocked-Reverse-Engineering

_Russian version: [README.ru.md](README.ru.md)_

The Mi weight scale broadcasts every measurement in plain BLE advertisement packets. Here is that layout, byte by byte, and an offline decoder for it.

![License](https://img.shields.io/github/license/ipanalytics/Xiaomi-Scale-Unlocked-Reverse-Engineering.svg)
![Status](https://img.shields.io/badge/status-stable-green.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)

## Overview

I wanted weight history in a database I control, not behind a vendor login. The scale gives the measurement away: it sits in the advertisement the device broadcasts several times per second, so a passive scan is enough. No connection, no pairing, nothing written to the device. Xiaomi does not document the payload, so the layout below comes from my own capture of these frames.

Two generations of the same family are covered here:

- `0x181D`, 10 bytes — Mi Smart Scale
- `0x181B`, 13 bytes — Mi Body Composition Scale (advertises as `MIBFS`)

## Frame layout

Version 2, 13 bytes (`0x181B`):

| Bytes | Field | Encoding |
| --- | --- | --- |
| 0 | header | `0x02` |
| 1 | flags | `0x02` impedance present, `0x20` stabilized, `0x80` load removed |
| 2-3 | year | little-endian 16-bit |
| 4-8 | month, day, hour, minute, second | one byte each |
| 9-10 | impedance | little-endian 16-bit, `0xFFFD` when absent |
| 11-12 | weight | little-endian 16-bit, divide by 200 for kilograms (raw unit 5 g) |

Version 1, 10 bytes (`0x181D`): control byte (`0x22` measuring, `0xA2` stabilized), weight in bytes 1-2 with the same scale factor, then year, month, day, hour, minute, second.

Full field notes, flag behaviour and worked examples: [docs/protocol.md](docs/protocol.md).

## Quick start

```bash
python3 -m unittest discover -s tests
python3 tools/xiaomi_scale_decode.py -f examples/frames.txt
python3 tools/xiaomi_scale_decode.py 0224b2070104030637fdff983a
python3 tools/body_composition.py --weight 65 --height 172 --age 35 --sex female --impedance 560
```

Hex frames are accepted with spaces, colons or dashes; lines starting with `#` are skipped, so a capture file can carry comments. Each readable frame becomes one JSON object:

```json
{"version": 2, "weight_kg": 75.0, "impedance": null, "stabilized": true, "load_removed": false, "timestamp": "1970-01-04T03:06:55"}
```

## Structure

```
Xiaomi-Scale-Unlocked-Reverse-Engineering/
├── docs/
│   ├── protocol.md (+ .ru.md)                    frame layout and flag behaviour
│   ├── body-composition.md (+ .ru.md)            impedance to fat, water, muscle, BMR
│   ├── pitfalls.md (+ .ru.md)                    what bites you when collecting
│   └── reverse-engineering-method.md (+ .ru.md)  how the layout was recovered
├── tools/xiaomi_scale_decode.py                  decoder and CLI
├── tools/body_composition.py                     vendor-style body composition maths
├── tests/                                        offline unit tests, no Bluetooth
├── examples/frames.txt                           sample capture lines
└── README.md (+ .ru.md)
```

## Collecting

The decoder is offline: it turns hex frames into records. Capture frames with any scanner that can print service data, keep only the frames whose stabilized flag is set, drop the load-removed record, and store the rest under a unique key so repeated broadcasts collapse into one row. Adapter choices, scanning windows and the traps I hit: [docs/pitfalls.md](docs/pitfalls.md).

## Scope and limitations

- The layout is specific to this device family; a Xiaomi layout says nothing about another brand's scale.
- Advertisement decoding gives the measurement only. I do not touch what the vendor app does on top of it: history sync, body-composition algorithms, firmware updates.
- The frame carries raw impedance. The fat, water, muscle, bone, protein, visceral fat, BMR and metabolic age numbers are arithmetic on top of weight, impedance, height, age and sex: [docs/body-composition.md](docs/body-composition.md) has the formulas and the caveats.
- The clock field is useless on a scale whose time was never set by a vendor app: the year reads 1970. Weight and flags are unaffected.

## License

MIT

# Xiaomi scale advertisement protocol

_Russian version: [protocol.ru.md](protocol.ru.md)_

What the scale puts into its advertisement, field by field, with worked examples.

## Transport

The measurement travels in service data inside the advertisement. Two UUIDs are in use across the family:

- `0000181d-0000-1000-8000-00805f9b34fb` — 10-byte payload (Mi Smart Scale)
- `0000181b-0000-1000-8000-00805f9b34fb` — 13-byte payload (Mi Body Composition Scale)

The device name in the advertisement depends on the model; the `MIBFS` name is typical for the body-composition generation. Nothing in the payload is encrypted, and no connection is required.

## Version 2 — 13 bytes (`0x181B`)

| Offset | Size | Field | Notes |
| --- | --- | --- | --- |
| 0 | 1 | header | always `0x02` |
| 1 | 1 | flags | see below |
| 2-3 | 2 | year | little-endian; reads 1970 when the clock was never set |
| 4 | 1 | month | 1-12 |
| 5 | 1 | day | 1-31 |
| 6 | 1 | hour | 0-23 |
| 7 | 1 | minute | 0-59 |
| 8 | 1 | second | 0-59 |
| 9-10 | 2 | impedance | little-endian, in ohms; `0xFFFD` when no impedance measurement was taken |
| 11-12 | 2 | weight | little-endian; divide by 200 for kilograms |

Flag byte, bit by bit:

| Bit | Mask | Meaning |
| --- | --- | --- |
| 1 | `0x02` | 1 = impedance present in bytes 9-10 |
| 5 | `0x20` | 1 = weight has stabilized |
| 7 | `0x80` | 1 = load removed (nobody on the scale) |

Bits 0, 2, 3, 4 and 6 are unused on this family.

## Version 1 — 10 bytes (`0x181D`)

| Offset | Size | Field | Notes |
| --- | --- | --- | --- |
| 0 | 1 | control | `0x22` measuring, `0xA2` stabilized |
| 1-2 | 2 | weight | little-endian, divide by 200 |
| 3-4 | 2 | year | little-endian |
| 5 | 1 | month | |
| 6 | 1 | day | |
| 7 | 1 | hour | |
| 8 | 1 | minute | |
| 9 | 1 | second | |

Version 1 carries no impedance field.

## Worked examples

Stabilized weighing, 75.0 kg:

```
frame: 02 24 b2 07 01 04 03 06 37 fd ff 98 3a
       │  │  └──┬──┘ └─────┬─────┘ └──┬──┘ └──┬──┘
       │  │     │          │          │       └ 98 3a → 0x3a98 = 15000 → /200 = 75.0 kg
       │  │     │          │          └───────── no impedance measured (0xfffd)
       │  │     │          └──────────────────── 1970-01-04 03:06:55 (clock never set)
       │  │     └─────────────────────────────── year, little-endian
       │  └───────────────────────────────────── flags: stabilized, no impedance, load present
       └──────────────────────────────────────── header
```

Same scale right after stepping off:

```
frame: 02 84 b2 07 01 04 03 07 26 00 00 14 00
weight: 14 00 → 0x0014 = 20 → /200 = 0.1 kg, flags report load removed
```

Version 1 frame, 75.75 kg:

```
frame: 22 2e 3b b2 07 01 01 00 36 15
weight: 2e 3b → 0x3b2e = 15150 → /200 = 75.75 kg
```

## Field notes

- **Weight resolution** is 5 grams per raw unit, so kg = raw / 200. The scale settles in 50 g steps.
- **Stabilized vs intermediate.** While the person is settling, the device emits frames with the stabilized bit clear and a drifting weight. Store only the stabilized ones.
- **Load removed** frames keep the last weight briefly, then drop to the empty-scale value, which is a tenth of a kilogram on my unit. Treat that as "nobody is on the scale", not as a reading.
- **Impedance** only appears when the weighing was taken with impedance enabled — bare feet, and a session the device considers a body-composition measurement. When it is missing, the bit stays clear and bytes 9-10 carry `0xFFFD`.
- **The clock** is only as good as the last vendor-app sync. A scale that was never paired reports year 1970; the decoder still returns the rest of the fields.
- **No GATT path.** The family also exposes a vendor service that requires an authentication token, and the weight characteristic does not report without it. Everything needed is in the advertisement, and no key is involved.

## See also

- [reverse-engineering-method.md](reverse-engineering-method.md) — how this layout was recovered, and how to repeat it on another device.
- [pitfalls.md](pitfalls.md) — collector-side traps.

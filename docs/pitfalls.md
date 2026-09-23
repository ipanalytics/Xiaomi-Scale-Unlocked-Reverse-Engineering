# Collector-side pitfalls

_Russian version: [pitfalls.ru.md](pitfalls.ru.md)_

Traps I hit while getting these frames into a database. Some of them cost an evening.

## The dongle is the biggest trap

Not every USB Bluetooth dongle can do the LE central role that scanning requires. Cheap dongles built on CSR silicon (USB ID `0a12:0001`) are common and often support only classic BR/EDR. The failure is quiet:

```
$ btmgmt info
    supported settings: powered connectable discoverable bondable link-security br/edr ...
```

No `le` in that list means the radio will never see an advertisement. A scanner fails with `No Bluetooth adapters with BLE 'central' role found`, and no amount of driver reloading helps. Check `btmgmt info` (or the chipset datasheet) before buying: a dongle that lists `le` in supported settings is the one you want. One of my two dongles was a CSR part with classic Bluetooth only, and it was useless for this.

## Do not pair

Pairing is not needed and gets in the way: once bonded, some devices stop advertising to anyone else, and the vendor app and your collector start fighting over the connection. Read the advertisement, touch nothing.

## Share the radio carefully

One adapter, several devices. A scan that runs continuously keeps the radio busy and can disturb a GATT client that shares the adapter — another collector reconnecting on its own schedule, a blood-pressure cuff or a heart-rate strap, will start missing sessions. Scan in short windows (five minutes around the weighing), not around the clock. If a second device stops delivering, suspect the scan first.

## Filter before storing

A stabilising weight is broadcast several times a second, and the value drifts while the person settles. Store only frames with the stabilized flag set, and treat the load-removed frame as "nobody on the scale" rather than a reading. Without that filter, history fills with hundreds of near-duplicate rows and the odd 0.1 kg entry.

## Deduplicate on write, not in code

Give the storage layer a unique key over device, timestamp and metric, and write with `INSERT OR IGNORE`. Passive collection is idempotent by nature: replaying the same capture must not create a second row.

## Addresses and identity

These scales advertise a public, stable address, which is what makes a usable device key. Do not assume that for every device: many BLE peripherals rotate their address for privacy and must be matched by name or manufacturer data instead.

## Trust the capture over the clock

The timestamp field reads 1970 until a vendor app sets the clock. The frame is fine — the clock was never set. Use your own receive time and treat the device time as a hint.

## Re-capture after firmware updates

A layout recovered from advertisements can change when the vendor ships a firmware update. If the numbers stop making sense, capture a fresh session with a known weight before assuming the device died.

## Permissions

Scanning through BlueZ goes over the system D-Bus. On most distributions the collector needs root or an explicit policy rule; a scan that returns nothing at all is usually a permissions problem.

## See also

- [protocol.md](protocol.md) — the frame layout itself.
- [reverse-engineering-method.md](reverse-engineering-method.md) — how to recover a layout for a different device.

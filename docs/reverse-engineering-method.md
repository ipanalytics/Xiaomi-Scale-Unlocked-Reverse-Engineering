# Recovering an undocumented BLE frame format

_Russian version: [reverse-engineering-method.ru.md](reverse-engineering-method.ru.md)_

Vendors rarely document what their health devices broadcast. The measurement is usually there anyway, because the phone app has to read it without a round trip to a server. This is the procedure I use to turn that broadcast into a documented format, and it needs no vendor app at any step.

## Prerequisites

- A BLE radio on the machine that will do the capture (an on-board adapter or a USB dongle), with BlueZ on Linux.
- A scanner that prints the raw advertisement, including manufacturer and service data. Anything that can dump service data works; I use a short Python script on top of `bleak`.
- The device itself, and the ability to make it produce a measurement on demand.
- A file to append raw frames to, one JSON record or one hex line per advertisement.

## Procedure

1. **Capture the background.** Record two or three minutes with the device idle — nobody on the scale, no measurement running. This is the baseline: some devices keep broadcasting a stale or zero record, and you need to recognise that state before you can filter it out.

2. **Capture a known value.** Produce a measurement whose value you already know — stand on the scale, take a reading you can see on its own display. Record the whole session, including the seconds before and after, so you catch both the stabilising frames and the settle-down frames.

3. **Diff against the background.** Compare the two sets byte by byte. Almost every byte is constant; the ones that move are the payload. In a 13-byte frame, four or five bytes changing between sessions is normal.

4. **Anchor the known field.** You know one number in the frame — the measurement you read off the display. Try the moving byte pairs as little-endian and big-endian integers, divide by plausible scales (1, 10, 100, 200, 500, 1000), and find the combination that reproduces your value. For Xiaomi scales the answer is little-endian, divided by 200, i.e. a raw unit of 5 grams.

5. **Identify flags and status bits.** The byte right after the header usually carries flags: measurement present, stabilised, load removed, impedance available. Toggling the device state — stepping off the scale, weighing without socks, letting the display settle — moves those bits one at a time.

6. **Cross-check against public sources.** Somebody has usually decoded the same family already. Community firmware projects document frame layouts in code, and a published implementation gives me a check on the offsets and the scale factor. Where my capture and the public source disagree, I trust the capture and note the difference.

7. **Verify the branches you cannot reproduce.** A flag whose state you never observed — impedance, a second user profile — gets a synthetic frame in the test suite: build the frame you would expect, assert the decoder reads it as intended. The test records the assumption.

8. **Filter before storing.** A stabilising measurement is broadcast several times per second. Keep only frames whose stabilised bit is set, and drop the load-removed record — otherwise history fills with noise.

## What to publish, and what not to

An advertisement contains no personal data: it is a measurement and a device address. The device address is still an identifier, and the measurement is still health data. When I write a format up:

- replace device addresses with placeholders (`AA:BB:CC:DD:EE:FF`);
- use a neutral measurement in examples and tests instead of a real one;
- keep network addresses, hostnames, service names and file paths out of the text entirely;
- publish the layout, the decoder and the method — the parts that are useful to a stranger — and nothing that identifies a person or a machine.

Frame bytes of a real capture can be published once the address is gone and the measurement is replaced; the bytes themselves carry no identity.

## Limits

- The procedure recovers formats that are broadcast. A device that only reports over an encrypted GATT channel needs a different approach; I do not break encryption.
- Layouts are family-specific. Two scales from the same vendor can still differ.
- A format recovered this way can change with a firmware update; capture again if the numbers stop making sense.

## See also

The steps above describe the method; the frame layout of the first device I documented lives in [protocol.md](protocol.md), and the collector-side traps in [pitfalls.md](pitfalls.md).

# Body composition from two numbers

_Russian version: [body-composition.ru.md](body-composition.ru.md)_

The scale sends weight and impedance. The app shows fat, water, muscle, bone, protein, visceral fat, BMR and metabolic age. The gap between the two is arithmetic, and this page spells it out.

## What impedance actually is

Body-composition scales pass a small alternating current through the body and measure how hard it is to push. The four metal pads under the feet are that circuit: one pair carries the current, the other pair measures the voltage drop, so the resistance of the skin under the pads cancels out and what is left is the resistance of the path through the legs, always at a fixed frequency — 50 kHz on single-frequency models such as the Mi Body Composition Scale 2.

Fat and bone hold very little water, so they resist; muscle and the water inside it conduct. A higher impedance at the same weight therefore means more fat. The current path also explains the limits: the circuit runs leg to leg, so the upper body is only ever estimated, never measured, and hydration moves the number more than a real change in fat does. A glass of water, a workout or dry feet can shift the reading by more than a week of dieting.

For reference, a few hundred ohms is the ordinary range for an adult; the exact number depends on the path length through the legs, so height and build move it as much as body fat does.

## What the frame carries, and what it does not

The 13-byte advertisement has exactly two measured quantities: weight (bytes 11-12) and impedance (bytes 9-10, flagged by bit `0x02`, `0xFFFD` when absent). Everything else listed on the box is derived. The device timestamp helps track a measurement, but the scale has no clock of its own, so it is only as good as the last app that set it.

## The vendor arithmetic

Xiaomi never published the formulas. They were recovered from the Mi Fit app and are reproduced below, as used by openScale, bodymiscale and the Home Assistant integrations. The whole chain hangs on one lean-body-mass coefficient:

```
LBM = (height × 9.058 / 100) × (height / 100)
    + weight × 0.32 + 12.226
    − impedance × 0.0068
    − age × 0.0542
```

From there, for a male profile:

```
const = 0.8
coefficient = 1.0                     (0.98 below 61 kg)
fat % = (1 − ((LBM − const) × coefficient) / weight) × 100
water % = (100 − fat %) × 0.7, times 1.02 below 50 %, else 0.98
bone mass = (0.18016894 − LBM × 0.05158) × −1   (±0.1 kg around 2.2 kg)
muscle mass = weight − fat % × weight − bone mass
protein % = muscle mass / weight × 100 − water %
BMR = 877.8 + weight × 14.916 − height × 0.726 − age × 8.976
metabolic age = height × −0.7471 + weight × 0.9161 + age × 0.4184 + impedance × 0.0517 + 54.2267
```

Female profiles use their own constants (`9.25` below 50 years, `7.25` above; `0.245691014` for bone base; different BMR and metabolic-age coefficients), and the visceral-fat branch is quadratic in height and weight rather than a single line. The full set with the branches is in [tools/body_composition.py](../tools/body_composition.py).

Worked example — invented numbers, there only to show the arithmetic (65 kg, 172 cm, 35 years, female, 560 Ω). Not a reading of anyone:

| Metric | Value |
| --- | --- |
| Body fat | 31.7 % (20.6 kg) |
| Lean body mass | 44.4 kg |
| Water | 48.7 % |
| Muscle mass | 41.7 kg |
| Bone mass | 2.65 kg |
| Protein | 15.5 % |
| Visceral fat | 1 (1–59 scale) |
| BMR | 1243 kcal/day |
| Metabolic age | 33 |
| BMI | 22.0 |

Run your own:

```
python3 tools/body_composition.py --weight 65 --height 172 --age 35 --sex female --impedance 560
```

## How far to trust it

- These are the 2017 Mi Fit numbers. Newer app builds moved part of the maths into a native library (`libBodyfat.so`), so a current Zepp Life screen can differ by a few points from the table above. Nothing is lost by that: both are regressions against the same two inputs.
- Single-frequency leg-to-leg bioimpedance carries roughly ±3–5 percentage points of error on body fat, and it is a black box rather than a lab method. Absolute numbers flatter nobody; the day-to-day trend is the useful part.
- Measure the same way every time: morning, empty stomach, bare feet, before coffee, water or exercise. Then the only thing changing between readings is you.
- None of this is a medical measurement. Treat it as a number in a table, not a diagnosis.

## Where this lives in the wild

The page above is not folklore: the same chain sits in maintained code. [dckiller51/bodymiscale](https://github.com/dckiller51/bodymiscale) (Home Assistant, Python) carries the identical `get_lbm` line and the same fat, water, bone, muscle, protein, visceral-fat, BMR and metabolic-age constants; [lolouk44/xiaomi_mi_scale](https://github.com/lolouk44/xiaomi_mi_scale) is the original 2018 recovery of them; [oliexdev/openScale](https://github.com/oliexdev/openScale) is the Java implementation.

Two things worth knowing before trusting a random snippet:

- Links that circulate in forum posts and in answers from AI models — `vrachieru/mi-scale-body-composition`, `custom-components/bodymiscale`, `syssi/esphome-bodymiscale` — do not exist on GitHub, and the lean-body-mass coefficients `0.485` / `0.382` that appear alongside them are not in any of the maintained projects. Copy the formula from this page, not from a summary that cites a dead repository.
- The native library name is real — `libBodyfat.so` is called out in the openScale issue tracker — but its contents were never published. Everything said about its internals, including which chip vendor wrote it, is an inference from the outside.

## Dual-frequency hardware

The S400 and similar models add a second frequency (250 kHz) and with it the compartment metrics that need it: extracellular and intracellular water, their ratio, body cell mass and MRI-validated skeletal mass. On a 50 kHz scale those columns stay empty, and no formula fills them in.

Their protocol is a different animal as well: not the open `0x181B` broadcast but the proprietary MiBeacon service data `0xFE95`, with the payload encrypted under a per-device bind key from the vendor cloud (AES-CCM), the weight carried as a uint16 in hundredths of a kilogram and the measurement object numbered `0x4e16`. The class that does this in openScale — `XiaomiS800Lib` — is a good place to see the layout.

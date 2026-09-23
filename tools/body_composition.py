#!/usr/bin/env python3
"""Body composition from weight and impedance, Xiaomi Mi scale family.

The scale measures two things: weight and the electrical impedance of the body
between the electrodes under the feet, always at 50 kHz on a single-frequency
model. Everything else in the vendor app - fat, water, muscle, bone, protein,
visceral fat, BMR, metabolic age - is arithmetic on top of those two numbers plus
height, age and sex.

The arithmetic below is the 2017 Mi Fit regression set, recovered by reverse
engineering and used by openScale, bodymiscale and the Home Assistant
integrations. It reproduces the numbers the old app showed, not the current
Zepp Life ones: newer Xiaomi builds moved part of the maths into a native
library (libBodyfat.so), so a fresh app can differ by a few
points. Treat the output as an estimate, and compare only measurements taken
under the same conditions.

Usage:
    python3 body_composition.py --weight 65 --height 172 --age 35 --sex female --impedance 560
    python3 body_composition.py --weight 65 --height 172 --age 35 --sex female --impedance 560 --json
"""

import argparse
import json


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def body_composition(weight_kg: float, height_cm: float, age: int, sex: str, impedance_ohm: float) -> dict:
    """Return the vendor-style body composition estimate for one weighing.

    weight_kg   - measured weight
    height_cm   - user height
    age         - user age in years
    sex         - "male" or "female"
    impedance_ohm - raw impedance from the frame; refuses values above 3000
    """
    if sex not in ("male", "female"):
        raise ValueError("sex must be 'male' or 'female'")
    if not 10 <= weight_kg <= 200:
        raise ValueError("weight outside 10-200 kg")
    if not 100 <= height_cm <= 220:
        raise ValueError("height outside 100-220 cm")
    if not 5 <= age <= 99:
        raise ValueError("age outside 5-99 years")
    if not 100 <= impedance_ohm <= 3000:
        raise ValueError("impedance outside 100-3000 Ohm - electrode contact is usually the cause")

    female = sex == "female"

    # Lean-body-mass coefficient: the one place impedance enters the whole chain.
    lbm_coef = (height_cm * 9.058 / 100) * (height_cm / 100)
    lbm_coef += weight_kg * 0.32 + 12.226
    lbm_coef -= impedance_ohm * 0.0068
    lbm_coef -= age * 0.0542

    const = 9.25 if (female and age <= 49) else (7.25 if female else 0.8)
    if not female and weight_kg < 61:
        coef = 0.98
    elif female and weight_kg > 60:
        coef = 0.96 * (1.03 if height_cm > 160 else 1.0)
    elif female and weight_kg < 50:
        coef = 1.02 * (1.03 if height_cm > 160 else 1.0)
    else:
        coef = 1.0
    fat_percent = (1.0 - (((lbm_coef - const) * coef) / weight_kg)) * 100
    if fat_percent > 63:
        fat_percent = 75
    fat_percent = _clamp(fat_percent, 5, 75)

    water = (100 - fat_percent) * 0.7
    water = _clamp(water * (1.02 if water <= 50 else 0.98), 35, 75)

    bone = (0.245691014 if female else 0.18016894) - lbm_coef * 0.05158
    bone = -bone
    bone = bone + 0.1 if bone > 2.2 else bone - 0.1
    bone = _clamp(bone, 0.5, 8)

    muscle = weight_kg - (fat_percent * 0.01 * weight_kg) - bone
    muscle = _clamp(muscle, 10, 120)

    if female:
        if weight_kg > (13 - (height_cm * 0.5)) * -1:
            sub = ((height_cm * 1.45) + (height_cm * 0.1158) * height_cm) - 120
            visceral = (weight_kg * 500 / sub - 6) + (age * 0.07)
        else:
            sub = 0.691 + (height_cm * -0.0024) + (height_cm * -0.0024)
            visceral = (((height_cm * 0.027) - (sub * weight_kg)) * -1) + (age * 0.07) - age
    else:
        if height_cm < weight_kg * 1.6:
            sub = ((height_cm * 0.4) - (height_cm * (height_cm * 0.0826))) * -1
            visceral = ((weight_kg * 305) / (sub + 48)) - 2.9 + (age * 0.15)
        else:
            sub = 0.765 + height_cm * -0.0015
            visceral = (((height_cm * 0.143) - (weight_kg * sub)) * -1) + (age * 0.15) - 5.0
    visceral = _clamp(visceral, 1, 50)

    bmr = 864.6 + weight_kg * 10.2036 - height_cm * 0.39336 - age * 6.204 if female \
        else 877.8 + weight_kg * 14.916 - height_cm * 0.726 - age * 8.976
    if (female and bmr > 2996) or (not female and bmr > 2322):
        bmr = 5000
    bmr = _clamp(bmr, 500, 10000)

    protein = _clamp((muscle / weight_kg) * 100 - water, 5, 32)

    if female:
        meta_age = (height_cm * -1.1165) + (weight_kg * 1.5784) + (age * 0.4615) + (impedance_ohm * 0.0415) + 83.2548
    else:
        meta_age = (height_cm * -0.7471) + (weight_kg * 0.9161) + (age * 0.4184) + (impedance_ohm * 0.0517) + 54.2267
    meta_age = _clamp(meta_age, 15, 80)

    bmi = _clamp(weight_kg / ((height_cm / 100) ** 2), 10, 90)
    ideal = (height_cm - 70) * 0.6 if female else (height_cm - 80) * 0.7

    return {
        "weight_kg": round(weight_kg, 2),
        "impedance_ohm": round(impedance_ohm, 1),
        "fat_percent": round(fat_percent, 1),
        "fat_mass_kg": round(fat_percent * 0.01 * weight_kg, 2),
        "water_percent": round(water, 1),
        "muscle_mass_kg": round(muscle, 2),
        "bone_mass_kg": round(bone, 2),
        "protein_percent": round(protein, 1),
        "visceral_fat": round(visceral, 1),
        "bmr_kcal": round(bmr),
        "metabolic_age": round(meta_age),
        "lean_body_mass_kg": round(weight_kg - fat_percent * 0.01 * weight_kg, 2),
        "bmi": round(bmi, 1),
        "ideal_weight_kg": round(ideal, 1),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Body composition from weight and impedance (Xiaomi scale family)")
    parser.add_argument("--weight", type=float, required=True, help="weight in kg")
    parser.add_argument("--height", type=float, required=True, help="height in cm")
    parser.add_argument("--age", type=int, required=True, help="age in years")
    parser.add_argument("--sex", required=True, choices=("male", "female"))
    parser.add_argument("--impedance", type=float, required=True, help="impedance in Ohm, straight from the frame")
    parser.add_argument("--json", action="store_true", help="print one JSON object instead of text")
    args = parser.parse_args()

    result = body_composition(args.weight, args.height, args.age, args.sex, args.impedance)
    if args.json:
        print(json.dumps(result, ensure_ascii=False))
        return
    for key, value in result.items():
        print(f"{key:<20} {value}")


if __name__ == "__main__":
    main()

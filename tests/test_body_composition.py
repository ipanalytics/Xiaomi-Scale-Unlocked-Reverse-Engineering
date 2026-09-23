import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tools"))

from body_composition import body_composition  # noqa: E402

# Illustrative profiles only; no real person's numbers appear in this repository.
DEMO_WEIGHT, DEMO_HEIGHT, DEMO_AGE, DEMO_IMPEDANCE = 65.0, 172, 35, 560.0


class BodyCompositionTest(unittest.TestCase):
    def test_demo_measurement(self):
        r = body_composition(DEMO_WEIGHT, DEMO_HEIGHT, DEMO_AGE, "female", DEMO_IMPEDANCE)
        self.assertAlmostEqual(r["fat_percent"], 31.7, places=1)
        self.assertAlmostEqual(r["fat_mass_kg"], 20.6, places=1)
        self.assertAlmostEqual(r["lean_body_mass_kg"], 44.4, places=1)
        self.assertAlmostEqual(r["water_percent"], 48.7, places=1)
        self.assertAlmostEqual(r["muscle_mass_kg"], 41.7, places=1)
        self.assertAlmostEqual(r["bone_mass_kg"], 2.65, places=2)
        self.assertAlmostEqual(r["protein_percent"], 15.5, places=1)
        self.assertEqual(r["bmr_kcal"], 1243)
        self.assertEqual(r["metabolic_age"], 33)

    def test_fat_and_lean_add_up_to_weight(self):
        r = body_composition(DEMO_WEIGHT, DEMO_HEIGHT, DEMO_AGE, "female", DEMO_IMPEDANCE)
        self.assertAlmostEqual(r["fat_mass_kg"] + r["lean_body_mass_kg"], DEMO_WEIGHT, places=1)

    def test_sex_changes_the_estimate(self):
        female = body_composition(DEMO_WEIGHT, DEMO_HEIGHT, DEMO_AGE, "female", DEMO_IMPEDANCE)["fat_percent"]
        male = body_composition(DEMO_WEIGHT, DEMO_HEIGHT, DEMO_AGE, "male", DEMO_IMPEDANCE)["fat_percent"]
        self.assertGreater(female, male)                     # same body, different constants

    def test_impedance_moves_fat_estimate(self):
        low = body_composition(DEMO_WEIGHT, DEMO_HEIGHT, DEMO_AGE, "female", 520)["fat_percent"]
        high = body_composition(DEMO_WEIGHT, DEMO_HEIGHT, DEMO_AGE, "female", 640)["fat_percent"]
        self.assertGreater(high, low)                        # more resistance, more fat

    def test_rejects_impossible_input(self):
        with self.assertRaises(ValueError):
            body_composition(DEMO_WEIGHT, DEMO_HEIGHT, DEMO_AGE, "female", 3500)   # no foot contact
        with self.assertRaises(ValueError):
            body_composition(5, DEMO_HEIGHT, DEMO_AGE, "female", DEMO_IMPEDANCE)
        with self.assertRaises(ValueError):
            body_composition(DEMO_WEIGHT, DEMO_HEIGHT, DEMO_AGE, "unknown", DEMO_IMPEDANCE)

    def test_caps_are_respected(self):
        r = body_composition(180, 160, 60, "female", 900)
        self.assertLessEqual(r["fat_percent"], 75)
        self.assertGreaterEqual(r["muscle_mass_kg"], 10)
        self.assertLessEqual(r["visceral_fat"], 50)


if __name__ == "__main__":
    unittest.main()

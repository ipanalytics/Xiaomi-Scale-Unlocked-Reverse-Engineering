import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

from xiaomi_scale_decode import (  # noqa: E402
    decode_frame,
    decode_stream,
    _frame_from_line,
    main,
)

# Frame captured from a Mi Body Composition Scale (0x181B, 13 bytes) while a
# 75.0 kg load stood on it; the impedance field carries 0xFFFD because that
# weighing was started without the impedance option enabled in a vendor app.
V2_STABILIZED = bytes.fromhex("0224b2070104030637fdff983a")
# Same scale right after the load was removed: weight has collapsed to 0.1 kg.
V2_LOAD_REMOVED = bytes.fromhex("0284b207010403072600001400")
# Synthetic frame with the impedance flag set, to exercise that branch.
V2_WITH_IMPEDANCE = bytes.fromhex("0222b20701040306372c01983a")
# Mi Smart Scale (0x181D, 10 bytes), weight 75.75 kg.
V1_FRAME = bytes.fromhex("222e3bb2070101003615")


class TestFrameParsing(unittest.TestCase):
    def test_hex_accepts_common_separators(self):
        self.assertEqual(_frame_from_line("02:24-B2 07"), bytes.fromhex("0224b207"))
        self.assertIsNone(_frame_from_line("02 24 b"))
        self.assertIsNone(_frame_from_line("hello"))
        self.assertIsNone(_frame_from_line("0224b207zz"))

    def test_v2_stabilized_weight(self):
        record = decode_frame(V2_STABILIZED)
        self.assertEqual(record["version"], 2)
        self.assertAlmostEqual(record["weight_kg"], 75.0)
        self.assertTrue(record["stabilized"])
        self.assertFalse(record["load_removed"])
        self.assertIsNone(record["impedance"])
        self.assertEqual(record["timestamp"], "1970-01-04T03:06:55")

    def test_v2_load_removed_reports_empty_scale(self):
        record = decode_frame(V2_LOAD_REMOVED)
        self.assertAlmostEqual(record["weight_kg"], 0.1)
        self.assertTrue(record["load_removed"])
        self.assertFalse(record["stabilized"])

    def test_v2_impedance_only_when_flagged(self):
        record = decode_frame(V2_WITH_IMPEDANCE)
        self.assertEqual(record["impedance"], 300)
        self.assertFalse(decode_frame(V2_STABILIZED)["impedance"])

    def test_v1_weight_and_time(self):
        record = decode_frame(V1_FRAME)
        self.assertEqual(record["version"], 1)
        self.assertAlmostEqual(record["weight_kg"], 75.75)
        self.assertIsNone(record["impedance"])

    def test_rejects_unknown_length(self):
        with self.assertRaises(ValueError):
            decode_frame(b"\x02" * 12)


class TestCli(unittest.TestCase):
    def test_decodes_frame_argument(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main([V2_STABILIZED.hex()])
        self.assertEqual(code, 0)
        payload = json.loads(buffer.getvalue().strip())
        self.assertAlmostEqual(payload["weight_kg"], 75.0)

    def test_bad_argument_sets_exit_code(self):
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = main(["nonsense"])
        self.assertEqual(code, 2)
        self.assertIn("error", buffer.getvalue())

    def test_stream_keeps_going_after_bad_line(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "frames.txt")
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("not hex\n")
                handle.write("# a comment line is ignored\n")
                handle.write(V2_STABILIZED.hex() + "\n")
                handle.write(V1_FRAME.hex() + "\n")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                counted = decode_stream(open(path, encoding="utf-8"))
            self.assertEqual(counted, 2)
            lines = [json.loads(x) for x in buffer.getvalue().strip().splitlines()]
            self.assertEqual(lines[0]["error"], "not a hex frame")
            self.assertEqual(lines[2]["version"], 1)


if __name__ == "__main__":
    unittest.main()

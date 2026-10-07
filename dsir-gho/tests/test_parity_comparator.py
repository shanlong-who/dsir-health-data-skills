"""Ensure the source-parity comparator rejects corrupted evidence."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evals"))
from run_parity import compare_context


class ParityComparatorTests(unittest.TestCase):
    def test_numeric_serialization_rounding_is_tolerated(self):
        self.assertTrue(compare_context([{"NumericValue": 123.12345678912345}], [{"NumericValue": 123.123456789123}]))

    def test_values_labels_and_missingness_cannot_be_changed_to_pass(self):
        baseline = [{"NumericValue": 10.0, "Value": "NA", "DIM_SEX": "FEMALE"}]
        for corrupted in ([{"NumericValue": 11.0, "Value": "NA", "DIM_SEX": "FEMALE"}],
                          [{"NumericValue": 10.0, "Value": None, "DIM_SEX": "FEMALE"}],
                          [{"NumericValue": 10.0, "Value": "NA", "DIM_SEX": "MALE"}], []):
            self.assertFalse(compare_context(baseline, corrupted))


if __name__ == "__main__":
    unittest.main()

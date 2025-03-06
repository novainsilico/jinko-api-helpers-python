import unittest
import json
import csv
import crabbit.utils


class TestCrabbit(unittest.TestCase):
    def test_merge_vpop(self):
        merged_vpop = crabbit.utils.merge_vpops(
            [
                "tests/crabbit/data/small-vpop-3.json",
                "tests/crabbit/data/small-vpop-5.json",
            ]
        )
        self.assertEqual(
            merged_vpop,
            json.load(
                open("tests/crabbit/data/merged-vpop.json", "r", encoding="utf-8")
            ),
        )

    def test_merge_vpop_design_success(self):
        merged_vpop_design = crabbit.utils.merge_vpop_designs(
            [
                "tests/crabbit/data/VpopDesign-A.json",
                "tests/crabbit/data/VpopDesign-B.json",
                "tests/crabbit/data/VpopDesign-C.json",
            ]
        )
        self.assertEqual(
            merged_vpop_design,
            json.load(
                open("tests/crabbit/data/VpopDesign-merged.json", "r", encoding="utf-8")
            ),
        )

    def test_merge_vpop_design_conflict(self):
        merged_vpop_design = crabbit.utils.merge_vpop_designs(
            [
                "tests/crabbit/data/VpopDesign-A.json",
                "tests/crabbit/data/VpopDesign-B.json",
                "tests/crabbit/data/VpopDesign-Cbis.json",
            ]
        )
        self.assertEqual(merged_vpop_design, None)

    def test_merge_csv_success(self):
        merged_csv = crabbit.utils.merge_csv(
            [
                "tests/crabbit/data/csv-A.csv",
                "tests/crabbit/data/csv-B.csv",
            ]
        )
        all_equal = True
        with open(
            "tests/crabbit/data/csv-merged.csv", "r", newline="", encoding="utf-8"
        ) as f:
            reader = csv.reader(f, delimiter=",")
            for result, golden in zip(merged_csv, reader):
                all_equal = all_equal and (result == golden)
        self.assertEqual(all_equal, True)

    def test_merge_csv_conflict(self):
        merged_csv = crabbit.utils.merge_csv(
            [
                "tests/crabbit/data/csv-A.csv",
                "tests/crabbit/data/csv-D.csv",
            ]
        )
        self.assertEqual(merged_csv, None)

    def test_merge_csv_mismatch(self):
        merged_csv = crabbit.utils.merge_csv(
            [
                "tests/crabbit/data/csv-A.csv",
                "tests/crabbit/data/csv-D.csv",
            ]
        )
        self.assertEqual(merged_csv, None)


if __name__ == "__main__":
    unittest.main()

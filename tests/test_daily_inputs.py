"""Synthetic file-interface checks; no scientific input access."""

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from toshkan_workflow.preprocessing import read_daily_depths


class DailyInputTests(unittest.TestCase):
    def setUp(self):
        self.folder = TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name) / "synthetic.csv"
        self.header = "date,grid_id,depth_mm,units\n"
        self.rows = "2000-02-28,g,1,mm/day\n2000-02-29,g,2,mm/day\n"

    def read(self, text=None, **kwargs):
        self.path.write_text(self.header+self.rows if text is None else text, encoding="utf-8")
        options = dict(start_date="2000-02-28", end_date="2000-02-29", expected_grid_ids=["g"])
        options.update(kwargs)
        return read_daily_depths(self.path, **options)

    def test_complete_leap_days(self):
        result = self.read()
        self.assertEqual(result["dates"], ["2000-02-28", "2000-02-29"])
        self.assertEqual(result["depths_mm_per_day"], {"g": [1, 2]})
        self.assertEqual(self.path.read_text(), self.header+self.rows)

    def test_interleaved_grids(self):
        rows = "".join(f"{d},{g},1,mm/day\n" for d in ["2000-02-28", "2000-02-29"] for g in ["b", "a"])
        self.assertEqual(self.read(self.header+rows, expected_grid_ids=["a", "b"])["depths_mm_per_day"],
                         {"a": [1, 1], "b": [1, 1]})

    def test_schema_and_bad_rows(self):
        for text in ("", self.header, "date,grid_id,depth_mm,depth_mm\n"+self.rows,
                     self.header+"2000-02-28,g,1\n", self.header+self.rows.replace("1,mm/day", "1,mm/day,extra")):
            with self.subTest(text=text), self.assertRaises(ValueError):
                self.read(text)

    def test_dates_and_coverage(self):
        for rows in (self.rows.splitlines()[0]+"\n", self.rows.replace("2000-02-29", "2000-02-28"),
                     "\n".join(reversed(self.rows.splitlines())), self.rows.replace("2000-02-29", "2000-03-01")):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.read(self.header+rows)
        for options in (dict(start_date="2000-03-01"), dict(start_date="20000228"),
                        dict(expected_grid_ids=["other"]), dict(expected_grid_ids=["g", "g"]),
                        dict(expected_grid_ids=[]), dict(expected_grid_ids=["g", "missing"])):
            with self.subTest(options=options), self.assertRaises(ValueError):
                self.read(**options)

    def test_values_and_units(self):
        for value in ("-1", "nan", "inf", "", "true"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.read(self.header+self.rows.replace(",1,", f",{value},"))
        with self.assertRaises(ValueError):
            self.read(self.header+self.rows.replace("mm/day", "m3/day"))

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            read_daily_depths(self.path, start_date="2000-01-01", end_date="2000-01-01", expected_grid_ids=["g"])


if __name__ == "__main__":
    unittest.main()

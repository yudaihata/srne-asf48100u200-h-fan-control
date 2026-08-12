from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

try:
    import pandas  # noqa: F401
except ImportError:
    pandas = None


@unittest.skipIf(pandas is None, "optional pandas analysis dependency is not installed")
class HistoryAnalysisTests(unittest.TestCase):
    def test_fixture_preserves_unknown_and_reports_cooling_delta(self) -> None:
        from analyze_history import compare, reconstruct, stats

        stock_data = reconstruct(ROOT / "tests/fixtures/history-stock.csv", "UTC")
        candidate_data = reconstruct(
            ROOT / "tests/fixtures/history-candidate.csv", "UTC"
        )
        self.assertTrue(stock_data.iloc[1].isna().any())
        stock = stats(stock_data)
        candidate = stats(candidate_data)
        self.assertEqual(stock["complete_minutes"], 2)
        result = compare(stock, candidate)
        self.assertEqual(result["all"]["temp_b_mean_delta"], -4.0)
        self.assertEqual(result["all"]["temp_c_mean_delta"], -3.0)
        self.assertIsNone(result["low_load_le_1000w"]["temp_b_mean_delta"])


if __name__ == "__main__":
    unittest.main()

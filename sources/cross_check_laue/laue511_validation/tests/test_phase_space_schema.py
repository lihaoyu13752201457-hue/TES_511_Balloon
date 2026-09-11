from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from laue511.phase_space import validate_phase_space


class PhaseSpaceSchemaTest(unittest.TestCase):
    def test_phase_space_schema_accepts_canonical_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "phase_space.csv"
            with path.open("w", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["event_id", "photon_id", "E_keV", "x_mm", "y_mm", "z_mm", "dx", "dy", "dz", "time_s", "weight", "source_tag"],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "event_id": 1,
                        "photon_id": 2,
                        "E_keV": 511.0,
                        "x_mm": 0.0,
                        "y_mm": 0.0,
                        "z_mm": 8300.0,
                        "dx": 0.0,
                        "dy": 0.0,
                        "dz": 1.0,
                        "time_s": 0.0,
                        "weight": 1.0,
                        "source_tag": "unit",
                    }
                )
            report = validate_phase_space(path)
            self.assertTrue(report["ok"], report)


if __name__ == "__main__":
    unittest.main()

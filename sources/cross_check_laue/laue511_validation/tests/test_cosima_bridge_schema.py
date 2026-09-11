from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from laue511.cosima_bridge import convert_phase_space_csv


class CosimaBridgeSchemaTest(unittest.TestCase):
    def test_bridge_preserves_phase_space_fields_in_sidecar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            phase = tmp_path / "phase_space.csv"
            out = tmp_path / "cosima_eventlist.source"
            sidecar = tmp_path / "phase_space_sidecar.json"
            with phase.open("w", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "event_id",
                        "photon_id",
                        "E_keV",
                        "x_mm",
                        "y_mm",
                        "z_mm",
                        "dx",
                        "dy",
                        "dz",
                        "time_s",
                        "weight",
                        "ring_id",
                        "tile_id",
                        "branch",
                        "source_tag",
                        "offaxis_x_rad",
                        "offaxis_y_rad",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "event_id": 4,
                        "photon_id": 9,
                        "E_keV": 511.0,
                        "x_mm": 1.0,
                        "y_mm": 2.0,
                        "z_mm": 8300.0,
                        "dx": 0.0,
                        "dy": 0.0,
                        "dz": 1.0,
                        "time_s": 1.5,
                        "weight": 0.7,
                        "ring_id": 2,
                        "tile_id": 3,
                        "branch": "DIFFRACT",
                        "source_tag": "unit",
                        "offaxis_x_rad": 0.0,
                        "offaxis_y_rad": 0.0,
                    }
                )
            summary = convert_phase_space_csv(phase, out, sidecar)
            saved = json.loads(sidecar.read_text(encoding="utf-8"))
            self.assertEqual(summary["n_rows"], 1)
            self.assertIn("EVENT 4 9 511", out.read_text(encoding="utf-8"))
            self.assertEqual(saved["provenance"][0]["ring_id"], 2)
            self.assertEqual(saved["provenance"][0]["branch"], "DIFFRACT")

    def test_bridge_joins_ring_tile_from_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            phase = tmp_path / "phase_space.csv"
            history = tmp_path / "optics_history.csv"
            out = tmp_path / "cosima_eventlist.source"
            sidecar = tmp_path / "phase_space_sidecar.json"
            with phase.open("w", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=[
                        "event_id",
                        "E_keV",
                        "x_mm",
                        "y_mm",
                        "z_mm",
                        "ux",
                        "uy",
                        "uz",
                        "weight",
                        "source_tag",
                        "track_id",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "event_id": 7,
                        "E_keV": 511.0,
                        "x_mm": 0.0,
                        "y_mm": 0.0,
                        "z_mm": 8300.0,
                        "ux": 0.0,
                        "uy": 0.0,
                        "uz": 1.0,
                        "weight": 1.0,
                        "source_tag": "geant4_laue_darwin_guan_process",
                        "track_id": 1,
                    }
                )
            with history.open("w", newline="") as handle:
                writer = csv.DictWriter(
                    handle,
                    fieldnames=["event_id", "track_id", "stage", "ring_id", "tile_id"],
                )
                writer.writeheader()
                writer.writerow({"event_id": 7, "track_id": 1, "stage": "DIFFRACT", "ring_id": 2, "tile_id": 44})
            summary = convert_phase_space_csv(phase, out, sidecar, history)
            saved = json.loads(sidecar.read_text(encoding="utf-8"))
            self.assertEqual(summary["history_join"]["matched_rows"], 1)
            self.assertEqual(saved["provenance"][0]["ring_id"], 2)
            self.assertEqual(saved["provenance"][0]["tile_id"], 44)
            self.assertTrue(saved["provenance"][0]["history_joined"])


if __name__ == "__main__":
    unittest.main()

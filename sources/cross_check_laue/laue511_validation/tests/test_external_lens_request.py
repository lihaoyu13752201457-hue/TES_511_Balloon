from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ExternalLensRequestTest(unittest.TestCase):
    def test_export_request_writes_oracle_input_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(
                [
                    "python3",
                    str(ROOT / "tools/export_external_lens_request.py"),
                    "--out-dir",
                    tmp,
                ],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
                text=True,
            )
            request = json.loads((Path(tmp) / "external_lens_oracle_request.json").read_text(encoding="utf-8"))
            heart_request = json.loads((Path(tmp) / "heart_lens_adapter_request.json").read_text(encoding="utf-8"))
            self.assertEqual(request["purpose"], "external_full_lens_oracle_request")
            self.assertEqual(len(request["rings"]), 5)
            self.assertEqual(heart_request["purpose"], "heart_full_lens_adapter_request")
            self.assertEqual(heart_request["source_request"], "external_lens_oracle_request.json")
            self.assertEqual(heart_request["requested_hit_table_schema"], "EXTERNAL_LENS_HITS_SCHEMA.md")
            self.assertEqual(heart_request["requested_tile_table"], "external_lens_oracle_tiles.csv")
            self.assertEqual(heart_request["requested_heart_hdf5_datasets"]["detector_image"], "Results/detector_image")
            self.assertTrue((Path(tmp) / "external_lens_oracle_rings.csv").exists())
            tiles_path = Path(tmp) / "external_lens_oracle_tiles.csv"
            self.assertTrue(tiles_path.exists())
            with tiles_path.open(newline="") as handle:
                tiles = list(csv.DictReader(handle))
            self.assertEqual(len(tiles), 360)
            self.assertIn("ideal_plane_normal_x", tiles[0])
            self.assertIn("expected_diffracted_uz", tiles[0])
            self.assertTrue((Path(tmp) / "external_lens_observables_schema_example.csv").exists())
            self.assertIn("python_reference_diffracted_area_cm2", request["comparison_targets"])
            self.assertEqual(request["requested_tile_table"], "external_lens_oracle_tiles.csv")


if __name__ == "__main__":
    unittest.main()

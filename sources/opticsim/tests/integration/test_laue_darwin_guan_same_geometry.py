from __future__ import annotations

import csv
import json
import math
import subprocess
import tempfile
import unittest
from pathlib import Path

from systems.laue_darwin_guan.darwin_guan_compare import (
    DarwinDynamicalModel,
    GuanStyleCrystalBraggModel,
    Vector3,
    load_rings,
)


ROOT = Path(__file__).resolve().parents[2]


class LaueDarwinGuanSameGeometryTest(unittest.TestCase):
    def test_geometry_snapshot_matches_canonical_rows(self) -> None:
        with (ROOT / "data/laue/ge111_480_550keV_multiring_darwin_config.csv").open(newline="", encoding="utf-8") as handle:
            canonical = list(csv.DictReader(handle))
        with (ROOT / "systems/laue_darwin_guan/geometry/ge111_480_550keV_multiring_darwin_config.csv").open(newline="", encoding="utf-8") as handle:
            snapshot = list(csv.DictReader(handle))
        self.assertEqual(canonical, snapshot)

    def test_bragg_model_reflects_to_focal_direction(self) -> None:
        rings = load_rings(ROOT / "systems/laue_darwin_guan/geometry/ge111_480_550keV_multiring_darwin_config.csv", 8300.0)
        darwin = DarwinDynamicalModel.from_csv(ROOT / "data/laue/Ge111_480_550keV_darwin_mosaic_table.csv")
        model = GuanStyleCrystalBraggModel(darwin, 8300.0)
        in_dir = Vector3(0.0, 0.0, 1.0)
        for ring in rings:
            with self.subTest(ring=ring.ring_id):
                pos = Vector3(ring.radius_mm, 0.0, -0.5 * ring.thickness_mm)
                decision = model.evaluate(ring, pos, in_dir)
                self.assertLess(decision.reflected_minus_ideal_norm, 1e-12)
                self.assertLess(abs(decision.bragg_angle_from_plane_rad - decision.theta_B_rad), 2e-6)
                self.assertAlmostEqual(
                    decision.probs.p_diff + decision.probs.p_abs + decision.probs.p_trans,
                    1.0,
                    places=12,
                )

    def test_runner_builds_same_geometry_comparison(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "guan_compare"
            subprocess.run(
                [
                    "python3",
                    "systems/laue_darwin_guan/darwin_guan_compare.py",
                    "--n",
                    "5000",
                    "--seed",
                    "20260521",
                    "--out",
                    str(out),
                ],
                cwd=ROOT,
                check=True,
            )
            summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["implementation_style"], "guan_style_model_process_split")
            self.assertEqual(summary["n_rings"], 5)
            self.assertEqual(summary["n_tiles_total"], 360)
            self.assertEqual(summary["same_geometry_as"], "systems/laue_darwin_guan/geometry/ge111_480_550keV_multiring_darwin_config.csv")
            self.assertLess(summary["max_probability_sum_error"], 1e-10)
            self.assertLess(summary["max_reflection_vector_error"], 1e-12)
            self.assertLess(summary["max_plane_minus_bragg_abs_rad"], 2e-5)
            self.assertLess(
                summary["comparison_to_barhoum"]["max_abs_delta_expected_p_diff_vs_barhoum_mean_p_diff"],
                0.003,
            )
            self.assertTrue(math.isfinite(summary["sampled_spot_d90_cm"]))
            self.assertTrue((out / "GEANT4_DARWIN_GUAN_VS_BARHOUM_REPORT.md").exists())


if __name__ == "__main__":
    unittest.main()

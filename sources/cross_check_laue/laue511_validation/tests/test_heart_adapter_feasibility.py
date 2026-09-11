from __future__ import annotations

import tempfile
import unittest
import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
_SPEC = importlib.util.spec_from_file_location(
    "build_heart_adapter_feasibility",
    ROOT / "tools/build_heart_adapter_feasibility.py",
)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
build_report = _MODULE.build_report


class HeartAdapterFeasibilityTest(unittest.TestCase):
    def test_build_report_recognizes_surface_normal_coupling(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            heart = Path(tmp) / "HEART"
            (heart / "docs/files").mkdir(parents=True)
            (heart / "HEART/components").mkdir(parents=True)
            (heart / "HEART").mkdir(parents=True, exist_ok=True)
            (heart / "docs/files/start.rst").write_text(
                "used to calculate the Bragg angles and structure factors\n"
                "angle between the crystallite surface normal and the crystal surface normal\n",
                encoding="utf-8",
            )
            (heart / "HEART/components/FlatCrystal.py").write_text(
                "axis_N: Surface normal of the crystal\n",
                encoding="utf-8",
            )
            (heart / "HEART/ray_tracer.py").write_text(
                "photon.c_norm[:] = get_crystal_normal(crystal, pos)\n"
                "crystallite = rodrigues_rotation(k=cross(photon.c_norm, photon.ray), theta=0, v=photon.c_norm)\n",
                encoding="utf-8",
            )
            report = build_report(
                heart,
                ROOT / "benchmarks/reference_outputs/external_lens_oracle_tiles.csv",
            )
        self.assertTrue(report["ok"])
        self.assertFalse(report["full_lens_runner_ready"])
        self.assertEqual(report["tile_geometry"]["tile_rows"], 360)
        self.assertGreater(report["tile_geometry"]["min_abs_angle_slab_to_ideal_plane_normal_deg"], 80.0)

    def test_handoff_patch_records_independent_plane_normal_argument(self) -> None:
        patch = (ROOT / "benchmarks/reference_outputs/heart_independent_plane_normal.patch").read_text(
            encoding="utf-8"
        )
        self.assertIn("diff_plane_N", patch)
        self.assertIn("use_independent_diff_plane_norm", patch)
        self.assertIn("crystal.diff_plane_norm", patch)
        self.assertIn("x_int_s, x_int_b = -np.inf, np.inf", patch)
        self.assertIn("origin + 0. * ray", patch)


if __name__ == "__main__":
    unittest.main()

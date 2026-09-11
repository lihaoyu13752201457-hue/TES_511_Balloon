from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("import_heart_detector_image", ROOT / "tools/import_heart_detector_image.py")
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
heart_detector_image_to_hits = MODULE.heart_detector_image_to_hits


@unittest.skipUnless(importlib.util.find_spec("h5py"), "h5py is optional for the HEART HDF5 importer")
class HeartDetectorImageImportTest(unittest.TestCase):
    def test_heart_detector_image_to_hits(self) -> None:
        import h5py

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            h5_path = tmp_path / "heart.h5"
            csv_path = tmp_path / "hits.csv"
            with h5py.File(h5_path, "w") as h5:
                h5.create_dataset("Version", data="2.1.3")
                detector = h5.create_group("Detector")
                detector.create_dataset("detector_L_pos", data=[-0.5, 0.5])
                detector.create_dataset("detector_W_pos", data=[-1.0, 1.0])
                diagnostics = h5.create_group("Diagnostics")
                diagnostics.create_dataset("Number_of_Photons", data=10)
                results = h5.create_group("Results")
                results.create_dataset("detector_image", data=[[0.0, 2.0], [3.0, 0.0]])

            summary = heart_detector_image_to_hits(h5_path, csv_path)
            self.assertEqual(summary["nonzero_detector_pixels"], 2)
            self.assertAlmostEqual(summary["detector_weight"], 5.0)
            rows = csv_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(rows[0], "x_mm,y_mm,weight")
            self.assertEqual(len(rows), 3)


if __name__ == "__main__":
    unittest.main()

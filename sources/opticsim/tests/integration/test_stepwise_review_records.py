import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class StepwiseReviewRecordsTest(unittest.TestCase):
    def test_stepwise_review_record_builder(self):
        repo = Path(__file__).resolve().parents[2]
        script = repo / "records/stepwise_review_2026-05-22/06_figure_scripts/build_stepwise_review_records.py"
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "stepwise_review"

            result = subprocess.run(
                ["python3", str(script), "--repo-root", str(repo), "--out", str(out)],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertIn("wrote", result.stdout)
            expected_files = [
                "README.md",
                "00_review_map/review_map.md",
                "00_review_map/review_pipeline.png",
                "01_laue_barhoum_baseline/laue_barhoum_baseline.md",
                "01_laue_barhoum_baseline/implementation_manual.md",
                "01_laue_barhoum_baseline/code_commentary.md",
                "01_laue_barhoum_baseline/code_function_map.csv",
                "01_laue_barhoum_baseline/laue_multiring_scene.wrl",
                "01_laue_barhoum_baseline/laue_wrl_quicklook.png",
                "02_laue_darwin_guan_process/laue_darwin_guan_process.md",
                "02_laue_darwin_guan_process/implementation_manual.md",
                "02_laue_darwin_guan_process/code_commentary.md",
                "02_laue_darwin_guan_process/code_function_map.csv",
                "02_laue_darwin_guan_process/laue_multiring_scene.wrl",
                "02_laue_darwin_guan_process/guan_wrl_quicklook.png",
                "03_channel_wallbywall/channel_wallbywall.md",
                "03_channel_wallbywall/implementation_manual.md",
                "03_channel_wallbywall/code_commentary.md",
                "03_channel_wallbywall/code_function_map.csv",
                "03_channel_wallbywall/channel_wallbywall_scene.wrl",
                "03_channel_wallbywall/channel_wrl_quicklook.png",
                "04_detector_activation_bridge/detector_activation_bridge.md",
                "05_review_checklist/review_checklist.md",
            ]
            for rel_path in expected_files:
                self.assertTrue((out / rel_path).exists(), rel_path)

            manifest = json.loads((out / "00_review_map/review_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["status"], "PASS")
            self.assertIn("runs/channel_wallbywall_rebuild/summary.json", manifest["source_summaries"])

            guan_md = (out / "02_laue_darwin_guan_process/laue_darwin_guan_process.md").read_text(encoding="utf-8")
            self.assertIn("not a Geant4 toolkit patch", guan_md)
            self.assertIn("registered in Geant4 EM category", guan_md)

            channel_md = (out / "03_channel_wallbywall/channel_wallbywall.md").read_text(encoding="utf-8")
            self.assertIn("No-fudge closure", channel_md)
            self.assertIn("0.7615", channel_md)

            laue_manual = (out / "01_laue_barhoum_baseline/implementation_manual.md").read_text(encoding="utf-8")
            self.assertIn("MultiRingProcess::PostStepDoIt", laue_manual)
            self.assertIn("laue_multiring_scene.wrl", laue_manual)

            channel_manual = (out / "03_channel_wallbywall/implementation_manual.md").read_text(encoding="utf-8")
            self.assertIn("没有输入固定反射次数", channel_manual)
            self.assertIn("_trace_one_event", channel_manual)

            pngs = list(out.glob("*/*.png"))
            self.assertGreaterEqual(len(pngs), 10)
            for path in pngs:
                self.assertGreater(path.stat().st_size, 5000, str(path))


if __name__ == "__main__":
    unittest.main()

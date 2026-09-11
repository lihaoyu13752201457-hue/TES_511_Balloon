from __future__ import annotations

import re
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class TwoOpticsGroupMeetingMaterialsTest(unittest.TestCase):
    def test_deck_builds_with_expected_structure_and_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "two_optics_materials.html"
            subprocess.run(
                [
                    "python3",
                    "analysis/build_two_optics_group_meeting_materials.py",
                    "--out",
                    str(out.relative_to(ROOT)) if out.is_relative_to(ROOT) else str(out),
                ],
                cwd=ROOT,
                check=True,
            )
            text = out.read_text(encoding="utf-8")

        self.assertIn('<meta name="generator" content="html-slides v0.9.4">', text)
        self.assertIn('<div class="deck" id="deck">', text)
        self.assertIn("function goTo(index)", text)
        self.assertIn("function next()", text)
        self.assertIn("function prev()", text)
        self.assertIn("Channel 用公开 CAM511 物理复现性能量级", text)
        self.assertIn("Laue 用 Geant4 表驱动给出独立光学路线", text)
        self.assertIn("4.47 arcmin", text)
        self.assertIn("No correction factor", text)

        slide_ids = [int(item) for item in re.findall(r'data-slide="(\d+)"', text)]
        self.assertGreaterEqual(len(slide_ids), 25)
        self.assertEqual(slide_ids, list(range(len(slide_ids))))
        self.assertEqual(text.count('class="slide active"'), 1)


if __name__ == "__main__":
    unittest.main()

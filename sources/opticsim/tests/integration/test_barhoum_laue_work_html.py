from __future__ import annotations

import re
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class BarhoumLaueWorkHtmlTest(unittest.TestCase):
    def test_deck_builds_with_expected_structure_and_claims(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "barhoum_laue.html"
            subprocess.run(
                [
                    "python3",
                    "analysis/build_barhoum_laue_work_html.py",
                    "--out",
                    str(out),
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
        self.assertIn("Barhoum 的工作", text)
        self.assertIn("StronglyForced", text)
        self.assertIn("DBL_MAX", text)
        self.assertIn("Zachariasen/Darwin mosaic-crystal", text)
        self.assertIn("不是校正因子", text)
        self.assertIn("geant4_app/src/laue_multiring_table_demo.cc", text)
        self.assertIn("runs/laue_physics_confidence_audit/summary.json", text)
        self.assertIn("https://agenda.infn.it/event/21084/contributions/178539/", text)

        slide_ids = [int(item) for item in re.findall(r'data-slide="(\d+)"', text)]
        self.assertGreaterEqual(len(slide_ids), 14)
        self.assertEqual(slide_ids, list(range(len(slide_ids))))
        self.assertEqual(text.count('class="slide active"'), 1)


if __name__ == "__main__":
    unittest.main()

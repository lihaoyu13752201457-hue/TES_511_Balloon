from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from laue511.external_lens import (
    import_external_lens_hits,
    import_external_lens_observables,
    summarize_external_lens_observables,
)


class ExternalLensTest(unittest.TestCase):
    def test_import_external_lens_observables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            current = tmp_path / "current.json"
            python_ref = tmp_path / "python.json"
            external = tmp_path / "external.csv"
            current.write_text(
                json.dumps({"observed_diffracted_area_cm2": 0.568, "spot_d90_cm": 0.219}),
                encoding="utf-8",
            )
            python_ref.write_text(
                json.dumps({"diffracted_area_reference_cm2": 0.567}),
                encoding="utf-8",
            )
            _write_external_lens_csv(external)
            summary = import_external_lens_observables(
                external,
                tmp_path / "external_lens",
                current_observables_path=current,
                python_reference_path=python_ref,
            )
            self.assertTrue(summary["ok"], summary)
            self.assertAlmostEqual(summary["comparison"]["diffracted_area_minus_python_reference_cm2"], 0.001)
            self.assertTrue((tmp_path / "external_lens/external_lens_observables.csv").exists())

    def test_import_external_lens_hits(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            current = tmp_path / "current.json"
            python_ref = tmp_path / "python.json"
            hits = tmp_path / "hits.csv"
            current.write_text(
                json.dumps({"observed_diffracted_area_cm2": 1.50, "spot_d90_cm": 0.20}),
                encoding="utf-8",
            )
            python_ref.write_text(json.dumps({"diffracted_area_reference_cm2": 1.49}), encoding="utf-8")
            hits.write_text(
                "x_cm,y_cm,weight\n"
                "0.00,0.00,1\n"
                "0.05,0.00,1\n"
                "0.10,0.00,1\n",
                encoding="utf-8",
            )
            summary = import_external_lens_hits(
                hits,
                tmp_path / "external_lens",
                current_observables_path=current,
                python_reference_path=python_ref,
                geometric_area_cm2=2.0,
                incident_weight=4.0,
                source_tool="unit-hits",
                source_version="0",
            )
            self.assertTrue(summary["ok"], summary)
            self.assertAlmostEqual(summary["lens_metrics"]["diffracted_area_cm2"], 1.5)
            self.assertAlmostEqual(summary["lens_metrics"]["spot_d90_cm"], 0.2)
            self.assertEqual(summary["hit_summary"]["n_hits"], 3)
            self.assertTrue((tmp_path / "external_lens/external_lens_hits.csv").exists())
            self.assertTrue((tmp_path / "external_lens/external_lens_observables.csv").exists())

    def test_missing_required_lens_metric_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            current = tmp_path / "current.json"
            python_ref = tmp_path / "python.json"
            external = tmp_path / "external.csv"
            current.write_text(json.dumps({"observed_diffracted_area_cm2": 0.568, "spot_d90_cm": 0.219}), encoding="utf-8")
            python_ref.write_text(json.dumps({"diffracted_area_reference_cm2": 0.567}), encoding="utf-8")
            external.write_text(
                "scope,metric,value,unit,source_tool,source_version\n"
                "lens,diffracted_area_cm2,0.568,cm2,unit,0\n",
                encoding="utf-8",
            )
            summary = summarize_external_lens_observables(
                external,
                current_observables_path=current,
                python_reference_path=python_ref,
            )
            self.assertFalse(summary["ok"])
            self.assertIn("missing lens metrics", summary["errors"][0])

    def test_large_observable_delta_needs_attention(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            current = tmp_path / "current.json"
            python_ref = tmp_path / "python.json"
            external = tmp_path / "external.csv"
            current.write_text(json.dumps({"observed_diffracted_area_cm2": 0.568, "spot_d90_cm": 0.219}), encoding="utf-8")
            python_ref.write_text(json.dumps({"diffracted_area_reference_cm2": 0.567}), encoding="utf-8")
            _write_external_lens_csv(external, diffracted_area_cm2=0.80, spot_d90_cm=0.50)
            summary = summarize_external_lens_observables(
                external,
                current_observables_path=current,
                python_reference_path=python_ref,
            )
            self.assertFalse(summary["ok"])
            self.assertFalse(summary["agreement_checks"]["diffracted_area_vs_current"])
            self.assertFalse(summary["agreement_checks"]["spot_d90_vs_current"])


def _write_external_lens_csv(path: Path, *, diffracted_area_cm2: float = 0.568, spot_d90_cm: float = 0.220) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["scope", "metric", "value", "unit", "source_tool", "source_version"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "scope": "lens",
                "metric": "diffracted_area_cm2",
                "value": str(diffracted_area_cm2),
                "unit": "cm2",
                "source_tool": "unit",
                "source_version": "0",
            }
        )
        writer.writerow(
            {
                "scope": "lens",
                "metric": "spot_d90_cm",
                "value": str(spot_d90_cm),
                "unit": "cm",
                "source_tool": "unit",
                "source_version": "0",
            }
        )


if __name__ == "__main__":
    unittest.main()

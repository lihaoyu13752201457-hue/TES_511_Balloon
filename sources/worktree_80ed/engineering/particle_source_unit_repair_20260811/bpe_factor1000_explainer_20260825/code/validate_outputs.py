#!/usr/bin/env python3
"""Lightweight numerical checks for the two BPE explainer figures."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
OUT = PACKAGE / "outputs"


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    provenance = json.loads((OUT / "provenance.json").read_text(encoding="utf-8"))
    assert provenance["status"] == "PASS__TWO_NON_MANUSCRIPT_BPE_FACTOR1000_EXPLAINER_FIGURES"
    for name in provenance["outputs"]:
        path = OUT / name
        assert path.exists() and path.stat().st_size > 0, path

    expected = {"Cu61": 0.8847553386855578, "Cu62": 0.8421455746190778, "Cu64": 0.8965602431961425}
    integrated = read_csv(OUT / "integrated_cu_indices.csv")
    for product, target in expected.items():
        row = next(
            item
            for item in integrated
            if item["scenario"] == "corrected_transport"
            and item["stage"] == "output"
            and item["product"] == product
        )
        assert math.isclose(float(row["output_over_input"]), target, rel_tol=0.0, abs_tol=1.0e-12)

    for value in provenance["corrected_kernel_closure_factors"].values():
        assert abs(float(value) - 1.0) < 0.02

    spectra = read_csv(OUT / "spectra_for_figures.csv")
    lookup = {(row["scenario"], row["stage"], row["energy_center_keV"]): row for row in spectra}
    current_total = 0.0
    legacy_total = 0.0
    for row in spectra:
        lo = float(row["energy_lo_keV"])
        hi = float(row["energy_hi_keV"])
        contribution = float(row["rate_per_decade_s-1"]) * math.log10(hi / lo)
        if row["scenario"] == "corrected_transport" and row["stage"] == "input":
            current_total += contribution
        if row["scenario"] == "factor1000_proxy" and row["stage"] == "input":
            legacy_total += contribution
        if row["scenario"] == "factor1000_proxy" and row["stage"] == "output":
            before = lookup[("factor1000_proxy", "input", row["energy_center_keV"])]
            assert float(row["rate_per_decade_s-1"]) <= float(before["rate_per_decade_s-1"]) + 1.0e-12
    assert math.isclose(current_total, legacy_total, rel_tol=1.0e-12, abs_tol=1.0e-9)

    print(
        json.dumps(
            {
                "status": "PASS",
                "corrected_vs_factor1000_integrated_input_current": [current_total, legacy_total],
                "max_kernel_closure_deviation": max(
                    abs(float(value) - 1.0)
                    for value in provenance["corrected_kernel_closure_factors"].values()
                ),
                "corrected_ratios": expected,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

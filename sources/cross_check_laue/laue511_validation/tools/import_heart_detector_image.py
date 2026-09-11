#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from laue511.external_lens import import_external_lens_hits


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, help="HEART HDF5 output file")
    parser.add_argument("--out-dir", default=str(ROOT / "benchmarks/reference_outputs/external_lens_observables"))
    parser.add_argument("--current-observables", default=str(ROOT / "reports/full_lens_observables/metrics.json"))
    parser.add_argument("--python-reference", default=str(ROOT / "reports/python_full_lens_reference/metrics.json"))
    parser.add_argument("--geometric-area-cm2", type=float)
    parser.add_argument("--incident-weight", type=float)
    parser.add_argument("--image-dataset", default="Results/detector_image")
    parser.add_argument("--detector-l-dataset", default="Detector/detector_L_pos")
    parser.add_argument("--detector-w-dataset", default="Detector/detector_W_pos")
    args = parser.parse_args()

    geometric_area = args.geometric_area_cm2
    if geometric_area is None:
        current = json.loads(Path(args.current_observables).read_text(encoding="utf-8"))
        geometric_area = float(current["geometric_area_cm2"])

    with tempfile.TemporaryDirectory(prefix="laue511_heart_h5_") as tmp:
        tmp_path = Path(tmp)
        hits_csv = tmp_path / "heart_detector_hits.csv"
        h5_summary = heart_detector_image_to_hits(
            args.input,
            hits_csv,
            image_dataset=args.image_dataset,
            detector_l_dataset=args.detector_l_dataset,
            detector_w_dataset=args.detector_w_dataset,
        )
        incident_weight = args.incident_weight
        if incident_weight is None:
            incident_weight = float(h5_summary["number_of_photons"])

        summary = import_external_lens_hits(
            hits_csv,
            args.out_dir,
            current_observables_path=args.current_observables,
            python_reference_path=args.python_reference,
            geometric_area_cm2=geometric_area,
            incident_weight=incident_weight,
            position_unit="mm",
            x_column="x_mm",
            y_column="y_mm",
            source_tool="HEART-detector-image",
            source_version=str(h5_summary["heart_version"]),
        )
        summary["heart_hdf5"] = h5_summary

    _write_readme(Path(args.out_dir), summary)
    Path(args.out_dir, "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if summary["ok"] else 1


def heart_detector_image_to_hits(
    input_path: str | Path,
    output_csv: str | Path,
    *,
    image_dataset: str = "Results/detector_image",
    detector_l_dataset: str = "Detector/detector_L_pos",
    detector_w_dataset: str = "Detector/detector_W_pos",
) -> dict[str, object]:
    import h5py

    input_path = Path(input_path)
    output_csv = Path(output_csv)
    with h5py.File(input_path, "r") as h5:
        image = h5[image_dataset][()]
        l_pos = h5[detector_l_dataset][()]
        w_pos = h5[detector_w_dataset][()]
        if image.shape != (len(w_pos), len(l_pos)):
            raise ValueError(
                f"detector image shape {image.shape} does not match W/L axes {(len(w_pos), len(l_pos))}"
            )
        version = _scalar_text(h5["Version"][()]) if "Version" in h5 else "unknown"
        number_of_photons = float(h5["Diagnostics/Number_of_Photons"][()])
        detector_hit_model = (
            _scalar_text(h5["Diagnostics/Detector_Hit_Model"][()])
            if "Diagnostics/Detector_Hit_Model" in h5
            else "heart"
        )
        source_jitter_mm = (
            float(h5["Diagnostics/Source_Jitter_mm"][()])
            if "Diagnostics/Source_Jitter_mm" in h5
            else None
        )

    n_pixels = 0
    total_weight = 0.0
    with output_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["x_mm", "y_mm", "weight"])
        writer.writeheader()
        for w_index, y_mm in enumerate(w_pos):
            for l_index, x_mm in enumerate(l_pos):
                weight = float(image[w_index, l_index])
                if weight <= 0.0:
                    continue
                writer.writerow({"x_mm": x_mm, "y_mm": y_mm, "weight": weight})
                n_pixels += 1
                total_weight += weight

    return {
        "input_hdf5": str(input_path),
        "heart_version": version,
        "image_dataset": image_dataset,
        "detector_l_dataset": detector_l_dataset,
        "detector_w_dataset": detector_w_dataset,
        "image_shape": list(image.shape),
        "number_of_photons": number_of_photons,
        "nonzero_detector_pixels": n_pixels,
        "detector_weight": total_weight,
        "detector_hit_model": detector_hit_model,
        "source_jitter_mm": source_jitter_mm,
    }


def _scalar_text(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode()
    return str(value)


def _write_readme(out_dir: Path, summary: dict[str, object]) -> None:
    lines = [
        "# External Lens Observables",
        "",
        "Imported from a HEART detector-image HDF5 file.",
        "",
        f"- ok: {summary['ok']}",
    ]
    heart = summary.get("heart_hdf5", {})
    if isinstance(heart, dict):
        lines.extend(
            [
                f"- HEART version: {heart.get('heart_version')}",
                f"- detector pixels with weight: {heart.get('nonzero_detector_pixels')}",
                f"- detector weight: {heart.get('detector_weight')}",
                f"- incident photons: {heart.get('number_of_photons')}",
                f"- detector hit model: {heart.get('detector_hit_model')}",
            ]
        )
    if summary.get("ok"):
        lens = summary["lens_metrics"]
        lines.extend(
            [
                f"- diffracted area: {lens['diffracted_area_cm2']:.6g} cm2",
                f"- spot d90: {lens['spot_d90_cm']:.6g} cm",
            ]
        )
    out_dir.joinpath("README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())

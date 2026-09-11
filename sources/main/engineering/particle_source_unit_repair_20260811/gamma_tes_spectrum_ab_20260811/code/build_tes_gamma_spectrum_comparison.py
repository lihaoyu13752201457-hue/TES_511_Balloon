#!/usr/bin/env python3
"""Build raw and measured TES gamma-spectrum A/B figures.

The A arm is the validated corrected-keV batch0001 instant gamma transport.
The B arm is the fresh, isolated historical factor-1000-axis control.  TES
energy is aggregated per primary and per TES pixel before applying the current
420 eV FWHM / 0.3 keV pixel-threshold response proxy.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


def find_root(path: Path) -> Path:
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists() and (candidate / "AGENTS.md").is_file():
            return candidate
    raise RuntimeError("repository root not found")


THIS_FILE = Path(__file__).resolve()
ROOT = find_root(THIS_FILE.parent)
PACKAGE = THIS_FILE.parents[1]
RUN_ROOT = ROOT / "runs/particle_source_unit_repair_20260811/gamma_tes_spectrum_ab_20260811"
CURRENT_LEDGER = ROOT / "runs/particle_source_unit_repair_20260811/seven_family_batch0001_v1_ledger.json"
LEGACY_VALIDATION = RUN_ROOT / "legacy_axis_gamma_control_validation.json"
DATA_DIR = PACKAGE / "data"
FIGURE_DIR = PACKAGE / "figures"
EVENT_CSV = DATA_DIR / "tes_gamma_axis_ab_detected_events.csv.gz"
HISTOGRAM_CSV = DATA_DIR / "tes_gamma_axis_ab_histograms.csv"
SUMMARY_JSON = DATA_DIR / "tes_gamma_axis_ab_summary.json"
CHART_CONTRACT_JSON = DATA_DIR / "chart_contract.json"
MEASURED_FIGURE_PNG = FIGURE_DIR / "tes_gamma_axis_ab_measured.png"
MEASURED_FIGURE_SVG = FIGURE_DIR / "tes_gamma_axis_ab_measured.svg"
RAW_FIGURE_PNG = FIGURE_DIR / "tes_gamma_axis_ab_raw.png"
RAW_FIGURE_SVG = FIGURE_DIR / "tes_gamma_axis_ab_raw.svg"
VALIDATION_JSON = DATA_DIR / "tes_gamma_axis_ab_analysis_validation.json"

AUTHORITY = "PROMPT_GAMMA_TES_TRANSFER_DIAGNOSTIC__NOT_STEP05_AUTHORITY"
GEOMETRY_ORDER = ("mass_model_511", "s3d_o8")
ARM_ORDER = ("legacy_bug_axis", "corrected_keV")
ARM_LABELS = {
    "legacy_bug_axis": "Legacy bug axis (E/1000)",
    "corrected_keV": "Corrected keV axis",
}
GEOMETRY_LABELS = {"mass_model_511": "Mass_model_511", "s3d_o8": "S3d-O8"}
COLORS = {"legacy_bug_axis": "#D55E00", "corrected_keV": "#0072B2"}
LINESTYLES = {"legacy_bug_axis": "--", "corrected_keV": "-"}

TES_RE = re.compile(r"^TP_L(?P<layer>[0-5])_(?P<pixel>\d+)$", re.IGNORECASE)
CC_HIT_RE = re.compile(r"^CC\s+HIT\s+(\S+)\s+(.*)$")
KV_RE = re.compile(r"(\w+)=([^\s]+)")
ID_RE = re.compile(r"^ID\s+(\d+)")
FWHM_KEV = 0.420
GAUSSIAN_SIGMA_KEV = FWHM_KEV / 2.3548200450309493
PIXEL_THRESHOLD_KEV = 0.3
RESPONSE_SEEDS = {
    ("mass_model_511", "legacy_bug_axis"): 2_605_110_101,
    ("mass_model_511", "corrected_keV"): 2_605_110_102,
    ("s3d_o8", "legacy_bug_axis"): 2_605_110_201,
    ("s3d_o8", "corrected_keV"): 2_605_110_202,
}

BROAD_EDGES = 10.0 ** __import__("numpy").arange(-2.0, 5.0001, 0.5)
LOW_EDGES = __import__("numpy").arange(0.0, 2.0001, 0.1)
ZOOM_EDGES = __import__("numpy").arange(480.0, 550.0001, 2.0)


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


@dataclass
class EventRecord:
    geometry: str
    arm: str
    shard: str
    local_id: int
    raw_keV: float
    measured_keV: float
    raw_pixels: int
    measured_pixels: int


@dataclass
class Dataset:
    geometry: str
    arm: str
    primary_count: int
    sum_TT_s: float
    records: list[EventRecord]
    sim_inputs: list[dict[str, Any]]

    def positive(self, response: str):
        import numpy as np

        values = [
            record.raw_keV if response == "raw" else record.measured_keV
            for record in self.records
            if (record.raw_keV if response == "raw" else record.measured_keV) > 0.0
        ]
        return np.asarray(values, dtype=np.float64)


def parse_sim(
    path: Path,
    geometry: str,
    arm: str,
    rng,
) -> tuple[int, list[EventRecord]]:
    current_id: int | None = None
    expected_next_id = 1
    pixels: dict[str, float] = {}
    primary_count = 0
    records: list[EventRecord] = []

    def flush() -> None:
        nonlocal current_id, pixels
        if current_id is None:
            return
        raw_energies = [energy for _, energy in sorted(pixels.items()) if energy > 0.0]
        raw_total = math.fsum(raw_energies)
        measured_energies: list[float] = []
        for energy in raw_energies:
            measured = float(energy + rng.normal(0.0, GAUSSIAN_SIGMA_KEV))
            if measured >= PIXEL_THRESHOLD_KEV:
                measured_energies.append(measured)
        measured_total = math.fsum(measured_energies)
        if raw_total > 0.0 or measured_total > 0.0:
            records.append(
                EventRecord(
                    geometry=geometry,
                    arm=arm,
                    shard=path.name,
                    local_id=int(current_id),
                    raw_keV=raw_total,
                    measured_keV=measured_total,
                    raw_pixels=len(raw_energies),
                    measured_pixels=len(measured_energies),
                )
            )
        current_id = None
        pixels = {}

    with gzip.open(path, "rt", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            if line == "SE":
                flush()
                continue
            match_id = ID_RE.match(line)
            if match_id:
                if current_id is not None:
                    raise RuntimeError(f"{rel(path)}: ID before previous event SE")
                current_id = int(match_id.group(1))
                if current_id != expected_next_id:
                    raise RuntimeError(
                        f"{rel(path)}: ID sequence got {current_id}, expected {expected_next_id}"
                    )
                expected_next_id += 1
                primary_count += 1
                continue
            if not line.startswith("CC HIT "):
                continue
            match_hit = CC_HIT_RE.match(line)
            if not match_hit or current_id is None:
                continue
            volume = match_hit.group(1)
            if not TES_RE.match(volume):
                continue
            values = dict(KV_RE.findall(match_hit.group(2)))
            try:
                energy = float(values["edep_keV"])
            except (KeyError, ValueError):
                raise RuntimeError(f"{rel(path)}: malformed TES CC HIT") from None
            if not math.isfinite(energy) or energy < 0.0:
                raise RuntimeError(f"{rel(path)}: invalid TES deposit {energy}")
            pixels[volume] = pixels.get(volume, 0.0) + energy
    flush()
    return primary_count, records


def current_inputs(ledger: dict[str, Any], geometry: str) -> tuple[list[dict[str, Any]], float]:
    campaigns = [
        item
        for item in ledger.get("campaigns", [])
        if item.get("geometry") == geometry and item.get("mode") == "instant"
    ]
    if len(campaigns) != 1:
        raise RuntimeError(f"current ledger has {len(campaigns)} instant campaigns for {geometry}")
    jobs = [item for item in campaigns[0]["jobs"] if item.get("family") == "gamma"]
    jobs.sort(key=lambda item: item["job_name"])
    if len(jobs) != 4 or sum(int(item["events"]) for item in jobs) != 100_000:
        raise RuntimeError(f"{geometry}: current gamma input is not 100,000 primaries")
    records: list[dict[str, Any]] = []
    tt = 0.0
    for job in jobs:
        sim = ROOT / job["sim"]
        if not sim.is_file() or sha256(sim) != job["sim_sha256"]:
            raise RuntimeError(f"corrected SIM hash drift: {job['sim']}")
        tt += float(job["TT_s_from_isotope_dat"])
        records.append(
            {
                "path": rel(sim),
                "sha256": job["sim_sha256"],
                "events": int(job["events"]),
                "seed": int(job["seed"]),
                "TT_s": float(job["TT_s_from_isotope_dat"]),
            }
        )
    return records, tt


def legacy_inputs(validation: dict[str, Any], geometry: str) -> tuple[list[dict[str, Any]], float]:
    jobs = [item for item in validation.get("jobs", []) if item.get("geometry") == geometry]
    jobs.sort(key=lambda item: item["job_name"])
    if len(jobs) != 4 or sum(int(item["events"]) for item in jobs) != 100_000:
        raise RuntimeError(f"{geometry}: legacy gamma input is not 100,000 primaries")
    records: list[dict[str, Any]] = []
    tt = 0.0
    for job in jobs:
        sim = ROOT / job["sim"]
        if not sim.is_file() or sha256(sim) != job["sim_sha256"]:
            raise RuntimeError(f"legacy SIM hash drift: {job['sim']}")
        value = float(job["isotope_store"]["TT_s"])
        tt += value
        records.append(
            {
                "path": rel(sim),
                "sha256": job["sim_sha256"],
                "events": int(job["events"]),
                "seed": int(job["seed"]),
                "TT_s": value,
            }
        )
    return records, tt


def build_dataset(geometry: str, arm: str, inputs: list[dict[str, Any]], sum_tt: float) -> Dataset:
    import numpy as np

    rng = np.random.default_rng(RESPONSE_SEEDS[(geometry, arm)])
    total_primaries = 0
    records: list[EventRecord] = []
    for item in inputs:
        count, parsed = parse_sim(ROOT / item["path"], geometry, arm, rng)
        if count != int(item["events"]):
            raise RuntimeError(f"{item['path']}: parsed {count} primaries, expected {item['events']}")
        total_primaries += count
        records.extend(parsed)
    if total_primaries != 100_000:
        raise RuntimeError(f"{geometry}/{arm}: total primaries={total_primaries}, expected 100000")
    return Dataset(geometry, arm, total_primaries, sum_tt, records, inputs)


def wilson_interval(successes: int, total: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if total <= 0:
        return (math.nan, math.nan)
    p = successes / total
    denom = 1.0 + z * z / total
    center = (p + z * z / (2.0 * total)) / denom
    half = z * math.sqrt(p * (1.0 - p) / total + z * z / (4.0 * total * total)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def garwood(count: int, alpha: float = 0.05) -> tuple[float, float]:
    from scipy.stats import chi2

    low = 0.0 if count == 0 else 0.5 * float(chi2.ppf(alpha / 2.0, 2 * count))
    high = 0.5 * float(chi2.ppf(1.0 - alpha / 2.0, 2 * (count + 1)))
    return low, high


def dataset_summary(dataset: Dataset, response: str) -> dict[str, Any]:
    import numpy as np

    values = dataset.positive(response)
    detected = int(values.size)
    low, high = wilson_interval(detected, dataset.primary_count)
    w2 = int(np.count_nonzero((values >= 510.58) & (values <= 511.42)))
    broad511 = int(np.count_nonzero((values >= 480.0) & (values <= 550.0)))
    broad_underflow = int(np.count_nonzero(values < BROAD_EDGES[0]))
    broad_overflow = int(np.count_nonzero(values >= BROAD_EDGES[-1]))
    return {
        "geometry": dataset.geometry,
        "arm": dataset.arm,
        "response": response,
        "primary_count": dataset.primary_count,
        "sum_TT_s": dataset.sum_TT_s,
        "detected_events": detected,
        "detection_efficiency": detected / dataset.primary_count,
        "detection_efficiency_wilson95": [low, high],
        "detected_rate_per_s": detected / dataset.sum_TT_s,
        "events_480_550_keV": broad511,
        "events_510p58_511p42_keV": w2,
        "broad_histogram_underflow_below_0p01_keV": broad_underflow,
        "broad_histogram_overflow_at_or_above_100MeV": broad_overflow,
        "minimum_positive_keV": float(values.min()) if detected else None,
        "median_positive_keV": float(np.median(values)) if detected else None,
        "maximum_positive_keV": float(values.max()) if detected else None,
        "response_seed": RESPONSE_SEEDS[(dataset.geometry, dataset.arm)] if response == "measured" else None,
    }


def histogram_rows(datasets: Iterable[Dataset]) -> list[dict[str, Any]]:
    import numpy as np

    rows: list[dict[str, Any]] = []
    views = {
        "broad_log": (BROAD_EDGES, "log10_keV"),
        "low_0_2keV": (LOW_EDGES, "keV"),
        "zoom_480_550keV": (ZOOM_EDGES, "keV"),
    }
    for dataset in datasets:
        for response in ("raw", "measured"):
            values = dataset.positive(response)
            for view, (edges, width_unit) in views.items():
                counts, _ = np.histogram(values, bins=edges)
                transformed = np.log10(edges) if width_unit == "log10_keV" else edges
                widths = np.diff(transformed)
                for index, count_value in enumerate(counts):
                    count = int(count_value)
                    poisson_low, poisson_high = garwood(count)
                    width = float(widths[index])
                    scale = 100_000.0 / dataset.primary_count
                    rows.append(
                        {
                            "geometry": dataset.geometry,
                            "arm": dataset.arm,
                            "response": response,
                            "view": view,
                            "bin_index": index,
                            "energy_low_keV": float(edges[index]),
                            "energy_high_keV": float(edges[index + 1]),
                            "width_unit": width_unit,
                            "bin_width": width,
                            "count": count,
                            "count_garwood95_low": poisson_low,
                            "count_garwood95_high": poisson_high,
                            "events_per_100k_primaries_per_width": count * scale / width,
                            "events_per_100k_garwood95_low_per_width": poisson_low * scale / width,
                            "events_per_100k_garwood95_high_per_width": poisson_high * scale / width,
                            "rate_per_s_per_width": count / dataset.sum_TT_s / width,
                        }
                    )
    return rows


def write_event_csv(datasets: Iterable[Dataset]) -> None:
    EVENT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(EVENT_CSV, "wt", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=(
                "geometry",
                "arm",
                "shard",
                "local_id",
                "raw_keV",
                "measured_keV",
                "raw_pixels",
                "measured_pixels",
            ),
        )
        writer.writeheader()
        for dataset in datasets:
            for record in dataset.records:
                writer.writerow(record.__dict__)


def write_histogram_csv(rows: list[dict[str, Any]]) -> None:
    HISTOGRAM_CSV.parent.mkdir(parents=True, exist_ok=True)
    with HISTOGRAM_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def plot_response(datasets: list[Dataset], response: str, png: Path, svg: Path) -> None:
    mpl_cache = Path("/tmp/tes_gamma_ab_mplconfig")
    mpl_cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("MPLCONFIGDIR", str(mpl_cache))
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    fig, axes = plt.subplots(2, 3, figsize=(16.0, 8.4), constrained_layout=True)
    for row_index, geometry in enumerate(GEOMETRY_ORDER):
        geometry_sets = {item.arm: item for item in datasets if item.geometry == geometry}
        for arm in ARM_ORDER:
            dataset = geometry_sets[arm]
            values = dataset.positive(response)
            label = ARM_LABELS[arm]
            color = COLORS[arm]
            linestyle = LINESTYLES[arm]

            broad_counts, _ = np.histogram(values, bins=BROAD_EDGES)
            broad_y = broad_counts * (100_000.0 / dataset.primary_count) / np.diff(np.log10(BROAD_EDGES))
            broad_y = np.where(broad_y > 0.0, broad_y, np.nan)
            axes[row_index, 0].stairs(
                broad_y,
                BROAD_EDGES,
                color=color,
                linestyle=linestyle,
                linewidth=2.0,
                label=label,
            )

            for column, edges in ((1, LOW_EDGES), (2, ZOOM_EDGES)):
                counts, _ = np.histogram(values, bins=edges)
                centers = 0.5 * (edges[:-1] + edges[1:])
                y = counts * (100_000.0 / dataset.primary_count)
                low = np.asarray([garwood(int(value))[0] for value in counts]) * (
                    100_000.0 / dataset.primary_count
                )
                high = np.asarray([garwood(int(value))[1] for value in counts]) * (
                    100_000.0 / dataset.primary_count
                )
                axes[row_index, column].stairs(
                    y,
                    edges,
                    color=color,
                    linestyle=linestyle,
                    linewidth=1.5,
                    label=label,
                )
                mask = counts > 0
                axes[row_index, column].errorbar(
                    centers[mask],
                    y[mask],
                    yerr=np.vstack((y[mask] - low[mask], high[mask] - y[mask])),
                    color=color,
                    linestyle="none",
                    marker="o" if arm == "corrected_keV" else "s",
                    markersize=4.0,
                    capsize=2.0,
                )

        broad = axes[row_index, 0]
        broad.set_xscale("log")
        broad.set_yscale("log")
        broad.set_xlim(BROAD_EDGES[0], BROAD_EDGES[-1])
        broad.set_ylim(bottom=0.5)
        broad.set_ylabel(f"{GEOMETRY_LABELS[geometry]}\nTES events / 100k / decade")
        broad.grid(True, which="both", alpha=0.18)
        axes[row_index, 1].axvline(0.510999, color="#666666", linewidth=1.0, alpha=0.7)
        axes[row_index, 1].set_xlim(0.0, 2.0)
        low_total = sum(
            int(np.count_nonzero((geometry_sets[arm].positive(response) >= 0.0) & (geometry_sets[arm].positive(response) < 2.0)))
            for arm in ARM_ORDER
        )
        if low_total == 0:
            axes[row_index, 1].text(
                0.5,
                0.5,
                "No TES events in either 100k sample",
                transform=axes[row_index, 1].transAxes,
                ha="center",
                va="center",
                fontsize=10,
                color="#444444",
            )
            axes[row_index, 1].set_ylim(0.0, 1.0)
        axes[row_index, 1].grid(True, alpha=0.18)
        axes[row_index, 2].axvspan(510.58, 511.42, color="#999999", alpha=0.18, linewidth=0)
        axes[row_index, 2].axvline(510.999, color="#666666", linewidth=1.0, alpha=0.7)
        axes[row_index, 2].set_xlim(480.0, 550.0)
        axes[row_index, 2].grid(True, alpha=0.18)
        if row_index == 0:
            broad.set_title("Full TES spectrum")
            axes[row_index, 1].set_title("Legacy 0.511-keV region")
            axes[row_index, 2].set_title("Physical 511-keV region")
            broad.legend(frameon=False, fontsize=9)
        if row_index == 1:
            broad.set_xlabel("TES event energy (keV)")
            axes[row_index, 1].set_xlabel("TES event energy (keV)")
            axes[row_index, 2].set_xlabel("TES event energy (keV)")
        axes[row_index, 1].set_ylabel("TES events / 100k / 0.1 keV")
        axes[row_index, 2].set_ylabel("TES events / 100k / 2 keV")

    response_title = (
        "TES measured spectrum: 420 eV FWHM per pixel + 0.3 keV pixel threshold"
        if response == "measured"
        else "TES raw transport spectrum: event-summed D1-D6 pixel energy deposits"
    )
    fig.suptitle(
        response_title
        + "\n100,000 gamma primaries per arm and geometry; prompt-only, no veto/FoV/Step05 cuts",
        fontsize=13,
    )
    fig.savefig(png, dpi=180, facecolor="white")
    fig.savefig(svg, facecolor="white")
    plt.close(fig)


def main() -> int:
    errors: list[str] = []
    if not CURRENT_LEDGER.is_file() or not LEGACY_VALIDATION.is_file():
        raise SystemExit("missing corrected ledger or legacy-control validation")
    current_ledger = json.loads(CURRENT_LEDGER.read_text(encoding="utf-8"))
    legacy_validation = json.loads(LEGACY_VALIDATION.read_text(encoding="utf-8"))
    if current_ledger.get("status") != "PASS__BATCH0001_MERGE_ELIGIBLE":
        raise SystemExit("corrected batch0001 ledger is not PASS")
    if legacy_validation.get("status") != "PASS__LEGACY_AXIS_DIAGNOSTIC_ONLY__NON_MERGEABLE":
        raise SystemExit("legacy diagnostic validation is not PASS")

    datasets: list[Dataset] = []
    for geometry in GEOMETRY_ORDER:
        legacy_files, legacy_tt = legacy_inputs(legacy_validation, geometry)
        corrected_files, corrected_tt = current_inputs(current_ledger, geometry)
        datasets.append(build_dataset(geometry, "legacy_bug_axis", legacy_files, legacy_tt))
        datasets.append(build_dataset(geometry, "corrected_keV", corrected_files, corrected_tt))

    summaries = [
        dataset_summary(dataset, response)
        for dataset in datasets
        for response in ("raw", "measured")
    ]
    rows = histogram_rows(datasets)
    write_event_csv(datasets)
    write_histogram_csv(rows)
    plot_response(datasets, "measured", MEASURED_FIGURE_PNG, MEASURED_FIGURE_SVG)
    plot_response(datasets, "raw", RAW_FIGURE_PNG, RAW_FIGURE_SVG)

    measured_lookup = {
        (item["geometry"], item["arm"]): item
        for item in summaries
        if item["response"] == "measured"
    }
    efficiency_ratios: dict[str, float | None] = {}
    for geometry in GEOMETRY_ORDER:
        old = measured_lookup[(geometry, "legacy_bug_axis")]["detection_efficiency"]
        new = measured_lookup[(geometry, "corrected_keV")]["detection_efficiency"]
        efficiency_ratios[geometry] = new / old if old > 0.0 else None

    summary = {
        "schema_version": 1,
        "status": "PASS__PROMPT_GAMMA_TES_TRANSFER_DIAGNOSTIC",
        "authority": AUTHORITY,
        "physics_authority": False,
        "step05_authority": False,
        "comparison": "corrected-keV axis versus isolated historical E/1000 bug-axis gamma control",
        "primary_count_per_geometry_arm": 100_000,
        "tes_definition": (
            "Within each primary, sum CC HIT edep_keV by TP_L0..TP_L5 pixel UID, then sum pixels. "
            "BGO, plastic, silicon substrate, and support volumes are excluded."
        ),
        "measured_response": {
            "fwhm_keV_per_pixel": FWHM_KEV,
            "gaussian_sigma_keV_per_pixel": GAUSSIAN_SIGMA_KEV,
            "post_noise_pixel_threshold_keV": PIXEL_THRESHOLD_KEV,
            "response_seeds": {f"{key[0]}/{key[1]}": value for key, value in RESPONSE_SEEDS.items()},
            "boundary": "single reproducible response realization; not an MC uncertainty band",
        },
        "selection_boundary": (
            "prompt gamma only; no BGO/plastic veto, no Compton/FoV, no 1 us coincidence, "
            "and no W2 selection"
        ),
        "gamma_model_boundary": "total gamma spectrum only; no additional mono-511 component",
        "inputs": {
            "corrected_ledger": rel(CURRENT_LEDGER),
            "corrected_ledger_sha256": sha256(CURRENT_LEDGER),
            "legacy_validation": rel(LEGACY_VALIDATION),
            "legacy_validation_sha256": sha256(LEGACY_VALIDATION),
            "datasets": [
                {
                    "geometry": dataset.geometry,
                    "arm": dataset.arm,
                    "primary_count": dataset.primary_count,
                    "sum_TT_s": dataset.sum_TT_s,
                    "sim_inputs": dataset.sim_inputs,
                }
                for dataset in datasets
            ],
        },
        "results": summaries,
        "measured_detection_efficiency_corrected_over_legacy": efficiency_ratios,
        "outputs": {
            "event_level_detected_csv_gz": rel(EVENT_CSV),
            "histogram_csv": rel(HISTOGRAM_CSV),
            "measured_figure_png": rel(MEASURED_FIGURE_PNG),
            "measured_figure_svg": rel(MEASURED_FIGURE_SVG),
            "raw_figure_png": rel(RAW_FIGURE_PNG),
            "raw_figure_svg": rel(RAW_FIGURE_SVG),
        },
        "low_statistics_warning": (
            "Only about O(100) corrected events per 100,000 primaries reach TES; detailed bin-level "
            "structure and the 511-keV zoom are Poisson limited."
        ),
    }
    atomic_json(SUMMARY_JSON, summary)

    takeaway_parts = []
    for geometry in GEOMETRY_ORDER:
        old = measured_lookup[(geometry, "legacy_bug_axis")]["detected_events"]
        new = measured_lookup[(geometry, "corrected_keV")]["detected_events"]
        takeaway_parts.append(f"{GEOMETRY_LABELS[geometry]}: {old} legacy vs {new} corrected TES events")
    chart_contract = {
        "schema_version": 1,
        "analytical_question": (
            "At equal 100,000-primary statistics, how does restoring the atmospheric gamma energy axis "
            "from E/1000 to keV change the event-summed TES spectrum in the two retained geometries?"
        ),
        "one_sentence_takeaway": "; ".join(takeaway_parts) + ".",
        "chart_family": "distribution / histogram",
        "facets": "rows are geometry; columns are full range, 0-2 keV, and 480-550 keV",
        "x": "event-summed TES energy in keV",
        "y": "TES-hit events per 100,000 primaries per plotted bin width",
        "series": [ARM_LABELS[arm] for arm in ARM_ORDER],
        "uncertainty": "95% Garwood Poisson intervals in the two linear zoom panels",
        "filters": "prompt gamma only; no veto/FoV/Step05 cuts",
        "data_availability": "event-level detected-event table plus fixed-bin histogram CSV",
    }
    atomic_json(CHART_CONTRACT_JSON, chart_contract)

    required_outputs = (
        EVENT_CSV,
        HISTOGRAM_CSV,
        SUMMARY_JSON,
        CHART_CONTRACT_JSON,
        MEASURED_FIGURE_PNG,
        MEASURED_FIGURE_SVG,
        RAW_FIGURE_PNG,
        RAW_FIGURE_SVG,
    )
    for path in required_outputs:
        if not path.is_file() or path.stat().st_size <= 0:
            errors.append(f"missing/empty output: {rel(path)}")
    summary_by_key = {
        (item["geometry"], item["arm"], item["response"]): item for item in summaries
    }
    histogram_closure = True
    for dataset in datasets:
        for response in ("raw", "measured"):
            values = dataset.positive(response)
            in_range = int(__import__("numpy").count_nonzero((values >= BROAD_EDGES[0]) & (values < BROAD_EDGES[-1])))
            broad_count = sum(
                int(row["count"])
                for row in rows
                if row["geometry"] == dataset.geometry
                and row["arm"] == dataset.arm
                and row["response"] == response
                and row["view"] == "broad_log"
            )
            record = summary_by_key[(dataset.geometry, dataset.arm, response)]
            histogram_closure &= broad_count == in_range
            histogram_closure &= (
                broad_count
                + int(record["broad_histogram_underflow_below_0p01_keV"])
                + int(record["broad_histogram_overflow_at_or_above_100MeV"])
                == int(record["detected_events"])
            )
    try:
        from PIL import Image

        image_qa = {}
        for path in (MEASURED_FIGURE_PNG, RAW_FIGURE_PNG):
            with Image.open(path) as figure:
                figure.verify()
            with Image.open(path) as figure:
                image_qa[rel(path)] = {"format": figure.format, "width": figure.width, "height": figure.height}
        figures_readable = all(item["width"] >= 2000 and item["height"] >= 1000 for item in image_qa.values())
    except Exception as exc:
        figures_readable = False
        image_qa = {"error": str(exc)}
        errors.append(f"figure readability QA failed: {exc}")
    if not histogram_closure:
        errors.append("broad histogram count/underflow/overflow closure failed")
    corrected_hashes_match = all(
        sha256(ROOT / item["path"]) == item["sha256"]
        for dataset in datasets
        if dataset.arm == "corrected_keV"
        for item in dataset.sim_inputs
    )
    legacy_hashes_match = all(
        sha256(ROOT / item["path"]) == item["sha256"]
        for dataset in datasets
        if dataset.arm == "legacy_bug_axis"
        for item in dataset.sim_inputs
    )
    if not corrected_hashes_match:
        errors.append("corrected input hash drift during analysis")
    if not legacy_hashes_match:
        errors.append("legacy input hash drift during analysis")

    validation = {
        "schema_version": 1,
        "status": "PASS" if not errors else "FAIL",
        "authority": AUTHORITY,
        "errors": errors,
        "summary": rel(SUMMARY_JSON),
        "summary_sha256": sha256(SUMMARY_JSON),
        "outputs": [
            {"path": rel(path), "sha256": sha256(path), "size_bytes": path.stat().st_size}
            for path in required_outputs
            if path.is_file()
        ],
        "checks": {
            "datasets": len(datasets),
            "all_primary_counts_100000": all(dataset.primary_count == 100_000 for dataset in datasets),
            "all_sum_TT_positive": all(dataset.sum_TT_s > 0.0 for dataset in datasets),
            "corrected_input_hashes_match_ledger": corrected_hashes_match,
            "legacy_input_hashes_match_validation": legacy_hashes_match,
            "tes_pixel_regex": TES_RE.pattern,
            "response_contract_applied": True,
            "common_histogram_bins": len(BROAD_EDGES) > 2 and len(LOW_EDGES) > 2 and len(ZOOM_EDGES) > 2,
            "broad_histogram_count_closure": histogram_closure,
            "figures_readable": figures_readable,
            "figure_qa": image_qa,
        },
    }
    atomic_json(VALIDATION_JSON, validation)
    print(json.dumps({"status": validation["status"], "results": summaries}, indent=2, ensure_ascii=False))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

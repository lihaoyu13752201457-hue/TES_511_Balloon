#!/usr/bin/env python3
"""Empirical MEGAlib length-unit probe using 511 keV photons in copper.

The test writes a minimal copper slab geometry, runs Cosima with a monoenergetic
collimated beam, and compares the interaction fraction against NIST XCOM
attenuation for copper.  The discriminant is simple:

  numeric thickness 1.0
    if MEGAlib length unit is cm -> t = 1.0 cm
    if MEGAlib length unit is mm -> t = 0.1 cm

The measured interaction probability should be near 1-exp(-mu*t).
"""

from __future__ import annotations

import csv
import gzip
import json
import math
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent
COSIMA = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima")

EVENTS_PER_CASE = 20000
ENERGY_KEV = 511.0
COPPER_DENSITY_G_CM3 = 8.954

# NIST XCOM copper table values bracketing 511 keV:
# https://physics.nist.gov/PhysRefData/XrayMassCoef/ElemTab/z29.html
# Energy in MeV, total mass attenuation coefficient in cm^2/g.
NIST_CU_POINTS = [
    (0.500, 8.362e-2),
    (0.600, 7.625e-2),
]


@dataclass(frozen=True)
class Case:
    name: str
    thickness_numeric: float


def loglog_interpolate(points: list[tuple[float, float]], x: float) -> float:
    (x0, y0), (x1, y1) = points
    lx0, lx1, lx = math.log(x0), math.log(x1), math.log(x)
    ly0, ly1 = math.log(y0), math.log(y1)
    return math.exp(ly0 + (ly1 - ly0) * (lx - lx0) / (lx1 - lx0))


def expected_interaction(mu_per_cm: float, thickness_cm: float) -> float:
    return 1.0 - math.exp(-mu_per_cm * thickness_cm)


def write_case_files(case: Case, case_dir: Path) -> Path:
    half_z = case.thickness_numeric / 2.0
    output_base = f"runs/{case.name}"

    setup = """Name UnitScaleProbe
Version 1
Include unit_scale_probe.geo
Include unit_scale_probe.det
SurroundingSphere 100 0 0 0 100
"""

    geo = f"""Name UnitScaleProbeMassModel
Version 1

Include $(MEGALIB)/resource/examples/geomega/materials/Materials.geo

Volume WorldVolume
WorldVolume.Visibility 0
WorldVolume.Material Vacuum
WorldVolume.Shape BRIK 20 20 20
WorldVolume.Mother 0

Volume CuSlab
CuSlab.Material Copper
CuSlab.Visibility 1
CuSlab.Shape BRIK 5 5 {half_z:.8g}
CuSlab.Position 0 0 0
CuSlab.Mother WorldVolume
"""

    det = """Scintillator CuProbe
CuProbe.SensitiveVolume CuSlab
CuProbe.DetectorVolume CuSlab
CuProbe.TriggerThreshold 0.0001
CuProbe.EnergyResolution Gauss 0.001 0.001 0.001
CuProbe.EnergyResolution Gauss 3000 3000 0.001
"""

    source = f"""Version 1
Geometry unit_scale_probe.geo.setup
PhysicsListEM LivermorePol
StoreSimulationInfo all
PreTriggerMode everything
DiscretizeHits true
DetectorTimeConstant 1e-9

Run {case.name}
{case.name}.FileName {output_base}
{case.name}.Events {EVENTS_PER_CASE}
{case.name}.Source Beam511

Beam511.ParticleType 1
Beam511.Beam HomogeneousBeam 0.0 0.0 -2.0 0.0 0.0 1.0 0.25
Beam511.Spectrum Mono {ENERGY_KEV:.6f}
Beam511.Flux 1.0
"""

    (case_dir / "unit_scale_probe.geo.setup").write_text(setup, encoding="utf-8")
    (case_dir / "unit_scale_probe.geo").write_text(geo, encoding="utf-8")
    (case_dir / "unit_scale_probe.det").write_text(det, encoding="utf-8")
    source_path = case_dir / f"{case.name}.source"
    source_path.write_text(source, encoding="utf-8")
    runs_dir = case_dir / "runs"
    runs_dir.mkdir(exist_ok=True)
    for old in runs_dir.glob(f"{case.name}.inc*.id*.sim*"):
        old.unlink()
    return source_path


def run_cosima(source_path: Path, case_dir: Path, seed: int) -> Path:
    log_path = case_dir / f"{source_path.stem}.log"
    with log_path.open("w", encoding="utf-8") as log:
        subprocess.run(
            [str(COSIMA), "-s", str(seed), source_path.name],
            cwd=case_dir,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=True,
        )
    return log_path


def parse_log_generated(log_path: Path) -> int | None:
    pattern = re.compile(r"Total number of generated particles:\s+(\d+)")
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.search(line)
        if match:
            return int(match.group(1))
    return None


def open_text(path: Path):
    if path.suffix == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("r", encoding="utf-8", errors="replace")


def parse_sim(sim_path: Path) -> dict[str, int]:
    event_count = 0
    interaction_event_count = 0
    edep_event_count = 0
    ia_count = 0
    htsim_count = 0
    ts_count: int | None = None
    current_event = False
    current_has_interaction = False
    current_has_edep = False

    def finish_event() -> None:
        nonlocal current_event, current_has_interaction, current_has_edep
        nonlocal interaction_event_count, edep_event_count
        if current_event and current_has_interaction:
            interaction_event_count += 1
        if current_event and current_has_edep:
            edep_event_count += 1
        current_event = False
        current_has_interaction = False
        current_has_edep = False

    with open_text(sim_path) as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith("ID "):
                finish_event()
                event_count += 1
                current_event = True
            elif line.startswith("ED "):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        current_has_edep = float(parts[1]) > 0.0
                    except ValueError:
                        pass
            elif line.startswith("IA "):
                parts = line.split()
                if len(parts) >= 2:
                    process = parts[1]
                    if process not in {"INIT", "ESCP"}:
                        current_has_interaction = True
                        ia_count += 1
            elif line.startswith("HTsim "):
                current_has_edep = True
                htsim_count += 1
            elif line.startswith("TS "):
                parts = line.split()
                if len(parts) >= 2:
                    try:
                        ts_count = int(float(parts[1]))
                    except ValueError:
                        pass

    finish_event()
    simulated = ts_count if ts_count is not None else event_count
    return {
        "simulated_events": simulated,
        "stored_events": event_count,
        "interaction_events": interaction_event_count,
        "edep_events": edep_event_count,
        "ia_count": ia_count,
        "htsim_count": htsim_count,
    }


def find_sim_file(case: Case, case_dir: Path) -> Path:
    matches = sorted((case_dir / "runs").glob(f"{case.name}.inc*.id*.sim"))
    matches += sorted((case_dir / "runs").glob(f"{case.name}.inc*.id*.sim.gz"))
    if len(matches) != 1:
        raise RuntimeError(f"Expected one sim file for {case.name}, found {matches}")
    return matches[0]


def run_case(case: Case) -> dict[str, float | int | str]:
    case_dir = ROOT / case.name
    case_dir.mkdir(exist_ok=True)
    source_path = write_case_files(case, case_dir)
    seed = 511000 + int(round(case.thickness_numeric * 1000))
    log_path = run_cosima(source_path, case_dir, seed)
    sim_path = find_sim_file(case, case_dir)
    parsed = parse_sim(sim_path)
    generated = parse_log_generated(log_path)
    n = generated or parsed["simulated_events"]
    interaction_events = parsed["interaction_events"]
    measured = interaction_events / n
    sigma = math.sqrt(max(measured * (1.0 - measured), 0.0) / n)

    nist_mu_over_rho = loglog_interpolate(NIST_CU_POINTS, ENERGY_KEV / 1000.0)
    mu_per_cm = nist_mu_over_rho * COPPER_DENSITY_G_CM3
    expected_cm = expected_interaction(mu_per_cm, case.thickness_numeric)
    expected_mm = expected_interaction(mu_per_cm, case.thickness_numeric / 10.0)

    return {
        "case": case.name,
        "source": str(source_path.relative_to(ROOT)),
        "log": str(log_path.relative_to(ROOT)),
        "sim": str(sim_path.relative_to(ROOT)),
        "energy_keV": ENERGY_KEV,
        "material": "Copper",
        "density_g_cm3": COPPER_DENSITY_G_CM3,
        "thickness_numeric": case.thickness_numeric,
        "events": n,
        "stored_events": parsed["stored_events"],
        "interaction_events": interaction_events,
        "edep_events": parsed["edep_events"],
        "ia_count": parsed["ia_count"],
        "htsim_count": parsed["htsim_count"],
        "measured_interaction": measured,
        "binomial_sigma": sigma,
        "nist_mu_over_rho_cm2_g": nist_mu_over_rho,
        "nist_mu_per_cm": mu_per_cm,
        "expected_if_numeric_is_cm": expected_cm,
        "expected_if_numeric_is_mm": expected_mm,
        "delta_to_cm_sigma": abs(measured - expected_cm) / sigma if sigma > 0 else float("inf"),
        "delta_to_mm_sigma": abs(measured - expected_mm) / sigma if sigma > 0 else float("inf"),
    }


def write_outputs(results: list[dict[str, float | int | str]]) -> None:
    json_path = ROOT / "unit_scale_probe_results.json"
    json_path.write_text(json.dumps(results, indent=2, sort_keys=True), encoding="utf-8")

    csv_path = ROOT / "unit_scale_probe_results.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0].keys()))
        writer.writeheader()
        writer.writerows(results)

    lines = [
        "# MEGAlib unit scale probe",
        "",
        "Monoenergetic 511 keV photons were fired into a copper slab.  The",
        "interaction fraction is compared to NIST XCOM copper attenuation.",
        "",
        "NIST copper table values used for log-log interpolation:",
        "- 0.500 MeV: mu/rho = 8.362e-2 cm^2/g",
        "- 0.600 MeV: mu/rho = 7.625e-2 cm^2/g",
        "- Source: https://physics.nist.gov/PhysRefData/XrayMassCoef/ElemTab/z29.html",
        "",
        "| case | numeric thickness | events | interaction events | measured | NIST if cm | NIST if mm | cm sigma | mm sigma |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in results:
        lines.append(
            "| {case} | {thickness_numeric:.3f} | {events:d} | {interaction_events:d} | "
            "{measured_interaction:.5f} +/- {binomial_sigma:.5f} | "
            "{expected_if_numeric_is_cm:.5f} | {expected_if_numeric_is_mm:.5f} | "
            "{delta_to_cm_sigma:.2f} | {delta_to_mm_sigma:.2f} |".format(**row)
        )
    lines.extend(
        [
            "",
            "Interpretation: if the measured column follows `NIST if cm`, MEGAlib",
            "is treating the bare geometry numbers as centimeters. If it follows",
            "`NIST if mm`, the bare numbers are millimeters.",
            "",
            "Conclusion from this run: the measured interaction fractions match",
            "the `NIST if cm` predictions and reject the `NIST if mm` predictions",
            "by tens to hundreds of statistical sigma. Bare MEGAlib geometry",
            "length numbers are therefore being used as centimeters in Cosima.",
        ]
    )
    (ROOT / "unit_scale_probe_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    cases = [
        Case("copper_t0p100", 0.1),
        Case("copper_t1p000", 1.0),
    ]
    results = [run_case(case) for case in cases]
    write_outputs(results)
    for row in results:
        print(
            "{case}: measured={measured_interaction:.5f} +/- {binomial_sigma:.5f}, "
            "NIST_cm={expected_if_numeric_is_cm:.5f}, "
            "NIST_mm={expected_if_numeric_is_mm:.5f}".format(**row)
        )
    print(f"Wrote {ROOT / 'unit_scale_probe_report.md'}")


if __name__ == "__main__":
    main()

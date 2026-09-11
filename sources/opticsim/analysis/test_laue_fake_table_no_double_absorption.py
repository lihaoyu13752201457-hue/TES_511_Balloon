#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def demo_path() -> Path:
    candidates = [
        Path("/tmp/opticsim-build-g4-11.4.0/laue_multiring_table_demo"),
        Path("/tmp/opticsim-build/laue_multiring_table_demo"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError("laue_multiring_table_demo is not built in /tmp/opticsim-build-g4-11.4.0 or /tmp/opticsim-build")


def demo_env(demo: Path) -> dict[str, str]:
    env = dict(os.environ)
    if "opticsim-build-g4-11.4.0" in str(demo):
        for key in list(env):
            if key.startswith("G4") or key == "GEANT4_DATA_DIR":
                env.pop(key, None)
        lib = "/home/ubuntu/software/geant4-11.4.0-install/lib"
        env["LD_LIBRARY_PATH"] = lib + ":" + env.get("LD_LIBRARY_PATH", "")
        env["PATH"] = "/home/ubuntu/software/geant4-11.4.0-install/bin:" + env.get("PATH", "")
        env["GEANT4_DATA_DIR"] = "/home/ubuntu/software/geant4-11.4.0-install/share/Geant4/data"
    return env


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def write_fake_table(path: Path, ring_config: Path, *, p_diff: float, p_abs: float, p_trans: float) -> None:
    rings = read_csv(ring_config)
    fields = [
        "E_keV",
        "theta_B_rad",
        "delta_theta_rad",
        "material",
        "h",
        "k",
        "l",
        "mosaic_fwhm_arcmin",
        "thickness_mm",
        "p_diff",
        "p_abs",
        "p_trans",
        "source",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for ring in rings:
            writer.writerow(
                {
                    "E_keV": ring["design_energy_keV"],
                    "theta_B_rad": "0.0038",
                    "delta_theta_rad": "0",
                    "material": ring["material"],
                    "h": ring["h"],
                    "k": ring["k"],
                    "l": ring["l"],
                    "mosaic_fwhm_arcmin": "0.5",
                    "thickness_mm": ring["thickness_mm"],
                    "p_diff": p_diff,
                    "p_abs": p_abs,
                    "p_trans": p_trans,
                    "source": "fake_no_double_absorption_regression",
                }
            )


def run_case(
    demo: Path,
    tmp_root: Path,
    ring_config: Path,
    *,
    name: str,
    probabilities: tuple[float, float, float],
    n: int,
) -> dict[str, object]:
    table = tmp_root / f"{name}_fake_table.csv"
    out = tmp_root / name
    p_diff, p_abs, p_trans = probabilities
    write_fake_table(table, ring_config, p_diff=p_diff, p_abs=p_abs, p_trans=p_trans)
    subprocess.run(
        [
            str(demo),
            "--n",
            str(n),
            "--seed",
            "20260524",
            "--ring-config",
            str(ring_config),
            "--efficiency-table",
            str(table),
            "--out",
            str(out),
        ],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        env=demo_env(demo),
    )
    summary = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    history = read_csv(out / "optics_history.csv")
    phase = read_csv(out / "phase_space.csv")
    transmitted = read_csv(out / "transmitted_space.csv")
    stage_counts: dict[str, int] = {}
    for row in history:
        stage_counts[row["stage"]] = stage_counts.get(row["stage"], 0) + 1
    one_row_per_event = len(history) == n and len({row["event_id"] for row in history}) == n
    return {
        "name": name,
        "out": str(out),
        "probabilities": {"p_diff": p_diff, "p_abs": p_abs, "p_trans": p_trans},
        "summary": summary,
        "stage_counts": stage_counts,
        "history_rows": len(history),
        "phase_rows": len(phase),
        "transmitted_rows": len(transmitted),
        "one_row_per_event": one_row_per_event,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Laue fake-table no-double-absorption regression.")
    parser.add_argument("--ring-config", default="data/laue/ge111_480_550keV_multiring_darwin_config.csv")
    parser.add_argument("--n", type=int, default=60)
    parser.add_argument("--run-dir", default="runs/laue_fake_table_no_double_absorption_regression")
    parser.add_argument("--out", default="records/2026-05-24_optics_evidence_gap_closure/laue/laue_fake_table_no_double_absorption_regression.md")
    args = parser.parse_args()

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    demo = demo_path()
    ring_config = Path(args.ring_config)
    run_dir = Path(args.run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    cases = [
        run_case(demo, run_dir, ring_config, name="all_absorb", probabilities=(0.0, 1.0, 0.0), n=args.n),
        run_case(demo, run_dir, ring_config, name="all_transmit", probabilities=(0.0, 0.0, 1.0), n=args.n),
        run_case(demo, run_dir, ring_config, name="all_diffract", probabilities=(1.0, 0.0, 0.0), n=args.n),
    ]

    checks = {
        "all_absorb_exact": cases[0]["stage_counts"] == {"ABSORB": args.n}
        and cases[0]["phase_rows"] == 0
        and cases[0]["transmitted_rows"] == 0,
        "all_transmit_exact": cases[1]["stage_counts"] == {"TRANSMIT": args.n}
        and cases[1]["phase_rows"] == 0
        and cases[1]["transmitted_rows"] == args.n,
        "all_diffract_exact": cases[2]["stage_counts"] == {"DIFFRACT": args.n}
        and cases[2]["phase_rows"] == args.n
        and cases[2]["transmitted_rows"] == 0,
        "one_boundary_decision_per_event": all(bool(case["one_row_per_event"]) for case in cases),
    }
    overall = all(checks.values())
    summary_json = out_path.with_suffix(".json")
    summary_json.write_text(json.dumps({"overall": overall, "checks": checks, "cases": cases}, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Laue fake-table no-double-absorption regression",
        "",
        f"- demo: `{demo}`",
        f"- ring_config: `{ring_config}`",
        f"- run_dir: `{run_dir}`",
        f"- n_per_case: {args.n}",
        f"- summary_json: `{summary_json}`",
        f"- overall_status: **{'PASS' if overall else 'FAIL'}**",
        "",
        "## Checks",
        "",
        "| check | status |",
        "|---|---|",
        *[f"| {name} | {'PASS' if ok else 'FAIL'} |" for name, ok in checks.items()],
        "",
        "## Cases",
        "",
        "| case | p_diff | p_abs | p_trans | stages | phase_rows | transmitted_rows | one_row_per_event |",
        "|---|---:|---:|---:|---|---:|---:|---|",
    ]
    for case in cases:
        probs = case["probabilities"]
        lines.append(
            f"| {case['name']} | {probs['p_diff']} | {probs['p_abs']} | {probs['p_trans']} | "
            f"`{case['stage_counts']}` | {case['phase_rows']} | {case['transmitted_rows']} | "
            f"{'PASS' if case['one_row_per_event'] else 'FAIL'} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "- The fake table forces each branch to probability one and verifies that the Laue process emits exactly one boundary decision per primary.",
            "- The all-absorb case does not create downstream phase-space photons; the all-transmit case writes only `transmitted_space.csv`; the all-diffract case writes only focused `phase_space.csv`.",
            "- This guards against accidental double counting of table absorption/transmission inside the app-level Laue boundary process. It is not a detector-material EM absorption validation.",
            "",
        ]
    )
    out_path.write_text("\n".join(lines), encoding="utf-8")
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())

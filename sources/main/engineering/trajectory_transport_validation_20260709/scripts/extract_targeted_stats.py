#!/usr/bin/env python3
"""Extract TES/band rates and Q from targeted Cosima sims.

Uses HTsim energy at field index 4 (not time at 5); det IDs 1–6; band 480–550 keV.
Writes under 05_targeted_stats/ only — does not re-run Cosima.
"""
from __future__ import annotations

import csv
import gzip
import json
import re
from collections import defaultdict
from pathlib import Path

PKG = Path(__file__).resolve().parents[1]
OUT = PKG / "05_targeted_stats"
PARTICLES = ["eplus", "n", "gamma"]
EVENTS_EXPECTED = {"eplus": 1_000_000, "n": 200_000, "gamma": 500_000}


def open_sim(path: Path):
    if str(path).endswith(".gz"):
        return gzip.open(path, "rt", errors="replace")
    return path.open("rt", errors="replace")


def is_gzip_ok(path: Path) -> bool:
    try:
        with gzip.open(path, "rb") as f:
            while f.read(1 << 20):
                pass
        return True
    except Exception as e:
        print(f"  BAD gzip {path}: {e}")
        return False


def extract_tes_stats(sim_paths: list[Path]) -> dict:
    n_events = n_tes = n_band = 0
    sum_tes = 0.0
    for sim_path in sim_paths:
        in_event = False
        tes_e = 0.0
        try:
            with open_sim(sim_path) as f:
                for line in f:
                    if line.startswith("SE"):
                        if in_event:
                            n_events += 1
                            if tes_e > 0:
                                n_tes += 1
                                sum_tes += tes_e
                                if 480.0 <= tes_e <= 550.0:
                                    n_band += 1
                        in_event = True
                        tes_e = 0.0
                    elif in_event and line.startswith("HTsim"):
                        try:
                            fields = line.split(None, 1)[1].split(";")
                            det = int(float(fields[0]))
                            e = float(fields[4])  # energy; fields[5] is time
                            if 1 <= det <= 6:
                                tes_e += e
                        except Exception:
                            pass
                if in_event:
                    n_events += 1
                    if tes_e > 0:
                        n_tes += 1
                        sum_tes += tes_e
                        if 480.0 <= tes_e <= 550.0:
                            n_band += 1
        except EOFError:
            print(f"  EOF mid-read {sim_path.name}; counting partial")
            if in_event:
                n_events += 1
                if tes_e > 0:
                    n_tes += 1
                    sum_tes += tes_e
                    if 480.0 <= tes_e <= 550.0:
                        n_band += 1
    return {
        "n_events": n_events,
        "n_tes": n_tes,
        "n_band480_550": n_band,
        "sum_tes_keV": sum_tes,
    }


def parse_log(log_path: Path):
    if not log_path.exists():
        return None, None
    text = log_path.read_text(errors="replace")
    gen = obs = None
    for line in text.splitlines():
        if "Total number of generated particles" in line:
            m = re.search(r"(\d+)\s*$", line.strip())
            if m:
                gen = int(m.group(1))
        if "Observation time" in line:
            m = re.search(r"([0-9.eE+\-]+)\s*sec", line)
            if m:
                obs = float(m.group(1))
    return gen, obs


def main() -> None:
    points = list(csv.DictReader((PKG / "01_points/validation_points.csv").open()))
    parma = {
        r["point_id"]: r
        for r in csv.DictReader((PKG / "02_sources/parma_live/live_parma_scales.csv").open())
    }

    inventory = []
    run_rows = []
    for p in points:
        pid = p["point_id"]
        sa = float(p["analytic_prompt_scale_to_day15"])
        for part in PARTICLES:
            rundir = OUT / "per_point" / pid / part
            sims_all = sorted(rundir.glob("*.sim.gz"))
            sims = []
            for s in sims_all:
                if s.stat().st_size < 1000:
                    continue
                if is_gzip_ok(s):
                    sims.append(s)
                else:
                    inventory.append(
                        {
                            "point_id": pid,
                            "particle": part,
                            "sim": str(s.relative_to(PKG)),
                            "status": "truncated_gzip",
                            "size": s.stat().st_size,
                        }
                    )
            log = PKG / "logs/targeted" / f"{pid}_{part}_targeted.log"
            gen, obs = parse_log(log)
            stats = (
                extract_tes_stats(sims)
                if sims
                else {"n_events": 0, "n_tes": 0, "n_band480_550": 0, "sum_tes_keV": 0.0}
            )
            if gen is None and stats["n_events"]:
                gen = stats["n_events"]
            scale_lp = float(parma[pid].get(f"scale_{part}", "nan"))
            ok = bool(sims) and obs is not None and gen is not None
            inventory.append(
                {
                    "point_id": pid,
                    "particle": part,
                    "n_good_sims": len(sims),
                    "sizes": [s.stat().st_size for s in sims],
                    "gen": gen,
                    "obs_s": obs,
                    "n_events_sim": stats["n_events"],
                    "status": "ok" if ok else "incomplete",
                }
            )
            row = {
                "point_id": pid,
                "particle": part,
                "events_requested": EVENTS_EXPECTED[part],
                "scale_live_parma": scale_lp,
                "analytic_prompt_scale": sa,
                "gen": gen,
                "obs_s": obs,
                "n_events_sim": stats["n_events"],
                "n_tes": stats["n_tes"],
                "n_band480_550": stats["n_band480_550"],
                "sum_tes_keV": stats["sum_tes_keV"],
                "rc": 0 if ok else -1,
                "sim": ";".join(str(s.relative_to(PKG)) for s in sims),
            }
            if obs and gen:
                row["gen_rate_hz"] = gen / obs
                row["tes_rate_hz"] = stats["n_tes"] / obs
                row["band_rate_hz"] = stats["n_band480_550"] / obs
            else:
                row["gen_rate_hz"] = float("nan")
                row["tes_rate_hz"] = float("nan")
                row["band_rate_hz"] = float("nan")
            run_rows.append(row)
            print(
                f"{pid:3s} {part:6s} status={'OK' if ok else 'INCOMPLETE'} "
                f"gen={gen} obs={obs} n_tes={stats['n_tes']} n_band={stats['n_band480_550']}"
            )

    # Q vs REF
    ref = {r["particle"]: r for r in run_rows if r["point_id"] == "REF"}
    for r in run_rows:
        rr = ref.get(r["particle"])
        for key in ("gen_rate_hz", "tes_rate_hz", "band_rate_hz"):
            if not rr or not rr.get(key) or rr[key] != rr[key] or rr[key] <= 0:
                over = float("nan")
            elif r[key] != r[key]:
                over = float("nan")
            else:
                over = r[key] / rr[key]
            r[f"{key}_over_REF"] = over
            sa = r["analytic_prompt_scale"]
            sp = r["scale_live_parma"]
            r[f"Q_{key}_vs_analytic"] = (over / sa) if sa and over == over else float("nan")
            r[f"Q_{key}_vs_live_parma"] = (
                (over / sp) if sp and sp == sp and sp > 0 and over == over else float("nan")
            )

    fields = sorted({k for r in run_rows for k in r})
    with (OUT / "targeted_prompt_results.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(run_rows)

    # combined multi-species
    by_pt: dict = defaultdict(lambda: {"band": 0.0, "tes": 0.0, "gen": 0.0})
    for r in run_rows:
        pid = r["point_id"]
        for k, src in [("band", "band_rate_hz"), ("tes", "tes_rate_hz"), ("gen", "gen_rate_hz")]:
            v = r[src]
            if v == v:
                by_pt[pid][k] += v
        by_pt[pid]["analytic"] = r["analytic_prompt_scale"]
        by_pt[pid]["parma_eplus"] = float(parma[pid]["scale_eplus"])

    ref_b = by_pt["REF"]["band"]
    ref_t = by_pt["REF"]["tes"]
    combined = []
    for pid in ["REF", "L1", "H1", "L2"]:
        v = by_pt[pid]
        row = {
            "point_id": pid,
            "band_rate_sum_hz": v["band"],
            "tes_rate_sum_hz": v["tes"],
            "gen_rate_sum_hz": v["gen"],
            "band_over_REF": v["band"] / ref_b if ref_b > 0 else float("nan"),
            "tes_over_REF": v["tes"] / ref_t if ref_t > 0 else float("nan"),
            "analytic_prompt_scale": v["analytic"],
            "live_parma_eplus_scale": v["parma_eplus"],
        }
        row["Q_band_vs_analytic"] = (
            row["band_over_REF"] / row["analytic_prompt_scale"]
            if row["analytic_prompt_scale"]
            else float("nan")
        )
        row["Q_band_vs_parma_eplus"] = (
            row["band_over_REF"] / row["live_parma_eplus_scale"]
            if row["live_parma_eplus_scale"]
            else float("nan")
        )
        row["Q_tes_vs_analytic"] = (
            row["tes_over_REF"] / row["analytic_prompt_scale"]
            if row["analytic_prompt_scale"]
            else float("nan")
        )
        row["Q_tes_vs_parma_eplus"] = (
            row["tes_over_REF"] / row["live_parma_eplus_scale"]
            if row["live_parma_eplus_scale"]
            else float("nan")
        )
        combined.append(row)

    with (OUT / "combined_species_Q.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(combined[0].keys()))
        w.writeheader()
        w.writerows(combined)

    n_ok = sum(1 for r in run_rows if r["rc"] == 0)
    decision = {
        "status": "TARGETED_STATS_NOT_FULL4",
        "claim_level": "TARGETED_STATS_NOT_FULL4",
        "events": EVENTS_EXPECTED,
        "n_runs_ok": n_ok,
        "n_runs_total": len(run_rows),
        "inventory": inventory,
        "combined_Q": combined,
        "blocks_full_curve_claim": True,
        "not_equivalent_to_fable5": [
            "not Step05 W2",
            "not activation residual",
            "not delayed history-aware",
            "not full4 ~1e8 primaries",
        ],
    }

    def clean(o):
        if isinstance(o, float):
            if o != o or o in (float("inf"), float("-inf")):
                return None
            return o
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items()}
        if isinstance(o, list):
            return [clean(x) for x in o]
        return o

    (OUT / "targeted_decision.json").write_text(json.dumps(clean(decision), indent=2) + "\n")

    print("\n=== e+ Q summary ===")
    for r in run_rows:
        if r["particle"] != "eplus":
            continue
        print(
            f"{r['point_id']:3s} band/REF={r['band_rate_hz_over_REF']:.4f} "
            f"Qb_ana={r['Q_band_rate_hz_vs_analytic']:.4f} "
            f"Qb_par={r['Q_band_rate_hz_vs_live_parma']:.4f} "
            f"n_band={r['n_band480_550']}"
        )
    print(f"\nOK {n_ok}/{len(run_rows)}")
    print(f"Wrote {OUT / 'targeted_prompt_results.csv'}")
    print(f"Wrote {OUT / 'combined_species_Q.csv'}")
    print(f"Wrote {OUT / 'targeted_decision.json'}")
    if n_ok < len(run_rows):
        raise SystemExit(2)


if __name__ == "__main__":
    main()

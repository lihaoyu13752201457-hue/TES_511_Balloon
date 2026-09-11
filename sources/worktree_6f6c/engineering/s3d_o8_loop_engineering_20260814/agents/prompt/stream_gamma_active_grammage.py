#!/usr/bin/env python3
"""Add exact incoming active grammage to the complete gamma denominator.

Each raw IA INIT ray is followed from its far-field start to its closest
approach to the InstrumentFrame origin.  The companion C++ query uses the true
MEGAlib boolean shapes for the six exact active volumes.  This is a geometry
query, not particle transport.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import math
import subprocess
import threading
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

from scipy.stats import beta

from stream_gamma_denominator import (
    AZ_EDGES_DEG,
    ENERGY_EDGES_KEV,
    MU_X_EDGES,
    bin_index,
    parse_init,
    transformed_direction,
)


GRAMMAGE_EDGES = (0.0, 1.0e-6, 5.0, 15.0, 25.0, 35.0, 50.0, 75.0, 100.0, math.inf)


def worker(task: tuple[list[str], dict[str, dict[int, tuple[int, int, int]]], str, str]) -> dict:
    sim_paths, labels_by_path, binary, geometry = task
    proc = subprocess.Popen(
        [binary, geometry], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, bufsize=1,
    )
    assert proc.stdin is not None and proc.stdout is not None and proc.stderr is not None
    feed_error: list[BaseException] = []
    n_fed = 0

    def feed() -> None:
        nonlocal n_fed
        try:
            for sim_path in sim_paths:
                labels = labels_by_path.get(sim_path, {})
                current_id: int | None = None
                with gzip.open(sim_path, "rt", encoding="utf-8", errors="replace") as stream:
                    for line in stream:
                        if line.startswith("ID "):
                            current_id = int(line.split()[1])
                        elif line.startswith("IA INIT"):
                            if current_id is None:
                                raise ValueError(f"INIT before ID in {sim_path}")
                            x, y, z, dx, dy, dz, energy = parse_init(line)
                            mux, _, _, _, az = transformed_direction(dx, dy, dz)
                            ie = bin_index(energy, ENERGY_EDGES_KEV)
                            im = bin_index(mux, MU_X_EDGES)
                            ia = bin_index(az, AZ_EDGES_DEG)
                            pre, veto, step = labels.get(current_id, (0, 0, 0))
                            norm = math.sqrt(dx*dx + dy*dy + dz*dz)
                            ux, uy, uz = dx/norm, dy/norm, dz/norm
                            t_closest = -(x*ux + y*uy + z*uz)
                            if t_closest <= 0:
                                raise ValueError(f"outward INIT ray in {sim_path} ID {current_id}")
                            qid = f"q{ie}_{im}_{ia}_{pre}{veto}{step}"
                            proc.stdin.write(
                                f"{qid} {x:.8g} {y:.8g} {z:.8g} {dx:.8g} {dy:.8g} {dz:.8g} {t_closest:.12g}\n"
                            )
                            n_fed += 1
            proc.stdin.close()
        except BaseException as exc:
            feed_error.append(exc)
            try:
                proc.stdin.close()
            except BaseException:
                pass

    feeder = threading.Thread(target=feed, daemon=True)
    feeder.start()
    counts: Counter[tuple[int, int, int, int, str]] = Counter()
    sums: Counter[str] = Counter()
    n_read = 0
    for line in proc.stdout:
        if not line.startswith("q"):
            continue
        qid, bgo_text, plastic_text, gram_text = line.rstrip().split(",")
        ie, im, ia, flags = qid[1:].split("_")
        gram = float(gram_text)
        ig = bin_index(max(0.0, gram), GRAMMAGE_EDGES)
        key = (int(ie), int(im), int(ia), ig)
        counts[key + ("incident",)] += 1
        if flags[0] == "1": counts[key + ("pre_w2",)] += 1
        if flags[1] == "1": counts[key + ("veto_leak",)] += 1
        if flags[2] == "1": counts[key + ("step05",)] += 1
        sums["bgo_chord_cm"] += float(bgo_text)
        sums["plastic_chord_cm"] += float(plastic_text)
        sums["active_grammage_g_cm2"] += gram
        n_read += 1
    feeder.join()
    stderr = proc.stderr.read()
    rc = proc.wait()
    if feed_error:
        raise feed_error[0]
    if rc != 0 or n_fed != n_read:
        raise RuntimeError(f"query failed rc={rc}, fed/read={n_fed}/{n_read}: {stderr[-1000:]}")
    return {"n": n_read, "counts": dict(counts), "sums": dict(sums)}


def cp_upper(k: int, n: int) -> float:
    if k >= n: return 1.0
    return float(beta.ppf(0.95, k + 1, n - k))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--w2-events", type=Path, required=True)
    ap.add_argument("--repo-root", type=Path, default=Path("/home/ubuntu/TES_511_Balloon"))
    ap.add_argument("--binary", type=Path, required=True)
    ap.add_argument("--geometry", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--workers", type=int, default=3)
    args = ap.parse_args()

    jobs = []
    with args.manifest.open(newline="") as stream:
        for row in csv.DictReader(stream):
            if row["geometry"] == "S3d_O8" and row["family"] == "gamma" and row["mode"] == "instant":
                jobs.append(row)
    paths = [str((args.repo_root / row["sim_path"]).resolve()) for row in jobs]
    labels: dict[str, dict[int, tuple[int, int, int]]] = {}
    with args.w2_events.open(newline="") as stream:
        for row in csv.DictReader(stream):
            if row["family"] != "gamma": continue
            labels.setdefault(str(Path(row["source_file"]).resolve()), {})[int(row["local_event_id"])] = (
                1, int(row["pass_veto50"] == "True"), int(row["step05_pass"] == "True")
            )
    chunks = [paths[i::args.workers] for i in range(args.workers)]
    tasks = [(chunk, labels, str(args.binary.resolve()), str(args.geometry.resolve())) for chunk in chunks]
    aggregate: Counter = Counter()
    sums: Counter = Counter()
    n = 0
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        for result in pool.map(worker, tasks):
            n += result["n"]
            aggregate.update(result["counts"])
            sums.update(result["sums"])
    expected = sum(int(row["events"]) for row in jobs)
    if n != expected:
        raise SystemExit(f"expected/read mismatch {expected}/{n}")
    tt = sum(float(row["TT_s"]) for row in jobs)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "energy_lo_keV", "energy_hi_keV", "mu_x_lo", "mu_x_hi",
        "azimuth_lo_deg", "azimuth_hi_deg", "active_grammage_lo_g_cm2",
        "active_grammage_hi_g_cm2", "n_incident", "n_pre_w2", "n_veto_leak",
        "n_step05", "veto_leak_probability", "veto_leak_probability_upper95_onesided",
        "veto_leak_rate_cps",
    ]
    with args.output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for ie in range(len(ENERGY_EDGES_KEV)-1):
            for im in range(len(MU_X_EDGES)-1):
                for ia in range(len(AZ_EDGES_DEG)-1):
                    for ig in range(len(GRAMMAGE_EDGES)-1):
                        key = (ie, im, ia, ig)
                        ni = aggregate[key + ("incident",)]
                        if not ni: continue
                        k = aggregate[key + ("veto_leak",)]
                        writer.writerow({
                            "energy_lo_keV": ENERGY_EDGES_KEV[ie], "energy_hi_keV": ENERGY_EDGES_KEV[ie+1],
                            "mu_x_lo": MU_X_EDGES[im], "mu_x_hi": MU_X_EDGES[im+1],
                            "azimuth_lo_deg": AZ_EDGES_DEG[ia], "azimuth_hi_deg": AZ_EDGES_DEG[ia+1],
                            "active_grammage_lo_g_cm2": GRAMMAGE_EDGES[ig],
                            "active_grammage_hi_g_cm2": GRAMMAGE_EDGES[ig+1],
                            "n_incident": ni, "n_pre_w2": aggregate[key + ("pre_w2",)],
                            "n_veto_leak": k, "n_step05": aggregate[key + ("step05",)],
                            "veto_leak_probability": k/ni,
                            "veto_leak_probability_upper95_onesided": cp_upper(k, ni),
                            "veto_leak_rate_cps": k/tt,
                        })
    print({"n": n, "TT_s": tt, "rows": sum(1 for _ in args.output.open())-1,
           "mean_bgo_chord_cm": sums["bgo_chord_cm"]/n,
           "mean_plastic_chord_cm": sums["plastic_chord_cm"]/n,
           "mean_active_grammage_g_cm2": sums["active_grammage_g_cm2"]/n})


if __name__ == "__main__":
    main()

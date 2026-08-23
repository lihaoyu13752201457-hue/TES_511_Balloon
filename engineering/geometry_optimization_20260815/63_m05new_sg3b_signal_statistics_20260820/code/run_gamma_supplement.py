#!/usr/bin/env python3
"""Generate and run independent corrected-keV SG3B prompt-gamma shards."""
from __future__ import annotations

import argparse
import concurrent.futures
import gzip
import hashlib
import json
import re
import subprocess
import time
from functools import lru_cache
from pathlib import Path

ROOT = Path("/home/ubuntu/TES_511_Balloon")
PACKAGE = ROOT / "engineering/geometry_optimization_20260815/63_m05new_sg3b_signal_statistics_20260820"
TEMPLATE = Path("/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute/generated/sg3b_plan1_extra2x_v1/sources/sg3b_instant_gamma_shard0001.source")
DATA_ROOT = Path("/mnt/data/TES_Balloon_511_data/SG3/m05new_sg3b_gamma_expansion_20260820")
CONFIG_DIR = PACKAGE / "config/gamma_shards"
RECEIPT_DIR = PACKAGE / "outputs/02_gamma_transport/receipts"
LOG_DIR = ROOT / "runs/m05new_sg3b_gamma_expansion_20260820/logs"
COSIMA = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima")
MEGALIB_ENV = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh")
GEOMETRY = Path("/home/ubuntu/.codex/worktrees/4f50/TES_511_Balloon/engineering/geometry_optimization_20260815/55_geoopt_sg3b_bi_halfcylinder_al_harness_20260816/geometry/DEMO2_DR_v3p5_SG3B.geo.setup")
EVENTS_PER_SHARD = 534_624
SEEDS = [
    1632015376, 951002459, 712635489, 28548787, 273525302, 801797908,
    449560183, 1527950586, 1925157423, 1357967649, 1634078472,
    2076789638, 604399541, 1957562292, 933717882, 594649669, 357857592,
    485647514, 1798594615, 613312341, 1097622479, 105823648, 50100289,
    262949503, 109383887, 1986671238, 879679706, 349988300, 1136771565,
    1215895822, 2117415547, 2028442033, 268979520, 1425437368,
    1366323122, 1029855818, 127592966, 359118107, 738292705, 855753631,
    703037182, 617000847, 1294612004, 387351967, 1064875490,
    658587188, 1871581609, 2111500766, 1597863816, 1840699618,
    575322874, 167693060, 179244911, 210346754, 1147098391, 1371034906,
    525685399, 754580070, 235877232, 1438877585, 1491289391,
    1478472189, 191027709, 1012386290, 1216201956, 861058201, 1451077107,
    219857204, 152673708, 1659503061, 1917773750, 353402041, 1423443008,
    1774396864, 1383449810, 691651325, 1722526680, 1881609908,
    484779101, 1995195010,
]


@lru_cache(maxsize=1)
def cosima_environment() -> dict[str, str]:
    """Return a complete MEGAlib environment independent of the parent shell."""
    proc = subprocess.run(
        ["bash", "-lc", f"source {MEGALIB_ENV} >/dev/null && env -0"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode("utf-8", errors="replace"))
    env = {}
    for item in proc.stdout.split(b"\0"):
        if not item or b"=" not in item:
            continue
        key, value = item.split(b"=", 1)
        env[key.decode()] = value.decode()
    probe = subprocess.run(
        ["ldd", str(COSIMA)], capture_output=True, text=True, env=env, check=False
    )
    if probe.returncode != 0 or "not found" in probe.stdout + probe.stderr:
        raise RuntimeError(f"Cosima dynamic-library preflight failed:\n{probe.stdout}{probe.stderr}")
    return env


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def paths(index: int) -> dict[str, Path | str]:
    job_id = f"m05new_sg3b_gamma_shard{index:04d}"
    job_dir = DATA_ROOT / "jobs" / job_id
    prefix = job_dir / job_id
    return {
        "job_id": job_id,
        "run_name": f"M05NEW_SG3B_instant_gamma_{index:04d}",
        "job_dir": job_dir,
        "prefix": prefix,
        "source": CONFIG_DIR / f"{job_id}.source",
        "sim": Path(str(prefix) + ".inc1.id1.sim.gz"),
        "activation": Path(str(prefix) + ".dat.inc1.dat"),
        "receipt": RECEIPT_DIR / f"{job_id}.json",
        "stderr": LOG_DIR / f"{job_id}.stderr.log",
    }


def build_source(index: int) -> dict[str, Path | str]:
    p = paths(index)
    text = TEMPLATE.read_text(encoding="utf-8")
    old_run = "SG3B_instant_gamma_0001"
    text = text.replace(old_run, str(p["run_name"]))
    text = re.sub(r"(?m)^Seed\s+\d+\s*$", f"Seed {SEEDS[index - 1]}", text, count=1)
    text = re.sub(r"(?m)^([^\s]+\.FileName)\s+\S+\s*$", rf"\1 {p['prefix']}", text, count=1)
    text = re.sub(r"(?m)^([^\s]+\.IsotopeProductionFile)\s+\S+\s*$", rf"\1 {p['prefix']}.dat", text, count=1)
    if f"Geometry {GEOMETRY}" not in text:
        raise RuntimeError("template geometry is not the retained SG3B setup")
    if "cosima_spectra_dp_2602units" in text:
        raise RuntimeError("legacy factor-1000 spectrum path found")
    refs = re.findall(r"(?m)^\S+\.Spectrum File\s+(\S+)$", text)
    if len(refs) != 20 or any("correct_keV_total" not in ref for ref in refs):
        raise RuntimeError("corrected-keV 20-bin gamma source contract failed")
    Path(p["job_dir"]).mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    Path(p["source"]).write_text(text, encoding="utf-8")
    return p


def run_one(index: int) -> dict[str, object]:
    p = build_source(index)
    receipt_path = Path(p["receipt"])
    if receipt_path.exists():
        old = json.loads(receipt_path.read_text(encoding="utf-8"))
        if (
            old.get("status") == "PASS"
            and int(old.get("source_seed", -1)) == SEEDS[index - 1]
            and int(old.get("sim_header_seed", -2)) == SEEDS[index - 1]
            and Path(str(p["sim"])).exists()
        ):
            return old
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    RECEIPT_DIR.mkdir(parents=True, exist_ok=True)
    started = time.time()
    with Path(p["stderr"]).open("wb") as stderr:
        proc = subprocess.run(
            [str(COSIMA), "-s", str(SEEDS[index - 1]), str(p["source"])],
            cwd=ROOT,
            env=cosima_environment(),
            stdout=subprocess.DEVNULL,
            stderr=stderr,
            check=False,
        )
    ended = time.time()
    sim = Path(p["sim"])
    header_geometry = None
    header_seed = None
    if proc.returncode == 0 and sim.exists():
        with gzip.open(sim, "rt") as handle:
            for line in handle:
                if line.startswith("Geometry"):
                    header_geometry = line.split(maxsplit=1)[1].strip()
                elif line.startswith("Seed"):
                    header_seed = int(line.split()[1])
                elif line.startswith("ID "):
                    break
    status = "PASS" if (
        proc.returncode == 0 and sim.exists() and sim.stat().st_size > 0
        and header_geometry == str(GEOMETRY)
        and header_seed == SEEDS[index - 1]
    ) else "FAIL"
    result = {
        "schema_version": 1,
        "status": status,
        "job_id": p["job_id"],
        "index": index,
        "source_seed": SEEDS[index - 1],
        "sim_header_seed": header_seed,
        "events_requested": EVENTS_PER_SHARD,
        "returncode": proc.returncode,
        "wall_seconds": ended - started,
        "geometry": str(GEOMETRY),
        "header_geometry": header_geometry,
        "source": str(p["source"]),
        "source_sha256": sha256(Path(p["source"])),
        "sim": str(sim),
        "sim_bytes": sim.stat().st_size if sim.exists() else 0,
        "sim_sha256": sha256(sim) if status == "PASS" else None,
        "activation": str(p["activation"]),
        "stderr": str(p["stderr"]),
        "started_unix": started,
        "ended_unix": ended,
    }
    receipt_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if status != "PASS":
        raise RuntimeError(json.dumps(result, indent=2))
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--count", type=int, required=True)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    indices = list(range(args.start, args.start + args.count))
    if not indices or indices[-1] > len(SEEDS):
        raise SystemExit("requested shard range exceeds registered seeds")
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        future_index = {pool.submit(run_one, index): index for index in indices}
        for future in concurrent.futures.as_completed(future_index):
            result = future.result()
            results.append(result)
            print(json.dumps({
                "completed": result["job_id"],
                "status": result["status"],
                "wall_seconds": result["wall_seconds"],
                "sim_GiB": result["sim_bytes"] / 2**30,
            }), flush=True)
    results.sort(key=lambda row: int(row["index"]))
    campaign = {
        "schema_version": 1,
        "status": "PASS" if all(row["status"] == "PASS" for row in results) else "FAIL",
        "indices": indices,
        "events_per_shard": EVENTS_PER_SHARD,
        "events_requested": EVENTS_PER_SHARD * len(indices),
        "receipts": [str(RECEIPT_DIR / f"{row['job_id']}.json") for row in results],
        "sim_bytes": sum(int(row["sim_bytes"]) for row in results),
    }
    out = PACKAGE / f"outputs/02_gamma_transport/campaign_{indices[0]:04d}_{indices[-1]:04d}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(campaign, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(campaign, indent=2), flush=True)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Run the two SG3 minimal-SD alpha pilot arms sequentially."""

from __future__ import annotations

import json
import argparse
import os
import re
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
MANIFEST = PACKAGE / "PILOT_MANIFEST.json"
STATE = PACKAGE / "PILOT_RUN_STATE.json"
MEGALIB_ENV = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh")
COSIMA = Path("/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima")


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, payload: dict) -> None:
    partial = path.with_name(f".{path.name}.{os.getpid()}.partial")
    partial.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    os.replace(partial, path)


def publish(status: str, jobs: list[dict], current: str | None, error: str | None = None) -> None:
    atomic_json(
        STATE,
        {
            "schema_version": 1,
            "status": status,
            "updated_at": now(),
            "current_job": current,
            "jobs": jobs,
            "error": error,
        },
    )


def main() -> int:
    global MANIFEST, STATE
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    parser.add_argument("--state", type=Path, default=STATE)
    args = parser.parse_args()
    MANIFEST = args.manifest.resolve()
    STATE = args.state.resolve()
    manifest = json.loads(MANIFEST.read_text())
    results: list[dict] = []
    if STATE.exists():
        previous = json.loads(STATE.read_text())
        if previous.get("status") == "COMPLETE":
            print(json.dumps(previous, indent=2, sort_keys=True))
            return 0
    publish("STARTING", results, None)
    try:
        for job in manifest["jobs"]:
            job_id = job["job_id"]
            output_root = Path(job["output_root"])
            active = output_root / "active"
            passed = output_root / "pass"
            if passed.exists():
                results.append({"job_id": job_id, "status": "ALREADY_PASS", "path": str(passed)})
                continue
            if active.exists():
                prior_log = active / f"{job_id}.stdout_time.log"
                prior_text = prior_log.read_text(encoding="utf-8", errors="replace")
                prior_generated = re.search(
                    r"(?:Generated events|Total number of generated particles):\s*(\d+)",
                    prior_text,
                )
                prior_sims = sorted(active.glob("*.sim")) + sorted(active.glob("*.sim.gz"))
                if (
                    prior_generated is not None
                    and int(prior_generated.group(1)) == int(manifest["events"])
                    and len(prior_sims) == 1
                    and prior_sims[0].stat().st_size > 0
                    and re.search(r"Exit status:\s*0\s*$", prior_text, re.MULTILINE)
                ):
                    prior_rss = re.search(
                        r"Maximum resident set size \(kbytes\):\s*(\d+)", prior_text
                    )
                    prior_elapsed = re.search(
                        r"Elapsed \(wall clock\) time.*\):\s*([^\n]+)", prior_text
                    )
                    prior_sim_bytes = prior_sims[0].stat().st_size
                    shutil.move(str(active), str(passed))
                    results.append(
                        {
                            "job_id": job_id,
                            "status": "PASS_RECOVERED_FROM_PARSER_FALSE_FAILURE",
                            "generated_events": int(prior_generated.group(1)),
                            "maximum_rss_kib": int(prior_rss.group(1)) if prior_rss else None,
                            "elapsed": prior_elapsed.group(1).strip() if prior_elapsed else None,
                            "sim_bytes": prior_sim_bytes,
                            "path": str(passed),
                        }
                    )
                    publish("RUNNING", results, None)
                    continue
                raise FileExistsError(f"unvalidated residual active directory: {active}")
            active.mkdir(parents=True)
            log_path = active / f"{job_id}.stdout_time.log"
            command = (
                "set -e; "
                f"source {shlex.quote(str(MEGALIB_ENV))}; "
                "export LC_ALL=C; "
                f"exec /usr/bin/time -v {shlex.quote(str(COSIMA))} "
                f"-s {int(manifest['seed'])} "
                f"{shlex.quote(job['source'])}"
            )
            started = now()
            publish("RUNNING", results, job_id)
            with log_path.open("w", encoding="utf-8") as log:
                process = subprocess.run(
                    ["bash", "-lc", command],
                    cwd="/home/ubuntu/.codex/worktrees/ebb2/TES_511_Balloon",
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )
            text = log_path.read_text(encoding="utf-8", errors="replace")
            generated = re.search(
                r"(?:Generated events|Total number of generated particles):\s*(\d+)",
                text,
            )
            max_rss = re.search(r"Maximum resident set size \(kbytes\):\s*(\d+)", text)
            elapsed = re.search(r"Elapsed \(wall clock\) time.*\):\s*([^\n]+)", text)
            sim_paths = sorted(active.glob("*.sim")) + sorted(active.glob("*.sim.gz"))
            errors = []
            if process.returncode != 0:
                errors.append(f"returncode={process.returncode}")
            if generated is None or int(generated.group(1)) != int(manifest["events"]):
                errors.append(f"generated={generated.group(1) if generated else None}")
            if len(sim_paths) != 1 or sim_paths[0].stat().st_size <= 0:
                errors.append(f"sim_artifacts={len(sim_paths)}")
            row = {
                "job_id": job_id,
                "status": "FAIL" if errors else "PASS",
                "started_at": started,
                "ended_at": now(),
                "returncode": process.returncode,
                "generated_events": int(generated.group(1)) if generated else None,
                "maximum_rss_kib": int(max_rss.group(1)) if max_rss else None,
                "elapsed": elapsed.group(1).strip() if elapsed else None,
                "sim_bytes": sim_paths[0].stat().st_size if len(sim_paths) == 1 else None,
                "errors": errors,
            }
            if errors:
                results.append(row)
                publish("FAILED", results, job_id, "; ".join(errors))
                return 1
            shutil.move(str(active), str(passed))
            row["path"] = str(passed)
            results.append(row)
            publish("RUNNING", results, None)
        publish("COMPLETE", results, None)
        print(json.dumps(json.loads(STATE.read_text()), indent=2, sort_keys=True))
        return 0
    except BaseException as exc:
        publish("FAILED", results, None, str(exc))
        raise


if __name__ == "__main__":
    raise SystemExit(main())

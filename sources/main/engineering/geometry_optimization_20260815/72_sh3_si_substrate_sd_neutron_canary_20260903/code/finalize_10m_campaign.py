#!/usr/bin/env python3
"""Wait for the protected 10M controller, then run the bound summarizer."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
PRODUCTION = PACKAGE / "production_10m"
CONTROLLER_STATE = PRODUCTION / "run/controller_state.json"
FINALIZER_STATE = PRODUCTION / "FINALIZER_STATE.json"
FINALIZER_LOG = PRODUCTION / "finalizer.log"
SUMMARIZER = Path(__file__).with_name("summarize_10m_campaign.py")
SERVICE = "sh3-sisd-n10m-20260903.service"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def publish(status: str, **extra: object) -> None:
    payload = {"schema_version": 1, "status": status, "updated_at": utc_now(), **extra}
    temporary = FINALIZER_STATE.with_suffix(".json.partial")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, FINALIZER_STATE)


def service_active() -> bool:
    result = subprocess.run(
        ("systemctl", "--user", "is-active", "--quiet", SERVICE),
        check=False,
    )
    return result.returncode == 0


def main() -> int:
    publish("WAITING_FOR_TRANSPORT", controller_state=str(CONTROLLER_STATE))
    while True:
        state = (
            json.loads(CONTROLLER_STATE.read_text(encoding="utf-8"))
            if CONTROLLER_STATE.is_file()
            else {"status": "NOT_STARTED"}
        )
        status = state.get("status")
        if status == "COMPLETE":
            if state.get("completed_count") != 99 or state.get("error") is not None:
                publish("FAILED", error="controller COMPLETE evidence is inconsistent")
                return 1
            break
        if status == "FAILED":
            publish("FAILED", error=state.get("error", "transport controller failed"))
            return 1
        if not service_active():
            publish("FAILED", error=f"transport service inactive with controller status {status}")
            return 1
        time.sleep(30)

    publish("SUMMARIZING", completed_transport_jobs=99)
    with FINALIZER_LOG.open("x", encoding="utf-8") as handle:
        result = subprocess.run(
            (sys.executable, str(SUMMARIZER)),
            cwd=str(PACKAGE),
            stdout=handle,
            stderr=subprocess.STDOUT,
            check=False,
        )
    summary_path = PRODUCTION / "analysis_10m/si_deposition_summary_10m.json"
    if result.returncode != 0 or not summary_path.is_file():
        publish(
            "FAILED",
            error=f"summarizer failed with return code {result.returncode}",
            log=str(FINALIZER_LOG),
        )
        return 1
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if summary.get("status") != "PASS__SH3_SI_SD_NEUTRON_10M_SUMMARIZED":
        publish("FAILED", error="unexpected summarizer status", log=str(FINALIZER_LOG))
        return 1
    publish(
        "COMPLETE",
        completed_transport_jobs=99,
        combined_histories=10_000_000,
        summary=str(summary_path),
        log=str(FINALIZER_LOG),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

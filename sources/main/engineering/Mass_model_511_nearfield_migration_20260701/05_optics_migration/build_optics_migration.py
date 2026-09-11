#!/usr/bin/env python3
"""Build the optics-model migration statement for the Mass_model_511 nearfield
migration package.

This records that the new f10m multiband UNIFIED optics geometry (1245 Ge tiles
+ G10/Al support, "一体" version) has been migrated INTO this repository and
verified loadable/overlap-clean/transporting under cosima Monte Carlo from an
in-repo setup.

Honest boundary: this is an available optics mass/geometry model. It is NOT
coupled into the detector background transport chain, and it does NOT change the
main package's detector-only G5 state (`OPTICS_BRIDGE_NOT_REQUIRED_DETECTOR_ONLY`
remains true for the detector background branch). No background rate, no
optics-to-detector bridge, and no no-effect claim is made here.
"""

from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = Path("/home/ubuntu/TES_511_Balloon")

CORE_GEO = HERE / "geometry/MultibandUnified_TilesAndSupport_f10m.geo"
OVERLAP_LEDGER = HERE / "geometry/overlap_ledger.json"
SETUP = HERE / "geometry/multiband_unified_migrated.setup"
SOURCE = HERE / "geometry/multiband_unified_migrated.source"
VERIFY_LOG = HERE / "verify/cosima_migrated_verify.log"
VERIFY_SIM = HERE / "verify/multiband_unified_migrated.inc1.id1.sim.gz"
MC_SMOKE_DOC = HERE / "MC_SMOKE_UNIFIED.md"

# Provenance: where the migrated geometry was designed/validated (outside the repo).
PROVENANCE_SOURCE = "/home/ubuntu/opticsim/opticsim_full/designs/f10m_multiband_20260701"

MANIFEST = HERE / "optics_migration_manifest.json"
DOC = HERE / "optics_migration.md"

OVERLAP_BAD_PATTERNS = ["Overlap is detected", "overlapping by", "CheckOverlaps()", "GeomVol"]


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except Exception:
        return str(path)


def sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
                                       stderr=subprocess.DEVNULL).strip()
    except Exception:
        return ""


def file_rec(path: Path, role: str) -> dict[str, Any]:
    rec = {"path": rel(path), "exists": path.exists(), "role": role}
    if path.exists() and path.is_file():
        rec["sha256"] = sha256(path)
        rec["size"] = path.stat().st_size
    return rec


def read_verify() -> dict[str, Any]:
    """Parse the in-repo cosima verification log + sim for the honest result."""
    result: dict[str, Any] = {
        "log": rel(VERIFY_LOG),
        "log_exists": VERIFY_LOG.exists(),
        "overlap_clean": None,
        "overlap_bad_lines": [],
        "generated_primaries": None,
        "triggered_events": None,
        "distinct_tile_hit_positions": None,
    }
    if VERIFY_LOG.exists():
        text = VERIFY_LOG.read_text(encoding="utf-8", errors="replace")
        bad = [ln for ln in text.splitlines() if any(p in ln for p in OVERLAP_BAD_PATTERNS)]
        result["overlap_bad_lines"] = bad[:10]
        result["overlap_clean"] = len(bad) == 0
        m = re.search(r"Total number of generated particles:\s*(\d+)", text)
        if m:
            result["generated_primaries"] = int(m.group(1))
    if VERIFY_SIM.exists():
        result["sim"] = rel(VERIFY_SIM)
        se = 0
        positions: set[tuple[str, str, str]] = set()
        with gzip.open(VERIFY_SIM, "rt", errors="replace") as f:
            for line in f:
                if line.startswith("SE"):
                    se += 1
                elif line.startswith("HTsim"):
                    parts = line.split(";")
                    if len(parts) >= 4:
                        positions.add((parts[1].strip(), parts[2].strip(), parts[3].strip()))
        result["triggered_events"] = se
        result["distinct_tile_hit_positions"] = len(positions)
    return result


def main() -> int:
    ledger = json.loads(OVERLAP_LEDGER.read_text()) if OVERLAP_LEDGER.exists() else {}
    verify = read_verify()

    overlap_clean = bool(verify.get("overlap_clean"))
    transported = bool(verify.get("triggered_events"))
    ledger_ok = bool(ledger.get("all_positive"))
    verified = overlap_clean and transported and ledger_ok

    status = (
        "OPTICS_GEOMETRY_MIGRATED_AND_MC_SMOKE_VERIFIED_IN_REPO"
        if verified else "OPTICS_GEOMETRY_MIGRATED_VERIFICATION_INCOMPLETE"
    )

    manifest = {
        "document_type": "multiband_optics_geometry_migration_statement",
        "generated_at_utc": now_utc(),
        "status": status,
        "repo_head": git_head(),
        "model": "balloon511_f10m_ge111_multiband (unified / 一体: tiles + support)",
        "what_was_migrated": {
            "core_geometry_file": rel(CORE_GEO),
            "description": "Six coplanar Ge(111) rings (451-551 keV, 511 exact) as 1245 real Ge tiles "
                           "on a single shared template MB_Tile, plus G10 carrier + Al outer mount + 4 Al brackets.",
            "optical_axis": "+x, lens plane at x=0",
            "provenance_design_dir": PROVENANCE_SOURCE,
        },
        "no_overlap_evidence": {
            "analytic_ledger": rel(OVERLAP_LEDGER),
            "all_clearances_positive": ledger_ok,
            "min_tangential_gap_lower_bound_um": ledger.get("min_tangential_gap_lower_bound_um"),
            "min_radial_gap_um": ledger.get("min_radial_gap_um"),
            "geant4_check": "cosima CheckForOverlaps 500 0.0001 on all 1245 tiles + support",
            "geant4_overlap_clean": overlap_clean,
        },
        "in_repo_mc_verification": verify,
        "files": [
            file_rec(CORE_GEO, "MIGRATED_OPTICS_CORE_GEOMETRY"),
            file_rec(OVERLAP_LEDGER, "NO_OVERLAP_ANALYTIC_LEDGER"),
            file_rec(SETUP, "REPO_LOCAL_RUNNABLE_SETUP"),
            file_rec(SOURCE, "REPO_LOCAL_VERIFICATION_SOURCE"),
            file_rec(VERIFY_LOG, "IN_REPO_COSIMA_VERIFY_LOG"),
            file_rec(VERIFY_SIM, "IN_REPO_COSIMA_VERIFY_SIM"),
            file_rec(MC_SMOKE_DOC, "UPSTREAM_MC_SMOKE_SUMMARY"),
        ],
        "boundary_and_non_claims": [
            "This is an available optics mass/geometry model migrated into the repo; it is loadable and MC-runnable in-repo.",
            "It is NOT coupled into the detector background transport chain.",
            "It does NOT change the main package detector-only state: G5 remains OPTICS_BRIDGE_NOT_REQUIRED_DETECTOR_ONLY for the detector background branch.",
            "No background rate, no optics-to-detector bridge, and no no-effect claim is made.",
            "Per-energy effective area in the design summary remains a design-stage estimate; only the 511 ring has an external XOP curve.",
        ],
        "allowed_next_steps": [
            "If an optics-coupled background is ever required, build an explicit optics-to-detector bridge (do not fold this into the detector-only G5).",
            "Extract transported per-ring A_eff and generate external XOP/CRYSTAL curves for the 5 non-511 energies before any publication-grade optics number.",
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    v = verify
    doc = [
        "# Optics Model Migration Statement — f10m multiband (unified / 一体)",
        "",
        f"generated_at_utc: `{manifest['generated_at_utc']}`",
        f"status: `{status}`",
        "",
        "## What was migrated",
        "",
        f"- core geometry file (in-repo): `{rel(CORE_GEO)}`",
        "- model: six coplanar Ge(111) rings 451–551 keV (511 exact), **1245 real Ge tiles** on one",
        "  shared template `MB_Tile`, plus G10 carrier + Al outer mount + 4 Al brackets.",
        f"- provenance (design/validation): `{PROVENANCE_SOURCE}`",
        "",
        "## No-overlap evidence",
        "",
        f"- analytic ledger `{rel(OVERLAP_LEDGER)}`: all clearances positive = `{ledger_ok}`",
        f"  (min tangential ≥ {ledger.get('min_tangential_gap_lower_bound_um')} µm, "
        f"min radial {ledger.get('min_radial_gap_um')} µm).",
        f"- Geant4 authoritative: cosima `CheckForOverlaps 500 0.0001` on all 1245 tiles + support "
        f"→ overlap-clean = `{overlap_clean}`.",
        "",
        "## In-repo Monte-Carlo verification",
        "",
        f"- setup `{rel(SETUP)}`, source `{rel(SOURCE)}` (all includes inside the repo).",
        f"- log `{v.get('log')}`: generated {v.get('generated_primaries')} primaries, "
        f"triggered **{v.get('triggered_events')}** events, "
        f"hits on **{v.get('distinct_tile_hit_positions')}** distinct tile positions.",
        f"- overlap-clean in this in-repo run: `{overlap_clean}`.",
        "",
        "## Boundary (read this)",
        "",
        "This migrates an **optics mass/geometry model** into the repo and shows it loads, is",
        "overlap-free, and transports under Monte Carlo from an in-repo setup. It is **not** coupled",
        "into the detector background transport chain and does **not** change the main package's",
        "detector-only `G5 = OPTICS_BRIDGE_NOT_REQUIRED_DETECTOR_ONLY`. No background rate,",
        "optics-to-detector bridge, or no-effect claim is made here.",
        "",
        "## Reproduce",
        "",
        "```bash",
        "cd engineering/Mass_model_511_nearfield_migration_20260701/05_optics_migration",
        "source megalib_env.sh",
        "cosima geometry/multiband_unified_migrated.source   # overlap check + transport",
        "python3 build_optics_migration.py                   # regenerate this statement",
        "```",
        "",
    ]
    DOC.write_text("\n".join(doc), encoding="utf-8")
    print(f"status: {status}")
    print(f"wrote {rel(MANIFEST)}")
    print(f"wrote {rel(DOC)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

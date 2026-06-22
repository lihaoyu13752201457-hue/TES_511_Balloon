#!/usr/bin/env python3
"""Audit prompt-511 repack replica independence and seed handling."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WORK = ROOT / "outputs/reports/prompt511_repack_smoke_20260617"
L1_JSON = WORK / "prompt511_repack_l1_proxy_summary.json"
OUT_JSON = WORK / "prompt511_repack_seed_independence_audit.json"
OUT_MD = WORK / "prompt511_repack_seed_independence_audit.md"
REPACK_PREFIX_BYTES = 8 * 1024 * 1024

REPACK_HASH_CASES = {
    "legacy_eplus": ("eplus", WORK / "runs/instant_eplus_g10m_r4_rawline"),
    "legacy_n": ("n", WORK / "runs/instant_n_g10m_r16_l1plan"),
    "cli_seed_eplus": ("eplus", WORK / "runs/instant_eplus_g10m_r4_cli_seed"),
    "cli_seed_n": ("n", WORK / "runs/instant_n_g10m_r16_cli_seed"),
}
SEEDCHECK_DIRS = {
    "source_seed_eplus_g2e4_r2": WORK / "runs/seedcheck_source_seed_eplus_g2e4_r2",
    "cli_seed_eplus_g2e4_r2": WORK / "runs/seedcheck_cli_seed_eplus_g2e4_r2",
}


def rel(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def sha256_file(path: Path, max_bytes: int | None = None) -> str:
    h = hashlib.sha256()
    remaining = max_bytes
    with path.open("rb") as fh:
        while True:
            read_size = 1024 * 1024 if remaining is None else min(1024 * 1024, remaining)
            if read_size <= 0:
                break
            chunk = fh.read(read_size)
            if not chunk:
                break
            h.update(chunk)
            if remaining is not None:
                remaining -= len(chunk)
    return h.hexdigest()


def hash_sims(prompt_dir: Path, tag: str) -> dict[str, Any]:
    sims = sorted(prompt_dir.glob(f"Background_{tag}_fullsphere20_rep*_part01.inc1.id1.sim.gz"))
    rows = [{"path": rel(path), "prefix_sha256": sha256_file(path, REPACK_PREFIX_BYTES)} for path in sims]
    groups: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        groups[row["prefix_sha256"]].append(row["path"])
    return {
        "prompt_dir": rel(prompt_dir),
        "tag": tag,
        "exists": prompt_dir.exists(),
        "prefix_bytes": REPACK_PREFIX_BYTES,
        "sim_files": rows,
        "file_count": len(rows),
        "unique_prefix_sha256_count": len(groups),
        "duplicate_groups": [
            {"prefix_sha256": sha, "paths": paths}
            for sha, paths in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))
            if len(paths) > 1
        ],
    }


def selected_signature_groups(l1: dict[str, Any], tag: str) -> dict[str, Any]:
    rows = l1["particle_cases"][tag]["w_liner_repack"]["files"]
    groups: dict[str, list[str]] = defaultdict(list)
    file_rows = []
    for row in rows:
        sig = tuple(
            (
                int(ex["local_id"]),
                round(float(ex["tes_total_keV"]), 6),
                round(float(ex["active_veto_keV"]), 6),
                str(ex["side_compton_class"]),
            )
            for ex in row.get("selected_examples", [])
        )
        key = json.dumps(sig, separators=(",", ":"))
        groups[key].append(row["path"])
        file_rows.append(
            {
                "path": row["path"],
                "raw_events": row["raw_events"],
                "active_veto_pass_events": row["active_veto_pass_events"],
                "side_compton_fov_pass_events": row["side_compton_fov_pass_events"],
                "selected_signature": sig,
            }
        )
    return {
        "tag": tag,
        "file_count": len(rows),
        "unique_selected_signature_count": len(groups),
        "duplicate_selected_signature_groups": [
            {"signature": json.loads(sig), "paths": paths}
            for sig, paths in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))
            if len(paths) > 1
        ],
        "files": file_rows,
    }


def seedcheck(prompt_dir: Path) -> dict[str, Any]:
    sims = sorted(prompt_dir.glob("Background_eplus_fullsphere20_rep*_part01.inc1.id1.sim.gz"))
    rows = [{"path": rel(path), "sha256": sha256_file(path)} for path in sims]
    return {
        "prompt_dir": rel(prompt_dir),
        "file_count": len(rows),
        "unique_sha256_count": len({row["sha256"] for row in rows}),
        "sim_files": rows,
    }


def markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Prompt-511 Repack Seed Independence Audit",
        "",
        f"Status: `{payload['status']}`",
        "",
        "This audit checks whether prompt-repack replicas are independent. It is a",
        "method/provenance audit for the W-liner diagnostic, not a rate authority.",
        "",
        "## Repack SIM Hashes",
        "",
        f"Large repack SIMs use a prefix hash over `{REPACK_PREFIX_BYTES}` bytes,",
        "then cross-check selected-event signatures from the L1 proxy summary.",
        "",
        "| tag | files | unique prefix SHA256 | duplicate groups |",
        "|---|---:|---:|---:|",
    ]
    for tag, row in payload["repack_hashes"].items():
        lines.append(
            f"| {tag} | {row['file_count']} | {row['unique_prefix_sha256_count']} | "
            f"{len(row['duplicate_groups'])} |"
        )
    lines.extend(["", "## Selected-Event Signatures", ""])
    lines.extend(["| tag | files | unique selected signatures |", "|---|---:|---:|"])
    for tag, row in payload["selected_signature_groups"].items():
        lines.append(f"| {tag} | {row['file_count']} | {row['unique_selected_signature_count']} |")
    lines.extend(["", "## Seed Checks", ""])
    lines.extend(["| check | files | unique SHA256 | interpretation |", "|---|---:|---:|---|"])
    for name, row in payload["seedchecks"].items():
        interp = "different outputs" if row["unique_sha256_count"] == row["file_count"] else "repeated output"
        lines.append(f"| {name} | {row['file_count']} | {row['unique_sha256_count']} | {interp} |")
    lines.extend(
        [
            "",
            "## Conclusion",
            "",
            "- The source-card `Seed` field is not sufficient for independent replicas in",
            "  this runner path: the source-seed eplus check produced two identical SIM",
            "  hashes despite different kept source files.",
            "- Passing `-s <seed>` to `cosima` fixes the small seed check: the two CLI-seed",
            "  replicas have different SIM hashes.",
            "- Legacy W-liner eplus and n repack rows must be treated as repeated-seed",
            "  diagnostics. Their central rates are at best few-sequence estimates under",
            "  the replica weight convention, and their counting uncertainties/high-stat",
            "  claims are not valid.",
            "- CLI-seed repack rows, when present with one unique prefix hash per file,",
            "  replace the legacy repeated-seed rows for quantitative prompt diagnostics.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    l1 = json.loads(L1_JSON.read_text(encoding="utf-8"))
    repack_hashes = {
        name: hash_sims(path, tag)
        for name, (tag, path) in REPACK_HASH_CASES.items()
        if path.exists()
    }
    sig_groups = {
        tag: selected_signature_groups(l1, tag)
        for tag in l1.get("particle_cases", {})
    }
    seedchecks = {name: seedcheck(path) for name, path in SEEDCHECK_DIRS.items()}

    source_seed_ok = seedchecks["source_seed_eplus_g2e4_r2"]["unique_sha256_count"] == 2
    cli_seed_ok = seedchecks["cli_seed_eplus_g2e4_r2"]["unique_sha256_count"] == 2
    legacy_cases = {k: v for k, v in repack_hashes.items() if k.startswith("legacy_")}
    cli_cases = {k: v for k, v in repack_hashes.items() if k.startswith("cli_seed_")}
    legacy_independent = all(row["unique_prefix_sha256_count"] == row["file_count"] for row in legacy_cases.values())
    cli_independent = bool(cli_cases) and all(
        row["unique_prefix_sha256_count"] == row["file_count"] for row in cli_cases.values()
    )
    status = "FAIL_REPACK_REPLICA_INDEPENDENCE"
    if source_seed_ok:
        status = "UNEXPECTED_SOURCE_SEED_INDEPENDENT"
    elif cli_seed_ok and cli_independent and not legacy_independent:
        status = "PASS_CLI_SEED_REPACK_INDEPENDENT_LEGACY_NOT_INDEPENDENT"
    elif cli_seed_ok and not legacy_independent:
        status = "PASS_SEED_FIX_IDENTIFIED_REPACK_NOT_INDEPENDENT"

    payload = {
        "status": status,
        "l1_summary": rel(L1_JSON),
        "repack_hashes": repack_hashes,
        "selected_signature_groups": sig_groups,
        "seedchecks": seedchecks,
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(markdown(payload), encoding="utf-8")
    print(f"wrote {rel(OUT_JSON)}")
    print(f"wrote {rel(OUT_MD)}")
    print(f"status={status}")
    pass_statuses = {
        "PASS_SEED_FIX_IDENTIFIED_REPACK_NOT_INDEPENDENT",
        "PASS_CLI_SEED_REPACK_INDEPENDENT_LEGACY_NOT_INDEPENDENT",
    }
    return 0 if status in pass_statuses else 1


if __name__ == "__main__":
    raise SystemExit(main())

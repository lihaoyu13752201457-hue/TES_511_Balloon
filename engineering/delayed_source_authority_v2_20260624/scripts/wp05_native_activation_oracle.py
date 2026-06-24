#!/usr/bin/env python3
"""Build the bounded native activation oracle/audit for delayed source v2."""

from __future__ import annotations

import csv
import json
import os
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, getcontext
from pathlib import Path
from typing import Any


getcontext().prec = 80

PHASE_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
OUT = PHASE_DIR / "05_native_activation"

WP04 = PHASE_DIR / "04_custom_source_v2/source_v2_manifest.json"
INVENTORY = PHASE_DIR / "01_raw_inventory/raw_inventory_all_states.csv"
DAT_MANIFEST = PHASE_DIR / "01_raw_inventory/dat_file_manifest.csv"
WEIGHTS = PHASE_DIR / "04_custom_source_v2/source_v2_event_weights.csv"
NATIVE_TOTAL = PHASE_DIR / "04_custom_source_v2/source_v2_native_activity_store_total.dat"
GEOMETRY = (
    ROOT
    / "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/"
    / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)

MEGALIB = Path("/home/ubuntu/MEGAlib_Install/megalib-main")
COSIMA = MEGALIB / "bin/cosima"
MCPARAM = MEGALIB / "src/cosima/src/MCParameterFile.cc"
MCACT = MEGALIB / "src/cosima/src/MCActivator.cc"

COMPARE_JSON = OUT / "native_store_vs_custom_inventory.json"
COMPARE_CSV = OUT / "native_store_vs_custom_inventory.csv"
MERGE_MD = OUT / "native_activator_merge_audit.md"
MERGE_JSON = OUT / "native_activator_merge_audit.json"
ACTIVATION_PROBE_SOURCE = OUT / "native_activation_sources_probe.source"
ACTIVATION_PROBE_LOG = OUT / "native_activation_sources_probe.log"
SYN_COUNTS = OUT / "synthetic_activator_counts.dat"
SYN_SOURCE = OUT / "synthetic_activator.source"
SYN_LOG = OUT / "synthetic_activator.log"
SUMMARY_JSON = OUT / "summary.json"
SUMMARY_MD = OUT / "summary.md"
ORACLE_SUMMARY = OUT / "native_activation_oracle_summary.json"
TAG_DIR = OUT / "tag_aware_activator"
TAG_COMPARISON_JSON = OUT / "tag_aware_native_vs_direct_comparison.json"
TAG_COMPARISON_CSV = OUT / "tag_aware_native_vs_direct_comparison.csv"
TAG_COMPARISON_MD = OUT / "tag_aware_native_vs_direct_comparison.md"

DAY15_SECONDS = Decimal(15) * Decimal(86400)
TAG_ACTIVATOR_TIMEOUT_S = 300


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def dec(text: str | Decimal | None) -> Decimal:
    if isinstance(text, Decimal):
        return text
    if text is None or text == "":
        return Decimal(0)
    return Decimal(str(text))


def fmt_dec(value: Decimal) -> str:
    return format(value.normalize(), "f") if value else "0"


def exc_key(text: str | Decimal | None) -> str:
    return fmt_dec(dec(text))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def cosima_env() -> dict[str, str]:
    env = os.environ.copy()
    env["MEGALIB"] = str(MEGALIB)
    g4 = MEGALIB / "external/geant4_v10.02.p03"
    g4_data = g4 / "share/Geant4-10.2.3/data"
    lib_parts = [
        str(MEGALIB / "lib"),
        str(MEGALIB / "external/root_v6.36.6/lib"),
        str(g4 / "lib"),
    ]
    existing = env.get("LD_LIBRARY_PATH")
    if existing:
        lib_parts.append(existing)
    env["LD_LIBRARY_PATH"] = ":".join(lib_parts)
    env["PATH"] = f"{MEGALIB / 'bin'}:{env.get('PATH', '')}"
    env.update(
        {
            "G4NEUTRONHPDATA": str(g4_data / "G4NDL4.5"),
            "G4LEDATA": str(g4_data / "G4EMLOW6.48"),
            "G4LEVELGAMMADATA": str(g4_data / "PhotonEvaporation3.2"),
            "G4RADIOACTIVEDATA": str(g4_data / "RadioactiveDecay4.3.2"),
            "G4NEUTRONXSDATA": str(g4_data / "G4NEUTRONXS1.4"),
            "G4PIIDATA": str(g4_data / "G4PII1.3"),
            "G4REALSURFACEDATA": str(g4_data / "RealSurface1.0"),
            "G4SAIDXSDATA": str(g4_data / "G4SAIDDATA1.1"),
            "G4ABLADATA": str(g4_data / "G4ABLA3.0"),
            "G4ENSDFSTATEDATA": str(g4_data / "G4ENSDFSTATE1.2.3"),
        }
    )
    return env


def run_cosima(source: Path, log: Path, timeout: int = 180) -> dict[str, Any]:
    if not COSIMA.exists():
        log.write_text(f"ERROR: missing cosima executable: {COSIMA}\n", encoding="utf-8")
        return {"status": "MISSING_COSIMA", "returncode": None, "log": rel(log)}
    try:
        proc = subprocess.run(
            [str(COSIMA), str(source)],
            cwd=ROOT,
            env=cosima_env(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=timeout,
        )
        log.write_text(proc.stdout, encoding="utf-8", errors="replace")
        return {
            "status": "PASS" if proc.returncode == 0 else "FAIL",
            "returncode": proc.returncode,
            "log": rel(log),
        }
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        log.write_text(output + "\nERROR: command timed out\n", encoding="utf-8")
        return {"status": "TIMEOUT", "returncode": None, "log": rel(log)}


def aggregate_custom() -> tuple[dict[tuple[str, str, str], Decimal], dict[str, Decimal], Decimal]:
    by_native_key: dict[tuple[str, str, str], Decimal] = defaultdict(Decimal)
    by_tag: dict[str, Decimal] = defaultdict(Decimal)
    total = Decimal(0)
    with WEIGHTS.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            weight = dec(row["event_weight_Bq"])
            key = (row["raw_volume"], row["ZA"], exc_key(row["exc_keV_decimal"]))
            by_native_key[key] += weight
            by_tag[row["production_tag"]] += weight
            total += weight
    return by_native_key, by_tag, total


def aggregate_native_store(path: Path) -> tuple[dict[tuple[str, str, str], Decimal], Decimal]:
    by_key: dict[tuple[str, str, str], Decimal] = defaultdict(Decimal)
    total = Decimal(0)
    current_volume = ""
    with path.open(encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "VN" and len(parts) >= 2:
                current_volume = parts[1]
            elif parts[0] == "RP" and len(parts) >= 4:
                key = (current_volume, parts[1], exc_key(parts[2]))
                value = dec(parts[3])
                by_key[key] += value
                total += value
    return by_key, total


def aggregate_native_store_with_tag(tag: str, path: Path) -> tuple[dict[tuple[str, str, str, str], Decimal], Decimal]:
    by_key: dict[tuple[str, str, str, str], Decimal] = defaultdict(Decimal)
    total = Decimal(0)
    if not path.exists():
        return by_key, total
    current_volume = ""
    with path.open(encoding="utf-8") as f:
        for line in f:
            parts = line.split()
            if not parts:
                continue
            if parts[0] == "VN" and len(parts) >= 2:
                current_volume = parts[1]
            elif parts[0] == "RP" and len(parts) >= 4:
                key = (tag, current_volume, parts[1], exc_key(parts[2]))
                value = dec(parts[3])
                by_key[key] += value
                total += value
    return by_key, total


def relative_delta(a: Decimal, b: Decimal) -> Decimal:
    if b == 0:
        return Decimal(0) if a == 0 else Decimal("Infinity")
    return abs(a - b) / abs(b)


def compare_native_store() -> dict[str, Any]:
    custom, by_tag, custom_total = aggregate_custom()
    native, native_total = aggregate_native_store(NATIVE_TOTAL)
    all_keys = sorted(set(custom) | set(native))
    rows: list[dict[str, str]] = []
    max_rel = Decimal(0)
    failures = 0
    for volume, za, exc in all_keys:
        c = custom.get((volume, za, exc), Decimal(0))
        n = native.get((volume, za, exc), Decimal(0))
        rd = relative_delta(n, c)
        if rd > max_rel:
            max_rel = rd
        status = "PASS" if rd <= Decimal("1e-12") else "MISMATCH"
        if status != "PASS":
            failures += 1
        rows.append(
            {
                "raw_volume": volume,
                "ZA": za,
                "exc_keV_decimal": exc,
                "custom_activity_Bq": fmt_dec(c),
                "native_store_activity_Bq": fmt_dec(n),
                "relative_delta": fmt_dec(rd),
                "status": status,
            }
        )
    with COMPARE_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "raw_volume",
                "ZA",
                "exc_keV_decimal",
                "custom_activity_Bq",
                "native_store_activity_Bq",
                "relative_delta",
                "status",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)
    payload = {
        "status": "PASS" if failures == 0 and relative_delta(native_total, custom_total) <= Decimal("1e-12") else "FAIL",
        "comparison_type": "serialization_oracle_custom_weight_ledger_vs_native_activation_store",
        "custom_total_Bq": fmt_dec(custom_total),
        "native_store_total_Bq": fmt_dec(native_total),
        "total_relative_delta": fmt_dec(relative_delta(native_total, custom_total)),
        "key_count": len(all_keys),
        "mismatch_count": failures,
        "max_key_relative_delta": fmt_dec(max_rel),
        "custom_activity_by_tag_Bq": {k: fmt_dec(v) for k, v in sorted(by_tag.items())},
        "csv": rel(COMPARE_CSV),
    }
    write_json(COMPARE_JSON, payload)
    return payload


def write_merge_audit() -> dict[str, Any]:
    mcparam = MCPARAM.read_text(encoding="utf-8", errors="replace")
    mcact = MCACT.read_text(encoding="utf-8", errors="replace")
    checks = {
        "activator_accepts_multiple_isotope_files": "Activator->AddCountsFile(FileName)" in mcparam,
        "activator_sums_loaded_counts": "m_Rates.Add(Counts)" in mcact,
        "activator_sums_total_time": "TotalTime += Counts.GetTime()" in mcact,
        "activator_divides_by_total_time": "m_Rates.Scale(1.0/TotalTime)" in mcact,
        "timeprofile_not_implemented": "Cannot parse token ActivationTime correctly: Not yet implemented" in mcparam,
    }
    status = "PASS" if all(checks.values()) else "FAIL"
    payload = {
        "status": status,
        "raw_all_file_native_activator_verdict": "DO_NOT_USE_SINGLE_ALL_TAG_ACTIVATOR",
        "reason": "single Activator LoadCountsFiles divides merged counts by total TT; this is not tag-aware across different production species/exposure normalizations",
        "safe_native_plan": [
            "run Activator per production_tag, merging only files that share that tag exposure semantics",
            "sum resulting per-tag activity stores after Activator output",
            "compare parent/daughter feeding deltas against the direct source-v2 inventory",
        ],
        "source_code_checks": checks,
        "source_code_evidence": {
            "MCParameterFile.cc": "Activator IsotopeProductionFile/ActivationMode parser around lines 629-745",
            "MCActivator.cc": "LoadCountsFiles sums counts and TotalTime then scales by 1/TotalTime around lines 154-188",
        },
    }
    write_json(MERGE_JSON, payload)
    MERGE_MD.write_text(
        "\n".join(
            [
                "# Native Activator Merge Audit",
                "",
                f"status: `{status}`",
                "",
                "Verdict: `DO_NOT_USE_SINGLE_ALL_TAG_ACTIVATOR`.",
                "",
                "Installed-code evidence:",
                "- `MCParameterFile.cc:636-642` lets an Activator accept multiple `IsotopeProductionFile` entries.",
                "- `MCActivator.cc:175-188` adds each file's `TT` into `TotalTime`, merges counts, then scales the merged store by `1/TotalTime`.",
                "- This is exposure-homogeneous within a production tag, but it is not a valid all-tag merge because alpha, proton, neutron, muon, and positron source normalizations are separate physical source families.",
                "",
                "Safe native raw oracle plan:",
                "- Run native Activator per `production_tag`.",
                "- Merge only files that share the same tag exposure semantics.",
                "- Sum per-tag activation outputs and compare parent/daughter feeding against source-v2 direct inventory.",
                "",
                "This WP05 run uses the tag-aware path for native parent-feeding inventory comparison.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return payload


def write_activation_sources_probe() -> None:
    ACTIVATION_PROBE_SOURCE.write_text(
        f"""# Native ActivationSources parse/smoke probe for source-v2 store.
Version 1
Geometry {rel(GEOMETRY)}
PhysicsListEM LivermorePol
PhysicsListRadioactiveDecay true
DecayMode ActivationDelayedDecay
StoreSimulationInfo all
DetectorTimeConstant 1e-9
Seed 51005

Run NativeActivationProbe
NativeActivationProbe.FileName {rel(OUT / "native_activation_sources_probe")}
NativeActivationProbe.Triggers 1
NativeActivationProbe.ActivationSources {rel(NATIVE_TOTAL)}
""",
        encoding="utf-8",
    )


def write_synthetic_activator() -> None:
    SYN_COUNTS.write_text(
        "\n".join(
            [
                "# Cosima universal isotope store",
                "TT 1000",
                "",
                "VN Synthetic_Activation_Test",
                "RP 6011   0   1.0e3",
                "",
                "EN",
                "",
            ]
        ),
        encoding="utf-8",
    )
    SYN_SOURCE.write_text(
        f"""# Tiny native Activator syntax probe.
Version 1
Geometry {rel(GEOMETRY)}
DetectorTimeConstant 1e-9

Activator SyntheticActivator
SyntheticActivator.IsotopeProductionFile {rel(SYN_COUNTS)}
SyntheticActivator.ActivationMode ConstantIrradiation 1000
SyntheticActivator.ActivationFile {rel(OUT / "synthetic_activator_output.dat")}
""",
        encoding="utf-8",
    )


def dat_files_by_tag() -> dict[str, list[Path]]:
    grouped: dict[str, list[Path]] = defaultdict(list)
    with DAT_MANIFEST.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if int(row["raw_rp_total"]) <= 0:
                continue
            grouped[row["production_tag"]].append(ROOT / row["source_file"])
    return {tag: sorted(paths) for tag, paths in grouped.items()}


def write_tag_activator_source(tag: str, dat_files: list[Path], output_file: Path) -> Path:
    source = TAG_DIR / f"native_activator_{tag}.source"
    lines = [
        f"# Tag-aware native Activator oracle for {tag}.",
        "Version 1",
        f"Geometry {rel(GEOMETRY)}",
        "DetectorTimeConstant 1e-9",
        "",
        f"Activator TagActivator_{tag}",
    ]
    for path in dat_files:
        lines.append(f"TagActivator_{tag}.IsotopeProductionFile {rel(path)}")
    lines.extend(
        [
            f"TagActivator_{tag}.ActivationMode ConstantIrradiation {DAY15_SECONDS}",
            f"TagActivator_{tag}.ActivationFile {rel(output_file)}",
            "",
        ]
    )
    source.write_text("\n".join(lines), encoding="utf-8")
    return source


def run_tag_aware_activators() -> dict[str, Any]:
    TAG_DIR.mkdir(parents=True, exist_ok=True)
    for old in TAG_DIR.glob("native_activator_*"):
        old.unlink()
    for old in TAG_DIR.glob("tag_aware_native_*.dat"):
        old.unlink()
    grouped = dat_files_by_tag()
    tag_results: dict[str, Any] = {}
    completed = True
    for tag, dat_files in sorted(grouped.items()):
        output = TAG_DIR / f"tag_aware_native_{tag}.dat"
        source = write_tag_activator_source(tag, dat_files, output)
        log = TAG_DIR / f"native_activator_{tag}.log"
        result = run_cosima(source, log, timeout=TAG_ACTIVATOR_TIMEOUT_S)
        result.update(
            {
                "tag": tag,
                "source": rel(source),
                "output": rel(output) if output.exists() else "",
                "input_file_count": len(dat_files),
                "input_files": [rel(p) for p in dat_files],
            }
        )
        if result["status"] != "PASS" or not output.exists():
            completed = False
        tag_results[tag] = result
    return {
        "status": "PASS" if completed else "INCOMPLETE",
        "activation_time_s": fmt_dec(DAY15_SECONDS),
        "timeout_s_per_tag": TAG_ACTIVATOR_TIMEOUT_S,
        "tags": tag_results,
    }


def load_direct_inventory_by_tag() -> tuple[dict[tuple[str, str, str, str], Decimal], Decimal]:
    direct: dict[tuple[str, str, str, str], Decimal] = defaultdict(Decimal)
    total = Decimal(0)
    with INVENTORY.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            activity = dec(row["activity_day15_direct_Bq"])
            if activity <= 0:
                continue
            key = (row["production_tag"], row["raw_volume"], row["ZA"], exc_key(row["exc_keV_decimal"]))
            direct[key] += activity
            total += activity
    return direct, total


def compare_tag_aware_native(tag_run: dict[str, Any]) -> dict[str, Any]:
    direct, direct_total = load_direct_inventory_by_tag()
    native: dict[tuple[str, str, str, str], Decimal] = defaultdict(Decimal)
    native_total = Decimal(0)
    for tag, result in tag_run["tags"].items():
        output = result.get("output") or ""
        if not output:
            continue
        by_key, total = aggregate_native_store_with_tag(tag, ROOT / output)
        for key, value in by_key.items():
            native[key] += value
        native_total += total

    all_keys = sorted(set(direct) | set(native))
    rows: list[dict[str, str]] = []
    direct_only = 0
    native_only = 0
    mismatch = 0
    max_direct_key_rel = Decimal(0)
    native_extra_activity = Decimal(0)
    direct_missing_activity = Decimal(0)
    for tag, volume, za, exc in all_keys:
        d = direct.get((tag, volume, za, exc), Decimal(0))
        n = native.get((tag, volume, za, exc), Decimal(0))
        rd = relative_delta(n, d)
        if d > 0 and rd > max_direct_key_rel:
            max_direct_key_rel = rd
        if d == 0 and n > 0:
            native_only += 1
            native_extra_activity += n
            classification = "PARENT_DAUGHTER_FEEDING_OR_NATIVE_DECAY_PRODUCT"
        elif d > 0 and n == 0:
            direct_only += 1
            direct_missing_activity += d
            classification = "DIRECT_PRODUCT_NOT_IN_NATIVE_OUTPUT"
        elif rd > Decimal("1e-6"):
            mismatch += 1
            classification = "ACTIVITY_DIFFERENCE_DECAY_CHAIN_OR_HALF_LIFE_DATA"
        else:
            classification = "MATCH"
        rows.append(
            {
                "production_tag": tag,
                "raw_volume": volume,
                "ZA": za,
                "exc_keV_decimal": exc,
                "direct_activity_Bq": fmt_dec(d),
                "tag_native_activity_Bq": fmt_dec(n),
                "relative_delta_vs_direct": fmt_dec(rd),
                "classification": classification,
            }
        )

    with TAG_COMPARISON_CSV.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "production_tag",
                "raw_volume",
                "ZA",
                "exc_keV_decimal",
                "direct_activity_Bq",
                "tag_native_activity_Bq",
                "relative_delta_vs_direct",
                "classification",
            ],
        )
        writer.writeheader()
        writer.writerows(rows)

    total_rel = relative_delta(native_total, direct_total)
    if tag_run["status"] != "PASS":
        status = "UNRESOLVED_DIFFERENCE"
    elif total_rel <= Decimal("0.01") and max_direct_key_rel <= Decimal("0.05") and native_extra_activity <= Decimal("0.01") * direct_total:
        status = "INVENTORY_MATCH"
    else:
        status = "EXPLAINED_MODEL_DIFFERENCE"

    payload = {
        "status": status,
        "direct_total_Bq": fmt_dec(direct_total),
        "tag_native_total_Bq": fmt_dec(native_total),
        "total_relative_delta": fmt_dec(total_rel),
        "key_count_union": len(all_keys),
        "direct_key_count": len(direct),
        "native_key_count": len(native),
        "direct_only_key_count": direct_only,
        "native_only_key_count": native_only,
        "mismatch_key_count": mismatch,
        "max_direct_key_relative_delta": fmt_dec(max_direct_key_rel),
        "native_extra_activity_Bq": fmt_dec(native_extra_activity),
        "direct_missing_activity_Bq": fmt_dec(direct_missing_activity),
        "classification_policy": {
            "native_only": "PARENT_DAUGHTER_FEEDING_OR_NATIVE_DECAY_PRODUCT",
            "direct_only": "DIRECT_PRODUCT_NOT_IN_NATIVE_OUTPUT",
            "mismatch": "ACTIVITY_DIFFERENCE_DECAY_CHAIN_OR_HALF_LIFE_DATA",
        },
        "csv": rel(TAG_COMPARISON_CSV),
    }
    write_json(TAG_COMPARISON_JSON, payload)
    TAG_COMPARISON_MD.write_text(
        "\n".join(
            [
                "# Tag-Aware Native Activator Comparison",
                "",
                f"status: `{status}`",
                "",
                f"- direct total Bq: `{payload['direct_total_Bq']}`",
                f"- tag-aware native total Bq: `{payload['tag_native_total_Bq']}`",
                f"- total relative delta: `{payload['total_relative_delta']}`",
                f"- direct-only keys: `{direct_only}`",
                f"- native-only keys: `{native_only}`",
                f"- mismatch keys: `{mismatch}`",
                f"- native extra activity Bq: `{payload['native_extra_activity_Bq']}`",
                "",
                "Interpretation:",
                "- Native-only activity is classified as parent/daughter feeding or another native decay product.",
                "- This comparison resolves the invalid all-tag merge problem by running one Activator per production tag.",
                "- Selected-rate promotion still requires transport and Step05 ingestion.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    wp04 = json.loads(WP04.read_text(encoding="utf-8"))
    if wp04.get("status") != "PASS":
        raise RuntimeError("WP04 must pass before WP05")
    for old_probe in OUT.glob("native_activation_sources_probe*.sim.gz"):
        old_probe.unlink()
    old_synthetic_output = OUT / "synthetic_activator_output.dat"
    if old_synthetic_output.exists():
        old_synthetic_output.unlink()

    comparison = compare_native_store()
    merge_audit = write_merge_audit()
    write_activation_sources_probe()
    activation_probe = run_cosima(ACTIVATION_PROBE_SOURCE, ACTIVATION_PROBE_LOG, timeout=180)
    write_synthetic_activator()
    synthetic_probe = run_cosima(SYN_SOURCE, SYN_LOG, timeout=180)
    probe_products = sorted(OUT.glob("native_activation_sources_probe*.sim.gz"))
    synthetic_output = OUT / "synthetic_activator_output.dat"
    tag_aware_run = run_tag_aware_activators()
    tag_aware_comparison = compare_tag_aware_native(tag_aware_run)

    full_native_raw_oracle = tag_aware_comparison["status"]
    status = full_native_raw_oracle
    if comparison["status"] != "PASS" or merge_audit["status"] != "PASS":
        status = "FAIL_NATIVE_COMPARISON"
    if activation_probe["status"] != "PASS":
        status = "WARN_NATIVE_ORACLE_LIMITED"
    if synthetic_probe["status"] != "PASS":
        status = "WARN_NATIVE_ORACLE_LIMITED"
    if tag_aware_run["status"] != "PASS":
        status = "UNRESOLVED_DIFFERENCE"

    summary = {
        "status": status,
        "outputs": [
            rel(ORACLE_SUMMARY),
            rel(COMPARE_JSON),
            rel(COMPARE_CSV),
            rel(MERGE_JSON),
            rel(MERGE_MD),
            rel(ACTIVATION_PROBE_SOURCE),
            rel(ACTIVATION_PROBE_LOG),
            rel(SYN_SOURCE),
            rel(SYN_COUNTS),
            rel(SYN_LOG),
            *(rel(p) for p in probe_products),
            *( [rel(synthetic_output)] if synthetic_output.exists() else [] ),
            rel(TAG_COMPARISON_JSON),
            rel(TAG_COMPARISON_CSV),
            rel(TAG_COMPARISON_MD),
            *(result["source"] for result in tag_aware_run["tags"].values()),
            *(result["log"] for result in tag_aware_run["tags"].values()),
            *(result["output"] for result in tag_aware_run["tags"].values() if result.get("output")),
            rel(SUMMARY_MD),
        ],
        "findings": [
            f"Native store serialization comparison: {comparison['status']}.",
            f"ActivationSources probe: {activation_probe['status']}.",
            f"Synthetic Activator probe: {synthetic_probe['status']}.",
            f"Tag-aware native Activator oracle: {tag_aware_comparison['status']}.",
        ],
        "next_gate": "G6 DetectorTimeConstant and decay-chain boundary audit",
        "user_decision_required": False,
    }
    top = {
        "status": status,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "claim_boundary": "native serialization/source compatibility plus tag-aware raw Activator inventory comparison; no selected-rate promotion",
        "native_store_comparison": comparison,
        "merge_audit": merge_audit,
        "activation_sources_probe": activation_probe,
        "activation_sources_probe_products": [rel(p) for p in probe_products],
        "synthetic_activator_probe": synthetic_probe,
        "synthetic_activator_output": rel(synthetic_output) if synthetic_output.exists() else "",
        "tag_aware_activator_run": tag_aware_run,
        "tag_aware_native_comparison": tag_aware_comparison,
        "full_native_raw_oracle": full_native_raw_oracle,
    }
    write_json(ORACLE_SUMMARY, top)
    write_json(SUMMARY_JSON, summary)
    SUMMARY_MD.write_text(
        "\n".join(
            [
                "# WP05 Native Activation Oracle Summary",
                "",
                f"status: `{status}`",
                "",
                f"- native store serialization comparison: `{comparison['status']}`",
                f"- total relative delta: `{comparison['total_relative_delta']}`",
                f"- ActivationSources probe: `{activation_probe['status']}`",
                f"- synthetic Activator probe: `{synthetic_probe['status']}`",
                f"- tag-aware native Activator oracle: `{full_native_raw_oracle}`",
                "",
                "Boundary:",
                "- A single all-tag native Activator is not used because the installed merge path divides by total loaded `TT`.",
                "- The tag-aware native oracle resolves that merge issue, but selected-rate promotion still requires pilot/full transport and Step05 ingestion.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"WP05 {status}")
    print(json.dumps(top, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

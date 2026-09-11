#!/usr/bin/env python3
"""Close the SE3 whole-instrument mass change against its exact whitelist ledger.

MEGAlib ``MDVolume::GetMasses`` is used for paired O8-before and SE3-after
native snapshots.  Those absolute snapshots are explicitly approximate where
ROOT/TGeo Boolean ``Capacity()`` sampling is involved.  The whitelist mass
change remains the analytic value in ``se3_mass_ledger.csv``; it is never
relabelled as a native-exact result.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import statistics
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
SE3_SETUP = PACKAGE / "geometry/DEMO2_DR_v3p5_SE3.geo.setup"
MASS_LEDGER = PACKAGE / "data/se3_mass_ledger.csv"
OUTPUT = PACKAGE / "audit/se3_mass_validation.json"
AUTHORITY_GEOMETRY = Path(
    "/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/"
    "geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry"
)
AUTHORITY_STEM = "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy"
AUTHORITY_SETUP = AUTHORITY_GEOMETRY / f"{AUTHORITY_STEM}.geo.setup"
DEFAULT_MEGALIB = Path("/home/ubuntu/MEGAlib_Install/megalib-main")

AUTHORITY_CORE_SHA256 = {
    f"{AUTHORITY_STEM}.geo.setup": "86a9e56e54dc86834dfe2a9b03a5f71373fb40f2ef24e3889fa66f216058fbec",
    f"{AUTHORITY_STEM}.geo": "ff4e8402df702501e0112fe377d837a74c39100317146b09e9569b7bd615c37c",
    f"{AUTHORITY_STEM}.det": "dd2c1d68cd474f8b0c7489f2cbbfc924eb69beb14d3ce360d9437c319a33d6cb",
    f"Intro_{AUTHORITY_STEM}.geo": "f4ea834bf385f68a85690e018fd52d692e94e19dd93959e35e6f91efd3dbfd52",
    "Materials_DEMO2_DR_v3p5.geo": "751cd83f08631085496ee86efa4418e4f001a639b15573554b93e73ff95678bf",
}

# Repeating paired measurements with the same seed makes unchanged Boolean
# shapes consume the same random stream and cancel in before/after differences.
NATIVE_SEEDS = (20260815, 20260816, 20260817)

# Predeclared, conservative relative-closure gate.  MEGAlib documents TGeo
# Boolean Capacity as a random-sampling estimate (>1% for a 10,000-point call)
# and averages subtraction/intersection capacity 16 times (~4x statistical
# improvement).  Pairing seeds cancels unchanged shapes, so the remaining gate
# is max(50 g, 2% of exact whitelist delta, 500 ppm of native before mass).
TOLERANCE_FLOOR_KG = 0.050
TOLERANCE_EXACT_DELTA_FRACTION = 0.020
TOLERANCE_NATIVE_BEFORE_PPM = 500.0


NATIVE_MACRO = r'''
R__LOAD_LIBRARY(libMEGAlib.so)

#include "TSystem.h"
#include "TRandom.h"
#include "MGlobal.h"
#include "MString.h"
#include "MDGeometryQuest.h"
#include "MDMaterial.h"
#include "MDVolume.h"

#include <cmath>
#include <fstream>
#include <iomanip>
#include <map>
#include <sstream>
#include <string>
#include <vector>

namespace {

struct Snapshot {
  unsigned int seed = 0;
  double world_shape_volume_cm3 = 0.0;
  double total_g = 0.0;
  double non_vacuum_total_g = 0.0;
  unsigned int negative_material_masses = 0;
  std::map<std::string, double> by_material_g;
};

std::string Escape(const std::string& value) {
  std::ostringstream out;
  for (unsigned char c : value) {
    if (c == '"') out << "\\\"";
    else if (c == '\\') out << "\\\\";
    else if (c == '\n') out << "\\n";
    else if (c == '\r') out << "\\r";
    else if (c == '\t') out << "\\t";
    else out << static_cast<char>(c);
  }
  return out.str();
}

bool Measure(const std::string& setup, const std::vector<unsigned int>& seeds,
             std::vector<Snapshot>& snapshots, std::string& error) {
  MDGeometryQuest geometry;
  if (!geometry.ScanSetupFile(MString(setup.c_str()), true, false, false)) {
    error = "MDGeometryQuest::ScanSetupFile failed for " + setup;
    return false;
  }
  if (geometry.GetWorldVolume() == nullptr) {
    error = "geometry has no world volume: " + setup;
    return false;
  }
  for (unsigned int seed : seeds) {
    gRandom->SetSeed(seed);
    std::map<MDMaterial*, double> native;
    Snapshot snapshot;
    snapshot.seed = seed;
    snapshot.world_shape_volume_cm3 = geometry.GetWorldVolume()->GetMasses(native);
    for (const auto& entry : native) {
      if (entry.first == nullptr || !std::isfinite(entry.second)) {
        error = "GetMasses returned null material or non-finite mass";
        return false;
      }
      const std::string name = entry.first->GetName().GetString();
      snapshot.by_material_g[name] += entry.second;
      snapshot.total_g += entry.second;
      if (name != "Vacuum") snapshot.non_vacuum_total_g += entry.second;
      if (entry.second < 0.0) ++snapshot.negative_material_masses;
    }
    if (!std::isfinite(snapshot.total_g) ||
        !std::isfinite(snapshot.non_vacuum_total_g)) {
      error = "GetMasses total is non-finite";
      return false;
    }
    snapshots.push_back(snapshot);
  }
  return true;
}

void WriteSnapshot(std::ostream& out, const Snapshot& snapshot) {
  out << "{\"seed\":" << snapshot.seed
      << ",\"world_shape_volume_cm3\":" << std::setprecision(17)
      << snapshot.world_shape_volume_cm3 << ",\"total_g\":" << snapshot.total_g
      << ",\"non_vacuum_total_g\":" << snapshot.non_vacuum_total_g
      << ",\"negative_material_masses\":" << snapshot.negative_material_masses
      << ",\"by_material_g\":{";
  bool first = true;
  for (const auto& entry : snapshot.by_material_g) {
    if (!first) out << ",";
    first = false;
    out << "\"" << Escape(entry.first) << "\":" << entry.second;
  }
  out << "}}";
}

bool WriteOutput(const std::string& path, bool initialized, bool before_loaded,
                 bool after_loaded, const std::string& error,
                 const std::vector<unsigned int>& seeds,
                 const std::vector<Snapshot>& before,
                 const std::vector<Snapshot>& after) {
  std::ofstream out(path, std::ios::out | std::ios::trunc);
  if (!out) return false;
  const bool passed = initialized && before_loaded && after_loaded && error.empty() &&
                      before.size() == seeds.size() && after.size() == seeds.size();
  out << "{\"status\":\"" << (passed ? "PASS" : "FAIL")
      << "\",\"mglobal_initialized\":" << (initialized ? "true" : "false")
      << ",\"before_loaded\":" << (before_loaded ? "true" : "false")
      << ",\"after_loaded\":" << (after_loaded ? "true" : "false")
      << ",\"create_nodes\":true,\"allow_cross_section_creation\":false"
      << ",\"paired_random_seeds\":[";
  for (std::size_t i = 0; i < seeds.size(); ++i) {
    if (i != 0) out << ",";
    out << seeds[i];
  }
  out << "],\"error\":\"" << Escape(error) << "\",\"before\":[";
  for (std::size_t i = 0; i < before.size(); ++i) {
    if (i != 0) out << ",";
    WriteSnapshot(out, before[i]);
  }
  out << "],\"after\":[";
  for (std::size_t i = 0; i < after.size(); ++i) {
    if (i != 0) out << ",";
    WriteSnapshot(out, after[i]);
  }
  out << "],\"transport_launched\":false}\n";
  out.flush();
  return static_cast<bool>(out);
}

int Run(const char* before_setup, const char* after_setup, const char* output_path) {
  const std::vector<unsigned int> seeds = {20260815, 20260816, 20260817};
  std::vector<Snapshot> before;
  std::vector<Snapshot> after;
  std::string error;
  const bool initialized = MGlobal::Initialize(
      "SE3MassValidation", "paired native whole-geometry mass snapshots");
  bool before_loaded = false;
  bool after_loaded = false;
  if (!initialized) {
    error = "MGlobal::Initialize returned false";
  } else {
    before_loaded = Measure(before_setup, seeds, before, error);
    if (before_loaded) after_loaded = Measure(after_setup, seeds, after, error);
  }
  if (!WriteOutput(output_path, initialized, before_loaded, after_loaded, error,
                   seeds, before, after)) return 2;
  return initialized && before_loaded && after_loaded && error.empty() ? 0 : 1;
}

}  // namespace

void se3_mass_snapshot(const char* before_setup, const char* after_setup,
                       const char* output_path) {
  gSystem->Exit(Run(before_setup, after_setup, output_path));
}
'''


class ValidationError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_file(path: Path, label: str) -> Path:
    try:
        resolved = path.expanduser().resolve(strict=True)
    except OSError as exc:
        raise ValidationError(f"{label} does not resolve: {path}: {exc}") from exc
    if not resolved.is_file():
        raise ValidationError(f"{label} is not a regular file: {resolved}")
    return resolved


def record(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "size_bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(payload, handle, indent=2, sort_keys=True, allow_nan=False)
            handle.write("\n")
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def validate_authority_core() -> dict[str, Any]:
    files: dict[str, Any] = {}
    for name, expected_hash in AUTHORITY_CORE_SHA256.items():
        path = require_file(AUTHORITY_GEOMETRY / name, f"O8 authority core {name}")
        item = record(path)
        item["expected_sha256"] = expected_hash
        item["hash_match"] = item["sha256"] == expected_hash
        if not item["hash_match"]:
            raise ValidationError(
                f"O8 authority core hash mismatch for {name}: {item['sha256']}"
            )
        files[name] = item
    return {
        "status": "PASS",
        "classification": "hash-pinned finished S3d-O8 authority",
        "files": files,
    }


def validate_se3_bundle(setup: Path) -> dict[str, Any]:
    geometry = setup.parent
    names = (
        "DEMO2_DR_v3p5_SE3.geo.setup",
        "DEMO2_DR_v3p5_SE3.geo",
        "DEMO2_DR_v3p5_SE3.det",
        f"Intro_{AUTHORITY_STEM}.geo",
        "Materials_DEMO2_DR_v3p5.geo",
    )
    files = {name: record(require_file(geometry / name, f"SE3 core {name}")) for name in names}
    text = setup.read_text(encoding="utf-8")
    for exact_line in (
        "Name DEMO2_DR_v3p5_SE3",
        "Include DEMO2_DR_v3p5_SE3.geo",
        "Include DEMO2_DR_v3p5_SE3.det",
    ):
        if exact_line not in text.splitlines():
            raise ValidationError(f"SE3 setup missing exact line: {exact_line}")
    return {"status": "PASS", "files": files}


def finite_float(row: dict[str, str], field: str, component: str) -> float:
    try:
        value = float(row[field])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValidationError(f"ledger {component}: invalid {field}") from exc
    if not math.isfinite(value):
        raise ValidationError(f"ledger {component}: non-finite {field}")
    return value


def read_exact_ledger(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValidationError("mass ledger is empty")
    total_rows = [
        row
        for row in rows
        if row.get("scope") == "touched_components_total"
        and row.get("component") == "SE3_WHITELIST_EXACT_DELTA"
    ]
    if len(total_rows) != 1:
        raise ValidationError(
            f"expected exactly one whitelist total row, found {len(total_rows)}"
        )
    components = [row for row in rows if row not in total_rows]
    if not components:
        raise ValidationError("mass ledger has no component rows")

    parsed_components: list[dict[str, Any]] = []
    summed_before = 0.0
    summed_after = 0.0
    summed_delta = 0.0
    for row in components:
        component = row.get("component", "<missing>")
        before = finite_float(row, "mass_before_kg", component)
        after = finite_float(row, "mass_after_kg", component)
        delta = finite_float(row, "delta_mass_kg", component)
        if not math.isclose(after - before, delta, rel_tol=0.0, abs_tol=1.0e-12):
            raise ValidationError(f"ledger {component}: after-before does not equal delta")
        method = row.get("method", "")
        if not method.startswith("exact "):
            raise ValidationError(f"ledger {component}: method is not labelled exact")
        summed_before += before
        summed_after += after
        summed_delta += delta
        parsed_components.append(
            {
                "scope": row.get("scope"),
                "component": component,
                "mass_before_kg": before,
                "mass_after_kg": after,
                "delta_mass_kg": delta,
                "method": method,
            }
        )

    total = total_rows[0]
    exact_before = finite_float(total, "mass_before_kg", total["component"])
    exact_after = finite_float(total, "mass_after_kg", total["component"])
    exact_delta = finite_float(total, "delta_mass_kg", total["component"])
    for name, summed, stated in (
        ("before", summed_before, exact_before),
        ("after", summed_after, exact_after),
        ("delta", summed_delta, exact_delta),
    ):
        if not math.isclose(summed, stated, rel_tol=0.0, abs_tol=1.0e-11):
            raise ValidationError(
                f"ledger component sum {name}={summed} != total row {stated}"
            )
    if not math.isclose(exact_after - exact_before, exact_delta, rel_tol=0.0, abs_tol=1.0e-12):
        raise ValidationError("ledger total after-before does not equal delta")
    return {
        "classification": "exact analytic whitelist delta",
        "path": str(path),
        "sha256": sha256(path),
        "component_count": len(parsed_components),
        "components": parsed_components,
        "touched_mass_before_kg": exact_before,
        "touched_mass_after_kg": exact_after,
        "exact_whitelist_delta_kg": exact_delta,
        "component_sum_closure_kg": {
            "before_residual": summed_before - exact_before,
            "after_residual": summed_after - exact_after,
            "delta_residual": summed_delta - exact_delta,
        },
        "method": total.get("method"),
    }


def cpp_string(value: str) -> str:
    if any(character in value for character in ("\x00", "\n", "\r")):
        raise ValidationError("native macro path contains a control character")
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def prepend_env(env: dict[str, str], name: str, paths: list[Path]) -> None:
    values = [str(path) for path in paths]
    if env.get(name):
        values.append(env[name])
    env[name] = os.pathsep.join(values)


def tail(value: str | None, limit: int = 12000) -> str:
    return (value or "")[-limit:]


def mean(values: list[float]) -> float:
    if not values:
        raise ValidationError("cannot summarize an empty native sample set")
    return statistics.fmean(values)


def summary(values: list[float]) -> dict[str, Any]:
    return {
        "count": len(values),
        "min": min(values),
        "mean": mean(values),
        "max": max(values),
        "population_stdev": statistics.pstdev(values),
    }


def paired_closure(native: dict[str, Any], ledger: dict[str, Any]) -> dict[str, Any]:
    if native.get("status") != "PASS":
        raise ValidationError(f"native mass macro failed: {native.get('error')}")
    before = native.get("before")
    after = native.get("after")
    if not isinstance(before, list) or not isinstance(after, list):
        raise ValidationError("native mass JSON lacks before/after sample lists")
    if len(before) != len(NATIVE_SEEDS) or len(after) != len(NATIVE_SEEDS):
        raise ValidationError("native mass sample count does not match paired seed contract")

    before_by_seed = {int(item["seed"]): item for item in before}
    after_by_seed = {int(item["seed"]): item for item in after}
    if set(before_by_seed) != set(NATIVE_SEEDS) or set(after_by_seed) != set(NATIVE_SEEDS):
        raise ValidationError("native mass seeds do not match the locked paired seeds")
    exact_delta = float(ledger["exact_whitelist_delta_kg"])
    samples: list[dict[str, Any]] = []
    before_values: list[float] = []
    after_values: list[float] = []
    delta_values: list[float] = []
    residual_values: list[float] = []
    for seed in NATIVE_SEEDS:
        before_sample = before_by_seed[seed]
        after_sample = after_by_seed[seed]
        if before_sample.get("negative_material_masses") != 0 or after_sample.get(
            "negative_material_masses"
        ) != 0:
            raise ValidationError(f"native GetMasses has negative material mass at seed {seed}")
        before_kg = float(before_sample["non_vacuum_total_g"]) / 1000.0
        after_kg = float(after_sample["non_vacuum_total_g"]) / 1000.0
        if not math.isfinite(before_kg) or not math.isfinite(after_kg):
            raise ValidationError(f"non-finite native mass at seed {seed}")
        native_delta = after_kg - before_kg
        expected_after = before_kg + exact_delta
        residual = after_kg - expected_after
        samples.append(
            {
                "seed": seed,
                "native_before_kg": before_kg,
                "native_after_kg": after_kg,
                "native_delta_kg": native_delta,
                "expected_after_from_before_plus_exact_delta_kg": expected_after,
                "residual_native_minus_relative_expectation_kg": residual,
                "residual_ppm_of_native_before": residual / before_kg * 1.0e6,
            }
        )
        before_values.append(before_kg)
        after_values.append(after_kg)
        delta_values.append(native_delta)
        residual_values.append(residual)

    before_mean = mean(before_values)
    after_mean = mean(after_values)
    delta_mean = mean(delta_values)
    residual_mean = mean(residual_values)
    tolerance = max(
        TOLERANCE_FLOOR_KG,
        TOLERANCE_EXACT_DELTA_FRACTION * abs(exact_delta),
        TOLERANCE_NATIVE_BEFORE_PPM * 1.0e-6 * abs(before_mean),
    )
    maximum_absolute_residual = max(abs(value) for value in residual_values)
    passed = maximum_absolute_residual <= tolerance

    all_materials = sorted(
        set().union(
            *(set(item["by_material_g"]) for item in before),
            *(set(item["by_material_g"]) for item in after),
        )
    )
    material_deltas: dict[str, Any] = {}
    for material in all_materials:
        values = [
            (
                float(after_by_seed[seed]["by_material_g"].get(material, 0.0))
                - float(before_by_seed[seed]["by_material_g"].get(material, 0.0))
            )
            / 1000.0
            for seed in NATIVE_SEEDS
        ]
        material_deltas[material] = summary(values)

    return {
        "status": "PASS" if passed else "FAIL",
        "classification": "paired native relative closure against exact analytic delta",
        "samples": samples,
        "native_absolute_before_kg": summary(before_values),
        "native_absolute_after_kg": summary(after_values),
        "native_delta_kg": summary(delta_values),
        "exact_whitelist_delta_kg": exact_delta,
        "expected_after_mean_from_before_plus_exact_delta_kg": before_mean
        + exact_delta,
        "observed_native_after_mean_kg": after_mean,
        "mean_residual_kg": residual_mean,
        "mean_residual_ppm_of_native_before": residual_mean / before_mean * 1.0e6,
        "mean_residual_ppm_of_exact_delta_magnitude": residual_mean
        / abs(exact_delta)
        * 1.0e6,
        "maximum_absolute_seed_residual_kg": maximum_absolute_residual,
        "native_material_delta_kg": material_deltas,
        "gate": {
            "status": "PASS" if passed else "FAIL",
            "criterion": "maximum absolute paired-seed residual <= capacity-estimate tolerance",
            "capacity_estimate_tolerance_kg": tolerance,
            "tolerance_policy": {
                "floor_kg": TOLERANCE_FLOOR_KG,
                "fraction_of_exact_delta": TOLERANCE_EXACT_DELTA_FRACTION,
                "ppm_of_native_before": TOLERANCE_NATIVE_BEFORE_PPM,
                "combination": "maximum of the three predeclared terms",
            },
        },
        "cancellation_method": (
            "For each seed, reset ROOT gRandom immediately before GetMasses for O8 "
            "and SE3. The whitelist leaves other volume definitions unchanged, so "
            "their native capacity estimates share the random stream and cancel in "
            "the paired difference; the ledger supplies the exact changed-component delta."
        ),
    }


def failure_payload(
    message: str, output: Path, started: str, start_time: float,
    inputs: dict[str, Any] | None = None, invocation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": "FAIL",
        "generated_utc": utc_now(),
        "started_utc": started,
        "elapsed_seconds": time.monotonic() - start_time,
        "transport_launched": False,
        "output": str(output),
        "input_integrity": inputs or {},
        "native_invocation": invocation or {},
        "errors": [message],
    }


def run(args: argparse.Namespace) -> int:
    started = utc_now()
    start_time = time.monotonic()
    output = args.output.expanduser().resolve()
    inputs: dict[str, Any] = {}
    invocation: dict[str, Any] = {}
    try:
        authority_setup = require_file(args.authority_setup, "O8 authority setup")
        se3_setup = require_file(args.se3_setup, "SE3 setup")
        ledger_path = require_file(args.ledger, "SE3 mass ledger")
        megalib = args.megalib.expanduser().resolve(strict=True)
        root_binary = (
            require_file(args.root_binary, "ROOT binary")
            if args.root_binary is not None
            else require_file(
                megalib / "external/root_v6.36.6/bin/root", "ROOT binary"
            )
        )
        if not os.access(root_binary, os.X_OK):
            raise ValidationError(f"ROOT binary is not executable: {root_binary}")
        if authority_setup != AUTHORITY_SETUP.resolve():
            raise ValidationError(
                f"before setup must be the pinned O8 authority: {AUTHORITY_SETUP}"
            )

        authority_record = validate_authority_core()
        se3_record = validate_se3_bundle(se3_setup)
        ledger = read_exact_ledger(ledger_path)
        inputs = {
            "authority_o8": authority_record,
            "se3": se3_record,
            "mass_ledger": {
                "path": str(ledger_path),
                "size_bytes": ledger_path.stat().st_size,
                "sha256": ledger["sha256"],
            },
            "embedded_native_macro_sha256": hashlib.sha256(
                NATIVE_MACRO.encode("utf-8")
            ).hexdigest(),
        }

        env = os.environ.copy()
        rootsys = root_binary.parents[1]
        env["MEGALIB"] = str(megalib)
        env["ROOTSYS"] = str(rootsys)
        prepend_env(env, "PATH", [megalib / "bin", rootsys / "bin"])
        prepend_env(env, "LD_LIBRARY_PATH", [megalib / "lib", rootsys / "lib"])
        prepend_env(env, "ROOT_INCLUDE_PATH", [megalib / "include"])

        with tempfile.TemporaryDirectory(prefix="se3_mass_validation_") as temp:
            temporary = Path(temp)
            macro = temporary / "se3_mass_snapshot.C"
            raw_output = temporary / "native_mass.json"
            build_dir = temporary / "aclic"
            build_dir.mkdir()
            macro.write_text(NATIVE_MACRO, encoding="utf-8")
            macro_call = (
                f"{macro}+({cpp_string(str(authority_setup))},"
                f"{cpp_string(str(se3_setup))},{cpp_string(str(raw_output))})"
            )
            build_expression = (
                f"gSystem->SetBuildDir({cpp_string(str(build_dir))}, kTRUE);"
            )
            command = [
                str(root_binary), "-l", "-b", "-n", "-q", "-e",
                build_expression, macro_call,
            ]
            invocation = {
                "engine": "ROOT ACLiC + MEGAlib MDGeometryQuest/MDVolume::GetMasses",
                "command": command,
                "paired_random_seeds": list(NATIVE_SEEDS),
                "timeout_seconds": args.timeout,
                "temporary_macro_and_build_directory": True,
                "transport_launched": False,
            }
            try:
                process = subprocess.run(
                    command,
                    cwd=PACKAGE / "code",
                    env=env,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=args.timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                invocation.update(
                    {
                        "timed_out": True,
                        "stdout_tail": tail(exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else exc.stdout),
                        "stderr_tail": tail(exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr),
                    }
                )
                raise ValidationError(
                    f"native GetMasses audit exceeded {args.timeout} seconds"
                ) from exc
            invocation.update(
                {
                    "returncode": process.returncode,
                    "timed_out": False,
                    "stdout_sha256": hashlib.sha256(
                        process.stdout.encode("utf-8", errors="replace")
                    ).hexdigest(),
                    "stderr_sha256": hashlib.sha256(
                        process.stderr.encode("utf-8", errors="replace")
                    ).hexdigest(),
                    "stdout_tail": tail(process.stdout),
                    "stderr_tail": tail(process.stderr),
                }
            )
            if not raw_output.is_file():
                raise ValidationError(
                    f"native GetMasses macro produced no JSON (rc={process.returncode})"
                )
            try:
                native = json.loads(raw_output.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise ValidationError(f"native GetMasses JSON is invalid: {exc}") from exc
            if process.returncode != 0:
                raise ValidationError(
                    f"native GetMasses macro failed with return code {process.returncode}: "
                    f"{native.get('error')}"
                )

        closure = paired_closure(native, ledger)
        status = "PASS" if closure["status"] == "PASS" else "FAIL"
        result = {
            "schema_version": 1,
            "status": status,
            "generated_utc": utc_now(),
            "started_utc": started,
            "elapsed_seconds": time.monotonic() - start_time,
            "transport_launched": False,
            "output": str(output),
            "input_integrity": inputs,
            "native_absolute_snapshot": {
                "classification": "approximate native MDVolume::GetMasses snapshot",
                "before_geometry": str(authority_setup),
                "after_geometry": str(se3_setup),
                "samples": native,
                "limitations": [
                    "MDVolume::GetMasses recursively uses shape GetVolume and subtracts daughter volumes.",
                    "ROOT/TGeo Boolean Capacity is random-sampling based; MEGAlib states >1% accuracy for a 10,000-sample call.",
                    "MEGAlib averages subtraction/intersection Capacity 16 times for roughly fourfold better statistical precision.",
                    "Therefore absolute native masses are validation snapshots, not mathematical exact masses.",
                ],
            },
            "exact_analytic_whitelist": ledger,
            "whole_instrument_relative_closure": closure,
            "native_invocation": invocation,
            "interpretation": (
                "The whole-instrument after expectation is each approximate native O8 "
                "before snapshot plus the exact analytic whitelist delta. Only the "
                "paired residual is gated; native absolute snapshots are not called exact."
            ),
        }
        atomic_json(output, result)
        print(json.dumps({"status": status, "output": str(output)}, indent=2))
        return 0 if status == "PASS" else 1
    except (ValidationError, OSError, ValueError, KeyError, TypeError) as exc:
        result = failure_payload(
            str(exc), output, started, start_time, inputs, invocation
        )
        atomic_json(output, result)
        print(
            json.dumps(
                {"status": "FAIL", "output": str(output), "error": str(exc)},
                indent=2,
            )
        )
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--authority-setup", type=Path, default=AUTHORITY_SETUP)
    parser.add_argument("--se3-setup", type=Path, default=SE3_SETUP)
    parser.add_argument("--ledger", type=Path, default=MASS_LEDGER)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--megalib", type=Path, default=DEFAULT_MEGALIB)
    parser.add_argument("--root-binary", type=Path)
    parser.add_argument("--timeout", type=float, default=3600.0)
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be a finite positive number")
    return run(args)


if __name__ == "__main__":
    raise SystemExit(main())

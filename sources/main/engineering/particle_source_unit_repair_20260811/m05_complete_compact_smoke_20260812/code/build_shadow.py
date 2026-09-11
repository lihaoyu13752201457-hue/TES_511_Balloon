#!/usr/bin/env python3
"""Create and compile a fully isolated Cosima shadow tree; never executes it."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from preflight_common import PACKAGE, canonical_json_bytes, rel, sha256, sha256_bytes, write_once


UPSTREAM = Path("/home/ubuntu/MEGAlib_Install/megalib-main/src/cosima")
EXTENSIONS = PACKAGE / "code/shadow_extensions"
PATCH = PACKAGE / "patches/m05_shadow_hooks.patch"
EXPECTED_UPSTREAM = {
    "inc/MCSource.hh": "d8bf38ca3b2134480f05dd78e93a622833b870eea5c4fb67d3c4a09939de7071",
    "inc/MCRun.hh": "d249d2da6a0c0dc82ff0954274fdb248bf1d3c66b06e0fc353f95384cc74e7c8",
    "inc/MCMain.hh": "544c8e74d40da92e6a0f3a533228d90960807100f1009cbaa94174adcbdc4824",
    "src/MCRun.cc": "2b5ced2724ef901889b1a9a0b52e9b639ad2adb20d5fd1b625bf9f1911adf354",
    "src/MCEventAction.cc": "bb31dbb73c3f04c297f5c9f07cd500171b41e2d71660097932639133bab2e6db",
    "src/MCSteppingAction.cc": "eb1cd57239b9412bf84c6c469a8587fa835d9ec29076802913aad3d7e52d8f44",
    "src/MCRunManager.cc": "8b0ac32a46441f8f597f39e54d46e19b802f5d75dc3fa1e076720cdcc7fbb191",
}
PATCHED_PATHS = {
    "inc/MCSource.hh", "inc/MCRun.hh", "inc/MCMain.hh", "src/MCRun.cc", "src/MCEventAction.cc",
    "src/MCSteppingAction.cc", "src/MCRunManager.cc",
}
FORBIDDEN_RNG_TOKENS = (
    "gRandom", "G4UniformRand", "CLHEP::", "RandFlat", "RandGauss", "::shoot(", "drand48(", "random("
)


def run(command: list[str], *, cwd: Path, capture: bool = True) -> str:
    completed = subprocess.run(
        command,
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.STDOUT if capture else None,
        env=os.environ.copy(),
    )
    return completed.stdout or ""


def file_manifest(root: Path, patterns: tuple[str, ...]) -> list[dict[str, Any]]:
    files: list[Path] = []
    for pattern in patterns:
        files.extend(root.glob(pattern))
    records = []
    for path in sorted(set(files)):
        if path.is_file():
            records.append({"path": str(path.relative_to(root)), "sha256": sha256(path), "size_bytes": path.stat().st_size})
    return records


def executable_identity(name_or_path: str, *, cwd: Path) -> dict[str, Any]:
    candidate = shutil.which(name_or_path) if "/" not in name_or_path else name_or_path
    if not candidate:
        raise FileNotFoundError(f"missing build tool {name_or_path}")
    path = Path(candidate).resolve()
    if not path.is_file():
        raise FileNotFoundError(path)
    version_option = "--version"
    version = run([str(path), version_option], cwd=cwd).splitlines()[0]
    return {"path": str(path), "sha256": sha256(path), "size_bytes": path.stat().st_size, "version": version}


def linked_library_manifest(ldd: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in ldd.splitlines():
        match = re.search(r"=>\s+(/\S+)\s+\(", line)
        if match is None:
            match = re.match(r"\s*(/\S+)\s+\(", line)
        if match is None:
            continue
        lexical = Path(match.group(1))
        path = lexical.resolve()
        if not path.is_file():
            raise FileNotFoundError(f"linked library vanished: {lexical}")
        records.append(
            {
                "loader_path": str(lexical),
                "resolved_path": str(path),
                "sha256": sha256(path),
                "size_bytes": path.stat().st_size,
            }
        )
    records.sort(key=lambda row: row["loader_path"])
    if not records:
        raise ValueError("ldd yielded no hashable linked libraries")
    return records


def build(output: Path, jobs: int) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"write-once shadow build already exists: {output}")
    for relative, expected in EXPECTED_UPSTREAM.items():
        actual = sha256(UPSTREAM / relative)
        if actual != expected:
            raise ValueError(f"upstream drift {relative}: {actual} != {expected}")
    scorer_text = (EXTENSIONS / "M05CompactScorer.cc").read_text(encoding="utf-8")
    found_rng = [token for token in FORBIDDEN_RNG_TOKENS if token in scorer_text]
    if found_rng:
        raise ValueError(f"compact scorer contains forbidden RNG token(s): {found_rng}")
    extension_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in sorted(EXTENSIONS.glob("*")) if path.is_file()
    )
    if "G4MTRunManager" in extension_text:
        raise ValueError("shadow extensions reference forbidden G4MTRunManager")
    run_manager_header = (UPSTREAM / "inc/MCRunManager.hh").read_text(encoding="utf-8")
    if "class MCRunManager : public G4RunManager" not in run_manager_header:
        raise ValueError("installed run manager is not the pinned sequential G4RunManager implementation")
    patch_targets = set(re.findall(r"^--- a/(\S+)$", PATCH.read_text(encoding="utf-8"), flags=re.MULTILINE))
    if patch_targets != PATCHED_PATHS:
        raise ValueError(f"patch target set drift: {sorted(patch_targets)} != {sorted(PATCHED_PATHS)}")

    output.mkdir(parents=True, exist_ok=False)
    shutil.copytree(UPSTREAM / "inc", output / "inc", symlinks=False)
    shutil.copytree(UPSTREAM / "src", output / "src", symlinks=False)
    upstream_source_manifest = file_manifest(output, ("inc/*.hh", "src/*.cc"))
    dry_run_log = run(
        ["patch", "--dry-run", "--batch", "--forward", "--fuzz=0", "-p1", "-i", str(PATCH)], cwd=output
    )
    forbidden_patch_report = re.compile(r"offset|fuzz|failed|malformed|reversed|previously applied", re.IGNORECASE)
    if forbidden_patch_report.search(dry_run_log):
        raise ValueError(f"zero-fuzz patch dry-run reported a non-exact hunk:\n{dry_run_log}")
    patch_log = run(
        ["patch", "--batch", "--forward", "--fuzz=0", "-p1", "-i", str(PATCH)], cwd=output
    )
    if forbidden_patch_report.search(patch_log):
        raise ValueError(f"zero-fuzz patch application reported a non-exact hunk:\n{patch_log}")
    dry_run_log_path = output / "patch_dry_run.log"
    patch_log_path = output / "patch_apply.log"
    write_once(dry_run_log_path, dry_run_log.encode("utf-8"))
    write_once(patch_log_path, patch_log.encode("utf-8"))
    rejects = sorted(
        str(path.relative_to(output))
        for path in output.rglob("*")
        if path.is_file() and path.suffix in {".orig", ".rej"}
    )
    if rejects:
        raise ValueError(f"patch left reject/original artifacts: {rejects}")
    post_patch_source_manifest = file_manifest(output, ("inc/*.hh", "src/*.cc"))
    for source in sorted(EXTENSIONS.glob("*.hh")):
        shutil.copy2(source, output / "inc" / source.name)
    for source in sorted(EXTENSIONS.glob("*.cc")):
        shutil.copy2(source, output / "src" / source.name)
    shutil.copy2(EXTENSIONS / "Makefile.shadow", output / "Makefile")
    complete_build_input_manifest = file_manifest(output, ("inc/*.hh", "src/*.cc", "Makefile"))
    frozen_extensions = file_manifest(EXTENSIONS, ("*.hh", "*.cc", "Makefile.shadow"))
    copied_by_path = {row["path"]: row for row in complete_build_input_manifest}
    for row in frozen_extensions:
        destination = "Makefile" if row["path"] == "Makefile.shadow" else (
            "inc/" + row["path"] if row["path"].endswith(".hh") else "src/" + row["path"]
        )
        copied = copied_by_path.get(destination)
        if copied is None or copied["sha256"] != row["sha256"] or copied["size_bytes"] != row["size_bytes"]:
            raise ValueError(f"copied shadow extension differs from frozen source: {row['path']}")
    compile_commands = run(["make", "-n", f"-j{jobs}"], cwd=output)
    if "G4MULTITHREADED" in compile_commands or "G4MTRunManager" in compile_commands:
        raise ValueError("shadow compile flags violate the pinned single-thread build contract")
    build_log_path = output / "build.log"
    try:
        build_log = run(["make", f"-j{jobs}"], cwd=output)
        write_once(build_log_path, build_log.encode("utf-8"))
    except subprocess.CalledProcessError as error:
        write_once(build_log_path, (error.stdout or "").encode("utf-8"))
        raise
    binary = output / "bin/m05cosima"
    if not binary.is_file():
        raise ValueError("shadow link produced no executable")
    readelf = run(["readelf", "-d", str(binary)], cwd=output)
    if "libCosima" in readelf:
        raise ValueError("shadow executable illegally links installed libCosima")
    scorer_object = output / "build/M05CompactScorer.o"
    nm_undefined = run(["nm", "-uC", str(scorer_object)], cwd=output)
    scorer_disassembly = run(["objdump", "-drC", str(scorer_object)], cwd=output)
    # Including Geant4 headers emits a static CLHEP::HepRandom::createInstance
    # reference even when this translation unit makes no draw. Reject callable
    # draw APIs, not that unavoidable factory initializer.
    random_symbol_lines = [
        line.strip() for line in nm_undefined.splitlines()
        if re.search(r"Random|Rand(?:Flat|Gauss)|G4UniformRand|drand48|\brandom\b", line)
    ]
    allowed_header_initializer = "U CLHEP::HepRandom::createInstance()"
    if random_symbol_lines != [allowed_header_initializer]:
        raise ValueError(f"scorer object imports non-allowlisted RNG symbols: {random_symbol_lines}")
    if scorer_disassembly.count("CLHEP::HepRandom::createInstance()") != 1:
        raise ValueError("unexpected CLHEP header initializer relocation count")
    initializer_at = scorer_disassembly.find("<_GLOBAL__sub_I_M05CompactScorer.cc")
    relocation_at = scorer_disassembly.find("CLHEP::HepRandom::createInstance()")
    if initializer_at < 0 or relocation_at < initializer_at:
        raise ValueError("CLHEP factory relocation is not confined to the translation-unit header initializer")
    ldd = run(["ldd", str(binary)], cwd=output)
    if "not found" in ldd:
        raise ValueError("shadow executable has unresolved dynamic libraries")
    toolchain = {
        "compiler": executable_identity("g++", cwd=output),
        "make": executable_identity("make", cwd=output),
        "patch": executable_identity("patch", cwd=output),
        "root_config": executable_identity(
            "/home/ubuntu/MEGAlib_Install/megalib-main/external/root_v6.36.6/bin/root-config", cwd=output
        ),
        "geant4_config": executable_identity(
            "/home/ubuntu/MEGAlib_Install/megalib-main/external/geant4_v10.02.p03/bin/geant4-config", cwd=output
        ),
    }
    configuration = {
        "root_cflags": run([toolchain["root_config"]["path"], "--cflags"], cwd=output).strip(),
        "root_libs": run([toolchain["root_config"]["path"], "--glibs", "--libs"], cwd=output).strip(),
        "geant4_cflags": run([toolchain["geant4_config"]["path"], "--cflags"], cwd=output).strip(),
        "geant4_libs": run([toolchain["geant4_config"]["path"], "--libs"], cwd=output).strip(),
        "makefile_sha256": sha256(output / "Makefile"),
    }
    manifest = {
        "schema_version": 1,
        "status": "PASS__SHADOW_BUILD_ONLY__EXECUTABLE_NOT_RUN",
        "transport_events_launched": 0,
        "builder_path": rel(Path(__file__).resolve()),
        "builder_sha256": sha256(Path(__file__).resolve()),
        "upstream_root": str(UPSTREAM),
        "upstream_required_hashes": EXPECTED_UPSTREAM,
        "upstream_source_manifest_before_patch": upstream_source_manifest,
        "post_patch_source_manifest": post_patch_source_manifest,
        "complete_build_input_manifest": complete_build_input_manifest,
        "patched_path_set": sorted(PATCHED_PATHS),
        "patch_path": rel(PATCH),
        "patch_sha256": sha256(PATCH),
        "patch_command_dry_run": ["patch", "--dry-run", "--batch", "--forward", "--fuzz=0", "-p1"],
        "patch_command_apply": ["patch", "--batch", "--forward", "--fuzz=0", "-p1"],
        "patch_dry_run_log": dry_run_log,
        "patch_dry_run_log_path": str(dry_run_log_path),
        "patch_dry_run_log_sha256": sha256(dry_run_log_path),
        "extension_source_manifest": frozen_extensions,
        "binary_path": str(binary),
        "binary_sha256": sha256(binary),
        "binary_size_bytes": binary.stat().st_size,
        "build_log_path": str(build_log_path),
        "build_log_sha256": sha256(build_log_path),
        "patch_log": patch_log,
        "patch_apply_log_path": str(patch_log_path),
        "patch_apply_log_sha256": sha256(patch_log_path),
        "zero_fuzz_zero_offset_gate": "PASS",
        "readelf_dynamic": readelf,
        "ldd": ldd,
        "linked_library_manifest": linked_library_manifest(ldd),
        "toolchain": toolchain,
        "configuration": configuration,
        "build_command": ["make", f"-j{jobs}"],
        "compile_commands_dry_run": compile_commands,
        "scorer_undefined_symbols": nm_undefined,
        "scorer_object_disassembly_sha256": sha256_bytes(scorer_disassembly.encode("utf-8")),
        "no_needed_libCosima": True,
        "scorer_rng_source_scan": {"status": "PASS", "forbidden_tokens": list(FORBIDDEN_RNG_TOKENS)},
        "scorer_rng_undefined_symbol_scan": "PASS__ONLY_ALLOWLISTED_HEADER_INITIALIZER",
        "scorer_rng_header_initializer_allowlist": [allowed_header_initializer],
        "single_thread_source_gate": {
            "status": "PASS",
            "run_manager_base": "G4RunManager",
            "g4_mt_run_manager_references": 0,
            "process_parallelism_only": True,
        },
        "execution_authority_note": (
            "This observer build is isolated and unexecuted. F/U remain bound to the installed production cosima; "
            "C/N1 may run only after independent preflight re-review."
        ),
    }
    manifest_path = output / "build_manifest.json"
    write_once(manifest_path, canonical_json_bytes(manifest))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--jobs", type=int, default=2)
    args = parser.parse_args()
    if args.jobs < 1 or args.jobs > 2:
        raise ValueError("build parallelism must be 1 or 2 on this host")
    build(args.output.resolve(), args.jobs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

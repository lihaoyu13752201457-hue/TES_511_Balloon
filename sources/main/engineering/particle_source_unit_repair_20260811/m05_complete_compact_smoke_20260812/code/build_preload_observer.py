#!/usr/bin/env python3
"""Compile and attest the dormant installed-Cosima MCRun preload observer.

This builder never executes Cosima, EventList, or any Geant4 transport.  It
only compiles a shared object and proves that the pinned installed call site is
ELF-interposable.  The output is write-once and explicitly not transport
authority.
"""

from __future__ import annotations

import argparse
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

from preflight_common import PACKAGE, canonical_json_bytes, fsync_directory, rel, sha256, sha256_bytes, write_once


SOURCE = PACKAGE / "code/preload_observer/M05GPSPreloadObserver.cc"
TRANSACTION_HEADER = PACKAGE / "code/preload_observer/M05ObserverTransaction.hh"
MEGALIB = Path("/home/ubuntu/MEGAlib_Install/megalib-main")
LIB_COSIMA = MEGALIB / "lib/libCosima.so"
COSIMA = MEGALIB / "bin/cosima"
G4_ROOT = MEGALIB / "external/geant4_v10.02.p03"
LIB_G4EVENT = G4_ROOT / "lib/libG4event.so"
G4_CONFIG = G4_ROOT / "bin/geant4-config"
ROOT_CONFIG = MEGALIB / "external/root_v6.36.6/bin/root-config"
TARGET_SYMBOL = "_ZN5MCRun17GeneratePrimariesEP7G4EventP23G4GeneralParticleSource"
COMPILE_MCRUN_HEADER = MEGALIB / "include/MCRun.hh"
SOURCE_MCRUN_HEADER = MEGALIB / "src/cosima/inc/MCRun.hh"

PINNED: dict[Path, str] = {
    LIB_COSIMA: "0656a54e0351a72347ad70437a96097b4d37688d10ac9059038e0b697ce6a495",
    COSIMA: "3fb7613de58ebb365f2a55c3336e54d2aabea2a4ddb282003a5d25eac6f1c74a",
    LIB_G4EVENT: "0ccca33e0fc42c704aa0d37e4d713ada83d269842b5e91658e52d5d472251ffe",
    G4_CONFIG: "c7fde124bebda55c976c7c66bafbf831f5b53b05de21aad581f017633b848788",
    ROOT_CONFIG: "1ef3a947335465571885d3d750fbcad7dcd28dc1a0270d6d64f8d81811ebe2ae",
    SOURCE_MCRUN_HEADER: "d249d2da6a0c0dc82ff0954274fdb248bf1d3c66b06e0fc353f95384cc74e7c8",
    MEGALIB / "src/cosima/src/MCRun.cc": "2b5ced2724ef901889b1a9a0b52e9b639ad2adb20d5fd1b625bf9f1911adf354",
    MEGALIB / "src/cosima/src/MCSource.cc": "1322cb460bd0e8cd2c788e5507ec3be5de06d97d65af98f013055480d5d94b1d",
    G4_ROOT / "include/Geant4/G4GeneralParticleSource.hh": "1e3e84bf4a5765c95b0475e726e002fcbada8844f31f639e0ade7cd1e9e76505",
    G4_ROOT / "include/Geant4/G4SingleParticleSource.hh": "a4c20002a5aff5e1404670d2f93d724ea56c9ebcb4f2386cc46cfc0a6fc56464",
    G4_ROOT / "include/Geant4/G4SystemOfUnits.hh": "06a8112bb07670cc3c49ce8ae3746330398d07d48b6b01f99f5c8b787cedc05c",
    G4_ROOT / "include/Geant4/CLHEP/Units/SystemOfUnits.h": (
        "7dd1f113e100f31a527953531bb768bb7d87ad1bf2bfbcdec7d463e88450a7ac"
    ),
    G4_ROOT / "include/Geant4/CLHEP/Units/PhysicalConstants.h": (
        "2d2a01da1cb16d048b9ba721c03218a3e00dec5a9bfd910f53c5e051471819e5"
    ),
    G4_ROOT / "geant4_v10.02.p03-source/source/event/src/G4GeneralParticleSource.cc": (
        "f5732425916a2e1690feff4d9e8d1a8da42ce4270ee63a1fc35c3f50bf2c03c3"
    ),
    G4_ROOT / "geant4_v10.02.p03-source/source/event/src/G4SingleParticleSource.cc": (
        "0fe1c0418077375c6b77028101da18733609be48c4b0fd3f241aff8f8af745f1"
    ),
    G4_ROOT / "geant4_v10.02.p03-source/source/event/src/G4SPSAngDistribution.cc": (
        "975e0c3717035151b70cb3b89a06d1f36473dd55c8b2ed2322a1a22803746ffd"
    ),
    G4_ROOT / "geant4_v10.02.p03-source/source/event/src/G4SPSPosDistribution.cc": (
        "b38410baeea9a3ab4a1d2a80f3c4cf2d206a04b5a45076bde641a3e2d033090b"
    ),
    G4_ROOT / "geant4_v10.02.p03-source/source/event/src/G4SPSEneDistribution.cc": (
        "a8b7c24f7314d2159d386b9f6aa5ef154cbd46801d006811f00e18d023cc9cba"
    ),
    G4_ROOT / "include/Geant4/CLHEP/Vector/ThreeVector.icc": (
        "f6335d6a8692e7120704ec51c59b5d354eb71563178cef88494164d6bbdb01f1"
    ),
}

FORBIDDEN_RNG = (
    "gRandom", "TRandom", "G4UniformRand", "CLHEP::Rand", "CLHEP::HepRandom",
    "RandFlat", "RandGauss", "::shoot(", "drand48(", "random(", "rand(", "srand(",
    "getrandom", "getentropy", "arc4random", "std::random_device", "random_device",
    "/dev/random", "/dev/urandom",
)
FORBIDDEN_RNG_SYMBOL_PATTERN = re.compile(
    r"gRandom|TRandom|G4UniformRand|CLHEP::(?:Rand|HepRandom)|RandFlat|RandGauss|"
    r"\b(?:getrandom|getentropy|arc4random|drand48|random|rand|srand)\b|random_device"
)


def run(command: list[str], *, cwd: Path) -> str:
    return subprocess.run(
        command, cwd=cwd, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    ).stdout


def identity(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"missing/non-regular pinned authority: {path}")
    return {"absolute_path": str(path), "sha256": sha256(path), "size_bytes": path.stat().st_size}


def compile_header_identity() -> dict[str, Any]:
    """Bind the lexical header selected by ``-I.../include`` and its target."""

    if not COMPILE_MCRUN_HEADER.is_symlink():
        raise ValueError(f"actual compile MCRun header is not the expected symlink: {COMPILE_MCRUN_HEADER}")
    resolved = COMPILE_MCRUN_HEADER.resolve(strict=True)
    if resolved != SOURCE_MCRUN_HEADER:
        raise ValueError(f"actual compile MCRun header resolves unexpectedly: {resolved}")
    if sha256(COMPILE_MCRUN_HEADER) != PINNED[SOURCE_MCRUN_HEADER]:
        raise ValueError("actual compile MCRun header bytes differ from pinned source header")
    return {
        "lexical_path": str(COMPILE_MCRUN_HEADER),
        "is_symlink": True,
        "symlink_target": os.readlink(COMPILE_MCRUN_HEADER),
        "resolved_path": str(resolved),
        "sha256": sha256(COMPILE_MCRUN_HEADER),
        "size_bytes": COMPILE_MCRUN_HEADER.stat().st_size,
    }


def parse_dependency_file(path: Path, *, cwd: Path) -> list[dict[str, Any]]:
    """Parse and hash the compiler-emitted ``-MD`` full header closure."""

    raw = path.read_text(encoding="utf-8")
    logical = raw.replace("\\\n", "")
    if ":" not in logical:
        raise ValueError("compiler dependency file has no target separator")
    _, dependency_text = logical.split(":", 1)
    names = shlex.split(dependency_text, posix=True)
    if not names:
        raise ValueError("compiler dependency closure is empty")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for name in names:
        lexical = Path(name)
        if not lexical.is_absolute():
            lexical = (cwd / lexical).absolute()
        key = str(lexical)
        if key in seen:
            continue
        seen.add(key)
        if not lexical.exists():
            raise FileNotFoundError(f"compiler dependency disappeared: {lexical}")
        resolved = lexical.resolve(strict=True)
        if not resolved.is_file():
            raise ValueError(f"compiler dependency is not a regular file: {lexical}")
        rows.append({
            "lexical_path": key,
            "is_symlink": lexical.is_symlink(),
            "resolved_path": str(resolved),
            "sha256": sha256(resolved),
            "size_bytes": resolved.stat().st_size,
        })
    rows.sort(key=lambda row: row["lexical_path"])
    return rows


def linked_libraries(text: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for line in text.splitlines():
        match = re.search(r"=>\s+(/\S+)\s+\(", line) or re.match(r"\s*(/\S+)\s+\(", line)
        if match is None:
            continue
        lexical = Path(match.group(1))
        resolved = lexical.resolve()
        if not resolved.is_file():
            raise FileNotFoundError(resolved)
        result.append({
            "loader_path": str(lexical), "resolved_path": str(resolved),
            "sha256": sha256(resolved), "size_bytes": resolved.stat().st_size,
        })
    return sorted(result, key=lambda row: row["loader_path"])


def build(output: Path) -> dict[str, Any]:
    if output.exists():
        raise FileExistsError(f"write-once preload build exists: {output}")
    for path, expected in PINNED.items():
        actual = sha256(path)
        if actual != expected:
            raise ValueError(f"pinned installed authority drift: {path}: {actual} != {expected}")
    actual_compile_header = compile_header_identity()

    source_text = SOURCE.read_text(encoding="utf-8") + "\n" + TRANSACTION_HEADER.read_text(encoding="utf-8")
    forbidden = [token for token in FORBIDDEN_RNG if token in source_text]
    if forbidden:
        raise ValueError(f"observer source references forbidden RNG APIs: {forbidden}")
    if source_text.count("original(this, event, particleSource);") != 1:
        raise ValueError("observer must call the RTLD_NEXT installed MCRun implementation exactly once")
    for required in (
        "RTLD_NEXT", "GetSimulatedTime()/s", "particleSource->GetParticlePosition()",
        "particleSource->GetParticleMomentumDirection()", "particleSource->GetParticlePolarization()",
        "particleSource->GetParticleEnergy()/keV", "before+1", "GetNumberOfParticle() != 1",
        "O_EXCL | O_NOFOLLOW", "TES511_PRELOAD_ALLOWED_ROOT", "std::atexit(Finalize)",
        "void Finalize() noexcept", "exception escaped transaction finalizer",
        "PASS__GENERATED_OBSERVATIONS_ONLY__NOT_JOB_PASS", "artifact_is_transport_authority",
        "generated_observations_sha256", "generated_observations_size_bytes",
        "actual vertex/primary bits differ from the post-GPS getter state",
        "primary->GetG4code() != definition", "vertex->GetT0()", "particleSource->GetParticleTime()",
        "TES511_PRELOAD_EXPECTED_LIBCOSIMA", "TES511_PRELOAD_EXPECTED_LIBCOSIMA_SHA256",
        "dladdr(address, &information)", "gResolvedOriginalLibraryPath != resolvedOrigin",
        "M05ObserverPublishDirectoryNoReplaceDurable(", "PostRenameFsyncFailedQuarantined",
    ):
        if required not in source_text:
            raise ValueError(f"observer source contract token absent: {required}")

    nm_cosima = run(["nm", "-D", str(LIB_COSIMA)], cwd=PACKAGE)
    definitions = [line for line in nm_cosima.splitlines() if line.endswith(" " + TARGET_SYMBOL)]
    if len(definitions) != 1 or " T " not in definitions[0]:
        raise ValueError("installed libCosima lacks one exported MCRun GeneratePrimaries definition")
    relocations = run(["readelf", "-rW", str(LIB_COSIMA)], cwd=PACKAGE)
    matching_relocations = [line for line in relocations.splitlines() if TARGET_SYMBOL in line]
    if len(matching_relocations) != 1 or "JUMP_SLOT" not in matching_relocations[0]:
        raise ValueError("installed libCosima call boundary is not one PLT/JUMP_SLOT relocation")
    dynamic_cosima = run(["readelf", "-dW", str(LIB_COSIMA)], cwd=PACKAGE)
    if "SYMBOLIC" in dynamic_cosima or "DF_SYMBOLIC" in dynamic_cosima:
        raise ValueError("installed libCosima forbids symbol interposition")

    compiler_name = os.environ.get("CXX", "g++")
    compiler = Path(shutil.which(compiler_name) or "")
    if not compiler.is_file():
        raise FileNotFoundError(compiler_name)
    root_cflags = shlex.split(run([str(ROOT_CONFIG), "--cflags"], cwd=PACKAGE).strip())
    root_libs = shlex.split(run([str(ROOT_CONFIG), "--libs"], cwd=PACKAGE).strip())
    g4_cflags = shlex.split(run([str(G4_CONFIG), "--cflags"], cwd=PACKAGE).strip())

    output.mkdir(parents=True, exist_ok=False)
    partial = output / ".libM05GPSPreloadObserver.so.partial"
    binary = output / "libM05GPSPreloadObserver.so"
    dependency_partial = output / ".compile_dependencies.d.partial"
    dependency_file = output / "compile_dependencies.d"
    command = [
        str(compiler), "-O2", "-Wall", "-Wextra", "-Werror", "-Wno-unused-parameter",
        "-Wno-deprecated-declarations", "-fPIC", "-shared", "-D_REENTRANT", "-D___LINUX___", "-D___CLING___",
        "-MD", "-MF", str(dependency_partial), "-MT", str(binary),
        "-I" + str(MEGALIB / "include"), "-I" + str(MEGALIB / "config"),
        *root_cflags, *g4_cflags, "-std=c++17", str(SOURCE), "-Wl,--no-undefined",
        "-Wl,--disable-new-dtags", "-Wl,-rpath," + str(MEGALIB / "lib"),
        "-Wl,-rpath," + str(G4_ROOT / "lib"),
        "-Wl,-rpath," + str(MEGALIB / "external/root_v6.36.6/lib"),
        "-L" + str(MEGALIB / "lib"), "-L" + str(G4_ROOT / "lib"),
        "-lG4event", "-lG4particles", "-lG4global", "-lG4clhep", "-lcrypto", "-ldl",
        *root_libs, "-o", str(partial),
    ]
    build_log = run(command, cwd=output)
    dependencies = parse_dependency_file(dependency_partial, cwd=output)
    dependency_paths = {row["lexical_path"] for row in dependencies}
    for required_dependency in (str(SOURCE), str(TRANSACTION_HEADER), str(COMPILE_MCRUN_HEADER)):
        if required_dependency not in dependency_paths:
            raise ValueError(f"compiler dependency closure omits {required_dependency}")
    os.replace(partial, binary)
    os.replace(dependency_partial, dependency_file)
    fsync_directory(output)
    write_once(output / "build.log", build_log.encode("utf-8"))

    nm_defined = run(["nm", "-D", "--defined-only", str(binary)], cwd=output)
    exported = [line for line in nm_defined.splitlines() if line.endswith(" " + TARGET_SYMBOL)]
    if len(exported) != 1 or " T " not in exported[0]:
        raise ValueError("compiled observer does not export exactly the target MCRun symbol")
    nm_undefined = run(["nm", "-uC", str(binary)], cwd=output)
    rng_undefined = [line for line in nm_undefined.splitlines() if FORBIDDEN_RNG_SYMBOL_PATTERN.search(line)]
    if rng_undefined:
        raise ValueError(f"observer imports RNG symbols: {rng_undefined}")
    disassembly = run(["objdump", "-drC", str(binary)], cwd=output)
    rng_disassembly = [line for line in disassembly.splitlines() if FORBIDDEN_RNG_SYMBOL_PATTERN.search(line)]
    if rng_disassembly:
        raise ValueError(f"observer disassembly references RNG symbols: {rng_disassembly}")
    ldd = run(["ldd", str(binary)], cwd=output)
    if "not found" in ldd:
        raise ValueError("observer has unresolved dynamic dependencies")
    dynamic_observer = run(["readelf", "-dW", str(binary)], cwd=output)
    if re.search(r"\(NEEDED\).*libCosima(?:\.so)?", dynamic_observer):
        raise ValueError("observer must not acquire a direct NEEDED dependency on libCosima")

    manifest = {
        "schema_version": 2,
        "status": "PASS__PRELOAD_OBSERVER_BUILD_ONLY__NOT_EXECUTED",
        "artifact_is_transport_authority": False,
        "transport_events_launched": 0,
        "builder": {"path": rel(Path(__file__).resolve()), "sha256": sha256(Path(__file__).resolve()),
                    "size_bytes": Path(__file__).resolve().stat().st_size},
        "runtime_state": "DORMANT__NO_COSIMA_OR_EVENTLIST_EXECUTION",
        "source": {"path": rel(SOURCE), "sha256": sha256(SOURCE), "size_bytes": SOURCE.stat().st_size},
        "transaction_header": {
            "path": rel(TRANSACTION_HEADER), "sha256": sha256(TRANSACTION_HEADER),
            "size_bytes": TRANSACTION_HEADER.stat().st_size,
        },
        "binary": {"path": str(binary), "sha256": sha256(binary), "size_bytes": binary.stat().st_size},
        "target": {
            "mangled_symbol": TARGET_SYMBOL,
            "installed_cosima": identity(COSIMA),
            "installed_libCosima": identity(LIB_COSIMA),
            "installed_libG4event": identity(LIB_G4EVENT),
            "definition": definitions[0],
            "plt_relocation": matching_relocations[0],
            "df_symbolic_absent": True,
        },
        "pinned_source_and_tool_authorities": [identity(path) for path in sorted(PINNED, key=str)],
        "actual_compile_mcrun_header": actual_compile_header,
        "compiler_dependency_file": {
            "path": str(dependency_file),
            "sha256": sha256(dependency_file),
            "size_bytes": dependency_file.stat().st_size,
        },
        "compiler_dependency_mode": "-MD__INCLUDING_SYSTEM_HEADERS",
        "compiler_dependency_closure": dependencies,
        "compiler": {
            **identity(compiler.resolve()),
            "version": run([str(compiler), "--version"], cwd=output).splitlines()[0],
        },
        "compile_command": command,
        "build_log_sha256": sha256(output / "build.log"),
        "exported_target_definition": exported[0],
        "undefined_symbols_sha256": sha256_bytes(nm_undefined.encode("utf-8")),
        "disassembly_sha256": sha256_bytes(disassembly.encode("utf-8")),
        "rng_source_scan": "PASS",
        "rng_undefined_symbol_scan": "PASS",
        "rng_disassembly_scan": "PASS",
        "ldd": ldd,
        "linked_library_manifest": linked_libraries(ldd),
        "dynamic_section_sha256": sha256_bytes(dynamic_observer.encode("utf-8")),
        "needed_libCosima_absent": True,
        "runtime_contract": {
            "original_call_count": 1,
            "new_vertex_count": 1,
            "new_primary_count": 1,
            "observation_boundary": "MCRun::GeneratePrimaries return; GPS getters plus MCRun simulated time",
            "rtld_next_origin": {
                "status": "REQUIRED_AT_RUNTIME__DLADDR_CANONICAL_PATH_EXACT",
                "expected_path": str(LIB_COSIMA),
                "expected_sha256": PINNED[LIB_COSIMA],
                "runtime_environment": [
                    "TES511_PRELOAD_EXPECTED_LIBCOSIMA",
                    "TES511_PRELOAD_EXPECTED_LIBCOSIMA_SHA256",
                ],
            },
            "vertex_primary_copy_closure": (
                "PASS__SOURCE_REQUIRES_BIT_EXACT_GPS_GETTERS_TO_NEW_VERTEX_PRIMARY_DEFINITION_POSITION_"
                "DIRECTION_POLARIZATION_ENERGY_AND_PARTICLE_TIME"
            ),
            "transaction": (
                "O_EXCL/O_NOFOLLOW .partial; signal leaves partial; fsync; Linux "
                "renameat2(RENAME_NOREPLACE) with no ordinary-rename fallback; post-rename parent-fsync "
                "failure moves only the exact owned published inode to a collision-safe .failed namespace"
            ),
            "completion_scope": "generated observations only; outer job validator/receipt remains mandatory",
            "outer_job_completion_required": [
                "installed Cosima process exits 0 without signal/timeout/OOM",
                "complete rich SIM passes strict canonical/event validation",
                "unique native DAT and TT pass strict validation",
                "generated-only observer transaction passes exact tape/count/hash validation",
                "C-arm production bundles separately require hash-bound RP reconciliation; F/U sentinel does not claim it",
                "outer job receipt atomically binds every preceding artifact and validation",
            ],
        },
    }
    write_once(output / "build_manifest.json", canonical_json_bytes(manifest))
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    build(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

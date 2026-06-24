#!/usr/bin/env python3
"""Audit installed Cosima delayed-source semantics for Phase-2 authority v2."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PHASE_DIR = Path(__file__).resolve().parents[1]
ROOT = Path(__file__).resolve().parents[3]
OUT = PHASE_DIR / "03_source_semantics"

MEGALIB = Path("/home/ubuntu/MEGAlib_Install/megalib-main")
COSIMA = MEGALIB / "bin/cosima"
GEOMETRY = (
    ROOT
    / "outputs/geometry/DEMO2_DR_v3p5_user_cylmag_redesign_multiholeW_fix5_20260621_megalib_proxy/"
    / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)

SOURCE_FILES = {
    "MCParameterFile.cc": MEGALIB / "src/cosima/src/MCParameterFile.cc",
    "MCIsotopeStore.cc": MEGALIB / "src/cosima/src/MCIsotopeStore.cc",
    "MCSource.cc": MEGALIB / "src/cosima/src/MCSource.cc",
    "MCSteppingAction.cc": MEGALIB / "src/cosima/src/MCSteppingAction.cc",
}


def rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


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


def contains(path: Path, needle: str) -> bool:
    return needle in path.read_text(encoding="utf-8", errors="replace")


def write_syntax_probe_source(path: Path) -> None:
    text = f"""Version 1
Geometry {GEOMETRY}
PhysicsListEM LivermorePol
PhysicsListRadioactiveDecay true
DecayMode ActivationDelayedDecay
DetectorTimeConstant 1e-9

Run SyntaxProbe
SyntaxProbe.FileName {OUT / "excited_ion_source_syntax_test"}
SyntaxProbe.NEvents 1
SyntaxProbe.Source ExcitedIonProbe

ExcitedIonProbe.Particles Ion 6011 1000.0
ExcitedIonProbe.Beam PointSource 0 0 0
ExcitedIonProbe.Spectrum Mono 0
ExcitedIonProbe.Flux 1.0
"""
    path.write_text(text, encoding="utf-8")


def run_syntax_probe(source: Path, log: Path) -> dict[str, Any]:
    if not COSIMA.exists():
        message = f"ERROR: missing cosima executable: {COSIMA}\n"
        log.write_text(message, encoding="utf-8")
        return {
            "status": "MISSING_COSIMA",
            "returncode": None,
            "log": rel(log),
            "rejected_particles_ion_keyword": False,
        }
    try:
        proc = subprocess.run(
            [str(COSIMA), str(source)],
            cwd=ROOT,
            env=cosima_env(),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
            timeout=180,
        )
        log.write_text(proc.stdout, encoding="utf-8", errors="replace")
        rejected = proc.returncode != 0 and "Unknown keyword: Particles" in proc.stdout
        status = "REJECTED_UNSUPPORTED_PARTICLES_ION" if rejected else "UNEXPECTED_RESULT"
        return {
            "status": status,
            "returncode": proc.returncode,
            "log": rel(log),
            "rejected_particles_ion_keyword": rejected,
        }
    except subprocess.TimeoutExpired as exc:
        output = exc.stdout or ""
        if isinstance(output, bytes):
            output = output.decode("utf-8", errors="replace")
        log.write_text(output + "\nERROR: syntax probe timed out\n", encoding="utf-8")
        return {
            "status": "TIMEOUT",
            "returncode": None,
            "log": rel(log),
            "rejected_particles_ion_keyword": False,
        }


def static_evidence() -> dict[str, Any]:
    p = SOURCE_FILES["MCParameterFile.cc"]
    store = SOURCE_FILES["MCIsotopeStore.cc"]
    source = SOURCE_FILES["MCSource.cc"]
    stepping = SOURCE_FILES["MCSteppingAction.cc"]
    checks = {
        "detector_time_constant_parser": contains(p, 'T->IsTokenAt(0, "DetectorTimeConstant", true)')
        and contains(p, "m_DetectorTimeConstant = T->GetTokenAtAsDouble(1)*s"),
        "activation_sources_parser": contains(p, 'T->IsTokenAt(1, "ActivationSources", true)')
        and contains(p, "CreateSourceListByActivity()"),
        "eventlist_parser": contains(p, 'T->IsTokenAt(1, "EventList", true)')
        and contains(source, "bool MCSource::SetEventListFromFile(MString FileName)"),
        "eventlist_reads_particle_excitation": contains(source, "Entry->m_ParticleType = Tokens.GetTokenAtAsInt(2)")
        and contains(source, "Entry->m_ParticleExcitation = Tokens.GetTokenAtAsInt(3)"),
        "eventlist_reads_exact_position": contains(
            source,
            "Entry->m_Position = G4ThreeVector(Tokens.GetTokenAtAsDouble(5)*cm",
        )
        and contains(source, "SetCentreCoords(m_EventList[0]->m_Position)"),
        "ordinary_particle_type_parser_only_sets_za": contains(
            p,
            'T->IsTokenAt(1, "ParticleType", true) == true || T->IsTokenAt(1, "Particle", true)',
        )
        and contains(p, "Source->SetParticleType(T->GetTokenAtAsInt(2))"),
        "no_particle_excitation_token_in_parameter_parser": "ParticleExcitation" not in p.read_text(
            encoding="utf-8", errors="replace"
        ),
        "isotope_store_loads_excitation_keV": contains(store, "m_Excitations.back().back().push_back(Tokenizer.GetTokenAtAsDouble(2)*keV)"),
        "activation_source_sets_particle_excitation": contains(store, "Source->SetParticleExcitation(m_Excitations[v][i][e])"),
        "activation_source_sets_volume_and_flux": contains(store, "Source->SetVolume(m_VolumeNames[v])")
        and contains(store, "Source->SetFlux(m_Values[v][i][e]/s)"),
        "source_particle_definition_uses_excitation": contains(
            source,
            "MCSteppingAction::GetParticleDefinition(m_ParticleType, m_ParticleExcitation)",
        ),
        "geant4_ion_lookup_uses_excitation": contains(stepping, "Table->GetIon(AtomicNumber, AtomicMass, Excitation)"),
        "activation_buildup_detector_time_constant_cut": contains(
            stepping,
            "m_DecayMode == MCParameterFile::c_DecayModeActivationBuildUp",
        )
        and contains(stepping, "TimeDelay > m_DetectorTimeConstant"),
        "activation_delayed_decay_detector_time_constant_cut": contains(
            stepping,
            "m_DecayMode == MCParameterFile::c_DecayModeActivationDelayedDecay",
        )
        and contains(stepping, "DoNotStart = true"),
    }
    return checks


def write_docs(verdict: dict[str, Any]) -> None:
    semantics = OUT / "installed_megalib_activation_semantics.md"
    semantics.write_text(
        "\n".join(
            [
                "# Installed MEGAlib Activation Semantics",
                "",
                "Decision: use EventList for exact-position custom source-v2 authority, and use `Run.ActivationSources <isotope-store.dat>` for the native volume-based oracle.",
                "",
                "Evidence from installed source code:",
                "- `MCParameterFile.cc:977-985` parses `Source.EventList <file>`.",
                "- `MCSource.cc:2274-2289` requires 15 EventList tokens and reads particle type from token 2, an excitation field from token 3, time from token 4, and position from tokens 5-7.",
                "- `MCSource.cc:2466-2479`, `2636-2642`, and `2792-2797` use the EventList particle, energy, position, and direction when firing the particle gun.",
                "- `MCParameterFile.cc:919-929` parses `Run.ActivationSources`, loads an `MCIsotopeStore`, and adds sources from `CreateSourceListByActivity()`.",
                "- `MCIsotopeStore.cc:175-188` documents the isotope-store format: `VN <volume>` and `RP <ZA> <excitation_keV> <value>`.",
                "- `MCIsotopeStore.cc:239-282` loads excitation from token 2 in keV and value from token 3.",
                "- `MCIsotopeStore.cc:371-394` creates activation sources with particle type, particle excitation, activation spectrum, near-field activation beam, volume, and flux.",
                "- `MCSource.cc:2502-2521` resolves the source particle definition through `MCSteppingAction::GetParticleDefinition(particle_type, particle_excitation)`.",
                "- `MCSteppingAction.cc:1911-1922` asks Geant4's ion table for `GetIon(Z, A, excitation)`.",
                "",
                "Rejected path:",
                "- Ordinary source-card `ParticleType` supports the ZA integer but has no parser token for excitation.",
                "- The `.Particles Ion <ZA> <excitation>` syntax is not accepted by this installed parser; see `excited_ion_source_syntax_test.log`.",
                "",
                "Implication for WP04:",
                "- The current G1 inventory has no positive non-ground states, so WP04 can emit an exact-position EventList and external weight ledger without state substitution.",
                "- Positive nonzero excitation in a future run must block or move to a hybrid/native stream until EventList excitation units are proven; the file parser reads token 3 as an integer and does not visibly multiply by keV.",
                "- WP04 should also emit a matching isotope-store activity file so WP05 can run the native volume-based comparison.",
                "- ParticleType-only delayed source cards can be retained only as legacy/comparator evidence, not as the state-resolved authority.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    decay = OUT / "decay_chain_semantics.md"
    decay.write_text(
        "\n".join(
            [
                "# Decay Chain Semantics",
                "",
                "The custom exact-position stream uses EventList rows. Its source-card normalization is external: each row has a weight from the WP04 activity ledger, and selected-rate analysis must consume the EventList weight sidecar.",
                "",
                "`ActivationSources` values are interpreted as activities in Bq by `CreateSourceListByActivity()` and are reserved for the native volume-based oracle.",
                "",
                "For custom exact-position delayed-source transport, use:",
                "- `PhysicsListRadioactiveDecay true`",
                "- `DecayMode ActivationDelayedDecay`",
                "- `Run.Source <event-list-source>`",
                "- `<event-list-source>.EventList <source-v2.eventlist.dat>`",
                "",
                "For native cross-check transport, use:",
                "- `Run.ActivationSources <source-v2-activity-store.dat>`",
                "",
                "The source nucleus is the primary delayed decay. Secondary decays inside the chain are handled by the installed Geant4 radioactive-decay path. `MCSteppingAction.cc` applies `DetectorTimeConstant` to decide whether non-primary delayed secondaries are kept in the same event or moved to future-event handling.",
                "",
                "This gate does not promote a numerical delayed rate. It only chooses the source representation needed by WP04.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    tc = OUT / "detector_time_constant_authority.md"
    tc.write_text(
        "\n".join(
            [
                "# DetectorTimeConstant Authority",
                "",
                "Installed parser evidence:",
                "- `MCParameterFile.cc:188-191` parses `DetectorTimeConstant <seconds>` and multiplies the token by `s`.",
                "- `MCParameterFile.cc:2998-3006` forwards that value to activators through `SetHalfLifeCutOff()`.",
                "- `MCSteppingAction.cc:980-994` and `1012-1022` compare decay delays against `m_DetectorTimeConstant` in activation buildup and activation delayed-decay modes.",
                "",
                "Authority for subsequent Phase-2 source cards:",
                "- Use `DetectorTimeConstant 1e-9` unless a later gate explicitly changes the timing contract.",
                "- WP06 still needs to audit final generated cards and logs; WP03 only establishes parser semantics.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    summary_md = OUT / "summary.md"
    summary_md.write_text(
        "\n".join(
            [
                "# WP03 Source Semantics Summary",
                "",
                f"status: `{verdict['status']}`",
                "",
                "Key findings:",
                "- Current all-ground exact-position source-v2 authority can use MEGAlib EventList plus a weight ledger.",
                "- Nonzero-excitation exact-position EventList remains a boundary condition, not a proven authority path.",
                "- `ActivationSources` remains the native volume-based cross-check path.",
                "- `ParticleType` alone loses excitation state.",
                "- `.Particles Ion` is not supported by this installed parser.",
                "- DetectorTimeConstant is parsed in seconds; use `1e-9` for the current contract.",
                "",
                f"syntax_probe_status: `{verdict['syntax_probe']['status']}`",
                f"syntax_probe_log: `{verdict['syntax_probe']['log']}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    source = OUT / "excited_ion_source_syntax_test.source"
    log = OUT / "excited_ion_source_syntax_test.log"
    write_syntax_probe_source(source)

    checks = static_evidence()
    syntax_probe = run_syntax_probe(source, log)
    required = [
        "detector_time_constant_parser",
        "activation_sources_parser",
        "eventlist_parser",
        "eventlist_reads_particle_excitation",
        "eventlist_reads_exact_position",
        "ordinary_particle_type_parser_only_sets_za",
        "no_particle_excitation_token_in_parameter_parser",
        "isotope_store_loads_excitation_keV",
        "activation_source_sets_particle_excitation",
        "activation_source_sets_volume_and_flux",
        "source_particle_definition_uses_excitation",
        "geant4_ion_lookup_uses_excitation",
        "activation_delayed_decay_detector_time_constant_cut",
    ]
    missing = [name for name in required if not checks.get(name)]
    status = "PASS" if not missing and syntax_probe["rejected_particles_ion_keyword"] else "FAIL"
    verdict = {
        "status": status,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "claim_boundary": "source-semantics only; no delayed-rate promotion",
        "strategy": "EVENTLIST_EXACT_POSITION_CUSTOM_SOURCE_WITH_NATIVE_ACTIVATION_SOURCES_ORACLE",
        "eventlist_exact_position_boundary": "valid for current all-ground positive inventory; positive nonzero excitation must block or use hybrid/native until EventList excitation units are proven",
        "do_not_use_for_authority": ["ParticleType-only excited delayed ions", ".Particles Ion syntax"],
        "source_code_checks": checks,
        "missing_required_checks": missing,
        "syntax_probe": syntax_probe,
        "source_files": {name: str(path) for name, path in SOURCE_FILES.items()},
        "fix5_geometry_used_for_probe": rel(GEOMETRY),
        "next_gate": "G4 build source-v2 EventList, weight ledger, and native isotope-store authority from raw inventory and RPIP alignment",
    }
    write_json(OUT / "source_semantics_verdict.json", verdict)
    write_docs(verdict)
    summary = {
        "status": status,
        "outputs": [
            rel(OUT / "source_semantics_verdict.json"),
            rel(OUT / "installed_megalib_activation_semantics.md"),
            rel(OUT / "decay_chain_semantics.md"),
            rel(OUT / "detector_time_constant_authority.md"),
            rel(source),
            rel(log),
            rel(OUT / "summary.md"),
        ],
        "findings": [
            "EventList preserves excitation and exact position for custom source-v2 transport.",
            "ActivationSources/isotope-store preserves excitation and volume for native oracle transport.",
            "ParticleType-only source cards cannot represent excitation state.",
            ".Particles Ion syntax is rejected by installed Cosima parser.",
            "DetectorTimeConstant is parsed as seconds and participates in activation delayed-decay branching.",
        ],
        "next_gate": verdict["next_gate"],
        "user_decision_required": False,
    }
    write_json(OUT / "summary.json", summary)
    print(f"WP03 {status}")
    print(json.dumps(verdict, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

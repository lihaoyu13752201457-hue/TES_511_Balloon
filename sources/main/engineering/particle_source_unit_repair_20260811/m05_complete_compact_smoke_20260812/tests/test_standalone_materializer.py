#!/usr/bin/env python3
"""Zero-transport fixtures for the compact-truth standalone SIM materializer."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from typing import Any


PACKAGE = Path(__file__).resolve().parents[1]
CODE = PACKAGE / "code"
sys.path.insert(0, str(CODE))

import materialize_standalone_sim as materializer  # noqa: E402
import build_mfileeventssim_roundtrip  # noqa: E402
import revan_zero_transport_gate  # noqa: E402
import tape_contract  # noqa: E402
import geometry_classification  # noqa: E402


_CLASSIFICATION_BYTES: bytes | None = None


def _classification_bytes() -> bytes:
    global _CLASSIFICATION_BYTES
    if _CLASSIFICATION_BYTES is None:
        _CLASSIFICATION_BYTES = materializer.canonical_json_bytes(
            geometry_classification.build_geometry_classification()
        )
    return _CLASSIFICATION_BYTES


def _write_tsv(path: Path, header: list[str] | tuple[str, ...], rows: list[list[Any]]) -> None:
    path.write_text(
        "\t".join(header) + "\n" + "".join("\t".join(str(value) for value in row) + "\n" for row in rows),
        encoding="utf-8",
    )


def _eventlist_line(event_id: int, particle: int, time_s: float, position: tuple[float, float, float],
                    direction: tuple[float, float, float], energy: float) -> str:
    fields = [
        str(event_id), "0", str(particle), "0", format(time_s, ".17g"),
        *(format(value, ".17g") for value in position),
        *(format(value, ".17g") for value in direction),
        "0", "0", "0", format(energy, ".17g"),
    ]
    assert len(fields) == 15
    return " ".join(fields)


def _native_with_ht(tape: materializer.TapeRow, event_id: int) -> bytes:
    lines = materializer.minimal_event(tape, event_id).decode("utf-8").splitlines()
    lines[3] = "ED 1.25"
    position = (21.09300, 9.31843, 13.48453)  # Known active detector coordinate in the Mass geometry.
    hit = (
        "HTsim 4;"
        + ";".join(materializer._scientific(value, 17, 24) for value in position)
        + ";" + materializer._scientific(1.25, 17, 23)
        + ";" + materializer._scientific(0.0, 17, 23)
        + ";1"
    )
    lines.append(hit)
    return ("\n".join(lines) + "\n").encode("utf-8")


def build_fixture(root: Path, *, geometry: Path | None = None, corruption: str | None = None) -> dict[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    if geometry is None:
        geometry = root / "fixture.geo.setup"
        geometry.write_text("Name M05MaterializerFixture\n", encoding="utf-8")
    geometry = geometry.resolve()

    states = [
        ((21.0, 9.0, 60.0), (0.0, 0.0, -1.0), 16.392, 0.00065601312345678),
        ((0.0, 0.0, 60.0), (0.0, 0.0, -1.0), 20.0, 0.001),
        ((-10.0, -20.0, 60.0), (0.0, 0.0, -1.0), 30.0, 0.002),
        ((5.0, -7.0, 60.0), (0.0, 0.0, -1.0), 40.0, 0.003),
        ((-8.0, 11.0, 60.0), (0.0, 0.0, -1.0), 50.0, 0.004),
    ]
    tape_lines: list[str] = []
    sidecar_rows: list[list[Any]] = []
    tape_rows: list[materializer.TapeRow] = []
    source_card_sha = materializer.sha256_bytes(b"fixture source card\n")
    source_contract_sha = materializer.sha256_bytes(b"fixture source contract\n")
    spectrum_sha = materializer.sha256_bytes(b"fixture corrected-keV spectrum\n")
    sampler_seed = 123456789
    built_rows: list[dict[str, str]] = []
    runtime_primaries: list[tape_contract.Primary] = []
    previous_runtime_internal_time = 0.0
    for index, (position, direction, energy, source_time) in enumerate(states):
        eventlist_id = index + 1
        line = _eventlist_line(eventlist_id, 6, source_time, position, direction, energy)
        raw_sha = materializer.sha256_bytes(line.encode("utf-8"))
        expected_sha = materializer.tuple_hash(6, 0.0, source_time, position, direction, (0.0, 0.0, 0.0), energy)
        row = {
            "schema": "m05-tape-root-v2", "row_index0": str(index), "global_row_index0": str(index),
            "eventlist_id": str(eventlist_id), "stable_root_id": "", "driver": "Atm_n_bin00_down",
            "driver_assignment": "sampled_exact_not_inferred", "bin_index": "0", "family": "n", "mode": "instant",
            "source_card_path": "fixture.source", "source_card_sha256": source_card_sha,
            "source_contract_path": "fixture.contract.json", "source_contract_sha256": source_contract_sha,
            "spectrum_path": "fixture.spectrum.dat", "spectrum_sha256": spectrum_sha,
            "sampler_algorithm": tape_contract.SAMPLER_ALGORITHM, "sampler_seed_u64": str(sampler_seed),
            "sampler_counter_start0": str(index * 7), "sampler_counter_end0": str(index * 7 + 7),
            "particle": "6", "excitation_keV": "0", "source_time_s": format(source_time, ".17g"),
            "global_poisson_time_s": format(source_time, ".17g"), "shard_global_time_offset_s": "0",
            "x_cm": format(position[0], ".17g"), "y_cm": format(position[1], ".17g"),
            "z_cm": format(position[2], ".17g"), "dx": format(direction[0], ".17g"),
            "dy": format(direction[1], ".17g"), "dz": format(direction[2], ".17g"),
            "px": "0", "py": "0", "pz": "0", "energy_keV": format(energy, ".17g"),
            "raw_eventlist_line_sha256": raw_sha, "expected_eventlist_binary64_sha256": "",
            "expected_generated_binary64_sha256": "",
            "expected_generated_tuple_sha256": expected_sha,
            "control_flag": "",
        }
        primary = tape_contract._primary_from_row(row)
        eventlist_binary64_sha = tape_contract.eventlist_binary64_hash(primary)
        runtime_source_time, previous_runtime_internal_time = tape_contract.runtime_source_time_projection(
            primary.source_time_s, previous_runtime_internal_time
        )
        runtime_primary = tape_contract.runtime_projected_primary(
            primary, runtime_source_time_s=runtime_source_time
        )
        runtime_primaries.append(runtime_primary)
        generated_binary64_sha = tape_contract.generated_binary64_hash(
            primary, runtime_source_time_s=runtime_source_time
        )
        row["expected_eventlist_binary64_sha256"] = eventlist_binary64_sha
        row["expected_generated_binary64_sha256"] = generated_binary64_sha
        row["stable_root_id"] = materializer.sha256_bytes(materializer.canonical_json_bytes(
            tape_contract._root_payload(
                row=row, raw_line_sha256=raw_sha,
                eventlist_binary64_sha256=eventlist_binary64_sha,
                generated_binary64_sha256=generated_binary64_sha, tuple_sha256=expected_sha,
            )
        ))
        row["control_flag"] = "1" if index < 3 or int(row["stable_root_id"][:16], 16) % 100 == 0 else "0"
        built_rows.append(row)
        tape_lines.append(line)
    while built_rows[3]["control_flag"] == "1" or built_rows[4]["control_flag"] == "1":
        sampler_seed += 1
        for index, row in enumerate(built_rows):
            row["sampler_seed_u64"] = str(sampler_seed)
            row["stable_root_id"] = materializer.sha256_bytes(materializer.canonical_json_bytes(
                tape_contract._root_payload(
                    row=row, raw_line_sha256=row["raw_eventlist_line_sha256"],
                    eventlist_binary64_sha256=row["expected_eventlist_binary64_sha256"],
                    generated_binary64_sha256=row["expected_generated_binary64_sha256"],
                    tuple_sha256=row["expected_generated_tuple_sha256"],
                )
            ))
            row["control_flag"] = "1" if index < 3 or int(row["stable_root_id"][:16], 16) % 100 == 0 else "0"
    if corruption == "tape_hash":
        built_rows[0]["raw_eventlist_line_sha256"] = "0" * 64
    elif corruption == "generated_tape_binary":
        built_rows[0]["expected_generated_binary64_sha256"] = "0" * 64
    for index, row in enumerate(built_rows):
        sidecar_rows.append([row[column] for column in tape_contract.SIDECAR_COLUMNS])
        position, direction, energy, source_time = states[index]
        tape_rows.append(materializer.TapeRow(
            index, index + 1, row["stable_root_id"], "Atm_n_bin00_down", "n", "instant", 6, 0.0, source_time, position, direction,
            (0.0, 0.0, 0.0), energy, row["raw_eventlist_line_sha256"],
            row["expected_generated_tuple_sha256"], row["expected_eventlist_binary64_sha256"],
            row["expected_generated_binary64_sha256"],
            row["control_flag"] == "1",
        ))
    tape = root / "fixture.eventlist"
    tape.write_text("\n".join(tape_lines) + "\n", encoding="utf-8")
    tape_roots = root / "fixture.tape_roots.tsv"
    _write_tsv(tape_roots, tape_contract.SIDECAR_COLUMNS, sidecar_rows)

    native_controls = [materializer.minimal_event(tape_rows[index], index + 1) for index in range(3)]
    native_candidate = _native_with_ht(tape_rows[4], 5)
    if corruption == "id":
        native_controls[0] = native_controls[0].replace(b"ID 1 1\n", b"ID 9 9\n", 1)
    elif corruption == "se":
        native_controls[0] = b"SE\n" + native_controls[0]
    elif corruption == "ia":
        native_controls[0] = native_controls[0].replace(b"IA INIT", b"IA BAD?", 1)
    elif corruption == "ht":
        native_candidate = native_candidate.replace(b";1\n", b";99\n", 1)
    selected = [
        (1, "control", native_controls[0]),
        (2, "control", native_controls[1]),
        (3, "control", native_controls[2]),
        (5, "candidate", native_candidate),
    ]
    if corruption == "missing_control":
        selected = selected[-1:]
    truth_blob = b"".join(fragment for _, _, fragment in selected)
    truth_stream = root / "fixture.truth.sim"
    truth_stream.write_bytes(truth_blob)
    truth_rows: list[list[Any]] = []
    cursor = 0
    for event_id, reason, fragment in selected:
        digest = materializer.sha256_bytes(fragment)
        if corruption == "truth_hash" and event_id == 1:
            digest = "f" * 64
        truth_rows.append([event_id, tape_rows[event_id - 1].stable_root_id, reason, cursor, len(fragment), digest])
        cursor += len(fragment)

    root_rows: list[list[Any]] = []
    generated_observation_rows: list[list[Any]] = []
    event_rows: list[list[Any]] = []
    for event_id, tape_row in enumerate(tape_rows, 1):
        runtime_primary = runtime_primaries[event_id - 1]
        control = 1 if tape_row.control_flag else 0
        serialized_ia_sha = materializer.ia_init_hash(
            tape_row.particle, 0.0, tape_row.position_cm,
            tape_row.direction, tape_row.polarization, tape_row.energy_keV,
        )
        root_rows.append([
            event_id, event_id - 1, event_id, tape_row.stable_root_id, tape_row.driver,
            "", "unavailable", "[]", "n", 1, 1, 1, 1, 0, tape_row.raw_line_sha256,
            tape_row.expected_tuple_sha256, tape_row.expected_tuple_sha256, serialized_ia_sha, control,
        ])
        generated_binary = tape_row.generated_binary64_sha256
        generated_observation_rows.append([
            event_id, tape_row.stable_root_id, event_id, tape_row.eventlist_binary64_sha256,
            tape_row.particle, format(tape_row.excitation_keV, ".17g"), format(runtime_primary.source_time_s, ".17g"),
            *(format(value, ".17g") for value in runtime_primary.position_cm),
            *(format(value, ".17g") for value in runtime_primary.direction),
            *(format(value, ".17g") for value in runtime_primary.polarization),
            format(runtime_primary.energy_keV, ".17g"), generated_binary,
            materializer._time_text(tape_row.source_time_s), tape_row.particle, "0",
            *(format(value, ".17g") for value in runtime_primary.position_cm),
            *(format(value, ".17g") for value in runtime_primary.direction),
            *(format(value, ".17g") for value in runtime_primary.polarization),
            format(runtime_primary.energy_keV, ".17g"), serialized_ia_sha,
            "1e-06", "1e-09", "1e-09", "GENERATED_BINARY64_BE_V1__IA_SERIALIZED_17G_FIELD_TOL_V2",
        ])
        if corruption == "observation_tape_binary" and event_id == 1:
            generated_observation_rows[-1][3] = "f" * 64
        elif corruption == "observation_generated_binary" and event_id == 1:
            # Stay inside the declared serialized-field/quantized-tuple tolerances,
            # but change the binary64 identity.  Only the exact tape-generated
            # binary64 join should reject this fixture.
            changed_position = (tape_row.position_cm[0] + 1.0e-7, *tape_row.position_cm[1:])
            generated_observation_rows[-1][7] = format(changed_position[0], ".17g")
            generated_observation_rows[-1][17] = tape_contract._binary64_hash(
                tape_contract.Primary(
                    particle=tape_row.particle,
                    excitation_keV=tape_row.excitation_keV,
                    source_time_s=tape_row.source_time_s,
                    global_poisson_time_s=tape_row.source_time_s,
                    position_cm=changed_position,
                    direction=tape_row.direction,
                    polarization=tape_row.polarization,
                    energy_keV=tape_row.energy_keV,
                    driver=tape_row.driver,
                    bin_index=0,
                    spectrum_path="fixture.spectrum.dat",
                    spectrum_sha256=spectrum_sha,
                    sampler_counter_start0=0,
                    sampler_counter_end0=7,
                ),
                tape_row.direction,
            )
        tes = "1.25" if event_id == 5 else "0"
        raw_positive = 1 if event_id == 5 else 0
        event_rows.append([
            event_id, tape_row.stable_root_id, "mass_model_511", format(runtime_primary.source_time_s, ".17g"), "1",
            tes, "0", "0", "0", "0", "0", "0", raw_positive, raw_positive,
            "tes" if raw_positive else "none", control, 1 if raw_positive or control else 0, 1, 1, 1,
        ])

    schema = json.loads(materializer.RECORD_SCHEMA.read_text(encoding="utf-8"))
    table_headers = {name: value["header"] for name, value in schema["x-tsv-tables"].items()}
    table_rows: dict[str, list[list[Any]]] = {
        "roots": root_rows,
        "generated_observations": generated_observation_rows,
        "events": event_rows,
        "truth_index": truth_rows,
        "pixels": [[5, tape_rows[4].stable_root_id, "TP_L0_0:TP_L0_0_Log:0", 0, "TP_L0_0:TP_L0_0_Log:0", "1.25", 0, 0, 0,
                    0, 0, 0, 1, 1, 1, "POST_GLOBAL_V1"]],
        "deposits": [[5, tape_rows[4].stable_root_id, 1, "tes", "TP_L0_0", "TP_L0_0_Log",
                      "TP_L0_0:TP_L0_0_Log:0", "HgTe", "1.25", 0, 0, 0, 0, 0, 0, 0, 0,
                      1, 0, 1, "neutron", "none", "neutron", "primary", "hadElastic"]],
        "activation": [],
    }
    whitelist = json.loads(materializer.ACTIVE_WHITELIST.read_text(encoding="utf-8"))
    whitelist_sha = materializer.sha256_file(materializer.ACTIVE_WHITELIST)
    veto_rows: list[list[Any]] = []
    for event_id, tape_row in enumerate(tape_rows, 1):
        for physical in whitelist["mass_csi_physical_volumes"]:
            veto_rows.append([
                event_id, tape_row.stable_root_id, "mass_model_511", f"mass_csi:{physical}", "mass_csi", physical,
                0, "", "", "", 0, "POST_GLOBAL_V1", whitelist_sha,
            ])
    table_rows["veto_blocks"] = veto_rows
    record_schema_sha = materializer.sha256_file(materializer.RECORD_SCHEMA)
    footer_values = [
        "C", "mass_model_511", "instant", "n", "fixture_job", 0, 12345, 5, 5, 5, 5, 5, 5, 5, 5, 5,
        0, 0, "0.004", "geometry_specific", whitelist_sha, record_schema_sha, 1,
    ]
    if corruption == "count":
        footer_values[8] = 2
    table_rows["footer"] = [footer_values]

    native_dat = root / "fixture.dat"
    native_dat.write_text("TT 0.004\nEN\n", encoding="utf-8")
    classification = root / "geometry_classification_manifest.json"
    classification.write_bytes(_classification_bytes())

    table_bindings: dict[str, dict[str, Any]] = {}
    for name in materializer.REQUIRED_TABLES:
        path = root / f"fixture.{name}.tsv"
        _write_tsv(path, table_headers[name], table_rows[name])
        table_bindings[name] = {"path": path.name, "sha256": materializer.sha256_file(path), "row_count": len(table_rows[name])}
    bundle = {
        "schema_version": "m05cc-v2-record-bundle",
        "record_schema_sha256": record_schema_sha,
        "veto_whitelist_sha256": whitelist_sha,
        "geometry_classification_sha256": materializer.sha256_file(classification),
        "provenance": {
            "geometry_bundle_sha256": next(
                entry["geometry_bundle_sha256"]
                for entry in json.loads(classification.read_text(encoding="utf-8"))["geometries"]
                if entry["geometry"] == "mass_model_511"
            ),
            "tape_root_sidecar_sha256": materializer.sha256_file(tape_roots),
            "tape_root_sidecar_path": tape_roots.name,
            "source_card_sha256": source_card_sha,
            "source_contract_sha256": source_contract_sha,
        },
        "run": {
            "arm": "C", "geometry": "mass_model_511", "mode": "instant", "family": "n",
            "job_id": "fixture_job", "shard_index": 0, "seed": 12345,
            "active_block_coverage": "geometry_specific", "expected_event_count": 5,
        },
        "tables": table_bindings,
        "blobs": {
            "truth_stream": {"path": truth_stream.name, "sha256": materializer.sha256_file(truth_stream), "size_bytes": len(truth_blob)},
            "native_dat": {"path": native_dat.name, "sha256": materializer.sha256_file(native_dat), "size_bytes": native_dat.stat().st_size},
        },
    }
    bundle_path = root / "record_bundle.json"
    if corruption == "provenance_tape_path":
        bundle["provenance"]["tape_root_sidecar_path"] = "wrong.tape_roots.tsv"
    bundle_path.write_bytes(materializer.canonical_json_bytes(bundle))
    return {
        "bundle": bundle_path, "tape": tape, "tape_roots": tape_roots,
        "geometry": geometry, "classification": classification,
    }


class StandaloneMaterializerTest(unittest.TestCase):
    def _materialize(self, fixture: dict[str, Path], prefix: Path) -> dict[str, Any]:
        return materializer.materialize(
            record_bundle=fixture["bundle"], tape_path=fixture["tape"], tape_roots_path=fixture["tape_roots"],
            geometry_path=fixture["geometry"], geometry_sha256=materializer.sha256_file(fixture["geometry"]),
            output_prefix=prefix, geometry_classification_path=fixture["classification"],
            _verify_tape_authorities=False,
        )

    def test_materializes_native_selected_control_and_minimal_nonselected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = build_fixture(root / "input")
            result = self._materialize(fixture, root / "output")
            self.assertEqual(result["counts"]["event_count"], 5)
            self.assertEqual(result["counts"]["native_event_count"], 4)
            self.assertEqual(result["counts"]["minimal_init_event_count"], 1)
            self.assertEqual(result["counts"]["ht_count"], 1)
            sim = (root / "output.standalone/events.sim").read_bytes()
            self.assertIn(b"Type       SIM\nVersion    101\nGeometry   ", sim)
            self.assertEqual(sim.count(b"SE\n"), 5)
            self.assertEqual(sim.count(b"\nID "), 5)
            self.assertEqual(sim.count(b"IA INIT"), 5)
            self.assertEqual(sim.count(b"HTsim"), 1)
            self.assertEqual(sim.count(b"\nEN\n"), 1)
            index = (root / "output.standalone/index.tsv").read_text(encoding="utf-8")
            self.assertEqual(index.count("\tnative\t"), 4)
            self.assertEqual(index.count("\tminimal_init\t"), 1)
            self.assertTrue((root / "output.standalone/manifest.json").is_file())
            with self.assertRaises(FileExistsError):
                self._materialize(fixture, root / "output")

    def test_rejects_event_id_se_ia_ht_count_and_hash_failures(self) -> None:
        corruptions = (
            "truth_hash", "id", "se", "ia", "ht", "count", "tape_hash", "generated_tape_binary",
            "observation_tape_binary", "observation_generated_binary", "missing_control",
            "provenance_tape_path",
        )
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for corruption in corruptions:
                with self.subTest(corruption=corruption):
                    fixture = build_fixture(root / corruption, corruption=corruption)
                    with self.assertRaises(materializer.ContractError):
                        self._materialize(fixture, root / f"out_{corruption}")

    def test_transaction_failure_leaves_only_quarantined_partial(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            final = root / "transaction.standalone"
            original = materializer._durable_write
            calls = 0

            def fail_second(path: Path, payload: bytes) -> None:
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("fixture disk-full equivalent")
                original(path, payload)

            with mock.patch.object(materializer, "_durable_write", side_effect=fail_second):
                with self.assertRaisesRegex(OSError, "disk-full"):
                    materializer._publish_directory(
                        final,
                        (("events.sim", b"sim"), ("index.tsv", b"index"), ("manifest.json", b"manifest")),
                    )
            self.assertFalse(final.exists())
            partial = root / "transaction.standalone.partial"
            self.assertTrue(partial.is_dir())
            self.assertTrue((partial / "events.sim").is_file())
            self.assertFalse((partial / "manifest.json").exists())
            with self.assertRaises(FileExistsError):
                materializer._publish_directory(
                    final,
                    (("events.sim", b"sim"), ("index.tsv", b"index"), ("manifest.json", b"manifest")),
                )

    def test_transaction_publication_never_replaces_racing_final_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            final = root / "race.standalone"

            def create_racing_final(source: Path, target: Path) -> None:
                self.assertEqual(target, final)
                target.mkdir()
                materializer.rename_no_replace(source, target)

            with mock.patch.object(materializer, "rename_no_replace", side_effect=create_racing_final):
                with self.assertRaises(FileExistsError):
                    materializer._publish_directory(
                        final,
                        (("events.sim", b"sim"), ("index.tsv", b"index"), ("manifest.json", b"manifest")),
                    )
            self.assertTrue(final.is_dir())
            self.assertEqual(list(final.iterdir()), [])
            self.assertTrue((root / "race.standalone.partial/manifest.json").is_file())

    def test_parent_fsync_failure_quarantines_published_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            final = root / "fsync.standalone"
            with mock.patch.object(materializer, "fsync_directory", side_effect=OSError("parent fsync failure")):
                with self.assertRaisesRegex(OSError, "parent fsync failure"):
                    materializer._publish_directory(
                        final,
                        (("events.sim", b"sim"), ("index.tsv", b"index"), ("manifest.json", b"manifest")),
                    )
            self.assertFalse(final.exists())
            quarantines = list(root.glob("fsync.standalone.failed*"))
            self.assertEqual(len(quarantines), 1)
            self.assertTrue((quarantines[0] / "manifest.json").is_file())

    def test_durable_member_failure_retains_diagnostic_partial_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "member.partial"
            with mock.patch.object(materializer.os, "fsync", side_effect=OSError("fixture fsync failure")):
                with self.assertRaisesRegex(OSError, "fsync failure"):
                    materializer._durable_write(path, b"diagnostic bytes")
            self.assertTrue(path.is_file())
            self.assertEqual(path.read_bytes(), b"diagnostic bytes")

    def test_real_mfileeventssim_roundtrip(self) -> None:
        if os.environ.get("M05_MFILE_CONSUMER"):
            consumer = Path(os.environ["M05_MFILE_CONSUMER"])
            build_manifest = None
        else:
            consumer, build_manifest = build_mfileeventssim_roundtrip.build_consumer()
        if os.environ.get("M05_TEST_GEOMETRY"):
            geometry = Path(os.environ["M05_TEST_GEOMETRY"])
        else:
            classification = geometry_classification.build_geometry_classification()
            setup = next(
                row["geometry_setup"] for row in classification["geometries"]
                if row["geometry"] == "mass_model_511"
            )
            geometry = Path(setup)
            if not geometry.is_absolute():
                geometry = PACKAGE.parents[2] / geometry
        self.assertTrue(consumer.is_file())
        self.assertTrue(geometry.is_file())
        if build_manifest is not None:
            self.assertEqual(
                build_manifest["status"],
                "PASS__REAL_MEGALIB_REVAN_CONSUMER_BUILD__NO_TRANSPORT",
            )
            self.assertEqual(build_manifest["transport_events_launched"], 0)
        consumer_environment = os.environ.copy()
        if build_manifest is not None:
            consumer_environment.setdefault("MEGALIB", build_manifest["identity"]["megalib_root"])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = build_fixture(root / "input", geometry=geometry)
            result = self._materialize(fixture, root / "roundtrip")
            completed = subprocess.run(
                [str(consumer), str(geometry), str(root / "roundtrip.standalone/events.sim"),
                 str(root / "roundtrip.standalone/index.tsv")],
                check=False, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=120,
                env=consumer_environment, cwd=root,
            )
            self.assertEqual(completed.returncode, 0, completed.stdout)
            record_line = next(line for line in completed.stdout.splitlines() if line.startswith("M05_ROUNDTRIP_JSON "))
            record = json.loads(record_line.split(" ", 1)[1])
            self.assertEqual(
                record["status"],
                "PASS__REAL_MFILEEVENTSSIM_ROUNDTRIP__REAL_REVAN_INPUT_AND_ANALYZE",
            )
            self.assertEqual(record["event_count"], 5)
            self.assertEqual(record["ia_count"], 5)
            self.assertEqual(record["ht_count"], 1)
            self.assertEqual(record["revan_initial_event_count"], 1)
            self.assertEqual(record["revan_initial_rese_count"], 1)
            self.assertEqual(record["revan_analyze_success_count"], 1)
            self.assertEqual(
                record["event_ia_ht_hash_sha256"],
                result["mfileeventssim_roundtrip"]["expected_event_ia_ht_hash_sha256"],
            )

    @unittest.skipUnless(
        os.environ.get("M05_REVAN_EXECUTABLE") and os.environ.get("M05_TEST_GEOMETRY"),
        "set M05_REVAN_EXECUTABLE and M05_TEST_GEOMETRY for the real Revan gate",
    )
    def test_real_revan_zero_transport_consumer(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = build_fixture(root / "input", geometry=Path(os.environ["M05_TEST_GEOMETRY"]))
            self._materialize(fixture, root / "materialized")
            result = revan_zero_transport_gate.run_gate(
                standalone_manifest=root / "materialized.standalone/manifest.json",
                revan_executable=Path(os.environ["M05_REVAN_EXECUTABLE"]),
                revan_config=materializer.FROZEN_REVAN_CONFIG,
                output_prefix=root / "consumer",
            )
            self.assertEqual(result["status"], revan_zero_transport_gate.PASS_STATUS)
            self.assertEqual(result["counts"]["standalone_event_count"], 5)
            self.assertEqual(result["counts"]["revan_triggered_event_count"], 5)
            self.assertEqual(result["counts"]["tra_reconstructed_event_ids"], [5])
            tra = (root / "consumer.revan/output.tra").read_bytes()
            self.assertIn(b"Type      tra\nVersion   1\nGeometry  ", tra)


if __name__ == "__main__":
    unittest.main()

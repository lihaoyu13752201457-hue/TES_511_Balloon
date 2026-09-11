#!/usr/bin/env python3
"""Zero-transport positive and negative fixtures for the m05cc-v2 gate."""

from __future__ import annotations

import hashlib
import json
import struct
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from typing import Any, Callable


PACKAGE = Path(__file__).resolve().parents[1]
CODE = PACKAGE / "code"
sys.path.insert(0, str(CODE))

import record_validation as rv  # noqa: E402
import geometry_classification  # noqa: E402
from tape_contract import SIDECAR_COLUMNS, _root_payload  # noqa: E402
from preflight_common import canonical_json_bytes  # noqa: E402


CLASSIFICATION_PATH: Path | None = None


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_tsv(path: Path, header: list[str], rows: list[list[Any]]) -> None:
    text = "\t".join(header) + "\n"
    text += "".join("\t".join(str(value) for value in row) + "\n" for row in rows)
    path.write_text(text, encoding="utf-8", newline="")


def _manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_manifest(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")


def _rebind_table(bundle_path: Path, table: str, *, row_count: int | None = None) -> None:
    value = _manifest(bundle_path)
    table_path = bundle_path.parent / value["tables"][table]["path"]
    value["tables"][table]["sha256"] = rv.sha256_file(table_path)
    if row_count is not None:
        value["tables"][table]["row_count"] = row_count
    _write_manifest(bundle_path, value)


def _rebind_blob(bundle_path: Path, blob: str) -> None:
    value = _manifest(bundle_path)
    blob_path = bundle_path.parent / value["blobs"][blob]["path"]
    value["blobs"][blob]["sha256"] = rv.sha256_file(blob_path)
    value["blobs"][blob]["size_bytes"] = blob_path.stat().st_size
    _write_manifest(bundle_path, value)


def _mutate_table(
    bundle_path: Path,
    table: str,
    mutate: Callable[[list[list[str]]], None],
    *,
    row_count: int | None = None,
) -> None:
    value = _manifest(bundle_path)
    table_path = bundle_path.parent / value["tables"][table]["path"]
    rows = [line.split("\t") for line in table_path.read_text(encoding="utf-8").splitlines()]
    mutate(rows)
    table_path.write_text("\n".join("\t".join(row) for row in rows) + "\n", encoding="utf-8")
    _rebind_table(bundle_path, table, row_count=row_count)


def _column(rows: list[list[str]], name: str) -> int:
    return rows[0].index(name)


def build_fixture(root: Path, *, diagnostic_deposits: bool = False, activation: bool = False) -> Path:
    if CLASSIFICATION_PATH is None:
        raise AssertionError("test classification artifact was not initialized")
    root.mkdir(parents=True, exist_ok=True)
    schema = json.loads(rv.SCHEMA_PATH.read_text(encoding="utf-8"))
    headers = {name: value["header"] for name, value in schema["x-tsv-tables"].items()}
    whitelist = json.loads(rv.WHITELIST_PATH.read_text(encoding="utf-8"))
    whitelist_sha = rv.sha256_file(rv.WHITELIST_PATH)
    schema_sha = rv.sha256_file(rv.SCHEMA_PATH)

    roots: list[list[Any]] = []
    observations: list[list[Any]] = []
    stable_roots: list[str] = []
    tape_rows: list[list[Any]] = []
    fixture_source_card_sha = _sha(b"fixture source card")
    fixture_source_contract_sha = _sha(b"fixture source contract")
    fixture_spectrum_sha = _sha(b"fixture spectrum")
    for index in range(3):
        event_id = index + 1
        particle, excitation, source_time = 6, 0.0, event_id * 0.001
        position = (float(index - 1), 0.0, 60.0)
        direction = (0.0, 0.0, -1.0)
        polarization = (0.0, 0.0, 0.0)
        energy = 20.0 + event_id
        binary = rv._binary64_digest(
            particle, excitation, source_time, position, direction, polarization, energy
        )
        quantized = rv._quantized_tuple_digest(
            particle, excitation, source_time, position, direction, polarization, energy
        )
        ia_quantized = rv._ia_init_digest(particle, 0.0, position, direction, polarization, energy)
        raw_line_sha = _sha(f"line-{event_id}".encode())
        raw_binary_sha = binary
        tape_values = {
            "schema": "m05-tape-root-v2", "row_index0": index, "global_row_index0": index,
            "eventlist_id": event_id, "stable_root_id": "", "driver": "Atm_n_bin00_down",
            "driver_assignment": "sampled_exact_not_inferred", "bin_index": 0, "family": "n", "mode": "instant",
            "source_card_path": "fixture.source.source", "source_card_sha256": fixture_source_card_sha,
            "source_contract_path": "fixture.contract.json", "source_contract_sha256": fixture_source_contract_sha,
            "spectrum_path": "fixture.spectrum.dat", "spectrum_sha256": fixture_spectrum_sha,
            "sampler_algorithm": "fixture-independent-v1", "sampler_seed_u64": 12345,
            "sampler_counter_start0": 7 * index, "sampler_counter_end0": 7 * index + 7,
            "particle": particle, "excitation_keV": excitation, "source_time_s": source_time,
            "global_poisson_time_s": source_time, "shard_global_time_offset_s": 0,
            "x_cm": position[0], "y_cm": position[1], "z_cm": position[2],
            "dx": direction[0], "dy": direction[1], "dz": direction[2],
            "px": polarization[0], "py": polarization[1], "pz": polarization[2], "energy_keV": energy,
            "raw_eventlist_line_sha256": raw_line_sha,
            "expected_eventlist_binary64_sha256": raw_binary_sha,
            "expected_generated_binary64_sha256": binary,
            "expected_generated_tuple_sha256": quantized, "control_flag": 1 if event_id == 1 else 0,
        }
        tape_text = {key: str(value) for key, value in tape_values.items()}
        stable = _sha(canonical_json_bytes(_root_payload(
            row=tape_text,
            raw_line_sha256=raw_line_sha,
            eventlist_binary64_sha256=raw_binary_sha,
            generated_binary64_sha256=binary,
            tuple_sha256=quantized,
        )))
        tape_values["stable_root_id"] = stable
        stable_roots.append(stable)
        tape_rows.append([tape_values[name] for name in SIDECAR_COLUMNS])
        roots.append([
            event_id, index, event_id, stable, "Atm_n_bin00_down", "", "unavailable",
            '[]', "n", 1, 1, 1, 1, 0, raw_line_sha,
            quantized, quantized, ia_quantized, 1 if event_id == 1 else 0,
        ])
        observations.append([
            event_id, stable, event_id, raw_binary_sha, particle, "0",
            format(source_time, ".17g"), *(format(value, ".17g") for value in position),
            *(format(value, ".17g") for value in direction), *(format(value, ".17g") for value in polarization),
            format(energy, ".17g"), binary, format(source_time, ".17g"), particle, "0",
            *(format(value, ".17g") for value in position),
            *(format(value, ".17g") for value in direction), *(format(value, ".17g") for value in polarization),
            format(energy, ".17g"), ia_quantized, "1e-06", "1e-09", "1e-09",
            "GENERATED_BINARY64_BE_V1__IA_SERIALIZED_17G_FIELD_TOL_V2",
        ])

    # Event 1 is a forced TES-zero control. Event 2 is TES+active and event 3
    # is veto-only, proving truth selection remains at raw-TES/control grain.
    events = [
        [1, stable_roots[0], "mass_model_511", "0.001", 1, 0, 0, 0, 0, 0, 0, 0, 0, 0,
         "none", 1, 1, 1, 1, 1],
        [2, stable_roots[1], "mass_model_511", "0.002", 1, 1.25, 60, 0, 0, 60, 60, 0, 1, 1,
         "tes+active_veto", 0, 1, 0, 1, 1],
        [3, stable_roots[2], "mass_model_511", "0.003", 1, 0, 5, 0, 0, 5, 5, 0, 0, 0,
         "active_veto", 0, 0, 1, 1, 1],
    ]
    tes_uid = "TP_L0_0:TP_L0_0_Log:0/Instrument:Instrument_Log:0"
    pixels = [[
        2, stable_roots[1], tes_uid, 0, tes_uid, 1.25, 2.2, 3.2, 4.2,
        0.1, 0.3, 0.22, 2, 1, 2, "POST_GLOBAL_V1",
    ]]

    deposits: list[list[Any]] = []
    first_mass = whitelist["mass_csi_physical_volumes"][0]
    if diagnostic_deposits:
        deposits = [
            [2, stable_roots[1], 1, "tes", "TP_L0_0", "TP_L0_0_Log", tes_uid, "HgTe", 0.5,
             1, 2, 3, 1, 2, 3, 0.05, 0.1, 1, 0, 1, "neutron", "", "neutron", "primary", "hadElastic"],
            [2, stable_roots[1], 2, "tes", "TP_L0_0", "TP_L0_0_Log", tes_uid, "HgTe", 0.75,
             3, 4, 5, 3, 4, 5, 0.2, 0.3, 2, 1, 1, "e-", "neutron", "neutron", "ionIoni", "ionIoni"],
            [2, stable_roots[1], 3, "mass_csi", first_mass, "CsI_Log", "CsI:CsI_Log:0", "CsI", 60,
             0, 0, 0, 0, 0, 0, 0.35, 0.4, 3, 1, 1, "gamma", "neutron", "neutron", "nCapture", "compt"],
            [3, stable_roots[2], 1, "mass_csi", first_mass, "CsI_Log", "CsI:CsI_Log:0", "CsI", 5,
             0, 0, 0, 0, 0, 0, 0.1, 0.2, 1, 0, 1, "neutron", "", "neutron", "primary", "hadElastic"],
        ]

    veto_blocks: list[list[Any]] = []
    for event_id, stable in enumerate(stable_roots, start=1):
        for physical in whitelist["mass_csi_physical_volumes"]:
            energy = 60.0 if event_id == 2 and physical == first_mass else (
                5.0 if event_id == 3 and physical == first_mass else 0.0
            )
            count = 1 if energy else 0
            time = 0.4 if event_id == 2 else 0.2
            veto_blocks.append([
                event_id, stable, "mass_model_511", f"mass_csi:{physical}", "mass_csi", physical,
                format(energy, ".17g"), format(time, ".17g") if count else "",
                format(time, ".17g") if count else "", format(time, ".17g") if count else "", count,
                "POST_GLOBAL_V1", whitelist_sha,
            ])

    activation_rows: list[list[Any]] = []
    if activation:
        excitation = 1.5
        activation_rows.append([
            2, stable_roots[1], 2, "Atm_n_bin00_down", "n", 1, 1, 6012, 6, 12, excitation,
            struct.pack(">d", excitation).hex(), "ColdPlate_4K", "ColdPlate_4K", "ColdPlate_4KLog",
            "ColdPlate_4K:ColdPlate_4KLog:0", "Copper", -1.5, 2.5, 3.5, 0.4, 3, 2, 1,
            "C12", "neutron", "neutron", "neutronInelastic", "neutronInelastic", "1:0,2:1,3:2",
        ])

    fragment1 = b"SE\nID 1 1\nIA INIT fixture-control\n"
    fragment2 = b"SE\nID 2 2\nIA INIT fixture-candidate\n"
    truth_blob = fragment1 + fragment2
    truth_path = root / "fixture.truth.sim"
    truth_path.write_bytes(truth_blob)
    truth_index = [
        [1, stable_roots[0], "control", 0, len(fragment1), _sha(fragment1)],
        [2, stable_roots[1], "candidate", len(fragment1), len(fragment2), _sha(fragment2)],
    ]

    native_path = root / "fixture.native.dat"
    native_lines = ["# Cosima universal isotope store", "TT 0.003"]
    if activation_rows:
        native_lines.extend(["VN ColdPlate_4K", "RP 6012 1.50 1.00000e+00"])
    native_lines.append("EN")
    native_path.write_text("\n".join(native_lines) + "\n", encoding="utf-8")
    footer = [[
        "C", "mass_model_511", "instant", "n", "fixture_job", 0, 12345, 3, 3, 3, 3, 3, 3, 3, 3, 3,
        0, len(activation_rows), 0.003, "geometry_specific", whitelist_sha, schema_sha, 1,
    ]]
    table_rows = {
        "roots": roots,
        "generated_observations": observations,
        "events": events,
        "pixels": pixels,
        "deposits": deposits,
        "veto_blocks": veto_blocks,
        "activation": activation_rows,
        "truth_index": truth_index,
        "footer": footer,
    }
    table_bindings: dict[str, dict[str, Any]] = {}
    for name, rows in table_rows.items():
        path = root / f"fixture.{name}.tsv"
        _write_tsv(path, headers[name], rows)
        table_bindings[name] = {"path": path.name, "sha256": rv.sha256_file(path), "row_count": len(rows)}
    tape_root_path = root / "fixture.tape_roots.tsv"
    _write_tsv(tape_root_path, list(SIDECAR_COLUMNS), tape_rows)
    bundle = {
        "schema_version": "m05cc-v2-record-bundle",
        "record_schema_sha256": schema_sha,
        "veto_whitelist_sha256": whitelist_sha,
        "geometry_classification_sha256": rv.sha256_file(CLASSIFICATION_PATH),
        "provenance": {
            "geometry_bundle_sha256": next(
                entry["geometry_bundle_sha256"]
                for entry in json.loads(CLASSIFICATION_PATH.read_text(encoding="utf-8"))["geometries"]
                if entry["geometry"] == "mass_model_511"
            ),
            "tape_root_sidecar_sha256": rv.sha256_file(tape_root_path),
            "tape_root_sidecar_path": "fixture.tape_roots.tsv",
            "source_card_sha256": fixture_source_card_sha,
            "source_contract_sha256": fixture_source_contract_sha,
        },
        "run": {
            "arm": "C", "geometry": "mass_model_511", "mode": "instant", "family": "n",
            "job_id": "fixture_job", "shard_index": 0, "seed": 12345,
            "active_block_coverage": "geometry_specific", "expected_event_count": 3,
        },
        "tables": table_bindings,
        "blobs": {
            "truth_stream": {"path": truth_path.name, "sha256": rv.sha256_file(truth_path), "size_bytes": len(truth_blob)},
            "native_dat": {"path": native_path.name, "sha256": rv.sha256_file(native_path), "size_bytes": native_path.stat().st_size},
        },
    }
    bundle_path = root / "record_bundle.json"
    _write_manifest(bundle_path, bundle)
    return bundle_path


def convert_to_o8(
    bundle_path: Path, *, plastic_event3_keV: float = 49.0, bgo_event3_keV: float = 5.0
) -> None:
    """Convert the zero-step Mass fixture to the six-block O8 contract."""
    value = _manifest(bundle_path)
    if value["tables"]["deposits"]["row_count"] != 0:
        raise AssertionError("O8 conversion expects the production empty-deposits fixture")
    whitelist = json.loads(rv.WHITELIST_PATH.read_text(encoding="utf-8"))
    whitelist_sha = rv.sha256_file(rv.WHITELIST_PATH)

    events_path = bundle_path.parent / value["tables"]["events"]["path"]
    event_rows = [line.split("\t") for line in events_path.read_text(encoding="utf-8").splitlines()]
    header = event_rows[0]
    for index, row in enumerate(event_rows[1:], start=1):
        bgo = 60.0 if index == 2 else bgo_event3_keV if index == 3 else 0.0
        plastic = 10.0 if index == 2 else plastic_event3_keV if index == 3 else 0.0
        replacements = {
            "geometry": "s3d_o8", "mass_csi_keV": "0", "o8_bgo_keV": format(bgo, ".17g"),
            "o8_plastic_keV": format(plastic, ".17g"), "active_shield_keV": format(bgo, ".17g"),
            "active_veto_total_keV": format(bgo + plastic, ".17g"),
            "pass_veto50": "1" if bgo < 50 and plastic < 50 else "0",
            "pass_veto70": "1" if bgo < 70 and plastic < 50 else "0",
            "pass_veto80": "1" if bgo < 80 and plastic < 50 else "0",
        }
        for name, replacement in replacements.items():
            row[header.index(name)] = replacement
    events_path.write_text("\n".join("\t".join(row) for row in event_rows) + "\n", encoding="utf-8")

    roots_path = bundle_path.parent / value["tables"]["roots"]["path"]
    root_rows = [line.split("\t") for line in roots_path.read_text(encoding="utf-8").splitlines()]
    root_header = root_rows[0]
    stable_by_event = {
        int(row[root_header.index("simulation_event_id")]): row[root_header.index("stable_root_id")]
        for row in root_rows[1:]
    }
    veto_header = json.loads(rv.SCHEMA_PATH.read_text(encoding="utf-8"))["x-tsv-tables"]["veto_blocks"]["header"]
    veto_rows: list[list[Any]] = []
    groups = (
        ("o8_bgo", whitelist["o8_bgo_physical_volumes"]),
        ("o8_plastic", whitelist["o8_plastic_physical_volumes"]),
    )
    for event_id in (1, 2, 3):
        for detector_type, volumes in groups:
            for block_index, physical in enumerate(volumes):
                energy = 0.0
                if block_index == 0 and detector_type == "o8_bgo":
                    energy = 60.0 if event_id == 2 else bgo_event3_keV if event_id == 3 else 0.0
                if block_index == 0 and detector_type == "o8_plastic":
                    energy = 10.0 if event_id == 2 else plastic_event3_keV if event_id == 3 else 0.0
                count = int(energy > 0)
                time = 0.4 if event_id == 2 else 0.2
                veto_rows.append([
                    event_id, stable_by_event[event_id], "s3d_o8", f"{detector_type}:{physical}",
                    detector_type, physical, format(energy, ".17g"), format(time, ".17g") if count else "",
                    format(time, ".17g") if count else "", format(time, ".17g") if count else "", count,
                    "POST_GLOBAL_V1", whitelist_sha,
                ])
    veto_path = bundle_path.parent / value["tables"]["veto_blocks"]["path"]
    _write_tsv(veto_path, veto_header, veto_rows)

    footer_path = bundle_path.parent / value["tables"]["footer"]["path"]
    footer_rows = [line.split("\t") for line in footer_path.read_text(encoding="utf-8").splitlines()]
    footer_rows[1][_column(footer_rows, "geometry")] = "s3d_o8"
    footer_path.write_text("\n".join("\t".join(row) for row in footer_rows) + "\n", encoding="utf-8")
    value["run"]["geometry"] = "s3d_o8"
    if CLASSIFICATION_PATH is None:
        raise AssertionError("test classification artifact was not initialized")
    value["provenance"]["geometry_bundle_sha256"] = next(
        entry["geometry_bundle_sha256"]
        for entry in json.loads(CLASSIFICATION_PATH.read_text(encoding="utf-8"))["geometries"]
        if entry["geometry"] == "s3d_o8"
    )
    for table, count in (("events", 3), ("veto_blocks", 18), ("footer", 1)):
        path = bundle_path.parent / value["tables"][table]["path"]
        value["tables"][table]["sha256"] = rv.sha256_file(path)
        value["tables"][table]["row_count"] = count
    _write_manifest(bundle_path, value)


class RecordValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        global CLASSIFICATION_PATH
        cls._classification_temporary = tempfile.TemporaryDirectory()
        CLASSIFICATION_PATH = Path(cls._classification_temporary.name) / "geometry_classification_manifest.json"
        CLASSIFICATION_PATH.write_bytes(canonical_json_bytes(geometry_classification.build_geometry_classification()))

    @classmethod
    def tearDownClass(cls) -> None:
        global CLASSIFICATION_PATH
        CLASSIFICATION_PATH = None
        cls._classification_temporary.cleanup()

    def _assert_fails(self, bundle: Path, pattern: str) -> None:
        with self.assertRaisesRegex(rv.ValidationError, pattern):
            rv.validate_bundle(bundle, geometry_classification_path=CLASSIFICATION_PATH)

    def test_valid_production_bundle_with_empty_diagnostic_deposits(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = rv.validate_bundle(build_fixture(Path(temporary)), geometry_classification_path=CLASSIFICATION_PATH)
        self.assertEqual(result["status"], "PASS__M05CC_V2_PHYSICAL_RECORD_BUNDLE")
        self.assertEqual(result["event_count"], 3)
        self.assertEqual(result["table_row_counts"]["veto_blocks"], 72)
        self.assertEqual(result["table_row_counts"]["deposits"], 0)
        self.assertEqual(result["rp_reconciliation"]["status"], "PASS")
        self.assertEqual(result["rp_reconciliation_authority"], "code/rp_validation.py::reconcile")
        self.assertEqual(result["post_time_semantics"], "POST_GLOBAL_V1")

    def test_dedicated_rp_reconciliation_is_mandatory_and_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = build_fixture(Path(temporary))
            with mock.patch("rp_validation.reconcile", return_value={"status": "FAIL"}):
                self._assert_fails(bundle, "did not return PASS")
            with mock.patch("rp_validation.reconcile", side_effect=ValueError("fixture RP failure")):
                self._assert_fails(bundle, "dedicated RP/native-DAT reconciliation failed")

    def test_valid_diagnostic_steps_and_activation_edge_chain(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = rv.validate_bundle(
                build_fixture(Path(temporary), diagnostic_deposits=True, activation=True),
                geometry_classification_path=CLASSIFICATION_PATH,
            )
        self.assertEqual(result["table_row_counts"]["deposits"], 4)
        self.assertEqual(result["table_row_counts"]["activation"], 1)

    def test_native_dat_aggregate_and_tt_reconciliation_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = build_fixture(Path(temporary), activation=True)
            value = _manifest(bundle)
            dat = bundle.parent / value["blobs"]["native_dat"]["path"]
            dat.write_text(dat.read_text(encoding="utf-8").replace("1.00000e+00", "2.00000e+00"), encoding="utf-8")
            _rebind_blob(bundle, "native_dat")
            self._assert_fails(bundle, "aggregate RP mismatch")
        with tempfile.TemporaryDirectory() as temporary:
            bundle = build_fixture(Path(temporary))
            value = _manifest(bundle)
            dat = bundle.parent / value["blobs"]["native_dat"]["path"]
            dat.write_text(dat.read_text(encoding="utf-8").replace("TT 0.003", "TT 0"), encoding="utf-8")
            _rebind_blob(bundle, "native_dat")
            self._assert_fails(bundle, "TT must be positive")

    def test_geometry_and_provenance_hash_binding_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = build_fixture(Path(temporary))
            value = _manifest(bundle)
            value["provenance"]["geometry_bundle_sha256"] = "f" * 64
            _write_manifest(bundle, value)
            self._assert_fails(bundle, "geometry bundle differs")

    def test_transaction_bound_tape_exact_driver_and_generated_hash_join(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = build_fixture(Path(temporary))
            def alter_driver(rows: list[list[str]]) -> None:
                rows[1][_column(rows, "benchmark_driver_id")] = "Atm_n_bin01_down"
            _mutate_table(bundle, "roots", alter_driver)
            self._assert_fails(bundle, "benchmark_driver_id mismatch")

        with tempfile.TemporaryDirectory() as temporary:
            bundle = build_fixture(Path(temporary))
            value = _manifest(bundle)
            tape_path = bundle.parent / value["provenance"]["tape_root_sidecar_path"]
            tape_rows = [line.split("\t") for line in tape_path.read_text(encoding="utf-8").splitlines()]
            tape_rows[1][_column(tape_rows, "expected_generated_binary64_sha256")] = "f" * 64
            tape_path.write_text("\n".join("\t".join(row) for row in tape_rows) + "\n", encoding="utf-8")
            value["provenance"]["tape_root_sidecar_sha256"] = rv.sha256_file(tape_path)
            _write_manifest(bundle, value)
            self._assert_fails(bundle, "generated binary64 digest mismatch")

    def test_o8_six_block_contract_and_strict_plastic_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = build_fixture(Path(temporary))
            convert_to_o8(bundle, plastic_event3_keV=50.0)
            result = rv.validate_bundle(bundle, geometry_classification_path=CLASSIFICATION_PATH)
            self.assertEqual(result["geometry"], "s3d_o8")
            self.assertEqual(result["table_row_counts"]["veto_blocks"], 18)
            # Plastic equality at 50 vetoes every O8 threshold.
            events = (bundle.parent / _manifest(bundle)["tables"]["events"]["path"]).read_text(encoding="utf-8")
            event_rows = [line.split("\t") for line in events.splitlines()]
            self.assertEqual(event_rows[3][_column(event_rows, "pass_veto50")], "0")
            self.assertEqual(event_rows[3][_column(event_rows, "pass_veto70")], "0")
            self.assertEqual(event_rows[3][_column(event_rows, "pass_veto80")], "0")
            # BGO 60/plastic 10: fail50, pass70 and pass80.
            self.assertEqual(event_rows[2][_column(event_rows, "pass_veto50")], "0")
            self.assertEqual(event_rows[2][_column(event_rows, "pass_veto70")], "1")
            self.assertEqual(event_rows[2][_column(event_rows, "pass_veto80")], "1")

    def test_o8_bgo30_plus_plastic30_uses_separate_F_observables(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = build_fixture(Path(temporary))
            convert_to_o8(bundle, bgo_event3_keV=30.0, plastic_event3_keV=30.0)
            result = rv.validate_bundle(bundle, geometry_classification_path=CLASSIFICATION_PATH)
            self.assertEqual(result["status"], "PASS__M05CC_V2_PHYSICAL_RECORD_BUNDLE")
            events = (bundle.parent / _manifest(bundle)["tables"]["events"]["path"]).read_text(encoding="utf-8")
            rows = [line.split("\t") for line in events.splitlines()]
            self.assertEqual(rows[3][_column(rows, "active_veto_total_keV")], "60")
            self.assertEqual(rows[3][_column(rows, "pass_veto50")], "1")
            self.assertEqual(rows[3][_column(rows, "pass_veto70")], "1")
            self.assertEqual(rows[3][_column(rows, "pass_veto80")], "1")

    def test_ia_field_specific_serialization_tolerances(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = build_fixture(Path(temporary))
            def allowed_position_and_energy(rows: list[list[str]]) -> None:
                rows[1][_column(rows, "serialized_ia_x_cm")] = "-0.9999996"
                rows[1][_column(rows, "serialized_ia_energy_keV")] = "21.0000004"
            _mutate_table(bundle, "generated_observations", allowed_position_and_energy)
            rv.validate_bundle(bundle, geometry_classification_path=CLASSIFICATION_PATH)

        with tempfile.TemporaryDirectory() as temporary:
            bundle = build_fixture(Path(temporary))
            def forbidden_direction(rows: list[list[str]]) -> None:
                rows[1][_column(rows, "serialized_ia_dx")] = "5e-07"
            _mutate_table(bundle, "generated_observations", forbidden_direction)
            self._assert_fails(bundle, "IA/generated dx outside serialized tolerance")

    def test_cross_geometry_blocks_are_rejected_even_when_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = build_fixture(Path(temporary))
            whitelist = json.loads(rv.WHITELIST_PATH.read_text(encoding="utf-8"))
            value = _manifest(bundle)
            def add_cross_geometry_zero(rows: list[list[str]]) -> None:
                physical = whitelist["o8_bgo_physical_volumes"][0]
                rows.append([
                    "1", rows[1][_column(rows, "stable_root_id")], "mass_model_511",
                    f"o8_bgo:{physical}", "o8_bgo", physical, "0", "", "", "", "0",
                    "POST_GLOBAL_V1", value["veto_whitelist_sha256"],
                ])
            _mutate_table(bundle, "veto_blocks", add_cross_geometry_zero, row_count=73)
            self._assert_fails(bundle, "unexpected block")

    def test_exact_header_and_additional_properties_equivalent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = build_fixture(root)
            _mutate_table(bundle, "events", lambda rows: rows[0].append("unexpected"))
            self._assert_fails(bundle, "exact header mismatch")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            bundle = build_fixture(root)
            value = _manifest(bundle)
            value["unexpected"] = True
            _write_manifest(bundle, value)
            self._assert_fails(bundle, "exact properties mismatch")

    def test_malformed_scalar_type_nan_and_inf(self) -> None:
        cases = (("generated_flag", "true", "expected 0 or 1"), ("source_time_s", "NaN", "finite float"),
                 ("source_time_s", "Inf", "finite float"))
        for column, replacement, pattern in cases:
            with self.subTest(column=column, replacement=replacement), tempfile.TemporaryDirectory() as temporary:
                bundle = build_fixture(Path(temporary))
                table = "roots" if column == "generated_flag" else "events"
                def mutate(rows: list[list[str]], name: str = column, value: str = replacement) -> None:
                    rows[1][_column(rows, name)] = value
                _mutate_table(bundle, table, mutate)
                self._assert_fails(bundle, pattern)

    def test_scalar_range_and_enum_are_rejected(self) -> None:
        cases = (
            ("events", "geometry", "not_a_geometry", "invalid enum"),
            ("pixels", "layer", "6", "integer outside range"),
        )
        for table, column, replacement, pattern in cases:
            with self.subTest(table=table, column=column), tempfile.TemporaryDirectory() as temporary:
                bundle = build_fixture(Path(temporary))
                def mutate(rows: list[list[str]], name: str = column, value: str = replacement) -> None:
                    rows[1][_column(rows, name)] = value
                _mutate_table(bundle, table, mutate)
                self._assert_fails(bundle, pattern)

    def test_duplicate_exact_row_and_duplicate_composite_key(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = build_fixture(Path(temporary))
            def duplicate(rows: list[list[str]]) -> None:
                rows.append(list(rows[1]))
            _mutate_table(bundle, "roots", duplicate, row_count=4)
            self._assert_fails(bundle, "duplicate exact row")
        with tempfile.TemporaryDirectory() as temporary:
            bundle = build_fixture(Path(temporary))
            def duplicate_key(rows: list[list[str]]) -> None:
                duplicate = list(rows[1])
                duplicate[_column(rows, "sum_energy_keV")] = "2.5"
                rows.append(duplicate)
            _mutate_table(bundle, "pixels", duplicate_key, row_count=2)
            self._assert_fails(bundle, "duplicate key")

    def test_missing_active_block_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = build_fixture(Path(temporary))
            _mutate_table(bundle, "veto_blocks", lambda rows: rows.pop(), row_count=71)
            self._assert_fails(bundle, "incomplete event")

    def test_broken_foreign_key_join_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = build_fixture(Path(temporary))
            def break_join(rows: list[list[str]]) -> None:
                rows[1][_column(rows, "stable_root_id")] = "f" * 64
            _mutate_table(bundle, "pixels", break_join)
            self._assert_fails(bundle, "stable_root_id join mismatch")

    def test_altered_bound_file_and_fragment_hashes_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = build_fixture(Path(temporary))
            value = _manifest(bundle)
            events_path = bundle.parent / value["tables"]["events"]["path"]
            events_path.write_bytes(events_path.read_bytes() + b"\n")
            self._assert_fails(bundle, "altered file hash")
        with tempfile.TemporaryDirectory() as temporary:
            bundle = build_fixture(Path(temporary))
            def alter_fragment_hash(rows: list[list[str]]) -> None:
                rows[1][_column(rows, "sha256")] = "f" * 64
            _mutate_table(bundle, "truth_index", alter_fragment_hash)
            self._assert_fails(bundle, "altered fragment hash")

    def test_block_sums_veto_boundaries_and_whitelist_hash(self) -> None:
        cases = (
            ("events", "pass_veto50", "1", "pass_veto50 mismatch"),
            ("events", "mass_csi_keV", "59", "mass_csi block sum"),
            ("veto_blocks", "veto_whitelist_sha256", "f" * 64, "altered whitelist hash"),
        )
        for table, column, replacement, pattern in cases:
            with self.subTest(table=table, column=column), tempfile.TemporaryDirectory() as temporary:
                bundle = build_fixture(Path(temporary))
                def mutate(rows: list[list[str]], value: str = replacement, name: str = column) -> None:
                    target = 2 if table == "events" else 1
                    rows[target][_column(rows, name)] = value
                _mutate_table(bundle, table, mutate)
                self._assert_fails(bundle, pattern)

    def test_post_time_is_recomputed_only_from_post_step_time(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = build_fixture(Path(temporary), diagnostic_deposits=True)
            # 0.16 is the PRE-time energy-weighted value; valid POST value is 0.22.
            def use_pre_time(rows: list[list[str]]) -> None:
                rows[1][_column(rows, "post_time_energy_weighted_s")] = "0.16"
            _mutate_table(bundle, "pixels", use_pre_time)
            self._assert_fails(bundle, "POST weighted time")

    def test_generated_observation_hash_and_activation_edge_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bundle = build_fixture(Path(temporary))
            def alter_generated(rows: list[list[str]]) -> None:
                rows[1][_column(rows, "observed_generated_binary64_sha256")] = "f" * 64
            _mutate_table(bundle, "generated_observations", alter_generated)
            self._assert_fails(bundle, "generated binary64 digest mismatch")
        with tempfile.TemporaryDirectory() as temporary:
            bundle = build_fixture(Path(temporary))
            def alter_event_time(rows: list[list[str]]) -> None:
                # This is within the general float tolerance but the two clocks
                # are required to be numerically identical.
                rows[1][_column(rows, "native_event_time_s")] = "0.0010001"
            _mutate_table(bundle, "generated_observations", alter_event_time)
            self._assert_fails(bundle, "native event time differs")
        with tempfile.TemporaryDirectory() as temporary:
            bundle = build_fixture(Path(temporary))
            def alter_ia_time(rows: list[list[str]]) -> None:
                rows[1][_column(rows, "serialized_ia_time_s")] = "0.001"
            _mutate_table(bundle, "generated_observations", alter_ia_time)
            self._assert_fails(bundle, "expected constant '0'")
        with tempfile.TemporaryDirectory() as temporary:
            bundle = build_fixture(Path(temporary))
            def use_source_time_for_ia_hash(rows: list[list[str]]) -> None:
                particle = int(rows[1][_column(rows, "serialized_ia_particle")])
                position = tuple(float(rows[1][_column(rows, f"serialized_ia_{axis}_cm")]) for axis in "xyz")
                direction = tuple(float(rows[1][_column(rows, f"serialized_ia_d{axis}")]) for axis in "xyz")
                polarization = tuple(float(rows[1][_column(rows, f"serialized_ia_p{axis}")]) for axis in "xyz")
                energy = float(rows[1][_column(rows, "serialized_ia_energy_keV")])
                source_time = float(rows[1][_column(rows, "observed_generated_source_time_s")])
                rows[1][_column(rows, "serialized_ia_quantized_sha256")] = rv._ia_init_digest(
                    particle, source_time, position, direction, polarization, energy
                )
            _mutate_table(bundle, "generated_observations", use_source_time_for_ia_hash)
            self._assert_fails(bundle, "serialized IA quantized digest mismatch")
        with tempfile.TemporaryDirectory() as temporary:
            bundle = build_fixture(Path(temporary), activation=True)
            def break_edge(rows: list[list[str]]) -> None:
                rows[1][_column(rows, "ancestry_chain")] = "1:0,3:2"
            _mutate_table(bundle, "activation", break_edge)
            self._assert_fails(bundle, "do not form one root-to-leaf chain")


if __name__ == "__main__":
    unittest.main()

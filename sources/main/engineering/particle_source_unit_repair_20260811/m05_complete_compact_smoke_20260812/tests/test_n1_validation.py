#!/usr/bin/env python3
"""Zero-transport positive and hostile fixtures for the N1 commit contract."""

from __future__ import annotations

import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any


PACKAGE = Path(__file__).resolve().parents[1]
CODE = PACKAGE / "code"
TESTS = PACKAGE / "tests"
sys.path.insert(0, str(CODE))
sys.path.insert(0, str(TESTS))

import build_preflight  # noqa: E402
import geometry_classification  # noqa: E402
import materialize_standalone_sim  # noqa: E402
import n1_validation  # noqa: E402
import preflight_common as common  # noqa: E402
import record_validation  # noqa: E402
import tape_contract  # noqa: E402
from test_standalone_materializer import build_fixture  # noqa: E402


def _write_canonical(path: Path, value: dict[str, Any]) -> None:
    path.write_bytes(common.canonical_json_bytes(value))


def _binding(path: Path, row_count: int | None = None) -> dict[str, Any]:
    value: dict[str, Any] = {
        "path": path.name,
        "sha256": common.sha256(path),
        "size_bytes": path.stat().st_size,
    }
    if row_count is not None:
        value["row_count"] = row_count
    return value


def build_n1_fixture(root: Path) -> dict[str, Path]:
    classification_value = geometry_classification.build_geometry_classification()
    mass = next(row for row in classification_value["geometries"] if row["geometry"] == "mass_model_511")
    geometry_setup = common.repo_path(mass["geometry_setup"])
    c_fixture = build_fixture(root / "c_fixture", geometry=geometry_setup)
    c_bundle = json.loads(c_fixture["bundle"].read_text(encoding="utf-8"))
    n1_root = root / "fixture_job.m05cc"
    n1_root.mkdir()

    table_counts: dict[str, int] = {}
    for name in ("roots", "generated_observations", "footer"):
        source = c_fixture["bundle"].parent / c_bundle["tables"][name]["path"]
        target = n1_root / f"{name}.tsv"
        payload = source.read_bytes()
        if name == "footer":
            lines = payload.decode("utf-8").splitlines()
            header = lines[0].split("\t")
            fields = lines[1].split("\t")
            fields[header.index("arm")] = "N1"
            fields[header.index("record_schema_sha256")] = common.sha256(n1_validation.SCHEMA_PATH)
            payload = ("\t".join(header) + "\n" + "\t".join(fields) + "\n").encode("utf-8")
        target.write_bytes(payload)
        table_counts[name] = c_bundle["tables"][name]["row_count"]

    tape_roots = n1_root / "tape_roots.tsv"
    tape_roots.write_bytes(c_fixture["tape_roots"].read_bytes())
    native_dat = n1_root / "native.inc0.dat"
    native_dat.write_bytes((c_fixture["bundle"].parent / c_bundle["blobs"]["native_dat"]["path"]).read_bytes())
    classification = root / "geometry_classification_manifest.json"
    _write_canonical(classification, classification_value)

    with tape_roots.open("r", encoding="utf-8", newline="") as handle:
        tape_first = next(csv.DictReader(handle, delimiter="\t"))
    event_count = table_counts["roots"]
    job_id = "fixture_job"
    run_name = "M05_n_instant_s0_N1"
    source_card = root / "fixture_job.source"
    source_card.write_text(
        "\n".join([
            "# NON_MERGEABLE_BENCHMARK: isolated matched M05 compact smoke",
            "# Frozen EventList is the only source input; no spectrum/beam/flux source is permitted.",
            f"# canonical_geometry_bundle_sha256={mass['geometry_bundle_sha256']}",
            f"# corrected_source_contract_sha256={tape_first['source_contract_sha256']}",
            f"Geometry {geometry_setup}",
            "PhysicsListHD qgsp-bic-hp",
            "PhysicsListEM LivermorePol",
            "StoreSimulationInfo all",
            "StoreIsotopes true",
            "DetectorTimeConstant 1e-9",
            "StoreTextScientific true 17",
            "PreTriggerMode Everything",
            "",
            f"Run {run_name}",
            f"{run_name}.Events {event_count}",
            f"{run_name}.IsotopeProductionFile {n1_root}.partial/native",
            f"{run_name}.Source FrozenPrimary",
            f"FrozenPrimary.EventList {c_fixture['tape'].resolve()}",
            "",
        ]),
        encoding="utf-8",
    )
    commit = {
        "arm": "N1",
        "corrected_source_card_sha256": tape_first["source_card_sha256"],
        "footer": _binding(n1_root / "footer.tsv", table_counts["footer"]),
        "generated_observations": _binding(
            n1_root / "generated_observations.tsv", table_counts["generated_observations"]
        ),
        "geometry_bundle_sha256": mass["geometry_bundle_sha256"],
        "geometry_classification_sha256": common.sha256(classification),
        "n1_commit_schema_sha256": common.sha256(n1_validation.SCHEMA_PATH),
        "native_added_isotope_count": 0,
        "native_dat": _binding(native_dat),
        "roots": _binding(n1_root / "roots.tsv", table_counts["roots"]),
        "run": {
            "arm": "N1", "expected_event_count": event_count, "family": "n",
            "geometry": "mass_model_511", "job_id": job_id, "mode": "instant",
            "seed": 12345, "shard_index": 0,
        },
        "runtime_source_card_sha256": common.sha256(source_card),
        "schema_version": "m05cc-n1-v1-commit",
        "source_contract_sha256": tape_first["source_contract_sha256"],
        "status": "PASS__N1_TRANSACTION_COMPLETE",
        "tape_root_sidecar": _binding(tape_roots, event_count),
        "veto_whitelist_sha256": common.sha256(n1_validation.WHITELIST_PATH),
    }
    commit_path = n1_root / "commit.json"
    _write_canonical(commit_path, commit)
    return {
        "commit": commit_path,
        "eventlist": c_fixture["tape"],
        "source_card": source_card,
        "classification": classification,
        "c_bundle": c_fixture["bundle"],
    }


def _validate(fixture: dict[str, Path]) -> dict[str, Any]:
    return n1_validation.validate_n1_commit(
        fixture["commit"],
        eventlist_path=fixture["eventlist"],
        runtime_source_card_path=fixture["source_card"],
        geometry_classification_path=fixture["classification"],
        verify_external_authorities=False,
    )


class N1ValidatorTests(unittest.TestCase):
    def test_positive_n1_commit_is_strict_and_not_materializer_eligible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = build_n1_fixture(Path(directory))
            result = _validate(fixture)
            self.assertEqual(result["status"], "PASS__M05CC_N1_V1_COMMIT")
            self.assertEqual(result["root_count"], 5)
            self.assertEqual(result["generated_observation_count"], 5)
            self.assertFalse(result["materializer_eligible"])
            self.assertEqual(result["native_dat_evidence_grain"], "AGGREGATE_ONLY__NO_N1_RP_SIDECAR_OR_LINEAGE_CLAIM")

    def test_c_and_n1_commits_are_not_interchangeable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = build_n1_fixture(Path(directory))
            with self.assertRaises(n1_validation.N1ValidationError):
                n1_validation.validate_n1_commit(
                    fixture["c_bundle"],
                    eventlist_path=fixture["eventlist"],
                    runtime_source_card_path=fixture["source_card"],
                    geometry_classification_path=fixture["classification"],
                    verify_external_authorities=False,
                )
            with self.assertRaises(record_validation.ValidationError):
                record_validation.validate_bundle(
                    fixture["commit"], geometry_classification_path=fixture["classification"]
                )
            with self.assertRaises(materialize_standalone_sim.ContractError):
                materialize_standalone_sim.materialize(
                    record_bundle=fixture["commit"],
                    tape_path=fixture["eventlist"],
                    tape_roots_path=fixture["commit"].parent / "tape_roots.tsv",
                    geometry_path=Path("/dev/null"), geometry_sha256="0" * 64,
                    geometry_classification_path=fixture["classification"],
                    output_prefix=Path(directory) / "must_not_publish",
                    _verify_tape_authorities=False,
                )

    def test_hash_refresh_cannot_hide_root_tape_join_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = build_n1_fixture(Path(directory))
            roots = fixture["commit"].parent / "roots.tsv"
            lines = roots.read_text(encoding="utf-8").splitlines()
            header = lines[0].split("\t")
            fields = lines[1].split("\t")
            fields[header.index("benchmark_driver_id")] = "invented_driver"
            roots.write_text("\t".join(header) + "\n" + "\t".join(fields) + "\n" + "\n".join(lines[2:]) + "\n")
            commit = json.loads(fixture["commit"].read_text(encoding="utf-8"))
            commit["roots"] = _binding(roots, commit["roots"]["row_count"])
            _write_canonical(fixture["commit"], commit)
            with self.assertRaisesRegex(n1_validation.N1ValidationError, "sampled driver"):
                _validate(fixture)

    def test_hash_refresh_cannot_hide_observation_identity_or_mode_corruption(self) -> None:
        for column, replacement, message in (
            ("stable_root_id", "f" * 64, "observation stable root"),
            ("eventlist_id", "99", "observation EventList ID"),
        ):
            with self.subTest(column=column), tempfile.TemporaryDirectory() as directory:
                fixture = build_n1_fixture(Path(directory))
                observations = fixture["commit"].parent / "generated_observations.tsv"
                lines = observations.read_text(encoding="utf-8").splitlines()
                header = lines[0].split("\t")
                fields = lines[1].split("\t")
                fields[header.index(column)] = replacement
                observations.write_text(
                    "\t".join(header) + "\n" + "\t".join(fields) + "\n" + "\n".join(lines[2:]) + "\n",
                    encoding="utf-8",
                )
                commit = json.loads(fixture["commit"].read_text(encoding="utf-8"))
                commit["generated_observations"] = _binding(
                    observations, commit["generated_observations"]["row_count"]
                )
                _write_canonical(fixture["commit"], commit)
                with self.assertRaisesRegex(n1_validation.N1ValidationError, message):
                    _validate(fixture)

        with tempfile.TemporaryDirectory() as directory:
            fixture = build_n1_fixture(Path(directory))
            tape_roots = fixture["commit"].parent / "tape_roots.tsv"
            lines = tape_roots.read_text(encoding="utf-8").splitlines()
            header = lines[0].split("\t")
            fields = lines[1].split("\t")
            fields[header.index("mode")] = "buildup"
            tape_roots.write_text(
                "\t".join(header) + "\n" + "\t".join(fields) + "\n" + "\n".join(lines[2:]) + "\n",
                encoding="utf-8",
            )
            commit = json.loads(fixture["commit"].read_text(encoding="utf-8"))
            commit["tape_root_sidecar"] = _binding(tape_roots, commit["tape_root_sidecar"]["row_count"])
            _write_canonical(fixture["commit"], commit)
            with self.assertRaisesRegex(n1_validation.N1ValidationError, "mode differs from commit.run"):
                _validate(fixture)

    def test_runtime_source_card_uses_exact_absolute_setup_for_both_geometries(self) -> None:
        geometries = build_preflight.load_geometry_bundles()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tape = root / "fixture.eventlist"
            tape.write_text("fixture\n", encoding="utf-8")
            for geometry_name, geometry in geometries.items():
                with self.subTest(geometry=geometry_name):
                    output = root / f"{geometry_name}.sim"
                    card = root / f"{geometry_name}.source"
                    text = build_preflight._source_card_text(
                        geometry=geometry, family="n", mode="instant", shard_index=0,
                        events=5, seed=12345, arm="N1", tape_absolute=tape.resolve(),
                        output_prefix=output,
                    )
                    card.write_text(text, encoding="utf-8")
                    commit = {
                        "runtime_source_card_sha256": common.sha256(card),
                        "geometry_bundle_sha256": geometry["bundle_sha256"],
                        "source_contract_sha256": tape_contract.SOURCE_CONTRACT_SHA256,
                        "run": {"expected_event_count": 5, "mode": "instant"},
                    }
                    native_base = str(output.with_name(output.name + ".m05cc.partial") / "native")
                    n1_validation._validate_runtime_source_card(
                        card, commit, tape, geometry["setup_absolute_path"], native_base,
                    )
                    for wrong in (geometry["setup_path"], str(root / "wrong.geo.setup")):
                        altered = root / f"{geometry_name}.{Path(wrong).name}.source"
                        altered.write_text(
                            text.replace(
                                f"Geometry {geometry['setup_absolute_path']}", f"Geometry {wrong}", 1
                            ),
                            encoding="utf-8",
                        )
                        altered_commit = dict(commit)
                        altered_commit["runtime_source_card_sha256"] = common.sha256(altered)
                        with self.assertRaisesRegex(
                            n1_validation.N1ValidationError, "geometry/physics/event/tape/native"
                        ):
                            n1_validation._validate_runtime_source_card(
                                altered, altered_commit, tape, geometry["setup_absolute_path"], native_base,
                            )

    def test_extra_member_duplicate_json_and_wrong_footer_schema_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            fixture = build_n1_fixture(Path(directory))
            extra = fixture["commit"].parent / "record_bundle.json"
            extra.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(n1_validation.N1ValidationError, "exact member closure"):
                _validate(fixture)

        with tempfile.TemporaryDirectory() as directory:
            fixture = build_n1_fixture(Path(directory))
            payload = fixture["commit"].read_text(encoding="utf-8")
            fixture["commit"].write_text(
                payload.replace('{"arm":"N1",', '{"arm":"N1","arm":"N1",', 1), encoding="utf-8"
            )
            with self.assertRaisesRegex(n1_validation.N1ValidationError, "duplicate JSON key"):
                _validate(fixture)

        with tempfile.TemporaryDirectory() as directory:
            fixture = build_n1_fixture(Path(directory))
            footer = fixture["commit"].parent / "footer.tsv"
            lines = footer.read_text(encoding="utf-8").splitlines()
            header = lines[0].split("\t")
            fields = lines[1].split("\t")
            fields[header.index("record_schema_sha256")] = common.sha256(
                PACKAGE / "schema/m05cc_v2.record_schema.json"
            )
            footer.write_text("\t".join(header) + "\n" + "\t".join(fields) + "\n", encoding="utf-8")
            commit = json.loads(fixture["commit"].read_text(encoding="utf-8"))
            commit["footer"] = _binding(footer, 1)
            _write_canonical(fixture["commit"], commit)
            with self.assertRaises(n1_validation.N1ValidationError):
                _validate(fixture)


class N1PlannedBindingTests(unittest.TestCase):
    def test_all_112_c_and_112_n1_jobs_bind_disjoint_commits_and_validators(self) -> None:
        with tempfile.TemporaryDirectory(dir=PACKAGE) as directory:
            root = Path(directory)
            stage = root / "stage"
            final = root / "final"
            stage.mkdir()
            cells: list[dict[str, Any]] = []
            seeds: list[dict[str, Any]] = []
            seed = 100_000_000
            for family, mode in tape_contract.CELL_COUNTS:
                shards: list[dict[str, Any]] = []
                for shard_index, event_count in enumerate(tape_contract.CELL_COUNTS[(family, mode)]):
                    tape_final = final / "tapes" / f"{family}_{mode}" / f"shard{shard_index:04d}.eventlist"
                    sidecar_final = final / "tapes" / f"{family}_{mode}" / f"shard{shard_index:04d}.roots.tsv"
                    tape_stage = stage / tape_final.relative_to(final)
                    tape_stage.parent.mkdir(parents=True, exist_ok=True)
                    tape_stage.write_text("fixture\n", encoding="utf-8")
                    shards.append({
                        "shard_index": shard_index, "event_count": event_count,
                        "tape_path": common.rel(tape_final), "tape_sha256": "1" * 64,
                        "root_sidecar_path": common.rel(sidecar_final), "root_sidecar_sha256": "2" * 64,
                    })
                    seeds.append({"family": family, "mode": mode, "shard_index": shard_index, "seed": seed})
                    seed += 1
                cells.append({
                    "family": family, "mode": mode, "source_card_sha256": "3" * 64, "shards": shards,
                })
            geometries = {
                name: {"bundle_sha256": digit * 64, "setup_absolute_path": f"/frozen/{name}.geo.setup"}
                for name, digit in (("mass_model_511", "4"), ("s3d_o8", "5"))
            }
            production = {"binary_path": "/frozen/cosima", "binary_sha256": "6" * 64}
            shadow = {"binary_path": "/frozen/m05cosima", "binary_sha256": "7" * 64}
            observer = {
                "binary_path": "/frozen/libobserver.so", "binary_sha256": "8" * 64,
                "manifest_path": "observer/manifest.json", "manifest_sha256": "9" * 64,
                "schema_path": "observer/schema.json", "schema_sha256": "a" * 64,
                "validator_path": "observer/validator.py", "validator_sha256": "b" * 64,
                "validator_python_path": "/usr/bin/python3", "validator_python_sha256": "c" * 64,
            }
            jobs, blocked, cards = build_preflight.build_cards_and_jobs(
                stage, final, {"cells": cells}, seeds, geometries, production, shadow, observer, "d" * 64
            )
            self.assertEqual((len(jobs), len(blocked), len(cards)), (448, 112, 448))
            c_jobs = [job for job in jobs if job["arm"] == "C"]
            n1_jobs = [job for job in jobs if job["arm"] == "N1"]
            self.assertEqual((len(c_jobs), len(n1_jobs)), (112, 112))
            for job in c_jobs:
                binding = job["generated_observer_binding"]
                self.assertTrue(binding["planned_commit_path"].endswith(".m05cc/record_bundle.json"))
                self.assertEqual(binding["commit_contract"], "m05cc-v2-record-bundle__C_ONLY")
                self.assertEqual(binding["record_schema_sha256"], common.sha256(build_preflight.RECORD_SCHEMA))
                self.assertEqual(binding["validator_sha256"], common.sha256(build_preflight.RECORD_VALIDATOR))
                self.assertNotIn("m05cc_n1", " ".join(binding["validation_argv"]))
            for job in n1_jobs:
                binding = job["generated_observer_binding"]
                self.assertTrue(binding["planned_commit_path"].endswith(".m05cc/commit.json"))
                self.assertEqual(binding["commit_contract"], "m05cc-n1-v1-commit__N1_ONLY__NOT_MATERIALIZER_INPUT")
                self.assertEqual(binding["record_schema_sha256"], common.sha256(build_preflight.N1_COMMIT_SCHEMA))
                self.assertEqual(binding["validator_sha256"], common.sha256(build_preflight.N1_COMMIT_VALIDATOR))
                self.assertIn("n1_validation.py", " ".join(binding["validation_argv"]))
                self.assertFalse(binding["planned_commit_path"].endswith("record_bundle.json"))


if __name__ == "__main__":
    unittest.main()

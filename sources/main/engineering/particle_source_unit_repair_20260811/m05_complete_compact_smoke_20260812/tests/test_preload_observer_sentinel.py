from __future__ import annotations

import contextlib
import csv
import io
import json
import os
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / "code"))

import run_preload_observer_sentinel as sentinel
from preflight_common import canonical_json_bytes, sha256_bytes
from tape_contract import SIDECAR_COLUMNS


def _digest(label: str) -> str:
    return sha256_bytes(label.encode("utf-8"))


def _pair_matrix() -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for geometry in sentinel.GEOMETRIES:
        for family in sentinel.FAMILIES:
            for mode in sentinel.MODES:
                for shard in sentinel.SHARDS:
                    result.append({
                        "geometry": geometry,
                        "family": family,
                        "mode": mode,
                        "shard_index": shard,
                        "events_per_arm": 3,
                        "arm_order": ["baseline", "preload"] if shard % 2 == 0 else ["preload", "baseline"],
                    })
    return result


def _authorization_envelope(output: Path) -> dict[str, object]:
    digest = "a" * 64
    plan = {
        "output_root": str(output),
        "authority_bindings": {
            "installed_cosima": {"sha256": digest},
            "harness": {"sha256": digest},
            "mfile_consumer_binary": {"sha256": digest},
            "observer_binary": {"sha256": digest},
            "observer_build_manifest": {"sha256": digest},
            "planned_job_manifest": {"sha256": digest},
            "tape_provenance_manifest": {"sha256": digest},
        },
    }
    return {"plan": plan, "plan_sha256": "b" * 64}


def _minimal_input_envelope(root: Path) -> tuple[dict[str, object], Path, Path, bytes, bytes]:
    target = root / "candidate.inputs"
    partial = target.with_name(f".{target.name}.partial.inputs.{os.getpid()}")
    geometry = root / "geometry.geo.setup"
    geometry.write_text("Name fixture\n", encoding="utf-8")
    tape = b"1 0 1 0 0 0 0 60 0 0 -1 0 0 0 511\n"
    sidecar = ("\t".join(SIDECAR_COLUMNS) + "\n").encode()
    card = sentinel._source_card_bytes(
        geometry=geometry, mode="instant", tape=target / "tapes/x.eventlist",
    )
    pair = {
        "shared_tape": {
            "path": "tapes/x.eventlist", "absolute_path": str(target / "tapes/x.eventlist"),
            "sha256": sha256_bytes(tape),
        },
        "shared_root_sidecar": {
            "path": "tapes/x.roots.tsv", "absolute_path": str(target / "tapes/x.roots.tsv"),
            "sha256": sha256_bytes(sidecar),
        },
        "shared_source_card": {
            "path": "cards/x.source", "absolute_path": str(target / "cards/x.source"),
            "sha256": sha256_bytes(card),
        },
        "geometry_setup": {"absolute_path": str(geometry)}, "mode": "instant",
    }
    envelope = {"plan": {"input_bundle_root": str(target), "pairs": [pair]}, "plan_sha256": "a" * 64}
    return envelope, target, partial, tape, sidecar


class PreloadObserverSentinelTests(unittest.TestCase):
    def test_exact_28_cell_four_shard_ab_ba_matrix_is_672_events(self) -> None:
        pairs = _pair_matrix()
        checked = sentinel.validate_pair_matrix(pairs)
        self.assertEqual(
            checked,
            {"cells": 28, "pairs": 112, "invocations": 224, "events": 672},
        )
        for geometry in sentinel.GEOMETRIES:
            for family in sentinel.FAMILIES:
                for mode in sentinel.MODES:
                    cell = [
                        row for row in pairs
                        if (row["geometry"], row["family"], row["mode"]) == (geometry, family, mode)
                    ]
                    self.assertEqual(
                        sorted(tuple(row["arm_order"]) for row in cell),
                        sorted([
                            ("baseline", "preload"), ("baseline", "preload"),
                            ("preload", "baseline"), ("preload", "baseline"),
                        ]),
                    )
        broken = list(pairs)
        broken[-1] = {**broken[-1], "arm_order": ["baseline", "preload"]}
        with self.assertRaisesRegex(sentinel.SentinelError, "two-AB/two-BA"):
            sentinel.validate_pair_matrix(broken)

    def test_independent_seed_namespace_is_unique_and_disjoint(self) -> None:
        forbidden = {123456789, 987654321}
        seeds = sentinel._sentinel_seeds(forbidden)
        self.assertEqual(len(seeds), 56)
        self.assertEqual(len(set(seeds.values())), 56)
        self.assertTrue(set(seeds.values()).isdisjoint(forbidden))
        self.assertTrue(all(100_000_000 <= value < 1_000_000_000 for value in seeds.values()))
        self.assertEqual(seeds, sentinel._sentinel_seeds(forbidden))

    def test_first_three_derivation_preserves_exact_40_columns_and_controls(self) -> None:
        header = "\t".join(SIDECAR_COLUMNS) + "\n"
        tape_lines: list[str] = []
        sidecar_lines: list[str] = [header]
        for index in range(4):
            event_line = f"{index+1} 0 1 0 {index+1}.0 0 0 60 0 0 -1 0 0 0 511"
            tape_lines.append(event_line + "\n")
            row = {column: "x" for column in SIDECAR_COLUMNS}
            row.update({
                "schema": "m05-tape-root-v2",
                "row_index0": str(index),
                "global_row_index0": str(index),
                "eventlist_id": str(index + 1),
                "stable_root_id": _digest(f"root-{index}"),
                "driver": f"driver-{index}",
                "bin_index": str(index),
                "spectrum_sha256": _digest(f"spectrum-{index}"),
                "control_flag": "1" if index < 3 else "0",
            })
            sidecar_lines.append("\t".join(row[column] for column in SIDECAR_COLUMNS) + "\n")
        with tempfile.TemporaryDirectory() as directory:
            tape = Path(directory) / "parent.eventlist"
            sidecar = Path(directory) / "parent.roots.tsv"
            tape.write_text("".join(tape_lines), encoding="utf-8")
            sidecar.write_text("".join(sidecar_lines), encoding="utf-8")
            derived_tape, derived_sidecar, rows = sentinel._first_three(tape, sidecar)
        self.assertEqual(derived_tape, "".join(tape_lines[:3]).encode("utf-8"))
        self.assertEqual(derived_sidecar, "".join(sidecar_lines[:4]).encode("utf-8"))
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["control_flag"] == "1" for row in rows))
        self.assertEqual(len(SIDECAR_COLUMNS), 40)

    def test_authorization_is_exact_hash_bound_one_time_and_never_generated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            envelope = _authorization_envelope(root / "candidate")
            expected = sentinel.authorization_expected(envelope)
            document = {
                **expected,
                "authorization_id": "independent-review-0001",
                "independent_reviewer": "reviewer-two",
                "issued_utc": "2026-08-12T12:34:56Z",
                "one_time": True,
            }
            validated = sentinel.validate_authorization_document(document, envelope)
            self.assertEqual(validated, document)
            for field in (
                "plan_sha256", "harness_sha256", "cosima_sha256", "observer_binary_sha256",
                "observer_build_manifest_sha256", "mfile_consumer_sha256",
                "planned_job_manifest_sha256", "tape_provenance_manifest_sha256",
                "output_root", "transport_event_limit", "installed_cosima_invocation_limit",
            ):
                altered = dict(document)
                altered[field] = "c" * 64 if isinstance(altered[field], str) else altered[field] + 1
                with self.assertRaisesRegex(sentinel.SentinelError, "binding mismatch"):
                    sentinel.validate_authorization_document(altered, envelope)

            token = root / "authority.json"
            token.write_bytes(canonical_json_bytes(document))
            _, token_sha = sentinel.verify_authorization_token(token, envelope)
            self.assertEqual(token_sha, sha256_bytes(token.read_bytes()))
            consumed = token.with_name(token.name + ".consumed.json")
            consumed.write_text("{}\n", encoding="utf-8")
            with self.assertRaisesRegex(sentinel.SentinelError, "already consumed"):
                sentinel.verify_authorization_token(token, envelope)

    def test_default_cli_only_prints_plan_and_execute_without_token_fails_before_run(self) -> None:
        fake = {"plan": {"status": "PLAN_ONLY__NO_TRANSPORT_AUTHORITY"}, "plan_sha256": "d" * 64}
        with mock.patch.object(sentinel, "build_plan", return_value=fake), mock.patch.object(
            sentinel, "execute", side_effect=AssertionError("execute must not be called")
        ) as execute_mock:
            stdout = io.BytesIO()
            with mock.patch.object(sys, "stdout") as wrapped:
                wrapped.buffer = stdout
                self.assertEqual(sentinel.main([]), 0)
            execute_mock.assert_not_called()
            self.assertEqual(json.loads(stdout.getvalue()), fake)
        with self.assertRaisesRegex(sentinel.SentinelError, "requires --authorization-token"):
            sentinel.execute(fake, None)

    def test_default_print_plan_has_no_writes_and_stale_authority_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "must-not-exist"
            fake = {"plan": {"status": "PLAN_ONLY__NO_TRANSPORT_AUTHORITY"}, "plan_sha256": "e" * 64}
            with mock.patch.object(sentinel, "build_plan", return_value=fake), mock.patch.object(
                sentinel, "_write_exclusive", side_effect=AssertionError("read-only plan attempted a write")
            ), mock.patch.object(sentinel, "_rename_noreplace", side_effect=AssertionError("plan attempted publication")):
                stdout = io.BytesIO()
                with mock.patch.object(sys, "stdout") as wrapped:
                    wrapped.buffer = stdout
                    self.assertEqual(sentinel.main(["--print-plan", "--output-root", str(output)]), 0)
                self.assertFalse(output.exists())
                self.assertEqual(json.loads(stdout.getvalue()), fake)

            with mock.patch.object(
                sentinel,
                "_plan_authorities",
                side_effect=sentinel.SentinelError("normalized generated binary64 tuple hash mismatch"),
            ), mock.patch.object(sentinel, "_write_exclusive") as write_mock:
                with self.assertRaisesRegex(sentinel.SentinelError, "binary64"):
                    sentinel.build_plan(output)
                write_mock.assert_not_called()
                self.assertFalse(output.exists())

    def test_output_planning_allows_one_missing_parent_without_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "sentinel" / "candidate"
            self.assertFalse(output.parent.exists())
            self.assertEqual(sentinel._safe_output_root(output), output.absolute())
            self.assertFalse(output.parent.exists())

    def test_authorization_bytes_and_hash_share_one_descriptor(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            envelope = _authorization_envelope(root / "candidate")
            expected = sentinel.authorization_expected(envelope)
            document = {
                **expected,
                "authorization_id": "independent-review-0002",
                "independent_reviewer": "reviewer-two",
                "issued_utc": "2026-08-12T12:34:56Z",
                "one_time": True,
            }
            token = root / "authority.json"
            replacement = root / "replacement.json"
            original_payload = canonical_json_bytes(document)
            token.write_bytes(original_payload)
            replacement.write_bytes(canonical_json_bytes({**document, "independent_reviewer": "reviewer-three"}))
            real_open = os.open
            open_count = 0

            def counting_open(path: os.PathLike[str] | str, flags: int, mode: int = 0o777) -> int:
                nonlocal open_count
                if Path(path) == token:
                    open_count += 1
                return real_open(path, flags, mode)

            with mock.patch.object(sentinel.os, "open", side_effect=counting_open):
                _, digest = sentinel.verify_authorization_token(token, envelope)
            self.assertEqual(open_count, 1)
            self.assertEqual(digest, sha256_bytes(original_payload))

            held = root / "authority.opened-inode"
            open_count = 0
            swapped = False

            def swapping_open(path: os.PathLike[str] | str, flags: int, mode: int = 0o777) -> int:
                nonlocal open_count, swapped
                descriptor = real_open(path, flags, mode)
                if Path(path) == token:
                    open_count += 1
                    if not swapped:
                        # Preserve the opened inode as a single-link regular file,
                        # but replace the authority pathname before fstat/read.
                        os.rename(token, held)
                        os.rename(replacement, token)
                        swapped = True
                return descriptor

            with mock.patch.object(sentinel.os, "open", side_effect=swapping_open):
                with self.assertRaisesRegex(sentinel.SentinelError, "authority pathname changed"):
                    sentinel.verify_authorization_token(token, envelope)
            self.assertEqual(open_count, 1)
            self.assertFalse(token.with_name(token.name + ".consumed.json").exists())

    def test_runtime_environment_is_frozen_and_ambient_independent(self) -> None:
        first = sentinel._frozen_environment_contract()
        with mock.patch.dict(
            os.environ,
            {"PATH": "/malicious/path", "HOME": "/tmp/ambient-home", "DISPLAY": ":99"},
            clear=True,
        ):
            second = sentinel._frozen_environment_contract()
            runtime = sentinel._base_environment({"environment_contract": second})
        self.assertEqual(first, second)
        self.assertEqual(second["ambient_inheritance"], "NONE")
        self.assertNotIn("DISPLAY", runtime)
        self.assertNotIn("HOME", runtime)
        self.assertEqual(runtime["PATH"], sentinel.FROZEN_RUNTIME_ENVIRONMENT["PATH"])
        self.assertEqual(runtime["LD_LIBRARY_PATH"], sentinel.FROZEN_RUNTIME_ENVIRONMENT["LD_LIBRARY_PATH"])

    def test_input_initial_parent_fsync_failure_is_quarantined(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "candidate.inputs"
            partial = target.with_name(f".{target.name}.partial.inputs.{os.getpid()}")
            geometry = root / "geometry.geo.setup"
            geometry.write_text("Name fixture\n", encoding="utf-8")
            tape = b"1 0 1 0 0 0 0 60 0 0 -1 0 0 0 511\n"
            sidecar = ("\t".join(SIDECAR_COLUMNS) + "\n").encode()
            card = sentinel._source_card_bytes(
                geometry=geometry, mode="instant", tape=target / "tapes/x.eventlist",
            )
            pair = {
                "shared_tape": {
                    "path": "tapes/x.eventlist", "absolute_path": str(target / "tapes/x.eventlist"),
                    "sha256": sha256_bytes(tape),
                },
                "shared_root_sidecar": {
                    "path": "tapes/x.roots.tsv", "absolute_path": str(target / "tapes/x.roots.tsv"),
                    "sha256": sha256_bytes(sidecar),
                },
                "shared_source_card": {
                    "path": "cards/x.source", "absolute_path": str(target / "cards/x.source"),
                    "sha256": sha256_bytes(card),
                },
                "geometry_setup": {"absolute_path": str(geometry)}, "mode": "instant",
            }
            envelope = {"plan": {"input_bundle_root": str(target), "pairs": [pair]}, "plan_sha256": "a" * 64}

            def fsync_failure(path: Path) -> None:
                if Path(path) == target.parent and partial.exists():
                    raise OSError("injected initial input parent fsync failure")

            with (
                mock.patch.object(sentinel, "_reconstruct_derived", return_value=(tape, sidecar)),
                mock.patch.object(sentinel, "_resource_gate", return_value=0),
                mock.patch.object(sentinel, "fsync_directory", side_effect=fsync_failure),
                mock.patch.object(sentinel, "_write_exclusive") as write,
            ):
                with self.assertRaisesRegex(OSError, "initial input parent fsync failure"):
                    sentinel.prepare_input_bundle(envelope)
            write.assert_not_called()
            self.assertFalse(target.exists())
            self.assertFalse(partial.exists())
            self.assertTrue(partial.with_name(partial.name + ".failed").is_dir())

    def test_input_preexisting_and_mkdir_race_foreign_partial_are_never_moved(self) -> None:
        for scenario in ("preexisting", "mkdir_race"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                envelope, target, partial, tape, sidecar = _minimal_input_envelope(root)
                owner_payload = f"foreign-{scenario}\n"
                real_mkdir = Path.mkdir
                if scenario == "preexisting":
                    partial.mkdir()
                    (partial / "owner").write_text(owner_payload, encoding="utf-8")

                def racing_mkdir(path: Path, *args: object, **kwargs: object) -> None:
                    if scenario == "mkdir_race" and Path(path) == partial:
                        os.mkdir(partial)
                        (partial / "owner").write_text(owner_payload, encoding="utf-8")
                        raise FileExistsError("injected foreign partial mkdir race")
                    real_mkdir(path, *args, **kwargs)

                with (
                    mock.patch.object(sentinel, "_reconstruct_derived", return_value=(tape, sidecar)),
                    mock.patch.object(sentinel, "_resource_gate", return_value=0),
                    mock.patch.object(Path, "mkdir", new=racing_mkdir),
                ):
                    with self.assertRaises(FileExistsError):
                        sentinel.prepare_input_bundle(envelope)
                self.assertFalse(target.exists())
                self.assertTrue(partial.is_dir())
                self.assertEqual((partial / "owner").read_text(encoding="utf-8"), owner_payload)
                self.assertFalse(partial.with_name(partial.name + ".failed").exists())

    def test_execute_pretransport_setup_failures_quarantine_stage_and_inputs(self) -> None:
        for phase in ("stage_fsync", "execution_plan", "authorization_copy", "consume"):
            with self.subTest(phase=phase), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output = root / "candidate"
                input_root = root / "candidate.inputs"
                input_root.mkdir()
                input_commit_path = input_root / "input_bundle.commit.json"
                input_commit_path.write_text("{}\n", encoding="utf-8")
                token = {
                    "authorization_id": f"independent-review-{phase}",
                    "installed_cosima_invocation_limit": 2,
                    "transport_event_limit": 6,
                }
                token_path = root / "token.json"
                token_path.write_text("{}\n", encoding="utf-8")
                envelope = {
                    "plan_sha256": "b" * 64,
                    "plan": {"output_root": str(output), "input_bundle_root": str(input_root), "pairs": []},
                }
                stage = output.with_name(f".{output.name}.partial.{token['authorization_id']}")
                real_fsync = sentinel.fsync_directory
                real_write = sentinel._write_exclusive

                def maybe_fsync(path: Path) -> None:
                    if phase == "stage_fsync" and Path(path) == stage.parent and stage.exists():
                        raise OSError("injected stage fsync failure")
                    real_fsync(path)

                def maybe_write(path: Path, payload: bytes, mode: int = 0o644) -> None:
                    if phase == "execution_plan" and path.name == "execution_plan.json":
                        raise OSError("injected execution-plan failure")
                    if phase == "authorization_copy" and path.name == "authorization_token.json":
                        raise OSError("injected authorization-copy failure")
                    real_write(path, payload, mode)

                def maybe_consume(*args: object, **kwargs: object) -> Path:
                    if phase == "consume":
                        raise OSError("injected consumption failure")
                    return sentinel._consume_authorization(*args, **kwargs)

                consume = sentinel._consume_authorization
                if phase == "consume":
                    consume = maybe_consume
                with (
                    mock.patch.object(sentinel, "verify_authorization_token", return_value=(token, "c" * 64)),
                    mock.patch.object(sentinel, "prepare_input_bundle", return_value={"commit": {
                        "absolute_path": str(input_commit_path),
                        "sha256": sha256_bytes(input_commit_path.read_bytes()),
                        "size_bytes": input_commit_path.stat().st_size,
                    }}),
                    mock.patch.object(sentinel, "_resource_gate", return_value=0),
                    mock.patch.object(sentinel, "fsync_directory", side_effect=maybe_fsync),
                    mock.patch.object(sentinel, "_write_exclusive", side_effect=maybe_write),
                    mock.patch.object(sentinel, "_consume_authorization", side_effect=consume),
                    mock.patch.object(sentinel, "_run_arm", side_effect=AssertionError("transport path reached")),
                ):
                    with self.assertRaisesRegex(OSError, "injected"):
                        sentinel.execute(envelope, token_path)
                self.assertFalse(output.exists())
                self.assertFalse(stage.exists())
                self.assertFalse(input_root.exists())
                self.assertTrue(stage.with_name(stage.name + ".failed").is_dir())
                self.assertTrue(input_root.with_name(input_root.name + ".failed").is_dir())

    def test_execute_preexisting_and_mkdir_race_foreign_stage_are_never_moved(self) -> None:
        for scenario in ("preexisting", "mkdir_race"):
            with self.subTest(scenario=scenario), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                output = root / "candidate"
                input_root = root / "candidate.inputs"
                input_root.mkdir()
                input_commit_path = input_root / "input_bundle.commit.json"
                input_commit_path.write_text("{}\n", encoding="utf-8")
                token = {
                    "authorization_id": f"independent-review-{scenario}",
                    "installed_cosima_invocation_limit": 2,
                    "transport_event_limit": 6,
                }
                token_path = root / "token.json"
                token_path.write_text("{}\n", encoding="utf-8")
                stage = output.with_name(f".{output.name}.partial.{token['authorization_id']}")
                owner_payload = f"foreign-{scenario}\n"
                real_mkdir = Path.mkdir
                if scenario == "preexisting":
                    stage.mkdir()
                    (stage / "owner").write_text(owner_payload, encoding="utf-8")

                def racing_mkdir(path: Path, *args: object, **kwargs: object) -> None:
                    if scenario == "mkdir_race" and Path(path) == stage:
                        os.mkdir(stage)
                        (stage / "owner").write_text(owner_payload, encoding="utf-8")
                        raise FileExistsError("injected foreign stage mkdir race")
                    real_mkdir(path, *args, **kwargs)

                envelope = {
                    "plan_sha256": "b" * 64,
                    "plan": {"output_root": str(output), "input_bundle_root": str(input_root), "pairs": []},
                }
                with (
                    mock.patch.object(sentinel, "verify_authorization_token", return_value=(token, "c" * 64)),
                    mock.patch.object(sentinel, "prepare_input_bundle", return_value={"commit": {
                        "absolute_path": str(input_commit_path),
                        "sha256": sha256_bytes(input_commit_path.read_bytes()),
                        "size_bytes": input_commit_path.stat().st_size,
                    }}),
                    mock.patch.object(sentinel, "_resource_gate", return_value=0),
                    mock.patch.object(Path, "mkdir", new=racing_mkdir),
                    mock.patch.object(sentinel, "_run_arm", side_effect=AssertionError("transport path reached")),
                ):
                    with self.assertRaises(FileExistsError):
                        sentinel.execute(envelope, token_path)
                self.assertFalse(output.exists())
                self.assertTrue(stage.is_dir())
                self.assertEqual((stage / "owner").read_text(encoding="utf-8"), owner_payload)
                self.assertFalse(stage.with_name(stage.name + ".failed").exists())
                self.assertFalse(input_root.exists())
                self.assertTrue(input_root.with_name(input_root.name + ".failed").is_dir())

    def test_input_postrename_fsync_failure_quarantines_without_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "candidate.inputs"
            partial = target.with_name(f".{target.name}.partial.inputs.{os.getpid()}")
            foreign0 = target.with_name(target.name + ".failed")
            foreign1 = target.with_name(target.name + f".failed.{os.getpid()}")
            foreign0.mkdir(); foreign1.mkdir()
            (foreign0 / "owner").write_text("foreign-0", encoding="utf-8")
            (foreign1 / "owner").write_text("foreign-1", encoding="utf-8")
            tape = b"1 0 1 0 0 0 0 60 0 0 -1 0 0 0 511\n"
            sidecar = ("\t".join(SIDECAR_COLUMNS) + "\n").encode()
            geometry = root / "geometry.geo.setup"
            geometry.write_text("Name fixture\n", encoding="utf-8")
            card = sentinel._source_card_bytes(geometry=geometry, mode="instant", tape=target / "tapes/x.eventlist")
            pair = {
                "shared_tape": {
                    "path": "tapes/x.eventlist", "absolute_path": str(target / "tapes/x.eventlist"),
                    "sha256": sha256_bytes(tape),
                },
                "shared_root_sidecar": {
                    "path": "tapes/x.roots.tsv", "absolute_path": str(target / "tapes/x.roots.tsv"),
                    "sha256": sha256_bytes(sidecar),
                },
                "shared_source_card": {
                    "path": "cards/x.source", "absolute_path": str(target / "cards/x.source"),
                    "sha256": sha256_bytes(card),
                },
                "geometry_setup": {"absolute_path": str(geometry)}, "mode": "instant",
            }
            envelope = {"plan": {"input_bundle_root": str(target), "pairs": [pair]}, "plan_sha256": "a" * 64}
            real_fsync = sentinel.fsync_directory

            def fail_after_publish(path: Path) -> None:
                if Path(path) == target.parent and target.exists() and not partial.exists():
                    raise OSError("injected parent fsync failure")
                real_fsync(path)

            with (
                mock.patch.object(sentinel, "_reconstruct_derived", return_value=(tape, sidecar)),
                mock.patch.object(sentinel, "validate_sidecar", return_value={"event_count": 3}),
                mock.patch.object(sentinel, "_resource_gate", return_value=0),
                mock.patch.object(sentinel, "fsync_directory", side_effect=fail_after_publish),
            ):
                with self.assertRaisesRegex(OSError, "injected parent fsync failure"):
                    sentinel.prepare_input_bundle(envelope)
            failed = target.with_name(target.name + f".failed.{os.getpid()}.1")
            self.assertFalse(target.exists())
            self.assertFalse(partial.exists())
            self.assertEqual((foreign0 / "owner").read_text(), "foreign-0")
            self.assertEqual((foreign1 / "owner").read_text(), "foreign-1")
            self.assertTrue((failed / "input_bundle.commit.json").is_file())

    def test_final_postrename_fsync_failure_quarantines_and_never_recreates_stage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "candidate"
            input_root = root / "candidate.inputs"
            input_root.mkdir()
            input_commit_path = input_root / "input_bundle.commit.json"
            input_commit_path.write_text("{}\n", encoding="utf-8")
            foreign0 = output.with_name(output.name + ".failed")
            foreign1 = output.with_name(output.name + f".failed.{os.getpid()}")
            foreign0.mkdir(); foreign1.mkdir()
            (foreign0 / "owner").write_text("foreign-0", encoding="utf-8")
            (foreign1 / "owner").write_text("foreign-1", encoding="utf-8")
            envelope = {
                "plan_sha256": "b" * 64,
                "plan": {
                    "output_root": str(output), "input_bundle_root": str(input_root),
                    "pairs": [{"pair_id": "p", "arm_order": ["baseline", "preload"]}],
                },
            }
            token = {
                "authorization_id": "independent-review-0003",
                "installed_cosima_invocation_limit": 2,
                "transport_event_limit": 6,
            }
            token_path = root / "token.json"
            token_path.write_text("{}\n", encoding="utf-8")
            stage = output.with_name(f".{output.name}.partial.{token['authorization_id']}")
            real_fsync = sentinel.fsync_directory

            def fail_after_publish(path: Path) -> None:
                if Path(path) == output.parent and output.exists() and not stage.exists():
                    raise OSError("injected final parent fsync failure")
                real_fsync(path)

            arm_receipt = lambda arm: {
                "arm": arm,
                "cosima_metrics": {
                    "wall_s": 1.0, "cpu_user_s": 0.5, "cpu_system_s": 0.1,
                    "peak_process_group_rss_bytes": 100, "runtime_mapped_paths": [],
                },
            }
            with (
                mock.patch.object(sentinel, "verify_authorization_token", return_value=(token, "c" * 64)),
                mock.patch.object(sentinel, "prepare_input_bundle", return_value={"commit": {
                    "absolute_path": str(input_commit_path),
                    "sha256": sha256_bytes(input_commit_path.read_bytes()),
                    "size_bytes": input_commit_path.stat().st_size,
                }}),
                mock.patch.object(sentinel, "_run_arm", side_effect=lambda pair, arm, **kwargs: arm_receipt(arm)),
                mock.patch.object(sentinel, "_compare_pair", return_value={"commit": {"path": "p", "sha256": "e" * 64, "size_bytes": 1}}),
                mock.patch.object(sentinel, "_resource_gate", return_value=0),
                mock.patch.object(sentinel, "fsync_directory", side_effect=fail_after_publish),
                mock.patch.object(sentinel, "PAIR_COUNT", 1),
                mock.patch.object(sentinel, "INVOCATION_COUNT", 2),
                mock.patch.object(sentinel, "TRANSPORT_EVENT_COUNT", 6),
            ):
                with self.assertRaisesRegex(OSError, "injected final parent fsync failure"):
                    sentinel.execute(envelope, token_path)
            failed = output.with_name(output.name + f".failed.{os.getpid()}.1")
            self.assertFalse(output.exists())
            self.assertFalse(stage.exists())
            self.assertEqual((foreign0 / "owner").read_text(), "foreign-0")
            self.assertEqual((foreign1 / "owner").read_text(), "foreign-1")
            self.assertTrue((failed / "sentinel.commit.json").is_file())
            self.assertTrue((failed / "failure.json").is_file())

    def test_runtime_inputs_and_full_geometry_bundle_are_rehashed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            setup = root / "fixture.geo.setup"
            main = root / "main.geo"
            material = root / "material.geo"
            setup.write_text("Include main.geo\n", encoding="utf-8")
            main.write_text("Include material.geo\n", encoding="utf-8")
            material.write_text("Name material\n", encoding="utf-8")
            rows = [
                {"path": str(path), "sha256": sentinel.sha256(path)}
                for path in (setup, main, material)
            ]
            digest_input = "".join(
                f"{row['path']}\0{row['sha256']}\n" for row in sorted(rows, key=lambda value: value["path"])
            )
            bundle = {
                "setup": str(setup), "files": rows, "file_count": 3,
                "bundle_sha256": sha256_bytes(digest_input.encode()),
                "digest_contract": "SHA256 of sorted path\\0sha256\\n records",
            }
            geometry = sentinel._geometry_authority_record(bundle)
            tape = root / "tape.eventlist"
            sidecar = root / "tape.roots.tsv"
            card = root / "card.source"
            tape.write_text("1 0 1 0 0 0 0 60 0 0 -1 0 0 0 511\n", encoding="utf-8")
            sidecar.write_text("header\n", encoding="utf-8")
            card.write_bytes(sentinel._source_card_bytes(geometry=setup, mode="instant", tape=tape))
            pair = {
                "geometry": "mass_model_511", "geometry_bundle_sha256": geometry["bundle_sha256"],
                "shared_tape": sentinel._binding(tape),
                "shared_root_sidecar": sentinel._binding(sidecar),
                "shared_source_card": sentinel._binding(card),
            }
            plan = {"authority_bindings": {"geometry_bundles": {"mass_model_511": geometry}}}
            input_commit = root / "input_bundle.commit.json"
            execution_plan = root / "execution_plan.json"
            input_commit.write_text("{}\n", encoding="utf-8")
            execution_plan.write_text("{}\n", encoding="utf-8")
            transaction = {
                "input_bundle_commit": sentinel._binding(input_commit),
                "execution_plan": sentinel._binding(execution_plan),
            }
            sentinel._verify_pair_runtime_inputs(pair, plan, transaction)
            stdout = root / "must-not-create.stdout"
            stderr = root / "must-not-create.stderr"
            popen = mock.Mock(side_effect=AssertionError("child launched with drifted input"))
            mutations = (
                (tape, tape.read_bytes()), (sidecar, sidecar.read_bytes()),
                (card, card.read_bytes()), (main, main.read_bytes()),
                (material, material.read_bytes()),
                (input_commit, input_commit.read_bytes()),
                (execution_plan, execution_plan.read_bytes()),
            )
            with (
                mock.patch.object(sentinel, "_resource_gate", return_value=0),
                mock.patch.object(sentinel.subprocess, "Popen", popen),
            ):
                for path, original in mutations:
                    path.write_bytes(original + b"# drift\n")
                    with self.assertRaises((sentinel.SentinelError, ValueError)):
                        sentinel._run_supervised(
                            ["/usr/bin/true"], cwd=root, environment={},
                            stdout_path=stdout, stderr_path=stderr,
                            stage_root=root, input_root=root,
                            expected_executable_sha256=sentinel.sha256(Path("/usr/bin/true")),
                            input_validator=lambda: sentinel._verify_pair_runtime_inputs(
                                pair, plan, transaction,
                            ),
                        )
                    path.write_bytes(original)
                    self.assertFalse(stdout.exists())
                    self.assertFalse(stderr.exists())
            popen.assert_not_called()
            sentinel._verify_pair_runtime_inputs(pair, plan, transaction)

    def test_execute_reserve_failure_does_not_create_missing_output_parent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "sentinel" / "candidate"
            token = root / "authority.json"
            envelope = {"plan": {"output_root": str(output)}}
            verify = mock.Mock(return_value=({}, "a" * 64))
            with (
                mock.patch.object(
                    sentinel.shutil, "disk_usage",
                    return_value=type(
                        "Usage", (), {"free": sentinel.MINIMUM_LIVE_DISK_RESERVE_BYTES - 1},
                    )(),
                ),
                mock.patch.object(sentinel, "verify_authorization_token", verify),
            ):
                with self.assertRaisesRegex(sentinel.SentinelError, "minimum live disk reserve"):
                    sentinel.execute(envelope, token)
            verify.assert_called_once_with(token, envelope)
            self.assertFalse(output.parent.exists())

    def test_invalid_token_fails_before_any_output_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "sentinel" / "candidate"
            token = root / "invalid-token.json"
            token.write_text("{}\n", encoding="utf-8")
            envelope = {"plan": {"output_root": str(output)}}
            with (
                mock.patch.object(
                    sentinel, "verify_authorization_token",
                    side_effect=sentinel.SentinelError("invalid authorization token"),
                ),
                mock.patch.object(
                    sentinel, "_ensure_output_parent",
                    side_effect=AssertionError("invalid token caused output-parent write"),
                ) as ensure,
                mock.patch.object(
                    sentinel, "_resource_gate",
                    side_effect=AssertionError("invalid token passed authorization boundary"),
                ) as resource_gate,
            ):
                with self.assertRaisesRegex(sentinel.SentinelError, "invalid authorization token"):
                    sentinel.execute(envelope, token)
            ensure.assert_not_called()
            resource_gate.assert_not_called()
            self.assertFalse(output.parent.exists())

    def test_input_byte_cap_fails_before_any_publication_write(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "candidate.inputs"
            geometry = root / "geometry.geo.setup"
            geometry.write_text("Name fixture\n", encoding="utf-8")
            tape = b"1 0 1 0 0 0 0 60 0 0 -1 0 0 0 511\n"
            sidecar = ("\t".join(SIDECAR_COLUMNS) + "\n").encode()
            card = sentinel._source_card_bytes(
                geometry=geometry, mode="instant", tape=target / "tapes/x.eventlist",
            )
            pair = {
                "shared_tape": {
                    "path": "tapes/x.eventlist", "absolute_path": str(target / "tapes/x.eventlist"),
                    "sha256": sha256_bytes(tape),
                },
                "shared_root_sidecar": {
                    "path": "tapes/x.roots.tsv", "absolute_path": str(target / "tapes/x.roots.tsv"),
                    "sha256": sha256_bytes(sidecar),
                },
                "shared_source_card": {
                    "path": "cards/x.source", "absolute_path": str(target / "cards/x.source"),
                    "sha256": sha256_bytes(card),
                },
                "geometry_setup": {"absolute_path": str(geometry)}, "mode": "instant",
            }
            envelope = {"plan": {"input_bundle_root": str(target), "pairs": [pair]}, "plan_sha256": "a" * 64}
            with (
                mock.patch.object(sentinel, "_reconstruct_derived", return_value=(tape, sidecar)),
                mock.patch.object(sentinel, "MAXIMUM_NEW_BYTES", 1),
                mock.patch.object(sentinel, "_write_exclusive") as write,
            ):
                with self.assertRaisesRegex(sentinel.SentinelError, "global new-byte hard cap"):
                    sentinel.prepare_input_bundle(envelope)
            write.assert_not_called()
            self.assertFalse(target.exists())
            self.assertFalse(target.with_name(f".{target.name}.partial.inputs.{os.getpid()}").exists())

    def test_final_resource_failure_precedes_publish_and_quarantines_stage(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "candidate"
            input_root = root / "candidate.inputs"
            input_root.mkdir()
            input_commit_path = input_root / "input_bundle.commit.json"
            input_commit_path.write_text("{}\n", encoding="utf-8")
            envelope = {
                "plan_sha256": "b" * 64,
                "plan": {
                    "output_root": str(output), "input_bundle_root": str(input_root),
                    "pairs": [{"pair_id": "p", "arm_order": ["baseline", "preload"]}],
                },
            }
            token = {
                "authorization_id": "independent-review-0004",
                "installed_cosima_invocation_limit": 2,
                "transport_event_limit": 6,
            }
            token_path = root / "token.json"
            token_path.write_text("{}\n", encoding="utf-8")
            stage = output.with_name(f".{output.name}.partial.{token['authorization_id']}")
            arm_receipt = lambda arm: {
                "arm": arm,
                "cosima_metrics": {
                    "wall_s": 1.0, "cpu_user_s": 0.5, "cpu_system_s": 0.1,
                    "peak_process_group_rss_bytes": 100, "runtime_mapped_paths": [],
                },
            }

            def resource_gate(*, phase: str, **_: object) -> int:
                if phase == "before sentinel final publication":
                    raise sentinel.SentinelError("injected prepublication resource failure")
                return 0

            with (
                mock.patch.object(sentinel, "verify_authorization_token", return_value=(token, "c" * 64)),
                mock.patch.object(sentinel, "prepare_input_bundle", return_value={"commit": {
                    "absolute_path": str(input_commit_path),
                    "sha256": sha256_bytes(input_commit_path.read_bytes()),
                    "size_bytes": input_commit_path.stat().st_size,
                }}),
                mock.patch.object(sentinel, "_run_arm", side_effect=lambda pair, arm, **kwargs: arm_receipt(arm)),
                mock.patch.object(sentinel, "_compare_pair", return_value={"commit": {
                    "path": "p", "sha256": "e" * 64, "size_bytes": 1,
                }}),
                mock.patch.object(sentinel, "_resource_gate", side_effect=resource_gate),
                mock.patch.object(sentinel, "_rename_noreplace") as publish,
                mock.patch.object(sentinel, "PAIR_COUNT", 1),
                mock.patch.object(sentinel, "INVOCATION_COUNT", 2),
                mock.patch.object(sentinel, "TRANSPORT_EVENT_COUNT", 6),
            ):
                with self.assertRaisesRegex(sentinel.SentinelError, "prepublication resource failure"):
                    sentinel.execute(envelope, token_path)
            publish.assert_not_called()
            self.assertFalse(output.exists())
            self.assertFalse(stage.exists())
            failed = stage.with_name(stage.name + ".failed")
            self.assertTrue((failed / "sentinel.commit.json").is_file())
            self.assertTrue((failed / "failure.json").is_file())

    def test_resource_reserve_blocks_before_child_creation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            executable = Path("/usr/bin/true")
            validator = mock.Mock()
            with (
                mock.patch.object(
                    sentinel.shutil, "disk_usage",
                    return_value=type("Usage", (), {"free": sentinel.MINIMUM_LIVE_DISK_RESERVE_BYTES - 1})(),
                ),
                mock.patch.object(
                    sentinel.subprocess, "Popen",
                    side_effect=AssertionError("child was created before reserve gate"),
                ) as popen,
            ):
                with self.assertRaisesRegex(sentinel.SentinelError, "minimum live disk reserve"):
                    sentinel._run_supervised(
                        [str(executable)], cwd=root, environment={},
                        stdout_path=root / "stdout", stderr_path=root / "stderr",
                        stage_root=root, input_root=root,
                        expected_executable_sha256=sentinel.sha256(executable),
                        input_validator=validator,
                    )
            popen.assert_not_called()
            validator.assert_not_called()
            self.assertFalse((root / "stdout").exists())
            self.assertFalse((root / "stderr").exists())

    def test_resource_environment_transaction_and_shared_validator_are_hard_gates(self) -> None:
        source = Path(sentinel.__file__).read_text(encoding="utf-8")
        self.assertEqual(sentinel.MAXIMUM_NEW_BYTES, 1024**3)
        self.assertEqual(sentinel.MINIMUM_LIVE_DISK_RESERVE_BYTES, 20 * 1024**3)
        self.assertEqual(sentinel.MAXIMUM_PROCESS_GROUP_RSS_BYTES, 8 * 1024**3)
        self.assertIn("resource.setrlimit(resource.RLIMIT_FSIZE", source)
        self.assertIn("start_new_session=True", source)
        self.assertIn("os.killpg", source)
        self.assertIn("rename_no_replace as _rename_noreplace", source)
        self.assertIn("quarantine_directory_no_replace", source)
        self.assertIn("_verify_pair_runtime_inputs", source)
        self.assertIn("_read_one_regular_descriptor", source)
        self.assertIn("phase=\"immediately before child launch\"", source)
        self.assertIn("_fsync_tree(stage)", source)
        self.assertIn("validate_observer_transaction(", source)
        self.assertIn("TES511_PRELOAD_EXPECTED_LIBCOSIMA", source)
        self.assertIn("TES511_PRELOAD_EXPECTED_LIBCOSIMA_SHA256", source)
        self.assertIn("canonicalize_rich_sim_date", source)
        self.assertIn("baseline/preload native DAT raw bytes differ", source)
        self.assertNotIn("cosima_command=", source)

    def test_date_only_sim_canonicalization_and_native_dat_parser(self) -> None:
        left = b"Type       SIM\nVersion    101\nDate       2026-01-01 00:00:00\nEN\n"
        right = b"Type       SIM\nVersion    101\nDate       2026-01-02 00:00:00\nEN\n"
        self.assertEqual(
            sentinel.canonicalize_rich_sim_date(left),
            sentinel.canonicalize_rich_sim_date(right),
        )
        with self.assertRaisesRegex(sentinel.SentinelError, "0 Date"):
            sentinel.canonicalize_rich_sim_date(b"Type SIM\nEN\n")
        with self.assertRaisesRegex(sentinel.SentinelError, "2 Date"):
            sentinel.canonicalize_rich_sim_date(left + b"Date x\n")
        with tempfile.TemporaryDirectory() as directory:
            dat = Path(directory) / "native.dat"
            dat.write_text("# native\nTT 0.003\nEN\n", encoding="utf-8")
            result = sentinel._validate_native_dat_file(dat)
            self.assertEqual(result["TT_s"], 0.003)
            dat.write_text("TT 0\nEN\n", encoding="utf-8")
            with self.assertRaisesRegex(sentinel.SentinelError, "TT must be positive"):
                sentinel._validate_native_dat_file(dat)

    def test_pair_comparison_rejects_sim_and_dat_mismatch(self) -> None:
        def receipt(*, sim: bytes = b"same", dat: bytes = b"same") -> dict[str, object]:
            return {
                "_canonical_sim_bytes": sim,
                "_dat_bytes": dat,
                "_stdout_normalized": b"stdout",
                "_stderr_bytes": b"",
                "rich_sim": {"canonical_date_only_sha256": _digest(sim.decode())},
                "native_dat": {"TT_s": 0.003, "binding": {"sha256": _digest(dat.decode())}},
                "cosima_metrics": {
                    "wall_s": 1.0, "cpu_user_s": 0.5, "cpu_system_s": 0.1,
                    "peak_process_group_rss_bytes": 100,
                },
                "commit": {"path": "arm.commit.json", "sha256": "f" * 64, "size_bytes": 1},
            }

        pair = {
            "pair_id": "g__gamma_instant__s0000", "cell_id": "g__gamma_instant",
            "geometry": "g", "family": "gamma", "mode": "instant", "shard_index": 0,
            "arm_order": ["baseline", "preload"], "transport_seed": 123456789,
            "shared_tape": {"sha256": "1" * 64},
            "shared_root_sidecar": {"sha256": "2" * 64},
            "shared_source_card": {"sha256": "3" * 64},
        }
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory)
            (stage / "pairs" / pair["pair_id"]).mkdir(parents=True)
            with self.assertRaisesRegex(sentinel.SentinelError, "rich SIM differs"):
                sentinel._compare_pair(pair, {"baseline": receipt(), "preload": receipt(sim=b"changed")}, stage)
            with self.assertRaisesRegex(sentinel.SentinelError, "DAT raw bytes differ"):
                sentinel._compare_pair(pair, {"baseline": receipt(), "preload": receipt(dat=b"changed")}, stage)

    def test_run_arm_sets_exact_libcosima_env_and_calls_shared_validator(self) -> None:
        source = Path(sentinel.__file__).read_text(encoding="utf-8")
        self.assertIn(
            '"TES511_PRELOAD_EXPECTED_LIBCOSIMA": plan["authority_bindings"]["installed_libCosima"]["absolute_path"]',
            source,
        )
        self.assertIn(
            '"TES511_PRELOAD_EXPECTED_LIBCOSIMA_SHA256": plan["authority_bindings"]["installed_libCosima"]["sha256"]',
            source,
        )
        self.assertIn("shared_validation = validate_observer_transaction(", source)
        self.assertIn('"validator_origin": plan["authority_bindings"]["preload_observer_validation_code"]', source)
        self.assertGreaterEqual(source.count("_verify_runtime_authorities(plan)"), 2)
        self.assertIn('closure=plan["authority_bindings"]["installed_cosima_ldd_closure"]', source)
        self.assertIn('closure=plan["authority_bindings"]["mfile_consumer_ldd_closure"]', source)

    def test_runtime_executables_manifests_and_dso_closures_are_rehashed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            keys = (
                "observer_build_manifest", "observer_binary", "installed_cosima",
                "installed_libCosima", "mfile_consumer_manifest", "mfile_consumer_binary",
            )
            bindings = {}
            paths = []
            for index, key in enumerate(keys):
                path = root / key
                path.write_bytes(f"authority-{index}\n".encode())
                paths.append(path)
                bindings[key] = sentinel._binding(path)
            cosima_dso = root / "cosima.dso"
            mfile_dso = root / "mfile.dso"
            cosima_dso.write_bytes(b"cosima dso\n")
            mfile_dso.write_bytes(b"mfile dso\n")
            bindings["installed_cosima_ldd_closure"] = [sentinel._binding(cosima_dso)]
            bindings["mfile_consumer_ldd_closure"] = [sentinel._binding(mfile_dso)]
            plan = {"authority_bindings": bindings}
            sentinel._verify_runtime_authorities(plan)
            for path in (*paths, cosima_dso, mfile_dso):
                original = path.read_bytes()
                path.write_bytes(original + b"drift\n")
                with self.assertRaisesRegex(sentinel.SentinelError, "binding drift"):
                    sentinel._verify_runtime_authorities(plan)
                path.write_bytes(original)
            sentinel._verify_runtime_authorities(plan)

    def test_observer_all_row_join_recomputes_binary64_digest(self) -> None:
        values = [0.0, 1.0e-6, 0.0, 0.0, 60.0, 0.0, 0.0, -1.0, 0.0, 0.0, 0.0, 511.0]
        digest = sha256_bytes(b"m05-eventlist-binary64-v1\0" + struct.pack(">i12d", 1, *values))
        sidecar_row = {column: "x" for column in SIDECAR_COLUMNS}
        sidecar_row.update({
            "stable_root_id": _digest("root"),
            "particle": "1",
            "excitation_keV": "0",
            "source_time_s": "9.9999999999999995e-07",
            "x_cm": "0", "y_cm": "0", "z_cm": "60",
            "dx": "0", "dy": "0", "dz": "-1",
            "px": "0", "py": "0", "pz": "0",
            "energy_keV": "511",
            "expected_generated_binary64_sha256": digest,
        })
        observed = {
            "simulation_event_id": "1",
            "stable_root_id": sidecar_row["stable_root_id"],
            "eventlist_id": "1",
            "arm": "F",
            "observed_particle": "1",
            "observed_excitation_keV": "0",
            "expected_source_time_s": sidecar_row["source_time_s"],
            "observed_source_time_s": "9.9999999999999995e-07",
            "observed_x_cm": "0", "observed_y_cm": "0", "observed_z_cm": "60",
            "observed_dx": "0", "observed_dy": "0", "observed_dz": "-1",
            "observed_px": "0", "observed_py": "0", "observed_pz": "0",
            "observed_energy_keV": "511",
            "expected_generated_binary64_sha256": digest,
            "observed_generated_binary64_sha256": digest,
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            sidecar = root / "three.roots.tsv"
            observer = root / "generated_observations.tsv"
            sidecar.write_text(
                "\t".join(SIDECAR_COLUMNS) + "\n" +
                "\t".join(sidecar_row[column] for column in SIDECAR_COLUMNS) + "\n",
                encoding="utf-8",
            )
            observer.write_text(
                "\t".join(sentinel.OBSERVER_COLUMNS) + "\n" +
                "\t".join(observed[column] for column in sentinel.OBSERVER_COLUMNS) + "\n",
                encoding="utf-8",
            )
            checked = sentinel.validate_observer_rows(observer, sidecar)
            self.assertEqual(checked["event_count"], 1)
            with observer.open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle, delimiter="\t"))
            rows[0]["observed_energy_keV"] = "510"
            observer.write_text(
                "\t".join(sentinel.OBSERVER_COLUMNS) + "\n" +
                "\t".join(rows[0][column] for column in sentinel.OBSERVER_COLUMNS) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(sentinel.SentinelError, "digest"):
                sentinel.validate_observer_rows(observer, sidecar)


if __name__ == "__main__":
    unittest.main()

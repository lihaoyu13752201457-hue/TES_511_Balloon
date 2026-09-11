from __future__ import annotations

import fcntl
import json
import os
import signal
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[3]
CODE = ROOT / "engineering/particle_source_unit_repair_20260811/code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

import run_mergeable_gamma_instant_batch0003 as batch  # noqa: E402
import validate_mergeable_gamma_instant_batch0003 as validator  # noqa: E402


class GammaInstantBatch0003ContractTests(unittest.TestCase):
    def tearDown(self) -> None:
        batch._ABORT_EVENT.clear()
        with batch._ACTIVE_PROCESS_LOCK:
            batch._ACTIVE_PROCESSES.clear()

    def test_schedule_closes_exact_fixed_checkpoints(self) -> None:
        rows = batch.planned_shards()
        self.assertEqual(len(rows), 396)
        self.assertEqual(rows[195]["events"], 24_000)
        self.assertEqual(rows[195]["cumulative_events_per_geometry"], 5_000_000)
        self.assertEqual(rows[195]["checkpoint"], "5m")
        self.assertEqual(rows[-1]["cumulative_events_per_geometry"], 10_000_000)
        self.assertEqual(rows[-1]["checkpoint"], "10m")
        self.assertEqual(sum(int(row["events"]) for row in rows), 9_899_000)

    def test_seed_registry_is_unique_and_disjoint_from_all_retained_batches(self) -> None:
        ledgers = [
            batch._load_json(path)
            for path in (batch.BATCH0000_LEDGER, batch.BATCH0001_LEDGER, batch.BATCH0002_LEDGER)
        ]
        planned = {batch.shard_seed(i) for i in range(1, batch.FINAL_SHARD_COUNT + 1)}
        self.assertEqual(len(planned), batch.FINAL_SHARD_COUNT)
        self.assertTrue(planned.isdisjoint(batch._prior_seeds(*ledgers)))

    def test_corrected_gamma_cards_are_full_information_and_legacy_free(self) -> None:
        for geometry in batch.GEOMETRIES:
            text = batch.source_card_path(geometry).read_text(encoding="utf-8")
            self.assertEqual(
                text.count("engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/"),
                20,
            )
            self.assertNotIn("cosima_spectra_dp_2602units", text)
            self.assertEqual(text.count("StoreSimulationInfo all"), 1)

    def test_prior_101k_transport_and_geometry_are_exactly_equivalent(self) -> None:
        ledger0 = batch._load_json(batch.BATCH0000_LEDGER)
        ledger1 = batch._load_json(batch.BATCH0001_LEDGER)
        record = batch.require_prior_credit_equivalence(
            ledger0,
            ledger1,
            ledger1["transport"],
            ledger1["geometry_bundles"],
        )
        self.assertEqual(record["status"], "PASS__PRIOR_101K_PHYSICS_INPUTS_EQUAL_CURRENT")

        changed = json.loads(json.dumps(ledger1["geometry_bundles"]))
        changed["s3d_o8"]["bundle_sha256"] = "0" * 64
        with self.assertRaises(SystemExit):
            batch.require_prior_credit_equivalence(ledger0, ledger1, ledger1["transport"], changed)

    def test_pairing_is_operational_not_common_random_statistical_pairing(self) -> None:
        self.assertIn("operational", batch.PAIRING_RULE)
        self.assertIn("not common-random-number", batch.PAIRING_STATISTICAL_SEMANTICS)
        self.assertIn("independent normalization", batch.PAIRING_STATISTICAL_SEMANTICS)

    def test_concurrent_state_updates_are_serialized_and_lossless(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_path = Path(temporary) / "state.json"
            missing_contract = Path(temporary) / "no_global_contract.json"
            with mock.patch.object(batch, "EXECUTION_STATE", state_path), \
                 mock.patch.object(batch, "GLOBAL_CONTRACT", missing_contract):
                batch.atomic_replace_json(state_path, {"status": "RUNNING"})
                threads = [
                    threading.Thread(target=batch._update_state, kwargs={f"worker_{index}": index})
                    for index in range(32)
                ]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(timeout=5)
                self.assertFalse(any(thread.is_alive() for thread in threads))
                state = json.loads(state_path.read_text(encoding="utf-8"))
                for index in range(32):
                    self.assertEqual(state[f"worker_{index}"], index)

    def test_execution_state_rejects_extended_deadline_and_immutable_updates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            global_contract = Path(temporary) / "contract.json"
            global_contract.write_text("{}\n", encoding="utf-8")
            started = datetime(2026, 8, 11, 0, 0, tzinfo=timezone.utc)
            deadline = started + timedelta(hours=12)
            contract = {
                "execution": {
                    "wall_limit_hours": 12.0,
                    "frozen_started_utc": started.isoformat(),
                    "frozen_deadline_utc": deadline.isoformat(),
                }
            }
            with mock.patch.object(batch, "GLOBAL_CONTRACT", global_contract):
                state = {
                    "started_utc": started.isoformat(),
                    "deadline_utc": deadline.isoformat(),
                    "global_contract_sha256": batch.smoke.sha256(global_contract),
                }
                batch._validate_execution_state(contract, state)
                state["deadline_utc"] = (deadline + timedelta(hours=1)).isoformat()
                with self.assertRaisesRegex(RuntimeError, "immutable"):
                    batch._validate_execution_state(contract, state)
                with self.assertRaisesRegex(RuntimeError, "immutable execution-state update"):
                    batch._update_state(deadline_utc=deadline.isoformat())

    def test_disk_gate_includes_reserve_and_active_attempt_burst(self) -> None:
        contract = {
            "execution": {"requested_worker_cap": 4},
            "campaigns": [
                {"geometry": geometry, "calibration": {"observed_bytes_per_event": 1.0}}
                for geometry in batch.GEOMETRIES
            ],
        }
        with (
            mock.patch.object(batch, "remaining_point_bytes", return_value=1_000.0),
            mock.patch.object(batch, "_attempt_output_cap_bytes", return_value=500),
            mock.patch.object(batch.shutil, "disk_usage", return_value=SimpleNamespace(free=10**12)),
        ):
            gate = batch.disk_gate(contract, requested_workers=4)
        self.assertEqual(gate["active_worker_burst_margin_bytes"], 2_000)
        self.assertEqual(
            gate["required_free_bytes"],
            batch.DISK_RESERVE_BYTES + 2_000 + batch.DISK_EMERGENCY_MARGIN_BYTES,
        )
        self.assertEqual(gate["status"], "PASS")

    def test_terminate_process_group_signals_children_after_leader_exit(self) -> None:
        class ExitedLeader:
            pid = 424242

            @staticmethod
            def poll() -> int:
                return 0

            @staticmethod
            def wait(timeout: float) -> int:
                return 0

        calls: list[int] = []

        def fake_killpg(_pgid: int, signum: int) -> None:
            calls.append(signum)
            if signum == 0:
                raise ProcessLookupError

        with mock.patch.object(batch.os, "killpg", side_effect=fake_killpg):
            batch._terminate_process_group(ExitedLeader())
        self.assertIn(signal.SIGTERM, calls)

    def test_attempt_supervisor_exception_guarantees_process_cleanup(self) -> None:
        class FakeProcess:
            pid = 31337

            def __init__(self) -> None:
                self.alive = True

            def poll(self) -> int | None:
                return None if self.alive else -signal.SIGTERM

            def wait(self, timeout: float) -> int:
                self.alive = False
                return -signal.SIGTERM

        class FakeRuntime:
            @staticmethod
            def patch_source(job: dict[str, object]) -> None:
                Path(str(job["temp_source"])).write_text("patched\n", encoding="utf-8")

        fake = FakeProcess()

        def terminate(proc: FakeProcess) -> None:
            proc.alive = False

        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "base.source"
            source.write_text("base\n", encoding="utf-8")
            global_contract = root / "contract.json"
            global_contract.write_text("{}\n", encoding="utf-8")
            outdir = root / "attempt01"
            contract = {"transport": {"cosima": "/fake/cosima"}}
            deadline = datetime.now(timezone.utc) + timedelta(minutes=1)
            with (
                mock.patch.object(batch, "_load_generic_runner", return_value=FakeRuntime()),
                mock.patch.object(batch, "_verify_attempt_inputs", return_value="a" * 64),
                mock.patch.object(batch, "attempt_dir", return_value=outdir),
                mock.patch.object(batch, "GLOBAL_CONTRACT", global_contract),
                mock.patch.object(batch, "source_card_path", return_value=source),
                mock.patch.object(batch, "_attempt_output_cap_bytes", return_value=500_000_000),
                mock.patch.object(batch.subprocess, "Popen", return_value=fake),
                mock.patch.object(batch.time, "sleep", side_effect=RuntimeError("watchdog failure")),
                mock.patch.object(batch, "_terminate_process_group", side_effect=terminate) as cleanup,
                mock.patch.object(batch.shutil, "disk_usage", return_value=SimpleNamespace(free=10**12)),
            ):
                with self.assertRaisesRegex(RuntimeError, "watchdog failure"):
                    batch._run_attempt(contract, {}, "mass_model_511", 1, 1, deadline)
            cleanup.assert_called()
            self.assertFalse(fake.alive)
            self.assertFalse(batch._ACTIVE_PROCESSES)

    def test_controller_lock_is_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            lock_path = Path(temporary) / "controller.lock"
            with (
                mock.patch.object(batch, "RUN_ROOT", Path(temporary)),
                mock.patch.object(batch, "CONTROLLER_LOCK", lock_path),
            ):
                first = batch._acquire_controller_lock()
                try:
                    with self.assertRaises(SystemExit):
                        batch._acquire_controller_lock()
                finally:
                    fcntl.flock(first.fileno(), fcntl.LOCK_UN)
                    first.close()

    def test_stale_batch_process_detection_uses_attempt_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            proc_root = Path(temporary)
            process = proc_root / "1234"
            process.mkdir()
            marker = str(batch.campaign_dir("mass_model_511").resolve())
            (process / "cmdline").write_bytes(b"/fake/cosima\0" + marker.encode() + b"/job.source\0")
            found = batch._live_batch0003_processes(proc_root)
        self.assertEqual([row["pid"] for row in found], [1234])

    def test_stop_after_5m_publishes_stage_and_never_dispatches_later_ordinals(self) -> None:
        now = datetime.now(timezone.utc)
        stage_calls: list[tuple[int, int]] = []
        validator_calls: list[str] = []
        states: list[dict[str, object]] = []

        def fake_stage(_contract, _environment, start, end, *_args) -> None:
            stage_calls.append((start, end))

        with tempfile.TemporaryDirectory() as temporary:
            with (
                mock.patch.object(batch, "FINAL_LEDGER", Path(temporary) / "final.json"),
                mock.patch.object(batch, "STAGE5_LEDGER", Path(temporary) / "stage5.json"),
                mock.patch.object(batch, "_prepare_campaign_roots"),
                mock.patch.object(
                    batch,
                    "_execution_state",
                    return_value={"deadline_utc": (now + timedelta(hours=12)).isoformat()},
                ),
                mock.patch.object(batch, "_run_stage", side_effect=fake_stage),
                mock.patch.object(batch, "_run_stage_validator", side_effect=lambda stage, _d: validator_calls.append(stage)),
                mock.patch.object(batch, "_update_state", side_effect=lambda **values: states.append(values)),
            ):
                result = batch._run({}, {}, 4, now, now + timedelta(hours=12), "5m")
        self.assertEqual(result, 0)
        self.assertEqual(stage_calls, [(1, batch.STAGE5_SHARD_COUNT)])
        self.assertEqual(validator_calls, ["5m"])
        self.assertEqual(states[-1]["status"], "PASS__BATCH0003_STAGE5M_MERGE_ELIGIBLE")


class GammaInstantBatch0003ValidatorPublicationTests(unittest.TestCase):
    def test_receipt_and_ledger_job_keep_consumer_tt_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            validation_path = root / "validation.json"
            receipt_path = root / "receipt.json"
            pair_path = root / "pair.json"
            for path in (validation_path, receipt_path, pair_path):
                path.write_text("{}\n", encoding="utf-8")
            artifacts = {
                key: {"path": f"fake/{key}", "sha256": key * 8}
                for key in ("job_source", "sim", "isotope_dat", "log")
            }
            validation = {
                "geometry": "mass_model_511",
                "ordinal": 1,
                "attempt": 1,
                "events": 25_000,
                "seed": batch.shard_seed(1),
                "TT_s_from_log": 0.5,
                "TT_s_from_isotope_dat": 0.5,
                "flux_cm2_s": 4.8,
                "TT_s_expected_mean_from_events_flux_area": 0.46,
                "TT_authority": batch.TT_AUTHORITY,
                "source_references": {"corrected": 20, "legacy": 0},
                "peak_process_group_rss_bytes": 1,
                "attempt_output_cap_bytes": 500_000_000,
                "frozen_input_bundle_sha256": "a" * 64,
                "sim_scan": {"events": 25_000},
                "isotope_store": {"TT_s": 0.5},
                "artifacts": artifacts,
            }
            receipt = validator._receipt_payload(validation, validation_path)
            job = validator._ledger_job_payload(validation, 1, 1, receipt_path, pair_path)
        for payload in (receipt, job):
            self.assertEqual(float(payload["TT_s_from_isotope_dat"]), 0.5)
            self.assertEqual(float(payload["TT_s_from_log"]), 0.5)
            self.assertGreater(float(payload["flux_cm2_s"]), 0)
            self.assertGreater(float(payload["TT_s_expected_mean_from_events_flux_area"]), 0)
            self.assertEqual(payload["TT_authority"], batch.TT_AUTHORITY)

    def test_artifact_snapshot_detects_change_during_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            paths: dict[str, Path] = {}
            for key in ("attempt_contract", "job_source", "sim", "isotope_dat", "log"):
                path = Path(temporary) / key
                path.write_text("stable\n", encoding="utf-8")
                paths[key] = path
            original_sha256 = validator.smoke.sha256
            changed = False

            def mutating_sha256(path: Path) -> str:
                nonlocal changed
                digest = original_sha256(path)
                if path == paths["sim"] and not changed:
                    path.write_text("changed after hash\n", encoding="utf-8")
                    changed = True
                return digest

            with mock.patch.object(validator.smoke, "sha256", side_effect=mutating_sha256):
                _, problems = validator._artifact_snapshot(paths)
        self.assertTrue(any("sim: artifact changed while hashing" in problem for problem in problems))

    def test_campaign_controls_require_exact_shared_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            campaign_root = Path(temporary) / "campaign"
            campaign_root.mkdir()
            campaign_contract = campaign_root / "batch_contract.json"
            normalization = campaign_root / "normalization.json"
            expected_campaign = {"identity": "frozen"}
            expected_normalization = {"events": 9_899_000, "automatic_delete": False}
            batch.atomic_write_once_json(campaign_contract, expected_campaign)
            batch.atomic_write_once_json(normalization, expected_normalization)
            with (
                mock.patch.object(batch, "campaign_dir", return_value=campaign_root),
                mock.patch.object(batch, "_campaign_contract_payload", return_value=expected_campaign),
                mock.patch.object(batch, "_normalization_payload", return_value=expected_normalization),
            ):
                clean = validator.common.Gate()
                validator._validate_campaign_control_files({}, "mass_model_511", clean)
                self.assertFalse(clean.errors)
                normalization.write_text('{"events":9899000,"automatic_delete":true}\n', encoding="utf-8")
                tampered = validator.common.Gate()
                validator._validate_campaign_control_files({}, "mass_model_511", tampered)
                self.assertTrue(any("normalization payload mismatch" in error for error in tampered.errors))

    def test_pair_receipt_requires_exact_payload_including_selected_attempt(self) -> None:
        expected = {
            "schema_version": 1,
            "batch_id": batch.BATCH_ID,
            "geometry_receipts": {"mass_model_511": {"selected_attempt": 1}},
        }
        tampered = json.loads(json.dumps(expected))
        tampered["geometry_receipts"]["mass_model_511"]["selected_attempt"] = 2
        gate = validator.common.Gate()
        with mock.patch.object(batch, "_pair_receipt_payload", return_value=expected):
            validator._validate_pair_receipt_exact(tampered, 1, "shard0001", gate)
        self.assertTrue(any("pair receipt payload mismatch" in error for error in gate.errors))

    def test_attempt_contract_rejects_extra_or_tampered_provenance(self) -> None:
        expected = {
            "schema_version": 1,
            "status": "FROZEN_ATTEMPT__DYNAMIC_VALIDATION_REQUIRED",
            "frozen_input_bundle_sha256_pre": "a" * 64,
        }
        tampered = dict(expected)
        tampered["unregistered_provenance"] = True
        gate = validator.common.Gate()
        with (
            mock.patch.object(batch, "_job", return_value={}),
            mock.patch.object(batch, "_attempt_contract_payload", return_value=expected),
        ):
            validator._validate_attempt_contract_exact(
                {"transport": {"cosima": "/fake"}}, tampered, "mass_model_511", 1, 1, gate
            )
        self.assertTrue(any("attempt contract payload mismatch" in error for error in gate.errors))

    def test_check_rejects_incomplete_authority_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_path = Path(temporary) / "report.json"
            ledger_path = Path(temporary) / "ledger.json"
            report = {"status": "PASS", "errors": [], "stage": "5m"}
            ledger = {"status": "PASS", "stage": "5m"}
            batch.atomic_write_once_json(ledger_path, {"preplaced": True})
            spec = (1, 5_000_000, report_path, ledger_path, "PASS")
            with (
                mock.patch.object(validator, "_stage_spec", return_value=spec),
                mock.patch.object(validator, "validate_stage", return_value=(report, ledger)),
            ):
                self.assertEqual(validator._write_stage("5m", check=True), 1)

    def test_check_rejects_tampered_existing_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_path = Path(temporary) / "report.json"
            ledger_path = Path(temporary) / "ledger.json"
            report = {"status": "PASS", "errors": [], "stage": "5m"}
            ledger = {"status": "PASS", "stage": "5m"}
            batch.atomic_write_once_json(report_path, report)
            batch.atomic_write_once_json(ledger_path, {"tampered": True})
            spec = (1, 5_000_000, report_path, ledger_path, "PASS")
            with (
                mock.patch.object(validator, "_stage_spec", return_value=spec),
                mock.patch.object(validator, "validate_stage", return_value=(report, ledger)),
            ):
                self.assertEqual(validator._write_stage("5m", check=True), 1)

    def test_failed_stage_does_not_publish_canonical_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_path = Path(temporary) / "report.json"
            ledger_path = Path(temporary) / "ledger.json"
            spec = (1, 5_000_000, report_path, ledger_path, "PASS")
            with (
                mock.patch.object(validator, "_stage_spec", return_value=spec),
                mock.patch.object(
                    validator,
                    "validate_stage",
                    return_value=({"status": "FAIL", "errors": ["bad"]}, {"status": "FAIL"}),
                ),
            ):
                self.assertEqual(validator._write_stage("5m", check=False), 1)
            self.assertFalse(report_path.exists())
            self.assertFalse(ledger_path.exists())

    def test_resume_completes_ledger_after_report_only_crash(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report_path = Path(temporary) / "report.json"
            ledger_path = Path(temporary) / "ledger.json"
            report = {"status": "PASS", "errors": [], "stage": "5m"}
            ledger = {"status": "PASS", "stage": "5m"}
            batch.atomic_write_once_json(report_path, report)
            spec = (1, 5_000_000, report_path, ledger_path, "PASS")
            with (
                mock.patch.object(validator, "_stage_spec", return_value=spec),
                mock.patch.object(validator, "validate_stage", return_value=(report, ledger)),
            ):
                self.assertEqual(validator._write_stage("5m", check=False), 0)
            written = json.loads(ledger_path.read_text(encoding="utf-8"))
            self.assertEqual(written["validation_report_sha256"], batch.smoke.sha256(report_path))


if __name__ == "__main__":
    unittest.main()

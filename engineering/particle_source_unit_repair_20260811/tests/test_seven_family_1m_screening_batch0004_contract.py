from __future__ import annotations

import fcntl
import hashlib
import json
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

import run_mergeable_seven_family_1m_screening_batch0004 as batch  # noqa: E402
import validate_mergeable_seven_family_1m_screening_batch0004 as validator  # noqa: E402


class Batch0004ContractTests(unittest.TestCase):
    def tearDown(self) -> None:
        batch._ABORT_EVENT.clear()
        with batch._ACTIVE_PROCESS_LOCK:
            batch._ACTIVE_PROCESSES.clear()

    @staticmethod
    def _write_prefix76_authority(report_path: Path, ledger_path: Path) -> None:
        campaigns = [
            {
                "geometry": geometry,
                "mode": "instant",
                "family": "gamma",
                "prefix_start_ordinal": 1,
                "prefix_end_ordinal": batch.PREFIX_CHECKPOINT_ORDINAL,
                "cumulative_events": batch.PREFIX_CUMULATIVE_EVENTS_PER_GEOMETRY,
            }
            for geometry in batch.GEOMETRIES
        ]
        common_fields = {
            "batch_id": batch.BATCH0003_ID,
            "campaign_version": "mergeable_gamma_instant_10m_v1",
            "prior_events_per_geometry": batch.PREFIX_PRIOR_EVENTS_PER_GEOMETRY,
            "new_events_per_geometry": batch.PREFIX_NEW_EVENTS_PER_GEOMETRY,
            "cumulative_events_per_geometry": batch.PREFIX_CUMULATIVE_EVENTS_PER_GEOMETRY,
            "validated_pair_count": batch.PREFIX_CHECKPOINT_ORDINAL,
            "global_contract": batch.smoke.rel(batch.BATCH0003_CONTRACT),
            "global_contract_sha256": batch.smoke.sha256(batch.BATCH0003_CONTRACT),
            "validator": batch.smoke.rel(batch.PREFIX_VALIDATOR),
            "validator_sha256": batch.PREFIX_VALIDATOR_SHA256,
            "campaigns": campaigns,
            "errors": [],
        }
        report = {
            **common_fields,
            "status": batch.PREFIX_VALIDATION_STATUS,
            "merge_eligibility": batch.PREFIX_LEDGER_STATUS,
            "selection": {
                "selected_prefix_start_ordinal": 1,
                "selected_prefix_end_ordinal": batch.PREFIX_CHECKPOINT_ORDINAL,
                "complete_contiguous_pairs_required_and_snapshotted":
                    batch.PREFIX_CHECKPOINT_ORDINAL,
                "preferred_ordinal": True,
            },
        }
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        ledger = {
            **common_fields,
            "status": batch.PREFIX_LEDGER_STATUS,
            "validation_status": batch.PREFIX_VALIDATION_STATUS,
            "prefix_start_ordinal": 1,
            "prefix_end_ordinal": batch.PREFIX_CHECKPOINT_ORDINAL,
            "validation_report": batch.smoke.rel(report_path),
            "validation_report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        }
        ledger_path.write_text(
            json.dumps(ledger, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    @staticmethod
    def _write_stage5_authority(report_path: Path, ledger_path: Path) -> None:
        report = {
            "batch_id": batch.BATCH0003_ID,
            "status": "PASS",
            "stage": "5m",
            "cumulative_target_events_per_geometry": 5_000_000,
            "errors": [],
        }
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        ledger = {
            "batch_id": batch.BATCH0003_ID,
            "status": batch.BATCH0003_STATUS,
            "stage": "5m",
            "cumulative_target_events_per_geometry": 5_000_000,
            "validation_report": batch.smoke.rel(report_path),
            "validation_report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
            "errors": [],
        }
        ledger_path.write_text(
            json.dumps(ledger, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def test_exact_schedule_closes_all_screening_targets(self) -> None:
        self.assertEqual(batch.FINAL_SHARD_COUNT, 127)
        self.assertEqual(batch.FINAL_JOB_COUNT, 254)
        self.assertEqual(batch.TOTAL_NEW_EVENTS, 2_395_698)
        rows = batch.planned_shards()
        self.assertEqual(len(rows), 127)
        expected = {
            "gamma_buildup": (101_000, 899_000, 1_000_000, 36, 24_000),
            "n_instant": (9_727, 86_583, 96_310, 18, 1_583),
            "n_buildup": (9_727, 86_583, 96_310, 18, 1_583),
            "eplus_instant": (2_461, 21_909, 24_370, 9, 1_909),
            "eplus_buildup": (2_461, 21_909, 24_370, 9, 1_909),
            "alpha_instant": (241, 2_149, 2_390, 9, 149),
            "alpha_buildup": (241, 2_149, 2_390, 9, 149),
            "eminus_instant": (4_187, 37_273, 41_460, 8, 2_273),
            "eminus_buildup": (4_187, 37_273, 41_460, 8, 2_273),
            "muplus_instant": (117, 1_043, 1_160, 1, 1_043),
            "muplus_buildup": (117, 1_043, 1_160, 1, 1_043),
            "muminus_buildup": (105, 935, 1_040, 1, 935),
        }
        self.assertEqual(tuple(row["key"] for row in batch.STAGE_SPECS), batch.STAGE_ORDER)
        for stage in batch.STAGE_SPECS:
            prior, new, target, shards, last = expected[str(stage["key"])]
            self.assertEqual(
                (stage["prior_events_per_geometry"], stage["new_events_per_geometry"],
                 stage["target_events_per_geometry"], stage["paired_shards"],
                 stage["shard_events"][-1]),
                (prior, new, target, shards, last),
            )
            final = [row for row in rows if row["stage"] == stage["key"]][-1]
            self.assertEqual(final["cumulative_events_per_geometry"], target)
            self.assertEqual(final["checkpoint"], "family_mode_1m_equivalent_screening")

    def test_muminus_instant_is_prior_only_and_never_scheduled(self) -> None:
        self.assertNotIn("muminus_instant", batch.STAGE_ORDER)
        self.assertEqual(batch.PRIOR_EVENTS[("muminus", "instant")], 10_105)
        self.assertGreater(batch.PRIOR_EVENTS[("muminus", "instant")], batch.TARGET_EVENTS["muminus"])
        self.assertFalse(any(row["family"] == "muminus" and row["mode"] == "instant"
                             for row in batch.planned_shards()))

    def test_seed_registry_is_unique_and_disjoint_from_batches_0000_to_0003(self) -> None:
        ledgers = [batch._load_json(path) for path in (
            batch.BATCH0000_LEDGER, batch.BATCH0001_LEDGER, batch.BATCH0002_LEDGER
        )]
        historical = batch._prior_seeds(*ledgers)
        parent = batch._load_json(batch.BATCH0003_CONTRACT)
        historical.update(int(row["seed"])
                          for row in parent["statistics"]["paired_shards"])
        planned = {batch.shard_seed(i) for i in range(1, batch.FINAL_SHARD_COUNT + 1)}
        self.assertEqual(len(planned), batch.FINAL_SHARD_COUNT)
        self.assertTrue(planned.isdisjoint(historical))

    def test_all_selected_cards_are_corrected_and_full_information(self) -> None:
        for geometry in batch.GEOMETRIES:
            for family in batch.FAMILIES:
                text = batch.source_card_path(geometry, family).read_text(encoding="utf-8")
                self.assertEqual(text.count(
                    "engineering/particle_source_unit_repair_20260811/spectra/correct_keV_total/"
                ), 20)
                self.assertNotIn("cosima_spectra_dp_2602units", text)
                self.assertEqual(text.count("StoreSimulationInfo all"), 1)

    def test_preflight_inherits_exact_parent_window_without_extension(self) -> None:
        _, _, _, dependency, _ = batch.run_preflight(
            revalidate_prior=False,
            require_predecessor_authority=False,
            deadline=None,
        )
        started = datetime.fromisoformat(dependency["inherited_started_utc"])
        deadline = datetime.fromisoformat(dependency["inherited_deadline_utc"])
        self.assertEqual((deadline - started).total_seconds(), 12 * 3600)
        parent_state = batch._load_json(batch.BATCH0003_STATE)
        self.assertEqual(started.isoformat(), parent_state["started_utc"])
        self.assertEqual(deadline.isoformat(), parent_state["deadline_utc"])

    def test_predecessor_wait_is_output_free_until_canonical_authority_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prefix_report = root / "prefix_report.json"
            prefix_ledger = root / "prefix_ledger.json"
            stage_report = root / "stage_report.json"
            stage_ledger = root / "stage_ledger.json"
            with mock.patch.object(batch, "PREFIX_REPORT", prefix_report), \
                 mock.patch.object(batch, "PREFIX_LEDGER", prefix_ledger), \
                 mock.patch.object(batch, "BATCH0003_REPORT", stage_report), \
                 mock.patch.object(batch, "BATCH0003_LEDGER", stage_ledger):
                _, _, _, dependency, _ = batch.run_preflight(
                    revalidate_prior=False,
                    require_predecessor_authority=False,
                    deadline=None,
                )
            self.assertEqual(dependency["profile"], "wait")
            self.assertEqual(
                dependency["gate"],
                "WAIT__BATCH0003_PREFIX76_OR_STAGE5_NOT_YET_AUTHORITY",
            )
            self.assertFalse(prefix_report.exists() or prefix_ledger.exists())
            self.assertFalse(stage_report.exists() or stage_ledger.exists())

    def test_canonical_prefix76_is_preferred_and_freezes_exposure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prefix_report = root / "prefix_report.json"
            prefix_ledger = root / "prefix_ledger.json"
            stage_report = root / "stage_report.json"
            stage_ledger = root / "stage_ledger.json"
            with mock.patch.object(batch, "PREFIX_REPORT", prefix_report), \
                 mock.patch.object(batch, "PREFIX_LEDGER", prefix_ledger):
                self._write_prefix76_authority(prefix_report, prefix_ledger)
                with mock.patch.object(batch, "BATCH0003_REPORT", stage_report), \
                     mock.patch.object(batch, "BATCH0003_LEDGER", stage_ledger):
                    _, _, _, dependency, _ = batch.run_preflight(
                        revalidate_prior=False,
                        require_predecessor_authority=True,
                        deadline=None,
                    )
            self.assertEqual(dependency["profile"], "prefix_ordinal76")
            self.assertEqual(
                dependency["gate"], "PASS__BATCH0003_PREFIX76_AUTHORITY_PRESENT"
            )
            self.assertEqual(
                dependency["gamma_exposure"]["cumulative_events_per_geometry"],
                batch.PREFIX_CUMULATIVE_EVENTS_PER_GEOMETRY,
            )
            self.assertFalse(dependency["gamma_exposure"]["credited_to_batch0004_buildup"])
            self.assertEqual(
                dependency["seed_exclusion"]["planned_seed_count"],
                len(batch._load_json(batch.BATCH0003_CONTRACT)["statistics"]["paired_shards"]),
            )

    def test_stage5_fallback_remains_accepted_when_prefix_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            prefix_report = root / "missing_prefix_report.json"
            prefix_ledger = root / "missing_prefix_ledger.json"
            stage_report = root / "stage_report.json"
            stage_ledger = root / "stage_ledger.json"
            with mock.patch.object(batch, "BATCH0003_REPORT", stage_report), \
                 mock.patch.object(batch, "BATCH0003_LEDGER", stage_ledger):
                self._write_stage5_authority(stage_report, stage_ledger)
                with mock.patch.object(batch, "PREFIX_REPORT", prefix_report), \
                     mock.patch.object(batch, "PREFIX_LEDGER", prefix_ledger):
                    _, _, _, dependency, _ = batch.run_preflight(
                        revalidate_prior=False,
                        require_predecessor_authority=True,
                        deadline=None,
                    )
            self.assertEqual(dependency["profile"], "stage5")
            self.assertEqual(
                dependency["gate"], "PASS__BATCH0003_STAGE5_AUTHORITY_PRESENT"
            )
            self.assertEqual(
                dependency["gamma_exposure"]["cumulative_events_per_geometry"], 5_000_000
            )

    def test_actual_contract_creation_requires_predecessor_authority(self) -> None:
        now = datetime.now(timezone.utc)
        fake_contract = {
            "batch_id": batch.BATCH_ID,
            "campaign_version": batch.CAMPAIGN_VERSION,
            "transport": {"cosima": "/fake"},
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                mock.patch.object(batch, "RUN_ROOT", root),
                mock.patch.object(batch, "GLOBAL_CONTRACT", root / "contract.json"),
                mock.patch.object(batch, "EXECUTION_STATE", root / "state.json"),
                mock.patch.object(batch, "FINAL_VALIDATION_REPORT", root / "final_report.json"),
                mock.patch.object(batch, "FINAL_LEDGER", root / "final_ledger.json"),
                mock.patch.object(batch, "CHECKPOINT_ROOT", root / "checkpoints"),
                mock.patch.object(batch, "PAIR_RECEIPT_ROOT", root / "pairs"),
                mock.patch.object(batch, "campaign_dir", side_effect=lambda g, s: root / g / s),
                mock.patch.object(batch, "build_contract", return_value=(fake_contract, {})) as build,
                mock.patch.object(batch, "atomic_write_once_json"),
                mock.patch.object(batch, "_verify_toolchain_and_inputs"),
            ):
                batch._load_or_create_contract(None, 4, now + timedelta(hours=1))
        self.assertTrue(build.call_args.kwargs["require_predecessor_authority"])

    def test_run_dispatches_independent_checkpoints_in_priority_order(self) -> None:
        now = datetime.now(timezone.utc)
        stage_calls: list[tuple[int, int]] = []
        validator_calls: list[str] = []
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                mock.patch.object(batch, "FINAL_LEDGER", root / "final.json"),
                mock.patch.object(batch, "CHECKPOINT_ROOT", root / "checkpoints"),
                mock.patch.object(batch, "_prepare_campaign_roots"),
                mock.patch.object(batch, "_execution_state", return_value={
                    "deadline_utc": (now + timedelta(hours=12)).isoformat()
                }),
                mock.patch.object(batch, "_run_stage",
                                  side_effect=lambda _c, _e, start, end, *_a: stage_calls.append((start, end))),
                mock.patch.object(batch, "_run_stage_validator",
                                  side_effect=lambda stage, _d: validator_calls.append(stage)),
                mock.patch.object(batch, "_revalidate_predecessor_authority"),
                mock.patch.object(batch, "_run_final_validator"),
                mock.patch.object(batch, "_update_state"),
            ):
                self.assertEqual(batch._run({}, {}, 4, now, now + timedelta(hours=12)), 0)
        self.assertEqual(validator_calls, list(batch.STAGE_ORDER))
        self.assertEqual(stage_calls, [
            (int(stage["global_start_ordinal"]), int(stage["global_end_ordinal"]))
            for stage in batch.STAGE_SPECS
        ])

    def test_concurrent_state_updates_are_serialized(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            state_path = Path(temporary) / "state.json"
            with mock.patch.object(batch, "EXECUTION_STATE", state_path), \
                 mock.patch.object(batch, "GLOBAL_CONTRACT", Path(temporary) / "missing.json"):
                batch.atomic_replace_json(state_path, {"status": "RUNNING"})
                threads = [threading.Thread(target=batch._update_state,
                                            kwargs={f"worker_{i}": i}) for i in range(24)]
                for thread in threads:
                    thread.start()
                for thread in threads:
                    thread.join(timeout=5)
                state = json.loads(state_path.read_text(encoding="utf-8"))
        self.assertFalse(any(thread.is_alive() for thread in threads))
        for i in range(24):
            self.assertEqual(state[f"worker_{i}"], i)

    def test_state_rejects_parent_binding_or_deadline_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            global_contract = Path(temporary) / "contract.json"
            global_contract.write_text("{}\n", encoding="utf-8")
            started = datetime(2026, 8, 11, tzinfo=timezone.utc)
            deadline = started + timedelta(hours=12)
            contract = {"execution": {
                "wall_limit_hours": 12.0,
                "frozen_started_utc": started.isoformat(),
                "frozen_deadline_utc": deadline.isoformat(),
                "parent_state_sha256_at_freeze": "a" * 64,
            }}
            state = {
                "started_utc": started.isoformat(),
                "deadline_utc": deadline.isoformat(),
                "global_contract_sha256": batch.smoke.sha256(global_contract),
                "parent_state_sha256": "a" * 64,
            }
            with mock.patch.object(batch, "GLOBAL_CONTRACT", global_contract):
                batch._validate_execution_state(contract, state)
                state["parent_state_sha256"] = "b" * 64
                with self.assertRaisesRegex(RuntimeError, "parent-state"):
                    batch._validate_execution_state(contract, state)

    def test_disk_gate_includes_20gib_reserve_and_active_burst(self) -> None:
        contract = {"execution": {"requested_worker_cap": 4}, "campaigns": []}
        with (
            mock.patch.object(batch, "remaining_point_bytes", return_value=1_000.0),
            mock.patch.object(batch, "_attempt_output_cap_bytes", return_value=500),
            mock.patch.object(batch.shutil, "disk_usage", return_value=SimpleNamespace(free=10**12)),
        ):
            gate = batch.disk_gate(contract, requested_workers=4)
        self.assertEqual(gate["reserve_bytes"], 20 * 1024**3)
        self.assertEqual(gate["active_worker_burst_margin_bytes"], 2_000)
        self.assertEqual(gate["status"], "PASS")

    def test_controller_lock_is_process_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            lock_path = Path(temporary) / "controller.lock"
            with mock.patch.object(batch, "RUN_ROOT", Path(temporary)), \
                 mock.patch.object(batch, "CONTROLLER_LOCK", lock_path):
                first = batch._acquire_controller_lock()
                try:
                    with self.assertRaises(SystemExit):
                        batch._acquire_controller_lock()
                finally:
                    fcntl.flock(first.fileno(), fcntl.LOCK_UN)
                    first.close()

    def test_terminate_process_group_handles_exited_leader(self) -> None:
        leader = SimpleNamespace(pid=424242, poll=lambda: 0, wait=lambda timeout: 0)
        calls: list[int] = []

        def fake_killpg(_pgid: int, signum: int) -> None:
            calls.append(signum)
            if signum == 0:
                raise ProcessLookupError

        with mock.patch.object(batch.os, "killpg", side_effect=fake_killpg):
            batch._terminate_process_group(leader)
        self.assertIn(signal.SIGTERM, calls)


class Batch0004ValidatorTests(unittest.TestCase):
    def test_direct_import_dependency_hash_drift_is_fail_closed(self) -> None:
        expected = batch.toolchain_payload()
        self.assertEqual(
            expected["smoke_runner_helpers"]["path"], batch.smoke.rel(batch.SMOKE_RUNNER)
        )
        self.assertEqual(
            expected["muminus_runner_helpers"]["path"], batch.smoke.rel(batch.MUMINUS_RUNNER)
        )
        contract = {"toolchain": json.loads(json.dumps(expected))}
        clean = validator.common.Gate()
        validator._validate_toolchain_contract_exact(contract, clean)
        self.assertFalse(clean.errors)
        contract["toolchain"]["smoke_runner_helpers"]["sha256"] = "0" * 64
        drift = validator.common.Gate()
        validator._validate_toolchain_contract_exact(contract, drift)
        self.assertTrue(any("exact toolchain" in error for error in drift.errors))

    def test_receipt_and_ledger_keep_tt_and_cell_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            validation_path = root / "validation.json"
            receipt_path = root / "receipt.json"
            pair_path = root / "pair.json"
            for path in (validation_path, receipt_path, pair_path):
                path.write_text("{}\n", encoding="utf-8")
            spec = batch.shard_spec(1)
            artifacts = {key: {"path": f"fake/{key}", "sha256": "a" * 64}
                         for key in ("job_source", "sim", "isotope_dat", "log")}
            validation = {
                "geometry": "mass_model_511", "stage": spec["key"],
                "mode": spec["mode"], "family": spec["family"],
                "ordinal": 1, "stage_ordinal": 1, "attempt": 1,
                "events": batch.shard_events(1), "seed": batch.shard_seed(1),
                "TT_s_from_log": 0.5, "TT_s_from_isotope_dat": 0.5,
                "flux_cm2_s": 4.8, "TT_s_expected_mean_from_events_flux_area": 0.46,
                "TT_authority": batch.TT_AUTHORITY,
                "source_references": {"corrected": 20, "legacy": 0},
                "peak_process_group_rss_bytes": 1,
                "attempt_output_cap_bytes": 500_000_000,
                "frozen_input_bundle_sha256": "a" * 64,
                "sim_scan": {"events": batch.shard_events(1)},
                "isotope_store": {"TT_s": 0.5}, "artifacts": artifacts,
            }
            receipt = validator._receipt_payload(validation, validation_path)
            job = validator._ledger_job_payload(validation, 1, 1, receipt_path, pair_path)
        for payload in (receipt, job):
            self.assertEqual(payload["stage"], "gamma_buildup")
            self.assertEqual(payload["family"], "gamma")
            self.assertEqual(payload["mode"], "buildup")
            self.assertEqual(payload["TT_s_from_log"], 0.5)
            self.assertEqual(payload["TT_s_from_isotope_dat"], 0.5)

    def test_campaign_controls_fail_on_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            expected_campaign = {"identity": "frozen"}
            expected_normalization = {"automatic_delete": False}
            (root / "batch_contract.json").write_text(json.dumps(expected_campaign), encoding="utf-8")
            (root / "normalization.json").write_text(json.dumps(expected_normalization), encoding="utf-8")
            with (
                mock.patch.object(batch, "campaign_dir", return_value=root),
                mock.patch.object(batch, "_campaign_contract_payload", return_value=expected_campaign),
                mock.patch.object(batch, "_normalization_payload", return_value=expected_normalization),
            ):
                clean = validator.common.Gate()
                validator._validate_campaign_control_files({}, "mass_model_511", "gamma_buildup", clean)
                self.assertFalse(clean.errors)
                (root / "normalization.json").write_text('{"automatic_delete":true}', encoding="utf-8")
                tampered = validator.common.Gate()
                validator._validate_campaign_control_files({}, "mass_model_511", "gamma_buildup", tampered)
                self.assertTrue(any("normalization payload mismatch" in error for error in tampered.errors))

    def test_pair_receipt_exactness_rejects_extra_or_selected_attempt_change(self) -> None:
        expected = {"schema_version": 1, "geometry_receipts": {
            "mass_model_511": {"selected_attempt": 1}
        }}
        tampered = json.loads(json.dumps(expected))
        tampered["geometry_receipts"]["mass_model_511"]["selected_attempt"] = 2
        tampered["extra"] = True
        gate = validator.common.Gate()
        with mock.patch.object(batch, "_pair_receipt_payload", return_value=expected):
            validator._validate_pair_receipt_exact(tampered, 1, "global0001", gate)
        self.assertTrue(any("pair receipt payload mismatch" in error for error in gate.errors))

    def test_attempt_contract_exactness_rejects_extra_provenance(self) -> None:
        expected = {"schema_version": 1, "frozen_input_bundle_sha256_pre": "a" * 64}
        tampered = {**expected, "unregistered_provenance": True}
        gate = validator.common.Gate()
        with mock.patch.object(batch, "_job", return_value={}), \
             mock.patch.object(batch, "_attempt_contract_payload", return_value=expected):
            validator._validate_attempt_contract_exact(
                {"transport": {"cosima": "/fake"}}, tampered,
                "mass_model_511", 1, 1, gate,
            )
        self.assertTrue(any("attempt contract payload mismatch" in error for error in gate.errors))

    def test_empty_checkpoint_check_is_fail_closed_and_writes_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                mock.patch.object(batch, "GLOBAL_CONTRACT", root / "missing_contract.json"),
                mock.patch.object(batch, "CHECKPOINT_ROOT", root / "checkpoints"),
                mock.patch.object(batch, "SOURCE_CONTRACT", root / "missing_source.json"),
            ):
                self.assertEqual(validator._write_stage("gamma_buildup", check=True), 1)
                self.assertFalse((root / "checkpoints").exists())

    def test_failed_checkpoint_does_not_publish_canonical_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = {"status": "FAIL", "errors": ["broken"]}
            ledger = {"status": "FAIL_NOT_MERGE_ELIGIBLE"}
            with mock.patch.object(batch, "CHECKPOINT_ROOT", root), \
                 mock.patch.object(validator, "validate_stage", return_value=(report, ledger)):
                self.assertEqual(validator._write_stage("gamma_buildup", check=False), 1)
                self.assertFalse(batch.checkpoint_report_path("gamma_buildup").exists())
                self.assertFalse(batch.checkpoint_ledger_path("gamma_buildup").exists())

    def test_live_pass_checkpoint_check_requires_canonical_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = {"status": "PASS", "errors": []}
            ledger = {"status": "PASS__CHECKPOINT"}
            with mock.patch.object(batch, "CHECKPOINT_ROOT", root), \
                 mock.patch.object(validator, "validate_stage", return_value=(report, ledger)):
                self.assertEqual(validator._write_stage("gamma_buildup", check=True), 1)
                self.assertFalse(batch.checkpoint_report_path("gamma_buildup").exists())
                self.assertFalse(batch.checkpoint_ledger_path("gamma_buildup").exists())

    def test_live_pass_final_check_requires_canonical_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = {"status": "PASS", "errors": []}
            ledger = {"status": "PASS__FINAL"}
            with mock.patch.object(batch, "FINAL_VALIDATION_REPORT", root / "report.json"), \
                 mock.patch.object(batch, "FINAL_LEDGER", root / "ledger.json"), \
                 mock.patch.object(validator, "validate_final", return_value=(report, ledger)):
                self.assertEqual(validator._write_final(check=True), 1)
                self.assertFalse(batch.FINAL_VALIDATION_REPORT.exists())
                self.assertFalse(batch.FINAL_LEDGER.exists())

    def test_final_without_checkpoint_authorities_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with mock.patch.object(batch, "GLOBAL_CONTRACT", root / "missing_contract.json"), \
                 mock.patch.object(batch, "CHECKPOINT_ROOT", root / "checkpoints"):
                report, ledger = validator.validate_final()
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual(ledger["status"], "FAIL_NOT_MERGE_ELIGIBLE")


if __name__ == "__main__":
    unittest.main()

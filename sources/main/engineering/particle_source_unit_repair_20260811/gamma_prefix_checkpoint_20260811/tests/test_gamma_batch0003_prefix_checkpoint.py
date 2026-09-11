#!/usr/bin/env python3

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "code/validate_gamma_batch0003_prefix_checkpoint.py"
)
SPEC = importlib.util.spec_from_file_location("gamma_prefix_checkpoint", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
checkpoint = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = checkpoint
SPEC.loader.exec_module(checkpoint)


def canonical_bytes(payload: dict) -> bytes:
    return (
        json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    ).encode("utf-8")


class PrefixMathTests(unittest.TestCase):
    def test_preferred_prefix_totals_are_exact(self) -> None:
        self.assertEqual(checkpoint.cumulative_events_per_geometry(76), 2_001_000)
        self.assertEqual(checkpoint.cumulative_events_per_geometry(116), 3_001_000)
        self.assertEqual(checkpoint.cumulative_events_per_geometry(156), 4_001_000)

    def test_auto_milestone_and_exact_selection(self) -> None:
        self.assertEqual(checkpoint._select_prefix("auto", 45), 45)
        self.assertEqual(checkpoint._select_prefix("milestone", 76), 76)
        self.assertEqual(checkpoint._select_prefix("milestone", 120), 116)
        self.assertEqual(checkpoint._select_prefix("milestone", 200), 156)
        self.assertEqual(checkpoint._select_prefix("31", 45), 31)
        with self.assertRaises(checkpoint.PrefixValidationError):
            checkpoint._select_prefix("milestone", 75)
        with self.assertRaises(checkpoint.PrefixValidationError):
            checkpoint._select_prefix("46", 45)


class ReceiptDiscoveryTests(unittest.TestCase):
    def _pair_payload(self, ordinal: int, receipt_root: Path) -> dict:
        bindings = {}
        for geometry in checkpoint.batch.GEOMETRIES:
            path = receipt_root / geometry / f"shard{ordinal:04d}" / "receipt.json"
            bindings[geometry] = {
                "path": checkpoint.smoke.rel(path),
                "sha256": "a" * 64,
                "selected_attempt": 1,
            }
        return {
            "schema_version": 1,
            "status": "PASS__PAIRED_SHARD_MERGE_ELIGIBLE",
            "batch_id": checkpoint.batch.BATCH_ID,
            "campaign_version": checkpoint.batch.CAMPAIGN_VERSION,
            "ordinal": ordinal,
            "events_per_geometry": checkpoint.batch.shard_events(ordinal),
            "paired_seed": checkpoint.batch.shard_seed(ordinal),
            "pairing_rule": checkpoint.batch.PAIRING_RULE,
            "statistical_semantics": checkpoint.batch.PAIRING_STATISTICAL_SEMANTICS,
            "geometry_receipts": bindings,
        }

    def test_discovery_stops_at_first_gap_and_does_not_read_later_pair(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pairs = root / "pairs"
            receipts = root / "receipts"
            pairs.mkdir()
            pair1 = self._pair_payload(1, receipts)
            (pairs / "shard0001.json").write_bytes(canonical_bytes(pair1))
            # A malformed shard0003 proves discovery never jumps over missing 0002.
            (pairs / "shard0003.json").write_text("not-json", encoding="utf-8")
            with (
                mock.patch.object(checkpoint.batch, "FINAL_SHARD_COUNT", 5),
                mock.patch.object(
                    checkpoint.batch,
                    "pair_receipt_path",
                    side_effect=lambda ordinal: pairs / f"shard{ordinal:04d}.json",
                ),
                mock.patch.object(
                    checkpoint.batch,
                    "geometry_receipt_path",
                    side_effect=lambda geometry, ordinal: receipts
                    / geometry
                    / f"shard{ordinal:04d}"
                    / "receipt.json",
                ),
            ):
                snapshots = checkpoint.discover_contiguous_pairs()
            self.assertEqual(len(snapshots), 1)
            self.assertEqual(snapshots[0].payload["ordinal"], 1)

    def test_pair_requires_exact_two_geometry_envelope(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            payload = self._pair_payload(1, Path(tmp))
            payload["geometry_receipts"].pop("s3d_o8")
            errors = checkpoint._pair_envelope_errors(payload, 1)
            self.assertTrue(any("geometry keys" in error for error in errors))

    def test_invalid_receipt_is_not_followed_into_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pairs = root / "pairs"
            receipts = root / "receipts"
            pairs.mkdir()
            bindings = {}
            for geometry in checkpoint.batch.GEOMETRIES:
                path = receipts / geometry / "shard0001" / "receipt.json"
                path.parent.mkdir(parents=True)
                invalid = {
                    "schema_version": 1,
                    "status": "NOT_PASS",
                    "selected_attempt": 1,
                }
                raw = canonical_bytes(invalid)
                path.write_bytes(raw)
                bindings[geometry] = {
                    "path": checkpoint.smoke.rel(path),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "selected_attempt": 1,
                }
            pair = {
                "schema_version": 1,
                "status": "PASS__PAIRED_SHARD_MERGE_ELIGIBLE",
                "batch_id": checkpoint.batch.BATCH_ID,
                "campaign_version": checkpoint.batch.CAMPAIGN_VERSION,
                "ordinal": 1,
                "events_per_geometry": checkpoint.batch.shard_events(1),
                "paired_seed": checkpoint.batch.shard_seed(1),
                "pairing_rule": checkpoint.batch.PAIRING_RULE,
                "statistical_semantics": checkpoint.batch.PAIRING_STATISTICAL_SEMANTICS,
                "geometry_receipts": bindings,
            }
            pair_path = pairs / "shard0001.json"
            pair_path.write_bytes(canonical_bytes(pair))
            pair_snapshot = checkpoint._snapshot_file(pair_path, parse_json=True)
            gate = checkpoint.common.Gate()
            with (
                mock.patch.object(
                    checkpoint.batch,
                    "geometry_receipt_path",
                    side_effect=lambda geometry, ordinal: receipts
                    / geometry
                    / f"shard{ordinal:04d}"
                    / "receipt.json",
                ),
                mock.patch.object(
                    checkpoint.stage_validator,
                    "validate_attempt",
                    side_effect=AssertionError("invalid receipt must not be followed"),
                ) as validate_attempt,
            ):
                campaigns, _ = checkpoint._validate_committed_pairs(
                    {}, [pair_snapshot], gate, progress_every=0
                )
            validate_attempt.assert_not_called()
            self.assertTrue(gate.errors)
            self.assertEqual(sum(len(row["jobs"]) for row in campaigns), 0)


class PublicationSafetyTests(unittest.TestCase):
    @staticmethod
    def _authority_fixture(root: Path) -> tuple[dict, dict, Path, Path]:
        report = {"z": 3, "a": {"status": "PASS"}}
        ledger = {"status": checkpoint.MERGE_STATUS, "prefix_end_ordinal": 1}
        with mock.patch.object(checkpoint, "OUTPUT_ROOT", root):
            report_path, ledger_path = checkpoint.output_paths(1)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        return report, ledger, report_path, ledger_path

    def test_write_once_accepts_identical_and_rejects_difference(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "authority.json"
            checkpoint.atomic_write_once_json(path, {"status": "PASS", "n": 1})
            checkpoint.atomic_write_once_json(path, {"status": "PASS", "n": 1})
            with self.assertRaises(checkpoint.PrefixValidationError):
                checkpoint.atomic_write_once_json(path, {"status": "PASS", "n": 2})

    def test_authority_check_rejects_report_compression_or_reordering(self) -> None:
        variants = {
            "compressed": lambda payload: json.dumps(
                payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8"),
            "reordered": lambda payload: (
                json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False)
                + "\n"
            ).encode("utf-8"),
        }
        for label, encoder in variants.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                report, ledger, report_path, ledger_path = self._authority_fixture(root)
                canonical_report_sha = hashlib.sha256(
                    checkpoint._canonical_json_bytes(report)
                ).hexdigest()
                expected_ledger = dict(ledger)
                expected_ledger["validation_report_sha256"] = canonical_report_sha
                report_path.write_bytes(encoder(report))
                ledger_path.write_bytes(
                    checkpoint._canonical_json_bytes(expected_ledger)
                )
                with mock.patch.object(checkpoint, "OUTPUT_ROOT", root):
                    errors = checkpoint._authority_check(report, ledger, 1)
                self.assertTrue(errors)
                self.assertTrue(
                    any("report bytes" in error for error in errors), errors
                )

    def test_authority_check_rejects_noncanonical_ledger_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            report, ledger, report_path, ledger_path = self._authority_fixture(root)
            canonical_report = checkpoint._canonical_json_bytes(report)
            expected_ledger = dict(ledger)
            expected_ledger["validation_report_sha256"] = hashlib.sha256(
                canonical_report
            ).hexdigest()
            report_path.write_bytes(canonical_report)
            ledger_path.write_bytes(
                json.dumps(
                    expected_ledger,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            )
            with mock.patch.object(checkpoint, "OUTPUT_ROOT", root):
                errors = checkpoint._authority_check(report, ledger, 1)
            self.assertTrue(errors)
            self.assertTrue(any("ledger bytes" in error for error in errors), errors)

    def test_failed_revalidation_never_calls_writer(self) -> None:
        fake_pair = checkpoint.FileSnapshot(
            path=Path("/tmp/fake-pair.json"),
            sha256="b" * 64,
            size=1,
            identity=(1, 2, 3, 4),
            payload={},
        )
        failed_report = {"status": "FAIL", "errors": ["fixture failure"]}
        failed_ledger = {"status": checkpoint.FAIL_STATUS, "errors": ["fixture failure"]}
        with (
            mock.patch.object(
                checkpoint, "discover_contiguous_pairs", return_value=[fake_pair]
            ),
            mock.patch.object(
                checkpoint, "_build_outputs", return_value=(failed_report, failed_ledger)
            ),
            mock.patch.object(checkpoint, "atomic_write_once_json") as writer,
        ):
            result, returncode = checkpoint.validate_prefix(
                "auto", check=False, progress_every=0
            )
        self.assertEqual(returncode, 1)
        self.assertFalse(result["authority_written"])
        writer.assert_not_called()

    def test_source_has_no_live_state_or_cosima_execution_path(self) -> None:
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
        attributes = {
            node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
        }
        names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        self.assertNotIn("EXECUTION_STATE", attributes)
        self.assertNotIn("CONTROLLER_LOCK", attributes)
        self.assertNotIn("validate_stage", attributes)
        self.assertNotIn("build_transport_fingerprint", attributes)
        self.assertNotIn("subprocess", names)

    def test_authority_labels_are_explicitly_partial(self) -> None:
        self.assertEqual(
            checkpoint.MERGE_STATUS, "PARTIAL_PREFIX_MERGE_ELIGIBLE"
        )
        self.assertNotIn("FULL", checkpoint.MERGE_STATUS)

    def test_canonical_payload_excludes_dynamic_discovery_extent(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn('"complete_contiguous_pairs_observed_at_entry"', source)
        self.assertNotIn('"requested": requested', source)


if __name__ == "__main__":
    unittest.main()

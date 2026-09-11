from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1]
    / "code"
    / "publish_batch0004_partial_checkpoint.py"
)
SPEC = importlib.util.spec_from_file_location("batch0004_partial_publisher", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
publisher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(publisher)


class PartialPublisherContractTests(unittest.TestCase):
    def test_alpha_scope_is_exact_contiguous_seven_pair_prefix(self) -> None:
        self.assertEqual(publisher.expected_alpha_ordinals(), tuple(range(91, 98)))
        publisher.require_exact_contiguous_ordinals(
            [97, 91, 95, 92, 96, 93, 94], publisher.expected_alpha_ordinals()
        )

    def test_global_scope_is_exact_contiguous_prefix_through_97(self) -> None:
        self.assertEqual(publisher.expected_global_prefix_ordinals(), tuple(range(1, 98)))

    def test_gap_or_extra_ordinal_fails_closed(self) -> None:
        with self.assertRaises(publisher.PublicationError):
            publisher.require_exact_contiguous_ordinals(
                [91, 92, 94, 95, 96, 97], publisher.expected_alpha_ordinals()
            )
        with self.assertRaises(publisher.PublicationError):
            publisher.require_exact_contiguous_ordinals(
                list(range(91, 99)), publisher.expected_alpha_ordinals()
            )

    def test_status_tokens_are_explicitly_partial_and_not_final(self) -> None:
        for status in (publisher.ALPHA_LEDGER_STATUS, publisher.OVERALL_LEDGER_STATUS):
            self.assertIn("PARTIAL", status)
            self.assertNotIn("FINAL", status)
        self.assertNotEqual(
            publisher.OVERALL_LEDGER,
            publisher.batch.FINAL_LEDGER,
        )

    def test_fixed_complete_stage_prefix(self) -> None:
        self.assertEqual(
            publisher.COMPLETE_STAGES,
            (
                "gamma_buildup",
                "n_instant",
                "n_buildup",
                "eplus_instant",
                "eplus_buildup",
            ),
        )
        self.assertEqual(publisher.ALPHA_STAGE, "alpha_instant")

    def test_require_json_equal_rejects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "authority.json"
            path.write_text('{"status":"PASS"}\n', encoding="utf-8")
            publisher._require_json_equal(path, {"status": "PASS"}, "test authority")
            with self.assertRaises(publisher.PublicationError):
                publisher._require_json_equal(path, {"status": "FAIL"}, "test authority")

    def test_expected_hashes_are_sha256(self) -> None:
        for digest in (
            publisher.EXPECTED_SOURCE_CONTRACT_SHA256,
            publisher.EXPECTED_GLOBAL_CONTRACT_SHA256,
            publisher.EXPECTED_RUNNER_SHA256,
            publisher.EXPECTED_VALIDATOR_SHA256,
        ):
            self.assertEqual(len(digest), 64)
            int(digest, 16)


if __name__ == "__main__":
    unittest.main()

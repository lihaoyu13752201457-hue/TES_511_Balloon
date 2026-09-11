from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PACKAGE / "code"))

import build_preload_observer
import preflight_common as common
import preload_observer_validation as observer_validation
import tape_contract


class PreloadObserverTests(unittest.TestCase):
    def _observer_fixture(self, root: Path, arm: str = "F") -> tuple[Path, Path, Path]:
        cell = tape_contract.build_cell_tapes("alpha", "instant", root / "tapes")
        shard = cell["shards"][0]
        tape = common.ROOT / shard["tape_path"]
        sidecar = common.ROOT / shard["root_sidecar_path"]
        roots = tape_contract._parse_rows(sidecar)
        rows = ["\t".join(observer_validation.OBSERVATION_COLUMNS)]
        previous_runtime_internal_time = 0.0
        for index, root_row in enumerate(roots, start=1):
            primary = tape_contract._primary_from_row(root_row)
            runtime_time, previous_runtime_internal_time = tape_contract.runtime_source_time_projection(
                primary.source_time_s, previous_runtime_internal_time
            )
            projected = tape_contract.runtime_projected_primary(
                primary, runtime_source_time_s=runtime_time
            )
            digest = root_row["expected_generated_binary64_sha256"]
            fields = (
                str(index), root_row["stable_root_id"], str(index), arm,
                str(projected.particle), format(projected.excitation_keV, ".17g"),
                format(primary.source_time_s, ".17g"), format(projected.source_time_s, ".17g"),
                *(format(value, ".17g") for value in projected.position_cm),
                *(format(value, ".17g") for value in projected.direction),
                *(format(value, ".17g") for value in projected.polarization),
                format(projected.energy_keV, ".17g"), digest, digest,
            )
            rows.append("\t".join(fields))
        observer = root / "fixture.gpsobs"
        observer.mkdir()
        data = observer / observer_validation.DATA_NAME
        data.write_text("\n".join(rows) + "\n", encoding="utf-8")
        commit = {
            "arm": arm,
            "artifact_is_transport_authority": False,
            "event_count": len(roots),
            "generated_observations_path": observer_validation.DATA_NAME,
            "generated_observations_sha256": common.sha256(data),
            "generated_observations_size_bytes": data.stat().st_size,
            "resolved_original_library_path": observer_validation.PINNED_LIBCOSIMA_PATH,
            "resolved_original_library_sha256": observer_validation.PINNED_LIBCOSIMA_SHA256,
            "schema_version": 2,
            "status": observer_validation.STATUS,
            "tape_root_sidecar_sha256": common.sha256(sidecar),
        }
        (observer / observer_validation.COMMIT_NAME).write_bytes(common.canonical_json_bytes(commit))
        return observer, tape, sidecar

    def test_source_is_mcrun_boundary_read_only_fail_closed_transaction(self) -> None:
        text = build_preload_observer.SOURCE.read_text(encoding="utf-8")
        self.assertEqual(text.count("original(this, event, particleSource);"), 1)
        self.assertIn("RTLD_NEXT", text)
        self.assertIn("GetSimulatedTime()/s", text)
        self.assertIn("particleSource->GetParticlePosition()", text)
        self.assertIn("particleSource->GetParticleMomentumDirection()", text)
        self.assertIn("particleSource->GetParticlePolarization()", text)
        self.assertIn("particleSource->GetParticleEnergy()/keV", text)
        self.assertIn("primary->GetG4code() != definition", text)
        self.assertIn("vertex->GetT0()", text)
        self.assertIn("particleSource->GetParticleTime()", text)
        self.assertIn("TES511_PRELOAD_EXPECTED_LIBCOSIMA", text)
        self.assertIn("TES511_PRELOAD_EXPECTED_LIBCOSIMA_SHA256", text)
        self.assertIn("dladdr(address, &information)", text)
        self.assertIn("gResolvedOriginalLibraryPath != resolvedOrigin", text)
        self.assertIn("M05ObserverPublishDirectoryNoReplaceDurable(", text)
        self.assertIn("PostRenameFsyncFailedQuarantined", (PACKAGE / "code/preload_observer/M05ObserverTransaction.hh").read_text())
        self.assertNotIn("::rename(gStage.c_str(), gFinal.c_str())", text)
        self.assertIn("actual vertex/primary bits differ from the post-GPS getter state", text)
        self.assertIn("static_assert(sizeof(domain) == 26", text)
        self.assertIn("GetNumberOfPrimaryVertex() != before+1", text)
        self.assertIn("GetNumberOfParticle() != 1", text)
        self.assertIn("O_EXCL | O_NOFOLLOW", text)
        self.assertIn("TES511_PRELOAD_ALLOWED_ROOT", text)
        self.assertIn("std::atexit(Finalize)", text)
        self.assertIn("void Finalize() noexcept", text)
        self.assertIn("exception escaped transaction finalizer", text)
        self.assertNotIn("__attribute__((destructor))", text)
        self.assertIn("generated_observations_sha256", text)
        self.assertIn("generated_observations_size_bytes", text)
        self.assertIn("PASS__GENERATED_OBSERVATIONS_ONLY__NOT_JOB_PASS", text)
        self.assertIn("artifact_is_transport_authority", text)
        for token in build_preload_observer.FORBIDDEN_RNG:
            self.assertNotIn(token, text)
        for symbol in (
            "getrandom", "getentropy", "arc4random", "std::random_device", "TRandom",
            "CLHEP::HepRandom", "G4UniformRand",
        ):
            self.assertIsNotNone(build_preload_observer.FORBIDDEN_RNG_SYMBOL_PATTERN.search(symbol))

    def test_compile_only_build_is_hash_bound_and_never_executes_transport(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "preload_build"
            manifest = build_preload_observer.build(output)
            self.assertEqual(manifest["status"], "PASS__PRELOAD_OBSERVER_BUILD_ONLY__NOT_EXECUTED")
            self.assertFalse(manifest["artifact_is_transport_authority"])
            self.assertEqual(manifest["transport_events_launched"], 0)
            self.assertEqual(manifest["runtime_state"], "DORMANT__NO_COSIMA_OR_EVENTLIST_EXECUTION")
            self.assertEqual(manifest["runtime_contract"]["original_call_count"], 1)
            self.assertEqual(
                manifest["runtime_contract"]["rtld_next_origin"]["expected_sha256"],
                build_preload_observer.PINNED[build_preload_observer.LIB_COSIMA],
            )
            self.assertIn("RENAME_NOREPLACE", manifest["runtime_contract"]["transaction"])
            self.assertIn("post-rename parent-fsync", manifest["runtime_contract"]["transaction"])
            self.assertEqual(
                common.sha256(PACKAGE / "code/preload_observer/M05ObserverTransaction.hh"),
                manifest["transaction_header"]["sha256"],
            )
            self.assertTrue(manifest["needed_libCosima_absent"])
            self.assertEqual(manifest["compiler_dependency_mode"], "-MD__INCLUDING_SYSTEM_HEADERS")
            self.assertEqual(
                manifest["actual_compile_mcrun_header"]["lexical_path"],
                str(build_preload_observer.COMPILE_MCRUN_HEADER),
            )
            self.assertTrue(manifest["actual_compile_mcrun_header"]["is_symlink"])
            dependencies = {
                row["lexical_path"]: row for row in manifest["compiler_dependency_closure"]
            }
            self.assertIn(str(build_preload_observer.SOURCE), dependencies)
            self.assertIn(str(build_preload_observer.COMPILE_MCRUN_HEADER), dependencies)
            self.assertGreater(len(dependencies), 10)
            self.assertEqual(
                common.sha256(output / "compile_dependencies.d"),
                manifest["compiler_dependency_file"]["sha256"],
            )
            self.assertIn(
                "outer job receipt atomically binds every preceding artifact and validation",
                manifest["runtime_contract"]["outer_job_completion_required"],
            )
            binary = Path(manifest["binary"]["path"])
            self.assertEqual(common.sha256(binary), manifest["binary"]["sha256"])
            self.assertEqual(
                common.sha256(build_preload_observer.LIB_COSIMA),
                build_preload_observer.PINNED[build_preload_observer.LIB_COSIMA],
            )
            self.assertEqual(common.strict_json(output / "build_manifest.json"), manifest)
            with self.assertRaises(FileExistsError):
                build_preload_observer.build(output)

    def test_generated_observer_transaction_exactly_closes_to_tape_without_transport(self) -> None:
        with tempfile.TemporaryDirectory(dir=PACKAGE) as directory:
            observer, tape, sidecar = self._observer_fixture(Path(directory))
            checked = observer_validation.validate_observer_transaction(
                observer, tape, sidecar, expected_arm="F"
            )
            self.assertEqual(checked["status"], "PASS__OBSERVER_TRANSACTION_ONLY__NOT_JOB_PASS")
            self.assertFalse(checked["artifact_is_transport_authority"])
            self.assertEqual(checked["event_count"], 25)
            self.assertEqual(checked["unique_root_count"], 25)
            self.assertTrue(checked["outer_job_receipt_still_required"])
            self.assertEqual(checked["schema"]["column_count"], 20)

    def test_observer_transaction_rejects_nonfinite_duplicate_key_and_extra_artifact(self) -> None:
        with tempfile.TemporaryDirectory(dir=PACKAGE) as directory:
            observer, tape, sidecar = self._observer_fixture(Path(directory))
            data = observer / observer_validation.DATA_NAME
            lines = data.read_text(encoding="utf-8").splitlines()
            fields = lines[1].split("\t")
            fields[observer_validation.OBSERVATION_COLUMNS.index("observed_energy_keV")] = "nan"
            lines[1] = "\t".join(fields)
            data.write_text("\n".join(lines) + "\n", encoding="utf-8")
            commit_path = observer / observer_validation.COMMIT_NAME
            commit = common.strict_json(commit_path)
            commit["generated_observations_sha256"] = common.sha256(data)
            commit["generated_observations_size_bytes"] = data.stat().st_size
            commit_path.write_bytes(common.canonical_json_bytes(commit))
            with self.assertRaisesRegex(ValueError, "numeric syntax"):
                observer_validation.validate_observer_transaction(
                    observer, tape, sidecar, expected_arm="F"
                )

            observer2, tape2, sidecar2 = self._observer_fixture(Path(directory) / "second")
            commit2 = observer2 / observer_validation.COMMIT_NAME
            value = common.strict_json(commit2)
            raw = common.canonical_json_bytes(value).decode("utf-8").rstrip("\n}")
            commit2.write_text(raw + ',"arm":"F"}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
                observer_validation.validate_observer_transaction(
                    observer2, tape2, sidecar2, expected_arm="F"
                )

            observer3, tape3, sidecar3 = self._observer_fixture(Path(directory) / "third")
            (observer3 / "unexpected.txt").write_text("x\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing/extra"):
                observer_validation.validate_observer_transaction(
                    observer3, tape3, sidecar3, expected_arm="F"
                )


if __name__ == "__main__":
    unittest.main()

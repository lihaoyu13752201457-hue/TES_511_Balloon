from __future__ import annotations

import csv
import errno
import inspect
import json
import os
import subprocess
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


PACKAGE = Path(__file__).resolve().parents[1]
CODE = PACKAGE / "code"
ROOT = PACKAGE.parents[2]
sys.path.insert(0, str(CODE))

import manifest_discovery as discovery
import build_preflight
import preflight_common as common
import rp_validation
import geometry_classification
import representation_schema
import seven_family_projection as projection
import tape_contract


class IdentityTests(unittest.TestCase):
    def test_external_identities_are_immutable(self) -> None:
        path = PACKAGE / "external_sources.json"
        value = common.strict_json(path)
        self.assertEqual(value["schema_version"], 2)
        self.assertIn("TRANSPORT_BLOCKED", value["status"])
        for paper in value["papers"]:
            self.assertRegex(paper["versioned_url"], rf"/abs/{paper['arxiv_id']}v\d+$")
            self.assertRegex(paper["arxiv_version"], r"^v\d+$")
        for source in value["public_code_snapshots"]:
            self.assertRegex(source["commit_sha40"], r"^[0-9a-f]{40}$")
            self.assertIn(source["commit_sha40"], source["immutable_url"])
            self.assertNotIn("/main/", source["immutable_url"])
            self.assertNotIn("/develop/", source["immutable_url"])
        for authority in value["installed_execution_authorities"]:
            local = Path(authority["absolute_path"])
            self.assertTrue(local.is_file())
            self.assertEqual(common.sha256(local), authority["sha256"])
            self.assertEqual(local.stat().st_size, authority["size_bytes"])

    def test_status_is_fail_closed(self) -> None:
        status = common.strict_json(PACKAGE / "EXECUTION_STATUS.json")
        self.assertFalse(status["transport_authorized"])
        self.assertEqual(status["transport_events_launched"], 0)
        self.assertIn("TRANSPORT_BLOCKED", status["status"])


class ManifestOnlyTests(unittest.TestCase):
    def test_geometry_bundle_include_graph_is_exact_and_fail_closed(self) -> None:
        def bundle_for(setup: Path, files: list[Path]) -> dict[str, object]:
            rows = [{"path": str(path), "sha256": common.sha256(path)} for path in files]
            digest_input = "".join(
                f"{row['path']}\0{row['sha256']}\n" for row in sorted(rows, key=lambda value: value["path"])
            )
            return {
                "setup": str(setup),
                "files": rows,
                "file_count": len(rows),
                "bundle_sha256": common.sha256_bytes(digest_input.encode("utf-8")),
                "digest_contract": "SHA256 of sorted path\\0sha256\\n records",
            }

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            setup = root / "fixture.geo.setup"
            main = root / "main.geo"
            material = root / "material.geo"
            setup.write_text("Include main.geo\n", encoding="utf-8")
            main.write_text("Include material.geo\n", encoding="utf-8")
            material.write_text("Name material\n", encoding="utf-8")
            valid = bundle_for(setup, [setup, main, material])
            checked = discovery.verify_geometry_bundle(valid)
            self.assertEqual(checked["include_edge_count"], 2)
            self.assertEqual(checked["include_closure_file_count"], 3)

            extra = root / "unreferenced.geo"
            extra.write_text("Name extra\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "outside the setup Include closure"):
                discovery.verify_geometry_bundle(bundle_for(setup, [setup, main, material, extra]))

            unpinned = root / "unpinned.geo"
            unpinned.write_text("Name unpinned\n", encoding="utf-8")
            main.write_text("Include unpinned.geo\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "not pinned"):
                discovery.verify_geometry_bundle(bundle_for(setup, [setup, main, material]))
            main.write_text("Include fixture.geo.setup\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "cycle"):
                discovery.verify_geometry_bundle(bundle_for(setup, [setup, main]))
            main.write_text("Include $(UNKNOWN)/x.geo\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unknown geometry Include variable"):
                discovery.verify_geometry_bundle(bundle_for(setup, [setup, main]))
            main.write_text("Include *.geo\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "glob"):
                discovery.verify_geometry_bundle(bundle_for(setup, [setup, main]))

    def test_retained_geometry_bundles_have_exact_six_file_include_closure(self) -> None:
        ledger = discovery.load_authority("batch0001")
        bundles = ledger["geometry_bundles"]
        self.assertEqual(len(bundles), 2)
        for bundle in bundles.values():
            checked = discovery.verify_geometry_bundle(bundle)
            self.assertEqual(checked["include_edge_count"], 5)
            self.assertEqual(checked["include_closure_file_count"], 6)

    def test_duplicate_key_json_is_rejected_at_nested_depth(self) -> None:
        with tempfile.TemporaryDirectory(dir=PACKAGE) as directory:
            path = Path(directory) / "duplicate.json"
            path.write_text('{"outer":{"x":1,"x":2}}\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                common.strict_json(path)

    def test_discovery_uses_only_registered_ledgers(self) -> None:
        with (
            mock.patch.object(Path, "glob", side_effect=AssertionError("glob forbidden")),
            mock.patch.object(Path, "rglob", side_effect=AssertionError("rglob forbidden")),
            mock.patch("os.walk", side_effect=AssertionError("walk forbidden")),
            mock.patch("os.scandir", side_effect=AssertionError("scandir forbidden")),
        ):
            authorities = discovery.registered_authorities()
            donor = discovery.resolve_donor("gamma", "instant")
        self.assertEqual(len(authorities), 2)
        self.assertEqual(donor.job["ordinal"], 1)
        self.assertEqual(donor.authority_id, "batch0003_prefix76")

    def test_prefix_is_exact_and_extra_mass_ordinal77_is_excluded(self) -> None:
        ledger = discovery.load_authority("batch0003_prefix76")
        self.assertEqual(len(ledger["pair_receipts"]), 76)
        for campaign in ledger["campaigns"]:
            self.assertEqual([job["ordinal"] for job in campaign["jobs"]], list(range(1, 77)))
        extra = ROOT / (
            "runs/particle_source_unit_repair_20260811/mass_model_511/instant_gamma_batch0003_v1/"
            "shards/shard0077/receipt.json"
        )
        self.assertTrue(extra.is_file())
        all_paths = {job["sim"] for campaign in ledger["campaigns"] for job in campaign["jobs"]}
        self.assertFalse(any("shard0077" in path for path in all_paths))

    def test_bad_selector_and_live_state_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            discovery.resolve_job(
                "batch0003_prefix76", geometry="mass_model_511", mode="instant", family="gamma", ordinal=77
            )
        with self.assertRaises(KeyError):
            discovery.load_authority("gamma_instant_batch0003_v1_state.json")

    def test_parent_traversal_and_symlink_authorities_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            common.repo_path("engineering/../AGENTS.md")
        with tempfile.TemporaryDirectory(dir=PACKAGE) as directory:
            root = Path(directory)
            target = root / "real.json"
            link = root / "linked.json"
            target.write_text("{}\n", encoding="utf-8")
            link.symlink_to(target.name)
            with self.assertRaises(ValueError):
                common.repo_path(link)


class TapeTests(unittest.TestCase):
    def test_stateful_mcrun_time_recurrence_matches_cpp_and_catches_cancellation(self) -> None:
        source = PACKAGE / "tests/cpp/source_time_recurrence_golden.cc"
        geant4 = Path("/home/ubuntu/MEGAlib_Install/megalib-main/external/geant4_v10.02.p03")
        values = (
            2.8352243148788148e-06, 3.2514732268840163e-06,
            1.2651153371484591e-05, 2.9423287941143794e-05,
        )
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "source_time_recurrence_golden"
            subprocess.run([
                "g++", "-std=c++17", "-I" + str(geant4 / "include/Geant4"), str(source),
                "-L" + str(geant4 / "lib"), "-Wl,-rpath," + str(geant4 / "lib"),
                "-lG4clhep", "-o", str(binary),
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            observed = subprocess.run(
                [str(binary), *(format(value, ".17g") for value in values)],
                check=True, text=True, stdout=subprocess.PIPE,
            ).stdout.strip().split()
        previous_internal = 0.0
        expected: list[str] = []
        for value in values:
            seconds, previous_internal = tape_contract.runtime_source_time_projection(
                value, previous_internal
            )
            expected.append(struct.pack(">d", seconds).hex())
        self.assertEqual(observed, expected)
        independent = tape_contract.runtime_source_time_projection(values[-1])[0]
        self.assertNotEqual(struct.pack(">d", independent).hex(), expected[-1])

        changed = 0
        for family, mode in tape_contract.CELL_COUNTS:
            model = tape_contract.load_source_model(family)
            rng = tape_contract.SplitMix64(tape_contract._cell_seed(family, mode))
            global_time = 0.0
            for count in tape_contract.CELL_COUNTS[(family, mode)]:
                shard_offset = global_time
                previous_internal = 0.0
                for _ in range(count):
                    primary = tape_contract._sample_primary(
                        model, rng, global_time_before_s=global_time,
                        shard_time_offset_s=shard_offset,
                    )
                    global_time = primary.global_poisson_time_s
                    stateful, previous_internal = tape_contract.runtime_source_time_projection(
                        primary.source_time_s, previous_internal
                    )
                    independent = tape_contract.runtime_source_time_projection(primary.source_time_s)[0]
                    changed += struct.pack(">d", stateful) != struct.pack(">d", independent)
        self.assertEqual(changed, 5)

    def test_python_runtime_projection_and_digest_match_compiled_cpp_bits(self) -> None:
        source = PACKAGE / "tests/cpp/generated_binary64_golden.cc"
        geant4 = Path("/home/ubuntu/MEGAlib_Install/megalib-main/external/geant4_v10.02.p03")
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "generated_binary64_golden"
            subprocess.run([
                "g++", "-std=c++17", "-I" + str(geant4 / "include/Geant4"), str(source),
                "-L" + str(geant4 / "lib"), "-Wl,-rpath," + str(geant4 / "lib"),
                "-lG4clhep", "-lcrypto", "-o", str(binary),
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            model = tape_contract.load_source_model("gamma")
            vectors = (
                tape_contract.Primary(
                    particle=1, excitation_keV=0.0, source_time_s=0.033692844905283514,
                    global_poisson_time_s=0.033692844905283514,
                    position_cm=(-39.99788999650839, -30.416166832692625, 56.278867982975605),
                    direction=(-0.2471477324612656, 0.9510007329891896, -0.18578375653775303),
                    polarization=(0.0, 0.0, 0.0), energy_keV=33311978.477383174,
                    driver=model.drivers[0].name, bin_index=0,
                    spectrum_path=common.rel(model.drivers[0].spectrum_path),
                    spectrum_sha256=model.drivers[0].spectrum_sha256,
                    sampler_counter_start0=0, sampler_counter_end0=7,
                ),
                tape_contract.Primary(
                    particle=1, excitation_keV=0.0, source_time_s=0.1,
                    global_poisson_time_s=0.1, position_cm=(0.1, -0.2, 60.0),
                    direction=(0.0, 0.0, -1.0000000000000002),
                    polarization=(0.0, 0.0, 0.0), energy_keV=511.0,
                    driver=model.drivers[0].name, bin_index=0,
                    spectrum_path=common.rel(model.drivers[0].spectrum_path),
                    spectrum_sha256=model.drivers[0].spectrum_sha256,
                    sampler_counter_start0=0, sampler_counter_end0=7,
                ),
            )
            for primary in vectors:
                raw = (
                    primary.excitation_keV, primary.source_time_s, *primary.position_cm,
                    *primary.direction, *primary.polarization, primary.energy_keV,
                )
                observed = subprocess.run(
                    [str(binary), str(primary.particle), *(format(value, ".17g") for value in raw)],
                    check=True, text=True, stdout=subprocess.PIPE,
                ).stdout.strip().split()
                runtime = tape_contract.runtime_projected_primary(primary)
                expected_values = (
                    runtime.excitation_keV, runtime.source_time_s, *runtime.position_cm,
                    *runtime.direction, *runtime.polarization, runtime.energy_keV,
                )
                self.assertEqual(observed[:12], [struct.pack(">d", value).hex() for value in expected_values])
                self.assertEqual(observed[12], tape_contract.generated_binary64_hash(primary))

    def test_python_normalization_matches_compiled_clhep_unit_bits(self) -> None:
        source = PACKAGE / "tests/cpp/clhep_unit_golden.cc"
        geant4 = Path("/home/ubuntu/MEGAlib_Install/megalib-main/external/geant4_v10.02.p03")
        with tempfile.TemporaryDirectory() as directory:
            binary = Path(directory) / "clhep_unit_golden"
            subprocess.run([
                "g++", "-std=c++17", "-I" + str(geant4 / "include/Geant4"), str(source),
                "-L" + str(geant4 / "lib"), "-Wl,-rpath," + str(geant4 / "lib"),
                "-lG4clhep", "-o", str(binary),
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            vectors = (
                (0.12345678901234566, -0.7777777777777777, 0.6180339887498949),
                (0.0, 0.0, -1.0000000000000002),
                (-0.30000000000000004, 0.4, -0.8660254037844386),
            )
            for vector in vectors:
                observed = subprocess.run(
                    [str(binary), *(format(value, ".17g") for value in vector)],
                    check=True, text=True, stdout=subprocess.PIPE,
                ).stdout.strip().split()
                expected = [struct.pack(">d", value).hex() for value in tape_contract._normalized(vector)]
                self.assertEqual(observed, expected)

    def _fixture(
        self,
        root: Path,
        *,
        direction: tuple[float, float, float] = (0.0, 0.0, -1.0),
    ) -> tuple[Path, Path]:
        tape = root / "fixture.eventlist"
        sidecar = root / "fixture.roots.tsv"
        model = tape_contract.load_source_model("alpha")
        primary = tape_contract.Primary(
            particle=21, excitation_keV=0.0, source_time_s=0.1, global_poisson_time_s=0.1,
            position_cm=(0.0, 0.0, 60.0), direction=direction,
            polarization=(0.0, 0.0, 0.0), energy_keV=4000.0,
            driver=model.drivers[0].name, bin_index=0,
            spectrum_path=common.rel(model.drivers[0].spectrum_path),
            spectrum_sha256=model.drivers[0].spectrum_sha256,
            sampler_counter_start0=0, sampler_counter_end0=7,
        )
        line = tape_contract._eventlist_line(primary, 1)
        line_sha = common.sha256_bytes(line.encode())
        tuple_sha = tape_contract.generated_tuple_hash(primary)
        row = tape_contract._primary_row(
            primary, model=model, family="alpha", mode="buildup",
            seed=tape_contract._cell_seed("alpha", "buildup"), row_index0=0,
            global_row_index0=0, shard_offset_s=0.0, raw_line_sha256=line_sha,
            eventlist_binary64_sha256=tape_contract.eventlist_binary64_hash(primary),
            generated_binary64_sha256=tape_contract.generated_binary64_hash(primary),
            tuple_sha256=tuple_sha,
        )
        tape.write_text(line + "\n", encoding="utf-8")
        sidecar.write_text(
            "\t".join(tape_contract.SIDECAR_COLUMNS) + "\n"
            + "\t".join(row[column] for column in tape_contract.SIDECAR_COLUMNS) + "\n",
            encoding="utf-8",
        )
        return tape, sidecar

    def test_sidecar_order_and_raw_line_hash(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tape, sidecar = self._fixture(Path(directory))
            self.assertEqual(
                tape_contract.validate_sidecar(
                    tape, sidecar, verify_authorities=False, verify_sampler=False
                )["event_count"],
                1,
            )
            tape.write_text(tape.read_text().replace("4000", "4001"), encoding="utf-8")
            with self.assertRaises(ValueError):
                tape_contract.validate_sidecar(
                    tape, sidecar, verify_authorities=False, verify_sampler=False
                )

    def test_successor_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tape, sidecar = self._fixture(Path(directory))
            tape.write_text(tape.read_text().replace("1 0 21", "1 1 21"), encoding="utf-8")
            with self.assertRaises(ValueError):
                tape_contract.validate_sidecar(
                    tape, sidecar, verify_authorities=False, verify_sampler=False
                )

    def test_tuple_hash_and_sidecar_primary_are_recomputed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tape, sidecar = self._fixture(Path(directory))
            lines = sidecar.read_text(encoding="utf-8").splitlines()
            fields = lines[1].split("\t")
            fields[tape_contract.SIDECAR_COLUMNS.index("expected_generated_tuple_sha256")] = "e" * 64
            sidecar.write_text(lines[0] + "\n" + "\t".join(fields) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                tape_contract.validate_sidecar(
                    tape, sidecar, verify_authorities=False, verify_sampler=False
                )

    def test_binary64_hash_root_hash_and_nonfinite_state_are_recomputed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tape, sidecar = self._fixture(Path(directory))
            lines = sidecar.read_text(encoding="utf-8").splitlines()
            fields = lines[1].split("\t")
            fields[tape_contract.SIDECAR_COLUMNS.index("expected_eventlist_binary64_sha256")] = "e" * 64
            sidecar.write_text(lines[0] + "\n" + "\t".join(fields) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                tape_contract.validate_sidecar(
                    tape, sidecar, verify_authorities=False, verify_sampler=False
                )

            tape, sidecar = self._fixture(Path(directory))
            lines = sidecar.read_text(encoding="utf-8").splitlines()
            fields = lines[1].split("\t")
            fields[tape_contract.SIDECAR_COLUMNS.index("expected_generated_binary64_sha256")] = "e" * 64
            sidecar.write_text(lines[0] + "\n" + "\t".join(fields) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                tape_contract.validate_sidecar(
                    tape, sidecar, verify_authorities=False, verify_sampler=False
                )

            tape, sidecar = self._fixture(Path(directory))
            lines = sidecar.read_text(encoding="utf-8").splitlines()
            fields = lines[1].split("\t")
            fields[tape_contract.SIDECAR_COLUMNS.index("energy_keV")] = "nan"
            sidecar.write_text(lines[0] + "\n" + "\t".join(fields) + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                tape_contract.validate_sidecar(
                    tape, sidecar, verify_authorities=False, verify_sampler=False
                )

    def test_raw_direction_norm_rounding_changes_generated_binary64_bits(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tape, sidecar = self._fixture(
                Path(directory), direction=(0.0, 0.0, -1.0000000000000002)
            )
            row = tape_contract._parse_rows(sidecar)[0]
            self.assertNotEqual(
                row["expected_eventlist_binary64_sha256"],
                row["expected_generated_binary64_sha256"],
            )
            self.assertEqual(
                tape_contract.validate_sidecar(
                    tape, sidecar, verify_authorities=False, verify_sampler=False
                )["event_count"],
                1,
            )
            lines = sidecar.read_text(encoding="utf-8").splitlines()
            fields = lines[1].split("\t")
            raw_index = tape_contract.SIDECAR_COLUMNS.index("expected_eventlist_binary64_sha256")
            generated_index = tape_contract.SIDECAR_COLUMNS.index("expected_generated_binary64_sha256")
            fields[generated_index] = fields[raw_index]
            sidecar.write_text(lines[0] + "\n" + "\t".join(fields) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "normalized generated binary64"):
                tape_contract.validate_sidecar(
                    tape, sidecar, verify_authorities=False, verify_sampler=False
                )

    def test_real_schema_exactly_matches_40_column_validator_contract(self) -> None:
        checked = tape_contract.validate_schema_contract()
        self.assertEqual(checked["status"], "PASS")
        self.assertEqual(checked["column_count"], 40)

    def test_all_seven_source_models_bind_exactly_20_corrected_drivers_and_fluxes(self) -> None:
        for family in tape_contract.PARTICLE_TYPES:
            model = tape_contract.load_source_model(family)
            self.assertEqual(len(model.drivers), 20)
            self.assertEqual([row.bin_index for row in model.drivers], list(range(20)))
            self.assertAlmostEqual(
                sum(row.flux_cm2_s for row in model.drivers), model.total_flux_cm2_s, places=14
            )
            self.assertTrue(all(
                "engineering/particle_source_unit_repair_20260811/spectra/" in common.rel(row.spectrum_path)
                and "cosima_spectra_dp_2602units" not in common.rel(row.spectrum_path)
                for row in model.drivers
            ))

    def test_cell_tape_is_atomic_manifest_only_and_has_four_control_closed_shards(self) -> None:
        with tempfile.TemporaryDirectory(dir=PACKAGE) as directory:
            tape_root = Path(directory) / "tapes"
            result = tape_contract.build_cell_tapes("alpha", "instant", tape_root)
            cell_dir = tape_root / "alpha_instant"
            checked = tape_contract.validate_cell_manifest(cell_dir)
            self.assertEqual(checked["event_count"], 100)
            self.assertEqual(checked["shard_count"], 4)
            self.assertFalse(any(path.name.startswith(".alpha_instant.partial") for path in tape_root.iterdir()))
            self.assertEqual(common.sha256(cell_dir / "cell_manifest.json"), result["cell_manifest_sha256"])
            manifest = common.assert_canonical_json(cell_dir / "cell_manifest.json")
            self.assertEqual(len(manifest["all_20_driver_spectrum_flux_bindings"]), 20)
            self.assertTrue(all(row["pre_registered_outcome_independent_control_count"] >= 3 for row in manifest["shards"]))
            semantics = manifest["source_time_semantics"]
            self.assertEqual(semantics["clock_scope"], "independent_per_family_mode_cell")
            self.assertIn("not one globally coupled timeline", semantics["cross_family_prohibition"])
            self.assertIn("normalized per-family rates", semantics["cross_family_accidental_live"])
            self.assertEqual(
                manifest["precision_contract"]["F_U_observation_status"],
                "PLANNED__COMPILE_ONLY_PRELOAD_OBSERVER__NOT_TRANSPORT_VALIDATED",
            )
            tampered = json.loads(json.dumps(manifest))
            tampered["source_time_semantics"]["clock_scope"] = "global_across_families"
            (cell_dir / "cell_manifest.json").write_bytes(common.canonical_json_bytes(tampered))
            with self.assertRaisesRegex(ValueError, "manifest contract drift"):
                tape_contract.validate_cell_manifest(cell_dir)
            manifest["precision_contract"]["generated_binary64_identity"] = "tampered"
            (cell_dir / "cell_manifest.json").write_bytes(common.canonical_json_bytes(manifest))
            with self.assertRaisesRegex(ValueError, "manifest contract drift"):
                tape_contract.validate_cell_manifest(cell_dir)

    def test_cell_tape_publish_race_never_replaces_concurrent_target(self) -> None:
        with tempfile.TemporaryDirectory(dir=PACKAGE) as directory:
            tape_root = Path(directory) / "tapes"
            real_publish = common.rename_no_replace

            def collide(source: Path, target: Path) -> None:
                target.mkdir(exist_ok=False)
                (target / "concurrent-witness").write_text("untouched\n", encoding="utf-8")
                real_publish(source, target)

            with mock.patch.object(tape_contract, "rename_no_replace", side_effect=collide):
                with self.assertRaises(FileExistsError):
                    tape_contract.build_cell_tapes("alpha", "instant", tape_root)
            self.assertEqual(
                (tape_root / "alpha_instant/concurrent-witness").read_text(encoding="utf-8"),
                "untouched\n",
            )
            self.assertTrue(any(path.name.startswith(".alpha_instant.partial") for path in tape_root.iterdir()))

    def test_cell_tape_postrename_fsync_failure_quarantines_published_name(self) -> None:
        with tempfile.TemporaryDirectory(dir=PACKAGE) as directory:
            tape_root = Path(directory) / "tapes"
            real_publish = common.rename_no_replace
            real_fsync = tape_contract.fsync_directory
            published = False

            def publish(source: Path, target: Path) -> None:
                nonlocal published
                real_publish(source, target)
                published = True

            def fail_after_publish(path: Path) -> None:
                if published and path == tape_root:
                    raise OSError(errno.EIO, "injected directory fsync failure")
                real_fsync(path)

            with mock.patch.object(tape_contract, "rename_no_replace", side_effect=publish), mock.patch.object(
                tape_contract, "fsync_directory", side_effect=fail_after_publish
            ):
                with self.assertRaisesRegex(OSError, "injected directory fsync failure"):
                    tape_contract.build_cell_tapes("alpha", "instant", tape_root)
            self.assertFalse((tape_root / "alpha_instant").exists())
            self.assertTrue((tape_root / "alpha_instant.failed").is_dir())

    def test_missing_or_extra_sidecar_column_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            tape, sidecar = self._fixture(Path(directory))
            lines = sidecar.read_text(encoding="utf-8").splitlines()
            sidecar.write_text("\t".join(lines[0].split("\t")[:-1]) + "\n" + lines[1] + "\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                tape_contract.validate_sidecar(
                    tape, sidecar, verify_authorities=False, verify_sampler=False
                )


class ProjectionTests(unittest.TestCase):
    def test_historical_remaining_and_28_cell_partial_projection(self) -> None:
        value = projection.build_projection()
        self.assertEqual(value["families"], list(projection.FAMILIES))
        self.assertEqual(value["cell_count"], 28)
        self.assertEqual(value["planned_matched_subshards_per_cell"], 4)
        self.assertEqual(value["executed_cell_count"], 0)
        self.assertEqual(value["historical_total"]["events"], 93_353_632)
        self.assertEqual(
            value["historical_total"]["events"]
            - value["remaining_after_pinned_batch0000_through_batch0005"]["remaining_events"],
            value["remaining_after_pinned_batch0000_through_batch0005"]["credited_events"],
        )
        self.assertGreater(value["current_retained_disk"]["bytes"], 0)
        self.assertTrue(value["current_retained_disk"]["included_in_remaining_capacity_accounting"])
        self.assertEqual(
            value["remaining_after_pinned_batch0000_through_batch0005"]
            ["current_retained_plus_new_remaining_retain_all_bytes_point"],
            value["current_retained_disk"]["bytes"]
            + value["remaining_after_pinned_batch0000_through_batch0005"]["retain_all_bytes_point"],
        )
        self.assertEqual(len(value["pinned_credit_authorities"]), 6)
        self.assertIsNone(value["confidence_contract"]["current_disk_upper95_bytes"])
        self.assertIsNone(value["confidence_contract"]["current_reduction_lower95"])
        self.assertIsNone(value["confidence_contract"]["example_impossible_speed_denominator"]["value"])
        for row in value["records"]:
            self.assertIn("fixed_non_sim_bytes_per_job_point", row)
            self.assertIn("sim_bytes_per_event_point", row)
            self.assertIn("calibration_beam_on_elapsed_s", row)
            self.assertIsNone(row["compact_bytes_point"])
            self.assertIsNone(row["disk_upper95_bytes"])
            self.assertIsNone(row["reduction_lower95"])


class PreflightBuilderTests(unittest.TestCase):
    def test_rename_no_replace_does_not_replace_existing_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            target.mkdir()
            (source / "source-witness").write_text("source\n", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                common.rename_no_replace(source, target)
            self.assertTrue((source / "source-witness").is_file())
            self.assertTrue(target.is_dir())
            self.assertEqual(list(target.iterdir()), [])

    def test_rename_no_replace_requires_linux_primitive_without_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            target = root / "target"
            source.mkdir()
            with mock.patch.object(common.ctypes, "CDLL", return_value=object()):
                with self.assertRaisesRegex(OSError, "renameat2") as raised:
                    common.rename_no_replace(source, target)
            self.assertEqual(raised.exception.errno, errno.ENOSYS)
            self.assertTrue(source.is_dir())
            self.assertFalse(target.exists())

    def test_quarantine_directory_skips_all_existing_failure_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.mkdir()
            (root / "source.failed").mkdir()
            (root / f"source.failed.{os.getpid()}").mkdir()
            quarantined = common.quarantine_directory_no_replace(source)
            self.assertEqual(quarantined, root / f"source.failed.{os.getpid()}.1")
            self.assertTrue(quarantined.is_dir())
            self.assertTrue((root / "source.failed").is_dir())
            self.assertTrue((root / f"source.failed.{os.getpid()}").is_dir())

    def test_card_builder_signature_binds_preload_observer(self) -> None:
        parameters = inspect.signature(build_preflight.build_cards_and_jobs).parameters
        self.assertIn("preload_observer", parameters)
        self.assertLess(
            list(parameters).index("shadow"),
            list(parameters).index("preload_observer"),
        )

    def test_formal_shadow_manifest_is_accepted_and_unexecuted(self) -> None:
        shadow = build_preflight.load_shadow_build()
        self.assertEqual(shadow["status"], "PASS__SHADOW_BUILD_ONLY__EXECUTABLE_NOT_RUN")
        self.assertEqual(shadow["transport_events_launched"], 0)
        self.assertEqual(shadow["scorer_rng_undefined_symbol_scan"], "PASS")

    def test_formal_preload_build_and_durable_consumers_are_bound_but_not_transport_authority(self) -> None:
        preload = build_preflight.load_preload_observer_build()
        self.assertEqual(preload["status"], "PASS__PRELOAD_OBSERVER_BUILD_ONLY__NOT_EXECUTED")
        self.assertFalse(preload["artifact_is_transport_authority"])
        self.assertEqual(preload["transport_events_launched"], 0)
        self.assertEqual(preload["sentinel_status"], "NOT_EXECUTED__P12_REMAINS_BLOCKED")
        self.assertGreater(preload["compiler_dependency_count"], 100)
        durable = build_preflight.load_durable_consumer_fixture()
        self.assertEqual(durable["commit_sha256"], build_preflight.DURABLE_CONSUMER_COMMIT_SHA256)
        self.assertEqual(durable["bound_file_count"], 17)
        self.assertEqual(durable["transport_events_launched"], 0)

    def test_preflight_publication_failure_retains_failed_stage_and_never_commits_final(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / ".preflight.stage"
            final = root / "preflight"
            contract_path = root / "benchmark_contract.json"
            stage.mkdir()
            (stage / "preflight_validation.json").write_text("WAIT\n", encoding="utf-8")
            contract = {
                "status": "WAIT__FIXTURE__TRANSPORT_BLOCKED",
                "transport_authorized": False,
                "transport_events_launched": 0,
            }
            with self.assertRaises(RuntimeError):
                build_preflight.publish_wait_contract_then_preflight(
                    stage, final, contract_path, common.canonical_json_bytes(contract),
                    inject_failure_after_contract=True,
                )
            self.assertFalse(final.exists())
            self.assertTrue(contract_path.is_file())
            self.assertTrue((root / ".preflight.stage.failed").is_dir())
            self.assertIn("WAIT__", common.strict_json(contract_path)["status"])

    def test_preflight_publication_race_never_replaces_existing_final_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / ".preflight.stage"
            final = root / "preflight"
            contract_path = root / "benchmark_contract.json"
            stage.mkdir()
            (stage / "preflight_validation.json").write_text("WAIT\n", encoding="utf-8")
            contract = {
                "status": "WAIT__FIXTURE__TRANSPORT_BLOCKED",
                "transport_authorized": False,
                "transport_events_launched": 0,
            }
            real_publish = common.rename_no_replace

            def collide(source: Path, target: Path) -> None:
                target.mkdir(exist_ok=False)
                (target / "concurrent-witness").write_text("untouched\n", encoding="utf-8")
                real_publish(source, target)

            with mock.patch.object(build_preflight, "rename_no_replace", side_effect=collide):
                with self.assertRaises(FileExistsError):
                    build_preflight.publish_wait_contract_then_preflight(
                        stage, final, contract_path, common.canonical_json_bytes(contract)
                    )
            self.assertEqual(
                (final / "concurrent-witness").read_text(encoding="utf-8"), "untouched\n"
            )
            self.assertTrue((root / ".preflight.stage.failed").is_dir())
            self.assertTrue(contract_path.is_file())

    def test_preflight_postrename_fsync_failure_quarantines_final_and_keeps_wait_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stage = root / ".preflight.stage"
            final = root / "preflight"
            contract_path = root / "benchmark_contract.json"
            stage.mkdir()
            (stage / "preflight_validation.json").write_text("WAIT\n", encoding="utf-8")
            contract = {
                "status": "WAIT__FIXTURE__TRANSPORT_BLOCKED",
                "transport_authorized": False,
                "transport_events_launched": 0,
            }
            with mock.patch.object(
                build_preflight, "fsync_directory", side_effect=OSError(errno.EIO, "injected final fsync failure")
            ):
                with self.assertRaisesRegex(OSError, "injected final fsync failure"):
                    build_preflight.publish_wait_contract_then_preflight(
                        stage, final, contract_path, common.canonical_json_bytes(contract)
                    )
            self.assertFalse(final.exists())
            self.assertTrue((root / "preflight.failed").is_dir())
            self.assertTrue(contract_path.is_file())
            self.assertFalse(common.strict_json(contract_path)["transport_authorized"])

    def test_contract_binds_compile_only_F_U_observer_but_keeps_P12_and_N0_blocked(self) -> None:
        value = build_preflight.build_benchmark_contract(
            generated_utc="2026-08-12T00:00:00Z",
            geometries={}, production={}, shadow={}, preload_observer={"status": "BUILD_ONLY"},
            durable_consumer={"status": "FIXTURE_ONLY"}, execution_status={"status": "WAIT"},
            unit_tests={}, representation_mapping={},
            seed_authorities=[], seed_records=[], tape_binding={}, jobs_binding={}, cassette_binding={},
            projection_binding={}, geometry_classification_binding={},
        )
        self.assertEqual(
            value["status"],
            "WAIT__PREFLIGHT_PARTIAL__P12_SENTINEL_AND_N0_BLOCKED__PENDING_INDEPENDENT_REREVIEW",
        )
        self.assertEqual(
            value["equivalence_gates"]["P12_cross_arm_status"],
            "BLOCKED__PRELOAD_OBSERVER_SENTINEL_NOT_EXECUTED_OR_REVIEWED",
        )
        self.assertEqual(
            value["arms"]["F"]["generated_observation_contract"],
            "CANDIDATE__COMPILE_ONLY_MCRUN_POST_GPS_OBSERVER__SENTINEL_NOT_EXECUTED_OR_REVIEWED",
        )
        self.assertEqual(value["planned_execution"]["F_U_preload_observer_bound_job_count"], 224)
        self.assertFalse(value["arms"]["N0"]["runnable"])
        self.assertEqual(value["planned_execution"]["planned_job_count"], 448)
        self.assertEqual(value["planned_execution"]["runnable_job_count"], 0)
        self.assertFalse(value["transport_authorized"])
        self.assertEqual(value["transport_events_launched"], 0)

    def test_execution_status_is_separately_hash_bound_after_formal_tests(self) -> None:
        status = build_preflight.load_execution_status()
        self.assertFalse(status["transport_authorized"])
        self.assertEqual(status["transport_events_launched"], 0)
        self.assertIn("TRANSPORT_BLOCKED_PENDING_INDEPENDENT_REREVIEW", status["status"])

    def test_every_planned_job_is_nonrunnable_until_F_U_P12_is_closed(self) -> None:
        for arm in build_preflight.ARMS:
            readiness = build_preflight.planned_job_readiness(arm)
            self.assertFalse(readiness["runnable_after_independent_authorization"])
            self.assertIn("BLOCKED__", readiness["technical_readiness_status"])
        self.assertIn("P12", build_preflight.planned_job_readiness("F")["technical_readiness_status"])
        self.assertIn("MATCHED_MATRIX", build_preflight.planned_job_readiness("C")["technical_readiness_status"])

    def test_unproven_preload_candidate_is_explicitly_bound_but_nonrunnable(self) -> None:
        observer = (PACKAGE / "code/preload_observer/M05GPSPreloadObserver.cc").read_text()
        builder = (PACKAGE / "code/build_preflight.py").read_text()
        self.assertIn("PASS__GENERATED_OBSERVATIONS_ONLY__NOT_JOB_PASS", observer)
        self.assertIn("artifact_is_transport_authority", observer)
        self.assertIn('"LD_PRELOAD": preload_observer["binary_path"]', builder)
        for name in (
            "TES511_PRELOAD_ARM", "TES511_PRELOAD_TAPE_ROOT_SIDECAR",
            "TES511_PRELOAD_TAPE_ROOT_SIDECAR_SHA256", "TES511_PRELOAD_OUTPUT_PREFIX",
            "TES511_PRELOAD_ALLOWED_ROOT",
            "TES511_PRELOAD_EXPECTED_LIBCOSIMA", "TES511_PRELOAD_EXPECTED_LIBCOSIMA_SHA256",
        ):
            self.assertIn(f'"{name}"', builder)
        self.assertIn("outer atomic job receipt remains mandatory", builder)

    def test_physical_mapping_matches_logical_schema_and_compiled_scorer_headers(self) -> None:
        value = representation_schema.validate_mapping()
        self.assertEqual(value["status"], "PASS__SCORER_HEADERS_MATCH_FROZEN_M05CC_MAPPING")
        self.assertEqual(set(value["physical_table_columns"]), set(representation_schema.CPP_STREAMS))
        self.assertEqual(len(value["physical_table_columns"]["activation"]), 30)
        self.assertIn("touchable_copy_path", value["physical_table_columns"]["pixels"])
        mapping = common.strict_json(PACKAGE / "schema/m05cc_v1.mapping.json")
        self.assertEqual(
            set(mapping["lossless_views"]),
            {"run", "root", "event", "pixel", "deposit_truth", "ia_truth", "ht_truth", "activation", "truth_index", "job_footer"},
        )
        self.assertEqual(common.sha256(PACKAGE / "schema/m05cc_v2.record_schema.json"), value["mapping_sha256"])
        self.assertEqual(common.sha256(PACKAGE / "schema/m05cc_v2.record_schema.json"), value["logical_schema_sha256"])
        self.assertEqual(
            common.sha256(PACKAGE / "schema/active_volume_whitelist_v1.json"),
            value["active_volume_whitelist_sha256"],
        )
        self.assertEqual(common.sha256(PACKAGE / "code/shadow_extensions/M05CompactScorer.cc"), value["scorer_sha256"])

    def test_deterministic_seeds_are_registry_disjoint_and_paired_once(self) -> None:
        registered, authorities = build_preflight.load_registered_seeds()
        first = build_preflight.deterministic_seeds(registered)
        second = build_preflight.deterministic_seeds(registered)
        self.assertEqual(first, second)
        self.assertEqual(len(authorities), 6)
        self.assertEqual(len(first), 56)
        self.assertEqual(len({row["seed"] for row in first}), 56)
        self.assertEqual(
            {(row["family"], row["mode"]) for row in first},
            set(tape_contract.CELL_COUNTS),
        )
        self.assertTrue(all(len(counts) == 4 for counts in tape_contract.CELL_COUNTS.values()))
        self.assertFalse({row["seed"] for row in first} & registered)
        self.assertTrue(all(100_000_000 <= row["seed"] < 1_000_000_000 for row in first))
        self.assertEqual(build_preflight.ARM_ORDER, ("F", "C", "U", "N1"))

    def test_four_shard_arm_order_is_slot_and_pairwise_balanced(self) -> None:
        arms = build_preflight.ARM_ORDER
        for geometry_index in range(2):
            for cell_index in range(14):
                orders = [
                    build_preflight.arm_order_for(geometry_index, cell_index, shard_index)
                    for shard_index in range(4)
                ]
                self.assertEqual({tuple(order) for order in orders}, set(build_preflight.ARM_ORDER_DESIGN))
                for slot in range(4):
                    self.assertEqual({order[slot] for order in orders}, set(arms))
                for left in arms:
                    for right in arms:
                        if left == right:
                            continue
                        self.assertEqual(sum(order.index(left) < order.index(right) for order in orders), 2)

    def test_eventlist_card_has_no_seed_or_continuum_source_and_cli_owns_seed(self) -> None:
        geometry = {
            "bundle_sha256": "a" * 64,
            "setup_absolute_path": "/tmp/frozen.geo.setup",
        }
        text = build_preflight._source_card_text(
            geometry=geometry,
            family="n",
            mode="buildup",
            shard_index=0,
            events=667,
            seed=193048427,
            arm="F",
            tape_absolute=Path("/tmp/frozen.eventlist"),
            output_prefix=Path("/tmp/out"),
        )
        self.assertNotIn("\nSeed ", text)
        self.assertNotIn("Spectrum", text)
        self.assertNotIn(".Flux", text)
        self.assertNotIn(".Beam", text)
        self.assertEqual(text.count("FrozenPrimary.EventList "), 1)
        self.assertIn("DecayMode ActivationBuildUp", text)
        self.assertIn(".IsotopeProductionFile /tmp/out.dat", text)
        argv = build_preflight.transport_argv("/opt/cosima", "F", 193048427, Path("/tmp/frozen.source"))
        self.assertEqual(argv, ["/opt/cosima", "-z", "-s", "193048427", "/tmp/frozen.source"])
        self.assertNotIn("-f", argv)
        self.assertEqual(argv[-1], "/tmp/frozen.source")
        installed = Path("/home/ubuntu/MEGAlib_Install/megalib-main/src/cosima/src/MCMain.cc").read_text()
        self.assertIn('Option == "-s"', installed)
        self.assertIn("m_IncarnationID = atoi(argv[++i])", installed)

    def test_compact_card_disables_native_event_file_but_retains_native_dat(self) -> None:
        geometry = {"bundle_sha256": "b" * 64, "setup_absolute_path": "/tmp/o8.geo.setup"}
        text = build_preflight._source_card_text(
            geometry=geometry,
            family="alpha",
            mode="instant",
            shard_index=2,
            events=33,
            seed=300846559,
            arm="C",
            tape_absolute=Path("/tmp/a.eventlist"),
            output_prefix=Path("/tmp/a"),
        )
        self.assertNotIn(".FileName ", text)
        self.assertIn(".IsotopeProductionFile /tmp/a.m05cc.partial/native", text)
        self.assertNotIn("DecayMode ActivationBuildUp", text)
        argv = build_preflight.transport_argv("/opt/m05cosima", "C", 300846559, Path("/tmp/a.source"))
        self.assertEqual(argv, ["/opt/m05cosima", "-s", "300846559", "/tmp/a.source"])

    def test_cassette_selectors_resolve_only_registered_ledgers(self) -> None:
        self.assertEqual(len(build_preflight.CASSSETTE_SPECS), 11)
        with (
            mock.patch.object(Path, "glob", side_effect=AssertionError("glob forbidden")),
            mock.patch.object(Path, "rglob", side_effect=AssertionError("rglob forbidden")),
            mock.patch("os.walk", side_effect=AssertionError("walk forbidden")),
            mock.patch("os.scandir", side_effect=AssertionError("scandir forbidden")),
        ):
            for spec in build_preflight.CASSSETTE_SPECS:
                selector = {key: spec[key] for key in ("job_name", "ordinal") if key in spec}
                ref = discovery.resolve_job(
                    spec["authority_id"], geometry=spec["geometry"], mode=spec["mode"],
                    family=spec["family"], **selector,
                )
                self.assertIn(ref.authority_id, discovery.AUTHORITY_REGISTRY)
                if ref.authority_id == "batch0003_prefix76":
                    self.assertLessEqual(ref.job["ordinal"], 76)

    def test_builder_source_has_no_recursive_receipt_discovery_or_transport_call(self) -> None:
        source = (CODE / "build_preflight.py").read_text(encoding="utf-8")
        for token in (".glob(", ".rglob(", "os.walk(", "os.scandir(", "subprocess.run("):
            self.assertNotIn(token, source)
        self.assertNotIn("BeamOn(", source)
        self.assertNotIn("rmtree(", source)
        self.assertIn("transport_authorized\": False", source)

    def test_shadow_job_environment_binds_exact_runtime_and_scientific_authorities(self) -> None:
        source = (CODE / "build_preflight.py").read_text(encoding="utf-8")
        required = {
            "TES511_GEOMETRY_BUNDLE_SHA256",
            "TES511_TAPE_ROOT_SIDECAR_SHA256",
            "TES511_RUNTIME_SOURCE_CARD_SHA256",
            "TES511_CORRECTED_SOURCE_CARD_SHA256",
            "TES511_SOURCE_CONTRACT_SHA256",
            "TES511_N1_COMMIT_SCHEMA_SHA256",
        }
        self.assertTrue(all(f'"{name}"' in source for name in required))
        self.assertNotIn('"TES511_SOURCE_CARD_SHA256"', source)
        self.assertIn('"TES511_RUNTIME_SOURCE_CARD_SHA256": checked["sha256"]', source)
        self.assertIn('"TES511_CORRECTED_SOURCE_CARD_SHA256": cell["source_card_sha256"]', source)
        self.assertIn('"TES511_TAPE_ROOT_SIDECAR_SHA256": shard["root_sidecar_sha256"]', source)


class RPTests(unittest.TestCase):
    def _geometry_manifest(self) -> dict[str, object]:
        return {
            "schema_version": geometry_classification.SCHEMA_VERSION,
            "transport_events_launched": 0,
            "geometries": [{
                "geometry": "mass_model_511",
                "records": [{
                    "physical_volume": "PhysicalVolume", "source_volume": "Volume",
                    "runtime_logical_volume": "VolumeLog", "native_dat_volume": "Volume",
                    "material": "Copper", "copy_number": 0,
                    "role": "passive_activation", "active_detector_type": None,
                    "defined_in": "fixture.geo",
                }],
            }],
        }

    def _reconcile(self, activation: Path, dat: Path, footer: Path, roots: Path) -> dict[str, object]:
        return rp_validation.reconcile(
            activation, dat, footer, roots, roots.with_name("tape.tsv"),
            geometry="mass_model_511", geometry_classification=self._geometry_manifest(),
            verify_geometry_authority=False,
        )

    def _write_activation(self, path: Path, rows: list[dict[str, str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, delimiter="\t", fieldnames=rp_validation.REQUIRED_ACTIVATION_FIELDS)
            writer.writeheader()
            writer.writerows(rows)

    def _row(self, serial: int, excitation: str = "0.004") -> dict[str, str]:
        values = {field: "x" for field in rp_validation.REQUIRED_ACTIVATION_FIELDS}
        values.update({
            "simulation_event_id": "1", "stable_root_id": "a" * 64, "eventlist_id": "1",
            "driver": "Atm_alpha_bin00_down", "family": "alpha", "root_weight": "1",
            "production_serial": str(serial), "za": "29064", "z": "29", "a": "64",
            "excitation_keV": excitation,
            "excitation_f64_bits": f"{struct.unpack('>Q', struct.pack('>d', float(excitation)))[0]:016x}",
            "native_dat_volume": "Volume", "physical_volume": "PhysicalVolume", "logical_volume": "VolumeLog",
            "touchable_copy_path": "PhysicalVolume:VolumeLog:0", "material": "Copper",
            "production_x_cm": "1", "production_y_cm": "2",
            "production_z_cm": "3", "production_time_s": "0.01", "track_id": "2",
            "parent_track_id": "1", "primary_track_id": "1", "particle": "neutron",
            "parent_particle": "alpha", "primary_particle": "alpha", "creator_process": "alphaInelastic",
            "step_process": "neutronInelastic", "ancestry_chain": "1:0,2:1",
        })
        return values

    def _write_roots(self, path: Path) -> None:
        tape_values = {field: "0" for field in tape_contract.SIDECAR_COLUMNS}
        tape_values.update({
            "schema": "m05-tape-root-v2", "row_index0": "0", "global_row_index0": "0",
            "eventlist_id": "1", "stable_root_id": "a" * 64,
            "driver": "Atm_alpha_bin00_down", "driver_assignment": "sampled_exact_not_inferred",
            "family": "alpha", "mode": "buildup", "raw_eventlist_line_sha256": "b" * 64,
            "expected_generated_tuple_sha256": "c" * 64, "control_flag": "0",
        })
        with path.with_name("tape.tsv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, delimiter="\t", fieldnames=tape_contract.SIDECAR_COLUMNS)
            writer.writeheader()
            writer.writerow(tape_values)
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, delimiter="\t", fieldnames=rp_validation.REQUIRED_ROOT_FIELDS)
            writer.writeheader()
            writer.writerow({
                "simulation_event_id": "1", "row_index0": "0", "eventlist_id": "1",
                "stable_root_id": "a" * 64, "benchmark_driver_id": "Atm_alpha_bin00_down",
                "driver_inference": "", "driver_inference_quality": "unavailable",
                "driver_inference_ambiguity_set": "[]", "family": "alpha",
                "generated_flag": "1", "started_flag": "1", "native_event_populated": "1",
                "completed_flag": "1", "aborted_flag": "0",
                "raw_tape_line_sha256": "b" * 64, "expected_generated_tuple_sha256": "c" * 64,
                "observed_generated_tuple_sha256": "c" * 64, "observed_ia_init_tuple_sha256": "d" * 64,
                "control_flag": "0",
            })

    def _write_footer(self, path: Path, count: int, tt: float) -> None:
        fields = rp_validation.REQUIRED_FOOTER_FIELDS
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fields)
            writer.writeheader()
            writer.writerow({
                "arm": "C", "geometry": "mass_model_511", "mode": "buildup", "family": "alpha",
                "job_id": "rp_fixture", "shard_index": "0", "seed": "123456789", "tape_count": "1",
                "generated_count": "1", "started_count": "1", "completed_count": "1",
                "native_populated_count": "1", "root_count": "1", "ia_init_count": "1",
                "native_observed_simulation_event_id_count": "1", "native_observed_event_id_count": "1",
                "aborted_count": "0", "rp_row_count": str(count), "TT_s": str(tt),
                "active_block_coverage": "geometry_specific", "veto_whitelist_sha256": "e" * 64,
                "record_schema_sha256": "f" * 64, "finalized": "1",
            })

    def test_rp_one_to_one_and_displayed_state_aggregation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            activation, dat, footer, roots = root / "a.tsv", root / "a.dat", root / "f.tsv", root / "r.tsv"
            self._write_roots(roots)
            self._write_activation(activation, [self._row(1, "0.004"), self._row(2, "0.003")])
            dat.write_text("TT 1.25\nVN Volume\nRP 29064 0.00 2.00000e+00\nEN\n", encoding="utf-8")
            self._write_footer(footer, 2, 1.25)
            self.assertEqual(self._reconcile(activation, dat, footer, roots)["rp_row_count"], 2)
            rows = [self._row(1), self._row(3)]
            self._write_activation(activation, rows)
            with self.assertRaises(ValueError):
                self._reconcile(activation, dat, footer, roots)

    def test_zero_rp_requires_positive_tt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            activation, dat, footer, roots = root / "a.tsv", root / "a.dat", root / "f.tsv", root / "r.tsv"
            self._write_roots(roots)
            self._write_activation(activation, [])
            dat.write_text("TT 2.08885\nEN\n", encoding="utf-8")
            self._write_footer(footer, 0, 2.08885)
            self.assertTrue(self._reconcile(activation, dat, footer, roots)["zero_rp_positive_tt"])
            dat.write_text("TT 0\nEN\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                self._reconcile(activation, dat, footer, roots)

    def test_rp_exact_bits_and_root_join_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            activation, dat, footer, roots = root / "a.tsv", root / "a.dat", root / "f.tsv", root / "r.tsv"
            self._write_roots(roots)
            row = self._row(1)
            row["excitation_f64_bits"] = "0" * 16
            self._write_activation(activation, [row])
            dat.write_text("TT 1.0\nVN Volume\nRP 29064 0.00 1.00000e+00\nEN\n", encoding="utf-8")
            self._write_footer(footer, 1, 1.0)
            with self.assertRaises(ValueError):
                self._reconcile(activation, dat, footer, roots)
            row = self._row(1)
            row["eventlist_id"] = "2"
            self._write_activation(activation, [row])
            with self.assertRaises(ValueError):
                self._reconcile(activation, dat, footer, roots)

    def test_rp_canonical_geometry_classification_join_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            activation, dat, footer, roots = root / "a.tsv", root / "a.dat", root / "f.tsv", root / "r.tsv"
            self._write_roots(roots)
            row = self._row(1)
            row["material"] = "WrongMaterial"
            self._write_activation(activation, [row])
            dat.write_text("TT 1.0\nVN Volume\nRP 29064 0.00 1.00000e+00\nEN\n", encoding="utf-8")
            self._write_footer(footer, 1, 1.0)
            with self.assertRaises(ValueError):
                self._reconcile(activation, dat, footer, roots)

    def test_actual_canonical_geometry_classification_closes(self) -> None:
        manifest = geometry_classification.build_geometry_classification()
        self.assertEqual(manifest["status"], "PASS__DERIVED_FROM_CANONICAL_GEOMETRY_BUNDLES__NO_TRANSPORT")
        self.assertEqual(manifest["transport_events_launched"], 0)
        indexes = {
            geometry: geometry_classification.classification_index(manifest, geometry)
            for geometry in ("mass_model_511", "s3d_o8")
        }
        self.assertTrue(all(name in indexes["mass_model_511"] for name in common.strict_json(
            PACKAGE / "schema/active_volume_whitelist_v1.json"
        )["mass_csi_physical_volumes"]))
        self.assertNotIn("BGO_S3D_O8_FullWrap_BottomCap_30mm", indexes["mass_model_511"])
        checked = geometry_classification.validate_geometry_classification(manifest)
        self.assertTrue(checked["canonical_authority_rebuilt"])


class ShadowHookTests(unittest.TestCase):
    def test_wiring_order_and_rng_absence(self) -> None:
        patch = (PACKAGE / "patches/m05_shadow_hooks.patch").read_text(encoding="utf-8")
        scorer = (PACKAGE / "code/shadow_extensions/M05CompactScorer.cc").read_text(encoding="utf-8")
        self.assertLess(patch.index("M05EventListID = NextSource->GetEventListNextID"), patch.index("NextSource->GenerateParticles"))
        self.assertLess(patch.index("ParticleGun->GetParticleEnergy());"), patch.index("RecordGenerated("))
        self.assertLess(patch.index("AddIsotope(Nucleus, Hist)"), patch.index("RecordCommittedIsotope"))
        self.assertLess(patch.index("M05CompactScorer::Instance().EndEvent("), patch.index("Reset();"))
        self.assertLess(patch.index("SaveIsotopeStore();"), patch.index("EndRun("))
        for token in ("gRandom", "G4UniformRand", "CLHEP::", "RandFlat", "RandGauss", "::shoot(", "drand48(", "random("):
            self.assertNotIn(token, scorer)

    def test_patch_dry_run(self) -> None:
        upstream = Path("/home/ubuntu/MEGAlib_Install/megalib-main/src/cosima")
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            subprocess.run(["cp", "-a", str(upstream / "inc"), str(target / "inc")], check=True)
            subprocess.run(["cp", "-a", str(upstream / "src"), str(target / "src")], check=True)
            subprocess.run(
                ["patch", "--dry-run", "--batch", "--fuzz=0", "-p1", "-i", str(PACKAGE / "patches/m05_shadow_hooks.patch")],
                cwd=target,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )


if __name__ == "__main__":
    unittest.main()

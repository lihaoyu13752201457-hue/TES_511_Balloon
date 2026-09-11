from __future__ import annotations

import re
import subprocess
import tempfile
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
EXT = PACKAGE / "code/shadow_extensions"
PRELOAD = PACKAGE / "code/preload_observer"
PATCH = PACKAGE / "patches/m05_shadow_hooks.patch"
UPSTREAM = Path("/home/ubuntu/MEGAlib_Install/megalib-main/src/cosima")


class ShadowFeedback02ContractTest(unittest.TestCase):
    def _compile_and_run(self, name: str, extra_sources: tuple[Path, ...] = ()) -> str:
        source = PACKAGE / "tests/cpp" / f"test_{name}.cc"
        with tempfile.TemporaryDirectory(prefix=f"m05_{name}_", dir="/tmp") as directory:
            root = Path(directory)
            binary = root / f"test_{name}"
            command = [
                "g++", "-std=c++14", "-Wall", "-Wextra", "-pedantic",
                "-I", str(EXT), "-I", str(PRELOAD), str(source), *(str(path) for path in extra_sources),
            ]
            if name == "durable_file":
                command.extend(["-DM05_DURABLE_TEST_HOOKS", "-lcrypto"])
            command.extend(["-o", str(binary)])
            subprocess.run(command, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            argv = [str(binary)]
            if name in ("durable_file", "observer_transaction"):
                fixture = root / "durable_fixture"
                fixture.mkdir()
                argv.append(str(fixture))
            completed = subprocess.run(
                argv, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )
            return completed.stdout

    def test_compiled_lifecycle_fixture(self) -> None:
        self.assertIn("PASS lifecycle_state_nontransport", self._compile_and_run("lifecycle_state"))

    def test_compiled_veto_fixture(self) -> None:
        self.assertIn("PASS veto_policy_nontransport", self._compile_and_run("veto_policy"))

    def test_compiled_durable_file_fixture(self) -> None:
        self.assertIn(
            "PASS durable_file_nontransport",
            self._compile_and_run("durable_file", (EXT / "M05DurableFile.cc",)),
        )
        scorer = (EXT / "M05CompactScorer.cc").read_text(encoding="utf-8")
        self.assertIn(
            "M05DurableFile::PublishDirectoryDurableNoReplace(m_StageDirectory, m_FinalDirectory)",
            scorer,
        )

    def test_compiled_observer_transaction_fixture(self) -> None:
        self.assertIn(
            "PASS observer_transaction_nontransport",
            self._compile_and_run("observer_transaction"),
        )

    def test_lifecycle_hook_source_order(self) -> None:
        patch = PATCH.read_text(encoding="utf-8")
        begin = patch.index("BeginGeneratedEvent(Event->GetEventID()+1)")
        consume = patch.index("GenerationSuccessful = NextSource->GenerateParticles(ParticleGun)")
        record = patch.index("M05CompactScorer::Instance().RecordGenerated(")
        before = patch.index("M05VertexCountBefore = Event->GetNumberOfPrimaryVertex()")
        upstream = Path("/home/ubuntu/MEGAlib_Install/megalib-main/src/cosima/src/MCRun.cc").read_text(
            encoding="utf-8"
        )
        native_consume = upstream.index("GenerationSuccessful = NextSource->GenerateParticles(ParticleGun)")
        native_vertex = upstream.index("ParticleGun->GeneratePrimaryVertex(Event)")
        native_ia_tail = upstream.index("ParticleGun->GetParticleEnergy());", native_vertex)
        self.assertLess(begin, before)
        self.assertLess(begin, consume)
        self.assertLess(consume, record)
        self.assertLess(native_consume, native_vertex)
        self.assertLess(native_vertex, native_ia_tail)
        self.assertIn(
            "ParticleGun->GetParticleEnergy());\n+      if (M05CompactScorer::Instance().IsConfigured())",
            patch,
        )
        self.assertIn("M05VertexCountBefore,", patch)
        scorer = (EXT / "M05CompactScorer.cc").read_text(encoding="utf-8")
        for actual_gate in (
            "generatedEvent->GetNumberOfPrimaryVertex() == vertexIndex+1",
            "vertex->GetNumberOfParticle() == 1",
            "primary->GetG4code() == particleSource->GetParticleDefinition()",
            "actual G4PrimaryVertex/G4PrimaryParticle bits differ",
        ):
            self.assertIn(actual_gate, scorer)
        self.assertIn("ConfirmEventStarted(m_ID)", patch)
        self.assertLess(patch.index(".EndEvent("), patch.index("Reset();"))
        self.assertGreater(
            patch.index("M05NativeEventPopulated = true"),
            patch.index('Storing uncalibrated data is no longer supported'),
        )

    def test_patch_is_exact_current_tree_zero_fuzz(self) -> None:
        completed = subprocess.run(
            ["patch", "--dry-run", "--fuzz=0", "--batch", "--forward", "-p1", "-i", str(PATCH)],
            cwd=UPSTREAM, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        )
        self.assertNotRegex(completed.stdout.lower(), r"offset|fuzz|failed|reversed|previously applied")

    def test_post_initialize_gate_and_signal_quarantine(self) -> None:
        main = (EXT / "M05Cosima.cc").read_text(encoding="utf-8")
        self.assertLess(main.index("ParseCommandLine"), main.index("Initialize()"))
        self.assertLess(main.index("Initialize()"), main.index("ConfigureAfterInitialization"))
        self.assertLess(main.index("ConfigureAfterInitialization"), main.index("Execute()"))
        self.assertIn("g_Main->GetSeed()", main)
        self.assertIn("NotifyTerminationSignal", main)
        handler = main[main.index("void CatchSignal"):main.index("int main(")]
        self.assertIn("::_exit(128 + signal)", handler)
        for unsafe in ("std::cerr", "g_Main->Interrupt", "std::abort", "g_NInterrupts"):
            self.assertNotIn(unsafe, handler)
        scorer = (EXT / "M05CompactScorer.cc").read_text(encoding="utf-8")
        for gate in (
            "GetNRuns() == 1", "c_PreTriggerEverything", "c_StoreSimulationInfoAll",
            "StoreOneHitPerEvent() == false", "termination signal observed; publication quarantined",
        ):
            self.assertIn(gate, scorer)

    def test_single_thread_only(self) -> None:
        sources = "\n".join(path.read_text(encoding="utf-8") for path in EXT.glob("*.*"))
        self.assertNotIn("G4MTRunManager", sources)
        self.assertIn("!G4Threading::IsMultithreadedApplication()", sources)
        run_manager = (UPSTREAM / "inc/MCRunManager.hh").read_text(encoding="utf-8")
        self.assertIn("class MCRunManager : public G4RunManager", run_manager)

    def test_n1_observes_every_generated_tuple_transactionally(self) -> None:
        scorer = (EXT / "M05CompactScorer.cc").read_text(encoding="utf-8")
        open_pos = scorer.index('m_GeneratedObservationOut.OpenExclusive')
        compact_pos = scorer.index("if (IsCompactArm())", open_pos)
        self.assertLess(open_pos, compact_pos)
        self.assertIn(r'\"generated_observations\"', scorer)
        self.assertIn(r'\"schema_version\":\"m05cc-n1-v1-commit\"', scorer)
        self.assertIn(r'\"status\":\"PASS__N1_TRANSACTION_COMPLETE\"', scorer)
        self.assertIn('WriteDurableExclusive(m_StageDirectory + "/commit.json"', scorer)
        self.assertNotIn(r'\"schema_version\":1,\"status\":\"PASS__TRANSACTION_COMPLETE\"', scorer)
        self.assertIn("m_GeneratedObservationRowCount == static_cast<long>(m_Tape.size())", scorer)
        self.assertLess(scorer.index("CloseDurable"), scorer.index("PublishTransaction();"))

    def test_required_environment_and_native_dat_contract(self) -> None:
        scorer = (EXT / "M05CompactScorer.cc").read_text(encoding="utf-8")
        required = set(re.findall(r'RequiredEnvironment\("([A-Z0-9_]+)"\)', scorer))
        self.assertEqual(required, {
            "TES511_SMOKE_ARM", "TES511_GEOMETRY", "TES511_MODE", "TES511_FAMILY",
            "TES511_JOB_ID", "TES511_SHARD_INDEX", "TES511_SEED", "TES511_TAPE_ROOT_SIDECAR",
            "TES511_OUTPUT_PREFIX", "TES511_ALLOWED_RUN_DIRECTORY", "TES511_RECORD_SCHEMA_SHA256",
            "TES511_N1_COMMIT_SCHEMA_SHA256",
            "TES511_VETO_WHITELIST_SHA256", "TES511_GEOMETRY_CLASSIFICATION_SHA256",
            "TES511_GEOMETRY_BUNDLE_SHA256", "TES511_TAPE_ROOT_SIDECAR_SHA256",
            "TES511_RUNTIME_SOURCE_CARD_SHA256", "TES511_CORRECTED_SOURCE_CARD_SHA256",
            "TES511_SOURCE_CONTRACT_SHA256",
        })
        self.assertIn('m_StageDirectory + "/native"', scorer)
        self.assertIn('expectedNativeDat << ".inc" << incarnationID << ".dat"', scorer)
        self.assertIn("parameters.GetFileName().ToString()", scorer)
        self.assertIn("actual parsed runtime source card differs from harness identity", scorer)
        self.assertIn("actual parsed command-line seed differs from harness identity", scorer)

    def test_observed_binary64_is_a_gate_and_precision_schema_is_v2(self) -> None:
        scorer = (EXT / "M05CompactScorer.cc").read_text(encoding="utf-8")
        self.assertIn("observedBinary64 == row.expectedGeneratedBinary64SHA256", scorer)
        self.assertNotIn("observedBinary64 == row.expectedEventListBinary64SHA256", scorer)
        self.assertIn('"expected_generated_binary64_sha256"', scorer)
        self.assertIn("serialized_ia_position_energy_abs_tolerance", scorer)
        self.assertIn("serialized_ia_direction_polarization_abs_tolerance", scorer)
        self.assertIn("GENERATED_BINARY64_BE_V1__IA_SERIALIZED_17G_FIELD_TOL_V2", scorer)


if __name__ == "__main__":
    unittest.main()

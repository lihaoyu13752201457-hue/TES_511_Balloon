from __future__ import annotations

import gzip
import json
import os
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal, localcontext
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[4]
P0_ROOT = ROOT / "engineering/particle_source_unit_repair_20260811/proton_p0_sixband_pilot_20260812"
CODE = P0_ROOT / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

import build_proton_p0_sixband_sources as builder  # noqa: E402
import launch_cosima_with_limits as launcher  # noqa: E402
import p0_common as p0  # noqa: E402
import run_proton_p0_sixband_pilot as runner  # noqa: E402
import validate_proton_p0_sixband_pilot as validator  # noqa: E402


def strict_stdout_json(text: str) -> dict[str, object]:
    payload = json.loads(
        text,
        parse_constant=lambda token: (_ for _ in ()).throw(
            ValueError(f"non-finite JSON token {token}")
        ),
    )
    if not isinstance(payload, dict):
        raise AssertionError("CLI JSON root is not an object")
    return payload


def fake_manifest() -> dict[str, object]:
    edges = ("11.294", "10000", "30000", "100000", "300000", "1000000", "897160000")
    fluxes = (
        "0.01",
        "0.01",
        "0.01",
        "0.01",
        "0.01",
        "0.0623007216313341",
    )
    weights = ("0.1", "0.1", "0.1", "0.1", "0.1", "0.5")
    return {
        "bands": [
            {
                "index": index,
                "key": f"b{index}",
                "low_keV": edges[index],
                "high_keV": edges[index + 1],
                "high_inclusive": index == 5,
                "flux_cm2_s": fluxes[index],
                "weight": weights[index],
            }
            for index in range(6)
        ]
    }


class ProtonP0SixBandPreparationTests(unittest.TestCase):
    def test_main_print_plan_wait_is_output_free(self) -> None:
        self.assertFalse(p0.SOURCE_MANIFEST.exists(), "test is specific to the current WAIT gate")
        authority_paths = (
            runner.GLOBAL_CONTRACT,
            runner.EXECUTION_STATE,
            runner.FINAL_REPORT,
            runner.FINAL_LEDGER,
        )
        before = {path: path.exists() for path in authority_paths}
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        result = subprocess.run(
            [sys.executable, str(runner.THIS_FILE), "--print-plan"],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = strict_stdout_json(result.stdout)
        self.assertEqual(payload["status"], "WAIT__P0_SIXBAND_SCIENCE_CONTRACT_NOT_FROZEN")
        self.assertIs(payload["transport_launched"], False)
        self.assertEqual(payload["jobs"], 96)
        self.assertEqual(payload["primaries"], 6144)
        self.assertEqual(before, {path: path.exists() for path in authority_paths})

    def test_builder_print_plan_wait_writes_no_source_artifacts(self) -> None:
        self.assertFalse(builder.SCIENCE_CONTRACT.exists(), "test is specific to the current WAIT gate")
        watched = (
            p0.SOURCE_MANIFEST,
            P0_ROOT / "spectra/conditional_keV_total",
            P0_ROOT / "config/source_cards",
        )
        before = {path: path.exists() for path in watched}
        env = dict(os.environ)
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        result = subprocess.run(
            [sys.executable, str(builder.THIS_FILE), "--print-plan"],
            cwd=ROOT,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 3, result.stderr)
        payload = strict_stdout_json(result.stdout)
        self.assertEqual(payload["status"], "WAIT__P0_SIXBAND_SCIENCE_CONTRACT_NOT_FROZEN")
        self.assertIs(payload["transport_launched"], False)
        self.assertEqual(before, {path: path.exists() for path in watched})

    def test_schedule_is_exactly_96_jobs_and_6144_primaries(self) -> None:
        manifest = fake_manifest()
        cells = runner.cells(manifest)
        jobs = runner.jobs(manifest)
        self.assertEqual(len(cells), 24)
        self.assertEqual(len(jobs), p0.JOB_COUNT)
        self.assertEqual(sum(int(row["events"]) for row in jobs), p0.PRIMARY_COUNT)
        self.assertEqual([int(row["job_ordinal"]) for row in jobs], list(range(1, 97)))
        self.assertEqual({int(row["events"]) for row in jobs}, {64})
        self.assertEqual({int(row["shard"]) for row in jobs}, {1, 2, 3, 4})
        self.assertEqual({str(row["geometry"]) for row in jobs}, set(p0.GEOMETRIES))
        self.assertEqual({str(row["mode"]) for row in jobs}, set(p0.MODES))
        self.assertEqual({str(row["band"]) for row in jobs}, {f"b{i}" for i in range(6)})

    def test_seed_schedule_is_unique_and_deterministic(self) -> None:
        jobs = runner.jobs(fake_manifest())
        seeds = [int(row["seed"]) for row in jobs]
        expected = [runner.SEED_BASE + runner.SEED_STRIDE * ordinal for ordinal in range(1, 97)]
        self.assertEqual(seeds, expected)
        self.assertEqual(len(seeds), len(set(seeds)))
        self.assertTrue(all(seed > 0 for seed in seeds))

    def test_prior_operational_pair_seed_duplicates_are_reserved_not_rejected(self) -> None:
        reserved = runner._prior_seed_registry(fake_manifest())
        planned = {int(row["seed"]) for row in runner.jobs(fake_manifest())}
        self.assertTrue(reserved)
        self.assertFalse(planned & reserved)

    def test_decimal_parent_flux_and_six_band_residual_close_exactly(self) -> None:
        edges = tuple(
            Decimal(value)
            for value in ("11.294", "10000", "30000", "100000", "300000", "1000000", "897160000")
        )
        aggregate = [Decimal(0) for _ in range(6)]
        with localcontext() as context:
            context.prec = 70
            for geometry in p0.GEOMETRIES:
                records = p0.parent_card_records(p0.PARENT_SOURCE[geometry])
                self.assertEqual(sum(records["flux"].values(), Decimal(0)), p0.TOTAL_FLUX_DECIMAL)
            records = p0.parent_card_records(p0.PARENT_SOURCE["mass_model_511"])
            for angular_bin in range(20):
                points = p0.parse_dp_decimal(records["spectra"][angular_bin])
                self.assertEqual((points[0][0], points[-1][0]), (edges[0], edges[-1]))
                total_integral = p0.integrate_linear(points)
                integrals = [
                    p0.integrate_linear(points, low, high)
                    for low, high in zip(edges, edges[1:])
                ]
                self.assertLessEqual(
                    abs(sum(integrals, Decimal(0)) - total_integral),
                    max(abs(total_integral), Decimal(1)) * Decimal("1e-60"),
                )
                integrals[-1] = total_integral - sum(integrals[:5], Decimal(0))
                self.assertGreater(integrals[-1], 0)
                self.assertEqual(sum(integrals, Decimal(0)), total_integral)
                parent_flux = records["flux"][angular_bin]
                partial = [parent_flux * value / total_integral for value in integrals[:5]]
                partial.append(parent_flux - sum(partial, Decimal(0)))
                self.assertTrue(all(value > 0 for value in partial))
                self.assertEqual(sum(partial, Decimal(0)), parent_flux)
                for index, value in enumerate(partial):
                    aggregate[index] += value
        self.assertEqual(sum(aggregate, Decimal(0)), p0.TOTAL_FLUX_DECIMAL)
        self.assertNotEqual(p0.TOTAL_FLUX_DECIMAL, Decimal("0.112300721631334"))

    def test_in_memory_builder_serialization_closes_without_publication(self) -> None:
        edges = tuple(
            Decimal(value)
            for value in ("11.294", "10000", "30000", "100000", "300000", "1000000", "897160000")
        )
        with tempfile.TemporaryDirectory() as temporary:
            fake_science = Path(temporary) / "science.json"
            fake_science.write_text("{}\n", encoding="utf-8")
            with mock.patch.object(builder, "SCIENCE_CONTRACT", fake_science):
                payload, files = builder.derive_payload(edges, output_root=p0.P0_ROOT)
        self.assertEqual(len(files), 132)
        with localcontext() as context:
            context.prec = 400
            self.assertEqual(
                sum((Decimal(row["flux_cm2_s"]) for row in payload["bands"]), Decimal(0)),
                p0.TOTAL_FLUX_DECIMAL,
            )
        for geometry in p0.GEOMETRIES:
            for card in payload["geometries"][geometry]["band_source_cards"]:
                text = files[p0.resolve_path(card["path"])].decode("utf-8")
                values = [
                    Decimal(match.group("value"))
                    for line in text.splitlines()
                    if (match := p0.FLUX_RE.match(line.strip()))
                ]
                with localcontext() as context:
                    context.prec = 400
                    self.assertEqual(sum(values, Decimal(0)), Decimal(card["partial_flux_cm2_s"]))
        self.assertFalse(p0.SOURCE_MANIFEST.exists())

    def test_strict_json_rejects_nonfinite_and_nonobject_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid = root / "valid.json"
            valid.write_text('{"value": 1}\n', encoding="utf-8")
            self.assertEqual(p0.load_json_strict(valid), {"value": 1})
            for name, text in (
                ("nan.json", '{"value": NaN}\n'),
                ("infinity.json", '{"value": Infinity}\n'),
                ("array.json", '[1, 2, 3]\n'),
                ("trailing.json", '{"value": 1} trailing\n'),
            ):
                path = root / name
                path.write_text(text, encoding="utf-8")
                with self.assertRaises(RuntimeError, msg=name):
                    p0.load_json_strict(path)

    def test_generic_source_patcher_preserves_cut_and_physics_lines(self) -> None:
        generic = runner._load_generic_runner()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "parent.source"
            target = root / "derived.source"
            protected = (
                "PhysicsListEM LivermorePol",
                "PhysicsListEMRangeCut 0.01",
                "TestProductionCut 0.02",
            )
            source.write_text(
                "Geometry example.geo\n"
                + "\n".join(protected)
                + "\nSeed 1\nRun P0\nP0.Events 1\nP0.FileName old\n",
                encoding="utf-8",
            )
            generic.patch_source(
                {
                    "source": str(source),
                    "temp_source": str(target),
                    "mode": "instant",
                    "store_isotopes": True,
                    "seed": 99,
                    "events": 64,
                    "sim_prefix": str(root / "sim"),
                    "iso_prefix": str(root / "isotopes.dat"),
                }
            )
            rendered = target.read_text(encoding="utf-8").splitlines()
            for line in protected:
                self.assertEqual(rendered.count(line), 1)

    def test_limit_launcher_cli_maps_seed_source_and_disables_core(self) -> None:
        argv = [
            str(launcher.__file__),
            "--file-size-limit-bytes",
            "4096",
            "--cosima",
            "/opt/bin/cosima",
            "--seed",
            "123456",
            "--source",
            "/tmp/p0.source",
        ]
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.object(launcher.resource, "setrlimit") as setrlimit, \
             mock.patch.object(launcher.os, "execv") as execv:
            launcher.main()
        setrlimit.assert_any_call(launcher.resource.RLIMIT_FSIZE, (4096, 4096))
        setrlimit.assert_any_call(launcher.resource.RLIMIT_CORE, (0, 0))
        execv.assert_called_once_with(
            "/opt/bin/cosima",
            ["/opt/bin/cosima", "-s", "123456", "/tmp/p0.source"],
        )

    def test_validator_preflight_wait_is_output_free(self) -> None:
        self.assertFalse(p0.SOURCE_MANIFEST.exists())
        watched = (runner.GLOBAL_CONTRACT, runner.FINAL_REPORT, runner.FINAL_LEDGER)
        before = {path: path.exists() for path in watched}
        result = subprocess.run(
            [sys.executable, str(validator.THIS_FILE), "--preflight"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = strict_stdout_json(result.stdout)
        self.assertEqual(payload["status"], "WAIT__P0_SIXBAND_SCIENCE_CONTRACT_NOT_FROZEN")
        self.assertIs(payload["canonical_outputs_written"], False)
        self.assertEqual(before, {path: path.exists() for path in watched})

    @staticmethod
    def _init_line(*, particle: int = 4, energy: float = 5.0) -> str:
        fields = ["0"] * 23
        fields[0] = "1"
        fields[15] = str(particle)
        fields[16] = "1.0"
        fields[17] = "0.0"
        fields[18] = "0.0"
        fields[22] = str(energy)
        return "IA INIT  " + ";".join(fields)

    def _write_synthetic_sim(self, path: Path, geometry: Path, *, particle: int = 4, energy: float = 5.0) -> None:
        lines = [f"Geometry {geometry}", "Seed 123"]
        for event in (1, 2):
            lines.extend(("SE", f"ID {event} {event}", self._init_line(particle=particle, energy=energy)))
            if event == 1:
                lines.extend(
                    (
                        "CC HIT TP_L0_1 edep_keV=2.500000e+02",
                        "CC HIT TP_L0_2 edep_keV=2.500000e+02",
                        "CC HIT BGO_S3C_FullWrap_SideShell_WindowCut_40mm edep_keV=6.000000e+01",
                    )
                )
            else:
                lines.extend(
                    (
                        "CC HIT TP_L1_7 edep_keV=5.100000e+02",
                        "CC HIT Kapton_Active_But_Not_Veto edep_keV=1.000000e+03",
                    )
                )
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    def test_sim_scanner_proton_band_and_true_veto_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            geometry = root / "geometry.geo.setup"
            geometry.write_text("Version 0.1\n", encoding="utf-8")
            sim = root / "synthetic.sim.gz"
            self._write_synthetic_sim(sim, geometry)
            scan = validator.scan_sim(
                sim,
                geometry="s3d_o8",
                mode="instant",
                expected_events=2,
                expected_seed=123,
                expected_geometry=geometry,
                support_by_bin={index: (1.0, 10.0) for index in range(20)},
            )
        self.assertEqual(scan["problems"], [])
        self.assertEqual(scan["events"], 2)
        prompt = scan["prompt"]
        self.assertEqual(prompt["raw_tes_positive_events"], 2)
        self.assertEqual(prompt["raw_tes_480_550_events"], 2)
        self.assertEqual(prompt["veto_survivors_tes_480_550"], {"50": 1, "70": 2, "80": 2})

    def test_sim_scanner_rejects_wrong_particle_and_out_of_band_energy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            geometry = root / "geometry.geo.setup"
            geometry.write_text("Version 0.1\n", encoding="utf-8")
            sim = root / "bad.sim.gz"
            self._write_synthetic_sim(sim, geometry, particle=1, energy=11.0)
            scan = validator.scan_sim(
                sim,
                geometry="s3d_o8",
                mode="instant",
                expected_events=2,
                expected_seed=123,
                expected_geometry=geometry,
                support_by_bin={index: (1.0, 10.0) for index in range(20)},
            )
        self.assertEqual(scan["bad_particle_records"], 2)
        self.assertEqual(scan["bad_energy_records"], 2)
        self.assertTrue(any("wrong proton" in item for item in scan["problems"]))
        self.assertTrue(any("outside selected" in item for item in scan["problems"]))

    def test_source_card_allowed_diff_is_exactly_spectrum_and_flux(self) -> None:
        lines = ["Geometry fixed.geo", "PhysicsListEMRangeCut 0.01"]
        derived = list(lines)
        for angular in range(20):
            suffix = "down" if angular < 10 else "up"
            name = f"Atm_p_bin{angular:02d}_{suffix}"
            lines.extend((f"{name}.Spectrum File parent_{angular}.spectrum", f"{name}.Flux 1"))
            derived.extend((f"{name}.Spectrum File conditional_{angular}.spectrum", f"{name}.Flux 0.1"))
        result = validator.source_builder.allowed_band_card_diff("\n".join(lines) + "\n", "\n".join(derived) + "\n")
        self.assertEqual(result["spectrum_file_line_differences"], 20)
        self.assertEqual(result["partial_flux_line_differences"], 20)
        derived[1] = "PhysicsListEMRangeCut 1.0"
        with self.assertRaises(RuntimeError):
            validator.source_builder.allowed_band_card_diff("\n".join(lines) + "\n", "\n".join(derived) + "\n")

    def test_canonical_pair_check_requires_both_and_detects_tamper(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            report = root / "report.json"
            ledger = root / "ledger.json"
            expected_report = {"schema_version": 1, "status": "PASS"}
            build_ledger = lambda digest: {"schema_version": 1, "status": "PASS", "report_sha256": digest}
            with self.assertRaises(RuntimeError):
                validator._publish_pair(report, ledger, expected_report, build_ledger, check=True)
            self.assertFalse(report.exists())
            self.assertFalse(ledger.exists())
            validator._publish_pair(report, ledger, expected_report, build_ledger, check=False)
            validator._publish_pair(report, ledger, expected_report, build_ledger, check=True)
            ledger.write_text('{"schema_version":1,"status":"PASS","report_sha256":"bad"}\n', encoding="utf-8")
            with self.assertRaises(RuntimeError):
                validator._publish_pair(report, ledger, expected_report, build_ledger, check=True)

    def test_true_veto_volume_sets_match_frozen_postprocessor(self) -> None:
        self.assertEqual(len(validator.MASS_VETO), 24)
        self.assertEqual(len(validator.O8_BGO_VETO), 3)
        self.assertEqual(len(validator.O8_PLASTIC_VETO), 3)
        self.assertFalse(any("Kapton" in value for value in validator.MASS_VETO | validator.O8_BGO_VETO | validator.O8_PLASTIC_VETO))

    def test_tes_window_has_exclusive_550kev_upper_edge(self) -> None:
        summary = {
            "raw_tes_positive_events": 0,
            "raw_tes_480_550_events": 0,
            "veto_survivors_tes_positive": {"50": 0, "70": 0, "80": 0},
            "veto_survivors_tes_480_550": {"50": 0, "70": 0, "80": 0},
        }
        validator._finish_prompt_event("mass_model_511", {"TP_L0_1": 550.0}, 0.0, 0.0, summary)
        self.assertEqual(summary["raw_tes_positive_events"], 1)
        self.assertEqual(summary["raw_tes_480_550_events"], 0)

    def test_prompt_recomposition_sums_band_rates_not_pooled_tt(self) -> None:
        ledgers = []
        for index in range(6):
            ledgers.append(
                {
                    "band": f"b{index}",
                    "band_index": index,
                    "band_flux_weight": str(Decimal(1) / Decimal(6)),
                    "events": 256,
                    "sum_TT_s": float(index + 1),
                    "prompt_summary": {"counts": {"metric": index + 1}},
                }
            )
        result = validator._prompt_weighted_recomposition("mass_model_511", ledgers)
        metric = result["metrics"]["metric"]
        self.assertEqual(metric["physical_rate_s-1"], 6.0)
        self.assertNotEqual(metric["physical_rate_s-1"], sum(range(1, 7)) / sum(range(1, 7)))

    def test_activation_recomposition_explicitly_carries_zero_rp_bands(self) -> None:
        ledgers = []
        for index in range(6):
            ledgers.append(
                {
                    "band": f"b{index}",
                    "band_index": index,
                    "sum_TT_s": float(index + 1),
                    "buildup_RP_by_volume_isotope_state": (
                        [{"volume": "BGO", "isotope_id": 6012, "excitation_keV": 0.0, "sum_RP": 2.0}]
                        if index == 2
                        else []
                    ),
                }
            )
        result = validator._activation_weighted_recomposition("s3d_o8", ledgers)
        self.assertEqual(len(result["band_totals_including_zero"]), 6)
        self.assertEqual(len(result["states"]), 1)
        contributions = result["states"][0]["band_contributions"]
        self.assertEqual(len(contributions), 6)
        self.assertEqual(sum(item["is_explicit_zero"] for item in contributions), 5)
        self.assertAlmostEqual(result["states"][0]["production_rate_s-1"], 2.0 / 3.0)


if __name__ == "__main__":
    unittest.main()

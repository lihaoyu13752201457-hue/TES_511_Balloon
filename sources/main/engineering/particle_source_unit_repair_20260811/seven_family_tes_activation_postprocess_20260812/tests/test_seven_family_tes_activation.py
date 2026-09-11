from __future__ import annotations

import csv
import gzip
import hashlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[4]
MODULE_PATH = (
    ROOT
    / "engineering/particle_source_unit_repair_20260811"
    / "seven_family_tes_activation_postprocess_20260812"
    / "code/analyze_seven_family_tes_activation.py"
)
SPEC = importlib.util.spec_from_file_location("seven_family_postprocess_under_test", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
analysis = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = analysis
SPEC.loader.exec_module(analysis)


def init_line(particle_type: int, energy_keV: float, dir_z: float = -1.0) -> str:
    fields = ["0"] * 23
    fields[15] = str(particle_type)
    fields[16] = "0"
    fields[17] = "0"
    fields[18] = f"{dir_z:g}"
    fields[22] = f"{energy_keV:g}"
    return "IA INIT " + ";".join(fields)


def write_sim(
    path: Path,
    *,
    geometry: Path,
    seed: int,
    particle_type: int,
    energy_keV: float = 511.0,
    tes_keV: float = 511.0,
    pair: bool = False,
) -> str:
    lines = [
        f"Geometry {geometry}",
        f"Seed {seed}",
        "SE",
        "ID 1",
        init_line(particle_type, energy_keV),
    ]
    if pair:
        lines.extend(("IA PAIR", "IA ANNI"))
    lines.extend(
        (
            f"CC HIT TP_L0_0 edep_keV={tes_keV:g}",
            "EN",
            "TS 1",
            "TE 0.1",
        )
    )
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_job(
    root: Path,
    *,
    geometry: str,
    mode: str,
    family: str,
    index: int,
    rp: float | None,
) -> analysis.JobInput:
    directory = root / geometry / mode / family
    directory.mkdir(parents=True, exist_ok=True)
    geometry_setup = root / f"{geometry}.geo.setup"
    geometry_setup.write_text("Version 1\n", encoding="utf-8")
    job_name = f"job_{geometry}_{mode}_{family}_{index}"
    source = directory / f"{job_name}.source"
    source.write_text(f"Geometry {geometry_setup}\n", encoding="utf-8")
    dat = directory / f"{job_name}.dat"
    dat_lines = ["TT 1"]
    if rp is not None:
        dat_lines.extend(("VN ActiveVolume", f"RP 1001 0 {rp:g}"))
    dat_lines.append("EN")
    dat.write_text("\n".join(dat_lines) + "\n", encoding="utf-8")
    log = directory / f"{job_name}.log"
    log.write_text("Observation time: 1 sec\n", encoding="utf-8")
    sim = directory / f"{job_name}.sim.gz"
    seed = 900_000 + index
    if mode == "instant":
        sim_hash = write_sim(
            sim,
            geometry=geometry_setup,
            seed=seed,
            particle_type=analysis.PARTICLE_TYPES[family],
            pair=family == "gamma",
        )
    else:
        sim.write_bytes(b"buildup SIM is canonical but not a prompt input\n")
        sim_hash = hashlib.sha256(sim.read_bytes()).hexdigest()
    isotope_store = analysis.parse_isotope_dat(dat)
    return analysis.JobInput(
        geometry=geometry,
        mode=mode,
        family=family,
        batch_id="synthetic_PASS_batch",
        ledger=root / "synthetic_ledger.json",
        ledger_sha256="1" * 64,
        job_name=job_name,
        events=1,
        seed=seed,
        ordinal=index,
        tt_s=1.0,
        sim=sim,
        sim_sha256=sim_hash,
        job_source=source,
        job_source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        isotope_dat=dat,
        isotope_dat_sha256=hashlib.sha256(dat.read_bytes()).hexdigest(),
        log=log,
        log_sha256=hashlib.sha256(log.read_bytes()).hexdigest(),
        expected_geometry_setup=geometry_setup.resolve(),
        ledger_geometry_header=geometry_setup.resolve(),
        source_geometry=geometry_setup.resolve(),
        isotope_store=isotope_store,
    )


def inventory_row(job: analysis.JobInput) -> dict[str, object]:
    return {
        "geometry": job.geometry,
        "mode": job.mode,
        "family": job.family,
        "batch_id": job.batch_id,
        "ledger": analysis.rel(job.ledger),
        "ledger_sha256": job.ledger_sha256,
        "job_name": job.job_name,
        "events": job.events,
        "seed": job.seed,
        "ordinal": job.ordinal,
        "TT_s": job.tt_s,
        "RP_record_count": job.isotope_store["RP_record_count"],
        "job_source": analysis.rel(job.job_source),
        "job_source_sha256": job.job_source_sha256,
        "isotope_dat": analysis.rel(job.isotope_dat),
        "isotope_dat_sha256": job.isotope_dat_sha256,
        "log": analysis.rel(job.log),
        "log_sha256": job.log_sha256,
        "sim": analysis.rel(job.sim),
        "ledger_sim_sha256": job.sim_sha256,
        "observed_sim_sha256": None,
        "fixed_geometry_setup": analysis.rel(job.expected_geometry_setup),
        "ledger_geometry_header": analysis.rel(job.ledger_geometry_header),
    }


class ParserAndContractTests(unittest.TestCase):
    def test_strict_json_rejects_nonfinite_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "bad.json"
            path.write_text('{"value": NaN}\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                analysis._json(path)
            with self.assertRaises(ValueError):
                analysis.canonical_json_bytes({"value": float("nan")})

    def test_isotope_parser_groups_RP_and_requires_unique_positive_TT(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            good = root / "good.dat"
            good.write_text(
                "TT 2\nVN VolA\nRP 1001 0 2\nRP 1001 0 3\nVN VolB\nRP 2002 4.5 0\nEN\n",
                encoding="utf-8",
            )
            parsed = analysis.parse_isotope_dat(good)
            self.assertEqual(parsed["TT_s"], 2.0)
            self.assertEqual(parsed["RP_record_count"], 3)
            self.assertEqual(parsed["RP_totals_by_volume_isotope_state"][0]["sum_RP"], 5.0)
            duplicate = root / "duplicate.dat"
            duplicate.write_text("TT 1\nTT 1\nEN\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "TT=2"):
                analysis.parse_isotope_dat(duplicate)

    def test_true_veto_whitelists_and_kapton_exclusion(self) -> None:
        self.assertEqual(len(analysis.gamma.MASS_TRUE_CSI_VOLUMES), 24)
        self.assertEqual(len(analysis.gamma.O8_TRUE_BGO_VOLUMES), 3)
        self.assertEqual(len(analysis.gamma.O8_TRUE_PLASTIC_VOLUMES), 3)
        self.assertEqual(
            analysis.gamma._relevant_volume("s3d_o8", "ActiveShield_S3C_BGO_Kapton_Outer"),
            "kapton",
        )
        self.assertFalse(
            any(
                "KAPTON" in value.upper()
                for value in (
                    analysis.gamma.MASS_TRUE_CSI_VOLUMES
                    | analysis.gamma.O8_TRUE_BGO_VOLUMES
                    | analysis.gamma.O8_TRUE_PLASTIC_VOLUMES
                )
            )
        )

    def test_response_rng_is_keyed_and_order_invariant(self) -> None:
        first = analysis.keyed_standard_normal("g", "gamma", 1, "TP_L0_0")
        unrelated = analysis.keyed_standard_normal("other", 99)
        second = analysis.keyed_standard_normal("g", "gamma", 1, "TP_L0_0")
        self.assertTrue(unrelated == unrelated)
        self.assertEqual(first, second)
        self.assertNotEqual(first, analysis.keyed_standard_normal("g", "n", 1, "TP_L0_0"))

    def test_prompt_sim_particle_geometry_hash_and_footer_closure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            job = make_job(
                root,
                geometry="mass_model_511",
                mode="instant",
                family="n",
                index=1,
                rp=None,
            )
            acc = analysis.PromptAccumulator("mass_model_511", "n")
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=analysis.EVENT_FIELDS)
            writer.writeheader()
            observed = analysis.parse_prompt_sim(job, acc, writer)
            self.assertEqual(observed, job.sim_sha256)
            self.assertEqual(acc.primary_count, 1)
            self.assertEqual(acc.raw_tes_positive, 1)
            self.assertEqual(acc.cut_counts[("raw", "pre_veto", "broad_480_550")], 1)
            wrong = analysis.JobInput(
                **{
                    **job.__dict__,
                    "expected_geometry_setup": (root / "wrong.geo.setup").resolve(),
                }
            )
            with self.assertRaisesRegex(RuntimeError, "Geometry four-way"):
                analysis.parse_prompt_sim(
                    wrong,
                    analysis.PromptAccumulator("mass_model_511", "n"),
                    writer,
                )

    def test_activation_zero_RP_jobs_are_in_every_key_denominator(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            jobs_by_cell: dict[tuple[str, str, str], list[analysis.JobInput]] = {}
            for geometry in analysis.GEOMETRIES:
                for mode in analysis.MODES:
                    for family in analysis.FAMILIES:
                        rp = 2.0 if mode == "buildup" and family == "gamma" else None
                        jobs_by_cell[(geometry, mode, family)] = [
                            make_job(
                                root,
                                geometry=geometry,
                                mode=mode,
                                family=family,
                                index=len(jobs_by_cell) + 1,
                                rp=rp,
                            )
                        ]
            extra_zero = make_job(
                root,
                geometry="mass_model_511",
                mode="buildup",
                family="gamma",
                index=999,
                rp=None,
            )
            jobs_by_cell[("mass_model_511", "buildup", "gamma")].append(extra_zero)
            exposure, isotope = analysis.build_activation_rows(jobs_by_cell)
            row = next(
                value for value in isotope
                if value["geometry"] == "mass_model_511" and value["family"] == "gamma"
            )
            self.assertEqual(row["sum_RP"], 2.0)
            self.assertEqual(row["sum_TT_s_including_zero_RP_jobs"], 2.0)
            self.assertEqual(row["job_count_in_denominator"], 2)
            self.assertEqual(row["jobs_with_zero_RP_for_key"], 1)
            zero_family = next(
                value for value in exposure
                if value["geometry"] == "mass_model_511" and value["family"] == "n"
            )
            self.assertEqual(zero_family["total_sum_RP"], 0.0)
            self.assertIsNotNone(zero_family["zero_total_RP_one_sided95_rate_upper_s-1"])


class AuthorityAndTransactionTests(unittest.TestCase):
    def test_missing_canonical_authority_is_wait_and_writes_no_pin(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = analysis.CanonicalPaths(
                batch0000_ledger=root / "b0.json",
                batch0001_ledger=root / "b1.json",
                batch0002_ledger=root / "b2.json",
                batch0004_contract=root / "contract.json",
                batch0004_final_report=root / "final_report.json",
                batch0004_final_ledger=root / "final_ledger.json",
                batch0004_checkpoint_root=root / "checkpoints",
            )
            pin = root / "pin.json"
            with self.assertRaises(analysis.AuthorityWait):
                analysis.pin_authorities(paths=paths, pin_path=pin)
            self.assertFalse(pin.exists())
            self.assertFalse((root / "checkpoints").exists())

    def test_transaction_removes_temporary_directory_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            pin = root / "pin.json"
            analysis.atomic_json(pin, {"status": "synthetic"})
            target = root / "published"
            with mock.patch.object(
                analysis,
                "_run_analysis_in_directory",
                side_effect=RuntimeError("synthetic failure"),
            ):
                with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
                    analysis.run_analysis({}, [], {}, target, authority_pin_path=pin)
            self.assertFalse(target.exists())
            self.assertFalse(any(path.name.startswith(".published.tmp-") for path in root.iterdir()))

    def test_full_small_sample_transaction_passes_without_figures(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            jobs_by_cell: dict[tuple[str, str, str], list[analysis.JobInput]] = {}
            inventory: list[dict[str, object]] = []
            index = 0
            for geometry in analysis.GEOMETRIES:
                for mode in analysis.MODES:
                    for family in analysis.FAMILIES:
                        index += 1
                        rp = 1.0 if mode == "buildup" and index % 2 else None
                        job = make_job(
                            root / "inputs",
                            geometry=geometry,
                            mode=mode,
                            family=family,
                            index=index,
                            rp=rp,
                        )
                        jobs_by_cell[(geometry, mode, family)] = [job]
                        inventory.append(inventory_row(job))
            pin = root / "canonical_authorities.json"
            pin_payload = {
                "schema_version": 1,
                "status": "PASS__SEVEN_FAMILY_POSTPROCESS_CANONICAL_AUTHORITIES",
                "batch0003_selected_profile": "prefix_ordinal76",
                "batch0003_gamma_exposure": {
                    "mode": "instant",
                    "cumulative_events_per_geometry": 2_001_000,
                    "credited_to_batch0004_buildup": False,
                },
                "authorities": [],
                "toolchain": {
                    "analyzer": {
                        "path": analysis.rel(analysis.THIS_FILE),
                        "sha256": analysis.sha256(analysis.THIS_FILE),
                    },
                    "frozen_gamma_prompt_core": {
                        "path": analysis.rel(analysis.GAMMA_CORE_PATH),
                        "sha256": analysis.sha256(analysis.GAMMA_CORE_PATH),
                    },
                },
            }
            analysis.atomic_json(pin, pin_payload)
            output = root / "published"
            result = analysis.run_analysis(
                jobs_by_cell,
                inventory,
                {},
                output,
                authority_pin_path=pin,
                make_figures=False,
            )
            self.assertEqual(result["validation"]["status"], "PASS")
            self.assertTrue(output.is_dir())
            self.assertTrue((output / "seven_family_tes_activation_summary.json").is_file())
            self.assertTrue((output / "activation_family_exposure.csv").is_file())
            self.assertTrue((output / "prompt_tes_histograms.csv").is_file())
            parsed = json.loads(
                (output / "seven_family_tes_activation_summary.json").read_text(encoding="utf-8"),
                parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)),
            )
            self.assertEqual(len(parsed["prompt_cells"]), 14)
            self.assertEqual(len(parsed["activation_cells"]), 14)
            self.assertFalse(any(path.name.startswith(".published.tmp-") for path in root.iterdir()))


class RealCanonicalPriorReadTests(unittest.TestCase):
    def test_retained_batch0000_1_2_sample_rows_real_read(self) -> None:
        paths = (
            analysis.DEFAULT_PATHS.batch0000_ledger,
            analysis.DEFAULT_PATHS.batch0001_ledger,
            analysis.DEFAULT_PATHS.batch0002_ledger,
        )
        parsed = 0
        for ledger_path in paths:
            ledger = analysis._json(ledger_path)
            digest = analysis.sha256(ledger_path)
            for campaign in ledger["campaigns"]:
                row = next(
                    item for item in campaign["jobs"]
                    if item.get("family", campaign.get("family")) != "p"
                )
                job = analysis._job_from_row(ledger, ledger_path, digest, campaign, row)
                self.assertGreater(job.tt_s, 0.0)
                self.assertEqual(job.source_geometry, job.expected_geometry_setup)
                parsed += 1
        self.assertEqual(parsed, 10)


if __name__ == "__main__":
    unittest.main()

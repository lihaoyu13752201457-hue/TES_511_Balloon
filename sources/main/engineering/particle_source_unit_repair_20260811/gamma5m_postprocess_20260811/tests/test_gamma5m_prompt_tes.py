from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest import mock


CODE = Path(__file__).resolve().parents[1] / "code"
if str(CODE) not in sys.path:
    sys.path.insert(0, str(CODE))

import analyze_gamma5m_prompt_tes as analysis  # noqa: E402


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(65536), b""):
            value.update(block)
    return value.hexdigest()


def init_line(energy_keV: float, direction=(0.0, 0.0, -1.0)) -> str:
    fields = ["1"] + ["0"] * 14
    fields.extend(
        [
            "1",
            f"{direction[0]:.8f}",
            f"{direction[1]:.8f}",
            f"{direction[2]:.8f}",
            "0",
            "0",
            "0",
            f"{energy_keV:.8f}",
        ]
    )
    assert len(fields) == 23
    return "IA INIT " + ";".join(fields)


def hit(volume: str, energy_keV: float) -> str:
    return (
        f"CC HIT {volume} edep_keV={energy_keV:.8e} x=0 y=0 z=0 t=0 "
        "sec=gamma tid=1 pid=0 sproc=phot prim=gamma par=none cproc=primary primid=1"
    )


def write_sim(path: Path, geometry_header: Path, seed: int, events: list[list[str]]) -> None:
    lines = [
        "# synthetic SIM for postprocessor tests",
        "Type SIM",
        f"Geometry {geometry_header}",
        f"Seed {seed}",
    ]
    for event_id, records in enumerate(events, 1):
        lines.extend(("SE", f"ID {event_id} {event_id}"))
        lines.extend(records)
    lines.extend(("EN", "", "TE 1.0", f"TS {len(events)}"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8", newline="\n") as handle:
        handle.write("\n".join(lines) + "\n")


class SyntheticAuthority:
    def __init__(self, root: Path, selected_profile: str = "stage5"):
        self.root = root
        self.selected_profile = selected_profile
        if selected_profile not in {"stage5", "prefix76"}:
            raise ValueError(selected_profile)
        self.geometry_headers = {
            geometry: root / f"{geometry}.geo.setup" for geometry in analysis.GEOMETRIES
        }
        for path in self.geometry_headers.values():
            path.write_text("synthetic geometry\n", encoding="utf-8")
        self.geometry_contracts = {
            geometry: {
                "geometry_setup": self.geometry_headers[geometry],
                "geometry_setup_sha256": digest(self.geometry_headers[geometry]),
                "detector_map": analysis.GEOMETRY_CONTRACTS[geometry]["detector_map"],
                "detector_map_sha256": analysis.GEOMETRY_CONTRACTS[geometry]["detector_map_sha256"],
            }
            for geometry in analysis.GEOMETRIES
        }

    def _job(
        self,
        geometry: str,
        batch_id: str,
        job_name: str,
        seed: int,
        events: list[list[str]],
        ordinal: int | None = None,
    ) -> dict[str, object]:
        directory = self.root / geometry / batch_id / job_name
        directory.mkdir(parents=True, exist_ok=True)
        sim = directory / f"{job_name}.sim.gz"
        source = directory / f"{job_name}.source"
        isotope = directory / f"{job_name}.dat"
        log = directory / f"{job_name}.log"
        write_sim(sim, self.geometry_headers[geometry], seed, events)
        corrected_references = "".join(
            "Spectrum File engineering/particle_source_unit_repair_20260811/"
            f"spectra/correct_keV_total/synthetic_bin{index:02d}.spectrum\n"
            for index in range(20)
        )
        source.write_text(
            f"Geometry {self.geometry_headers[geometry]}\nsynthetic source\n{corrected_references}",
            encoding="utf-8",
        )
        isotope.write_text("TT 1.0\nEN\n", encoding="utf-8")
        log.write_text("Observation time: 1.0 sec\n", encoding="utf-8")
        payload: dict[str, object] = {
            "job_name": job_name,
            "family": "gamma",
            "events": len(events),
            "seed": seed,
            "TT_s_from_isotope_dat": 1.0,
            "TT_s_from_log": 1.0,
            "sim": str(sim),
            "sim_sha256": digest(sim),
            "job_source": str(source),
            "job_source_sha256": digest(source),
            "isotope_dat": str(isotope),
            "isotope_dat_sha256": digest(isotope),
            "log": str(log),
            "log_sha256": digest(log),
            "ia_init": {"geometry_header": str(self.geometry_headers[geometry])},
        }
        if ordinal is not None:
            payload["ordinal"] = ordinal
        return payload

    @staticmethod
    def _event(tes: float | None, active_volume: str, active: float, plastic_volume: str | None = None, plastic: float = 0.0, pair=False) -> list[str]:
        records: list[str] = []
        if tes is not None:
            records.append(hit("TP_L0_0", tes))
        if active > 0.0:
            records.append(hit(active_volume, active))
        if plastic_volume is not None and plastic > 0.0:
            records.append(hit(plastic_volume, plastic))
        records.append(hit("ActiveShield_S3C_BGO_Kapton_SideWrap_WindowCut_0p3mm", 10000.0))
        records.append(init_line(5000.0))
        if pair:
            records.extend(("IA PAIR 1;0", "IA ANNI 2;1"))
        return records

    def build(self) -> tuple[Path, Path, Path]:
        ledgers: list[dict[str, object]] = []
        definitions = (
            (
                "corrected_original_all8_fullsphere20_batch0000",
                "PASS__BATCH0000_MERGE_ELIGIBLE",
                101,
                "gamma_prior0",
                49.0,
                49.0,
                True,
            ),
            (
                "corrected_original_seven_family_fullsphere20_batch0001",
                "PASS__BATCH0001_MERGE_ELIGIBLE",
                202,
                "gamma_prior1",
                60.0,
                49.0,
                False,
            ),
            (
                "corrected_original_gamma_instant_batch0003",
                (
                    "PASS__BATCH0003_STAGE5M_MERGE_ELIGIBLE"
                    if self.selected_profile == "stage5"
                    else "PARTIAL_PREFIX_MERGE_ELIGIBLE"
                ),
                303,
                "gamma_stage5",
                90.0,
                60.0,
                False,
            ),
        )
        for batch_id, status, seed, job_name, active, plastic, pair in definitions:
            campaigns = []
            for geometry in analysis.GEOMETRIES:
                active_volume = (
                    "CsI_Side_Segment_00"
                    if geometry == "mass_model_511"
                    else "BGO_S3C_FullWrap_SideShell_WindowCut_40mm"
                )
                plastic_volume = (
                    None
                    if geometry == "mass_model_511"
                    else "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm"
                )
                if batch_id.endswith("batch0003"):
                    events = [
                        self._event(500.0, active_volume, active, plastic_volume, plastic, pair),
                        self._event(None, active_volume, 0.0, plastic_volume, 0.0, False),
                    ]
                else:
                    events = [self._event(500.0, active_volume, active, plastic_volume, plastic, pair)]
                job = self._job(
                    geometry,
                    batch_id,
                    job_name,
                    seed,
                    events,
                    ordinal=1 if batch_id.endswith("batch0003") else None,
                )
                campaign = {
                    "geometry": geometry,
                    "mode": "instant",
                    "jobs": [job],
                }
                if batch_id.endswith("batch0003"):
                    campaign.update(
                        {
                            "family": "gamma",
                            "prior_events_credited": 2,
                            "new_events_validated": 2,
                            "cumulative_events": 4,
                            "validated_shards": 1,
                            "TT_s_new_sum": 1.0,
                        }
                    )
                campaigns.append(campaign)
            ledger: dict[str, object] = {
                "schema_version": 1,
                "status": status,
                "batch_id": batch_id,
                "source_contract_manifest_sha256": analysis.SOURCE_CONTRACT_SHA256,
                "campaigns": campaigns,
            }
            if batch_id.endswith("batch0003"):
                ledger["prior_credit_revalidation"] = {
                    "status": "PASS",
                    "credited_events_per_geometry": {
                        geometry: 2 for geometry in analysis.GEOMETRIES
                    },
                }
                if self.selected_profile == "stage5":
                    ledger["stage"] = "5m"
                else:
                    ledger.update(
                        {
                            "validation_status": "PASS__PARTIAL_PREFIX_VALIDATED",
                            "prefix_start_ordinal": 1,
                            "prefix_end_ordinal": 1,
                            "prior_events_per_geometry": 2,
                            "new_events_per_geometry": 2,
                            "cumulative_events_per_geometry": 4,
                            "validated_pair_count": 1,
                            "authority_boundary": {
                                "full_batch0003_5m_or_10m_checkpoint_authority": False,
                                "full_eight_family_authority": False,
                                "physics_rate_sensitivity_or_geometry_promotion_authority": False,
                            },
                        }
                    )
            ledgers.append(ledger)
        paths = tuple(self.root / f"ledger{index}.json" for index in range(3))
        for path, payload in zip(paths, ledgers, strict=True):
            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        if self.selected_profile == "prefix76":
            self.profile = analysis.AuthorityProfile(
                key="prefix76",
                ledger=paths[2],
                validation=self.root / "synthetic-prefix-validation.json",
                ledger_status="PARTIAL_PREFIX_MERGE_ELIGIBLE",
                validation_status="PASS__PARTIAL_PREFIX_VALIDATED",
                prior_events_per_geometry=2,
                cumulative_events_per_geometry=4,
                new_events_per_geometry=2,
                expected_prior_shards=(1, 1),
                expected_new_shards=1,
                prefix_end_ordinal=1,
                full_checkpoint_authority=False,
                output_stem=analysis.PREFIX76_PROFILE.output_stem,
                display_title=analysis.PREFIX76_PROFILE.display_title,
                pass_status=analysis.PREFIX76_PROFILE.pass_status,
            )
        else:
            self.profile = analysis.AuthorityProfile(
                key="synthetic_stage",
                ledger=paths[2],
                validation=self.root / "synthetic-stage-validation.json",
                ledger_status="PASS__BATCH0003_STAGE5M_MERGE_ELIGIBLE",
                validation_status="PASS",
                prior_events_per_geometry=2,
                cumulative_events_per_geometry=4,
                new_events_per_geometry=2,
                expected_prior_shards=(1, 1),
                expected_new_shards=1,
                prefix_end_ordinal=1,
                full_checkpoint_authority=True,
                output_stem="gamma_synthetic_stage",
                display_title="Synthetic corrected-keV prompt gamma checkpoint",
                pass_status="PASS__SYNTHETIC_CORRECTED_KEV_GAMMA_PROMPT_TES_POSTPROCESS",
            )
        return paths


class Gamma5MPostprocessUnitTests(unittest.TestCase):
    def test_keyed_response_is_order_invariant_and_key_sensitive(self) -> None:
        key = ("mass_model_511", "batch", 101, "job", 7, "TP_L0_3")
        first = analysis.keyed_standard_normal(*key)
        second = analysis.keyed_standard_normal(*key)
        changed = analysis.keyed_standard_normal(*key[:-1], "TP_L0_4")
        self.assertEqual(first, second)
        self.assertNotEqual(first, changed)
        self.assertTrue(math.isfinite(first))

    def test_interval_boundaries(self) -> None:
        self.assertEqual(analysis.wilson_interval(0, 0), (None, None))
        low, high = analysis.wilson_interval(5, 10)
        self.assertLess(low, 0.5)
        self.assertGreater(high, 0.5)
        poisson_low, poisson_high = analysis.garwood_interval(0)
        self.assertEqual(poisson_low, 0.0)
        self.assertGreater(poisson_high, -math.log(0.05))

    def test_window_and_veto_boundaries_are_half_open_and_strict(self) -> None:
        self.assertTrue(analysis.window_flags(480.0)["broad_480_550"])
        self.assertFalse(analysis.window_flags(550.0)["broad_480_550"])
        self.assertTrue(analysis.window_flags(510.58)["w2_510p58_511p42"])
        self.assertFalse(analysis.window_flags(511.42)["w2_510p58_511p42"])
        self.assertEqual(analysis._relevant_volume("s3d_o8", "ActiveShield_S3C_BGO_Kapton_SideWrap_WindowCut_0p3mm"), "kapton")
        self.assertIsNone(analysis._relevant_volume("s3d_o8", "Outer_Al_S3C_BGO_Mechanical_SideShell_WindowCut_3mm"))


class Gamma5MPostprocessSyntheticIntegrationTests(unittest.TestCase):
    def test_prefix76_profile_is_explicit_nonfull_diagnostic_and_has_exact_job_prefix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authority = SyntheticAuthority(root, selected_profile="prefix76")
            ledger_paths = authority.build()
            jobs, inventory, ledgers = analysis.collect_jobs(
                *ledger_paths,
                profile=authority.profile,
                require_profile_envelope=True,
                geometry_contracts=authority.geometry_contracts,
            )
            for geometry in analysis.GEOMETRIES:
                selected = [job for job in jobs[geometry] if job.batch_id.endswith("batch0003")]
                self.assertEqual([job.ordinal for job in selected], [1])
                self.assertEqual(sum(job.events for job in jobs[geometry]), 4)
            self.assertEqual(len(inventory), 6)
            output = root / "prefix-analysis"
            result = analysis.run_analysis(
                jobs,
                inventory,
                ledgers,
                output,
                profile=authority.profile,
                make_figures=True,
                protect_existing=False,
            )
            profile_record = result["summary"]["authority_profile"]
            self.assertEqual(profile_record["key"], "prefix76")
            self.assertTrue(profile_record["diagnostic_nonfull"])
            self.assertFalse(profile_record["full_checkpoint_authority"])
            self.assertIn("2.001M prefix diagnostic", profile_record["display_title"])
            self.assertIn("NONFULL", result["summary"]["status"])
            self.assertNotIn("GAMMA5M", result["summary"]["status"])
            self.assertEqual(result["validation"]["authority_scope"], "diagnostic_nonfull")
            self.assertTrue(all("gamma5m" not in path.name.lower() for path in output.iterdir()))
            svg = (
                output / f"{analysis.profile_output_name(authority.profile, 'primary_drivers')}.svg"
            ).read_text(encoding="utf-8")
            self.assertIn("2.001M prefix diagnostic (ordinal 76; non-full)", svg)
            self.assertNotIn("5M checkpoint", svg)

    def test_prefix_profile_rejects_an_ordinal_gap(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authority = SyntheticAuthority(root, selected_profile="prefix76")
            ledger_paths = authority.build()
            payload = json.loads(ledger_paths[2].read_text(encoding="utf-8"))
            payload["campaigns"][0]["jobs"][0]["ordinal"] = 2
            ledger_paths[2].write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "exact continuous ordinal prefix"):
                analysis.collect_jobs(
                    *ledger_paths,
                    profile=authority.profile,
                    require_profile_envelope=True,
                    geometry_contracts=authority.geometry_contracts,
                )

    def test_unpublished_prefix_pin_fails_without_creating_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            missing_profile = replace(
                analysis.PREFIX76_PROFILE,
                ledger=root / "missing-prefix-ledger.json",
                validation=root / "missing-prefix-validation.json",
            )
            pin = root / "canonical_gamma_authority.json"
            with self.assertRaisesRegex(RuntimeError, "not published"):
                analysis.write_authority_pin(missing_profile, pin_path=pin)
            self.assertFalse(pin.exists())
            self.assertEqual(list(root.iterdir()), [])

    def test_authority_pin_profile_selection_is_mutually_exclusive(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            pin = Path(temporary) / "canonical_gamma_authority.json"

            def synthetic_pin_payload(profile):
                return {
                    "schema_version": 1,
                    "status": "PASS__CORRECTED_GAMMA_AUTHORITY_PIN",
                    "authority_profile": profile.key,
                }

            with mock.patch.object(
                analysis,
                "_build_authority_pin_payload",
                side_effect=synthetic_pin_payload,
            ):
                written = analysis.write_authority_pin(analysis.PREFIX76_PROFILE, pin_path=pin)
                self.assertEqual(written["authority_profile"], "prefix76")
                with self.assertRaisesRegex(RuntimeError, "different profile"):
                    analysis.write_authority_pin(analysis.STAGE5_PROFILE, pin_path=pin)

    def test_streaming_analysis_closes_counts_hashes_tt_veto_and_kapton_exclusion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authority = SyntheticAuthority(root)
            ledger_paths = authority.build()
            jobs, inventory, ledgers = analysis.collect_jobs(
                *ledger_paths,
                profile=authority.profile,
                require_profile_envelope=False,
                geometry_contracts=authority.geometry_contracts,
            )
            output = root / "analysis"
            result = analysis.run_analysis(
                jobs,
                inventory,
                ledgers,
                output,
                profile=authority.profile,
                make_figures=True,
                protect_existing=False,
            )
            self.assertEqual(result["validation"]["status"], "PASS")
            for geometry in analysis.GEOMETRIES:
                record = result["summary"]["geometries"][geometry]
                self.assertEqual(record["primary_count"], 4)
                self.assertEqual(record["sum_TT_s"], 3.0)
                self.assertEqual(record["raw_TES_positive_events"], 3)
                self.assertEqual(record["measured_TES_positive_events"], 3)
                self.assertEqual(record["TES_events_with_excluded_Kapton_deposit"], 3)
                lookup = {
                    (row["selection"], row["window"]): row["count"] for row in record["cutflow"]
                }
                self.assertEqual(lookup[("pre_veto", "broad_480_550")], 3)
                self.assertEqual(lookup[("veto50", "broad_480_550")], 1)
                self.assertEqual(lookup[("veto70", "broad_480_550")], 2)
                self.assertEqual(lookup[("veto80", "broad_480_550")], 2)
            self.assertTrue(result["validation"]["checks"]["all_sim_hashes_match_ledgers"])
            self.assertEqual(len(result["validation"]["figure_qa"]), 3)
            event_name = analysis.profile_output_name(authority.profile, "event_diagnostics.csv.gz")
            with gzip.open(output / event_name, "rt", encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 6)
            self.assertTrue(all(row["source_theta_deg"] == "0" for row in rows))
            # The huge Kapton deposit is recorded for audit, but the first event
            # still passes the true-crystal 50-keV veto.
            first = next(row for row in rows if row["batch_id"].endswith("batch0000"))
            self.assertEqual(first["pass_veto50"], "1")
            self.assertEqual(float(first["excluded_kapton_keV"]), 10000.0)

    def test_compressed_sim_hash_drift_is_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authority = SyntheticAuthority(root)
            ledger_paths = authority.build()
            jobs, inventory, ledgers = analysis.collect_jobs(
                *ledger_paths,
                profile=authority.profile,
                require_profile_envelope=False,
                geometry_contracts=authority.geometry_contracts,
            )
            target = jobs["mass_model_511"][0].sim
            with target.open("ab") as handle:
                handle.write(b"drift")
            with self.assertRaisesRegex(RuntimeError, "SHA-256|gzip/read failure"):
                analysis.run_analysis(
                    jobs,
                    inventory,
                    ledgers,
                    root / "analysis",
                    profile=authority.profile,
                    make_figures=False,
                    protect_existing=False,
                )

    def test_wrong_job_source_geometry_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authority = SyntheticAuthority(root)
            ledger_paths = authority.build()
            payload = json.loads(ledger_paths[0].read_text(encoding="utf-8"))
            job = payload["campaigns"][0]["jobs"][0]
            source = Path(job["job_source"])
            source.write_text(
                f"Geometry {authority.geometry_headers['s3d_o8']}\nsynthetic source\n",
                encoding="utf-8",
            )
            job["job_source_sha256"] = digest(source)
            ledger_paths[0].write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "job-source Geometry"):
                analysis.collect_jobs(
                    *ledger_paths,
                    profile=authority.profile,
                    require_profile_envelope=False,
                    geometry_contracts=authority.geometry_contracts,
                )

    def test_alternate_ledger_path_is_rejected_by_exact_authority(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authority = SyntheticAuthority(root)
            ledger_paths = authority.build()
            alternate = root / "alternate-stage5-ledger.json"
            alternate.write_bytes(ledger_paths[2].read_bytes())
            with self.assertRaisesRegex(RuntimeError, "alternate ledger path"):
                analysis.collect_jobs(
                    ledger_paths[0],
                    ledger_paths[1],
                    alternate,
                    profile=authority.profile,
                    require_profile_envelope=False,
                    exact_ledger_paths=ledger_paths,
                    expected_ledger_sha256=tuple(digest(path) for path in ledger_paths),
                    geometry_contracts=authority.geometry_contracts,
                )

    def test_dat_tt_tamper_is_rejected_even_when_ledger_hash_is_updated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authority = SyntheticAuthority(root)
            ledger_paths = authority.build()
            payload = json.loads(ledger_paths[0].read_text(encoding="utf-8"))
            job = payload["campaigns"][0]["jobs"][0]
            isotope = Path(job["isotope_dat"])
            isotope.write_text("TT 2.0\nEN\n", encoding="utf-8")
            job["isotope_dat_sha256"] = digest(isotope)
            ledger_paths[0].write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "TT mismatch"):
                analysis.collect_jobs(
                    *ledger_paths,
                    profile=authority.profile,
                    require_profile_envelope=False,
                    geometry_contracts=authority.geometry_contracts,
                )

    def test_false_closure_leaves_no_output_or_temp_and_is_rerunnable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authority = SyntheticAuthority(root)
            ledger_paths = authority.build()
            jobs, inventory, ledgers = analysis.collect_jobs(
                *ledger_paths,
                profile=authority.profile,
                require_profile_envelope=False,
                geometry_contracts=authority.geometry_contracts,
            )
            output = root / "analysis"
            real_closures = analysis.compute_closure_checks

            def false_closure(accumulators):
                checks = real_closures(accumulators)
                checks["pair_category_all_three_windows_count_closure"] = False
                return checks

            with mock.patch.object(analysis, "compute_closure_checks", side_effect=false_closure):
                with self.assertRaisesRegex(RuntimeError, "validation failed"):
                    analysis.run_analysis(
                        jobs,
                        inventory,
                        ledgers,
                        output,
                        profile=authority.profile,
                        make_figures=False,
                        protect_existing=False,
                    )
            self.assertFalse(output.exists())
            self.assertEqual(list(root.glob(".analysis.tmp-*")), [])
            result = analysis.run_analysis(
                jobs,
                inventory,
                ledgers,
                output,
                profile=authority.profile,
                make_figures=False,
                protect_existing=False,
            )
            self.assertEqual(result["validation"]["status"], "PASS")

    def test_strict_json_open_ended_null_and_source_side_svg_label(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            authority = SyntheticAuthority(root)
            ledger_paths = authority.build()
            jobs, inventory, ledgers = analysis.collect_jobs(
                *ledger_paths,
                profile=authority.profile,
                require_profile_envelope=False,
                geometry_contracts=authority.geometry_contracts,
            )
            output = root / "analysis"
            analysis.run_analysis(
                jobs,
                inventory,
                ledgers,
                output,
                profile=authority.profile,
                make_figures=True,
                protect_existing=False,
            )

            def reject_nonfinite(value: str):
                raise AssertionError(f"non-finite JSON token: {value}")

            summary_name = analysis.profile_output_name(authority.profile, "prompt_tes_summary.json")
            validation_name = analysis.profile_output_name(authority.profile, "postprocess_validation.json")
            for name in (summary_name, validation_name):
                json.loads(
                    (output / name).read_text(encoding="utf-8"),
                    parse_constant=reject_nonfinite,
                )
            summary = json.loads((output / summary_name).read_text(encoding="utf-8"))
            open_bins = [
                row
                for row in summary["geometries"]["mass_model_511"]["primary_drivers"]
                if row["dimension"] == "initial_energy" and row["bin_high_open_ended"]
            ]
            self.assertTrue(open_bins)
            self.assertTrue(all(row["bin_high"] is None for row in open_bins))
            svg = (
                output / f"{analysis.profile_output_name(authority.profile, 'primary_drivers')}.svg"
            ).read_text(encoding="utf-8")
            self.assertIn("Source-side polar angle acos(-IA dir_z) (deg)", svg)


class Gamma5MPostprocessRetainedReadOnlyTests(unittest.TestCase):
    def test_real_batch0000_gamma_sims_parse_read_only_with_frozen_geometry(self) -> None:
        ledger_path = analysis.DEFAULT_BATCH0000_LEDGER
        self.assertEqual(digest(ledger_path), analysis.CANONICAL_BATCH0000_LEDGER_SHA256)
        ledger = analysis._load_json(ledger_path)
        ledger_digest = digest(ledger_path)
        for geometry in analysis.GEOMETRIES:
            jobs = analysis._gamma_jobs(
                ledger,
                geometry,
                ledger_path,
                ledger_digest,
                analysis.GEOMETRY_CONTRACTS,
            )
            self.assertEqual(len(jobs), 1)
            sink = io.StringIO()
            writer = csv.DictWriter(sink, fieldnames=analysis.EVENT_FIELDS)
            writer.writeheader()
            accumulator = analysis.GeometryAccumulator(geometry)
            observed = analysis.parse_job(jobs[0], accumulator, writer)
            self.assertEqual(observed, jobs[0].sim_sha256)
            self.assertEqual(accumulator.primary_count, 1000)


if __name__ == "__main__":
    unittest.main()

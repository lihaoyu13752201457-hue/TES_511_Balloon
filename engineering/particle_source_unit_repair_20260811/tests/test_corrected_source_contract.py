#!/usr/bin/env python3
"""Positive and fail-closed negative tests for the corrected source contract."""

from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[3]
PACKAGE_RELATIVE = Path("engineering/particle_source_unit_repair_20260811")
PACKAGE = REPOSITORY / PACKAGE_RELATIVE
VALIDATOR_PATH = PACKAGE / "code/validate_corrected_source_package.py"

SPEC = importlib.util.spec_from_file_location("corrected_source_validator", VALIDATOR_PATH)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import machinery guard
    raise RuntimeError(f"cannot load validator: {VALIDATOR_PATH}")
VALIDATOR = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VALIDATOR
SPEC.loader.exec_module(VALIDATOR)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def copy_repo_file(source_root: Path, destination_root: Path, declared: str) -> Path:
    source = Path(declared)
    if not source.is_absolute():
        source = source_root / source
    relative = source.resolve().relative_to(source_root.resolve())
    destination = destination_root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    return destination


class CorrectedSourceContractTests(unittest.TestCase):
    """Use a private repository-shaped fixture so all corruptions are isolated."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._base_holder = tempfile.TemporaryDirectory(prefix="tes511-source-gate-base-")
        cls.base_repository = Path(cls._base_holder.name) / "repo"
        cls.base_repository.mkdir(parents=True)
        manifest_path = PACKAGE / "data/source_contract_manifest.json"
        cls.contract = json.loads(manifest_path.read_text(encoding="utf-8"))
        copy_repo_file(REPOSITORY, cls.base_repository, str(manifest_path.relative_to(REPOSITORY)))

        provenance_scope = {
            "input_provenance": cls.contract.get("input_provenance", {}),
            "environment": cls.contract.get("source_model", {}).get("environment", {}),
        }
        for row in VALIDATOR._objects_with_path_and_hash(provenance_scope):
            copy_repo_file(REPOSITORY, cls.base_repository, row["path"])

        for row in cls.contract["spectra"]["files"]:
            copy_repo_file(REPOSITORY, cls.base_repository, row["raw_spectrum"])
            copy_repo_file(REPOSITORY, cls.base_repository, row["corrected_spectrum"])
        for package in cls.contract["geometries"].values():
            for geometry_row in package["geometry_bundle"]["files"]:
                if geometry_row["scope"] == "repository":
                    copy_repo_file(
                        REPOSITORY,
                        cls.base_repository,
                        geometry_row["path"],
                    )
            for row in package["cards"]:
                copy_repo_file(REPOSITORY, cls.base_repository, row["parent_source"])
                copy_repo_file(REPOSITORY, cls.base_repository, row["source"])
            source_dir = cls.base_repository / package["source_dir"]
            copy_repo_file(
                REPOSITORY,
                cls.base_repository,
                str((REPOSITORY / package["source_dir"] / "source_migration_manifest.json").relative_to(REPOSITORY)),
            )
            cls.assertTrue(cls, (source_dir / "source_migration_manifest.json").is_file())

    @classmethod
    def tearDownClass(cls) -> None:
        cls._base_holder.cleanup()

    def setUp(self) -> None:
        self._holder = tempfile.TemporaryDirectory(prefix="tes511-source-gate-test-")
        self.repository = Path(self._holder.name) / "repo"
        shutil.copytree(self.base_repository, self.repository)
        self.package = self.repository / PACKAGE_RELATIVE
        self.manifest_path = self.package / "data/source_contract_manifest.json"

    def tearDown(self) -> None:
        self._holder.cleanup()

    def load_contract(self) -> dict:
        return json.loads(self.manifest_path.read_text(encoding="utf-8"))

    def save_contract_and_refresh_package_hashes(self, contract: dict) -> None:
        self.manifest_path.write_text(
            json.dumps(contract, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        contract_hash = digest(self.manifest_path)
        for package in contract["geometries"].values():
            package_manifest_path = self.repository / package["source_dir"] / "source_migration_manifest.json"
            package_manifest = json.loads(package_manifest_path.read_text(encoding="utf-8"))
            package_manifest["source_contract_manifest_sha256"] = contract_hash
            package_manifest_path.write_text(
                json.dumps(package_manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                encoding="utf-8",
            )

    def validate(self) -> dict:
        return VALIDATOR.run_validation(self.package, self.repository)

    def assertRejectedWith(self, needle: str) -> None:
        result = self.validate()
        self.assertEqual(result["status"], "FAIL", result)
        self.assertTrue(
            any(needle.lower() in error.lower() for error in result["errors"]),
            f"did not find {needle!r} in errors: {result['errors']}",
        )

    def test_complete_contract_passes_and_check_mode_is_read_only(self) -> None:
        first_spectrum = self.load_contract()["spectra"]["files"][0]
        self.assertFalse(
            (self.repository / first_spectrum["original_raw_path"]).exists(),
            "fixture intentionally omits the ignored global raw tree",
        )
        result = self.validate()
        self.assertEqual(result["status"], "PASS", result)
        self.assertEqual(result["spectra"]["files"], 160)
        self.assertEqual(result["source_packages"]["cards"], 24)
        self.assertEqual(result["source_packages"]["spectrum_references"], 480)
        self.assertEqual(result["source_packages"]["legacy_references"], 0)

        report = self.package / "data/static_validation.json"
        self.assertFalse(report.exists())
        with contextlib.redirect_stdout(io.StringIO()):
            return_code = VALIDATOR.main(
                [
                    "--package-root",
                    str(self.package),
                    "--repository-root",
                    str(self.repository),
                    "--check",
                ]
            )
        self.assertEqual(return_code, 0)
        self.assertFalse(report.exists(), "--check must not create static_validation.json")

    def test_factor_1000_energy_axis_is_rejected_even_with_fresh_hash(self) -> None:
        contract = self.load_contract()
        row = next(item for item in contract["spectra"]["files"] if item["family"] == "gamma")
        spectrum = self.repository / row["corrected_spectrum"]
        rewritten: list[str] = []
        for line in spectrum.read_text(encoding="utf-8").splitlines():
            fields = line.split()
            if len(fields) == 3 and fields[0] == "DP":
                line = f"DP {float(fields[1]) / 1000.0:.10e} {fields[2]}"
            rewritten.append(line)
        spectrum.write_text("\n".join(rewritten) + "\n", encoding="utf-8")
        row["corrected_sha256"] = digest(spectrum)
        row["corrected_pdf_integral"] = VALIDATOR.trapz(VALIDATOR.parse_dp(spectrum))
        self.save_contract_and_refresh_package_hashes(contract)
        self.assertRejectedWith("raw->DP energy conversion failed")

    def test_changed_flux_is_rejected_even_with_fresh_manifests(self) -> None:
        contract = self.load_contract()
        package = contract["geometries"]["mass_model_511"]
        card_row = next(item for item in package["cards"] if item["family"] == "gamma")
        source = self.repository / card_row["source"]
        lines = source.read_text(encoding="utf-8").splitlines()
        for index, line in enumerate(lines):
            if ".Flux " in line:
                prefix, value = line.rsplit(None, 1)
                lines[index] = f"{prefix} {float(value) * 2.0:.12e}"
                break
        source.write_text("\n".join(lines) + "\n", encoding="utf-8")
        parsed = VALIDATOR.parse_source_card(source)
        new_flux = float(sum((item.flux for item in parsed.definitions.values()), VALIDATOR.Decimal(0)))
        card_row["source_sha256"] = digest(source)
        card_row["flux_sum_cm2_s"] = new_flux
        self.manifest_path.write_text(
            json.dumps(contract, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        package_manifest_path = self.repository / package["source_dir"] / "source_migration_manifest.json"
        package_manifest = json.loads(package_manifest_path.read_text(encoding="utf-8"))
        source_row = next(item for item in package_manifest["sources"] if item["particle"] == "gamma")
        source_row["source_sha256"] = digest(source)
        source_row["total_flux_cm2_s"] = new_flux
        package_manifest_path.write_text(
            json.dumps(package_manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        # Refresh all global-contract hashes after both inventories honestly
        # describe the corrupted card.
        contract = self.load_contract()
        self.save_contract_and_refresh_package_hashes(contract)
        # Reapply the package-local source metadata overwritten by the helper.
        package_manifest = json.loads(package_manifest_path.read_text(encoding="utf-8"))
        source_row = next(item for item in package_manifest["sources"] if item["particle"] == "gamma")
        source_row["source_sha256"] = digest(source)
        source_row["total_flux_cm2_s"] = new_flux
        package_manifest_path.write_text(
            json.dumps(package_manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.assertRejectedWith("Flux differs from parent")

    def test_legacy_spectrum_reference_is_rejected_with_fresh_hashes(self) -> None:
        contract = self.load_contract()
        package = contract["geometries"]["s3d_o8"]
        card_row = next(item for item in package["cards"] if item["family"] == "n")
        source = self.repository / card_row["source"]
        text = source.read_text(encoding="utf-8")
        text = text.replace("/correct_keV_total/", "/cosima_spectra_dp_2602units/", 1)
        source.write_text(text, encoding="utf-8")
        card_row["source_sha256"] = digest(source)
        self.manifest_path.write_text(
            json.dumps(contract, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        package_manifest_path = self.repository / package["source_dir"] / "source_migration_manifest.json"
        package_manifest = json.loads(package_manifest_path.read_text(encoding="utf-8"))
        source_row = next(item for item in package_manifest["sources"] if item["particle"] == "n")
        source_row["source_sha256"] = digest(source)
        package_manifest_path.write_text(
            json.dumps(package_manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        contract = self.load_contract()
        self.save_contract_and_refresh_package_hashes(contract)
        package_manifest = json.loads(package_manifest_path.read_text(encoding="utf-8"))
        source_row = next(item for item in package_manifest["sources"] if item["particle"] == "n")
        source_row["source_sha256"] = digest(source)
        package_manifest_path.write_text(
            json.dumps(package_manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        self.assertRejectedWith("legacy 2602units reference is forbidden")

    def test_missing_angular_bin_is_rejected(self) -> None:
        contract = self.load_contract()
        row = next(
            item
            for item in contract["spectra"]["files"]
            if item["family"] == "alpha" and int(item["bin_id"]) == 19
        )
        (self.repository / row["corrected_spectrum"]).unlink()
        self.assertRejectedWith("missing file")

    def test_package_raw_snapshot_mutation_is_rejected(self) -> None:
        contract = self.load_contract()
        row = next(
            item
            for item in contract["spectra"]["files"]
            if item["family"] == "eplus" and int(item["bin_id"]) == 3
        )
        snapshot = self.repository / row["package_raw_snapshot_path"]
        snapshot.write_bytes(snapshot.read_bytes() + b"\n# test mutation\n")
        self.assertRejectedWith("package raw snapshot")

    def test_transitive_geometry_file_mutation_is_rejected(self) -> None:
        contract = self.load_contract()
        bundle = contract["geometries"]["s3d_o8"]["geometry_bundle"]
        row = next(
            item
            for item in bundle["files"]
            if item["scope"] == "repository"
            and item["role"] == "transitive_repository"
        )
        included_file = self.repository / row["path"]
        included_file.write_bytes(included_file.read_bytes() + b"\n# test mutation\n")
        self.assertRejectedWith("geometry file SHA-256 mismatch")


if __name__ == "__main__":
    unittest.main()

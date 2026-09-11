#!/usr/bin/env python3
"""Build a pinned LEO-versus-balloon source-input comparison.

The script is deliberately source-level only.  It does not create detector
rates, activation inventories, delayed backgrounds, or mission sensitivity.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "tes511_mplconfig"))
import matplotlib.pyplot as plt  # noqa: E402


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]
CONTRACT_PATH = PACKAGE_ROOT / "data" / "comparison_contract.json"
PIN_PATH = PACKAGE_ROOT / "data" / "pinned_input_sha256.json"
SATELLITE_INPUT = PACKAGE_ROOT / "inputs" / "cosi_dc4_pinned"
BALLOON_ROOT = REPO_ROOT / "engineering" / "particle_source_unit_repair_20260811"
TABLE_ROOT = PACKAGE_ROOT / "outputs" / "tables"
SPECTRUM_ROOT = PACKAGE_ROOT / "outputs" / "spectra"
FIGURE_ROOT = PACKAGE_ROOT / "outputs" / "figures"

FAMILIES = ("gamma", "n", "p", "alpha", "eminus", "eplus", "muminus", "muplus")
FAMILY_LABEL = {
    "gamma": "gamma",
    "n": "neutron",
    "p": "proton",
    "alpha": "alpha",
    "eminus": "electron",
    "eplus": "positron",
    "muminus": "mu-",
    "muplus": "mu+",
}
FOUR_PI = 4.0 * math.pi
TWO_PI = 2.0 * math.pi
BALLOON_BIN_OMEGA = FOUR_PI / 20.0


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass(frozen=True)
class Spectrum:
    energy_keV: np.ndarray
    density: np.ndarray
    interpolation: str
    path: Path

    def __post_init__(self) -> None:
        if self.energy_keV.ndim != 1 or self.density.ndim != 1:
            raise ValueError(f"Spectrum arrays must be one-dimensional: {self.path}")
        if len(self.energy_keV) < 2 or len(self.energy_keV) != len(self.density):
            raise ValueError(f"Invalid spectrum length: {self.path}")
        if not np.all(np.isfinite(self.energy_keV)) or not np.all(np.isfinite(self.density)):
            raise ValueError(f"Non-finite spectrum value: {self.path}")
        if not np.all(np.diff(self.energy_keV) > 0):
            raise ValueError(f"Energy is not strictly increasing: {self.path}")
        if np.any(self.energy_keV <= 0) or np.any(self.density < 0):
            raise ValueError(f"Non-positive energy or negative density: {self.path}")
        if self.interpolation not in {"linlin", "loglog"}:
            raise ValueError(f"Unsupported interpolation {self.interpolation}: {self.path}")

    @property
    def low(self) -> float:
        return float(self.energy_keV[0])

    @property
    def high(self) -> float:
        return float(self.energy_keV[-1])

    def evaluate(self, energy_keV: np.ndarray | Sequence[float] | float) -> np.ndarray:
        values = np.asarray(energy_keV, dtype=float)
        flat = values.reshape(-1)
        out = np.zeros_like(flat)
        inside = (flat >= self.low) & (flat <= self.high)
        if not np.any(inside):
            return out.reshape(values.shape)
        xin = flat[inside]
        index = np.searchsorted(self.energy_keV, xin, side="right") - 1
        index = np.clip(index, 0, len(self.energy_keV) - 2)
        x0 = self.energy_keV[index]
        x1 = self.energy_keV[index + 1]
        y0 = self.density[index]
        y1 = self.density[index + 1]
        if self.interpolation == "loglog":
            positive = (y0 > 0) & (y1 > 0)
            current = np.zeros_like(xin)
            if np.any(positive):
                t = np.log(xin[positive] / x0[positive]) / np.log(x1[positive] / x0[positive])
                current[positive] = np.exp(np.log(y0[positive]) + t * np.log(y1[positive] / y0[positive]))
            if np.any(~positive):
                t = (xin[~positive] - x0[~positive]) / (x1[~positive] - x0[~positive])
                current[~positive] = y0[~positive] + t * (y1[~positive] - y0[~positive])
            out[inside] = current
        else:
            t = (xin - x0) / (x1 - x0)
            out[inside] = y0 + t * (y1 - y0)
        out[np.isclose(flat, self.high, rtol=0.0, atol=0.0)] = self.density[-1]
        return out.reshape(values.shape)

    def integrate(self, low: float | None = None, high: float | None = None) -> float:
        low = self.low if low is None else max(float(low), self.low)
        high = self.high if high is None else min(float(high), self.high)
        if high <= low:
            return 0.0
        interior = self.energy_keV[(self.energy_keV > low) & (self.energy_keV < high)]
        grid = np.concatenate(([low], interior, [high]))
        y = self.evaluate(grid)
        total = 0.0
        for x0, x1, y0, y1 in zip(grid[:-1], grid[1:], y[:-1], y[1:]):
            if self.interpolation == "loglog" and y0 > 0 and y1 > 0:
                exponent = math.log(y1 / y0) / math.log(x1 / x0)
                if abs(exponent + 1.0) < 1e-12:
                    total += y0 * x0 * math.log(x1 / x0)
                else:
                    total += y0 * x0 * ((x1 / x0) ** (exponent + 1.0) - 1.0) / (exponent + 1.0)
            else:
                total += 0.5 * (y0 + y1) * (x1 - x0)
        return float(total)

    def normalized(self) -> "Spectrum":
        integral = self.integrate()
        if not math.isfinite(integral) or integral <= 0:
            raise ValueError(f"Spectrum has non-positive integral: {self.path}")
        return Spectrum(self.energy_keV.copy(), self.density / integral, self.interpolation, self.path)


@dataclass
class WeightedSpectrum:
    spectrum: Spectrum
    flux_cm2_s: float
    component_id: str
    family: str
    domain: str
    solid_angle_sr: float | None
    model_valid_min_keV: float | None = None
    model_valid_max_keV: float | None = None

    def evaluate_flux(self, energy_keV: np.ndarray | Sequence[float] | float) -> np.ndarray:
        return self.flux_cm2_s * self.spectrum.evaluate(energy_keV)

    def integrate_flux(self, low: float | None = None, high: float | None = None) -> float:
        return self.flux_cm2_s * self.spectrum.integrate(low, high)

    @property
    def valid_low(self) -> float:
        return max(self.spectrum.low, self.model_valid_min_keV or self.spectrum.low)

    @property
    def valid_high(self) -> float:
        return min(self.spectrum.high, self.model_valid_max_keV or self.spectrum.high)

    def evaluate_valid_flux(self, energy_keV: np.ndarray | Sequence[float] | float) -> np.ndarray:
        values = np.asarray(energy_keV, dtype=float)
        out = self.evaluate_flux(values)
        return np.where((values >= self.valid_low) & (values <= self.valid_high), out, 0.0)

    def integrate_valid_flux(self, low: float | None = None, high: float | None = None) -> float:
        low = self.valid_low if low is None else max(float(low), self.valid_low)
        high = self.valid_high if high is None else min(float(high), self.valid_high)
        return self.integrate_flux(low, high) if high > low else 0.0

    def validity_coverage(self, low: float, high: float) -> str:
        if high <= self.valid_low or low >= self.valid_high:
            return "none"
        if low >= self.valid_low and high <= self.valid_high:
            return "complete"
        return "partial"


def parse_spectrum(path: Path) -> Spectrum:
    interpolation = None
    energies: list[float] = []
    densities: list[float] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.upper().startswith("IP "):
            token = re.sub(r"[^A-Z]", "", line.upper().split(maxsplit=1)[1])
            if token in {"LIN", "LINLIN"}:
                interpolation = "linlin"
            elif token == "LOGLOG":
                interpolation = "loglog"
            else:
                raise ValueError(f"Unsupported IP token {line!r}: {path}")
        elif line.upper().startswith("DP "):
            fields = line.split()
            if len(fields) < 3:
                raise ValueError(f"Malformed DP row: {path}: {line}")
            energies.append(float(fields[1]))
            densities.append(float(fields[2]))
    if interpolation is None:
        raise ValueError(f"Missing IP declaration: {path}")
    return Spectrum(np.asarray(energies), np.asarray(densities), interpolation, path)


def parse_source_scalar(text: str, source_key: str, field: str) -> float:
    pattern = re.compile(rf"^{re.escape(source_key)}\.{re.escape(field)}\s+([^\s#]+)", re.MULTILINE)
    match = pattern.search(text)
    if match is None:
        raise ValueError(f"Missing {source_key}.{field}")
    return float(match.group(1))


def parse_source_text(text: str, source_key: str, field: str) -> str:
    pattern = re.compile(rf"^{re.escape(source_key)}\.{re.escape(field)}\s+(.+?)\s*$", re.MULTILINE)
    match = pattern.search(text)
    if match is None:
        raise ValueError(f"Missing {source_key}.{field}")
    return match.group(1).strip()


def coverage_status(spectrum: Spectrum, low: float, high: float) -> str:
    if high <= spectrum.low or low >= spectrum.high:
        return "none"
    if low >= spectrum.low and high <= spectrum.high:
        return "complete"
    return "partial"


def dense_grid(spectra: Iterable[Spectrum], points_per_decade: int = 28) -> np.ndarray:
    spectra = tuple(spectra)
    low = min(item.low for item in spectra)
    high = max(item.high for item in spectra)
    count = max(2, int(math.ceil(math.log10(high / low) * points_per_decade)) + 1)
    base = np.logspace(math.log10(low), math.log10(high), count)
    knots = np.concatenate([item.energy_keV for item in spectra])
    return np.unique(np.concatenate((base, knots)))


def write_csv(path: Path, rows: list[dict], fieldnames: Sequence[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        if not rows:
            raise ValueError(f"Cannot infer columns for empty table: {path}")
        fieldnames = tuple(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames, extrasaction="raise")
        writer.writeheader()
        writer.writerows(rows)


def write_markdown_table(path: Path, rows: list[dict], columns: Sequence[str]) -> None:
    def clean(value: object) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    lines = ["| " + " | ".join(columns) + " |", "| " + " | ".join("---" for _ in columns) + " |"]
    lines.extend("| " + " | ".join(clean(row.get(column, "")) for column in columns) + " |" for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def verify_pinned_inputs(pin_contract: dict) -> list[dict]:
    rows = []
    expected_files = pin_contract["files"]
    actual_files = {
        str(path.relative_to(SATELLITE_INPUT))
        for path in SATELLITE_INPUT.rglob("*")
        if path.is_file()
    }
    if actual_files != set(expected_files):
        missing = sorted(set(expected_files) - actual_files)
        extra = sorted(actual_files - set(expected_files))
        raise RuntimeError(f"Pinned COSI snapshot inventory mismatch; missing={missing}, extra={extra}")
    for relative_path, expected_hash in sorted(expected_files.items()):
        path = SATELLITE_INPUT / relative_path
        actual_hash = sha256(path)
        if actual_hash != expected_hash:
            raise RuntimeError(f"Pinned COSI hash mismatch: {relative_path}")
        rows.append(
            {
                "relative_path": relative_path,
                "sha256": actual_hash,
                "bytes": path.stat().st_size,
                "upstream_commit": pin_contract["commit"],
            }
        )
    return rows


def verify_balloon_authority(contract: dict) -> dict:
    manifest_path = BALLOON_ROOT / "data" / "source_contract_manifest.json"
    static_path = BALLOON_ROOT / "data" / "static_validation.json"
    actual_hash = sha256(manifest_path)
    expected_hash = contract["balloon_baseline"]["source_contract_sha256"]
    if actual_hash != expected_hash:
        raise RuntimeError(f"Balloon source contract hash mismatch: {actual_hash} != {expected_hash}")
    static = json.loads(static_path.read_text(encoding="utf-8"))
    if static.get("status") != "PASS" or static.get("source_packages", {}).get("legacy_references") != 0:
        raise RuntimeError("Corrected-keV balloon source package does not pass its static gate")
    if static.get("spectra", {}).get("files") != 160:
        raise RuntimeError("Corrected-keV balloon package does not contain exactly 160 spectra")
    return {
        "source_contract_path": str(manifest_path.relative_to(REPO_ROOT)),
        "source_contract_sha256": actual_hash,
        "static_validation_path": str(static_path.relative_to(REPO_ROOT)),
        "static_validation_status": static["status"],
        "spectrum_files": static["spectra"]["files"],
        "legacy_references": static["source_packages"]["legacy_references"],
    }


def load_balloon_spectra() -> tuple[dict[str, list[WeightedSpectrum]], list[dict], dict]:
    family_spectra: dict[str, list[WeightedSpectrum]] = {}
    angular_rows: list[dict] = []
    closure: dict[str, dict] = {}
    card_root = BALLOON_ROOT / "config" / "source_cards" / "mass_model_511"
    for family in FAMILIES:
        card_path = card_root / f"Background_{family}_fullsphere20.source"
        text = card_path.read_text(encoding="utf-8")
        if "cosima_spectra_dp_2602units" in text:
            raise RuntimeError(f"Legacy spectrum reference found in corrected card: {card_path}")
        if re.search(r"\.Spectrum\s+Mono\b", text):
            raise RuntimeError(f"Unexpected mono source in balloon broadband profile: {card_path}")
        spectrum_refs = dict(re.findall(r"^(\S+)\.Spectrum\s+File\s+(\S+)\s*$", text, re.MULTILINE))
        flux_refs = {key: float(value) for key, value in re.findall(r"^(\S+)\.Flux\s+([^\s#]+)", text, re.MULTILINE)}
        beam_refs = dict(re.findall(r"^(\S+)\.Beam\s+(.+?)\s*$", text, re.MULTILINE))
        if len(spectrum_refs) != 20 or set(spectrum_refs) != set(flux_refs):
            raise RuntimeError(f"Balloon source-card reference mismatch: {card_path}")
        weighted: list[WeightedSpectrum] = []
        for source_name, relative_spectrum in sorted(
            spectrum_refs.items(), key=lambda item: int(re.search(r"_bin(\d+)_", item[0]).group(1))
        ):
            bin_index = int(re.search(r"_bin(\d+)_", source_name).group(1))
            spectrum_path = REPO_ROOT / relative_spectrum
            parsed = parse_spectrum(spectrum_path)
            if parsed.interpolation != "linlin":
                raise RuntimeError(f"Balloon corrected spectrum is not IP LIN: {spectrum_path}")
            integral = parsed.integrate()
            if abs(integral - 1.0) > 1e-8:
                raise RuntimeError(f"Balloon PDF does not integrate to one: {spectrum_path}: {integral}")
            normalized = parsed.normalized()
            domain = "down" if bin_index < 10 else "up"
            beam = beam_refs[source_name]
            beam_numbers = [float(value) for value in re.findall(r"[-+]?\d+(?:\.\d+)?", beam)]
            if len(beam_numbers) < 4:
                raise RuntimeError(f"Cannot parse balloon Beam: {source_name}: {beam}")
            flux = flux_refs[source_name]
            item = WeightedSpectrum(normalized, flux, source_name, family, domain, BALLOON_BIN_OMEGA)
            weighted.append(item)
            for energy, pdf in zip(normalized.energy_keV, normalized.density):
                angular_rows.append(
                    {
                        "environment": "balloon_38km",
                        "profile": "unit_only_total_gamma",
                        "family": family,
                        "bin_index": bin_index,
                        "domain": domain,
                        "theta_min_deg": beam_numbers[0],
                        "theta_max_deg": beam_numbers[1],
                        "solid_angle_sr": BALLOON_BIN_OMEGA,
                        "energy_keV_total": energy,
                        "pdf_keV_inv": pdf,
                        "bin_flux_cm2_s": flux,
                        "differential_flux_cm2_s_keV": flux * pdf,
                        "support_avg_intensity_cm2_s_sr_keV": flux * pdf / BALLOON_BIN_OMEGA,
                        "source_path": str(spectrum_path.relative_to(REPO_ROOT)),
                        "source_sha256": sha256(spectrum_path),
                    }
                )
        family_spectra[family] = weighted
        down_flux = sum(item.flux_cm2_s for item in weighted if item.domain == "down")
        up_flux = sum(item.flux_cm2_s for item in weighted if item.domain == "up")
        closure[family] = {
            "down_flux_cm2_s": down_flux,
            "up_flux_cm2_s": up_flux,
            "full_flux_cm2_s": down_flux + up_flux,
            "spectrum_count": len(weighted),
        }
    return family_spectra, angular_rows, closure


def aggregate_balloon(
    family_spectra: dict[str, list[WeightedSpectrum]],
) -> tuple[list[dict], dict[tuple[str, str], list[WeightedSpectrum]]]:
    rows: list[dict] = []
    groups: dict[tuple[str, str], list[WeightedSpectrum]] = {}
    for family, spectra in family_spectra.items():
        for domain in ("down", "up", "full"):
            selected = [item for item in spectra if domain == "full" or item.domain == domain]
            groups[(family, domain)] = selected
            grid = dense_grid([item.spectrum for item in selected])
            differential = sum((item.evaluate_flux(grid) for item in selected), np.zeros_like(grid))
            omega = FOUR_PI if domain == "full" else TWO_PI
            for energy, value in zip(grid, differential):
                rows.append(
                    {
                        "environment": "balloon_38km",
                        "profile": "unit_only_total_gamma",
                        "family": family,
                        "domain": domain,
                        "solid_angle_sr": omega,
                        "energy_keV_total": energy,
                        "differential_flux_cm2_s_keV": value,
                        "energy_weighted_flux_cm2_s": energy * value,
                        "support_avg_intensity_cm2_s_sr_keV": value / omega,
                    }
                )
    return rows, groups


def load_satellite_components(contract: dict) -> tuple[dict[str, WeightedSpectrum], list[dict], list[dict]]:
    components: dict[str, WeightedSpectrum] = {}
    inventory: list[dict] = []
    lines: list[dict] = []
    deweight = float(contract["satellite_baseline"]["dc4_flux_deweight_factor"])
    for spec in contract["components"]:
        card_path = SATELLITE_INPUT / spec["source_card"]
        card_text = card_path.read_text(encoding="utf-8")
        base_inventory = {
            "component_id": spec["id"],
            "family": spec["family"],
            "kind": spec["kind"],
            "nominal": spec["nominal"],
            "angular_domain": spec["angular_domain"],
            "solid_angle_sr": spec.get("solid_angle_sr", ""),
            "cutoff_rigidity_gv": spec.get("cutoff_rigidity_gv", ""),
            "comparison_grade": spec["comparison_grade"],
            "source_card": spec["source_card"],
            "source_card_sha256": sha256(card_path),
            "source_link_status": "not_applicable",
            "simulation_flux_cm2_s": "",
            "physical_flux_cm2_s": "",
            "spectrum_header_integral_flux_cm2_s": "",
            "physical_card_to_header_ratio": "",
            "dc4_deweight_factor": "",
            "interpolation": "",
            "energy_min_keV_total": "",
            "energy_max_keV_total": "",
            "model_valid_min_keV": spec.get("model_valid_min_keV", ""),
            "model_valid_max_keV": spec.get("model_valid_max_keV", ""),
            "note": spec.get("note", ""),
        }
        if spec["kind"] == "continuum":
            spectrum_path = SATELLITE_INPUT / spec["spectrum_file"]
            parsed = parse_spectrum(spectrum_path)
            if parsed.interpolation != "loglog":
                raise RuntimeError(f"Expected COSI continuum IP LOGLOG: {spectrum_path}")
            normalized = parsed.normalized()
            simulation_flux = parse_source_scalar(card_text, spec["source_key"], "Flux")
            physical_flux = simulation_flux * deweight
            header_match = re.search(
                r"^#\s*Integral Flux:\s*([^\s#]+)", spectrum_path.read_text(encoding="utf-8"), re.MULTILINE
            )
            if header_match is None:
                raise RuntimeError(f"Missing COSI spectrum-header integral: {spectrum_path}")
            header_integral = float(header_match.group(1))
            declared = parse_source_text(card_text, spec["source_key"], "Spectrum").split()[-1]
            actual = spectrum_path.name
            link_status = "match" if declared == actual else "mismatch"
            if link_status != "match" and spec["id"] != "albedo_neutrons_10gv_proxy":
                raise RuntimeError(f"Unexpected COSI source-card spectrum mismatch: {spec['id']}: {declared} != {actual}")
            if spec["id"] == "albedo_neutrons_10gv_proxy" and link_status != "mismatch":
                raise RuntimeError("Expected the pinned DC4 neutron 12.6-GV/10-GV mismatch but did not find it")
            components[spec["id"]] = WeightedSpectrum(
                normalized,
                physical_flux,
                spec["id"],
                spec["family"],
                spec["angular_domain"],
                spec.get("solid_angle_sr"),
                spec.get("model_valid_min_keV"),
                spec.get("model_valid_max_keV"),
            )
            base_inventory.update(
                {
                    "source_link_status": link_status,
                    "simulation_flux_cm2_s": simulation_flux,
                    "physical_flux_cm2_s": physical_flux,
                    "spectrum_header_integral_flux_cm2_s": header_integral,
                    "physical_card_to_header_ratio": physical_flux / header_integral,
                    "dc4_deweight_factor": deweight,
                    "interpolation": normalized.interpolation,
                    "energy_min_keV_total": normalized.low,
                    "energy_max_keV_total": normalized.high,
                    "spectrum_sha256": sha256(spectrum_path),
                }
            )
        elif spec["kind"] == "mono":
            simulation_flux = parse_source_scalar(card_text, spec["source_key"], "Flux")
            physical_flux = simulation_flux * deweight
            declaration = parse_source_text(card_text, spec["source_key"], "Spectrum")
            fields = declaration.split()
            if len(fields) != 2 or fields[0].lower() != "mono" or float(fields[1]) != float(spec["line_energy_keV"]):
                raise RuntimeError(f"Unexpected mono declaration: {spec['id']}: {declaration}")
            line_row = {
                "component_id": spec["id"],
                "family": spec["family"],
                "line_energy_keV_total": spec["line_energy_keV"],
                "simulation_line_flux_cm2_s": simulation_flux,
                "physical_line_flux_cm2_s": physical_flux,
                "dc4_deweight_factor": deweight,
                "angular_domain": spec["angular_domain"],
                "solid_angle_sr": spec["solid_angle_sr"],
                "comparison_grade": spec["comparison_grade"],
            }
            lines.append(line_row)
            base_inventory.update(
                {
                    "source_link_status": "inline_mono",
                    "simulation_flux_cm2_s": simulation_flux,
                    "physical_flux_cm2_s": physical_flux,
                    "dc4_deweight_factor": deweight,
                    "interpolation": "delta_line",
                    "energy_min_keV_total": spec["line_energy_keV"],
                    "energy_max_keV_total": spec["line_energy_keV"],
                }
            )
        inventory.append(base_inventory)
    return components, inventory, lines


def write_satellite_spectra(components: dict[str, WeightedSpectrum]) -> list[dict]:
    rows: list[dict] = []
    restored_root = SPECTRUM_ROOT / "cosi_dc4_physical_restored_unit_pdf"
    restored_root.mkdir(parents=True, exist_ok=True)
    for component_id, item in sorted(components.items()):
        output_path = restored_root / f"{component_id}.spectrum"
        lines = [
            "# Pinned COSI DC4 spectral shape, normalized to a unit PDF.",
            "# Physical flux is stored separately in outputs/tables/component_inventory.csv.",
            "# Energy axis: total kinetic energy in keV; density: keV^-1.",
            "# NOT a transport-ready source card; preserve the component's angular support.",
            "IP LOGLOG",
        ]
        for energy, pdf in zip(item.spectrum.energy_keV, item.spectrum.density):
            lines.append(f"DP {energy:.17e} {pdf:.17e}")
            rows.append(
                {
                    "environment": "satellite_leo530_proxy",
                    "profile": "cosi_dc4_physical_restored",
                    "component_id": component_id,
                    "family": item.family,
                    "angular_domain": item.domain,
                    "solid_angle_sr": item.solid_angle_sr if item.solid_angle_sr is not None else "",
                    "energy_keV_total": energy,
                    "pdf_keV_inv": pdf,
                    "physical_flux_cm2_s": item.flux_cm2_s,
                    "differential_flux_cm2_s_keV": item.flux_cm2_s * pdf,
                    "energy_weighted_flux_cm2_s": energy * item.flux_cm2_s * pdf,
                    "within_cited_model_validity": item.valid_low <= energy <= item.valid_high,
                    "validity_filtered_differential_flux_cm2_s_keV": (
                        item.flux_cm2_s * pdf if item.valid_low <= energy <= item.valid_high else ""
                    ),
                    "support_avg_intensity_cm2_s_sr_keV": (
                        item.flux_cm2_s * pdf / item.solid_angle_sr if item.solid_angle_sr else ""
                    ),
                    "restored_spectrum_path": str(output_path.relative_to(PACKAGE_ROOT)),
                }
            )
        lines.append("EN")
        output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return rows


def build_satellite_profiles(
    components: dict[str, WeightedSpectrum], contract: dict
) -> tuple[dict[str, dict[str, list[WeightedSpectrum]]], list[dict]]:
    profile_groups: dict[str, dict[str, list[WeightedSpectrum]]] = {}
    rows: list[dict] = []
    profiles = {
        "satellite_nominal_continuum": contract["profiles"]["satellite_nominal_continuum"],
        "satellite_diagnostic_neutron_proxy": contract["profiles"]["satellite_diagnostic_neutron_proxy"],
    }
    for profile_name, component_ids in profiles.items():
        grouped: dict[str, list[WeightedSpectrum]] = {}
        for component_id in component_ids:
            if component_id not in components:
                continue
            grouped.setdefault(components[component_id].family, []).append(components[component_id])
        profile_groups[profile_name] = grouped
        for family, selected in grouped.items():
            grid = dense_grid([item.spectrum for item in selected])
            differential = sum((item.evaluate_flux(grid) for item in selected), np.zeros_like(grid))
            valid_differential = sum((item.evaluate_valid_flux(grid) for item in selected), np.zeros_like(grid))
            for energy, value, valid_value in zip(grid, differential, valid_differential):
                rows.append(
                    {
                        "environment": "satellite_leo530_proxy",
                        "profile": profile_name,
                        "family": family,
                        "domain": "mixed_component_support" if len(selected) > 1 else selected[0].domain,
                        "component_count": len(selected),
                        "energy_keV_total": energy,
                        "differential_flux_cm2_s_keV": value,
                        "energy_weighted_flux_cm2_s": energy * value,
                        "validity_filtered_differential_flux_cm2_s_keV": valid_value if valid_value > 0 else "",
                        "validity_filtered_energy_weighted_flux_cm2_s": energy * valid_value if valid_value > 0 else "",
                    }
                )
    return profile_groups, rows


def exact_group_band_flux(items: list[WeightedSpectrum], low: float, high: float) -> float:
    return sum(item.integrate_flux(low, high) for item in items)


def exact_group_valid_band_flux(items: list[WeightedSpectrum], low: float, high: float) -> float:
    return sum(item.integrate_valid_flux(low, high) for item in items)


def group_coverage(items: list[WeightedSpectrum], low: float, high: float) -> str:
    states = {coverage_status(item.spectrum, low, high) for item in items}
    if states == {"complete"}:
        return "complete"
    if states == {"none"}:
        return "none"
    return "partial_or_mixed"


def group_validity_coverage(items: list[WeightedSpectrum], low: float, high: float) -> str:
    states = {item.validity_coverage(low, high) for item in items}
    if states == {"complete"}:
        return "complete"
    if states == {"none"}:
        return "none"
    return "partial_or_mixed"


def build_band_tables(
    contract: dict,
    balloon_groups: dict[tuple[str, str], list[WeightedSpectrum]],
    satellite_components: dict[str, WeightedSpectrum],
    satellite_profiles: dict[str, dict[str, list[WeightedSpectrum]]],
    line_rows: list[dict],
) -> tuple[list[dict], list[dict]]:
    band_rows: list[dict] = []
    line_by_family = {row["family"]: row for row in line_rows}
    for band in contract["bands_keV"]:
        low, high = float(band["low"]), float(band["high"])
        for (family, domain), items in sorted(balloon_groups.items()):
            band_rows.append(
                {
                    "environment": "balloon_38km",
                    "profile": "unit_only_total_gamma",
                    "component_or_family": family,
                    "family": family,
                    "domain": domain,
                    "band": band["id"],
                    "low_keV": low,
                    "high_keV": high,
                    "band_flux_cm2_s": exact_group_band_flux(items, low, high),
                    "validity_filtered_band_flux_cm2_s": exact_group_valid_band_flux(items, low, high),
                    "coverage": group_coverage(items, low, high),
                    "model_validity_coverage": group_validity_coverage(items, low, high),
                    "comparison_grade": "B",
                }
            )
        for component_id, item in sorted(satellite_components.items()):
            band_rows.append(
                {
                    "environment": "satellite_leo530_proxy",
                    "profile": "component_physical_restored",
                    "component_or_family": component_id,
                    "family": item.family,
                    "domain": item.domain,
                    "band": band["id"],
                    "low_keV": low,
                    "high_keV": high,
                    "band_flux_cm2_s": item.integrate_flux(low, high),
                    "validity_filtered_band_flux_cm2_s": item.integrate_valid_flux(low, high),
                    "coverage": coverage_status(item.spectrum, low, high),
                    "model_validity_coverage": item.validity_coverage(low, high),
                    "comparison_grade": "C" if component_id == "albedo_neutrons_10gv_proxy" else "B",
                }
            )
        for profile_name, grouped in satellite_profiles.items():
            for family, items in grouped.items():
                band_rows.append(
                    {
                        "environment": "satellite_leo530_proxy",
                        "profile": profile_name,
                        "component_or_family": family,
                        "family": family,
                        "domain": "mixed_component_support" if len(items) > 1 else items[0].domain,
                        "band": band["id"],
                        "low_keV": low,
                        "high_keV": high,
                        "band_flux_cm2_s": exact_group_band_flux(items, low, high),
                        "validity_filtered_band_flux_cm2_s": exact_group_valid_band_flux(items, low, high),
                        "coverage": group_coverage(items, low, high),
                        "model_validity_coverage": group_validity_coverage(items, low, high),
                        "comparison_grade": "C" if profile_name.endswith("neutron_proxy") else "B",
                    }
                )
        for line in line_rows:
            line_flux = line["physical_line_flux_cm2_s"] if low <= line["line_energy_keV_total"] < high else 0.0
            band_rows.append(
                {
                    "environment": "satellite_leo530_proxy",
                    "profile": "delta_line_component",
                    "component_or_family": line["component_id"],
                    "family": line["family"],
                    "domain": line["angular_domain"],
                    "band": band["id"],
                    "low_keV": low,
                    "high_keV": high,
                    "band_flux_cm2_s": line_flux,
                    "validity_filtered_band_flux_cm2_s": line_flux,
                    "coverage": "delta_inside" if line_flux else "delta_outside",
                    "model_validity_coverage": "delta_inside" if line_flux else "delta_outside",
                    "comparison_grade": "C",
                }
            )

    contrasts: list[dict] = []
    nominal = satellite_profiles["satellite_nominal_continuum"]
    neutron_proxy = satellite_profiles["satellite_diagnostic_neutron_proxy"]
    for band in contract["bands_keV"]:
        low, high = float(band["low"]), float(band["high"])
        for family in FAMILIES:
            balloon_items = balloon_groups[(family, "full")]
            if family in nominal:
                satellite_items = nominal[family]
                profile = "satellite_nominal_continuum"
                grade = "B"
            elif family == "n" and family in neutron_proxy:
                satellite_items = neutron_proxy[family]
                profile = "satellite_diagnostic_neutron_proxy"
                grade = "C"
            else:
                contrasts.append(
                    {
                        "family": family,
                        "band": band["id"],
                        "balloon_full_flux_cm2_s": exact_group_band_flux(balloon_items, low, high),
                        "satellite_profile": "unavailable",
                        "satellite_flux_cm2_s": "",
                        "satellite_to_balloon_ratio": "",
                        "satellite_model_validity_coverage": "unavailable",
                        "comparison_grade": "NA",
                        "interpretation": "Satellite component unavailable; absence is not zero.",
                    }
                )
                continue
            balloon_flux = exact_group_band_flux(balloon_items, low, high)
            satellite_flux = exact_group_valid_band_flux(satellite_items, low, high)
            validity = group_validity_coverage(satellite_items, low, high)
            interpretation = "Environment contrast only; orbit, angular support, epoch, and model differ."
            if family == "n":
                interpretation = "Diagnostic only: pinned DC4 neutron card has a 12.6-GV/10-GV dangling reference."
            if family == "gamma" and band["id"] == "450_600_keV_annihilation_region_proxy":
                satellite_flux += line_by_family["gamma"]["physical_line_flux_cm2_s"]
                profile = "satellite_nominal_gamma_continuum_plus_atmospheric_511"
                grade = "C"
                interpretation = "Broad annihilation-region proxy, not a line-flux ratio; satellite delta line is included."
            if validity == "none":
                contrasts.append(
                    {
                        "family": family,
                        "band": band["id"],
                        "balloon_full_flux_cm2_s": balloon_flux,
                        "satellite_profile": profile,
                        "satellite_flux_cm2_s": "",
                        "satellite_to_balloon_ratio": "",
                        "satellite_model_validity_coverage": validity,
                        "comparison_grade": "NA",
                        "interpretation": "Band is outside the cited validity/support of the available satellite component(s); no zero is imputed.",
                    }
                )
                continue
            if validity != "complete" and grade == "B":
                interpretation += " Only components within cited validity contribute to this band value."
            contrasts.append(
                {
                    "family": family,
                    "band": band["id"],
                    "balloon_full_flux_cm2_s": balloon_flux,
                    "satellite_profile": profile,
                    "satellite_flux_cm2_s": satellite_flux,
                    "satellite_to_balloon_ratio": satellite_flux / balloon_flux if balloon_flux > 0 else "",
                    "satellite_model_validity_coverage": validity,
                    "comparison_grade": grade,
                    "interpretation": interpretation,
                }
            )
    return band_rows, contrasts


def curve_from_items(items: list[WeightedSpectrum], grid: np.ndarray) -> np.ndarray:
    return sum((item.evaluate_flux(grid) for item in items), np.zeros_like(grid))


def valid_curve_from_items(items: list[WeightedSpectrum], grid: np.ndarray) -> np.ndarray:
    return sum((item.evaluate_valid_flux(grid) for item in items), np.zeros_like(grid))


def configure_plotting() -> None:
    plt.rcParams.update(
        {
            "figure.dpi": 140,
            "savefig.dpi": 220,
            "font.size": 9.5,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "legend.fontsize": 8,
            "axes.grid": True,
            "grid.alpha": 0.22,
            "grid.linestyle": ":",
            "axes.spines.top": False,
            "axes.spines.right": False,
        }
    )


def save_figure(fig: plt.Figure, stem: str) -> None:
    fig.savefig(FIGURE_ROOT / f"{stem}.png", bbox_inches="tight")
    fig.savefig(FIGURE_ROOT / f"{stem}.pdf", bbox_inches="tight")
    plt.close(fig)


def plot_gamma(
    balloon_groups: dict[tuple[str, str], list[WeightedSpectrum]],
    components: dict[str, WeightedSpectrum],
    line_rows: list[dict],
) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13.2, 5.1), gridspec_kw={"width_ratios": [1.5, 1.0]})
    balloon_grid = np.logspace(math.log10(10.0), math.log10(1.0e7), 600)
    colors = {"full": "#173F5F", "down": "#20639B", "up": "#3CAEA3"}
    styles = {"full": "-", "down": "--", "up": ":"}
    for domain in ("full", "down", "up"):
        values = curve_from_items(balloon_groups[("gamma", domain)], balloon_grid)
        mask = values > 0
        axes[0].loglog(
            balloon_grid[mask],
            balloon_grid[mask] * values[mask],
            styles[domain],
            color=colors[domain],
            lw=2.25 if domain == "full" else 1.45,
            label=f"Balloon {domain}",
        )
    component_style = {
        "albedo_photons_continuum": ("#F28E2B", "--", "LEO albedo continuum"),
        "cosmic_photons": ("#8E5EA2", "-.", "LEO cosmic continuum"),
    }
    sat_items = [components[key] for key in component_style]
    sat_grid = np.logspace(math.log10(100.0), math.log10(1.0e7), 500)
    for component_id, (color, style, label) in component_style.items():
        values = components[component_id].evaluate_flux(sat_grid)
        mask = values > 0
        axes[0].loglog(sat_grid[mask], sat_grid[mask] * values[mask], style, color=color, lw=1.8, label=label)
    nominal = curve_from_items(sat_items, sat_grid)
    mask = nominal > 0
    axes[0].loglog(sat_grid[mask], sat_grid[mask] * nominal[mask], color="#111111", lw=2.0, dashes=(5, 2), label="LEO nominal continuum sum")
    axes[0].axvspan(450, 600, color="#D62728", alpha=0.08)
    axes[0].axvline(511, color="#D62728", lw=1.2, ls=":")
    line_flux = line_rows[0]["physical_line_flux_cm2_s"]
    axes[0].text(
        0.98,
        0.04,
        f"LEO atmospheric 511 delta line\nintegrated flux = {line_flux:.4g} cm$^{{-2}}$ s$^{{-1}}$\n(not plotted as a continuum density)",
        transform=axes[0].transAxes,
        ha="right",
        va="bottom",
        color="#9C1C1C",
        fontsize=8.3,
        bbox={"facecolor": "white", "edgecolor": "#D8D8D8", "alpha": 0.9, "pad": 4},
    )
    axes[0].set_xlim(10, 1.0e7)
    axes[0].set_xlabel("Total kinetic energy [keV]")
    axes[0].set_ylabel(r"$E\,dF/dE$ [cm$^{-2}$ s$^{-1}$]")
    axes[0].set_title("Broadband gamma environment")
    axes[0].legend(loc="upper right", ncol=2)

    zoom_grid = np.unique(
        np.concatenate(
            (
                np.linspace(300, 800, 350),
                *[item.spectrum.energy_keV[(item.spectrum.energy_keV >= 300) & (item.spectrum.energy_keV <= 800)] for item in sat_items],
            )
        )
    )
    balloon_full = curve_from_items(balloon_groups[("gamma", "full")], zoom_grid)
    axes[1].semilogy(zoom_grid, zoom_grid * balloon_full, color=colors["full"], lw=2.2, label="Balloon full (IP LIN)")
    for component_id, (color, style, label) in component_style.items():
        item = components[component_id]
        values = item.evaluate_flux(zoom_grid)
        axes[1].semilogy(zoom_grid, zoom_grid * values, style, color=color, lw=1.8, label=label)
        knots = item.spectrum.energy_keV[(item.spectrum.energy_keV >= 300) & (item.spectrum.energy_keV <= 800)]
        if len(knots):
            axes[1].scatter(knots, knots * item.evaluate_flux(knots), s=18, facecolor="white", edgecolor=color, zorder=4)
    balloon_knots = balloon_groups[("gamma", "full")][0].spectrum.energy_keV
    balloon_knots = balloon_knots[(balloon_knots >= 300) & (balloon_knots <= 800)]
    axes[1].scatter(
        balloon_knots,
        balloon_knots * curve_from_items(balloon_groups[("gamma", "full")], balloon_knots),
        s=24,
        color=colors["full"],
        zorder=5,
        label="Balloon native knots",
    )
    axes[1].axvspan(450, 600, color="#D62728", alpha=0.08)
    axes[1].axvline(511, color="#D62728", lw=1.3, ls=":")
    axes[1].set_xlim(300, 800)
    axes[1].set_xlabel("Total kinetic energy [keV]")
    axes[1].set_ylabel(r"$E\,dF/dE$ [cm$^{-2}$ s$^{-1}$]")
    axes[1].set_title("300–800 keV native-knot view")
    axes[1].text(
        0.03,
        0.05,
        "Balloon table has a coarse broadband bump,\nnot a resolved 511-keV line.",
        transform=axes[1].transAxes,
        ha="left",
        va="bottom",
        fontsize=8.4,
        bbox={"facecolor": "white", "edgecolor": "#D8D8D8", "alpha": 0.9, "pad": 4},
    )
    axes[1].legend(loc="upper right")
    fig.suptitle("LEO 530-km proxy vs corrected 38-km balloon gamma sources", fontsize=14, y=1.02)
    fig.text(
        0.5,
        0.965,
        "Angular-domain integrated incident flux; COSI DC4 physical flux restored ×1000; no orbit weighting; Galactic diffuse and SAA excluded",
        ha="center",
        fontsize=9,
        color="#4A4A4A",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save_figure(fig, "gamma_source_comparison")


def plot_particle_families(
    balloon_groups: dict[tuple[str, str], list[WeightedSpectrum]],
    components: dict[str, WeightedSpectrum],
) -> None:
    layout = [
        ("p", ["primary_proton", "secondary_proton"]),
        ("alpha", ["primary_alpha"]),
        ("eminus", ["primary_electron", "secondary_electron"]),
        ("eplus", ["primary_positron", "secondary_positron"]),
        ("n", ["albedo_neutrons_10gv_proxy"]),
        ("muons", []),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(14.0, 8.3))
    axes = axes.ravel()
    sat_colors = ["#F28E2B", "#59A14F"]
    for ax, (family, component_ids) in zip(axes, layout):
        if family == "muons":
            ax.axis("off")
            ax.text(0.5, 0.62, "Muon components", ha="center", va="center", fontsize=12, weight="bold")
            ax.text(
                0.5,
                0.42,
                "Balloon: μ− and μ+ available\nCOSI DC4 LEO library: unavailable\n\nMissing is not zero.",
                ha="center",
                va="center",
                fontsize=10,
                bbox={"facecolor": "#F7F7F7", "edgecolor": "#C8C8C8", "pad": 12},
            )
            continue
        selected_balloon = balloon_groups[(family, "full")]
        selected_sat = [components[key] for key in component_ids]
        low = min(min(item.spectrum.low for item in selected_balloon), min(item.valid_low for item in selected_sat))
        high = max(max(item.spectrum.high for item in selected_balloon), max(item.valid_high for item in selected_sat))
        grid = np.logspace(math.log10(low), math.log10(high), 480)
        for domain, style, color, width in (
            ("full", "-", "#173F5F", 2.1),
            ("down", "--", "#20639B", 1.15),
            ("up", ":", "#3CAEA3", 1.3),
        ):
            values = curve_from_items(balloon_groups[(family, domain)], grid)
            mask = values > 0
            ax.loglog(grid[mask], grid[mask] * values[mask], style, color=color, lw=width, label=f"Balloon {domain}")
        for index, item in enumerate(selected_sat):
            values = item.evaluate_valid_flux(grid)
            mask = values > 0
            label = item.component_id.replace("_", " ")
            if item.component_id == "albedo_neutrons_10gv_proxy":
                label = "LEO neutron 10-GV proxy*"
            ax.loglog(grid[mask], grid[mask] * values[mask], "-.", color=sat_colors[index], lw=1.6, label=label)
        if len(selected_sat) > 1:
            total = valid_curve_from_items(selected_sat, grid)
            mask = total > 0
            ax.loglog(grid[mask], grid[mask] * total[mask], color="#111111", lw=1.7, dashes=(4, 2), label="LEO component sum")
        ax.set_title(FAMILY_LABEL[family].title() + (" (diagnostic)" if family == "n" else ""))
        ax.set_xlabel("Total kinetic energy [keV]")
        ax.set_ylabel(r"$E\,dF/dE$ [cm$^{-2}$ s$^{-1}$]")
        ax.legend(loc="best", fontsize=7.2)
        if family == "n":
            ax.text(0.02, 0.03, "* DC4 card names 12.6 GV; pinned file is 10 GV.", transform=ax.transAxes, fontsize=7.5)
    fig.suptitle("Particle-family source comparison: LEO 530-km proxy vs balloon 38 km", fontsize=14, y=1.01)
    fig.text(
        0.5,
        0.965,
        "Domain-integrated physical number flux; primary and secondary LEO components remain separate; no detector response or orbit-time weighting",
        ha="center",
        fontsize=9,
        color="#4A4A4A",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save_figure(fig, "particle_family_source_comparison")


def plot_shape_comparison(
    balloon_groups: dict[tuple[str, str], list[WeightedSpectrum]],
    satellite_profiles: dict[str, dict[str, list[WeightedSpectrum]]],
) -> None:
    families = ("gamma", "p", "alpha", "eminus", "eplus", "n")
    nominal = satellite_profiles["satellite_nominal_continuum"]
    neutron = satellite_profiles["satellite_diagnostic_neutron_proxy"]
    fig, axes = plt.subplots(2, 3, figsize=(13.7, 8.0))
    for ax, family in zip(axes.ravel(), families):
        balloon = balloon_groups[(family, "full")]
        satellite = neutron[family] if family == "n" else nominal[family]
        low = max(min(item.spectrum.low for item in balloon), min(item.valid_low for item in satellite))
        high = min(max(item.spectrum.high for item in balloon), max(item.valid_high for item in satellite))
        grid = np.logspace(math.log10(low), math.log10(high), 500)
        balloon_curve = curve_from_items(balloon, grid)
        satellite_curve = valid_curve_from_items(satellite, grid)
        balloon_norm = exact_group_band_flux(balloon, low, high)
        satellite_norm = exact_group_valid_band_flux(satellite, low, high)
        q_balloon = grid * balloon_curve / balloon_norm
        q_satellite = grid * satellite_curve / satellite_norm
        mask_b = q_balloon > 0
        mask_s = q_satellite > 0
        ax.loglog(grid[mask_b], q_balloon[mask_b], color="#173F5F", lw=2.0, label="Balloon full")
        ax.loglog(grid[mask_s], q_satellite[mask_s], "--", color="#F28E2B", lw=1.8, label="LEO profile")
        ax.set_title(FAMILY_LABEL[family].title() + (" (10-GV proxy)" if family == "n" else ""))
        ax.set_xlabel("Total kinetic energy [keV]")
        ax.set_ylabel(r"$q(E)=E f(E)/\int f\,dE$")
        ax.legend(loc="best")
        ax.text(
            0.02,
            0.03,
            f"Common support:\n{low:.2g}–{high:.2g} keV",
            transform=ax.transAxes,
            fontsize=7.5,
            bbox={"facecolor": "white", "edgecolor": "#DDDDDD", "alpha": 0.85, "pad": 3},
        )
    fig.suptitle("Common-support spectral-shape comparison", fontsize=14, y=1.01)
    fig.text(
        0.5,
        0.965,
        "Each curve has unit integral over its stated common energy support; this removes absolute flux and angular-support normalization",
        ha="center",
        fontsize=9,
        color="#4A4A4A",
    )
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    save_figure(fig, "common_support_shape_comparison")


def build_summary(
    contract: dict,
    authority: dict,
    closure: dict,
    inventory: list[dict],
    lines: list[dict],
    contrasts: list[dict],
) -> dict:
    physical_flux = {
        row["component_id"]: row["physical_flux_cm2_s"]
        for row in inventory
        if row["physical_flux_cm2_s"] != ""
    }
    selected_contrasts = [
        row
        for row in contrasts
        if row["band"] in {"450_600_keV_annihilation_region_proxy", "1_10_MeV"}
        and row["family"] in {"gamma", "p", "alpha", "eminus", "eplus", "n"}
    ]
    return {
        "schema_version": 1,
        "status": "BUILT__SOURCE_INPUT_COMPARISON__NOT_TRANSPORT_AUTHORITY",
        "satellite_baseline": contract["satellite_baseline"],
        "balloon_authority": authority,
        "balloon_flux_closure_cm2_s": closure,
        "satellite_physical_flux_cm2_s": physical_flux,
        "satellite_atmospheric_511_line": lines[0],
        "selected_environment_contrasts": selected_contrasts,
        "upstream_issues": [
            {
                "id": "cosi_dc4_neutron_dangling_reference",
                "severity": "material_for_neutron_baseline",
                "detail": "AlbedoNeutrons.source declares a 12.6-GV spectrum filename, but the pinned DC4 directory contains only the 10-GV file. The 10-GV spectrum is diagnostic-only.",
            },
            {
                "id": "dc4_1000_way_parallel_shard_flux_scaling",
                "severity": "must_restore_for_physical_comparison",
                "detail": "The DC4 normal-background source rates are per one of 1000 intentional parallel simulation shards. Outputs retain both per-shard card rates and merged physical rates; plots use the latter.",
            },
        ],
        "interpretation_boundary": [
            "This package compares source inputs, not detector count rates, activation, delayed background, sensitivity, or geometry ranking.",
            "The LEO baseline is a COSI DC4 proxy for a future 511-CAM satellite, not a final orbit definition.",
            "No orbit-time weighting, SAA residence, pointing history, Earth-limb history, or solar-cycle ensemble is applied.",
            "The balloon broadband gamma table already contains a coarse annihilation bump and cannot provide a line-only atmospheric-511 normalization.",
        ],
    }


def main() -> None:
    TABLE_ROOT.mkdir(parents=True, exist_ok=True)
    SPECTRUM_ROOT.mkdir(parents=True, exist_ok=True)
    FIGURE_ROOT.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    pins = json.loads(PIN_PATH.read_text(encoding="utf-8"))
    input_rows = verify_pinned_inputs(pins)
    authority = verify_balloon_authority(contract)
    balloon_spectra, balloon_angular_rows, closure = load_balloon_spectra()
    balloon_aggregate_rows, balloon_groups = aggregate_balloon(balloon_spectra)
    satellite_components, inventory, line_rows = load_satellite_components(contract)
    satellite_component_rows = write_satellite_spectra(satellite_components)
    satellite_profiles, satellite_profile_rows = build_satellite_profiles(satellite_components, contract)
    band_rows, contrasts = build_band_tables(
        contract, balloon_groups, satellite_components, satellite_profiles, line_rows
    )

    write_csv(TABLE_ROOT / "pinned_source_files.csv", input_rows)
    write_csv(TABLE_ROOT / "component_inventory.csv", inventory)
    write_markdown_table(
        TABLE_ROOT / "component_inventory.md",
        inventory,
        (
            "component_id",
            "family",
            "kind",
            "nominal",
            "angular_domain",
            "physical_flux_cm2_s",
            "source_link_status",
            "comparison_grade",
            "note",
        ),
    )
    write_csv(TABLE_ROOT / "balloon_angular_spectra_long.csv", balloon_angular_rows)
    write_csv(TABLE_ROOT / "balloon_aggregated_spectra.csv", balloon_aggregate_rows)
    write_csv(TABLE_ROOT / "satellite_component_spectra.csv", satellite_component_rows)
    write_csv(TABLE_ROOT / "satellite_profile_spectra.csv", satellite_profile_rows)
    write_csv(TABLE_ROOT / "satellite_line_components.csv", line_rows)
    write_csv(TABLE_ROOT / "band_integrals.csv", band_rows)
    write_csv(TABLE_ROOT / "environment_contrasts.csv", contrasts)

    configure_plotting()
    plot_gamma(balloon_groups, satellite_components, line_rows)
    plot_particle_families(balloon_groups, satellite_components)
    plot_shape_comparison(balloon_groups, satellite_profiles)

    summary = build_summary(contract, authority, closure, inventory, line_rows, contrasts)
    (PACKAGE_ROOT / "outputs" / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": summary["status"], "output_root": str(PACKAGE_ROOT / "outputs")}, indent=2))


if __name__ == "__main__":
    main()

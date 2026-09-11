#!/usr/bin/env python3
"""Build the non-overwriting six-band conditional proton source package.

This builder is intentionally inert until the review-owned science contract is
present.  It never starts Cosima and never edits the corrected-keV parent cards
or spectra.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any


THIS_FILE = Path(__file__).resolve()
CODE_DIR = THIS_FILE.parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

import p0_common as common  # noqa: E402


SCIENCE_CONTRACT = common.SCIENCE_CONTRACT
DERIVATION_STATUS = "PASS__P0_SIXBAND_CONDITIONAL_SOURCE_DERIVATION"


def _science_edges(payload: dict[str, Any]) -> tuple[Decimal, ...]:
    if payload.get("schema_version") != 1 or payload.get("status") != "FROZEN__P0_SIXBAND_SCIENCE_CONTRACT":
        raise RuntimeError("P0 science contract is not frozen")
    raw = payload.get("energy_edges_keV")
    if not isinstance(raw, list) or len(raw) != 7:
        raise RuntimeError("P0 science contract must contain seven ordered energy edges")
    edges = tuple(Decimal(str(value)) for value in raw)
    if any(right <= left for left, right in zip(edges, edges[1:])):
        raise RuntimeError("P0 science-contract energy edges are not strictly increasing")
    if payload.get("band_count") != 6:
        raise RuntimeError("P0 science-contract band count is not six")
    if Decimal(str(payload.get("total_flux_cm2_s"))) != common.TOTAL_FLUX_DECIMAL:
        raise RuntimeError("P0 science-contract total Flux differs from the corrected parent")
    return edges


def _conditional_text(
    *,
    parent: Path,
    band_key: str,
    low: Decimal,
    high: Decimal,
    points: list[tuple[Decimal, Decimal]],
) -> str:
    lines = [
        "# Package-owned conditional view of the corrected-keV proton PDF.",
        f"# parent_corrected_spectrum={common.rel(parent)}",
        f"# energy_band={band_key}",
        f"# band_low_keV={format(low, 'f')}",
        f"# band_high_keV={format(high, 'f')}",
        "# policy=piecewise-linear restriction plus unit trapezoidal renormalization",
        "# physical normalization lives in the derived source-card partial Flux",
        "IP LIN",
    ]
    # Keep substantially more than binary64 precision so the serialized
    # conditional trapezoid remains auditable as unit-normalized.
    lines.extend(f"DP {format(x, '.24e')} {format(y, '.24e')}" for x, y in points)
    return "\n".join(lines) + "\n"


def _render_band_card(
    parent_text: str,
    *,
    band_key: str,
    spectrum_by_bin: dict[int, Path],
    flux_by_bin: dict[int, Decimal],
) -> str:
    seen_spectrum: set[int] = set()
    seen_flux: set[int] = set()
    output: list[str] = []
    for raw in parent_text.splitlines():
        stripped = raw.strip()
        if match := common.SPECTRUM_RE.match(stripped):
            angular_bin = int(match.group("bin"))
            seen_spectrum.add(angular_bin)
            output.append(
                f"{match.group('name')}.Spectrum File {common.rel(spectrum_by_bin[angular_bin])}"
            )
        elif match := common.FLUX_RE.match(stripped):
            angular_bin = int(match.group("bin"))
            seen_flux.add(angular_bin)
            # Do not round the proven Decimal residual closure at publication.
            output.append(f"{match.group('name')}.Flux {format(flux_by_bin[angular_bin], 'f')}")
        else:
            output.append(raw)
    if seen_spectrum != set(range(20)) or seen_flux != set(range(20)):
        raise RuntimeError(f"{band_key}: parent card does not expose exact 20 Spectrum/Flux rows")
    return "\n".join(output) + "\n"


def allowed_band_card_diff(
    parent_text: str,
    derived_text: str,
) -> dict[str, Any]:
    parent_lines = parent_text.splitlines()
    derived_lines = derived_text.splitlines()
    if len(parent_lines) != len(derived_lines):
        raise RuntimeError("derived band card line count differs from corrected parent")
    spectrum_diffs = 0
    flux_diffs = 0
    forbidden: list[int] = []
    for line_number, (parent, derived) in enumerate(zip(parent_lines, derived_lines, strict=True), 1):
        if parent == derived:
            continue
        if common.SPECTRUM_RE.match(parent.strip()) and common.SPECTRUM_RE.match(derived.strip()):
            spectrum_diffs += 1
        elif common.FLUX_RE.match(parent.strip()) and common.FLUX_RE.match(derived.strip()):
            flux_diffs += 1
        else:
            forbidden.append(line_number)
    if spectrum_diffs != 20 or flux_diffs != 20 or forbidden:
        raise RuntimeError(
            "derived conditional source allowed-diff failure: "
            f"Spectrum={spectrum_diffs}, Flux={flux_diffs}, forbidden={forbidden}"
        )
    return {
        "spectrum_file_line_differences": spectrum_diffs,
        "partial_flux_line_differences": flux_diffs,
        "all_other_lines_byte_equal": True,
    }


def derive_payload(
    edges: tuple[Decimal, ...],
    *,
    output_root: Path,
) -> tuple[dict[str, Any], dict[Path, bytes]]:
    if len(edges) != 7:
        raise RuntimeError("derive_payload requires seven energy edges")
    mass_records = common.parent_card_records(common.PARENT_SOURCE["mass_model_511"])
    for geometry in common.GEOMETRIES[1:]:
        records = common.parent_card_records(common.PARENT_SOURCE[geometry])
        if records["flux"] != mass_records["flux"]:
            raise RuntimeError(f"{geometry}: proton angular Flux differs from Mass parent")
        if tuple(records["beams"].values()) != tuple(mass_records["beams"].values()):
            raise RuntimeError(f"{geometry}: proton Beam rows differ from Mass parent")

    files: dict[Path, bytes] = {}
    spectra_records: list[dict[str, Any]] = []
    band_flux_by_bin: dict[int, list[Decimal]] = {index: [] for index in range(20)}
    band_spectrum_by_bin: dict[int, dict[int, Path]] = {index: {} for index in range(6)}
    integrals_by_bin: dict[int, list[Decimal]] = {}
    with localcontext() as context:
        context.prec = 160
        for angular_bin in range(20):
            parent = mass_records["spectra"][angular_bin]
            points = common.parse_dp_decimal(parent)
            if edges[0] != points[0][0] or edges[-1] != points[-1][0]:
                raise RuntimeError(
                    f"science edges must exactly span corrected support for bin{angular_bin:02d}: "
                    f"{points[0][0]}..{points[-1][0]}"
                )
            total_integral = common.integrate_linear(points)
            band_integrals: list[Decimal] = []
            for band_index, (low, high) in enumerate(zip(edges, edges[1:])):
                conditional, integral = common.conditional_points(points, low, high)
                band_integrals.append(integral)
                target = (
                    output_root
                    / "spectra/conditional_keV_total"
                    / f"p_bin{angular_bin:02d}_b{band_index}_conditional_pdf.spectrum"
                )
                files[target] = _conditional_text(
                    parent=parent,
                    band_key=f"b{band_index}",
                    low=low,
                    high=high,
                    points=conditional,
                ).encode("utf-8")
                band_spectrum_by_bin[band_index][angular_bin] = target
                spectra_records.append(
                    {
                        "band": f"b{band_index}",
                        "angular_bin": angular_bin,
                        "parent_corrected_spectrum": common.rel(parent),
                        "parent_corrected_spectrum_sha256": common.sha256(parent),
                        "path": common.rel(target),
                        "low_keV": format(low, "f"),
                        "high_keV": format(high, "f"),
                        "parent_integral": format(total_integral, "f"),
                        "band_integral_before_renormalization": format(integral, "f"),
                        "conditional_integral": "1",
                    }
                )
            raw_band_integrals = list(band_integrals)
            closure_error = sum(raw_band_integrals, Decimal(0)) - total_integral
            # Independent Decimal integrations can differ by one final context
            # ulp (observed 1E-70) even though the six intervals tile exactly.
            # Preserve the raw value used to normalize each conditional PDF,
            # but residualize the last *Flux-fraction* integral so the physical
            # angular Flux closes exactly and deterministically.
            closure_tolerance = max(abs(total_integral), Decimal(1)) * Decimal("1e-60")
            if abs(closure_error) > closure_tolerance:
                raise RuntimeError(
                    f"bin{angular_bin:02d}: band-integral closure error is too large: {closure_error}"
                )
            with localcontext() as exact_context:
                exact_context.prec = 400
                band_integrals[-1] = total_integral - sum(band_integrals[:5], Decimal(0))
                if band_integrals[-1] <= 0 or sum(band_integrals, Decimal(0)) != total_integral:
                    raise RuntimeError(f"bin{angular_bin:02d}: residual band integral does not close")
            for band_index, (raw_integral, flux_integral) in enumerate(
                zip(raw_band_integrals, band_integrals, strict=True)
            ):
                record = spectra_records[-6 + band_index]
                record["conditional_normalization_integral"] = format(raw_integral, "f")
                record["band_integral_for_flux_fraction"] = format(flux_integral, "f")
                record["flux_integral_residualized"] = band_index == 5
            parent_flux = mass_records["flux"][angular_bin]
            partial = [parent_flux * value / total_integral for value in band_integrals[:5]]
            with localcontext() as exact_context:
                exact_context.prec = 400
                partial.append(parent_flux - sum(partial, Decimal(0)))
                if any(value <= 0 for value in partial) or sum(partial, Decimal(0)) != parent_flux:
                    raise RuntimeError(f"bin{angular_bin:02d}: partial Flux residual closure failed")
            band_flux_by_bin[angular_bin] = partial
            integrals_by_bin[angular_bin] = band_integrals

    # The per-angle values carry ~70 significant Decimal digits.  Aggregate
    # them above the default Decimal precision so associativity rounding does
    # not manufacture a false all-angle closure error.
    with localcontext() as context:
        context.prec = 400
        band_totals = [
            sum(
                (band_flux_by_bin[angular_bin][band_index] for angular_bin in range(20)),
                Decimal(0),
            )
            for band_index in range(6)
        ]
        if sum(band_totals, Decimal(0)) != common.TOTAL_FLUX_DECIMAL:
            raise RuntimeError("all-angle/all-band partial Flux does not exactly close")

    geometry_records: dict[str, Any] = {}
    for geometry in common.GEOMETRIES:
        parent = common.PARENT_SOURCE[geometry]
        parent_text = parent.read_text(encoding="utf-8")
        cards: list[dict[str, Any]] = []
        for band_index in range(6):
            target = output_root / "config/source_cards" / geometry / f"Background_p_fullsphere20_b{band_index}.source"
            derived = _render_band_card(
                parent_text,
                band_key=f"b{band_index}",
                spectrum_by_bin=band_spectrum_by_bin[band_index],
                flux_by_bin={
                    angular_bin: band_flux_by_bin[angular_bin][band_index]
                    for angular_bin in range(20)
                },
            )
            allowed = allowed_band_card_diff(parent_text, derived)
            files[target] = derived.encode("utf-8")
            cards.append(
                {
                    "band": f"b{band_index}",
                    "path": common.rel(target),
                    "sha256": "__FILLED_AFTER_RENDER__",
                    "partial_flux_cm2_s": format(band_totals[band_index], "f"),
                    "allowed_diff": allowed,
                }
            )
        geometry_records[geometry] = {
            "parent_source": common.rel(parent),
            "parent_source_sha256": common.sha256(parent),
            "geometry": common.rel(common.parent_card_records(parent)["geometry"]),
            "band_source_cards": cards,
        }

    for row in spectra_records:
        path = common.resolve_path(row["path"])
        row["sha256"] = __import__("hashlib").sha256(files[path]).hexdigest()
    for geometry in common.GEOMETRIES:
        for row in geometry_records[geometry]["band_source_cards"]:
            path = common.resolve_path(row["path"])
            row["sha256"] = __import__("hashlib").sha256(files[path]).hexdigest()

    with localcontext() as context:
        context.prec = 400
        bands = [
            {
                "index": index,
                "key": f"b{index}",
                "low_keV": format(edges[index], "f"),
                "high_keV": format(edges[index + 1], "f"),
                "high_inclusive": index == 5,
                "flux_cm2_s": format(band_totals[index], "f"),
                "weight": format(band_totals[index] / common.TOTAL_FLUX_DECIMAL, "f"),
            }
            for index in range(6)
        ]
        # Residualize the last serialized weight to make the Decimal sum exact.
        last_weight = Decimal(1) - sum((Decimal(row["weight"]) for row in bands[:5]), Decimal(0))
    bands[-1]["weight"] = format(last_weight, "f")
    payload = {
        "schema_version": 1,
        "status": DERIVATION_STATUS,
        "derivation": (
            "per angular bin: piecewise-linear corrected PDF restriction; conditional PDF unit "
            "trapezoid; partial Flux=parent Flux*band integral/parent integral; band5 Decimal residual"
        ),
        "authority_boundary": (
            "full-support weighted P0 pilot source strata only; not unweighted full-spectrum, "
            "full-stat, sensitivity, or geometry-promotion authority"
        ),
        "source_contract_manifest": common.rel(common.SOURCE_CONTRACT),
        "source_contract_manifest_sha256": common.SOURCE_CONTRACT_SHA256,
        "science_contract": common.rel(SCIENCE_CONTRACT),
        "science_contract_sha256": common.sha256(SCIENCE_CONTRACT),
        "total_flux_cm2_s": format(common.TOTAL_FLUX_DECIMAL, "f"),
        "bands": bands,
        "angular_bin_partial_flux": [
            {
                "angular_bin": angular_bin,
                "parent_flux_cm2_s": format(mass_records["flux"][angular_bin], "f"),
                "partial_flux_cm2_s": [format(value, "f") for value in band_flux_by_bin[angular_bin]],
                "exact_residual_closure": True,
            }
            for angular_bin in range(20)
        ],
        "conditional_spectra": spectra_records,
        "geometries": geometry_records,
        "normalization": {
            "prompt_rate": "sum over bands of selected_count_band / sum_TT_band",
            "activation_rate": (
                "sum over bands of RP_band / sum_TT_band within geometry+volume+isotope+state"
            ),
            "per_primary_efficiency": (
                "sum over bands of band_flux_weight * selected_count_band / primary_count_band"
            ),
            "forbidden": [
                "sum(all selected counts)/sum(all band TT)",
                "unweighted pooling of the 6 equal-N strata",
                "calling omitted or partial bands a full spectrum",
            ],
        },
        "events_per_cell": common.EVENTS_PER_CELL,
        "shards_per_cell": common.SHARDS_PER_CELL,
        "events_per_shard": common.EVENTS_PER_SHARD,
    }
    return payload, files


def validate_published_package_exact(manifest: dict[str, Any]) -> dict[str, Any]:
    """Replay the corrected-parent derivation and require exact published bytes."""

    common.validate_source_manifest(manifest, verify_files=True)
    bands = common.bands_from_manifest(manifest)
    edges = (bands[0].low_keV, *(band.high_keV for band in bands))
    expected_manifest, expected_files = derive_payload(tuple(edges), output_root=common.P0_ROOT)
    if manifest != expected_manifest:
        raise RuntimeError("published manifest differs from exact corrected-parent derivation replay")
    for path, expected_bytes in expected_files.items():
        if not path.is_file() or path.read_bytes() != expected_bytes:
            raise RuntimeError(
                f"published derived artifact differs from exact corrected-parent replay: {common.rel(path)}"
            )
    return {
        "status": "PASS__P0_EXACT_PARENT_DERIVATION_REPLAY",
        "manifest_sha256": common.sha256(common.SOURCE_MANIFEST),
        "derived_artifacts": len(expected_files),
    }


def write_package(payload: dict[str, Any], files: dict[Path, bytes]) -> None:
    manifest = common.SOURCE_MANIFEST
    if manifest.exists():
        raise RuntimeError(f"refusing to overwrite frozen source manifest: {common.rel(manifest)}")
    temporary_root = Path(tempfile.mkdtemp(prefix=".p0-source-build-", dir=common.P0_ROOT))
    created_targets: list[Path] = []
    manifest_created = False
    try:
        for target, data in files.items():
            relative = target.resolve().relative_to(common.P0_ROOT.resolve())
            temporary = temporary_root / relative
            temporary.parent.mkdir(parents=True, exist_ok=True)
            temporary.write_bytes(data)
        # Ensure no target exists before a non-overwriting move into place.
        for target in files:
            if target.exists():
                raise RuntimeError(f"refusing to overwrite derived source artifact: {common.rel(target)}")
        for target in sorted(files, key=lambda path: (len(path.parts), str(path))):
            temporary = temporary_root / target.resolve().relative_to(common.P0_ROOT.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            os.link(temporary, target)
            created_targets.append(target)
        manifest_created = common.atomic_write_once_json(manifest, payload)
        validate_published_package_exact(common.load_json_strict(manifest))
    except BaseException:
        # Only files created by this invocation may be removed on failure.
        for target in created_targets:
            try:
                target.unlink()
            except FileNotFoundError:
                pass
        if manifest_created:
            try:
                manifest.unlink()
            except FileNotFoundError:
                pass
        raise
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--print-plan",
        action="store_true",
        help="validate the frozen science contract and print the derivation without writing",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="write the non-overwriting conditional spectra/cards/manifest; never starts transport",
    )
    args = parser.parse_args()
    if args.print_plan == args.write:
        parser.error("choose exactly one of --print-plan or --write")
    if not SCIENCE_CONTRACT.is_file():
        print(
            json.dumps(
                {
                    "status": "WAIT__P0_SIXBAND_SCIENCE_CONTRACT_NOT_FROZEN",
                    "transport_launched": False,
                    "science_contract": common.rel(SCIENCE_CONTRACT),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 3
    science = common.load_json_strict(SCIENCE_CONTRACT)
    edges = _science_edges(science)
    payload, files = derive_payload(edges, output_root=common.P0_ROOT)
    if args.print_plan:
        print(
            json.dumps(
                {
                    "status": "PASS__P0_SOURCE_DERIVATION_PLAN_READY",
                    "transport_launched": False,
                    "energy_edges_keV": [format(value, "f") for value in edges],
                    "total_flux_cm2_s": payload["total_flux_cm2_s"],
                    "band_flux_cm2_s": [row["flux_cm2_s"] for row in payload["bands"]],
                    "files_to_create": len(files) + 1,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    write_package(payload, files)
    print(
        json.dumps(
            {
                "status": DERIVATION_STATUS,
                "transport_launched": False,
                "manifest": common.rel(common.SOURCE_MANIFEST),
                "manifest_sha256": common.sha256(common.SOURCE_MANIFEST),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

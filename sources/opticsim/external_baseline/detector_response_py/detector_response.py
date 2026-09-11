from __future__ import annotations

import csv
import json
import math
import os
import random
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import yaml


SIGMA_TO_FWHM = 2.3548200450309493


@dataclass(frozen=True)
class AbsorberConfig:
    material: str
    n_layers: int
    pixels_x: int
    pixels_y: int
    pixel_size_x_mm: float
    pixel_size_y_mm: float
    layer_thickness_mm: float
    gap_mm: float
    stack_detection_efficiency: float

    @property
    def active_width_x_mm(self) -> float:
        return self.pixels_x * self.pixel_size_x_mm + max(0, self.pixels_x - 1) * self.gap_mm

    @property
    def active_width_y_mm(self) -> float:
        return self.pixels_y * self.pixel_size_y_mm + max(0, self.pixels_y - 1) * self.gap_mm

    @property
    def layer_absorption_probability(self) -> float:
        if self.stack_detection_efficiency >= 1.0:
            return 1.0
        return 1.0 - (1.0 - self.stack_detection_efficiency) ** (1.0 / self.n_layers)


@dataclass(frozen=True)
class TESConfig:
    threshold_keV: float
    pixel_resolution_fwhm_eV_at_511: float
    reconstructed_resolution_fwhm_eV_at_511: float
    full_energy_peak_fraction: float
    multihit_fraction: float
    tail_energy_range_keV: Tuple[float, float]

    @property
    def reco_sigma_keV(self) -> float:
        return (self.reconstructed_resolution_fwhm_eV_at_511 / 1000.0) / SIGMA_TO_FWHM


@dataclass(frozen=True)
class BGOConfig:
    enabled: bool
    side_thickness_cm: float
    bottom_thickness_cm: float
    threshold_keV: float
    resolution_fwhm_keV: float
    signal_self_veto_probability: float
    passthrough_detection_probability: float


@dataclass(frozen=True)
class SelectionConfig:
    line_window_keV: Tuple[float, float]
    require_no_bgo_veto: bool


@dataclass(frozen=True)
class DetectorConfig:
    system: str
    model: str
    warning: str
    expected_energy_keV: float
    detector_plane_z_mm: Optional[float]
    absorber: AbsorberConfig
    tes: TESConfig
    bgo: BGOConfig
    selection: SelectionConfig


@dataclass(frozen=True)
class PhaseSpacePhoton:
    event_id: int
    E_keV: float
    x_mm: float
    y_mm: float
    z_mm: float
    ux: float
    uy: float
    uz: float
    weight: float
    source_tag: str


@dataclass(frozen=True)
class DetectorHit:
    event_id: int
    track_id: int
    detector_kind: str
    layer_id: int
    pixel_i: int
    pixel_j: int
    pixel_uid: str
    x_mm: float
    y_mm: float
    z_mm: float
    edep_keV: float
    process_name: str
    time_ns: float


@dataclass(frozen=True)
class DetectorEventSummary:
    event_id: int
    status: str
    x_det_mm: float
    y_det_mm: float
    total_tes_edep_keV: float
    n_tes_pixel_hits: int
    is_singlehit: int
    is_multihit: int
    bgo_edep_keV: float
    bgo_veto: int
    reco_energy_keV: float
    in_line_window: int
    selected_signal: int
    weight: float


def _as_probability(value: float, name: str) -> float:
    v = float(value)
    if not (0.0 <= v <= 1.0):
        raise ValueError(f"{name} must be within [0, 1]")
    return v


def load_detector_config(path: str | Path) -> DetectorConfig:
    with Path(path).open() as f:
        raw = yaml.safe_load(f)
    absorber_raw = raw["absorber"]
    pixel_size = absorber_raw["pixel_size_mm"]
    absorber = AbsorberConfig(
        material=str(absorber_raw["material"]),
        n_layers=int(absorber_raw["n_layers"]),
        pixels_x=int(absorber_raw["pixels_x"]),
        pixels_y=int(absorber_raw["pixels_y"]),
        pixel_size_x_mm=float(pixel_size[0]),
        pixel_size_y_mm=float(pixel_size[1]),
        layer_thickness_mm=float(pixel_size[2]),
        gap_mm=float(absorber_raw.get("gap_mm", 0.0)),
        stack_detection_efficiency=_as_probability(absorber_raw["stack_detection_efficiency"], "stack_detection_efficiency"),
    )
    tes_raw = raw["tes"]
    tes = TESConfig(
        threshold_keV=float(tes_raw["threshold_keV"]),
        pixel_resolution_fwhm_eV_at_511=float(tes_raw["pixel_resolution_fwhm_eV_at_511"]),
        reconstructed_resolution_fwhm_eV_at_511=float(tes_raw["reconstructed_resolution_fwhm_eV_at_511"]),
        full_energy_peak_fraction=_as_probability(tes_raw["full_energy_peak_fraction"], "full_energy_peak_fraction"),
        multihit_fraction=_as_probability(tes_raw["multihit_fraction"], "multihit_fraction"),
        tail_energy_range_keV=(float(tes_raw["tail_energy_range_keV"][0]), float(tes_raw["tail_energy_range_keV"][1])),
    )
    bgo_raw = raw["bgo"]
    bgo = BGOConfig(
        enabled=bool(bgo_raw["enabled"]),
        side_thickness_cm=float(bgo_raw["side_thickness_cm"]),
        bottom_thickness_cm=float(bgo_raw["bottom_thickness_cm"]),
        threshold_keV=float(bgo_raw["threshold_keV"]),
        resolution_fwhm_keV=float(bgo_raw["resolution_fwhm_keV"]),
        signal_self_veto_probability=_as_probability(
            bgo_raw["signal_self_veto_probability"], "signal_self_veto_probability"
        ),
        passthrough_detection_probability=_as_probability(
            bgo_raw["passthrough_detection_probability"], "passthrough_detection_probability"
        ),
    )
    selection_raw = raw["selection"]
    selection = SelectionConfig(
        line_window_keV=(float(selection_raw["line_window_keV"][0]), float(selection_raw["line_window_keV"][1])),
        require_no_bgo_veto=bool(selection_raw["require_no_bgo_veto"]),
    )
    cfg = DetectorConfig(
        system=str(raw["system"]),
        model=str(raw["model"]),
        warning=str(raw.get("warning", "")),
        expected_energy_keV=float(raw["source"]["expected_energy_keV"]),
        detector_plane_z_mm=(
            None
            if raw["source"].get("detector_plane_z_mm") is None
            else float(raw["source"]["detector_plane_z_mm"])
        ),
        absorber=absorber,
        tes=tes,
        bgo=bgo,
        selection=selection,
    )
    validate_detector_config(cfg)
    return cfg


def validate_detector_config(cfg: DetectorConfig) -> None:
    if cfg.expected_energy_keV <= 0.0:
        raise ValueError("expected_energy_keV must be positive")
    if cfg.absorber.n_layers <= 0 or cfg.absorber.pixels_x <= 0 or cfg.absorber.pixels_y <= 0:
        raise ValueError("absorber layer and pixel counts must be positive")
    if cfg.absorber.pixel_size_x_mm <= 0.0 or cfg.absorber.pixel_size_y_mm <= 0.0:
        raise ValueError("pixel dimensions must be positive")
    if cfg.absorber.gap_mm < 0.0:
        raise ValueError("gap_mm must be non-negative")
    lo, hi = cfg.tes.tail_energy_range_keV
    if not (0.0 <= lo <= hi <= cfg.expected_energy_keV):
        raise ValueError("tail_energy_range_keV must be ordered and no higher than expected energy")
    line_lo, line_hi = cfg.selection.line_window_keV
    if line_lo >= line_hi:
        raise ValueError("line window must be ordered")


def read_phase_space_csv(path: str | Path) -> List[PhaseSpacePhoton]:
    rows: List[PhaseSpacePhoton] = []
    with Path(path).open(newline="") as f:
        for row in csv.DictReader(f):
            rows.append(
                PhaseSpacePhoton(
                    event_id=int(row["event_id"]),
                    E_keV=float(row["E_keV"]),
                    x_mm=float(row["x_mm"]),
                    y_mm=float(row["y_mm"]),
                    z_mm=float(row["z_mm"]),
                    ux=float(row["ux"]),
                    uy=float(row["uy"]),
                    uz=float(row["uz"]),
                    weight=float(row["weight"]),
                    source_tag=str(row["source_tag"]),
                )
            )
    return rows


def propagate_to_detector_plane(photon: PhaseSpacePhoton, detector_plane_z_mm: Optional[float]) -> Tuple[float, float, float]:
    if detector_plane_z_mm is None or math.isclose(detector_plane_z_mm, photon.z_mm, rel_tol=0.0, abs_tol=1e-9):
        return photon.x_mm, photon.y_mm, photon.z_mm
    if abs(photon.uz) < 1.0e-12:
        return float("nan"), float("nan"), detector_plane_z_mm
    t_mm = (detector_plane_z_mm - photon.z_mm) / photon.uz
    return photon.x_mm + photon.ux * t_mm, photon.y_mm + photon.uy * t_mm, detector_plane_z_mm


def pixel_index(x_mm: float, y_mm: float, absorber: AbsorberConfig) -> Optional[Tuple[int, int]]:
    i = _axis_pixel_index(x_mm, absorber.active_width_x_mm, absorber.pixel_size_x_mm, absorber.gap_mm, absorber.pixels_x)
    j = _axis_pixel_index(y_mm, absorber.active_width_y_mm, absorber.pixel_size_y_mm, absorber.gap_mm, absorber.pixels_y)
    if i is None or j is None:
        return None
    return i, j


def _axis_pixel_index(coord_mm: float, width_mm: float, pixel_mm: float, gap_mm: float, n: int) -> Optional[int]:
    local = coord_mm + 0.5 * width_mm
    if local < 0.0 or local >= width_mm:
        return None
    if gap_mm == 0.0:
        idx = int(local / pixel_mm)
        return idx if 0 <= idx < n else None
    pitch = pixel_mm + gap_mm
    idx = int(local / pitch)
    if idx < 0 or idx >= n:
        return None
    in_cell = local - idx * pitch
    if in_cell >= pixel_mm:
        return None
    return idx


def pixel_uid(layer_id: int, pixel_i: int, pixel_j: int) -> str:
    return f"L{layer_id:02d}_I{pixel_i:02d}_J{pixel_j:02d}"


def simulate_detector_response(
    cfg: DetectorConfig,
    photons: Sequence[PhaseSpacePhoton],
    seed: int = 12345,
) -> Tuple[List[DetectorHit], List[DetectorEventSummary]]:
    rng = random.Random(seed)
    hits: List[DetectorHit] = []
    summaries: List[DetectorEventSummary] = []
    for photon in photons:
        event_hits, summary = trace_detector_event(cfg, photon, rng)
        hits.extend(event_hits)
        summaries.append(summary)
    return hits, summaries


def trace_detector_event(
    cfg: DetectorConfig,
    photon: PhaseSpacePhoton,
    rng: random.Random,
) -> Tuple[List[DetectorHit], DetectorEventSummary]:
    x_det_mm, y_det_mm, z_det_mm = propagate_to_detector_plane(photon, cfg.detector_plane_z_mm)
    pix = pixel_index(x_det_mm, y_det_mm, cfg.absorber)
    hits: List[DetectorHit] = []
    status = "MISS_ACTIVE_AREA"
    reco_energy_keV = 0.0
    bgo_edep_keV = 0.0
    bgo_veto = 0

    if pix is not None:
        layer_id = _sample_absorber_layer(cfg.absorber, rng)
        if layer_id is None:
            status = "TES_NOT_ABSORBED"
            if cfg.bgo.enabled and rng.random() < cfg.bgo.passthrough_detection_probability:
                bgo_edep_keV = _sample_bgo_edep(cfg, rng)
                bgo_veto = int(bgo_edep_keV >= cfg.bgo.threshold_keV)
                hits.append(_make_bgo_hit(photon.event_id, x_det_mm, y_det_mm, z_det_mm, bgo_edep_keV))
        else:
            status = "TES_DETECTED"
            reco_energy_keV = _sample_reco_energy(cfg, photon.E_keV, rng)
            tes_hits = _make_tes_hits(cfg, photon.event_id, pix, layer_id, x_det_mm, y_det_mm, z_det_mm, reco_energy_keV, rng)
            hits.extend(tes_hits)
            if cfg.bgo.enabled and rng.random() < cfg.bgo.signal_self_veto_probability:
                bgo_edep_keV = _sample_bgo_edep(cfg, rng)
                bgo_veto = int(bgo_edep_keV >= cfg.bgo.threshold_keV)
                hits.append(_make_bgo_hit(photon.event_id, x_det_mm, y_det_mm, z_det_mm, bgo_edep_keV))
                if bgo_veto:
                    status = "TES_DETECTED_BGO_VETO"

    tes_edep = sum(hit.edep_keV for hit in hits if hit.detector_kind == "TES_PIXEL")
    unique_pixels = {hit.pixel_uid for hit in hits if hit.detector_kind == "TES_PIXEL" and hit.edep_keV >= cfg.tes.threshold_keV}
    n_tes_pixel_hits = len(unique_pixels)
    in_line = int(cfg.selection.line_window_keV[0] <= reco_energy_keV <= cfg.selection.line_window_keV[1])
    passes_veto = (not cfg.selection.require_no_bgo_veto) or not bool(bgo_veto)
    selected = int(tes_edep >= cfg.tes.threshold_keV and in_line and passes_veto)
    summary = DetectorEventSummary(
        event_id=photon.event_id,
        status=status,
        x_det_mm=x_det_mm,
        y_det_mm=y_det_mm,
        total_tes_edep_keV=tes_edep,
        n_tes_pixel_hits=n_tes_pixel_hits,
        is_singlehit=int(n_tes_pixel_hits == 1),
        is_multihit=int(n_tes_pixel_hits > 1),
        bgo_edep_keV=bgo_edep_keV,
        bgo_veto=bgo_veto,
        reco_energy_keV=reco_energy_keV,
        in_line_window=in_line,
        selected_signal=selected,
        weight=photon.weight,
    )
    return hits, summary


def _sample_absorber_layer(absorber: AbsorberConfig, rng: random.Random) -> Optional[int]:
    p_layer = absorber.layer_absorption_probability
    for layer_id in range(absorber.n_layers):
        if rng.random() < p_layer:
            return layer_id
    return None


def _sample_reco_energy(cfg: DetectorConfig, input_energy_keV: float, rng: random.Random) -> float:
    if rng.random() < cfg.tes.full_energy_peak_fraction:
        nominal = input_energy_keV
    else:
        lo, hi = cfg.tes.tail_energy_range_keV
        nominal = rng.uniform(lo, hi)
    sigma = cfg.tes.reco_sigma_keV
    return nominal if sigma <= 0.0 else rng.gauss(nominal, sigma)


def _make_tes_hits(
    cfg: DetectorConfig,
    event_id: int,
    pix: Tuple[int, int],
    layer_id: int,
    x_mm: float,
    y_mm: float,
    z_mm: float,
    reco_energy_keV: float,
    rng: random.Random,
) -> List[DetectorHit]:
    i, j = pix
    if rng.random() >= cfg.tes.multihit_fraction:
        return [
            DetectorHit(
                event_id=event_id,
                track_id=1,
                detector_kind="TES_PIXEL",
                layer_id=layer_id,
                pixel_i=i,
                pixel_j=j,
                pixel_uid=pixel_uid(layer_id, i, j),
                x_mm=x_mm,
                y_mm=y_mm,
                z_mm=z_mm + layer_id * cfg.absorber.layer_thickness_mm,
                edep_keV=reco_energy_keV,
                process_name="CALIBRATED_TES_FULL_OR_TAIL",
                time_ns=0.0,
            )
        ]

    ni, nj = _neighbor_pixel(i, j, cfg.absorber, rng)
    split = rng.uniform(0.25, 0.75)
    first = reco_energy_keV * split
    second = reco_energy_keV - first
    second_layer = min(cfg.absorber.n_layers - 1, layer_id + 1)
    return [
        DetectorHit(
            event_id=event_id,
            track_id=1,
            detector_kind="TES_PIXEL",
            layer_id=layer_id,
            pixel_i=i,
            pixel_j=j,
            pixel_uid=pixel_uid(layer_id, i, j),
            x_mm=x_mm,
            y_mm=y_mm,
            z_mm=z_mm + layer_id * cfg.absorber.layer_thickness_mm,
            edep_keV=first,
            process_name="CALIBRATED_TES_SPLIT",
            time_ns=0.0,
        ),
        DetectorHit(
            event_id=event_id,
            track_id=1,
            detector_kind="TES_PIXEL",
            layer_id=second_layer,
            pixel_i=ni,
            pixel_j=nj,
            pixel_uid=pixel_uid(second_layer, ni, nj),
            x_mm=x_mm,
            y_mm=y_mm,
            z_mm=z_mm + second_layer * cfg.absorber.layer_thickness_mm,
            edep_keV=second,
            process_name="CALIBRATED_TES_SPLIT",
            time_ns=0.0,
        ),
    ]


def _neighbor_pixel(i: int, j: int, absorber: AbsorberConfig, rng: random.Random) -> Tuple[int, int]:
    candidates = []
    for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ni, nj = i + di, j + dj
        if 0 <= ni < absorber.pixels_x and 0 <= nj < absorber.pixels_y:
            candidates.append((ni, nj))
    return rng.choice(candidates) if candidates else (i, j)


def _sample_bgo_edep(cfg: DetectorConfig, rng: random.Random) -> float:
    sigma = cfg.bgo.resolution_fwhm_keV / SIGMA_TO_FWHM
    return max(0.0, rng.gauss(cfg.expected_energy_keV, sigma))


def _make_bgo_hit(event_id: int, x_mm: float, y_mm: float, z_mm: float, edep_keV: float) -> DetectorHit:
    return DetectorHit(
        event_id=event_id,
        track_id=1,
        detector_kind="BGO",
        layer_id=-1,
        pixel_i=-1,
        pixel_j=-1,
        pixel_uid="BGO",
        x_mm=x_mm,
        y_mm=y_mm,
        z_mm=z_mm,
        edep_keV=edep_keV,
        process_name="CALIBRATED_BGO_VETO",
        time_ns=0.0,
    )


def summarize_detector_response(
    cfg: DetectorConfig,
    photons: Sequence[PhaseSpacePhoton],
    hits: Sequence[DetectorHit],
    events: Sequence[DetectorEventSummary],
    seed: int,
    source_path: str | Path,
) -> Dict[str, object]:
    n = len(events)
    n_inside_active = sum(1 for e in events if e.status != "MISS_ACTIVE_AREA")
    n_tes_detected = sum(1 for e in events if e.total_tes_edep_keV >= cfg.tes.threshold_keV)
    n_unvetoed_detected = sum(
        1 for e in events if e.total_tes_edep_keV >= cfg.tes.threshold_keV and not e.bgo_veto
    )
    n_line_unvetoed = sum(1 for e in events if e.selected_signal)
    n_bgo_veto = sum(1 for e in events if e.bgo_veto)
    n_tes_detected_bgo_veto = sum(
        1 for e in events if e.total_tes_edep_keV >= cfg.tes.threshold_keV and e.bgo_veto
    )
    n_singlehit = sum(1 for e in events if e.is_singlehit)
    n_multihit = sum(1 for e in events if e.is_multihit)
    peak_energies = [
        e.reco_energy_keV
        for e in events
        if e.total_tes_edep_keV >= cfg.tes.threshold_keV
        and cfg.selection.line_window_keV[0] <= e.reco_energy_keV <= cfg.selection.line_window_keV[1]
    ]
    mean_peak = sum(peak_energies) / len(peak_energies) if peak_energies else 0.0
    if len(peak_energies) > 1:
        var = sum((e - mean_peak) ** 2 for e in peak_energies) / (len(peak_energies) - 1)
        measured_fwhm_eV = math.sqrt(var) * SIGMA_TO_FWHM * 1000.0
    else:
        measured_fwhm_eV = 0.0
    status_counts: Dict[str, int] = {}
    for event in events:
        status_counts[event.status] = status_counts.get(event.status, 0) + 1
    return {
        "system": cfg.system,
        "model": cfg.model,
        "warning": cfg.warning,
        "seed": seed,
        "source_phase_space": str(source_path),
        "source_tag": photons[0].source_tag if photons else "",
        "n_input_photons": n,
        "expected_energy_keV": cfg.expected_energy_keV,
        "tes_material": cfg.absorber.material,
        "tes_layers": cfg.absorber.n_layers,
        "tes_pixels": [cfg.absorber.pixels_x, cfg.absorber.pixels_y],
        "tes_active_width_mm": [cfg.absorber.active_width_x_mm, cfg.absorber.active_width_y_mm],
        "configured_stack_detection_efficiency": cfg.absorber.stack_detection_efficiency,
        "configured_reconstructed_fwhm_eV_at_511": cfg.tes.reconstructed_resolution_fwhm_eV_at_511,
        "configured_full_energy_peak_fraction": cfg.tes.full_energy_peak_fraction,
        "line_window_keV": list(cfg.selection.line_window_keV),
        "n_inside_active_pixel": n_inside_active,
        "geometric_acceptance": n_inside_active / n if n else 0.0,
        "n_tes_detected": n_tes_detected,
        "tes_detection_fraction_total": n_tes_detected / n if n else 0.0,
        "tes_detection_given_active": n_tes_detected / n_inside_active if n_inside_active else 0.0,
        "n_bgo_veto": n_bgo_veto,
        "n_tes_detected_bgo_veto": n_tes_detected_bgo_veto,
        "bgo_veto_fraction_total": n_bgo_veto / n if n else 0.0,
        "bgo_veto_fraction_of_tes_detected": n_tes_detected_bgo_veto / n_tes_detected if n_tes_detected else 0.0,
        "n_singlehit": n_singlehit,
        "n_multihit": n_multihit,
        "singlehit_fraction_of_tes_detected": n_singlehit / n_tes_detected if n_tes_detected else 0.0,
        "multihit_fraction_of_tes_detected": n_multihit / n_tes_detected if n_tes_detected else 0.0,
        "n_unvetoed_detected": n_unvetoed_detected,
        "n_selected_line_window": n_line_unvetoed,
        "selected_fraction_total": n_line_unvetoed / n if n else 0.0,
        "line_window_fraction_of_unvetoed_detected": n_line_unvetoed / n_unvetoed_detected if n_unvetoed_detected else 0.0,
        "measured_peak_mean_keV": mean_peak,
        "measured_peak_fwhm_eV": measured_fwhm_eV,
        "n_hits": len(hits),
        "status_counts": status_counts,
    }


def write_hits_csv(path: str | Path, hits: Iterable[DetectorHit]) -> None:
    rows = [asdict(h) for h in hits]
    fields = list(DetectorHit.__dataclass_fields__.keys())
    with Path(path).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def write_event_summary_csv(path: str | Path, events: Iterable[DetectorEventSummary]) -> None:
    rows = [asdict(e) for e in events]
    fields = list(DetectorEventSummary.__dataclass_fields__.keys())
    with Path(path).open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def plot_detector_spectrum(path: str | Path, events: Sequence[DetectorEventSummary], cfg: DetectorConfig) -> None:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/opticsim_mpl")
    import matplotlib.pyplot as plt

    energies = [e.reco_energy_keV for e in events if e.total_tes_edep_keV >= cfg.tes.threshold_keV and not e.bgo_veto]
    fig, ax = plt.subplots(figsize=(6.5, 4.5), dpi=140)
    ax.hist(energies, bins=160, range=(470.0, 512.5), color="#2563eb", alpha=0.8)
    ax.axvspan(cfg.selection.line_window_keV[0], cfg.selection.line_window_keV[1], color="#16a34a", alpha=0.18)
    ax.set_xlabel("reconstructed energy [keV]")
    ax.set_ylabel("events")
    ax.set_title("Detector-only TES reconstructed spectrum")
    ax.grid(True, alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_detector_pixel_map(path: str | Path, hits: Sequence[DetectorHit], cfg: DetectorConfig) -> None:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/opticsim_mpl")
    import matplotlib.pyplot as plt

    counts = [[0 for _ in range(cfg.absorber.pixels_x)] for _ in range(cfg.absorber.pixels_y)]
    for hit in hits:
        if hit.detector_kind == "TES_PIXEL":
            counts[hit.pixel_j][hit.pixel_i] += 1
    fig, ax = plt.subplots(figsize=(5.8, 5.2), dpi=140)
    im = ax.imshow(counts, origin="lower", cmap="viridis")
    ax.set_xlabel("pixel i")
    ax.set_ylabel("pixel j")
    ax.set_title("TES pixel hit map")
    fig.colorbar(im, ax=ax, label="hits")
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def plot_detector_outcomes(path: str | Path, summary: Dict[str, object]) -> None:
    os.environ.setdefault("MPLCONFIGDIR", "/tmp/opticsim_mpl")
    import matplotlib.pyplot as plt

    counts = dict(summary["status_counts"])
    labels = list(counts.keys())
    values = [counts[k] for k in labels]
    fig, ax = plt.subplots(figsize=(6.4, 4.2), dpi=140)
    ax.bar(labels, values, color="#0ea5e9", alpha=0.85)
    ax.set_ylabel("events")
    ax.set_title("Detector-only event outcomes")
    ax.tick_params(axis="x", rotation=20)
    ax.grid(axis="y", alpha=0.25)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)


def run_detector_only(
    cfg: DetectorConfig,
    source_phase_space_path: str | Path,
    out_dir: str | Path,
    seed: int = 12345,
    config_path: Optional[str | Path] = None,
) -> Dict[str, object]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    photons = read_phase_space_csv(source_phase_space_path)
    hits, events = simulate_detector_response(cfg, photons, seed=seed)
    summary = summarize_detector_response(cfg, photons, hits, events, seed, source_phase_space_path)
    write_hits_csv(out / "hits.csv", hits)
    write_event_summary_csv(out / "event_summary.csv", events)
    plot_detector_spectrum(out / "detector_spectrum.png", events, cfg)
    plot_detector_pixel_map(out / "detector_pixel_map.png", hits, cfg)
    plot_detector_outcomes(out / "detector_outcomes.png", summary)
    with (out / "summary.json").open("w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
        f.write("\n")
    if config_path is not None:
        shutil.copyfile(config_path, out / "config_used.yaml")
    return summary

#!/usr/bin/python3
"""FEniCS small-signal two-node Ta-absorber/TES pulse comparison.

Each DG0 cell indexes one independent pixel.  The two thermal unknowns are the
mushroom Ta absorber and the directly Si-connected TES.  Candidate-C G4CMP
sensor energy is split 20/80 between those nodes according to the user-supplied
contact-perimeter rule.  Direct TP deposits and the photon reference enter the
absorber.  All event energies are normalized to 1 keV before solving so that
the calculation tests linear optimal-filter template shape, not saturation.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("DIJITSO_CACHE_DIR", str(ROOT / "build/fenics_cache/dijitso"))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib"))

from dolfin import (  # noqa: E402
    Constant,
    FiniteElement,
    Function,
    FunctionSpace,
    MixedElement,
    NonlinearVariationalProblem,
    NonlinearVariationalSolver,
    TestFunctions,
    TrialFunction,
    UnitIntervalMesh,
    derivative,
    dx,
    set_log_level,
    split,
)

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from simulate_tes_fenics import KEV_TO_J, file_hash, load_patterns  # noqa: E402


@dataclass(frozen=True)
class SplitInjection:
    time_s: float
    absorber_keV: float
    tes_keV: float
    source: str


def transition_and_operating_point(cfg: dict) -> dict[str, float | list[dict[str, float]]]:
    temp = cfg["temperature"]
    elec = cfg["electrical"]
    thermal = cfg["thermal"]
    tc = temp["Tc_K"]
    tb = temp["Tbath_K"]
    alpha = temp["transition_alpha_at_bias"]
    rfrac = temp["operating_resistance_fraction_Rn"]
    exponent = alpha / (1.0 - rfrac)
    t0 = tc * (rfrac / (1.0 - rfrac)) ** (1.0 / exponent)
    rn = elec["Rn_ohm_assumption"]
    r0 = rfrac * rn
    rsh = elec["Rshunt_ohm"]
    n = thermal["bath_power_exponent_n"]
    gtb_tc = thermal["G_TES_to_bath_at_Tc_W_K"]
    gab_tc = thermal["G_absorber_to_bath_at_Tc_W_K"]
    ktb = gtb_tc / (n * tc ** (n - 1.0))
    kab = gab_tc / (n * tc ** (n - 1.0))
    p0 = (ktb + kab) * (t0**n - tb**n)
    i0 = math.sqrt(p0 / r0)
    vbias = i0 * (r0 + rsh)

    volume_m3 = np.prod(np.asarray(thermal["Ta_pixel_dimensions_mm"])) * 1e-9
    absorber_mass_kg = volume_m3 * thermal["Ta_density_kg_m3"]
    ca = absorber_mass_kg * thermal["Ta_specific_heat_J_kg_K"]
    ct = thermal["TES_heat_capacity_J_K"]
    gat = thermal["G_absorber_to_TES_W_K"]
    gab0 = n * kab * t0 ** (n - 1.0)
    gtb0 = n * ktb * t0 ** (n - 1.0)
    rprime = r0 * alpha / t0
    inductance = elec["series_inductance_H"]

    jacobian = np.asarray(
        [
            [-(gab0 + gat) / ca, gat / ca, 0.0],
            [gat / ct, (i0 * i0 * rprime - gtb0 - gat) / ct, 2.0 * i0 * r0 / ct],
            [0.0, -i0 * rprime / inductance, -(r0 + rsh) / inductance],
        ]
    )
    eigenvalues = np.linalg.eigvals(jacobian)
    reduced_capacity = ca * ct / (ca + ct)
    return {
        "T0_K": t0,
        "normal_fraction_exponent": exponent,
        "C_absorber_J_K": ca,
        "C_TES_J_K": ct,
        "absorber_mass_kg": absorber_mass_kg,
        "G_TES_bath_at_T0_W_K": gtb0,
        "G_absorber_bath_at_T0_W_K": gab0,
        "G_absorber_TES_W_K": gat,
        "K_TES_bath_W_Kn": ktb,
        "K_absorber_bath_W_Kn": kab,
        "R0_ohm": r0,
        "Rprime_ohm_K": rprime,
        "P0_W": p0,
        "I0_A": i0,
        "Vbias_V": vbias,
        "electrical_tau_s": inductance / (r0 + rsh),
        "absorber_TES_differential_tau_s": reduced_capacity / gat,
        "combined_intrinsic_bath_tau_s": (ca + ct) / (gab0 + gtb0),
        "linear_eigenvalues_per_s": [
            {"real": float(value.real), "imag": float(value.imag)} for value in eigenvalues
        ],
        "linearly_stable": bool(np.all(eigenvalues.real < 0)),
    }


def split_and_normalize_patterns(cfg: dict):
    raw_patterns, provenance = load_patterns()
    selected = {event: raw_patterns[event] for event in cfg["scope"]["events"]}
    normalization_keV = cfg["linear_response"]["normalization_energy_keV_per_event"]
    si_split = cfg["input_partition"]["G4CMP_Si_phonon_sensor_energy"]

    event_original_totals = {}
    device_labels: list[str] = []
    device_events: list[str] = []
    device_channels: list[str] = []
    device_injections: list[list[SplitInjection]] = []
    event_indices: dict[str, list[int]] = defaultdict(list)
    ledgers: dict[str, dict[str, float]] = {}

    for event in cfg["scope"]["events"]:
        original_total = sum(
            injection.energy_keV
            for channel in selected[event].values()
            for injection in channel
        )
        event_original_totals[event] = original_total
        scale = normalization_keV / original_total
        ledger = {
            "original_total_keV": original_total,
            "normalization_scale": scale,
            "normalized_absorber_keV": 0.0,
            "normalized_TES_keV": 0.0,
            "normalized_total_keV": 0.0,
        }
        for channel in sorted(selected[event]):
            split_items: list[SplitInjection] = []
            for injection in selected[event][channel]:
                energy = injection.energy_keV * scale
                if injection.source.startswith("Si_phonon"):
                    absorber = energy * si_split["absorber_fraction"]
                    tes = energy * si_split["TES_fraction"]
                else:
                    absorber = energy
                    tes = 0.0
                split_items.append(
                    SplitInjection(injection.time_s, absorber, tes, injection.source)
                )
                ledger["normalized_absorber_keV"] += absorber
                ledger["normalized_TES_keV"] += tes
                ledger["normalized_total_keV"] += absorber + tes
            index = len(device_labels)
            event_indices[event].append(index)
            device_labels.append(f"{event}|{channel}")
            device_events.append(event)
            device_channels.append(channel)
            device_injections.append(sorted(split_items, key=lambda item: item.time_s))
        ledgers[event] = ledger

    if not all(abs(value["normalized_total_keV"] - normalization_keV) < 1e-12 for value in ledgers.values()):
        raise ValueError(f"Event normalization failed: {ledgers}")
    return (
        device_labels,
        device_events,
        device_channels,
        device_injections,
        event_indices,
        ledgers,
        provenance,
    )


def time_grid(refinement: int = 1) -> np.ndarray:
    if refinement < 1:
        raise ValueError("refinement must be positive")
    segments = [
        np.arange(0.0, 0.5e-6 + 2.5e-9 / refinement, 5e-9 / refinement),
        np.arange(0.5e-6 + 25e-9 / refinement, 5e-6 + 12.5e-9 / refinement, 25e-9 / refinement),
        np.arange(5e-6 + 0.25e-6 / refinement, 50e-6 + 0.125e-6 / refinement, 0.25e-6 / refinement),
        np.arange(50e-6 + 2.5e-6 / refinement, 0.5e-3 + 1.25e-6 / refinement, 2.5e-6 / refinement),
        np.arange(0.5e-3 + 10e-6 / refinement, 2e-3 + 5e-6 / refinement, 10e-6 / refinement),
        np.arange(2e-3 + 25e-6 / refinement, 12e-3 + 12.5e-6 / refinement, 25e-6 / refinement),
    ]
    return np.unique(np.concatenate(segments))


def fwhm(time_s: np.ndarray, pulse: np.ndarray) -> float:
    peak = float(np.max(pulse))
    indices = np.flatnonzero(pulse >= 0.5 * peak)
    if peak <= 0 or not indices.size:
        return float("nan")
    return float(time_s[indices[-1]] - time_s[indices[0]])


def trapz_inner(a: np.ndarray, b: np.ndarray, time_s: np.ndarray) -> float:
    return float(np.trapz(a * b, time_s))


def simulate(cfg: dict, refinement: int = 1):
    set_log_level(40)
    (
        labels,
        device_events,
        device_channels,
        injections,
        event_indices,
        ledgers,
        provenance,
    ) = split_and_normalize_patterns(cfg)
    op = transition_and_operating_point(cfg)
    if not op["linearly_stable"]:
        raise ValueError("Two-node operating point is not linearly stable")

    n_devices = len(labels)
    mesh = UnitIntervalMesh(n_devices)
    scalar = FiniteElement("DG", mesh.ufl_cell(), 0)
    mixed = FunctionSpace(mesh, MixedElement([scalar, scalar, scalar]))
    state = Function(mixed)
    previous = Function(mixed)
    ta, tt, current = split(state)
    ta_prev, tt_prev, current_prev = split(previous)
    test_a, test_t, test_i = TestFunctions(mixed)

    thermal = cfg["thermal"]
    electrical = cfg["electrical"]
    dt = Constant(5e-9)
    ca = Constant(op["C_absorber_J_K"])
    ct = Constant(op["C_TES_J_K"])
    gat = Constant(op["G_absorber_TES_W_K"])
    gab = Constant(op["G_absorber_bath_at_T0_W_K"])
    gtb = Constant(op["G_TES_bath_at_T0_W_K"])
    inductance = Constant(electrical["series_inductance_H"])
    r0 = Constant(op["R0_ohm"])
    rsh = Constant(electrical["Rshunt_ohm"])
    rprime = Constant(op["Rprime_ohm_K"])
    i0 = Constant(op["I0_A"])

    absorber_residual = (
        ca * (ta - ta_prev) / dt + gab * ta + gat * (ta - tt)
    ) * test_a * dx
    tes_residual = (
        ct * (tt - tt_prev) / dt
        + gtb * tt
        + gat * (tt - ta)
        - i0 * i0 * rprime * tt
        - 2.0 * i0 * r0 * current
    ) * test_t * dx
    electrical_residual = (
        inductance * (current - current_prev) / dt
        + (r0 + rsh) * current
        + i0 * rprime * tt
    ) * test_i * dx
    residual = absorber_residual + tes_residual + electrical_residual
    jacobian = derivative(residual, state, TrialFunction(mixed))
    problem = NonlinearVariationalProblem(residual, state, J=jacobian)
    solver = NonlinearVariationalSolver(problem)
    newton = solver.parameters["newton_solver"]
    # The transfer functions are evaluated for a 1-keV normalization, so the
    # integrated weak-form residuals are much smaller than in the nonlinear
    # 511-keV run.  A loose absolute tolerance would falsely freeze the tail.
    newton["absolute_tolerance"] = 1e-26
    newton["relative_tolerance"] = 1e-11
    newton["maximum_iterations"] = 8
    newton["linear_solver"] = "lu"
    newton["error_on_nonconvergence"] = True
    newton["report"] = False

    coordinates = mixed.tabulate_dof_coordinates().reshape((-1, 1))[:, 0]
    absorber_dofs = np.asarray(mixed.sub(0).dofmap().dofs(), dtype=int)
    tes_dofs = np.asarray(mixed.sub(1).dofmap().dofs(), dtype=int)
    current_dofs = np.asarray(mixed.sub(2).dofmap().dofs(), dtype=int)
    absorber_dofs = absorber_dofs[np.argsort(coordinates[absorber_dofs])]
    tes_dofs = tes_dofs[np.argsort(coordinates[tes_dofs])]
    current_dofs = current_dofs[np.argsort(coordinates[current_dofs])]

    previous.vector().zero()
    previous.vector().apply("insert")
    state.assign(previous)
    pointers = np.zeros(n_devices, dtype=int)
    times = time_grid(refinement)
    trace_by_event: dict[str, list[float]] = defaultdict(list)
    trace_rows: list[dict] = []
    max_absorber_delta = np.zeros(n_devices)
    max_tes_delta = np.zeros(n_devices)
    max_current_deficit = np.zeros(n_devices)

    def add_due_injections(until_time: float) -> None:
        values = previous.vector().get_local()
        for index, device in enumerate(injections):
            while pointers[index] < len(device) and device[pointers[index]].time_s <= until_time + 1e-18:
                item = device[pointers[index]]
                values[absorber_dofs[index]] += item.absorber_keV * KEV_TO_J / op["C_absorber_J_K"]
                values[tes_dofs[index]] += item.tes_keV * KEV_TO_J / op["C_TES_J_K"]
                pointers[index] += 1
        previous.vector().set_local(values)
        previous.vector().apply("insert")
        state.assign(previous)

    def record(at_time: float) -> None:
        values = state.vector().get_local()
        theta_a = values[absorber_dofs]
        theta_t = values[tes_dofs]
        current_deficit = -values[current_dofs]
        np.maximum(max_absorber_delta, theta_a, out=max_absorber_delta)
        np.maximum(max_tes_delta, theta_t, out=max_tes_delta)
        np.maximum(max_current_deficit, current_deficit, out=max_current_deficit)
        for event, indices in event_indices.items():
            pulse = float(np.sum(current_deficit[indices]))
            trace_by_event[event].append(pulse)
            trace_rows.append(
                {
                    "time_s": at_time,
                    "event": event,
                    "summed_current_deficit_A_per_1keV": pulse,
                    "max_absorber_deltaT_K_per_1keV": float(np.max(theta_a[indices])),
                    "max_TES_deltaT_K_per_1keV": float(np.max(theta_t[indices])),
                }
            )

    add_due_injections(0.0)
    record(0.0)
    previous_time = 0.0
    total_iterations = 0
    for current_time in times[1:]:
        add_due_injections(float(current_time))
        dt.assign(float(current_time - previous_time))
        iterations, converged = solver.solve()
        if not converged:
            raise RuntimeError(f"FEniCS solve failed at t={current_time}")
        total_iterations += int(iterations)
        previous.assign(state)
        previous_time = float(current_time)
        record(previous_time)

    reference = np.asarray(trace_by_event["photon_511"])
    metrics = {}
    for event, indices in event_indices.items():
        pulse = np.asarray(trace_by_event[event])
        peak_index = int(np.argmax(pulse))
        scale = trapz_inner(pulse, reference, times) / trapz_inner(reference, reference, times)
        residual = pulse - scale * reference
        residual_fraction = math.sqrt(
            trapz_inner(residual, residual, times) / trapz_inner(pulse, pulse, times)
        )
        metrics[event] = {
            **ledgers[event],
            "active_channels": len(indices),
            "peak_current_deficit_nA_per_1keV": float(pulse[peak_index] * 1e9),
            "time_to_peak_us": float(times[peak_index] * 1e6),
            "pulse_fwhm_ms": fwhm(times, pulse) * 1e3,
            "reference_template_best_scale": scale,
            "time_weighted_template_residual_l2_fraction": residual_fraction,
            "max_absorber_deltaT_uK_per_1keV": float(np.max(max_absorber_delta[indices]) * 1e6),
            "max_TES_deltaT_uK_per_1keV": float(np.max(max_tes_delta[indices]) * 1e6),
        }

    channel_rows = []
    for index, label in enumerate(labels):
        original_absorber = sum(item.absorber_keV for item in injections[index])
        original_tes = sum(item.tes_keV for item in injections[index])
        channel_rows.append(
            {
                "event": device_events[index],
                "channel": device_channels[index],
                "normalized_absorber_input_keV": original_absorber,
                "normalized_TES_input_keV": original_tes,
                "normalized_total_input_keV": original_absorber + original_tes,
                "max_absorber_deltaT_uK_per_1keV_event": max_absorber_delta[index] * 1e6,
                "max_TES_deltaT_uK_per_1keV_event": max_tes_delta[index] * 1e6,
                "peak_current_deficit_nA_per_1keV_event": max_current_deficit[index] * 1e9,
                "sources": ";".join(sorted({item.source for item in injections[index]})),
            }
        )
    diagnostics = {
        "operating_point": op,
        "metrics": metrics,
        "event_ledgers": ledgers,
        "device_count": n_devices,
        "time_grid_refinement": refinement,
        "time_step_count": len(times) - 1,
        "total_newton_iterations": total_iterations,
        "all_injections_consumed": bool(
            all(pointers[index] == len(injections[index]) for index in range(n_devices))
        ),
        "provenance": provenance,
    }
    return times, trace_by_event, trace_rows, channel_rows, diagnostics


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def make_plot(times: np.ndarray, traces: dict[str, list[float]], diagnostics: dict, output_prefix: Path) -> None:
    photon = np.asarray(traces["photon_511"])
    candidate = np.asarray(traces["candidate_C"])
    time_ms = times * 1e3

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.titlesize": 14,
            "axes.labelsize": 12,
        }
    )
    fig, ax = plt.subplots(figsize=(9.6, 5.7), constrained_layout=True)
    ax.plot(time_ms, photon / photon.max(), color="black", lw=2.8, label="one-pixel photon path → Ta absorber")
    ax.plot(
        time_ms,
        candidate / candidate.max(),
        color="#009e73",
        lw=2.2,
        label="counterfactual sum of candidate-C channels",
    )
    ax.set_xlim(0, 4.0)
    ax.set_ylim(-0.01, 1.04)
    ax.set_xlabel("time [ms]")
    ax.set_ylabel("peak-normalized TES current deficit")
    ax.set_title("Small-signal two-node pulse templates")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=10)

    op = diagnostics["operating_point"]
    fig.suptitle(
        "FEniCS linear two-node Ta absorber + TES response\n"
        "G_Tb=0.8 nW/K, G_Ab=0.2 nW/K, G_AT=1000 nW/K"
    )
    fig.text(
        0.5,
        -0.01,
        (
            "Both events are normalized to 1 keV to enforce the below-saturation optimal-filter limit. "
            f"Ta–TES differential equilibration time = {op['absorber_TES_differential_tau_s']*1e9:.2f} ns. "
            "The green curve is an array-sum stress test, not one physical TES channel."
        ),
        ha="center",
        fontsize=9.0,
    )
    png_path = output_prefix.with_suffix(".png")
    pdf_path = output_prefix.with_suffix(".pdf")
    fig.savefig(png_path, dpi=220, facecolor="white", bbox_inches="tight")
    fig.savefig(pdf_path, facecolor="white", bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    config_path = ROOT / "config/tes_two_node_fenics_model.json"
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    times, traces, trace_rows, channel_rows, diagnostics = simulate(cfg)
    _, _, _, _, refined = simulate(cfg, refinement=2)

    convergence = {}
    for event in cfg["scope"]["events"]:
        coarse_metrics = diagnostics["metrics"][event]
        refined_metrics = refined["metrics"][event]
        convergence[event] = {}
        for key in (
            "peak_current_deficit_nA_per_1keV",
            "time_to_peak_us",
            "pulse_fwhm_ms",
            "time_weighted_template_residual_l2_fraction",
        ):
            coarse = coarse_metrics[key]
            fine = refined_metrics[key]
            convergence[event][key] = {
                "coarse": coarse,
                "refined": fine,
                "relative_change": (fine - coarse) / coarse if coarse else 0.0,
            }

    photon = np.asarray(traces["photon_511"])
    candidate = np.asarray(traces["candidate_C"])
    best_scale = diagnostics["metrics"]["candidate_C"]["reference_template_best_scale"]
    normalized_difference = (candidate - best_scale * photon) / np.max(candidate)
    peak_difference_index = int(np.argmax(np.abs(normalized_difference)))
    diagnostics["shape_difference"] = {
        "maximum_absolute_difference_fraction_of_C_peak": float(
            abs(normalized_difference[peak_difference_index])
        ),
        "time_of_maximum_absolute_difference_us": float(times[peak_difference_index] * 1e6),
        "definition": "C minus best-scaled photon current, divided by candidate-C peak current",
    }
    diagnostics["time_step_convergence"] = convergence

    output_dir = ROOT / "outputs/tes_two_node_fenics"
    output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = output_dir / "pulse_traces.csv"
    channel_path = output_dir / "channel_summary.csv"
    result_path = output_dir / "TES_TWO_NODE_EVALUATION.json"
    report_path = output_dir / "TES_TWO_NODE_EVALUATION.md"
    figure_prefix = ROOT / "outputs/figures/sh3_tes_two_node_pulse_comparison"
    write_csv(trace_path, trace_rows)
    write_csv(channel_path, channel_rows)
    make_plot(times, traces, diagnostics, figure_prefix)

    result = {
        "schema_version": 1,
        "status": "PASS",
        "solver": {
            "name": "FEniCS/dolfin mixed DG0 backward-Euler linearized three-variable solve",
            "unknowns_per_pixel": ["absorber_temperature_perturbation", "TES_temperature_perturbation", "TES_current_perturbation"],
            "meaning_of_mesh": "Each DG0 cell indexes one independent pixel; it is not a spatial diffusion mesh",
            "version": "2019.2.0.64.dev0",
        },
        "config": {"path": str(config_path), "sha256": file_hash(config_path)},
        "diagnostics": diagnostics,
        "outputs": {
            "trace_csv": str(trace_path),
            "channel_csv": str(channel_path),
            "figure_png": str(figure_prefix.with_suffix('.png')),
            "figure_pdf": str(figure_prefix.with_suffix('.pdf')),
            "report_md": str(report_path),
        },
        "interpretation": [
            "This is the user-requested 80/20 ballistic-contact allocation in the linear below-saturation limit.",
            "G_absorber_TES=1000 nW/K locks the two temperatures on a timescale far shorter than the 0.3 ms electrical response.",
            "The residual is an unweighted time-domain shape metric, not an optimal-filter significance; a measured noise PSD is still required.",
        ],
    }
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    c_ledger = diagnostics["event_ledgers"]["candidate_C"]
    c_total = c_ledger["original_total_keV"]
    c_absorber = c_ledger["normalized_absorber_keV"] * c_total
    c_tes = c_ledger["normalized_TES_keV"] * c_total
    photon_metrics = diagnostics["metrics"]["photon_511"]
    c_metrics = diagnostics["metrics"]["candidate_C"]
    shape = diagnostics["shape_difference"]
    op = diagnostics["operating_point"]
    report = f"""# SH3 two-node Ta absorber / TES linear-response evaluation

## Model requested by the user

- Per-pixel TES-to-bath conductance at Tc: 0.8 nW/K.
- Per-pixel absorber-to-bath conductance at Tc: 0.2 nW/K.
- Absorber-to-TES conductance: 1000 nW/K.
- G4CMP Si-phonon sensor energy: 80% enters the TES node and 20% enters the
  absorber node, following the specified Si-contact-perimeter ratio.
- Photon and direct `TP_L...` mass-model deposits enter the Ta absorber.
- G4CMP surface absorption is an instantaneous source in this thermal model;
  no additional interface bottleneck is inserted.

The FEniCS solve is linearized about the voltage-biased operating point and
normalizes each event to 1 keV.  It therefore tests the below-saturation common-
template limit raised by the user, rather than the earlier nonlinear 511-keV
one-node response.

## Energy ledger for candidate C

The original candidate-C energy is {c_total:.6f} keV.  Under the requested
allocation:

```text
absorber node = {c_absorber:.6f} keV
TES node      = {c_tes:.6f} keV
total         = {c_absorber + c_tes:.6f} keV
```

Most energy remains on the photon-like absorber path because the 458.392-keV
direct `TP_L...` component enters the absorber.  Only 80% of the 52.573-keV
G4CMP substrate-phonon component enters the TES directly.

## Time scales and stability

```text
Ta--TES differential equilibration = {op['absorber_TES_differential_tau_s']*1e9:.3f} ns
electrical L/(R0+Rshunt)           = {op['electrical_tau_s']*1e6:.3f} us
combined intrinsic C/G            = {op['combined_intrinsic_bath_tau_s']*1e3:.3f} ms
linear poles                       = {', '.join(f"{x['real']:.3f} s^-1" for x in op['linear_eigenvalues_per_s'])}
```

All poles are negative.  The 1000-nW/K absorber--TES link removes the thermal
bottleneck as intended; the electrical inductance retains a small memory of the
brief direct-TES input.

## Small-signal pulse comparison

| event | peak per 1 keV | peak time | FWHM |
|---|---:|---:|---:|
| photon to absorber | {photon_metrics['peak_current_deficit_nA_per_1keV']:.6f} nA | {photon_metrics['time_to_peak_us']:.3f} us | {photon_metrics['pulse_fwhm_ms']:.6f} ms |
| candidate C, 80/20 split | {c_metrics['peak_current_deficit_nA_per_1keV']:.6f} nA | {c_metrics['time_to_peak_us']:.3f} us | {c_metrics['pulse_fwhm_ms']:.6f} ms |

- Best-fit photon-template scale for C: {c_metrics['reference_template_best_scale']:.9f}.
- Time-weighted, unweighted-noise L2 shape residual: {100*c_metrics['time_weighted_template_residual_l2_fraction']:.6f}%.
- Maximum pointwise leading-edge difference: {100*shape['maximum_absolute_difference_fraction_of_C_peak']:.6f}% of the C peak at {shape['time_of_maximum_absolute_difference_us']:.3f} us.
- Doubling the time-grid resolution changes the residual to
  {100*refined['metrics']['candidate_C']['time_weighted_template_residual_l2_fraction']:.6f}%.

The templates are therefore very similar in the linear, below-saturation limit.
This calculation does not establish pulse-shape rejection: a measured readout
noise PSD is required to turn the small residual into an optimal-filter
significance.  Candidate C's cross-layer and multi-pixel topology remains a
separate discriminator if those identities are preserved.

## Reproduction

```bash
cd /home/ubuntu/neutron_fen
mkdir -p build/fenics_cache/dijitso
PYTHONDONTWRITEBYTECODE=1 DIJITSO_CACHE_DIR=/home/ubuntu/neutron_fen/build/fenics_cache/dijitso \\
  MPLCONFIGDIR=/home/ubuntu/neutron_fen/.matplotlib \\
  /usr/bin/python3 code/simulate_tes_two_node_fenics.py
```
"""
    report_path.write_text(report, encoding="utf-8")
    print(
        json.dumps(
            {
                "result": str(result_path),
                "figure": str(figure_prefix.with_suffix('.png')),
                "operating_point": diagnostics["operating_point"],
                "metrics": diagnostics["metrics"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

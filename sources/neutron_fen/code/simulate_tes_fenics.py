#!/usr/bin/python3
"""FEniCS simulation of lumped Ta-absorber/TES electrothermal pulses.

Each DG0 cell is a computational index for one independent physical TES pixel;
there is deliberately no spatial coupling between cells. The mixed variational
problem advances pixel temperature and bias current with backward Euler.
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
    exp,
    set_log_level,
    split,
)

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


KEV_TO_J = 1.602176634e-16


@dataclass(frozen=True)
class Injection:
    time_s: float
    energy_keV: float
    source: str


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def add_injection(
    patterns: dict[str, dict[str, list[Injection]]],
    event: str,
    channel: str,
    time_s: float,
    energy_keV: float,
    source: str,
) -> None:
    patterns[event].setdefault(channel, []).append(
        Injection(max(0.0, time_s), energy_keV, source)
    )


def load_patterns() -> tuple[dict[str, dict[str, list[Injection]]], dict]:
    patterns: dict[str, dict[str, list[Injection]]] = defaultdict(dict)
    add_injection(patterns, "photon_511", "Lx:P_ref", 0.0, 511.0, "direct_Ta")

    direct_path = ROOT / "outputs/candidate_direct_tes_channels.csv"
    direct_rows = read_csv(direct_path)
    for row in direct_rows:
        candidate = row["candidate"]
        if candidate not in {"A", "C"}:
            continue
        channel = f"L{int(row['layer'])}:P{int(row['pixel_id'])}"
        add_injection(
            patterns,
            f"candidate_{candidate}",
            channel,
            0.0,
            float(row["energy_keV"]),
            "direct_Ta",
        )

    # Candidate C: average five independent tuned-C transport realizations.
    c_hit_paths = sorted(
        (ROOT / "runs/staircase/02c_candidate_C_replicates").glob("rep*/hits.csv")
    )
    if len(c_hit_paths) != 5:
        raise ValueError(f"Expected five candidate-C replicates, found {len(c_hit_paths)}")
    for path in c_hit_paths:
        for row in read_csv(path):
            if row["surface_class"] != "sensor":
                continue
            channel = f"L{int(row['layer'])}:P{int(row['pixel_id'])}"
            add_injection(
                patterns,
                "candidate_C",
                channel,
                float(row["arrival_from_group_ns"]) * 1e-9,
                float(row["weighted_energy_eV"]) / 1000.0 / len(c_hit_paths),
                "Si_phonon",
            )

    # Strict-recoil candidates A and B: use the spatial/time pattern of the
    # closest high-collection run, then rescale only the sensor-hit weights to
    # the exact eta required by the 511-keV energy ledger. This is explicitly a
    # counterfactual shape test, not a predicted collection efficiency.
    high_hit_path = ROOT / "runs/staircase/02_exact_ABC/tuned_high_bath0p06/hits.csv"
    direct_by_candidate = defaultdict(float)
    for row in direct_rows:
        direct_by_candidate[row["candidate"]] += float(row["energy_keV"])
    high_sensor_totals = defaultdict(float)
    high_sensor_rows: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_csv(high_hit_path):
        candidate = row["candidate"]
        if candidate in {"A", "B"} and row["surface_class"] == "sensor":
            high_sensor_rows[candidate].append(row)
            high_sensor_totals[candidate] += float(row["weighted_energy_eV"]) / 1000.0
    scale_factors = {}
    for candidate in ("A", "B"):
        target_sensor = 511.0 - direct_by_candidate[candidate]
        scale = target_sensor / high_sensor_totals[candidate]
        scale_factors[candidate] = scale
        for row in high_sensor_rows[candidate]:
            channel = f"L{int(row['layer'])}:P{int(row['pixel_id'])}"
            add_injection(
                patterns,
                f"candidate_{candidate}",
                channel,
                float(row["arrival_from_group_ns"]) * 1e-9,
                float(row["weighted_energy_eV"]) / 1000.0 * scale,
                "Si_phonon_rescaled",
            )

    provenance = {
        "direct_tes": {"path": str(direct_path), "sha256": file_hash(direct_path)},
        "candidate_C_hits": [
            {"path": str(path), "sha256": file_hash(path)} for path in c_hit_paths
        ],
        "candidate_A_B_high_collection_hits": {
            "path": str(high_hit_path),
            "sha256": file_hash(high_hit_path),
        },
        "A_B_sensor_rescale_to_511": scale_factors,
        "A_B_unscaled_high_collection_sensor_keV": dict(high_sensor_totals),
    }
    return patterns, provenance


def transition_parameters(cfg: dict, model: str) -> dict[str, float]:
    tc = cfg["temperature"]["Tc_K"]
    alpha = cfg["temperature"]["transition_alpha_at_bias"]
    r0_fraction = cfg["temperature"]["operating_resistance_fraction_Rn"]
    if model == "normal_fraction":
        exponent = alpha / (1.0 - r0_fraction)
        t0 = tc * (r0_fraction / (1.0 - r0_fraction)) ** (1.0 / exponent)
        return {"T0_K": t0, "normal_fraction_exponent": exponent}
    if model == "linear_temperature_logistic":
        logit = math.log(r0_fraction / (1.0 - r0_fraction))
        t0 = tc / (1.0 - (1.0 - r0_fraction) * logit / alpha)
        width = t0 * (1.0 - r0_fraction) / alpha
        return {"T0_K": t0, "transition_width_K": width}
    raise ValueError(f"Unknown resistance model {model!r}")


def operating_point(cfg: dict, g_tc: float, model: str) -> dict[str, float]:
    thermal = cfg["thermal"]
    electrical = cfg["electrical"]
    temperature = cfg["temperature"]
    transition = transition_parameters(cfg, model)
    t0 = transition["T0_K"]
    tc = temperature["Tc_K"]
    tb = temperature["Tbath_K"]
    n = thermal["bath_power_exponent_n"]
    rn = electrical["Rn_ohm_assumption"]
    r0 = temperature["operating_resistance_fraction_Rn"] * rn
    rsh = electrical["Rshunt_ohm"]
    k = g_tc / (n * tc ** (n - 1.0))
    p0 = k * (t0**n - tb**n)
    i0 = math.sqrt(p0 / r0)
    v_bias = i0 * (r0 + rsh)
    ibias = v_bias / rsh

    volume = np.prod(np.asarray(thermal["Ta_pixel_dimensions_mm"])) * 1e-9
    ta_mass = volume * thermal["Ta_density_kg_m3"]
    c_ta = ta_mass * thermal["Ta_specific_heat_J_kg_K"]
    c_total = c_ta + thermal["TES_heat_capacity_J_K"]
    g0 = n * k * t0 ** (n - 1.0)
    alpha = temperature["transition_alpha_at_bias"]
    rprime = r0 * alpha / t0
    inductance = electrical["series_inductance_H"]
    jacobian = np.asarray(
        [
            [(i0 * i0 * rprime - g0) / c_total, 2.0 * i0 * r0 / c_total],
            [-i0 * rprime / inductance, -(r0 + rsh) / inductance],
        ]
    )
    eigenvalues = np.linalg.eigvals(jacobian)
    result = {
        **transition,
        "G_Tc_W_K": g_tc,
        "K_W_Kn": k,
        "C_Ta_J_K": c_ta,
        "C_TES_J_K": thermal["TES_heat_capacity_J_K"],
        "C_total_J_K": c_total,
        "Ta_mass_kg": ta_mass,
        "R0_ohm": r0,
        "P0_W": p0,
        "I0_A": i0,
        "Vbias_V": v_bias,
        "Ibias_A": ibias,
        "G_at_T0_W_K": g0,
        "intrinsic_tau_s": c_total / g0,
        "electrical_tau_s": inductance / (r0 + rsh),
        "linear_eigenvalues_per_s": [
            {"real": float(value.real), "imag": float(value.imag)} for value in eigenvalues
        ],
        "linearly_stable": bool(np.all(eigenvalues.real < 0)),
        "linearly_overdamped": bool(np.all(np.abs(eigenvalues.imag) < 1e-9)),
    }
    return result


def time_grid(refinement: int = 1) -> np.ndarray:
    if refinement < 1:
        raise ValueError("Time-grid refinement must be a positive integer")
    segments = [
        np.arange(0.0, 20.0e-6 + 0.125e-6 / refinement, 0.25e-6 / refinement),
        np.arange(
            20.0e-6 + 2.0e-6 / refinement,
            200.0e-6 + 1.0e-6 / refinement,
            2.0e-6 / refinement,
        ),
        np.arange(
            200.0e-6 + 10.0e-6 / refinement,
            2.0e-3 + 5.0e-6 / refinement,
            10.0e-6 / refinement,
        ),
        np.arange(
            2.0e-3 + 25.0e-6 / refinement,
            12.0e-3 + 12.5e-6 / refinement,
            25.0e-6 / refinement,
        ),
    ]
    return np.unique(np.concatenate(segments))


def prepare_devices(patterns: dict[str, dict[str, list[Injection]]]):
    device_labels = []
    event_indices: dict[str, list[int]] = defaultdict(list)
    device_injections: list[list[Injection]] = []
    for event in ("photon_511", "candidate_A", "candidate_B", "candidate_C"):
        for channel in sorted(patterns[event]):
            event_indices[event].append(len(device_labels))
            device_labels.append(f"{event}|{channel}")
            device_injections.append(sorted(patterns[event][channel], key=lambda item: item.time_s))
    return device_labels, event_indices, device_injections


def fwhm(time_s: np.ndarray, pulse: np.ndarray) -> float:
    peak = float(np.max(pulse))
    if peak <= 0:
        return float("nan")
    indices = np.flatnonzero(pulse >= 0.5 * peak)
    return float(time_s[indices[-1]] - time_s[indices[0]]) if indices.size else float("nan")


def simulate(
    cfg: dict,
    patterns: dict[str, dict[str, list[Injection]]],
    g_tc: float,
    resistance_model: str,
    time_refinement: int = 1,
) -> tuple[list[dict], list[dict], dict]:
    set_log_level(40)
    labels, event_indices, injections = prepare_devices(patterns)
    n_devices = len(labels)
    op = operating_point(cfg, g_tc, resistance_model)
    if not op["linearly_stable"]:
        raise ValueError(f"Requested unstable operating point at G={g_tc}")

    temperature_cfg = cfg["temperature"]
    electrical = cfg["electrical"]
    thermal = cfg["thermal"]
    mesh = UnitIntervalMesh(n_devices)
    scalar = FiniteElement("DG", mesh.ufl_cell(), 0)
    mixed = FunctionSpace(mesh, MixedElement([scalar, scalar]))
    state = Function(mixed)
    previous = Function(mixed)
    temp, current = split(state)
    temp_prev, current_prev = split(previous)
    test_temp, test_current = TestFunctions(mixed)

    dt = Constant(1e-7)
    c_total = Constant(op["C_total_J_K"])
    inductance = Constant(electrical["series_inductance_H"])
    rn = Constant(electrical["Rn_ohm_assumption"])
    rsh = Constant(electrical["Rshunt_ohm"])
    tc = Constant(temperature_cfg["Tc_K"])
    tb = Constant(temperature_cfg["Tbath_K"])
    k = Constant(op["K_W_Kn"])
    n = thermal["bath_power_exponent_n"]
    vbias = Constant(op["Vbias_V"])
    if resistance_model == "normal_fraction":
        exponent = op["normal_fraction_exponent"]
        normal_ratio = (temp / tc) ** exponent
        resistance = rn * normal_ratio / (1.0 + normal_ratio)
    else:
        width = Constant(op["transition_width_K"])
        resistance = rn / (1.0 + exp(-(temp - tc) / width))
    bath_power = k * (temp**n - tb**n)
    joule_power = current * current * resistance
    thermal_residual = (
        c_total * (temp - temp_prev) / dt - joule_power + bath_power
    ) * test_temp * dx
    electrical_residual = (
        inductance * (current - current_prev) / dt
        - vbias
        + current * (rsh + resistance)
    ) * test_current * dx
    residual = thermal_residual + electrical_residual
    jac = derivative(residual, state, TrialFunction(mixed))
    problem = NonlinearVariationalProblem(residual, state, J=jac)
    solver = NonlinearVariationalSolver(problem)
    newton = solver.parameters["newton_solver"]
    newton["absolute_tolerance"] = 1e-12
    newton["relative_tolerance"] = 1e-10
    newton["maximum_iterations"] = 15
    newton["relaxation_parameter"] = 1.0
    newton["linear_solver"] = "lu"
    newton["error_on_nonconvergence"] = True
    newton["report"] = False

    temp_dofs = np.asarray(mixed.sub(0).dofmap().dofs(), dtype=int)
    current_dofs = np.asarray(mixed.sub(1).dofmap().dofs(), dtype=int)
    coordinates = mixed.tabulate_dof_coordinates().reshape((-1, 1))[:, 0]
    temp_dofs = temp_dofs[np.argsort(coordinates[temp_dofs])]
    current_dofs = current_dofs[np.argsort(coordinates[current_dofs])]

    initial = previous.vector().get_local()
    initial[temp_dofs] = op["T0_K"]
    initial[current_dofs] = op["I0_A"]
    previous.vector().set_local(initial)
    previous.vector().apply("insert")
    state.assign(previous)

    energy_by_device_kev = np.asarray(
        [sum(item.energy_keV for item in device) for device in injections]
    )
    sources_by_device = [sorted({item.source for item in device}) for device in injections]
    pointers = np.zeros(n_devices, dtype=int)
    max_temp = np.full(n_devices, op["T0_K"])
    max_deficit = np.zeros(n_devices)
    times = time_grid(time_refinement)
    trace_rows: list[dict] = []
    trace_by_event: dict[str, list[float]] = defaultdict(list)

    # Apply all t=0 energy as an enthalpy jump before the first recorded state.
    prev_values = previous.vector().get_local()
    for device_index, device in enumerate(injections):
        while pointers[device_index] < len(device) and device[pointers[device_index]].time_s <= 0:
            prev_values[temp_dofs[device_index]] += (
                device[pointers[device_index]].energy_keV * KEV_TO_J / op["C_total_J_K"]
            )
            pointers[device_index] += 1
    previous.vector().set_local(prev_values)
    previous.vector().apply("insert")
    state.assign(previous)

    def record(at_time: float) -> None:
        values = state.vector().get_local()
        temps = values[temp_dofs]
        currents = values[current_dofs]
        deficits = op["I0_A"] - currents
        np.maximum(max_temp, temps, out=max_temp)
        np.maximum(max_deficit, deficits, out=max_deficit)
        for event, indices in event_indices.items():
            total_deficit = float(np.sum(deficits[indices]))
            trace_by_event[event].append(total_deficit)
            trace_rows.append(
                {
                    "G_Tc_nW_K": g_tc / 1e-9,
                    "resistance_model": resistance_model,
                    "time_s": at_time,
                    "event": event,
                    "summed_current_deficit_A": total_deficit,
                    "max_pixel_temperature_K": float(np.max(temps[indices])),
                }
            )

    record(0.0)
    previous_time = 0.0
    total_newton_iterations = 0
    for current_time in times[1:]:
        prev_values = previous.vector().get_local()
        for device_index, device in enumerate(injections):
            while (
                pointers[device_index] < len(device)
                and device[pointers[device_index]].time_s <= current_time + 1e-18
            ):
                prev_values[temp_dofs[device_index]] += (
                    device[pointers[device_index]].energy_keV
                    * KEV_TO_J
                    / op["C_total_J_K"]
                )
                pointers[device_index] += 1
        previous.vector().set_local(prev_values)
        previous.vector().apply("insert")
        state.assign(previous)
        dt.assign(float(current_time - previous_time))
        iterations, converged = solver.solve()
        if not converged:
            raise RuntimeError(f"FEniCS Newton solve did not converge at t={current_time}")
        total_newton_iterations += int(iterations)
        previous.assign(state)
        previous_time = float(current_time)
        record(previous_time)

    time_values = times
    metrics = {}
    reference = np.asarray(trace_by_event["photon_511"])
    for event, indices in event_indices.items():
        pulse = np.asarray(trace_by_event[event])
        peak_index = int(np.argmax(pulse))
        area = float(np.trapz(pulse, time_values))
        ref_scale = float(np.dot(pulse, reference) / np.dot(reference, reference))
        residual = pulse - ref_scale * reference
        residual_fraction = float(
            np.linalg.norm(residual) / np.linalg.norm(pulse)
        )
        event_energy = float(np.sum(energy_by_device_kev[indices]))
        metrics[event] = {
            "input_to_TES_keV": event_energy,
            "active_channels": len(indices),
            "channels_ge_0p42keV": int(np.count_nonzero(energy_by_device_kev[indices] >= 0.42)),
            "channels_ge_1keV": int(np.count_nonzero(energy_by_device_kev[indices] >= 1.0)),
            "dominant_channel": labels[indices[int(np.argmax(energy_by_device_kev[indices]))]],
            "dominant_channel_energy_keV": float(np.max(energy_by_device_kev[indices])),
            "peak_summed_current_deficit_uA": float(pulse[peak_index] * 1e6),
            "time_to_peak_ms": float(time_values[peak_index] * 1e3),
            "pulse_fwhm_ms": fwhm(time_values, pulse) * 1e3,
            "current_deficit_area_A_s": area,
            "max_pixel_temperature_mK": float(np.max(max_temp[indices]) * 1e3),
            "reference_template_best_scale": ref_scale,
            "reference_template_residual_l2_fraction": residual_fraction,
        }

    channel_rows = []
    for index, label in enumerate(labels):
        event, channel = label.split("|", 1)
        channel_rows.append(
            {
                "G_Tc_nW_K": g_tc / 1e-9,
                "resistance_model": resistance_model,
                "event": event,
                "channel": channel,
                "input_to_TES_keV": energy_by_device_kev[index],
                "sources": ";".join(sources_by_device[index]),
                "max_temperature_mK": max_temp[index] * 1e3,
                "peak_current_deficit_uA": max_deficit[index] * 1e6,
            }
        )
    diagnostics = {
        "operating_point": op,
        "device_count": n_devices,
        "time_grid_refinement": time_refinement,
        "time_step_count": len(times) - 1,
        "total_newton_iterations": total_newton_iterations,
        "max_newton_iterations_per_step_bound": 15,
        "all_injections_consumed": bool(
            all(pointers[index] == len(injections[index]) for index in range(n_devices))
        ),
        "metrics": metrics,
    }
    return trace_rows, channel_rows, diagnostics


def write_csv(path: Path, data: list[dict]) -> None:
    if not data:
        raise ValueError(f"Refusing to write empty CSV {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)


def plot_results(trace_rows: list[dict], diagnostics: dict, output_prefix: Path) -> None:
    primary_rows = [
        row
        for row in trace_rows
        if row["G_Tc_nW_K"] == 1.0 and row["resistance_model"] == "normal_fraction"
    ]
    by_event: dict[str, list[dict]] = defaultdict(list)
    for row in primary_rows:
        by_event[row["event"]].append(row)

    labels = {
        "photon_511": "511 keV photon, one pixel",
        "candidate_A": "A strict recoil, η forced to ROI",
        "candidate_B": "B strict recoil, η forced to ROI",
        "candidate_C": "C actual tuned-C mean",
    }
    colors_by_event = {
        "photon_511": "black",
        "candidate_A": "#0072b2",
        "candidate_B": "#d55e00",
        "candidate_C": "#009e73",
    }
    fig, (ax0, ax1) = plt.subplots(1, 2, figsize=(13.8, 5.8), constrained_layout=True)
    for event in labels:
        series = by_event[event]
        time_ms = np.asarray([row["time_s"] for row in series]) * 1e3
        pulse = np.asarray([row["summed_current_deficit_A"] for row in series]) * 1e6
        ax0.plot(time_ms, pulse, label=labels[event], color=colors_by_event[event], lw=1.8)
        ax1.plot(
            time_ms,
            pulse / pulse.max(),
            label=labels[event],
            color=colors_by_event[event],
            lw=1.8,
        )
    for ax in (ax0, ax1):
        ax.set_xlim(0, 6.0)
        ax.set_xlabel("time [ms]")
        ax.grid(alpha=0.23)
    ax0.set_ylabel("summed TES current deficit [µA]")
    ax0.set_title("Absolute array-summed current pulses")
    ax1.set_ylabel("peak-normalized current deficit")
    ax1.set_title("Pulse-shape comparison")
    ax0.legend(fontsize=8)
    ax1.legend(fontsize=8)
    fig.suptitle(
        "FEniCS nonlinear lumped Ta+TES electrothermal response\n"
        "primary model: G(Tc)=1 nW/K, Rn=10 mΩ, R0=0.3Rn, L=1000 nH"
    )
    fig.text(
        0.5,
        -0.015,
        "A/B are energy-matched counterfactuals; C uses measured direct Ta deposits and the five-run mean G4CMP phonon arrival stream. No readout noise PSD is assumed.",
        ha="center",
        fontsize=8.2,
    )
    fig.savefig(
        output_prefix.with_suffix(".png"),
        dpi=220,
        facecolor="white",
        bbox_inches="tight",
        metadata={"Software": "FEniCS 2019.2 + Matplotlib; simulate_tes_fenics.py"},
    )
    fig.savefig(
        output_prefix.with_suffix(".pdf"),
        facecolor="white",
        bbox_inches="tight",
        metadata={
            "Creator": "FEniCS 2019.2 + Matplotlib; simulate_tes_fenics.py",
            "CreationDate": None,
            "ModDate": None,
        },
    )
    plt.close(fig)


def main() -> None:
    config_path = ROOT / "config/tes_lumped_fenics_model.json"
    with config_path.open(encoding="utf-8") as stream:
        cfg = json.load(stream)
    patterns, provenance = load_patterns()

    # Scan the complete G interval analytically to expose the chosen stability
    # boundary, then run the stable sensitivity points with FEniCS.
    scan = []
    for g_nw in np.linspace(0.1, 12.0, 120):
        scan.append(operating_point(cfg, float(g_nw * 1e-9), "normal_fraction"))
    stable_values = [item["G_Tc_W_K"] for item in scan if item["linearly_stable"]]
    stability_upper_nw = max(stable_values) / 1e-9

    all_trace_rows: list[dict] = []
    all_channel_rows: list[dict] = []
    runs = {}
    for g_tc in cfg["thermal"]["stable_G_sensitivity_W_K"]:
        trace, channels, diag = simulate(cfg, patterns, g_tc, "normal_fraction")
        all_trace_rows.extend(trace)
        all_channel_rows.extend(channels)
        runs[f"normal_fraction_G{g_tc / 1e-9:g}nW_K"] = diag
    # Resistance-law cross-check at the primary G.
    trace, channels, diag = simulate(
        cfg, patterns, cfg["thermal"]["primary_G_at_Tc_W_K"], "linear_temperature_logistic"
    )
    all_trace_rows.extend(trace)
    all_channel_rows.extend(channels)
    runs["linear_temperature_logistic_G1nW_K"] = diag

    # A factor-two time-step refinement is computed but not duplicated in the
    # trace CSV. It tests numerical convergence of all reported pulse metrics.
    _, _, refined_diag = simulate(
        cfg,
        patterns,
        cfg["thermal"]["primary_G_at_Tc_W_K"],
        "normal_fraction",
        time_refinement=2,
    )
    primary_diag = runs["normal_fraction_G1nW_K"]
    convergence = {}
    for event in primary_diag["metrics"]:
        coarse = primary_diag["metrics"][event]
        fine = refined_diag["metrics"][event]
        convergence[event] = {
            key: {
                "coarse": coarse[key],
                "refined": fine[key],
                "relative_change": (
                    (fine[key] - coarse[key]) / coarse[key] if coarse[key] != 0 else 0.0
                ),
            }
            for key in (
                "peak_summed_current_deficit_uA",
                "current_deficit_area_A_s",
                "reference_template_residual_l2_fraction",
            )
        }
    runs["normal_fraction_G1nW_K_refined_dt2"] = refined_diag

    output_dir = ROOT / "outputs/tes_fenics"
    output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = output_dir / "pulse_traces.csv"
    channel_path = output_dir / "channel_summary.csv"
    result_path = output_dir / "TES_FENICS_EVALUATION.json"
    figure_prefix = ROOT / "outputs/figures/sh3_tes_fenics_pulse_comparison"
    write_csv(trace_path, all_trace_rows)
    write_csv(channel_path, all_channel_rows)
    plot_results(all_trace_rows, runs, figure_prefix)

    sigma_kev = cfg["signal"]["response_fwhm_keV"] / 2.354820045
    c_energy = sum(
        injection.energy_keV
        for channel in patterns["candidate_C"].values()
        for injection in channel
    )
    z_separation = abs(c_energy - 511.0) / sigma_kev
    roi_low, roi_high = cfg["signal"]["roi_keV"]
    normal_cdf = lambda value: 0.5 * (
        1.0 + math.erf((value - c_energy) / (sigma_kev * math.sqrt(2.0)))
    )
    fixed_mean_roi_probability = normal_cdf(roi_high) - normal_cdf(roi_low)
    result = {
        "schema_version": 1,
        "status": "PASS",
        "solver": {
            "name": "FEniCS/dolfin mixed DG0 backward-Euler nonlinear variational solve",
            "version": "2019.2.0.64.dev0",
            "meaning_of_mesh": "Each DG0 cell indexes one independent lumped TES pixel; it is not a spatial diffusion mesh",
            "cache_dir": str(ROOT / "build/fenics_cache/dijitso"),
        },
        "config": {"path": str(config_path), "sha256": file_hash(config_path)},
        "provenance": provenance,
        "derived": {
            "stability_scan_step_nW_K": 0.1,
            "largest_stable_scanned_G_nW_K": stability_upper_nw,
            "candidate_C_mean_energy_keV": c_energy,
            "candidate_C_energy_offset_from_511_eV": (c_energy - 511.0) * 1000.0,
            "detector_sigma_keV_from_420eV_FWHM": sigma_kev,
            "candidate_C_energy_only_separation_sigma": z_separation,
            "candidate_C_fixed_mean_detector_only_roi_probability": fixed_mean_roi_probability,
            "primary_time_step_convergence": convergence,
        },
        "runs": runs,
        "outputs": {
            "trace_csv": str(trace_path),
            "channel_csv": str(channel_path),
            "figure_png": str(figure_prefix.with_suffix('.png')),
            "figure_pdf": str(figure_prefix.with_suffix('.pdf')),
        },
        "interpretation_guardrails": [
            "A and B pulse shapes are counterfactual energy-matched tests, not predicted efficiencies",
            "C uses a Monte-Carlo mean arrival stream; between-replicate spread is parameter-estimation uncertainty, not TES noise",
            "No noise PSD or SQUID transfer function is available, so waveform residuals are not quoted as statistical sigma",
            "Per-channel topology is a valid discriminator if the readout preserves layer and pixel identity",
        ],
    }
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "result": str(result_path),
                "figure": str(figure_prefix.with_suffix('.png')),
                "candidate_C_energy_keV": c_energy,
                "candidate_C_energy_separation_sigma": z_separation,
                "largest_stable_scanned_G_nW_K": stability_upper_nw,
                "primary_metrics": runs["normal_fraction_G1nW_K"]["metrics"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

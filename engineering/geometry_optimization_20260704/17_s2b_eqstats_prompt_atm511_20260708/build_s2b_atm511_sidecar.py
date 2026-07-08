#!/usr/bin/env python3
"""Build/analyze the S2b atmospheric 511-keV sidecar replay."""

from __future__ import annotations

import csv
import gzip
import importlib.util
import json
import math
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
BASE_SCRIPT = (
    ROOT
    / "engineering/geometry_optimization_20260704/12_atm511_sidecar_replay_20260708"
    / "build_geo_opt_atm511_sidecar_replay.py"
)
S1_ATM_SUMMARY = (
    ROOT
    / "engineering/geometry_optimization_20260704/12_atm511_sidecar_replay_20260708"
    / "p2_geo_opt_s1_bpe_w5_atm511_sidecar_summary.json"
)
RUN_DIR = ROOT / "runs/geometry_optimization_20260704/s2b_cryo_shell_45deg_atm511_sidecar_3m_20260708"
RUN_NAME = "Atm511SidecarS2bCryoShell3M"
SOURCE = RUN_DIR / f"{RUN_NAME}.source"
LOG = RUN_DIR / f"cosima_{RUN_NAME}.log"
SIM = RUN_DIR / f"{RUN_NAME}.inc1.id1.sim.gz"
GEOMETRY_SETUP = (
    ROOT
    / "engineering/geometry_optimization_20260704/16_geoopt_s2b_cryo_shell_45deg_20260708/geometry"
    / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
SUMMARY_JSON = WORK / "s2b_atm511_sidecar_3m_summary.json"
SUMMARY_MD = WORK / "s2b_atm511_sidecar_3m_summary.md"

ACTIVE_VETO_THRESHOLD_KEV = 50.0


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_base():
    spec = importlib.util.spec_from_file_location("s2b_atm511_base", BASE_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {BASE_SCRIPT}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    mod.OUT = WORK
    mod.RUN_DIR = RUN_DIR
    mod.RUN_NAME = RUN_NAME
    mod.SOURCE = SOURCE
    mod.LOG = LOG
    mod.SIM = SIM
    mod.GEOMETRY_SETUP = GEOMETRY_SETUP
    mod.ACTIVE_VETO_THRESHOLD_KEV = ACTIVE_VETO_THRESHOLD_KEV
    mod.is_active_veto_volume = is_active_veto_volume
    return mod


def is_active_veto_volume(vol: str) -> bool:
    upper = str(vol).upper()
    return (
        upper.startswith("CSI_")
        or "ACTIVE_SHIELD" in upper
        or "CEBR3" in upper
        or "BGO" in upper
        or upper.startswith("GEOOPT_S1_PLASTICFULLWRAP")
        or upper.startswith("GEOOPT_S2B_CRYOSHELL_PLASTIC")
    )


def p2_observation_time_s() -> float:
    for line in LOG.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "Observation time:" in line:
            nums = re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", line)
            if nums:
                return float(nums[0])
    raise RuntimeError(f"cannot locate Observation time in {LOG}")


def sim_header() -> dict[str, Any]:
    header: dict[str, Any] = {}
    if not SIM.exists():
        return header
    with gzip.open(SIM, "rt", encoding="utf-8", errors="ignore") as handle:
        for raw in handle:
            line = raw.strip()
            if line.startswith("Geometry"):
                header["geometry"] = line.split(None, 1)[1] if len(line.split(None, 1)) > 1 else ""
            elif line.startswith("Seed"):
                header["seed"] = int(line.split()[1])
            elif line == "SE":
                break
    return header


def ratio(num: float, den: float) -> float | None:
    return num / den if den > 0 else None


def poisson_ratio_sigma(num_events: int, den_events: int, value: float | None) -> float | None:
    if value is None or num_events <= 0 or den_events <= 0:
        return None
    return value * math.sqrt(1.0 / num_events + 1.0 / den_events)


def analyze(events: int) -> dict[str, Any]:
    base = load_base()
    source_payload = base.write_source_and_model(events)
    source_payload["inputs"]["geometry_setup"] = rel(GEOMETRY_SETUP)
    source_payload["inputs"]["source"] = rel(SOURCE)
    source_payload["inputs"]["log"] = rel(LOG)
    source_payload["inputs"]["sim"] = rel(SIM)
    source_payload["model"]["scenario"] = "S1 nominal physical source, transported through S2b geometry"

    if not (SIM.exists() and LOG.exists()):
        payload = {
            **source_payload,
            "status": "SOURCE_BUILT_S2B_ATM511_SIDECAR_WAITING_FOR_TRANSPORT",
            "generated_at_utc": now_utc(),
            "transport": {"status": "MISSING_SIM_OR_LOG", "events_requested": events},
        }
        write_json(SUMMARY_JSON, payload)
        write_readme(payload)
        return payload

    step05_mod = base.load_step05_module()
    cat = base.parse_catalog()
    cat["observation_time_s"] = p2_observation_time_s()
    phi_4pi = float(source_payload["model"]["phi_4pi_ph_cm2_s"])
    w2 = base.summarize_window(cat, step05_mod, 510.58, 511.42, phi_4pi)
    broad = base.summarize_window(cat, step05_mod, 480.0, 550.0, phi_4pi)

    s1 = load_json(S1_ATM_SUMMARY)
    s1_w2 = s1["windows"]["w2_510p58_511p42"]
    s1_broad = s1["windows"]["broad_480_550"]
    comparisons = {}
    for name, current, baseline in (("w2_510p58_511p42", w2, s1_w2), ("broad_480_550", broad, s1_broad)):
        comparisons[name] = {}
        for stage, rate_key, event_key in (
            ("raw", "raw_rate_cps", "raw_events"),
            ("active_veto_pass", "active_rate_cps", "active_veto_pass_events"),
            ("side_compton_fov_pass", "final_rate_cps", "side_compton_fov_pass_events"),
        ):
            value = ratio(float(current[rate_key]), float(baseline[rate_key]))
            comparisons[name][stage] = {
                "s2b_over_s1_ratio": value,
                "counting_only_1sigma": poisson_ratio_sigma(
                    int(current[event_key]), int(baseline[event_key]), value
                ),
                "s2b_events": int(current[event_key]),
                "s1_events": int(baseline[event_key]),
                "s2b_rate_cps": float(current[rate_key]),
                "s1_rate_cps": float(baseline[rate_key]),
            }

    payload = {
        **source_payload,
        "status": "PASS_S2B_ATM511_4PI_SIDECAR_REPLAY",
        "generated_at_utc": now_utc(),
        "sim_header": sim_header(),
        "normalization": {
            "source_total_4pi_flux_ph_cm2_s": phi_4pi,
            "source_upward_flux_ph_cm2_s": source_payload["model"]["phi_up_ph_cm2_s"],
            "source_downward_flux_ph_cm2_s": source_payload["model"]["phi_down_ph_cm2_s"],
            "observation_time_s": float(cat["observation_time_s"]),
            "rate_weight_per_generated_event_s-1": 1.0 / float(cat["observation_time_s"]),
            "active_veto_threshold_keV": ACTIVE_VETO_THRESHOLD_KEV,
            "active_veto_volume_rule": (
                "CsI/BGO/legacy active tokens plus GeoOpt_S1_PlasticFullWrap* and "
                "GeoOpt_S2B_CryoShell_Plastic* plastic skins."
            ),
        },
        "catalog": {
            "generated_events": int(cat["generated_events"]),
            "kept_events_tes_or_active": int(cat["kept_events_tes_or_active"]),
            "tes_events": int(np.sum(cat["tes_total_keV"] > 0)),
            "active_veto_events": int(np.sum(cat["active_total_keV"] > 0)),
        },
        "windows": {"w2_510p58_511p42": w2, "broad_480_550": broad},
        "s1_reference": {
            "summary": rel(S1_ATM_SUMMARY),
            "geometry": s1.get("sim_header", {}).get("geometry"),
            "w2_final_rate_cps": s1_w2["final_rate_cps"],
            "w2_final_events": s1_w2["side_compton_fov_pass_events"],
        },
        "relative_to_s1": comparisons,
        "transport": {"status": "PASS_SIM_ANALYZED", "events_requested": events},
    }
    write_json(SUMMARY_JSON, payload)
    write_readme(payload)
    return payload


def write_readme(payload: dict[str, Any]) -> None:
    lines = [
        "# S2b Atmospheric 511 Sidecar Replay",
        "",
        f"Status: `{payload['status']}`",
        "",
        f"- Geometry: `{rel(GEOMETRY_SETUP)}`",
        f"- Source: `{rel(SOURCE)}`",
        f"- SIM: `{rel(SIM)}`",
        f"- Active veto: `{payload.get('normalization', {}).get('active_veto_volume_rule', 'pending')}`",
        "",
    ]
    w2 = payload.get("windows", {}).get("w2_510p58_511p42")
    if w2:
        cmp_row = payload["relative_to_s1"]["w2_510p58_511p42"]["side_compton_fov_pass"]
        sig = cmp_row["counting_only_1sigma"]
        lines.extend(
            [
                "## W2 Result",
                "",
                f"- S2b raw/active/final events: `{w2['raw_events']}` / `{w2['active_veto_pass_events']}` / `{w2['side_compton_fov_pass_events']}`",
                f"- S2b final atm511 rate: `{w2['final_rate_cps']:.12g}` cps",
                f"- S1 final atm511 rate: `{cmp_row['s1_rate_cps']:.12g}` cps",
                f"- S2b/S1 final ratio: `{cmp_row['s2b_over_s1_ratio']:.6g}`"
                + ("" if sig is None else f" +/- `{sig:.3g}` counting-only"),
                "",
            ]
        )
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    events = 3_000_000
    payload = analyze(events)
    print(
        json.dumps(
            {
                "status": payload["status"],
                "source": rel(SOURCE),
                "sim_exists": SIM.exists(),
                "w2_final_events": payload.get("windows", {}).get("w2_510p58_511p42", {}).get("side_compton_fov_pass_events"),
                "w2_final_cps": payload.get("windows", {}).get("w2_510p58_511p42", {}).get("final_rate_cps"),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

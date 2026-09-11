#!/usr/bin/env python3
"""Build/analyze the S3c atmospheric 511-keV sidecar replay."""

from __future__ import annotations

import gzip
import importlib.util
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
WORK = Path(__file__).resolve().parent
BASE_SCRIPT = (
    ROOT
    / "engineering/geometry_optimization_20260704/12_atm511_sidecar_replay_20260708"
    / "build_geo_opt_atm511_sidecar_replay.py"
)
S3_BASELINE_ATM_SUMMARY = (
    ROOT
    / "engineering/geometry_optimization_20260704/40_s3c_mainline_lightweight_review_20260710/retained_conclusions"
    / "s3_atm511_sidecar_3m_summary.json"
)
RUN_DIR = ROOT / "runs/geometry_optimization_20260704/s3c_bgo_w2mm_al3mm_shell_atm511_sidecar_3m_20260709"
RUN_NAME = "Atm511SidecarS3cBgoW2mmAl3mmShell3M"
SOURCE = RUN_DIR / f"{RUN_NAME}.source"
LOG = RUN_DIR / f"cosima_{RUN_NAME}.log"
SIM = RUN_DIR / f"{RUN_NAME}.inc1.id1.sim.gz"
GEOMETRY_SETUP = (
    ROOT
    / "engineering/geometry_optimization_20260704/29_geoopt_s3c_bgo_w2mm_al3mm_shell_20260709/geometry"
    / "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)
SUMMARY_JSON = WORK / "s3c_atm511_sidecar_3m_summary.json"
SUMMARY_MD = WORK / "s3c_atm511_sidecar_3m_summary.md"

ACTIVE_VETO_THRESHOLD_KEV = 50.0
EVENTS = 3_000_000
SEED = 26070917


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


def is_active_veto_volume(vol: str) -> bool:
    upper = str(vol).upper()
    return (
        upper.startswith("CSI_")
        or "ACTIVE_SHIELD" in upper
        or "ACTIVESHIELD" in upper
        or "CEBR3" in upper
        or "BGO" in upper
        or upper.startswith("GEOOPT_S1_PLASTICFULLWRAP")
        or upper.startswith("GEOOPT_S2B_CRYOSHELL_PLASTIC")
    )


def load_base():
    spec = importlib.util.spec_from_file_location("s3_atm511_base", BASE_SCRIPT)
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


def write_readme(payload: dict[str, Any]) -> None:
    w2 = payload.get("windows", {}).get("w2_510p58_511p42", {})
    s3 = payload.get("relative_to_s3", {}).get("w2_510p58_511p42", {})
    lines = [
        "# S3c Atmospheric 511 Sidecar Replay",
        "",
        f"Status: `{payload.get('status')}`",
        "",
        f"- Geometry: `{rel(GEOMETRY_SETUP)}`",
        f"- Source: `{rel(SOURCE)}`",
        f"- SIM: `{rel(SIM)}`",
        "- Active veto: `BGO/CsI active scintillator + ActiveShield/CEBR3 + GeoOpt_S2B_CryoShell_Plastic*`; W/Al mechanical shell excluded",
        "",
        "## W2 Result",
        "",
        f"- S3c raw/active/final events: `{w2.get('raw_events')}` / `{w2.get('active_veto_pass_events')}` / `{w2.get('side_compton_fov_pass_events')}`",
        f"- S3c final atm511 rate: `{w2.get('final_rate_cps')} cps`",
    ]
    if s3:
        final = s3.get("side_compton_fov_pass", {})
        lines.append(
            f"- S3c/S3 final ratio: `{final.get('s3c_over_s3_ratio')}` +/- `{final.get('counting_only_1sigma')}` counting-only"
        )
    SUMMARY_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def analyze(events: int = EVENTS) -> dict[str, Any]:
    base = load_base()
    source_payload = base.write_source_and_model(events)
    # Force S3c geometry/seed/run name into the generated source if base rewrote paths
    if SOURCE.exists():
        text = SOURCE.read_text(encoding="utf-8")
        text = re.sub(r"^Geometry\s+.*$", f"Geometry {rel(GEOMETRY_SETUP)}", text, count=1, flags=re.M)
        text = re.sub(r"^Seed\s+.*$", f"Seed {SEED}", text, count=1, flags=re.M)
        # ensure run directory FileName points at the S3c run dir
        text = text.replace(
            "runs/geometry_optimization_20260704/p2_atm511_sidecar_s1_nominal_geo_opt_s1_bpe_w5_20260708/",
            f"{rel(RUN_DIR)}/",
        )
        text = text.replace(
            "runs/geometry_optimization_20260704/s2b_cryo_shell_45deg_atm511_sidecar_3m_20260708/",
            f"{rel(RUN_DIR)}/",
        )
        SOURCE.write_text(text, encoding="utf-8")

    source_payload["inputs"]["geometry_setup"] = rel(GEOMETRY_SETUP)
    source_payload["inputs"]["source"] = rel(SOURCE)
    source_payload["inputs"]["log"] = rel(LOG)
    source_payload["inputs"]["sim"] = rel(SIM)
    source_payload["model"]["scenario"] = "S1 nominal physical ATM511 source, transported through S3c geometry"

    if not (SIM.exists() and LOG.exists()):
        payload = {
            **source_payload,
            "status": "SOURCE_BUILT_S3C_ATM511_SIDECAR_WAITING_FOR_TRANSPORT",
            "generated_at_utc": now_utc(),
            "transport": {"status": "MISSING_SIM_OR_LOG", "events_requested": events},
        }
        write_json(SUMMARY_JSON, payload)
        write_readme(payload)
        return payload

    step05_mod = base.load_step05_module()
    # Ensure active veto uses the S3c dominant-background rule.
    step05_mod.is_v3p5_active_veto_volume = is_active_veto_volume
    cat = base.parse_catalog()
    cat["observation_time_s"] = p2_observation_time_s()
    phi_4pi = float(source_payload["model"]["phi_4pi_ph_cm2_s"])
    w2 = base.summarize_window(cat, step05_mod, 510.58, 511.42, phi_4pi)
    broad = base.summarize_window(cat, step05_mod, 480.0, 550.0, phi_4pi)

    relative_to_s3 = {}
    if S3_BASELINE_ATM_SUMMARY.exists():
        s3 = load_json(S3_BASELINE_ATM_SUMMARY)
        if s3.get("status") == "PASS_S3_ATM511_4PI_SIDECAR_REPLAY":
            s3_w2 = s3["windows"]["w2_510p58_511p42"]
            s3_broad = s3["windows"]["broad_480_550"]
            for name, current, baseline in (
                ("w2_510p58_511p42", w2, s3_w2),
                ("broad_480_550", broad, s3_broad),
            ):
                relative_to_s3[name] = {}
                for stage, rate_key, event_key in (
                    ("raw", "raw_rate_cps", "raw_events"),
                    ("active_veto_pass", "active_rate_cps", "active_veto_pass_events"),
                    ("side_compton_fov_pass", "final_rate_cps", "side_compton_fov_pass_events"),
                ):
                    value = ratio(float(current[rate_key]), float(baseline[rate_key]))
                    relative_to_s3[name][stage] = {
                        "s3c_over_s3_ratio": value,
                        "counting_only_1sigma": poisson_ratio_sigma(
                            int(current[event_key]), int(baseline[event_key]), value
                        ),
                        "s3c_events": int(current[event_key]),
                        "s3_events": int(baseline[event_key]),
                        "s3c_rate_cps": float(current[rate_key]),
                        "s3_rate_cps": float(baseline[rate_key]),
                    }

    payload = {
        **source_payload,
        "status": "PASS_S3C_ATM511_4PI_SIDECAR_REPLAY",
        "generated_at_utc": now_utc(),
        "sim_header": sim_header(),
        "transport": {
            "status": "PASS_COSIMA_TRANSPORT_COMPLETE",
            "events_requested": events,
            "events_generated": events,
            "log": rel(LOG),
            "sim": rel(SIM),
        },
        "normalization": {
            "source_total_4pi_flux_ph_cm2_s": phi_4pi,
            "observation_time_s": float(cat["observation_time_s"]),
            "rate_weight_per_generated_event_s-1": 1.0 / float(cat["observation_time_s"]),
            "active_veto_threshold_keV": ACTIVE_VETO_THRESHOLD_KEV,
            "active_veto_volume_rule": (
                "BGO/CsI active scintillator + ActiveShield/CEBR3 + "
                "GeoOpt_S2B_CryoShell_Plastic*; W/Al mechanical shell excluded"
            ),
            "events_generated": events,
            "seed": SEED,
            "baseline_summary": rel(S3_BASELINE_ATM_SUMMARY),
        },
        "windows": {
            "w2_510p58_511p42": w2,
            "broad_480_550": broad,
        },
        "relative_to_s3": relative_to_s3,
    }
    write_json(SUMMARY_JSON, payload)
    write_readme(payload)
    return payload


def main() -> int:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    payload = analyze(EVENTS)
    print(json.dumps({"status": payload["status"], "summary": rel(SUMMARY_JSON)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

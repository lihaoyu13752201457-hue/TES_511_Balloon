#!/usr/bin/env python3
"""Extract auditable 3-D ledgers for the three S3d-O8 prompt W2 veto leaks.

The extractor is deliberately narrow.  It streams each authoritative raw SIM
until the requested local event block, retains the raw IA/CC HIT/HTsim records,
and stops at that block's terminating ``SE``.  It does not launch transport,
copy SIM files, recompute large-file hashes, or represent CC HIT samples as a
complete Geant4 step trajectory.

Two independent ancestry views are retained:

* IA ``origin_id -> interaction_id`` edges, including HTsim contributor links;
* CC HIT ``parent_track_id -> track_id`` edges for tracks which left deposits.

The visualization segment table likewise keeps IA chords and CC-deposit
polylines as explicitly different, incomplete geometrical records.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import os
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


PACKAGE = Path(__file__).resolve().parents[1]
DEFAULT_RUN_ROOT = Path("/home/ubuntu/TES_511_Balloon/runs")
DEFAULT_OUTPUT_DIR = PACKAGE / "data"

GEOMETRY = "S3d_O8"
CORE_GEOMETRY = "s3d_o8"
MODE = "instant"
FAMILY = "gamma"
EVENT_WEIGHT_CPS = 0.016921464065444387
W2_LO_KEV = 510.58
W2_HI_KEV = 511.42
ACTIVE_THRESHOLD_KEV = 50.0
FROZEN_RADIUS_CM = 1.35
FROZEN_DEEPEST_LAYER = 3
IF_AXIS_Y_CM = 0.0
IF_AXIS_Z_CM = -5.2

FWHM_KEV = 0.420
SIGMA_KEV = FWHM_KEV / 2.3548200450309493
PIXEL_THRESHOLD_KEV = 0.3
RESPONSE_NAMESPACE = "TES511_CORRECTED_SEVEN_FAMILY_PROMPT_KEYED_PIXEL_RESPONSE_V1"

EXPECTED_GEOMETRY_SUFFIX = (
    "engineering/geometry_optimization_20260704/"
    "43_geoopt_s3d_o8_fallback_20260712/geometry/"
    "DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup"
)

ACTIVE_BGO_VOLUMES = {
    "BGO_S3C_FullWrap_SideShell_WindowCut_40mm",
    "BGO_S3D_O8_FullWrap_BottomCap_30mm",
    "BGO_S3D_O8_FullWrap_TopAnnulus_10mm",
}
ACTIVE_PLASTIC_VOLUMES = {
    "GeoOpt_S2B_CryoShell_Plastic_SideSkin_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_BottomCap_10mm",
    "GeoOpt_S2B_CryoShell_Plastic_TopCap_10mm",
}
ACTIVE_VOLUMES = ACTIVE_BGO_VOLUMES | ACTIVE_PLASTIC_VOLUMES

CC_RE = re.compile(r"^CC\s+HIT\s+(\S+)\s+(.*)$")
KV_RE = re.compile(r"(\w+)=([^\s]+)")
IA_RE = re.compile(r"^IA\s+(\S+)\s+(.*)$")
TP_RE = re.compile(r"^TP_L(?P<layer>\d+)_(?P<pixel>\d+)$", re.IGNORECASE)


@dataclass(frozen=True)
class EventSpec:
    local_event_id: int
    relative_sim: str
    batch_id: str
    job_name: str
    transport_seed: int
    declared_sim_sha256: str
    measured_total_keV: float
    measured_multiplicity: int
    pass_veto50: bool
    step05_pass: bool
    step05_class: str
    frozen_pass: bool
    expected_pair_host: str
    expected_annihilation_host: str
    expected_tes_pixels: int
    entry_class: str

    @property
    def event_uid(self) -> str:
        return f"{GEOMETRY}__{FAMILY}__{self.job_name}__ID{self.local_event_id}"


EVENT_SPECS = (
    EventSpec(
        local_event_id=3883,
        relative_sim=(
            "particle_source_unit_repair_20260811/s3d_o8/instant_gamma_batch0003_v1/"
            "shards/shard0032/attempt01/"
            "Background_gamma_fullsphere20_batch0003_shard0032.inc1.id1.sim.gz"
        ),
        batch_id="corrected_original_gamma_instant_batch0003",
        job_name="Background_gamma_fullsphere20_batch0003_shard0032",
        transport_seed=861353411,
        declared_sim_sha256="ca49d54d77c10a6b70b0fd284b36e58dbbfe9e6271818c47608c2eb1e79b41ee",
        measured_total_keV=510.9087803866569,
        measured_multiplicity=1,
        pass_veto50=True,
        step05_pass=True,
        step05_class="single",
        frozen_pass=False,
        expected_pair_host="Nb_MagShield_Inner_Cylinder_2mm",
        expected_annihilation_host="MuMetal_MagShield_Outer_Cylinder_2mm",
        expected_tes_pixels=1,
        entry_class="bottom_oblique",
    ),
    EventSpec(
        local_event_id=19932,
        relative_sim=(
            "particle_source_unit_repair_20260811/m05_16h_90gb_campaign_batch0006_v1/"
            "stage10_seven_family/S3d_O8/instant/gamma/shard0014/attempt01/"
            "s10_gamma_instant_S3d_O8_shard0014.inc1.id1.sim.gz"
        ),
        batch_id="batch0006_mainline",
        job_name="s10_gamma_instant_S3d_O8_shard0014",
        transport_seed=1314064139,
        declared_sim_sha256="075e1f5e0d571e02422f67022d0f55c0f714c0278c61e42116fb51e6332c0aa2",
        measured_total_keV=511.0188856039452,
        measured_multiplicity=1,
        pass_veto50=True,
        step05_pass=True,
        step05_class="single",
        frozen_pass=True,
        expected_pair_host="DR_MixingChamber_Cu",
        expected_annihilation_host="DR_MixingChamber_Cu",
        expected_tes_pixels=1,
        entry_class="plus_x_plus_z_oblique_side",
    ),
    EventSpec(
        local_event_id=8081,
        relative_sim=(
            "particle_source_unit_repair_20260811/m05_16h_90gb_campaign_batch0006_v1/"
            "recovery0007_efficiency_scheduler/attempts/stage10_seven_family/S3d_O8/"
            "instant/gamma/r6_s10_gamma_instant_S3d_O8_bundle0015/attempt01/"
            "r6_s10_gamma_instant_S3d_O8_bundle0015.inc1.id1.sim.gz"
        ),
        batch_id="batch0006_mainline",
        job_name="r6_s10_gamma_instant_S3d_O8_bundle0015",
        transport_seed=2007435762,
        declared_sim_sha256="1340b3a68d99d3c3b9edc28528222f535463da5b44ea99faaa36ab1c422e8d2f",
        measured_total_keV=511.1400327836163,
        measured_multiplicity=2,
        pass_veto50=True,
        step05_pass=False,
        step05_class="veto",
        frozen_pass=False,
        expected_pair_host="Nb_MagShield_Inner_Cylinder_2mm",
        expected_annihilation_host="Cu_SubstrateSupport_SolidDisk_L0_deepest",
        expected_tes_pixels=2,
        entry_class="plus_x_minus_y_oblique_side",
    ),
)


EVENT_FIELDS = [
    "event_uid", "geometry", "family", "mode", "batch_id", "job_name",
    "transport_seed", "declared_sim_sha256", "raw_sim_sha256_recomputed",
    "source_file", "local_event_id", "sim_id_second", "sim_header_geometry",
    "sim_header_seed", "sim_TI_s", "sim_ED_keV", "sim_EC_keV", "sim_NS_keV",
    "event_weight_cps", "entry_class", "init_ia_id", "init_particle_code",
    "init_energy_keV", "init_world_x_cm", "init_world_y_cm", "init_world_z_cm",
    "init_IF_x_cm", "init_IF_y_cm", "init_IF_z_cm", "init_dir_world_x",
    "init_dir_world_y", "init_dir_world_z", "init_dir_IF_x", "init_dir_IF_y",
    "init_dir_IF_z", "ia_node_count", "cc_hit_count", "htsim_hit_count",
    "tes_cc_hit_count", "tes_raw_pixel_count", "tes_measured_pixel_count",
    "tes_raw_total_keV", "tes_measured_total_keV", "authority_measured_total_keV",
    "measurement_residual_keV", "bgo_raw_sum_keV", "plastic_raw_sum_keV",
    "active_cc_hit_count", "pass_measured_w2", "pass_veto50",
    "authority_pass_veto50", "step05_pass", "step05_class",
    "step05_flag_source", "fixed_pixel_centroid_IF_x_cm",
    "fixed_pixel_centroid_IF_y_cm", "fixed_pixel_centroid_IF_z_cm",
    "fixed_pixel_centroid_r_cm", "deepest_measured_layer", "frozen_pass",
    "authority_frozen_pass", "expected_pair_host", "observed_pair_host_nearest_cc",
    "expected_annihilation_host", "observed_annihilation_host_nearest_cc",
    "selection_level", "coordinate_contract",
]

IA_FIELDS = [
    "event_uid", "source_file", "local_event_id", "sim_line_no", "ia_id",
    "origin_ia_id", "process", "detector_type", "time_s", "world_x_cm",
    "world_y_cm", "world_z_cm", "IF_x_cm", "IF_y_cm", "IF_z_cm",
    "mother_particle_code", "mother_dir_world_x", "mother_dir_world_y",
    "mother_dir_world_z", "mother_dir_IF_x", "mother_dir_IF_y", "mother_dir_IF_z",
    "mother_pol_x", "mother_pol_y", "mother_pol_z", "mother_energy_keV",
    "secondary_particle_code", "secondary_dir_world_x", "secondary_dir_world_y",
    "secondary_dir_world_z", "secondary_dir_IF_x", "secondary_dir_IF_y",
    "secondary_dir_IF_z", "secondary_pol_x", "secondary_pol_y", "secondary_pol_z",
    "secondary_energy_keV", "nearest_cc_seq", "nearest_cc_volume",
    "nearest_cc_distance_cm", "host_volume_nearest_cc_within_0p01cm",
]

CC_FIELDS = [
    "event_uid", "source_file", "local_event_id", "sim_line_no", "cc_seq",
    "volume", "volume_role", "edep_keV", "world_x_cm", "world_y_cm",
    "world_z_cm", "IF_x_cm", "IF_y_cm", "IF_z_cm", "time_s", "secondary_particle",
    "track_id", "parent_track_id", "secondary_process", "transport_primary",
    "parent_particle", "creator_process", "primary_track_id", "tes_pixel_uid",
    "tes_layer", "coordinate_frame", "trajectory_semantics",
]

HTSIM_FIELDS = [
    "event_uid", "source_file", "local_event_id", "sim_line_no", "htsim_seq",
    "detector_type", "raw_x", "raw_y", "raw_z", "coordinate_frame",
    "world_x_cm", "world_y_cm", "world_z_cm", "IF_x_cm", "IF_y_cm", "IF_z_cm",
    "energy_keV", "time_s", "contributing_ia_ids_json", "contributing_ia_count",
    "matched_pixel_uid", "matched_cc_energy_keV", "pixel_energy_residual_keV",
]

EDGE_FIELDS = [
    "event_uid", "edge_id", "graph_kind", "relation", "from_id", "to_id",
    "from_type", "to_type", "process", "particle", "source_record", "notes",
]

VERTEX_FIELDS = [
    "event_uid", "vertex_id", "vertex_kind", "source_record", "source_record_id",
    "process_or_role", "particle", "volume", "track_id", "world_x_cm",
    "world_y_cm", "world_z_cm", "IF_x_cm", "IF_y_cm", "IF_z_cm", "time_s",
    "energy_keV", "coordinate_frame", "coordinate_semantics",
]

SEGMENT_FIELDS = [
    "event_uid", "segment_id", "segment_kind", "from_vertex_id", "to_vertex_id",
    "track_id", "particle", "process", "start_world_x_cm", "start_world_y_cm",
    "start_world_z_cm", "end_world_x_cm", "end_world_y_cm", "end_world_z_cm",
    "start_IF_x_cm", "start_IF_y_cm", "start_IF_z_cm", "end_IF_x_cm",
    "end_IF_y_cm", "end_IF_z_cm", "start_time_s", "end_time_s",
    "start_volume", "end_volume", "is_complete_geant4_step_path", "segment_semantics",
]


def world_to_instrument(x: float, y: float, z: float) -> tuple[float, float, float]:
    """World -> InstrumentFrame for InstrumentFrame = World Ry(+45 deg)."""
    c = math.sqrt(0.5)
    return c * (x - z), y, c * (x + z)


def canonical_json_bytes(payload: Any) -> bytes:
    return (
        json.dumps(
            payload,
            indent=2,
            ensure_ascii=False,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def keyed_standard_normal(*parts: object) -> float:
    encoded = canonical_json_bytes([RESPONSE_NAMESPACE, *parts])
    digest = hashlib.sha256(encoded).digest()
    denominator = float(1 << 64)
    u1 = (int.from_bytes(digest[:8], "big") + 0.5) / denominator
    u2 = (int.from_bytes(digest[8:16], "big") + 0.5) / denominator
    return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)


def parse_int(value: str, *, label: str) -> int:
    try:
        return int(value.strip())
    except ValueError as exc:
        raise RuntimeError(f"invalid integer {label}={value!r}") from exc


def parse_float(value: str, *, label: str) -> float:
    try:
        result = float(value.strip())
    except ValueError as exc:
        raise RuntimeError(f"invalid float {label}={value!r}") from exc
    if not math.isfinite(result):
        raise RuntimeError(f"non-finite float {label}={value!r}")
    return result


def volume_role(volume: str) -> str:
    if TP_RE.match(volume):
        return "tes"
    if volume in ACTIVE_BGO_VOLUMES:
        return "active_bgo"
    if volume in ACTIVE_PLASTIC_VOLUMES:
        return "active_plastic"
    return "passive_or_uninstrumented"


def parse_ia(line: str, *, event_uid: str, source_file: str, local_id: int,
             line_no: int) -> dict[str, Any]:
    match = IA_RE.match(line)
    if match is None:
        raise RuntimeError(f"malformed IA line {line_no}: {line}")
    process, payload = match.groups()
    fields = [field.strip() for field in payload.split(";")]
    if len(fields) < 23:
        raise RuntimeError(f"IA line {line_no} has {len(fields)} fields, expected >=23")
    world = tuple(parse_float(fields[i], label=f"IA[{i}]") for i in (4, 5, 6))
    if_xyz = world_to_instrument(*world)
    mother_dir = tuple(parse_float(fields[i], label=f"IA[{i}]") for i in (8, 9, 10))
    mother_if = world_to_instrument(*mother_dir)
    secondary_dir = tuple(parse_float(fields[i], label=f"IA[{i}]") for i in (16, 17, 18))
    secondary_if = world_to_instrument(*secondary_dir)
    return {
        "event_uid": event_uid,
        "source_file": source_file,
        "local_event_id": local_id,
        "sim_line_no": line_no,
        "ia_id": parse_int(fields[0], label="ia_id"),
        "origin_ia_id": parse_int(fields[1], label="origin_ia_id"),
        "process": process,
        "detector_type": parse_int(fields[2], label="detector_type"),
        "time_s": parse_float(fields[3], label="ia_time_s"),
        "world_x_cm": world[0], "world_y_cm": world[1], "world_z_cm": world[2],
        "IF_x_cm": if_xyz[0], "IF_y_cm": if_xyz[1], "IF_z_cm": if_xyz[2],
        "mother_particle_code": parse_int(fields[7], label="mother_particle_code"),
        "mother_dir_world_x": mother_dir[0], "mother_dir_world_y": mother_dir[1],
        "mother_dir_world_z": mother_dir[2],
        "mother_dir_IF_x": mother_if[0], "mother_dir_IF_y": mother_if[1],
        "mother_dir_IF_z": mother_if[2],
        "mother_pol_x": parse_float(fields[11], label="mother_pol_x"),
        "mother_pol_y": parse_float(fields[12], label="mother_pol_y"),
        "mother_pol_z": parse_float(fields[13], label="mother_pol_z"),
        "mother_energy_keV": parse_float(fields[14], label="mother_energy_keV"),
        "secondary_particle_code": parse_int(fields[15], label="secondary_particle_code"),
        "secondary_dir_world_x": secondary_dir[0],
        "secondary_dir_world_y": secondary_dir[1],
        "secondary_dir_world_z": secondary_dir[2],
        "secondary_dir_IF_x": secondary_if[0],
        "secondary_dir_IF_y": secondary_if[1],
        "secondary_dir_IF_z": secondary_if[2],
        "secondary_pol_x": parse_float(fields[19], label="secondary_pol_x"),
        "secondary_pol_y": parse_float(fields[20], label="secondary_pol_y"),
        "secondary_pol_z": parse_float(fields[21], label="secondary_pol_z"),
        "secondary_energy_keV": parse_float(fields[22], label="secondary_energy_keV"),
        "nearest_cc_seq": "", "nearest_cc_volume": "", "nearest_cc_distance_cm": "",
        "host_volume_nearest_cc_within_0p01cm": "",
    }


def parse_cc(line: str, *, event_uid: str, source_file: str, local_id: int,
             line_no: int, cc_seq: int) -> dict[str, Any]:
    match = CC_RE.match(line)
    if match is None:
        raise RuntimeError(f"malformed CC HIT line {line_no}: {line}")
    volume, payload = match.groups()
    kv = dict(KV_RE.findall(payload))
    required = {
        "edep_keV", "x", "y", "z", "t", "sec", "tid", "pid", "sproc",
        "prim", "par", "cproc", "primid",
    }
    missing = sorted(required - set(kv))
    if missing:
        raise RuntimeError(f"CC HIT line {line_no} lacks fields: {missing}")
    world = tuple(parse_float(kv[name], label=f"CC.{name}") for name in ("x", "y", "z"))
    if_xyz = world_to_instrument(*world)
    pixel = TP_RE.match(volume)
    return {
        "event_uid": event_uid,
        "source_file": source_file,
        "local_event_id": local_id,
        "sim_line_no": line_no,
        "cc_seq": cc_seq,
        "volume": volume,
        "volume_role": volume_role(volume),
        "edep_keV": parse_float(kv["edep_keV"], label="CC.edep_keV"),
        "world_x_cm": world[0], "world_y_cm": world[1], "world_z_cm": world[2],
        "IF_x_cm": if_xyz[0], "IF_y_cm": if_xyz[1], "IF_z_cm": if_xyz[2],
        "time_s": parse_float(kv["t"], label="CC.t"),
        "secondary_particle": kv["sec"],
        "track_id": parse_int(kv["tid"], label="CC.tid"),
        "parent_track_id": parse_int(kv["pid"], label="CC.pid"),
        "secondary_process": kv["sproc"],
        "transport_primary": kv["prim"],
        "parent_particle": kv["par"],
        "creator_process": kv["cproc"],
        "primary_track_id": parse_int(kv["primid"], label="CC.primid"),
        "tes_pixel_uid": volume if pixel else "",
        "tes_layer": int(pixel.group("layer")) if pixel else "",
        "coordinate_frame": "world",
        "trajectory_semantics": (
            "recorded energy-deposit sample; not a complete Geant4 step or boundary path"
        ),
    }


def parse_htsim(line: str, *, event_uid: str, source_file: str, local_id: int,
                line_no: int, htsim_seq: int) -> dict[str, Any]:
    payload = line.split("HTsim", 1)[1].strip()
    fields = [field.strip() for field in payload.split(";")]
    if len(fields) < 6:
        raise RuntimeError(f"HTsim line {line_no} has {len(fields)} fields, expected >=6")
    detector_type = parse_int(fields[0], label="HTsim.detector_type")
    raw_xyz = tuple(parse_float(fields[i], label=f"HTsim[{i}]") for i in (1, 2, 3))
    contributors = [parse_int(value, label="HTsim.contributor") for value in fields[6:] if value]
    if detector_type == 2:
        coordinate_frame = "world_fixed_tes_pixel_center"
        world: tuple[float | str, float | str, float | str] = raw_xyz
        if_xyz: tuple[float | str, float | str, float | str] = world_to_instrument(*raw_xyz)
    else:
        coordinate_frame = "detector_local_or_aggregate__not_world"
        world = ("", "", "")
        if_xyz = ("", "", "")
    return {
        "event_uid": event_uid,
        "source_file": source_file,
        "local_event_id": local_id,
        "sim_line_no": line_no,
        "htsim_seq": htsim_seq,
        "detector_type": detector_type,
        "raw_x": raw_xyz[0], "raw_y": raw_xyz[1], "raw_z": raw_xyz[2],
        "coordinate_frame": coordinate_frame,
        "world_x_cm": world[0], "world_y_cm": world[1], "world_z_cm": world[2],
        "IF_x_cm": if_xyz[0], "IF_y_cm": if_xyz[1], "IF_z_cm": if_xyz[2],
        "energy_keV": parse_float(fields[4], label="HTsim.energy_keV"),
        "time_s": parse_float(fields[5], label="HTsim.time_s"),
        "contributing_ia_ids_json": json.dumps(contributors, separators=(",", ":")),
        "contributing_ia_count": len(contributors),
        "_contributing_ia_ids": contributors,
        "matched_pixel_uid": "", "matched_cc_energy_keV": "",
        "pixel_energy_residual_keV": "",
    }


def read_target_event(spec: EventSpec, run_root: Path) -> dict[str, Any]:
    path = (run_root / spec.relative_sim).resolve()
    if not path.is_file() or path.stat().st_size <= 0:
        raise FileNotFoundError(f"raw SIM is missing or empty: {path}")
    header_geometry: str | None = None
    header_seed: int | None = None
    event: dict[str, Any] = {
        "source_file": str(path),
        "local_event_id": spec.local_event_id,
        "sim_id_second": None,
        "sim_TI_s": None,
        "sim_ED_keV": None,
        "sim_EC_keV": None,
        "sim_NS_keV": None,
        "ia": [],
        "cc": [],
        "htsim": [],
    }
    in_target = False
    found = 0
    terminated = False
    with gzip.open(path, "rt", encoding="utf-8", errors="strict") as handle:
        for line_no, raw in enumerate(handle, 1):
            line = raw.strip()
            if header_geometry is None and line.startswith("Geometry "):
                header_geometry = line.split(maxsplit=1)[1].strip()
            if header_seed is None and line.startswith("Seed "):
                header_seed = parse_int(line.split()[1], label="header_seed")
            if line.startswith("ID "):
                parts = line.split()
                if len(parts) < 3:
                    raise RuntimeError(f"malformed ID line {line_no}: {line}")
                current = parse_int(parts[1], label="ID.first")
                if current == spec.local_event_id:
                    if found:
                        raise RuntimeError(f"duplicate target ID {current} in {path}")
                    found += 1
                    in_target = True
                    event["sim_id_second"] = parse_int(parts[2], label="ID.second")
                    event["id_line_no"] = line_no
                elif in_target:
                    raise RuntimeError(f"ID before target event terminating SE in {path}")
                continue
            if not in_target:
                continue
            if line == "SE":
                terminated = True
                event["se_line_no"] = line_no
                break
            if line.startswith("TI "):
                event["sim_TI_s"] = parse_float(line.split()[1], label="TI")
            elif line.startswith("ED "):
                event["sim_ED_keV"] = parse_float(line.split()[1], label="ED")
            elif line.startswith("EC "):
                event["sim_EC_keV"] = parse_float(line.split()[1], label="EC")
            elif line.startswith("NS "):
                event["sim_NS_keV"] = parse_float(line.split()[1], label="NS")
            elif line.startswith("IA "):
                event["ia"].append(
                    parse_ia(
                        line,
                        event_uid=spec.event_uid,
                        source_file=str(path),
                        local_id=spec.local_event_id,
                        line_no=line_no,
                    )
                )
            elif line.startswith("CC HIT "):
                event["cc"].append(
                    parse_cc(
                        line,
                        event_uid=spec.event_uid,
                        source_file=str(path),
                        local_id=spec.local_event_id,
                        line_no=line_no,
                        cc_seq=len(event["cc"]) + 1,
                    )
                )
            elif line.startswith("HTsim "):
                event["htsim"].append(
                    parse_htsim(
                        line,
                        event_uid=spec.event_uid,
                        source_file=str(path),
                        local_id=spec.local_event_id,
                        line_no=line_no,
                        htsim_seq=len(event["htsim"]) + 1,
                    )
                )
    if found != 1 or not terminated:
        raise RuntimeError(
            f"target ID {spec.local_event_id} extraction failed: found={found}, terminated={terminated}"
        )
    if header_geometry is None or header_seed is None:
        raise RuntimeError(f"SIM header lacks Geometry or Seed: {path}")
    event["sim_header_geometry"] = header_geometry
    event["sim_header_seed"] = header_seed
    return event


def squared_distance(left: dict[str, Any], right: dict[str, Any]) -> float:
    return math.fsum(
        (float(left[key]) - float(right[key])) ** 2
        for key in ("world_x_cm", "world_y_cm", "world_z_cm")
    )


def attach_nearest_cc(ia_rows: list[dict[str, Any]], cc_rows: list[dict[str, Any]]) -> None:
    for ia in ia_rows:
        if not cc_rows:
            continue
        nearest = min(cc_rows, key=lambda row: squared_distance(ia, row))
        distance = math.sqrt(squared_distance(ia, nearest))
        ia["nearest_cc_seq"] = nearest["cc_seq"]
        ia["nearest_cc_volume"] = nearest["volume"]
        ia["nearest_cc_distance_cm"] = distance
        if distance <= 0.01:
            ia["host_volume_nearest_cc_within_0p01cm"] = nearest["volume"]


def pixel_groups(cc_rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in cc_rows:
        uid = str(row["tes_pixel_uid"])
        if not uid:
            continue
        group = grouped.setdefault(
            uid,
            {
                "pixel_uid": uid,
                "layer": int(row["tes_layer"]),
                "raw_keV": 0.0,
                "wx": 0.0,
                "wy": 0.0,
                "wz": 0.0,
                "cc_count": 0,
            },
        )
        energy = float(row["edep_keV"])
        group["raw_keV"] += energy
        group["wx"] += energy * float(row["world_x_cm"])
        group["wy"] += energy * float(row["world_y_cm"])
        group["wz"] += energy * float(row["world_z_cm"])
        group["cc_count"] += 1
    for group in grouped.values():
        energy = float(group["raw_keV"])
        group["deposit_centroid_world_x_cm"] = group["wx"] / energy
        group["deposit_centroid_world_y_cm"] = group["wy"] / energy
        group["deposit_centroid_world_z_cm"] = group["wz"] / energy
    return grouped


def match_tes_htsim_to_pixels(ht_rows: list[dict[str, Any]],
                              pixels: dict[str, dict[str, Any]]) -> None:
    tes_ht = [row for row in ht_rows if int(row["detector_type"]) == 2]
    if len(tes_ht) != len(pixels):
        raise RuntimeError(f"TES HTsim/pixel count mismatch: {len(tes_ht)} != {len(pixels)}")
    unmatched = set(pixels)
    for ht in sorted(tes_ht, key=lambda row: int(row["htsim_seq"])):
        if not unmatched:
            raise RuntimeError("no unmatched TES pixel for HTsim")
        uid = min(
            unmatched,
            key=lambda key: (abs(float(pixels[key]["raw_keV"]) - float(ht["energy_keV"])), key),
        )
        group = pixels[uid]
        residual = float(group["raw_keV"]) - float(ht["energy_keV"])
        if abs(residual) > 1.0e-3:
            raise RuntimeError(
                f"HTsim/pixel energy mismatch for {uid}: residual={residual:.12g} keV"
            )
        ht["matched_pixel_uid"] = uid
        ht["matched_cc_energy_keV"] = group["raw_keV"]
        ht["pixel_energy_residual_keV"] = residual
        group["pixel_center_world_x_cm"] = ht["world_x_cm"]
        group["pixel_center_world_y_cm"] = ht["world_y_cm"]
        group["pixel_center_world_z_cm"] = ht["world_z_cm"]
        group["pixel_center_IF_x_cm"] = ht["IF_x_cm"]
        group["pixel_center_IF_y_cm"] = ht["IF_y_cm"]
        group["pixel_center_IF_z_cm"] = ht["IF_z_cm"]
        unmatched.remove(uid)


def measured_pixels(spec: EventSpec, pixels: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    kept = []
    for uid in sorted(pixels):
        group = pixels[uid]
        normal = keyed_standard_normal(
            CORE_GEOMETRY,
            MODE,
            FAMILY,
            spec.batch_id,
            spec.transport_seed,
            spec.job_name,
            spec.local_event_id,
            uid,
        )
        measured = float(group["raw_keV"]) + SIGMA_KEV * normal
        group["response_standard_normal"] = normal
        group["measured_keV_before_threshold"] = measured
        group["passes_pixel_threshold"] = measured >= PIXEL_THRESHOLD_KEV
        if group["passes_pixel_threshold"]:
            group["measured_keV"] = measured
            kept.append(group)
    return kept


def fixed_pixel_centroid(measured: list[dict[str, Any]]) -> tuple[float, float, float, float] | None:
    if not measured:
        return None
    total = math.fsum(float(row["measured_keV"]) for row in measured)
    x = math.fsum(float(row["measured_keV"]) * float(row["pixel_center_IF_x_cm"])
                  for row in measured) / total
    y = math.fsum(float(row["measured_keV"]) * float(row["pixel_center_IF_y_cm"])
                  for row in measured) / total
    z = math.fsum(float(row["measured_keV"]) * float(row["pixel_center_IF_z_cm"])
                  for row in measured) / total
    radius = math.hypot(y - IF_AXIS_Y_CM, z - IF_AXIS_Z_CM)
    return x, y, z, radius


def ancestor_chain(start: int, ia_by_id: dict[int, dict[str, Any]]) -> list[int]:
    chain = []
    current = start
    seen: set[int] = set()
    while current != 0:
        if current in seen:
            raise RuntimeError(f"IA ancestry cycle at {current}")
        if current not in ia_by_id:
            raise RuntimeError(f"IA ancestry references missing node {current}")
        seen.add(current)
        chain.append(current)
        current = int(ia_by_id[current]["origin_ia_id"])
    return chain


def host_for_first_process(ia_rows: list[dict[str, Any]], process: str) -> str:
    rows = sorted(
        (row for row in ia_rows if row["process"] == process),
        key=lambda row: int(row["ia_id"]),
    )
    return str(rows[0]["host_volume_nearest_cc_within_0p01cm"]) if rows else ""


def selection_level(spec: EventSpec) -> str:
    if spec.frozen_pass:
        return "frozen_survivor"
    if spec.step05_pass:
        return "step05_survivor__frozen_reject"
    return "veto50_survivor__step05_reject"


def build_edges(event_uid: str, ia_rows: list[dict[str, Any]],
                cc_rows: list[dict[str, Any]], ht_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges: list[dict[str, Any]] = []

    def add(**values: Any) -> None:
        values["edge_id"] = f"{event_uid}__EDGE{len(edges) + 1:05d}"
        edges.append(values)

    for ia in sorted(ia_rows, key=lambda row: int(row["ia_id"])):
        ia_id = int(ia["ia_id"])
        origin = int(ia["origin_ia_id"])
        add(
            event_uid=event_uid,
            graph_kind="ia_ancestry",
            relation="initializes" if origin == 0 else "origin_interaction",
            from_id="EVENT_ROOT" if origin == 0 else f"IA:{origin}",
            to_id=f"IA:{ia_id}",
            from_type="event_root" if origin == 0 else "ia_node",
            to_type="ia_node",
            process=ia["process"],
            particle=ia["secondary_particle_code"],
            source_record=f"IA line {ia['sim_line_no']}",
            notes="exact SIM IA origin relation",
        )

    track_relations: dict[int, tuple[int, str, str]] = {}
    for cc in cc_rows:
        tid = int(cc["track_id"])
        relation = (int(cc["parent_track_id"]), str(cc["secondary_particle"]),
                    str(cc["creator_process"]))
        previous = track_relations.setdefault(tid, relation)
        if previous != relation:
            raise RuntimeError(f"inconsistent parent/particle/creator for track {tid}")
    for tid, (pid, particle, creator) in sorted(track_relations.items()):
        add(
            event_uid=event_uid,
            graph_kind="cc_track_ancestry",
            relation="parent_track",
            from_id=f"TRACK:{pid}",
            to_id=f"TRACK:{tid}",
            from_type="track_root" if pid == 0 else "track",
            to_type="track",
            process=creator,
            particle=particle,
            source_record="deduplicated CC HIT tid/pid",
            notes="deposit-bearing track ancestry; tracks without CC deposits may be absent",
        )
    for cc in cc_rows:
        add(
            event_uid=event_uid,
            graph_kind="cc_track_ancestry",
            relation="deposits_at",
            from_id=f"TRACK:{cc['track_id']}",
            to_id=f"CC:{cc['cc_seq']}",
            from_type="track",
            to_type="cc_deposit",
            process=cc["secondary_process"],
            particle=cc["secondary_particle"],
            source_record=f"CC HIT line {cc['sim_line_no']}",
            notes="exact deposit membership; not a full step path",
        )
    for ht in ht_rows:
        for ia_id in ht["_contributing_ia_ids"]:
            add(
                event_uid=event_uid,
                graph_kind="htsim_attribution",
                relation="contributes_to_detector_hit",
                from_id=f"IA:{ia_id}",
                to_id=f"HT:{ht['htsim_seq']}",
                from_type="ia_node",
                to_type="htsim_hit",
                process="",
                particle="",
                source_record=f"HTsim line {ht['sim_line_no']}",
                notes="exact IA IDs printed by SIM HTsim record",
            )
    return edges


def build_vertices(event_uid: str, ia_rows: list[dict[str, Any]],
                   cc_rows: list[dict[str, Any]], ht_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ia in ia_rows:
        rows.append({
            "event_uid": event_uid,
            "vertex_id": f"IA:{ia['ia_id']}",
            "vertex_kind": "ia_interaction",
            "source_record": "IA",
            "source_record_id": ia["ia_id"],
            "process_or_role": ia["process"],
            "particle": ia["secondary_particle_code"],
            "volume": ia["host_volume_nearest_cc_within_0p01cm"],
            "track_id": "",
            "world_x_cm": ia["world_x_cm"], "world_y_cm": ia["world_y_cm"],
            "world_z_cm": ia["world_z_cm"],
            "IF_x_cm": ia["IF_x_cm"], "IF_y_cm": ia["IF_y_cm"],
            "IF_z_cm": ia["IF_z_cm"],
            "time_s": ia["time_s"],
            "energy_keV": ia["secondary_energy_keV"],
            "coordinate_frame": "world_and_InstrumentFrame",
            "coordinate_semantics": "recorded SIM interaction vertex",
        })
    for cc in cc_rows:
        rows.append({
            "event_uid": event_uid,
            "vertex_id": f"CC:{cc['cc_seq']}",
            "vertex_kind": "cc_energy_deposit",
            "source_record": "CC HIT",
            "source_record_id": cc["cc_seq"],
            "process_or_role": cc["secondary_process"],
            "particle": cc["secondary_particle"],
            "volume": cc["volume"],
            "track_id": cc["track_id"],
            "world_x_cm": cc["world_x_cm"], "world_y_cm": cc["world_y_cm"],
            "world_z_cm": cc["world_z_cm"],
            "IF_x_cm": cc["IF_x_cm"], "IF_y_cm": cc["IF_y_cm"],
            "IF_z_cm": cc["IF_z_cm"],
            "time_s": cc["time_s"],
            "energy_keV": cc["edep_keV"],
            "coordinate_frame": "world_and_InstrumentFrame",
            "coordinate_semantics": "recorded deposit sample; not a full Geant4 step",
        })
    for ht in ht_rows:
        if int(ht["detector_type"]) != 2:
            continue
        rows.append({
            "event_uid": event_uid,
            "vertex_id": f"HT:{ht['htsim_seq']}",
            "vertex_kind": "tes_fixed_pixel_center",
            "source_record": "HTsim type 2",
            "source_record_id": ht["htsim_seq"],
            "process_or_role": "tes_pixel_aggregate",
            "particle": "",
            "volume": ht["matched_pixel_uid"],
            "track_id": "",
            "world_x_cm": ht["world_x_cm"], "world_y_cm": ht["world_y_cm"],
            "world_z_cm": ht["world_z_cm"],
            "IF_x_cm": ht["IF_x_cm"], "IF_y_cm": ht["IF_y_cm"],
            "IF_z_cm": ht["IF_z_cm"],
            "time_s": ht["time_s"],
            "energy_keV": ht["energy_keV"],
            "coordinate_frame": "world_and_InstrumentFrame",
            "coordinate_semantics": "fixed TES pixel center, not deposit centroid",
        })
    return rows


def build_segments(event_uid: str, ia_rows: list[dict[str, Any]],
                   cc_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ia_by_id = {int(row["ia_id"]): row for row in ia_rows}

    def add(kind: str, left: dict[str, Any], right: dict[str, Any], **extra: Any) -> None:
        rows.append({
            "event_uid": event_uid,
            "segment_id": f"{event_uid}__SEG{len(rows) + 1:05d}",
            "segment_kind": kind,
            "from_vertex_id": extra["from_vertex_id"],
            "to_vertex_id": extra["to_vertex_id"],
            "track_id": extra.get("track_id", ""),
            "particle": extra.get("particle", ""),
            "process": extra.get("process", ""),
            "start_world_x_cm": left["world_x_cm"],
            "start_world_y_cm": left["world_y_cm"],
            "start_world_z_cm": left["world_z_cm"],
            "end_world_x_cm": right["world_x_cm"],
            "end_world_y_cm": right["world_y_cm"],
            "end_world_z_cm": right["world_z_cm"],
            "start_IF_x_cm": left["IF_x_cm"],
            "start_IF_y_cm": left["IF_y_cm"],
            "start_IF_z_cm": left["IF_z_cm"],
            "end_IF_x_cm": right["IF_x_cm"],
            "end_IF_y_cm": right["IF_y_cm"],
            "end_IF_z_cm": right["IF_z_cm"],
            "start_time_s": left["time_s"],
            "end_time_s": right["time_s"],
            "start_volume": extra.get("start_volume", ""),
            "end_volume": extra.get("end_volume", ""),
            "is_complete_geant4_step_path": False,
            "segment_semantics": extra["segment_semantics"],
        })

    for child in sorted(ia_rows, key=lambda row: int(row["ia_id"])):
        origin = int(child["origin_ia_id"])
        if origin == 0:
            continue
        parent = ia_by_id[origin]
        add(
            "ia_chord",
            parent,
            child,
            from_vertex_id=f"IA:{origin}",
            to_vertex_id=f"IA:{child['ia_id']}",
            process=child["process"],
            particle=child["secondary_particle_code"],
            start_volume=parent["host_volume_nearest_cc_within_0p01cm"],
            end_volume=child["host_volume_nearest_cc_within_0p01cm"],
            segment_semantics=(
                "straight chord between recorded IA vertices; boundary crossings and unrecorded steps absent"
            ),
        )

    by_track: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for cc in cc_rows:
        by_track[int(cc["track_id"])].append(cc)
    for track_id, deposits in sorted(by_track.items()):
        ordered = sorted(deposits, key=lambda row: (float(row["time_s"]), int(row["cc_seq"])))
        for left, right in zip(ordered, ordered[1:]):
            add(
                "cc_deposit_polyline",
                left,
                right,
                from_vertex_id=f"CC:{left['cc_seq']}",
                to_vertex_id=f"CC:{right['cc_seq']}",
                track_id=track_id,
                particle=right["secondary_particle"],
                process=right["secondary_process"],
                start_volume=left["volume"],
                end_volume=right["volume"],
                segment_semantics=(
                    "polyline between successive recorded deposits on one tid; not a complete Geant4 step path"
                ),
            )
    return rows


def build_one(spec: EventSpec, raw: dict[str, Any]) -> tuple[
    dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]],
    list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any],
]:
    ia_rows = raw["ia"]
    cc_rows = raw["cc"]
    ht_rows = raw["htsim"]
    attach_nearest_cc(ia_rows, cc_rows)
    pixels = pixel_groups(cc_rows)
    match_tes_htsim_to_pixels(ht_rows, pixels)
    measured = measured_pixels(spec, pixels)
    centroid = fixed_pixel_centroid(measured)

    init_rows = [row for row in ia_rows if row["process"] == "INIT"]
    if len(init_rows) != 1:
        raise RuntimeError(f"{spec.event_uid}: INIT count={len(init_rows)}, expected 1")
    init = init_rows[0]
    ia_by_id = {int(row["ia_id"]): row for row in ia_rows}
    if len(ia_by_id) != len(ia_rows):
        raise RuntimeError(f"{spec.event_uid}: duplicate IA IDs")
    for row in ia_rows:
        ancestor_chain(int(row["ia_id"]), ia_by_id)
    for ht in ht_rows:
        for ia_id in ht["_contributing_ia_ids"]:
            ancestor_chain(ia_id, ia_by_id)

    bgo_sum = math.fsum(float(row["edep_keV"]) for row in cc_rows
                        if row["volume"] in ACTIVE_BGO_VOLUMES)
    plastic_sum = math.fsum(float(row["edep_keV"]) for row in cc_rows
                           if row["volume"] in ACTIVE_PLASTIC_VOLUMES)
    active_cc_count = sum(row["volume"] in ACTIVE_VOLUMES for row in cc_rows)
    raw_tes = math.fsum(float(group["raw_keV"]) for group in pixels.values())
    measured_tes = math.fsum(float(group["measured_keV"]) for group in measured)
    htsim_tes = math.fsum(float(row["energy_keV"]) for row in ht_rows
                          if int(row["detector_type"]) == 2)
    pass_w2 = W2_LO_KEV <= measured_tes < W2_HI_KEV
    pass_veto = bgo_sum < ACTIVE_THRESHOLD_KEV and plastic_sum < ACTIVE_THRESHOLD_KEV
    deepest = max((int(group["layer"]) for group in measured), default=-1)
    if centroid is None:
        cx = cy = cz = radius = ""
    else:
        cx, cy, cz, radius = centroid
    computed_frozen = bool(
        pass_w2
        and pass_veto
        and spec.step05_pass
        and centroid is not None
        and float(radius) <= FROZEN_RADIUS_CM
        and deepest <= FROZEN_DEEPEST_LAYER
    )
    pair_host = host_for_first_process(ia_rows, "PAIR")
    anni_host = host_for_first_process(ia_rows, "ANNI")

    tes_ht_rows = [row for row in ht_rows if int(row["detector_type"]) == 2]
    ancestry_processes: set[str] = set()
    tes_chains: list[list[int]] = []
    for ht in tes_ht_rows:
        for ia_id in ht["_contributing_ia_ids"]:
            chain = ancestor_chain(ia_id, ia_by_id)
            tes_chains.append(chain)
            ancestry_processes.update(str(ia_by_id[node]["process"]) for node in chain)

    errors: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    check(raw["sim_id_second"] == spec.local_event_id, "ID first/second columns differ")
    check(str(raw["sim_header_geometry"]).endswith(EXPECTED_GEOMETRY_SUFFIX),
          "SIM header geometry differs from S3d-O8 authority")
    check(int(raw["sim_header_seed"]) == spec.transport_seed, "SIM header seed differs")
    check(len(pixels) == spec.expected_tes_pixels, "raw TES pixel count differs")
    check(len(measured) == spec.measured_multiplicity, "measured TES multiplicity differs")
    check(abs(raw_tes - htsim_tes) <= 1.0e-3, "CC TES and HTsim type-2 energy differ")
    check(abs(measured_tes - spec.measured_total_keV) <= 1.0e-9,
          "keyed measured TES total differs from durable authority")
    check(active_cc_count == 0, "active BGO/plastic CC HIT is nonzero")
    check(bgo_sum == 0.0 and plastic_sum == 0.0, "active deposit sum is nonzero")
    check(pass_veto == spec.pass_veto50, "computed veto50 flag differs")
    check(pass_w2, "event does not reproduce measured W2")
    check(computed_frozen == spec.frozen_pass, "computed frozen flag differs")
    check(pair_host == spec.expected_pair_host, "nearest-CC PAIR host differs")
    check(anni_host == spec.expected_annihilation_host, "nearest-CC ANNI host differs")
    check({"INIT", "PAIR", "ANNI"}.issubset(ancestry_processes),
          "TES HTsim ancestry lacks INIT/PAIR/ANNI")

    event_row = {
        "event_uid": spec.event_uid,
        "geometry": GEOMETRY,
        "family": FAMILY,
        "mode": MODE,
        "batch_id": spec.batch_id,
        "job_name": spec.job_name,
        "transport_seed": spec.transport_seed,
        "declared_sim_sha256": spec.declared_sim_sha256,
        "raw_sim_sha256_recomputed": False,
        "source_file": raw["source_file"],
        "local_event_id": spec.local_event_id,
        "sim_id_second": raw["sim_id_second"],
        "sim_header_geometry": raw["sim_header_geometry"],
        "sim_header_seed": raw["sim_header_seed"],
        "sim_TI_s": raw["sim_TI_s"],
        "sim_ED_keV": raw["sim_ED_keV"],
        "sim_EC_keV": raw["sim_EC_keV"],
        "sim_NS_keV": raw["sim_NS_keV"],
        "event_weight_cps": EVENT_WEIGHT_CPS,
        "entry_class": spec.entry_class,
        "init_ia_id": init["ia_id"],
        "init_particle_code": init["secondary_particle_code"],
        "init_energy_keV": init["secondary_energy_keV"],
        "init_world_x_cm": init["world_x_cm"],
        "init_world_y_cm": init["world_y_cm"],
        "init_world_z_cm": init["world_z_cm"],
        "init_IF_x_cm": init["IF_x_cm"],
        "init_IF_y_cm": init["IF_y_cm"],
        "init_IF_z_cm": init["IF_z_cm"],
        "init_dir_world_x": init["secondary_dir_world_x"],
        "init_dir_world_y": init["secondary_dir_world_y"],
        "init_dir_world_z": init["secondary_dir_world_z"],
        "init_dir_IF_x": init["secondary_dir_IF_x"],
        "init_dir_IF_y": init["secondary_dir_IF_y"],
        "init_dir_IF_z": init["secondary_dir_IF_z"],
        "ia_node_count": len(ia_rows),
        "cc_hit_count": len(cc_rows),
        "htsim_hit_count": len(ht_rows),
        "tes_cc_hit_count": sum(row["volume_role"] == "tes" for row in cc_rows),
        "tes_raw_pixel_count": len(pixels),
        "tes_measured_pixel_count": len(measured),
        "tes_raw_total_keV": raw_tes,
        "tes_measured_total_keV": measured_tes,
        "authority_measured_total_keV": spec.measured_total_keV,
        "measurement_residual_keV": measured_tes - spec.measured_total_keV,
        "bgo_raw_sum_keV": bgo_sum,
        "plastic_raw_sum_keV": plastic_sum,
        "active_cc_hit_count": active_cc_count,
        "pass_measured_w2": pass_w2,
        "pass_veto50": pass_veto,
        "authority_pass_veto50": spec.pass_veto50,
        "step05_pass": spec.step05_pass,
        "step05_class": spec.step05_class,
        "step05_flag_source": "durable prompt_w2_event_summary/common-response lineage",
        "fixed_pixel_centroid_IF_x_cm": cx,
        "fixed_pixel_centroid_IF_y_cm": cy,
        "fixed_pixel_centroid_IF_z_cm": cz,
        "fixed_pixel_centroid_r_cm": radius,
        "deepest_measured_layer": deepest,
        "frozen_pass": computed_frozen,
        "authority_frozen_pass": spec.frozen_pass,
        "expected_pair_host": spec.expected_pair_host,
        "observed_pair_host_nearest_cc": pair_host,
        "expected_annihilation_host": spec.expected_annihilation_host,
        "observed_annihilation_host_nearest_cc": anni_host,
        "selection_level": selection_level(spec),
        "coordinate_contract": (
            "IA/CC xyz are world; *_IF uses inverse InstrumentFrame Ry(+45deg); "
            "HTsim type2 is fixed TES pixel center; type4 remains detector-local/aggregate"
        ),
    }

    edges = build_edges(spec.event_uid, ia_rows, cc_rows, ht_rows)
    vertices = build_vertices(spec.event_uid, ia_rows, cc_rows, ht_rows)
    segments = build_segments(spec.event_uid, ia_rows, cc_rows)
    validation = {
        "status": "PASS" if not errors else "FAIL",
        "errors": errors,
        "source_file": raw["source_file"],
        "local_event_id": spec.local_event_id,
        "header_geometry": raw["sim_header_geometry"],
        "header_seed": raw["sim_header_seed"],
        "raw_sim_hash_policy": "declared hash retained; raw SIM hash not recomputed",
        "counts": {
            "ia_nodes": len(ia_rows),
            "cc_hits": len(cc_rows),
            "htsim_hits": len(ht_rows),
            "ancestry_edges": len(edges),
            "track_vertices": len(vertices),
            "track_segments": len(segments),
            "tes_pixels": len(pixels),
            "active_cc_hits": active_cc_count,
        },
        "energy_checks_keV": {
            "tes_cc_sum": raw_tes,
            "tes_htsim_type2_sum": htsim_tes,
            "tes_measured_replayed": measured_tes,
            "tes_measured_authority": spec.measured_total_keV,
            "bgo_sum": bgo_sum,
            "plastic_sum": plastic_sum,
        },
        "selection_checks": {
            "measured_w2": pass_w2,
            "veto50": pass_veto,
            "step05_authority": spec.step05_pass,
            "fixed_pixel_centroid_r_cm": radius,
            "deepest_measured_layer": deepest,
            "frozen_replayed": computed_frozen,
            "frozen_authority": spec.frozen_pass,
        },
        "host_checks": {
            "pair_expected": spec.expected_pair_host,
            "pair_nearest_cc": pair_host,
            "annihilation_expected": spec.expected_annihilation_host,
            "annihilation_nearest_cc": anni_host,
        },
        "tes_ia_ancestry_chains": tes_chains,
        "tes_ia_ancestry_processes": sorted(ancestry_processes),
    }
    for row in ht_rows:
        row.pop("_contributing_ia_ids", None)
    return event_row, ia_rows, cc_rows, ht_rows, edges, vertices, segments, validation


def write_csv(path: Path, fields: list[str], rows: Iterable[dict[str, Any]]) -> None:
    temp = path.with_name(path.name + f".tmp-{os.getpid()}")
    with temp.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temp, path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    temp = path.with_name(path.name + f".tmp-{os.getpid()}")
    temp.write_bytes(canonical_json_bytes(payload))
    os.replace(temp, path)


def run(run_root: Path, output_dir: Path, force: bool) -> dict[str, Any]:
    outputs = {
        "events": output_dir / "prompt_events.csv",
        "ia_nodes": output_dir / "prompt_ia_nodes.csv",
        "cc_hits": output_dir / "prompt_cc_hits.csv",
        "htsim_hits": output_dir / "prompt_htsim_hits.csv",
        "ancestry_edges": output_dir / "prompt_ancestry_edges.csv",
        "track_vertices": output_dir / "prompt_track_vertices.csv",
        "track_segments": output_dir / "prompt_track_segments.csv",
        "validation": output_dir / "prompt_validation.json",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    existing = [str(path) for path in outputs.values() if path.exists()]
    if existing and not force:
        raise FileExistsError(f"refusing to overwrite existing outputs: {existing}")

    events: list[dict[str, Any]] = []
    ia_nodes: list[dict[str, Any]] = []
    cc_hits: list[dict[str, Any]] = []
    htsim_hits: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    vertices: list[dict[str, Any]] = []
    segments: list[dict[str, Any]] = []
    event_validation: dict[str, Any] = {}
    for spec in EVENT_SPECS:
        result = build_one(spec, read_target_event(spec, run_root))
        event, ia, cc, ht, event_edges, event_vertices, event_segments, validation = result
        events.append(event)
        ia_nodes.extend(ia)
        cc_hits.extend(cc)
        htsim_hits.extend(ht)
        edges.extend(event_edges)
        vertices.extend(event_vertices)
        segments.extend(event_segments)
        event_validation[spec.event_uid] = validation

    global_errors = [
        f"{uid}: {message}"
        for uid, result in event_validation.items()
        for message in result["errors"]
    ]
    row_counts = {
        "prompt_events.csv": len(events),
        "prompt_ia_nodes.csv": len(ia_nodes),
        "prompt_cc_hits.csv": len(cc_hits),
        "prompt_htsim_hits.csv": len(htsim_hits),
        "prompt_ancestry_edges.csv": len(edges),
        "prompt_track_vertices.csv": len(vertices),
        "prompt_track_segments.csv": len(segments),
    }
    validation_payload = {
        "schema_version": 1,
        "status": "PASS__S3D_O8_PROMPT_THREE_LEAK_RAW_TRACK_LEDGER" if not global_errors else "FAIL",
        "errors": global_errors,
        "scope": (
            "three measured-W2 active-veto50 prompt leaks: two Step05 survivors and one frozen survivor"
        ),
        "event_order": [spec.event_uid for spec in EVENT_SPECS],
        "raw_sim_policy": (
            "read-only gzip stream to one target block per SIM; no transport, copy, or large-SIM rehash"
        ),
        "coordinate_contract": {
            "IA_and_CC": "SIM world coordinates plus inverse Ry(+45deg) InstrumentFrame coordinates",
            "HTsim_type2": "fixed TES pixel center in world plus InstrumentFrame",
            "HTsim_other": "raw detector-local/aggregate fields retained; not promoted to world coordinates",
        },
        "trajectory_contract": {
            "ia_chord": "straight chord between recorded IA vertices; not a boundary/step record",
            "cc_deposit_polyline": (
                "successive recorded CC energy deposits on one tid; not a complete Geant4 step path"
            ),
        },
        "active_volume_contract": {
            "bgo": sorted(ACTIVE_BGO_VOLUMES),
            "plastic": sorted(ACTIVE_PLASTIC_VOLUMES),
            "expected_active_deposit_for_all_three_keV": 0.0,
        },
        "selection_contract": {
            "measured_w2_keV": [W2_LO_KEV, W2_HI_KEV],
            "active_veto_threshold_keV": ACTIVE_THRESHOLD_KEV,
            "step05_flags": "retained durable event authority; not reimplemented here",
            "frozen_radius_cm": FROZEN_RADIUS_CM,
            "frozen_deepest_layer_max": FROZEN_DEEPEST_LAYER,
        },
        "row_counts": row_counts,
        "events": event_validation,
        "outputs": {key: str(path.resolve()) for key, path in outputs.items()},
    }

    write_csv(outputs["events"], EVENT_FIELDS, events)
    write_csv(outputs["ia_nodes"], IA_FIELDS, ia_nodes)
    write_csv(outputs["cc_hits"], CC_FIELDS, cc_hits)
    write_csv(outputs["htsim_hits"], HTSIM_FIELDS, htsim_hits)
    write_csv(outputs["ancestry_edges"], EDGE_FIELDS, edges)
    write_csv(outputs["track_vertices"], VERTEX_FIELDS, vertices)
    write_csv(outputs["track_segments"], SEGMENT_FIELDS, segments)
    write_json(outputs["validation"], validation_payload)
    if global_errors:
        raise RuntimeError("prompt track ledger validation failed: " + "; ".join(global_errors))
    return validation_payload


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-root", type=Path, default=DEFAULT_RUN_ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--force", action="store_true", help="replace only this script's outputs")
    args = parser.parse_args()
    result = run(args.run_root.resolve(), args.output_dir.resolve(), args.force)
    print(json.dumps({"status": result["status"], "row_counts": result["row_counts"]},
                     indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

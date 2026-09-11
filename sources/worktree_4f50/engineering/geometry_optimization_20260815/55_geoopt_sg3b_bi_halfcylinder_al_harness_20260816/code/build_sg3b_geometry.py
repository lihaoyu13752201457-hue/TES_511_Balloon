#!/usr/bin/env python3
"""Build SG3B from SG3A without launching transport.

Physical edits only:
1. replace the flat passive Bi plate with an x'-axis upper-half cylindrical
   liner immediately inside the retained 2 mm Al near-field cylinder;
2. change the five homogeneous NbTi cable proxies to Aluminium.

The Bi liner is split around x'=[3.24, 3.60] cm to clear the retained L0 Cu
heat-sink ring.  All other geometry and detector-response definitions remain
the SG3A parent.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path(__file__).resolve()
PACKAGE = SCRIPT.parents[1]
GEOMETRY = PACKAGE / "geometry"
AUDIT = PACKAGE / "audit/sg3b_geometry_validation.json"
MASS = PACKAGE / "data/sg3b_mass_delta.json"
PARENT = SCRIPT.parents[2] / "54_geoopt_sg3a_al_cold_can_20260816/geometry"
PARENT_STEM = "DEMO2_DR_v3p5_SG3A"
STEM = "DEMO2_DR_v3p5_SG3B"

SOURCE = {
    "setup": PARENT / f"{PARENT_STEM}.geo.setup",
    "geo": PARENT / f"{PARENT_STEM}.geo",
    "det": PARENT / f"{PARENT_STEM}.det",
    "intro": PARENT / "Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo",
    "materials": PARENT / "Materials_DEMO2_DR_v3p5.geo",
}
OUTPUT = {
    "setup": GEOMETRY / f"{STEM}.geo.setup",
    "geo": GEOMETRY / f"{STEM}.geo",
    "det": GEOMETRY / f"{STEM}.det",
    "intro": GEOMETRY / "Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo",
    "materials": GEOMETRY / "Materials_DEMO2_DR_v3p5.geo",
}
PINNED = {
    "setup": (126, "4244c2d7abc2d1c877eb87da978ace239137a7e6828c54aaee3cc69e81b1be26"),
    "geo": (697592, "0179e15229060cb059e4ac6b6c6832ef8a57308ee438a5d4b2f24eb35a6f18fd"),
    "det": (56730, "f851a72c871d4fc205e0f8602be2af7eb4a2092c8142a8393b4a10beb2492de3"),
    "intro": (500, "f4ea834bf385f68a85690e018fd52d692e94e19dd93959e35e6f91efd3dbfd52"),
    "materials": (2065, "56f6c2b58f072f4350a1fed8707490ed4f0b196769a9a4e22e0acb2ebe58ae0a"),
}

OLD_BI = """// BEGIN SG3_PASSIVE_BI_MXC_TES_SHADOW_UMBRELLA_4P796MM
// Passive Bi only: this is not an active-veto volume.
// Compact canopy under the MXC and above the TES; it does not wrap the detector.
// Bounds in InstrumentFrame: x=[-3.8,4.0], y=[-2.25,2.25], z=[-2.39,-1.9104] cm.
Volume SG3_Bi_MXC_TES_ShadowUmbrella_4p796mm
SG3_Bi_MXC_TES_ShadowUmbrella_4p796mm.Material Bi
SG3_Bi_MXC_TES_ShadowUmbrella_4p796mm.Visibility 1
SG3_Bi_MXC_TES_ShadowUmbrella_4p796mm.Shape BRIK 3.9 2.25 0.2398
SG3_Bi_MXC_TES_ShadowUmbrella_4p796mm.Position 0.1 0 -2.1502
SG3_Bi_MXC_TES_ShadowUmbrella_4p796mm.Mother InstrumentFrame
// END SG3_PASSIVE_BI_MXC_TES_SHADOW_UMBRELLA_4P796MM"""

NEW_BI = """// BEGIN SG3B_PASSIVE_BI_MXC_TES_UPPER_HALF_CYLINDER_4P796MM
// Passive Bi only: this is not an active-veto volume.
// Coaxial with and 0.05 mm inside SE3_Al_Shield_Inner_Cylinder_2mm.
// Axis=x'; center=(0,0,-5.2) cm; upper y'-z' semicircle only; no lower half.
// Radial thickness=4.796 mm; outer radius=3.995 cm; inner radius=3.5154 cm.
// The x' split [3.24,3.60] cm clears the retained L0 Cu heat-sink ring.
Volume SG3B_Bi_MXC_TES_UpperHalfCylinder_Main_4p796mm
SG3B_Bi_MXC_TES_UpperHalfCylinder_Main_4p796mm.Material Bi
SG3B_Bi_MXC_TES_UpperHalfCylinder_Main_4p796mm.Visibility 1
SG3B_Bi_MXC_TES_UpperHalfCylinder_Main_4p796mm.Shape PCON 90 180 2 -3.8 3.5154 3.995 3.24 3.5154 3.995
SG3B_Bi_MXC_TES_UpperHalfCylinder_Main_4p796mm.Position 0 0 -5.2
SG3B_Bi_MXC_TES_UpperHalfCylinder_Main_4p796mm.Rotation 0 90 0
SG3B_Bi_MXC_TES_UpperHalfCylinder_Main_4p796mm.Mother InstrumentFrame

Volume SG3B_Bi_MXC_TES_UpperHalfCylinder_Aft_4p796mm
SG3B_Bi_MXC_TES_UpperHalfCylinder_Aft_4p796mm.Material Bi
SG3B_Bi_MXC_TES_UpperHalfCylinder_Aft_4p796mm.Visibility 1
SG3B_Bi_MXC_TES_UpperHalfCylinder_Aft_4p796mm.Shape PCON 90 180 2 3.6 3.5154 3.995 4.0 3.5154 3.995
SG3B_Bi_MXC_TES_UpperHalfCylinder_Aft_4p796mm.Position 0 0 -5.2
SG3B_Bi_MXC_TES_UpperHalfCylinder_Aft_4p796mm.Rotation 0 90 0
SG3B_Bi_MXC_TES_UpperHalfCylinder_Aft_4p796mm.Mother InstrumentFrame
// END SG3B_PASSIVE_BI_MXC_TES_UPPER_HALF_CYLINDER_4P796MM"""

HARNESS = (
    "NbTi_Bundle_bay_to_MXC",
    "NbTi_Bundle_MXC_CP",
    "NbTi_Bundle_CP_Still",
    "NbTi_Bundle_Still_4K",
    "NbTi_Bundle_4K_60K",
)


class BuildError(RuntimeError):
    pass


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def record(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    return {"path": str(path), "bytes": len(data), "sha256": digest(data)}


def write_once(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() == data:
            return
        raise BuildError(f"write-once target differs: {path}")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", dir=path.parent, delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def json_once(path: Path, payload: dict[str, object]) -> None:
    encoded = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    if path.exists():
        old = json.loads(path.read_text())
        new = json.loads(encoded)
        old.pop("generated_at_utc", None); new.pop("generated_at_utc", None)
        if old != new:
            raise BuildError(f"write-once JSON differs: {path}")
        return
    write_once(path, encoded)


def verify_parent() -> dict[str, dict[str, object]]:
    out = {}
    for key, path in SOURCE.items():
        item = record(path)
        if (item["bytes"], item["sha256"]) != PINNED[key]:
            raise BuildError(f"pinned SG3A parent drift: {item}")
        out[key] = item
    return out


def replace_once(text: str, old: str, new: str) -> str:
    if text.count(old) != 1:
        raise BuildError(f"expected exact-once token: {old[:100]}")
    return text.replace(old, new, 1)


def transform_geo(parent: str) -> str:
    text = replace_once(parent, OLD_BI, NEW_BI)
    for old in HARNESS:
        new = old.replace("NbTi_Bundle", "SG3B_Al_Bundle")
        if old not in text:
            raise BuildError(f"missing harness volume: {old}")
        text = text.replace(old, new)
        text = replace_once(text, f"{new}.Material NbTiCableProxy", f"{new}.Material Aluminium")
        text = text.replace(
            f"// Volume {new}; material=NbTiCableProxy",
            f"// SG3B material-only harness proxy: {new}; material=Aluminium",
        )
    return text


def reverse_geo(candidate: str) -> str:
    text = candidate
    for old in reversed(HARNESS):
        new = old.replace("NbTi_Bundle", "SG3B_Al_Bundle")
        text = text.replace(
            f"// SG3B material-only harness proxy: {new}; material=Aluminium",
            f"// Volume {new}; material=NbTiCableProxy",
        )
        text = replace_once(text, f"{new}.Material Aluminium", f"{new}.Material NbTiCableProxy")
        text = text.replace(new, old)
    return replace_once(text, NEW_BI, OLD_BI)


def transform_det(parent: str) -> str:
    text = parent
    for old in HARNESS:
        text = text.replace(old, old.replace("NbTi_Bundle", "SG3B_Al_Bundle"))
    return text


def reverse_det(candidate: str) -> str:
    text = candidate
    for old in reversed(HARNESS):
        text = text.replace(old.replace("NbTi_Bundle", "SG3B_Al_Bundle"), old)
    return text


def expected() -> dict[str, bytes]:
    setup = "\n".join((f"Name {STEM}", "Version 1", f"Include {STEM}.geo", f"Include {STEM}.det", "SurroundingSphere 60 5 0 9 60", ""))
    return {
        "setup": setup.encode(),
        "geo": transform_geo(SOURCE["geo"].read_text()).encode(),
        "det": transform_det(SOURCE["det"].read_text()).encode(),
        "intro": SOURCE["intro"].read_bytes(),
        "materials": SOURCE["materials"].read_bytes(),
    }


def masses() -> dict[str, object]:
    nbti_volume = 87.338192
    still_volume = 24.568323
    old_flat_bi = 7.8 * 4.5 * 0.4796 * 9.747
    bi_volume = 0.5 * math.pi * (3.995**2 - 3.5154**2) * (7.04 + 0.40)
    return {
        "bi": {
            "old_flat_mass_g": old_flat_bi,
            "upper_half_cylinder_volume_cm3": bi_volume,
            "upper_half_cylinder_mass_g": bi_volume * 9.747,
            "delta_g": bi_volume * 9.747 - old_flat_bi,
        },
        "harness_proxy": {
            "unchanged_volume_cm3": nbti_volume,
            "old_nbti_proxy_mass_g": nbti_volume * 6.5,
            "new_aluminium_mass_g": nbti_volume * 2.699,
            "delta_g": nbti_volume * (2.699 - 6.5),
            "still_to_4k_old_mass_g": still_volume * 6.5,
            "still_to_4k_new_mass_g": still_volume * 2.699,
        },
        "net_candidate_minus_sg3a_g": bi_volume * 9.747 - old_flat_bi + nbti_volume * (2.699 - 6.5),
    }


def main() -> int:
    parent = verify_parent()
    built = expected()
    for key, data in built.items():
        write_once(OUTPUT[key], data)
    geo = OUTPUT["geo"].read_text(); det = OUTPUT["det"].read_text()
    if reverse_geo(geo) != SOURCE["geo"].read_text():
        raise BuildError("reverse geo did not reconstruct pinned SG3A")
    if reverse_det(det) != SOURCE["det"].read_text():
        raise BuildError("reverse det did not reconstruct pinned SG3A")
    mass = masses()
    json_once(MASS, mass)
    payload = {
        "status": "PASS__SG3B_DETERMINISTIC_GEOMETRY_BUILD",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "transport_launched": False,
        "parent": parent,
        "outputs": {key: record(path) for key, path in OUTPUT.items()},
        "physical_changes": [
            "flat passive Bi plate -> x-axis upper-half Bi cylindrical liner split around L0 ring",
            "five NbTiCableProxy volumes -> same-shape Aluminium proxy volumes",
        ],
        "unchanged_contract": "all other SG3A geometry, response, passive/veto roles, and source policy",
        "mass": mass,
    }
    json_once(AUDIT, payload)
    print(json.dumps({"status": payload["status"], "mass": mass}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

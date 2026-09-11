#!/usr/bin/env python3
"""Render the multiband lens+support MASS PROXY (.geo fragment) to WRL + PNG.

Reuses the project's validated MEGAlib-.geo tessellator
(add_mass/.../tools/render_nearfield_mass_proxy.py) so the multiband support
proxy is drawn with exactly the same BRIK/PCON facetting, .Copy handling and
material colouring as the OF1 optics near-field figure. This renders the
support structure (G10 carrier + Al mount + 4 Al brackets) plus the Ge
equal-volume mass-proxy annulus. It is NOT the six-ring optical tile geometry
(that is the Geant4 scene wrl in ../viz_scene_*/laue_multiring_scene.wrl).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RENDERER = Path(
    "/home/ubuntu/TES_511_Balloon/add_mass/TES_511_Balloon_nearfield_mass_proxy_v2"
    "/tools/render_nearfield_mass_proxy.py"
)

spec = importlib.util.spec_from_file_location("render_nearfield_mass_proxy", RENDERER)
R = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = R  # dataclass field-type resolution needs the module registered
spec.loader.exec_module(R)  # type: ignore[union-attr]

SCENE = {
    "setup": HERE / "multiband_support.geo.setup",
    "prefixes": None,
    "system": "optics",
    "scope": "full",
    "wrl": HERE / "multiband_lens_support_mass_proxy.wrl",
    "png": HERE / "multiband_lens_support_mass_proxy.png",
    "title": "f10m multiband lens + support mass proxy (Ge equal-volume annulus + G10/Al support)",
    "viewpoint": 'Viewpoint { position 55 -78 55 orientation 0.74 0.21 0.64 1.04 description "multiband support mass proxy" }',
    "note": "Mass proxy: Ge annulus preserves the exact 61.58 cm3 of tiled Ge; support scaled from project OF1 model. Not the optical tile geometry.",
}


def main() -> int:
    meshes = R.build_meshes(SCENE)
    if not meshes:
        raise SystemExit("no renderable meshes — check the setup/fragment Includes")
    R.write_wrl("multiband_support", SCENE, meshes)
    R.write_png("multiband_support", SCENE, meshes)
    print(f"rendered {len(meshes)} volumes")
    for m in meshes:
        print(f"  {m.name:40s} {m.material:12s} faces={len(m.faces)}")
    print(f"WRL {SCENE['wrl']}")
    print(f"PNG {SCENE['png']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

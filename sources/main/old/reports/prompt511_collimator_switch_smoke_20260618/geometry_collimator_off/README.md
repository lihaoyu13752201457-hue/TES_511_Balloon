# DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy

This directory contains a MEGAlib/Cosima proxy scaffold generated from the v3p5 center-finger bounds package.

Generated files:
- `DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo`
- `DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det`
- `DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- `Materials_DEMO2_DR_v3p5.geo`
- `geometry_proxy_validation.json`
- `overlap_check.source` / `cosima_overlap.log`

Important limitation: this is not final CAD. x-axis windows/substrates/W sleeve/supports are square BRIK-panel proxies, and side holes in z-axis annuli are rectangular azimuth/z cutouts.

Detector-core fidelity: the TES stack is emitted as 6 MDCalorimeter layers with 376 Ta pixel copies per layer, rotated for the side-entry beam axis.

Pointing policy: generated detector volumes are children of an invisible `InstrumentFrame` rotated by `0 45 0` degrees. The local side-window look axis `-x` therefore points 45 degrees above the global horizon in the zenith-frame source coordinates.

Checks:
- source design validation: `DESIGN_PASS`
- source components: `95`
- generated MEGAlib volumes: `2428`
- TES pixel copies: `2256`
- rotated geometry bounding radius: `49.5718 cm`
- setup/far-field radius: `60 cm`
- side-window sky elevation: `45 deg`
- Cosima overlap status: `PASS`

Use this scaffold for MEGAlib syntax/load and simulation-level closure. For CAD-level transport, replace remaining BRIK x-axis proxies with rotated PCON/TUBE or the project's Boolean CSG implementation.

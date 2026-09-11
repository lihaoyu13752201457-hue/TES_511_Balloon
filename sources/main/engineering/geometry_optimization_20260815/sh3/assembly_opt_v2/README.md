# SH3 optimized chimney + pure-DR assembly v2

> **Superseded interface concept:** the user rejected the large-frustum plus
> small-nozzle load path as mechanically non-credible. Preserve this package
> for provenance, but do not promote its interface. The boolean-welded saddle
> replacement is `../assembly_opt_v3/`.

## Status

This non-overwriting revision implements the requested mechanical/optical
cleanup on top of the retained SH3 chimney and pure-DR base. It is geometry
authority only.

- Build: `PASS__SH3_ASSEMBLY_OPT_V2_BUILT`
- Static validation: `PASS__SH3_ASSEMBLY_OPT_V2_STATIC`
- Full Cosima/Geant4 construction and overlap validation:
  `PASS__SH3_ASSEMBLY_OPT_V2_OVERLAP_NO_TRANSPORT`
- Native Geant4 WRL export:
  `PASS__SH3_ASSEMBLY_OPT_V2_NATIVE_WRL_NO_TRANSPORT`

The overlap gate used 10,000 samples per placement at 0.0001 cm tolerance.
The audit contains no overlap/error lines, generated particles, transport
markers, or event payload. No source, activation, response, Poisson time axis,
veto, background estimate, or sensitivity calculation was run.

## Requested changes

### Raised side interface

The common chimney/cold-finger axis and all five DR penetrations move from
`z'=-5.20 cm` to `z'=-2.80 cm`. The chimney outer radius remains 11.05 cm, so
its lowest point is `z'=-13.85 cm`, 0.25 cm above the retained 300 K vacuum
jacket bottom at `z'=-14.10 cm`. The chimney no longer projects below the DR
base.

### Aluminium curved-wall transition

A 3 mm aluminium annular frustum joins the chimney mechanical shell to a short
aluminium nozzle through the curved 300 K vacuum jacket:

- frustum axial extent: `x'=-24.65` to `-20.95 cm`;
- large-end radii: 10.75/11.05 cm;
- small-end/nozzle radii: 0.75/1.05 cm;
- nozzle axial extent: `x'=-20.95` to `-20.10 cm`.

Only the outer vacuum-jacket interface is enlarged to diameter 2.10 cm for the
nozzle. The MXC, Still, 4 K, and 60 K cold-stage penetrations stay at diameter
1.50 cm. This avoids treating a flat chimney end touching a curved shell along
a line as a complete mechanical interface.

### Unobstructed optical path

The retained `NF2_OuterSupport_Al_TopMountAnnulus` is now a subtraction solid
with a diameter-6.00 cm aperture centered on the chimney/TES optical axis. The
aperture exceeds the retained radius-2.70 cm signal opening.

### Simple W square-frame collimator

The old circular front-BGO recess is replaced by a 6.00 cm square recess. It
contains four solid W bars, not the previous grid/multihole concept:

- outer square: 6.00 x 6.00 cm;
- clear inner square: 5.40 x 5.40 cm;
- axial W depth: 2.00 cm;
- nominal W mass proxy: 0.264 kg.

The clear square contains the retained diameter-5.40 cm optical circle without
geometrically clipping it. Exact tolerances and a deliberate beam-clearance
margin remain mechanical-design questions; equality here is the nominal
geometry boundary.

### Bent cold finger

The copper route follows the raised ports, doglegs by `+1.10 cm` in local
`y'` inside the MXC region, and rises to the retained MXC plate contact pad.
The pad upper face remains coplanar with the MXC plate underside at
`z'=-0.20 cm`. The route is a 35.62 g copper density-volume proxy, not a
thermal or vibration closure.

## Retained boundary

The full `InstrumentFrame.Rotation 0 45 0`, six TES layers, three active BGO
volumes, cold plates, thermal shells, process hardware, and support cage are
retained from the pinned v1 inputs except for the exact changes above. The
standalone chimney, pure-DR base, and assembly v1 files remain unchanged.

## Files

- `geometry/SH3_Assembly_OptV2.geo`: complete optimized assembly.
- `geometry/SH3_Assembly_OptV2.geo.setup`: assembly setup.
- `geometry/SH3_Assembly_OptV2.det`: six TES and three BGO declarations.
- `code/build_sh3_assembly_opt_v2.py`: deterministic builder/static gate.
- `code/run_sh3_assembly_opt_v2_overlap.py`: zero-transport overlap harness.
- `code/export_sh3_assembly_opt_v2_wrl.py`: native WRL exporter.
- `data/assembly_opt_v2_manifest.json`: dimensions, mass proxies, source pins,
  and output hashes.
- `audit/assembly_opt_v2_static_validation.json`: analytic/static receipt.
- `audit/assembly_opt_v2_overlap_validation.json`: Geant4 overlap receipt.
- `audit/assembly_opt_v2_wrl_export_validation.json`: native WRL receipt.
- `figures/sh3_assembly_opt_v2_local_xz_section.svg`: dimensioned section.
- `figures/sh3_assembly_opt_v2_interface_optics_detail.svg`: enlarged
  curved-wall/nozzle section plus optical-axis front view.
- `figures/SH3_Chimney_DR_Assembly_OptV2.wrl`: native constructed view.

## Still not claimed

The aluminium transition and cold finger have not been thermally sized or
structurally/manufacturing qualified. The W frame has not been optimized with
the Laue ray bundle, and its background benefit has not been transported. This
revision therefore cannot support a background or minimum-flux claim.

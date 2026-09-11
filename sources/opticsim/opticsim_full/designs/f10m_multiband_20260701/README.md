# f10m Ge(111) Multiband Laue Design (2026-07-01)

Multi-ring extension of the single-ring `balloon511_f10m_ge111_511line` (A1)
optic. A1 focuses **only 511 keV** at ~20 cm² effective area. This design tiles
the **450–550 keV** band with **six coplanar Ge(111) rings** so the lens has a
spectral response across the band, at the cost of per-energy effective area.

> **Naming.** You asked for this as `f10m_a2`. The name `a2` is already taken by
> the existing *focal-spot-priority* single-ring variant (30×15 mm tiles,
> ~17 cm², in `optics_aeff_authority_f10m_a1.json`). To avoid overwriting real
> authority, this package is named **`f10m_multiband`**. Say the word and I will
> rename it to `a2`.

## What this design is

| item | value |
|---|---|
| Model | `balloon511_f10m_ge111_multiband` |
| Rings | 6, coplanar (z_offset = 0), all Ge(111), all 30″ mosaic |
| Focal length | 10 m |
| Design energies | 451, 471, 491, **511**, 531, 551 keV (511 kept exact) |
| Ring radii | 84.160, 80.586, 77.304, **74.278**, 71.480, 68.886 mm |
| Tiles | 2.2 mm square, 10.218801 mm thick (thickness locked to XOP validity) |
| Band coverage (FWHM) | ≈ 443–563 keV |
| Ge mass | 0.328 kg |
| Support mass | 0.346 kg |
| **Lens total mass** | **0.674 kg** |
| Per-energy A_eff (design est.) | **≈ 2.3–2.8 cm² per ring** |

## The trade you are buying (read this)

The six rings pack into roughly the **same 68–85 mm radial band** that A1's one
18-mm-deep ring occupied. Because that band is now split six ways, each ring is
only ~2.2 mm deep radially, so **per-energy effective area falls from ~20 cm²
(A1 at 511) to ~2.3–2.8 cm² per ring.** This is the physical price of band
coverage in a single-layer coplanar lens; it is not recoverable without either
a larger-diameter lens (more/deeper rings) or accepting energy gaps. Axial
stacking (rings at different z) was already rejected in the project because
upstream rings shadow the downstream anchor ring.

If the science target is the **unresolved 511 keV line only**, A1 (20 cm² at
511) is the better optic. This multiband design is for the case where spectral
response across 450–550 keV (e.g. Doppler-shifted lines or neighbouring
nucleosynthesis lines) is worth ~7× less peak area.

## Support structure

Scaled from the project's own optics near-field mass proxy
(`add_mass/TES_511_Balloon_nearfield_mass_proxy_v2/optics/OpticsNearfield_GeAndSupport_v2.geo`,
OF1 budget). Emitted in `OpticsMultiband_GeAndSupport_f10m.geo`:

| part | material | geometry | mass |
|---|---|---|---|
| Ge active mass | GeProxy | equal-volume annulus, r = 67.8–85.3 mm | 0.328 kg |
| Tile carrier | G10 | annulus r = 55–88 mm, 1 mm thick, x = +7 mm | 0.027 kg |
| Outer mount | Aluminium | annulus r = 88–115 mm, 5 mm thick | 0.232 kg |
| Brackets (×4) | Aluminium | 10×20×40 mm, at ±150 mm y,z | 0.086 kg |

The `.geo` is an **includable fragment** (mother = `InstrumentFrame`; materials
`GeProxy`/`G10`/`Aluminium` defined by the host geometry), byte-for-byte in the
same form as the validated OF2 fragment. The Ge volume is a **mass proxy** (an
equal-volume annulus preserving the exact 61.58 cm³ of tiled Ge), not the
optical tile geometry. Its purpose is to let this lens feed the upstream-optics
background chain the same way A1's proxy does.

## Honest status of the numbers

- The six-ring config is **transport-validated end-to-end**: a smoke run through
  the real `laue_multiring_bfull_demo` binary confirms all six rings diffract at
  their own energies with the correct efficiency trend, and the aggregate
  emergent-vs-analytic gate passes. See
  `smoke_validation_20260701_seed12345/SMOKE_VALIDATION.md`.
- **A_eff values in the summary are still DESIGN-STAGE estimates** (ring
  geometric area × the same 0.25184 reference diffracted fraction the A1 estimate
  uses). Extracting transported per-ring A_eff from `focal_crossings.csv` is the
  next step (needs `aeff_f10m_report.py` extended to group by ring/energy).
- **Only the 511 keV ring has an external XOP/CRYSTAL rocking curve.** The other
  five energies fall back to the C++ internal Ge(111) Darwin-Hamilton backend,
  which *is* energy-scaled, so it gives a reasonable first look — but each
  energy needs its own XOP/CRYSTAL curve before the numbers are
  publication-grade. Status per ring is in `..._xop_map.csv`.
- Tiles are modeled as dense small squares approximating a thin annulus; the
  same Phase-1 tile-rotation/overlap caveat as the single-ring optic applies but
  is negligible at this granularity (≈1.1° azimuthal step).

## Files

| file | what |
|---|---|
| `make_f10m_multiband_config.py` | generator; edit the knobs at top, re-run to regenerate everything |
| `ge111_balloon511_f10m_multiband_line_config.csv` | 6-ring config consumed by `laue_multiring_bfull_demo` |
| `ge111_balloon511_f10m_multiband_xop_map.csv` | per-ring rocking-curve status |
| `ge111_balloon511_f10m_multiband_design_summary.json` | all computed numbers + provenance |
| `OpticsMultiband_GeAndSupport_f10m.geo` | lens+support MEGAlib mass-proxy fragment |
| `smoke_validation_20260701_seed12345/` | real transport smoke run proving the config loads + diffracts (optics binary) |
| `mc_smoke_20260701/` | **cosima Monte-Carlo smoke** (mass-proxy annulus) proving the support-inclusive geometry loads/transports/triggers (see `MC_SMOKE.md`) |
| `mc_smoke_unified_20260701/` | **cosima MC + Geant4 overlap check on the 1245-tile unified geometry**: no overlaps (with positive control) + per-tile transport (see `MC_SMOKE_UNIFIED.md`) |
| `viz_unified_20260701/overlap_ledger.json` | analytic no-overlap ledger (all clearances positive; min 65.7 µm tangential) |
| `viz_scene_20260701/laue_multiring_scene.wrl` | Geant4 3D scene — six-ring **optical tile** geometry (no support; pure optics transport) |
| `viz_support_20260701/multiband_lens_support_mass_proxy.wrl` (+`.png`) | 3D mass proxy — **support structure + Ge annulus** (G10 carrier, Al mount, 4 brackets); no tile detail |

## 3D geometry (WRL)

**Want one file with everything?** Use
`viz_unified_20260701/multiband_unified_tiles_and_support.wrl` — it carries the
six rings of **real optical Ge tiles** *and* the **support structure** in a
single common frame (optical axis = +x, lens plane at x = 0). Regenerate with
`python3 viz_unified_20260701/build_unified_geo_and_render.py` (also writes a 2D
`.png` and the combined `MultibandUnified_TilesAndSupport_f10m.geo`). Every tile
of every ring is a faithful Ge box on its ring radius (1245 tiles), not a proxy.

The two single-purpose WRLs below still exist if you want just one aspect (the
unified file supersedes them for a combined view):

- `viz_scene_20260701/laue_multiring_scene.wrl` — emitted by the Geant4
  `laue_multiring_bfull_demo` binary. Shows all **six rings of real optical
  tiles** plus a sample of diffracted tracks converging to the focus. This is
  the optics transport model, so it has **no** G10/Al support. Regenerate by
  re-running the transport with any `--out DIR` (the scene is written to
  `DIR/laue_multiring_scene.wrl`).
- `viz_support_20260701/multiband_lens_support_mass_proxy.wrl` — rendered by
  `viz_support_20260701/render_multiband_support.py`, which reuses the project's
  own `.geo` tessellator (`render_nearfield_mass_proxy.py`) on
  `OpticsMultiband_GeAndSupport_f10m.geo`. Shows the **support structure + the Ge
  equal-volume mass-proxy annulus** (G10 carrier, Al outer mount, 4 Al
  brackets). The Ge here is a smooth annulus (mass proxy), **not** the tiles.
  Regenerate with `python3 viz_support_20260701/render_multiband_support.py`
  (also writes a 2D `.png` preview).

## How to run a transport (first-look, internal fallback)

Build once, then run the six-ring config **without** `--require-rocking-curve-map`
so the five curve-less energies use the internal Darwin fallback:

```bash
cd /home/ubuntu/opticsim/opticsim_full
DIR=designs/f10m_multiband_20260701
./analysis/run_with_geant4_114.sh cmake -S . -B /tmp/opticsim_full_build_g4_11_4 \
  -DGeant4_DIR=/home/ubuntu/software/geant4-11.4.0-install/lib/cmake/Geant4 -DCMAKE_BUILD_TYPE=Release
./analysis/run_with_geant4_114.sh cmake --build /tmp/opticsim_full_build_g4_11_4 \
  --target laue_multiring_bfull_demo -j 4
./analysis/run_with_geant4_114.sh /tmp/opticsim_full_build_g4_11_4/laue_multiring_bfull_demo \
  --n 50000 --seed 12345 \
  --ring-config $DIR/ge111_balloon511_f10m_multiband_line_config.csv \
  --efficiency-table data/laue/Ge111_480_550keV_darwin_mosaic_table.csv \
  --focal-mm 10000 --source-jitter-mm 2.2 \
  --out runs/f10m_multiband/first_look
```

`focal_crossings.csv` in the output dir holds the tracked diffracted crossings;
filter `source_tag=laue_bfull_diffracted` within the Be window to get the
per-energy A_eff and focal spot, exactly as the single-ring bridge does.

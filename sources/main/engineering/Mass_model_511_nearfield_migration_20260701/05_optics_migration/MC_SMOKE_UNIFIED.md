# Unified tiled geometry — no-overlap + Monte-Carlo smoke (2026-07-01)

**Question:** can the *unified* version (1245 real Ge tiles + support in one
frame) be built with **no tile overlap** and run a Monte Carlo?

**Answer: yes, verified four ways.** The tile counts already guarantee clearance;
Geant4 confirms no overlaps; a positive control proves that confirmation is real;
and cosima transports 511 keV gammas through the tiles.

## 1. Analytic overlap ledger (`../viz_unified_20260701/overlap_ledger.json`)

`all_positive = True`. Minimum clearances anywhere in the lens:

| kind | minimum | where |
|---|---|---|
| tangential (adjacent tiles) | **65.7 µm** lower bound | ring 5 (551 keV, 188 tiles) |
| radial (between rings) | **394.7 µm** | rings 4↔5 |
| tile → G10 carrier (axial) | 1.39 mm | all |
| tile → Al mount (radial) | 2.74 mm | outer |

The tangential number is a *guaranteed lower bound*: every point of a tile lies
within ±atan(hz/(r−hy)) of its azimuth, and the angular pitch exceeds twice that
on every ring, so adjacent boxes cannot touch. All clearances ≫ the 1 µm Geant4
tolerance.

## 2. Geant4 authoritative check (this dir)

`mb_unified_mc.source` sets `CheckForOverlaps 500 0.0001`, so cosima calls
`G4PVPlacement::CheckOverlaps(500, 1µm, verbose=false)` on **every** one of the
1245 tiles + 6 support volumes at construction. `verbose=false` prints **only on
overlap**.

- Result: **zero overlap warnings** in `cosima_unified_smoke.log`, exit 0.

## 3. Positive control (`overlap_positive_control/`)

To prove the clean log is not a silent no-op, the identical
`CheckForOverlaps 500 0.0001` was run on two deliberately overlapping boxes
(BoxA at z=0, BoxB at z=1.5 cm, each ±1 cm → 0.5 cm overlap):

```
*** G4Exception : GeomVol1002
      issued by : G4PVPlacement::CheckOverlaps()
Overlap with volume already placed !
          Overlap is detected for volume BoxB
          ... overlapping by at least: 4.65666 mm
```

The mechanism fires on a real overlap → the unified geometry's clean result is
trustworthy.

## 4. Transport (this dir)

Same run transported 511 keV far-field gammas through the tiles:

| check | result |
|---|---|
| cosima exit | 0 |
| primaries generated | 13329 |
| triggered events | 300 (`mb_unified_mc.inc1.id1.sim.gz`) |
| distinct tile hit positions | **345**, spread over ring radii 6.87–8.41 cm |

Unlike the single-annulus mass-proxy smoke (all hits at one point), here hits
resolve onto individual tiles at the six ring radii — the tiled optics is real in
the MC, not a proxy.

## Reproduce

```bash
cd .../designs/f10m_multiband_20260701
python3 viz_unified_20260701/build_unified_geo_and_render.py   # geo + ledger + WRL/PNG
source mc_smoke_20260701/megalib_env.sh
cd mc_smoke_unified_20260701
cosima mb_unified_mc.source                 # overlap check + transport
cosima overlap_positive_control/pc.source   # positive control
```

## Note

This tiled geometry is now MC-valid, so it can be used directly (not only the
mass-proxy annulus). For the background/mass chain the mass-proxy annulus is
still lighter and sufficient; use the tiled geometry when you need per-tile
spatial response.

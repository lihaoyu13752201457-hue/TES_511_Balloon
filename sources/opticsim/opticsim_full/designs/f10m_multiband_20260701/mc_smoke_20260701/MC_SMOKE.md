# Multiband geometry — Monte-Carlo smoke (cosima, 2026-07-01)

**Question:** does the support-inclusive multiband geometry actually run a Monte
Carlo simulation (not just render to WRL)?

**Answer: yes.** cosima (MEGAlib's Geant4 MC) loaded the geometry, transported
511 keV gammas through it, triggered, and wrote a `.sim`.

## What was run

- Geometry: `mb_mc_smoke.setup` = project optics materials (GeProxy/G10/Al/Vacuum)
  + WorldVolume + InstrumentFrame + **`OpticsMultiband_GeAndSupport_f10m.geo`**
  (the mass-proxy lens+support). The Ge annulus is declared as a single-volume
  `Scintillator` purely to give cosima a trigger.
- Source: `mb_mc_smoke.source` — 511 keV mono gammas, `FarFieldPointSource 90 0`
  (flat-on to the x-facing ring), stop at 300 triggers, seed 12345.
- Env: `megalib_env.sh` (mirrors the project's `cosima_env()`).
- Command: `source megalib_env.sh && cosima mb_mc_smoke.source`

## Result — PASS

| check | result |
|---|---|
| cosima exit code | 0 |
| geometry load / overlap errors | none in log |
| primaries generated | 14445 |
| triggered events written | 300 |
| output | `mb_mc_smoke.inc1.id1.sim.gz` (300 `SE` events) |
| Ge hit spectrum | 511 keV photopeak + Compton continuum (physically sane) |

The geometry parses, transports, and triggers under Geant4 Monte Carlo with no
overlap or navigation errors. That is the smoke-test bar.

## Scope / caveats

- This uses the **mass-proxy** `.geo` (single equal-volume Ge annulus), which is
  the geometry intended for the background/mass MC chain — not the 1245-tile
  visualization geo. The tiled geo is for WRL viewing; for MC the mass proxy is
  the right object (no tile-overlap risk, correct total Ge mass).
- The Ge annulus is one calorimeter voxel, so every deposit is reported at one
  representative point `(0,0,7.65)` cm (= mean ring radius). That is expected for
  an unsegmented smoke detector; the real detector segmentation lives in the
  DEMO2/fix5 model, into which this fragment is meant to be dropped as an
  additive optics-mass overlay.
- Smoke only: 300 triggers, one seed, artificial detector. It proves MC-runnable,
  not any background/efficiency number.

## Reproduce

```bash
cd /home/ubuntu/opticsim/opticsim_full/designs/f10m_multiband_20260701/mc_smoke_20260701
source megalib_env.sh
cosima mb_mc_smoke.source
```

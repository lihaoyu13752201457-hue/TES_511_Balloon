# Real-Position Delayed-Source Smoke Test

## Why this exists

The production Step03 delayed activation source compresses the true isotope
production positions (`CC IP RP <VN> x y z ZA exc t`) into an **axisymmetric
(z-bin + radial-profile) `RadialProfileBeam` grid** and regenerates azimuth
uniformly (`makedecaysourcewithplot_rpip.py`, CsI source used `--z-bins 10
--r-bins 20`). That grid was adopted to keep the `.source` file small and to
avoid a feared "astronomical" sampling cost.

The known weakness — and the user's original concern — is that the radial grid
is **too coarse for thin-wall structures**. This test implements and validates
the alternative that was recommended in `Project_Memory.md` §3 ("NEXT TIME, TRY
THE BETTER METHOD"):

> resample decays **directly from the exact stored RPIP points**, weighted by
> activity, and emit each as a point source — preserving the exact 3D
> distribution, material containment, and in-wall gradient with zero smearing.

## What it does

`build_realpos_smoke_source.py`:

1. **`build`** — loads the already-extracted exact point cloud
   (`stepwise_maintenance/step03_delay_source/outputs/rpip_production_points_sample.csv`,
   50k true RPIP positions) and the day-15 activity inventory; reweights each
   point by `Activity_Bq(VN,ZA) / n_points(VN,ZA)` so the per-species draw is
   activity-proportional; draws `M` decays with replacement; writes one Cosima
   **`PointSource`** block per decay at the exact `(x,y,z)` cm, with equal flux
   `Flux = A_total / M` (importance sampling => equal weight per emitted decay).
2. **`verify`** — parses the cosima `.sim`, confirms events were produced, and
   checks that the emitted `IA INIT` decay positions match the exact input
   coordinates.

`run_smoke.sh` orchestrates build → cosima → verify.

The builder reuses the **already-parsed** point cloud on disk, so it never
re-reads the multi-GB buildup SIM files. This directly refutes the
"throughput is astronomical" worry: you emit `M` (your choice, e.g. the trigger
budget), not all ~7e5 production points.

## How to run

```bash
bash tests/realpos_delayed_smoke/run_smoke.sh [N_DECAYS] [TRIGGERS]
# default: 2000 2000
```

Outputs land in `tests/realpos_delayed_smoke/outputs/`:
`realpos_delayed_smoke.source`, the cosima `.sim.gz`,
`realpos_smoke_manifest.json`, `verify_summary.json`, `fidelity_vs_grid.csv`.

## Result (M = 2000, seed 260609)

**Feasible — yes.** Cosima natively supports `<name>.Beam PointSource <x> <y>
<z>` (near-field isotropic point, cm). It parsed 2000 exact-position decay
blocks and ran in **~2.1 s CPU**, producing **2000 events**. Emitted `IA INIT`
positions matched the exact input cloud at **99.05%** (the ~1% gap is only
3-decimal rounding of cosima's 6-sig-fig output) — i.e. **zero radial
smearing**.

**Why it matters (fidelity vs grid).** `fidelity_vs_grid.csv` compares each
volume's true radial wall extent against the grid radial bin width that the
`--r-bins 20` grid would impose. Thin passive shells are badly under-resolved:

| Volume | wall thickness | grid r-bin | bins across wall |
| --- | --- | --- | --- |
| `Passive_W_Outer_Liner` | 0.060 cm | 0.498 cm | **0.12** |
| `Passive_Cu_Inner_Liner` | 0.080 cm | 0.494 cm | **0.16** |
| `ActiveShield_Al_Backplane_Liner` | 0.108 cm | 0.709 cm | **0.15** |
| `CsI_Active_Shield_Side0x` | ~4.0 cm | 0.70 cm | ~5.7 |

For the sub-mm/mm liners the grid bin is 5–8× **wider** than the actual wall:
the grid scatters those decays across a band several mm wide and can leak them
into the adjacent vacuum gap (the non-conservative failure mode noted in
`Project_Memory.md` §3). The exact-position `PointSource` method places every
decay exactly where it was produced, so this class of error vanishes.

## Filter semantics for a production rebuild (verified 2026-06-10)

Two different "delayed-relevant" filters exist and differ by exactly 167 points
out of the 723,576 total RPIP rows; a production exact-point source must pick
one deliberately:

- **708,537** (`rpip_production_map_summary.json` "delayed-relevant") =
  `(canonical VN, ZA)` present in the **raw** positive-activity day-15
  inventory (`activation_inventory_day15.csv`).
- **708,370** (`full_weighted_rpip_table.csv` `in_fixed_inventory=1`) =
  `(VN, ZA)` present in the **ground-state-fixed** source blocks
  (`activation_decay_day15_groundstate_fixed.source`).

The 167-point difference is species the ground-state fix removed/rescaled.
Since the production delayed source is the fixed source, a production rebuild
should sample with the `in_fixed_inventory` filter **and** the fixed
activities, keeping `(VN, ZA, exc)` granularity.

## Scope / honesty notes

- This is a **smoke test**, not a production rebuild. It uses the **raw**
  day-15 inventory activities (not the ground-state-fixed activities) and a
  small `M` / trigger budget. A production version should use the
  ground-state-fixed activities and `M` = full trigger budget (e.g. 1e6), and
  may resample positions weighted by per-point `wfile` (gamma vs non-gamma
  division) within a species for full faithfulness.
- The activity-weighted-with-replacement draw reproduces each species' activity
  **in expectation**; per-run Poisson/multinomial variance scales as
  `1/sqrt(M)`, negligible at production `M`.
- It does not change any current science authority. It demonstrates that the
  recommended upgrade is implementable and quantifies the grid's thin-wall
  error.

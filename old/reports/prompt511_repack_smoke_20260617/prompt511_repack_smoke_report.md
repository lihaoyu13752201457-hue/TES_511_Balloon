# Prompt-511 Repack Smoke Report

Date: 2026-06-17

## Answer

Adding a passive high-Z shell is not sufficient as a generic statement. A
targeted W shadow liner in the side-entry prompt-511 solid angle does suppress
the dominant prompt-eplus leakage in this smoke, but the design is not closed
until the delayed activation is rebuilt with the added W mass.

The useful statement from this run is narrower:

- A CAD-clean local W liner at `r=[4.25,5.95] cm`, with the signal sector
  `phi=[160,200] deg` open, reduces the current prompt-eplus raw TES 511-keV
  line-window rate by about `4.0x`.
- This is consistent with the earlier 80-event geometric screen upper bound of
  about `4.6x`.
- The delayed replay here transports an old activation inventory through the new
  geometry. It does not include new W-liner activation and therefore cannot be
  used as a final total-background answer.

## Geometry And Validation

- Geometry copy:
  `outputs/reports/prompt511_repack_smoke_20260617/geometry_repack/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_repack_r4p25_5p95.geo.setup`
- Builder:
  `outputs/reports/prompt511_repack_smoke_20260617/build_prompt511_repack_smoke.py`
- Manifest:
  `outputs/reports/prompt511_repack_smoke_20260617/prompt511_repack_smoke_manifest.json`
- Overlap log:
  `outputs/reports/prompt511_repack_smoke_20260617/overlap_repack.log`

Overlap status: no `GeomVol1002` warnings after the local support/finger repack.
The only warning left is the expected no-trigger warning from the one-particle
overlap source.

Important mechanical caveat: the local Cu off-axis fingers are shortened into
inner stubs for this design smoke. This proves that a W shadow volume can be
reserved without overlaps, not that the final mechanical/thermal CAD is solved.

## Prompt Results

All-particle 1/10 raw-line smoke:

- Run directory:
  `outputs/reports/prompt511_repack_smoke_20260617/runs/instant_1of10_rawline`
- Generated particles: `1,190,129`
- Direct summary:
  `outputs/reports/prompt511_repack_smoke_20260617/prompt511_repack_direct_summary_allparticle_1of10.md`
- Raw TES line window: `510.58 <= TES_total_keV < 511.42`
- Result: `1` prompt event, `0.0547537 s^-1`, tagged `n`.
- Prompt-eplus count in this 1/10 run: `0`.

This all-particle 1/10 run is too thin to decide the eplus prompt question.
Therefore an eplus-only boosted smoke was run.

Eplus-only boosted smoke:

- Run directory:
  `outputs/reports/prompt511_repack_smoke_20260617/runs/instant_eplus_g10m_r4_rawline`
- Generated eplus particles: `974,908`
- Direct summary:
  `outputs/reports/prompt511_repack_smoke_20260617/prompt511_repack_direct_summary_eplus_g10m_r4.md`
- Repacked geometry eplus raw TES line-window result: `12` events,
  `0.0163368 s^-1`.

Current-geometry eplus baseline, parsed with the same raw TES line-window
definition from `runs/step02_instant_v3p5_centerfinger_fullstat_v2`:

- Generated eplus particles: `1,949,816`
- Raw TES line-window result: `97` events, `0.0658845 s^-1`.
- Suppression factor from the W-liner repack: `0.0658845 / 0.0163368 = 4.03`.
- Approximate counting-only 1-sigma fractional uncertainty on this ratio:
  `sqrt(1/97 + 1/12) = 0.306`, so the factor is roughly `4.0 +/- 1.2`.

## Delayed Results

Reduced delayed replay:

- Source:
  `outputs/reports/prompt511_repack_smoke_20260617/runs/delayed_replay_existing_inventory/activation_decay_day15_groundstate_fixed_repack_replay_reduced.source`
- SIM:
  `outputs/reports/prompt511_repack_smoke_20260617/runs/delayed_replay_existing_inventory/DelayedDecayExistingInventoryRepackReduced.inc1.id1.sim.gz`
- Original delayed source points: `50,000`
- Kept source points: `2,000`
- Flux scale applied to kept points: `25.0`
- Generated delayed triggers: `20,000`
- Observation time in SIM: `229.111057 s`
- Raw TES line-window result: `0` events.
- 95 percent zero-count upper bound for this replay transport is about
  `3 / 229.111057 = 0.0131 s^-1`.

This is only an old-inventory transport replay. It excludes activation generated
inside the new W liner, so it cannot establish that total delayed background is
acceptable.

## Interpretation

The prompt-eplus problem is not fixed by any passive shell. It is fixed only if
the shell occupies the actual side-entry leakage solid angle and leaves the
signal sector open. The MC result supports that direction: the targeted W liner
gives about `4x` prompt-eplus suppression in the raw TES 511-keV window.

That is a meaningful reduction, but it is not yet a final background solution.
The missing closure item is W activation. A proper decision needs a matched
prompt plus buildup plus delayed-source rebuild for this geometry, followed by
the normal detector-response and selection chain if it is promoted beyond smoke.

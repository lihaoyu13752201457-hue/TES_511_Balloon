# Deep Sampling Audit: Old Delayed Source Axis Collapse

Date: 2026-06-23

This follow-up narrows the previous `UNRESOLVED_COMPARABILITY` result.  The
concrete clue is in the old `new_geo_re` delayed source sampling, not in
half-life, total activity, or `TE_s`.

## Finding

Status: **PROBABLE_OLD_DELAYED_SOURCE_PLACEMENT_BUG**

The old `new_geo_re` production delayed source compresses RPIP points into
`RadialProfileBeam` z/r source blocks, but the emitted old SIM shows I-128
decay starts collapsed onto the beam axis (`x=0`, `y=0`) rather than located in
the CsI active-shield volumes.  This provides a concrete mechanism for the old
delayed rate being much too strongly coupled to the TES detector.

Current fix5 exact-position sampling does not show this behavior: I-128 starts
at real CsI segment coordinates and almost never hits TES.

## Source-Builder Evidence

Old source builder:

- Builds z/r profiles from true RPIP points.
- Then emits each source block with `x_cm = 0.0`, `y_cm = 0.0`, and only a
  z-bin center.

Evidence:

- `/home/ubuntu/codex_tes_511_sim/new_geo_re/stepwise_maintenance/step02_raw_background_simulation/source_snapshots/makedecaysourcewithplot_rpip.py:945-960`
  builds the axisymmetric profiles.
- Same file `:1002-1020` distributes activity by z-bin and sets
  `"x_cm": 0.0, "y_cm": 0.0`.
- Old fixed source example:
  `/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_delay_fix_equiv2602_aligned/activation_decay_day15_groundstate_fixed.source:5986-5988`
  emits `S_CsI_Active_Shield_Bottom03_53128_z000.Beam RadialProfileBeam
  0.000000 0.000000 -21.549924 ...`.

Current fix5 exact-position source:

- Samples weighted RPIP points directly.
- Emits one equal-flux `PointSource` at each chosen true `(x,y,z)` coordinate.

Evidence:

- `code/tools/build_fix5_1of10_exactpos_delayed_source.py:413-438` computes
  per-point weights from fixed activity and RPIP support.
- Same file `:482-487` writes
  `Beam PointSource {point['x_cm']} {point['y_cm']} {point['z_cm']}`.
- Current source example:
  `runs/step02_delay_fix_fix5_fullstat_v2/activation_decay_day15_groundstate_fixed_exactpos_m50000_s260613.source:50018-50020`
  emits `RP_0000000.Beam PointSource -14.298900 8.591055 -12.831600`.

## SIM-Level Confirmation

I sampled the first `20000` delayed SIM events from each delayed transport file
and parsed `IA INIT` source coordinates for I-128 (`ZA=53128`).

Old `new_geo_re` delayed SIM:

- I-128 events in sample: `16856`
- I-128 mean start radius: `0.0 cm`
- I-128 fraction with `r < 0.001 cm`: `1.0`
- I-128 events with any TES/`TP_` hit: `2970 / 16856 = 0.17619838633127669`
- I-128 events with any CsI hit: `5586 / 16856 = 0.3313953488372093`
- I-128 events with any passive/W hit: `6782 / 16856 = 0.40234931181775035`
- Top first-hit volume: `Passive_Bottom_W_Shield` (`6289 / 16856`)

Current fix5 delayed SIM:

- I-128 events in sample: `15322`
- I-128 mean start radius: `14.78431518348516 cm`
- I-128 fraction with `r < 0.001 cm`: `0.0`
- I-128 events with any TES/`TP_` hit: `6 / 15322 = 0.0003915937867119175`
- I-128 events with any CsI hit: `15322 / 15322 = 1.0`
- I-128 events with any passive/W hit: `82 / 15322 = 0.00535178175172954`
- Top first-hit volumes are the actual CsI segment/quadrant names.

The old/current I-128 TES-hit fraction ratio in this sample is
`0.17619838633127669 / 0.0003915937867119175 = 449.95x`.

This is the missing clue: old delayed transport is not just higher activity.
Its dominant I-128 activity is starting on the central axis and frequently
interacting in passive/ADR/substrate/TES-adjacent volumes, while current exact
position I-128 starts in the CsI volumes and almost never reaches TES.

## Rate Decomposition

The activity ratios are too small to explain the old selected-rate dominance:

- total fixed delayed activity ratio old/current:
  `624.2710918319826 / 85.44920253876245 = 7.30575679215723`
- I-128 activity ratio old/current:
  `533.27573379 / 65.53339484535951 = 8.137465410549563`

The coupling ratios are much larger:

- delayed catalog rate per Bq old/current:
  `(280.59901174421475 / 624.2710918319826) /
  ((828162 / 11649.564832) / 85.44920253876245) = 0.5402755699344189`
- delayed TES-event fraction old/current:
  `(121458 / 444640) / (2217 / 828162) = 102.03923689949899`
- broad 480-550 raw selected per catalog event old/current:
  `0.012985786254048693 / 0.00010384441691359904 =
  125.05040367122642`
- broad 480-550 final cps/Bq old/current:
  `(2.31224086683797 / 624.2710918319826) /
  (0.003176084303026095 / 85.44920253876245) =
  99.64966448119739`
- W2 final cps/Bq old/current:
  `(0.15211317269106375 / 624.2710918319826) /
  (0.0025752034889400762 / 85.44920253876245) =
  8.085186871482254`

So the old delayed dominance is not created by more decays per Bq; current has
the higher delayed catalog rate per Bq.  The large difference appears after
transport/source placement, where old I-128 couples into TES at a vastly higher
rate.

## Half-Life And Activation Handling

This finding does not require a half-life bug:

- Current and old both use NUBASE ground-state correction.
- The I-128 activity ratio is only `8.14x`, close to the total activity ratio.
- `TE_s` mismatches are percent-level, not order-of-magnitude.

Half-life handling still matters for auditability, but it is not the main
explanation for the `cps/Bq` residual.

## Corrected Interpretation

The previous supervisor result should be narrowed again:

1. Current fix5 delayed processing is not shown to be suppressed by
   `O(10-100)`.
2. Old `new_geo_re` delayed processing now has a concrete probable inflation
   mechanism: `RadialProfileBeam` source blocks written at `x=y=0` collapse
   dominant CsI/I-128 activity onto the central axis in the emitted SIM.
3. The old delayed benchmark (`0.151456825339` or inspected
   `0.15211317269106375 cps`) is not a valid physical delayed comparison for
   fix5 until rebuilt with exact-position delayed sampling.

## Required Discriminator

The decisive next check is now sharper than "align sampling":

1. Rebuild old `new_geo_re` delayed source from old fixed inventory/RPIP using
   exact-position `PointSource` sampling.
2. Run delayed transport and current hard W2 Step05 selection.
3. Verify in the emitted SIM that I-128 `IA INIT` positions no longer have
   `r=0` collapse and match the RPIP cloud.
4. Compare `selected_cps/Bq` to current fix5.

If old exact-position replay drops toward current `cps/Bq`, the old delayed
dominance was a source-placement artifact, not a geometry/inventory truth.

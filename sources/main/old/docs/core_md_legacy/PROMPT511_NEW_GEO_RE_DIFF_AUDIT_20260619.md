# Prompt-511 new_geo_re vs current v3p5 Audit, 2026-06-19

Purpose: explain why old `new_geo_re` has much lower prompt-511 hard-window
rate than the current v3p5 side-entry chain, without confusing window leakage,
source normalization, spatial ROI diagnostics, or material-shield topology.

Current rate authority remains `fullstat_v2_exactpos_m50000_s260613`. This
note is a design/root-cause audit, not a replacement rate authority.

## Bottom Line

The prompt difference is primarily a **side-wall/side-port leakage topology**
problem, not a nominal Be/Al optical-window leakage problem.

Current v3p5 hard-window prompt-eplus:

- total prompt-eplus: `0.0543377485018 cps`, `80` events.
- strict nominal side-window leak: `1/80`, `0.000679221856 cps`.
- broad any-window/foil proxy: `3/80`, `0.00203766557 cps`.
- non-window leak: `77/80`, `0.052300082933 cps`.
- side-port side-wall component: `61/80`, `0.041432533233 cps`.

Old `new_geo_re` hard-window prompt-eplus:

- total prompt-eplus: `0.0244744226824 cps`, `106` events.
- old total prompt/delayed: `0.0323247092031 / 0.151456825339 cps`.
- Therefore old `new_geo_re`, even in the narrow line window, remains
  delayed-dominated: delayed/prompt is `4.68548`.

If only the current v3p5 side-port side-wall component were removed, current
prompt-eplus would be about `0.01291 cps`, below old `0.02447 cps`, without any
ROI cut. That is the clean target for a hardware fix.

Primary evidence:

- `outputs/reports/prompt511_entry_audit_20260617/prompt511_entry_audit.md`
- `outputs/reports/prompt511_entry_audit_20260617/prompt511_old_vs_v3p5_decomposition_summary.json`
- `outputs/reports/prompt511_entry_audit_20260617/prompt511_raytrace_ledger.md`
- `outputs/reports/prompt511_entry_audit_20260617/prompt511_material_ledger.md`
- `outputs/reports/prompt511_repack_smoke_20260617/prompt511_repack_smoke_report.md`
- `outputs/reports/prompt511_repack_smoke_20260617/prompt511_repack_l1_proxy_summary.md`
- `outputs/reports/prompt511_repack_smoke_20260617/prompt511_active_collar_bgo_l1_proxy_summary.md`
- `outputs/reports/prompt511_repack_smoke_20260617/prompt511_repack_seed_independence_audit.md`

## Source Normalization: Not A Flux-Card Bug

The eplus flux card is not the source of a hidden error:

- current and old eplus flux are identical:
  `0.116980545722762 cm^-2 s^-1`.
- current and old source cards both specify
  `Background_eplus_fullsphere20.Events 1000000`.
- catalog base eplus event denominator is identical: `243727`.
- current setup sphere is `60 cm`; old setup sphere is `35 cm`.
- surface-area ratio: `(60/35)^2 = 2.9387755102`.
- per-event rate ratio: `0.000679221856273 / 0.000230890780022 = 2.9417452538`.

The current/old prompt-eplus cps ratio is:

`2.22019 = (80/106 selected-event ratio) * (about 2.94 source-area weight ratio)`.

So the current absolute cps increase is mostly the larger far-field/enclosing
surface weight, while the selected-event efficiency per generated eplus is
lower (`80/106 = 0.754717`). This should be worded as source-surface/effective
area scaling, not as a bad flux card.

## Window Leakage vs Wall Leakage

The decisive split is:

| quantity | old new_geo_re | current v3p5 |
|---|---:|---:|
| total prompt-eplus | `0.0244744 cps` | `0.0543377 cps` |
| window-like leak | `~0.00231 cps` | strict `0.00068 cps`; broad foil `0.00204 cps` |
| wall/non-window leak | `~0.02217 cps` | `0.05230 cps` |

Thus the current side window itself is not worse than the old top/axial window.
The excess is the current wall/non-window component, especially the side-port
side-wall term `0.04143 cps`.

Do not say "the prompt excess is Be-window leakage." Under the strict current
definition, the Be+outer-Al side window contributes only `1/80`.

## Why Moving Top Entry To Side Is Not A Neutral Move

Old `new_geo_re` had no side optical port at the current beam location. The old
side barrel remained a continuous material column. Along the current side line
`y=0, z=-5.2 cm`, old geometry has:

`CsI:4.0 cm; Copper:1.63 cm; LowCarbonSteel:1.17 cm; Aluminium:1.10 cm; StainlessSteel:0.25 cm; G10:0.16 cm; W:0.06 cm; Kapton:0.05 cm`.

Current v3p5 side-window-only line has:

`Be:0.015 cm; Aluminium:0.013 cm`.

The ray-trace fixed-line attenuation screen gives:

| line | areal density | 511 transmission |
|---|---:|---:|
| current side-axis centerline | `3.62 g/cm2` | `0.7379` |
| old same side-axis centerline | `80.71 g/cm2` | `0.00109` |
| current side-window-only | `0.06 g/cm2` | `0.99468` |
| old corresponding outer-to-inner side line | `48.34 g/cm2` | `0.0164` |

The current builder also cuts side holes through a chain of shells/liners/CsI
segments. The `add_annulus_with_optional_side_hole()` logic removes a `z` band
and an azimuth wedge centered on the side port. For CsI side segments 03/04 the
port is declared at `phi=180 deg`, `z=-5.2 cm`, `r=2.6 cm`; the generated
geometry splits the CsI into below/above/side-port bands instead of leaving a
continuous old-style side wall.

Mental picture: old geometry is a thick continuous side wall; current geometry
is a hole and edge structure cut through that wall. The selected prompt 511s
mostly come from the side-wall/edge neighborhood, not through the center of the
designed optical window.

## Particle/Track Evidence

Current selected prompt-eplus survivors:

- `32/32` sampled selected events stop in TES.
- median non-Ta material chord from annihilation to TES: `3.8646 cm`.
- non-window subset median passive chord: `4.4120 cm`.
- first/last primary volumes are dominated by side-port/side-wall or outer
  shell categories.
- examples include:
  - `rep01_part01:84231`: born in
    `Vacuum_Jacket_Al_266mmClass_side_port_side_wall_above_side_port`,
    then reaches TES through about `2.18 cm` passive chord.
  - `rep01_part01:51708`: from
    `Passive_W_Liner_detector_bay_above_side_port -> Passive_Cu_Liner...`,
    about `0.971 cm` passive chord.

Side/shield no-TES samples show what blocks photons when a real material column
is present:

- old no-TES side/shield sample: `0/100` TES, stop materials
  `CsI 67`, `Aluminium 22`, `W 4`, `Copper 2`, other `5`; median shield
  deposited energy `523 keV`.
- current no-TES side/shield sample: `0/100` TES, stop materials
  `CsI 49`, `Aluminium 37`, `W 6`, other `8`; median shield deposited energy
  `517 keV`.

Representative old blocked events stop in CsI side panels, e.g. old
`rep01_part01:12` stops in `CsI_Active_Shield_Side00` with `CsI:10.7 cm` and
about a full-energy 511-keV deposit. This is the old-side-shield behavior the
current side-port cut has partially removed in the high-leakage region.

## What Does Not Solve It

1. **ROI / `spot_r90`**

   The spatial ROI scan is diagnostic only and is explicitly withdrawn as the
   prompt-suppression strategy. It shows prompt is more diffuse than signal,
   but it does not explain why old hard-window prompt was lower, and it is not
   a hardware solution.

2. **A simple aperture/window-plane baffle**

   Analytic screen: only `34/80` current prompt-eplus survivors cross the
   window plane. A W baffle around the nominal window plane leaves
   `~0.038 cps`, only `1.4x` suppression. The leak is surface/side-wall-like,
   not just a hole-center beam.

3. **Turning off the existing W side sleeve**

   Collimator-off smoke is statistically consistent with current raw eplus
   (`0.05436` vs `0.06588 cps`, ratio `0.825 +/- 0.274`). The existing sleeve is
   not the decisive suppressor.

4. **Generic global passive mass**

   The evidence points to a local side-port side-wall solid angle. Global added
   Cu/CsI/W can raise delayed activation and may miss the actual leak geometry.

## Mature Fix Direction

Target the local side-port side-wall component, not the nominal Be window and
not post-hoc ROI.

The hardware topology to restore is:

- keep only the true signal sector open;
- place shielding between TES (`r ~ 3 cm`) and side-wall emitters
  (`r ~ 13-19 cm`);
- restore a continuous material/veto column in the non-signal side-port solid
  angle;
- account for delayed activation and add-back before promotion.

Viable design families:

1. **Inner shadow liner / graded-Z collar**

   A compact W/Ta high-Z liner between TES and side-wall emitters, with the
   signal sector open, is the most compact passive test. It is useful as an
   eplus shadow, but the neutron follow-up below shows it is not a standalone
   mature solution. Existing smoke:

   - W liner at `r=[4.25,5.95] cm`;
   - z segments `[-8.75,-0.65]` and `[0.65,4.65] cm`;
   - signal sector `phi=[160,200] deg` open;
   - raw prompt-eplus line-window suppression about `4.0 +/- 1.2`.

   A follow-up prompt-only L1-like proxy, using the official current Step05
   event catalog for the baseline and reparsing the W-liner prompt SIMs, gives:

   - current baseline: raw `97` events, `0.0658845 cps`; active-veto pass
     `85` events, `0.0577339 cps`; side-Compton/FoV pass `80` events,
     `0.0543377 cps`.
   - seed-correct W-liner repack: raw `13` events, `0.0176495 cps`;
     active-veto pass `11` events, `0.0149342 cps`; side-Compton/FoV pass
     `10` events, `0.0135766 cps`.
   - current/repack suppression: raw `3.73 +/- 1.10`, active-veto pass
     `3.87 +/- 1.24`, side-Compton/FoV pass `4.00 +/- 1.34`.

   This matters because the remaining eplus repack events are not removed by
   the side-Compton/FoV proxy; the eplus suppression survives Step05-like
   selection but comes from the geometry/shadowing itself, not from an ROI or
   Compton-veto trick. Evidence:
   `outputs/reports/prompt511_repack_smoke_20260617/prompt511_repack_l1_proxy_summary.md`.

   The added W volume is about `585.73 cm3`, or `11.30 kg` at
   `19.3 g/cm3`.

   Seed-correct neutron follow-up: the runner now passes `-s <seed>` to
   `cosima`. A kept-source eplus check showed that changing the source-card
   `Seed` field alone produced identical SIM hashes; the companion seed audit
   now shows the legacy eplus/n repacks were not independent, while the
   CLI-seed eplus/n repacks are independent (`4/4` and `16/16` unique prefix
   hashes, and `4/4` and `16/16` unique selected-event signatures).

   Under the same Step05-like proxy, the current n contribution is `6` final
   events, `0.00407166 cps`; the seed-correct W-liner n row gives `59` final
   events, `0.0200251 cps`. The corresponding
   eplus+n+current-carried-muplus prompt projection is `0.034275 cps`, above
   old `new_geo_re` total prompt `0.0323247 cps` by `6.03%`.

   Interpretation: W can be part of a graded local shadow, but not as an
   uninstrumented standalone shell. It must be paired with restored active
   shield/veto material or a geometry correction that keeps neutron-induced
   line-window events correlated with active-shield energy.

2. **Restored CsI active side-wall continuity; BGO only as a surrogate smoke**

   The physical route is CsI/topology, not BGO. Old `new_geo_re` was low
   because the side region corresponding to the current high-leakage side-port
   solid angle was a continuous CsI/passive side wall. The direct fix is to
   restore that CsI active side-wall continuity, or shrink the current side-port
   CSG cut so non-signal side solid angle again sees an old-like active/passive
   material column. It must be placed between side-wall emitters and TES. A
   shell outside the emitting Al wall will not block 511 photons born inside
   that wall.

   BGO is discussed below only because a same-envelope active-veto surrogate
   was fast to test and has clear active-veto naming/threshold behavior in the
   existing Step05 proxy. It is not the mainline geometry route and should not
   be presented as replacing the CsI side shield. BGO_sample is also not proof
   of this fix because it keeps the same current side-port topology and is only
   a material/threshold control.

   The BGO surrogate smoke starts from the W-liner repack geometry and replaces
   the four local shadow-liner volumes with
   `BGO_Active_Shield_Prompt511_Collar_*` active-veto volumes at the same
   `r=[4.25,5.95] cm`, `z=[-8.75,-0.65]` and `[0.65,4.65] cm`, with the
   signal sector `phi=[160,200] deg` still open. In the generated `.geo`, the
   active volumes are `BGO_Active_Shield_Prompt511_Collar_z1_a/b` and
   `BGO_Active_Shield_Prompt511_Collar_z2_a/b`, with azimuth blocks
   `0.025--159.975 deg` and `200.025--359.975 deg`. Thus the open sector is the
   approximately `40 deg` side-entry signal azimuth around `phi=180 deg`, not a
   post-hoc ROI cut. The BGO volume is `585.728 cm3`, or `4.159 kg` at
   `7.1 g/cm3`; the radial areal density is `12.07 g/cm2` for the `1.70 cm`
   collar thickness. The Cosima overlap check
   exits cleanly; the only warning is the expected no-trigger criterion warning
   in the one-event overlap source. Step05 active-veto matching recognizes the
   new volumes because the volume names contain `BGO`/`ACTIVE_SHIELD`.

   Seed-correct prompt-only runs:

   - eplus active-collar run: `4/4` jobs passed, `974,908` generated particles,
     CPU `693.547 s`.
   - n active-collar run: `16/16` jobs passed, `15,409,056` generated
     particles, CPU `13745.916 s`.
   - muplus active-collar run: `80/80` jobs passed, `928,400` generated
     particles, CPU `2727.026 s`.
   - all-particle active-collar gross smoke:
     `32/32` jobs passed, `17,605,108` generated particles,
     CPU `11888.687 s`.
   - L1 proxy evidence:
     `outputs/reports/prompt511_repack_smoke_20260617/prompt511_active_collar_bgo_l1_proxy_summary.md`.
   - all-particle gross-check evidence:
     `outputs/reports/prompt511_repack_smoke_20260617/prompt511_active_collar_bgo_allparticle_smoke_l1_proxy_summary.md`.
   - focused-signal smoke evidence:
     `outputs/reports/prompt511_repack_smoke_20260617/prompt511_active_collar_bgo_focus_smoke_summary.md`.
   - delayed activation smoke evidence:
     `outputs/reports/prompt511_repack_smoke_20260617/prompt511_active_collar_bgo_delayed_smoke_summary.md`.

   Under the same Step05-like proxy:

   - eplus is reduced from current `80` final events, `0.0543377 cps`, to
     active-collar `12` final events, `0.0162824 cps`
     (`3.34 +/- 1.03` current/active-collar suppression).
   - n raw line-window events are lower than current (`0.0583701 cps` versus
     `0.0780401 cps`), but surviving active-veto-pass n is still higher than
     current: active-collar `28` final events, `0.00950210 cps`, versus current
     `6` events, `0.00407166 cps`. This is nevertheless much better than the
     W-only n follow-up (`59` events, `0.0200251 cps`).
   - muplus current has `1` final event, `0.000673320 cps`; the active-collar
     muplus follow-up has `65` raw line-window events, `1` active-veto-pass
     event, and `0` final side-Compton/FoV events.
   - Replacing current eplus, n, and muplus with the active-collar rows gives a
     prompt projection of `0.0257845 cps`, or `0.797671x` old `new_geo_re`
     prompt total `0.0323247 cps`. No nonzero current prompt tag is carried in
     this projection.
   - The low-replica all-particle gross check gives nonzero L1-like tags only
     for eplus and n: eplus `21` final events, `0.0285021 cps`; n `7` final
     events, `0.00949607 cps`; all other tags have zero L1-like final events.
     The gross-check total is `0.0379981 cps`, but this is not used as the
     central projection because the eplus row is only the r4 all-particle
     sample and is statistically higher than the dedicated high-stat eplus
     active-collar row (`0.0162824 cps`). Its role is to check for unexpected
     non-eplus/n/muplus channels; none appear in this smoke.
   - Focused-signal EventList smoke replays the current f10m A1 v3p5 Step09
     event list through the active-collar geometry. The transport generated
     `37194/37194` events. Relative to the current focused-signal SIM, the
     active collar keeps essentially the same Step05-like signal sample:
     W2 raw events `30274/30234 = 1.00132`, active-veto-pass events
     `30274/30234 = 1.00132`, and side-Compton/FoV-pass events
     `29646/29597 = 1.00166`. This is a focused-signal smoke only, but it
     directly checks that the open sector is not clipping the nominal focused
     511 signal in this proxy.
   - A rebuilt active-collar delayed activation smoke now exists. The rebuilt
     fixed source has total activity `85.4354 Bq`, close to the current
     fullstat fixed inventory `85.6367 Bq`. The new BGO collar self-activity is
     small: `0.141019 Bq`, `0.0016506` of the smoke inventory. The 100k delayed
     transport has `TE=1150.029637 s`. In the W2 line window it gives raw
     `23` events, `0.0199995 cps`; active-veto-pass `19` events,
     `0.0165213 cps`; and side-Compton/FoV-pass `18` events,
     `0.0156518 +/- 0.003689 cps`. The current authority delayed W2 rate is
     `0.00389764 cps`, so this smoke central value is `4.02x` current delayed.
     The selected-event diagnostics show this is not BGO-collar self-activation:
     the final delayed W2 events are Cu-region dominated (`Cu64 13/18`; first
     non-TES volumes are `ColdPlate_MXC_50mK_SD_anchor`,
     `Cu_SubstrateSupport_SolidDisk_L0_deepest`, `DR_MixingChamber_Cu`, and
     `ColdPlate_CP_100mK_intercept`; top non-TES material category is `Cu` for
     `18/18` events). A direct activity cross-check on those selected Cu
     volumes does not explain the `4.02x` rate by source strength: active/current
     activity in the selected volumes and selected nuclides is
     `0.949977/0.932133 Bq` (`1.019x`), and all-nuclide activity in those
     volumes is `1.30756/1.21173 Bq` (`1.079x`).

   Interpretation: the surrogate active collar confirms the mechanism that
   matters for prompt: restoring active material in the non-signal side solid
   angle can suppress the side-port prompt path without ROI and without clipping
   the focused signal in this smoke. But it does not change the mainline route:
   the preferred geometry fix remains restored CsI side-wall continuity or a
   side-hole CSG correction. The BGO surrogate also exposes a delayed risk.
   Active prompt projection plus this delayed smoke is `0.0414363 cps`: lower
   than the current authority background `0.0629804 cps`, but above old
   `new_geo_re` prompt total `0.0323247 cps`. Since the delayed W2 events are
   Cu-region dominated and not BGO self-activation, the next closure must
   distinguish smoke-statistics/source-sampling fluctuation from a real Cu
   delayed coupling before any active-collar material choice is promoted.

3. **Side-hole shrink / local CSG correction**

   If the proxy side-port cuts are wider than the true optical tunnel, shrink
   the z/phi cut in CsI/liners/outer shell to the physically required beam
   envelope, then rerun prompt diagnostics. This is likely the cleanest
   geometry correction if CAD permits it, because it restores mass where the
   leak is generated rather than adding unrelated global mass.

Required areal density scale:

- 90% removal at 511 keV is roughly `27 g/cm2`;
- examples: `1.4 cm W`, `3.8 cm BGO`, `6 cm CsI`, or `10 cm Al`;
- old corresponding side column is `48.3 g/cm2` with transmission about
  `0.016`.

## Validation Closure Required Before Promotion

A design is not mature until this sequence closes:

1. Geometry candidate with overlap check clean.
2. Prompt-eplus boosted runs, enough statistics to see the side-port component.
3. All-particle prompt run to catch non-eplus changes.
4. Activation buildup rerun for the modified material model.
5. Delayed source rebuilt from the new inventory, not replayed from old
   inventory.
6. Step05 detector response and active-veto selection rerun.
7. High-stat n and muplus prompt follow-ups or an all-particle prompt replay to
   catch prompt components that are increased by the added material.
8. Step06/07/08 mission/time significance rerun.
9. Entry audit repeated to prove the side-port side-wall component dropped and
   no new neutron-dominated side component replaced it.
10. Signal transport checked in the open sector to verify no unacceptable signal
   clipping.
11. Report mass, activation, and mechanical/thermal tradeoffs explicitly.

Until these pass, the best wording is:

> The prompt-511 excess is traced to a local side-port/side-wall leakage mode.
> A targeted local side-port collar that restores non-signal side-wall
> shielding is the leading hardware fix. A W-only shadow liner gives about
> fourfold prompt-eplus suppression in the seed-correct diagnostic, but the
> seed-correct neutron follow-up raises the surviving n component enough that
> the eplus+n+carried-muplus prompt projection remains above old `new_geo_re`.
> A same-envelope active-veto surrogate smoke keeps eplus suppressed,
> removes the small current muplus carry-over, and reduces the W-only neutron
> penalty, giving a prompt-only projection below old `new_geo_re` without ROI.
> This supports restoring active side material in the non-signal solid angle,
> but the mainline implementation should remain CsI side-wall continuity or a
> true side-hole CSG correction, followed by new activation, delayed add-back,
> prompt all-particle, signal-transport, and seed-correct prompt closure.

## Current Best Quantitative Expectation

Authority current hard-window values remain:

- background/signal: `0.06298036183985109 / 0.0011811656293957314 cps`.
- prompt/delayed in W2: `0.0590827 / 0.00389764 cps`.
- prompt-eplus: `0.0543377 cps`.
- `Z20d = 6.130394687582996`.
- `F3(20d) = 4.893649027323553e-5 ph cm^-2 s^-1`.

Directional, non-authority expectations:

- removing only the side-port side-wall prompt-eplus term gives residual
  prompt-eplus `~0.01291 cps`, below old prompt-eplus.
- a targeted W-liner seed-correct smoke achieved raw prompt-eplus suppression
  `3.73x` and eplus Step05-like suppression `4.00 +/- 1.34`, reducing current
  L1-like prompt-eplus from `0.0543377 cps` to `0.0135766 cps`.
- the seed-correct n-only repack follow-up changes the design-risk
  interpretation decisively: n rises from current `0.00407166 cps` to repack
  `0.0200251 cps` after Step05-like selection. With eplus and n replaced by
  seed-correct repack rows and muplus carried from current, the prompt
  projection is `0.0342750 cps`, or `1.0603x` old `new_geo_re` prompt total
  `0.0323247 cps`. W-only is therefore not sufficient as the mature solution.
- even if the small current muplus carry-over (`0.0006733 cps`) were removed,
  the seed-correct eplus+n central projection would be `0.0336016 cps`, still
  `1.0395x` old. Therefore the next decision-changing fix is not a muplus
  replay; it is reducing the repack neutron component or restoring active veto
  correlation.
- the active-veto surrogate prompt-only smoke now provides that
  decision-changing comparison: eplus L1-like prompt is `0.0162824 cps`, n
  L1-like prompt is `0.00950210 cps`, and muplus is `0` after
  side-Compton/FoV. The
  eplus+n+muplus projection is `0.0257845 cps` (`0.797671x` old `new_geo_re`
  prompt total), with no nonzero current prompt tag carried. A low-replica
  all-particle gross check finds no unexpected non-eplus/n/muplus final
  L1-like channel, although its eplus row fluctuates high and is not used as
  the central projection. This is the current best prompt-only hardware-fix
  candidate.
- the active BGO collar delayed activation smoke changes the maturity
  assessment. The BGO collar self-activity is only `0.141019 Bq`
  (`0.0016506` of the smoke inventory), but the 100k delayed transport gives
  W2 side-Compton/FoV-pass delayed `18` events, `0.0156518 +/- 0.003689 cps`,
  compared with current authority delayed `0.00389764 cps`. The selected-event
  diagnostics are Cu-region dominated (`Cu64 13/18`; top non-TES material
  category `Cu` for `18/18` events), so this is not evidence that BGO
  self-activation is the driver. The selected Cu volumes have only
  `1.019x` higher selected-nuclide activity and `1.079x` higher all-nuclide
  activity than current, so source strength alone cannot explain the `4.02x`
  delayed W2 rate. Combining the active prompt projection with this delayed
  smoke gives `0.0414363 cps`, lower than current total `0.0629804 cps` but
  not old-like relative to old prompt `0.0323247 cps`.
  Therefore the active-collar surrogate remains a mechanism check for a CsI
  side-wall-continuity fix, not a final sensitivity or mature total-background
  claim and not a material recommendation to switch the mainline to BGO.
- focused-signal smoke for the same active-collar geometry generated
  `37194/37194` current f10m A1 EventList triggers and gives active/current
  ratios of `1.00132` for W2 raw and active-veto-pass signal events and
  `1.00166` for side-Compton/FoV-pass signal events. This supports the claim
  that the collar is not achieving the prompt reduction by clipping the focused
  signal aperture in this proxy.

Do not quote these directional values as final sensitivity until the validation
closure above is complete.

## Requirement Coverage Audit

| requirement | current evidence | status |
|---|---|---|
| read and preserve project constraints | `core_md/HANDOFF_20260617.md`, `core_md/README.md`, `core_md/workflow.md`, `core_md/Project_Memory.md`; this note keeps `fullstat_v2_exactpos_m50000_s260613` as authority and keeps ROI/BGO boundaries explicit | covered |
| decide window versus wall leakage | strict current window `1/80`, broad foil/window `3/80`, non-window `77/80`; old/current window-like rates both around `0.001-0.002 cps`, while current wall/non-window is `0.05230 cps` | covered: wall/side-port dominates |
| explain source normalization without inventing a flux-card bug | eplus flux and base event denominator match; per-event source weight ratio `2.94175` matches `(60/35)^2`; selected-event efficiency is lower in current (`80/106`) | covered |
| analyze material/geometry difference in the leakage region | old corresponding side line has `48.34 g/cm2` material-column proxy and `T511~0.016`; current side-window-only has `0.06 g/cm2` and `T511~0.995`; geometry builder explicitly cuts side-port z/phi bands through annular shells | covered |
| follow prompt particles/interaction points | prompt incidence, interaction-track, material-ledger, and ray-trace outputs show current selected events born near side-port/side-wall and old side-region events stopping in CsI/Al/W/Cu; representative current and old events are listed above | covered as diagnostic, with stated SIM/chord caveats |
| show how current can approach old-like prompt without ROI | removing the current side-port side-wall eplus term gives `~0.01291 cps`; seed-correct W-liner repack suppresses eplus to `0.0135766 cps`, but seed-correct n rises to `0.0200251 cps`, giving prompt projection `0.0342750 cps` with muplus carried, above old `0.0323247 cps`; same-envelope active-veto surrogate gives eplus `0.0162824 cps`, n `0.00950210 cps`, muplus `0`, and eplus+n+muplus prompt projection `0.0257845 cps`, below old prompt; a low-replica all-particle gross check finds no unexpected non-eplus/n/muplus final channel; delayed smoke then adds a Cu-dominated `0.0156518 cps` central value, so total-background maturity is not closed | covered as prompt-only design smoke: restoring active side material can reach old-like prompt without ROI, W-only does not; mainline implementation remains CsI continuity/CSG correction; delayed add-back remains blocking |
| check active-collar signal clipping | focused EventList transport through the active-collar geometry generated `37194/37194` events; Step05-like signal ratios are `1.00132` for W2 raw/active-veto-pass and `1.00166` after side-Compton/FoV | covered as focused-signal smoke; final response/mission authority still pending |
| check active-collar delayed add-back | rebuilt active-collar delayed source total activity is `85.4354 Bq`; BGO self-activity is `0.141019 Bq`; delayed W2 smoke gives `18` final events, `0.0156518 cps`, `4.02x` current delayed, with final events dominated by Cu-region primaries/volumes rather than BGO collar | covered as smoke; blocks mature total-background promotion until higher-stat delayed closure |
| mature implementation path | leading prompt fix is restored CsI active side-wall continuity in the non-signal side-port solid angle, or side-hole shrink/CSG correction if the current cuts are wider than the physical beam tunnel; the BGO collar is only a surrogate active-veto smoke; total-background promotion now also requires resolving the Cu-dominated delayed W2 smoke | covered as engineering path; not yet a final rate authority |

The completed root-cause answer is therefore: old `new_geo_re` is not low
because it has a magic top-window response or an ROI-like selection. It is low
because the side region corresponding to the current high-leakage side-entry
solid angle is a continuous CsI/passive material column. Current v3p5 moved the
entry to the side and cut that column into side-port bands, creating a large
non-window side-wall source-to-TES path. The robust fix is to restore the
old-style non-signal side material/veto column locally while keeping the true
signal aperture open. A W-only passive liner is a useful diagnostic and eplus
shadow, but the seed-correct neutron follow-up shows that W-only leaves a
larger neutron-induced line-window component and remains above old prompt at
the central value. A same-envelope active-veto surrogate smoke shows that
restoring active material in the non-signal side solid angle can suppress
eplus, limit the neutron penalty, remove the small muplus final event in this
smoke, and project below old prompt without ROI. The focused EventList smoke
also shows that the open sector does not clip the nominal focused signal in the
current proxy. But this is a mechanism smoke, not a BGO mainline. The mainline
fix should remain CsI side-wall continuity or side-hole CSG correction. The
first rebuilt delayed smoke gives a Cu-dominated W2 delayed central value of
`0.0156518 cps`, well above the current delayed authority, even though BGO
self-activation is small and the implicated Cu-volume activity is only about
`1.02--1.08x` current. The mature solution must therefore restore the old-like
CsI active/passive side column for prompt, not just add passive W or swap the
mainline material, and it must also resolve central Cu delayed
transport/source-sampling stability before any total-background or sensitivity
promotion.

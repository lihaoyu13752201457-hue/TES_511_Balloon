# Prompt-511 Geometry Variant Review 2026-06-20

Status: `NO_PROMOTION`

This review covers the Claude `jacket_W_liner_variantB` geometry plus early
follow-up CsI smokes built to test whether the prompt excess is solved by a
simple passive/active shell addition. The active-CsI collar section has been
superseded by the current dedicated review in
`outputs/reports/prompt511_active_csi_collar_20260620/ACTIVE_CSI_COLLAR_REVIEW.md`.

## Authority Baseline

- Current authority label: `fullstat_v2_exactpos_m50000_s260613`.
- Current prompt/delayed W2 rates: `0.0590827 / 0.00389764 cps`.
- Current e+ prompt component: `0.0543377 cps`.
- Old `new_geo_re` prompt total: `0.0323247 cps`.
- Required interpretation boundary: prompt excess is not a narrow signal-window
  leak; current strict-window leak was only `1/80` in the earlier selected-event
  audit.

## Finding 1: VariantB Is Not Fixed

`outputs/geometry/DEMO2_DR_v3p5_jacket_W_liner_variantB_megalib_proxy` adds W
liner pieces around the side-port/jacket region.  Its overlap check is clean,
but the geometry does not cover the actual selected-event leakage as claimed.

Earlier raytrace against the 80 current prompt-e+ final records found:

- actual added-W hits: `33/80`, rate `0.0224143 cps`;
- actual misses: `47/80`, rate `0.0319234 cps`;
- predicted-caught-but-actual-miss: `45`, rate `0.030565 cps`;
- residual estimates stayed around `0.03394-0.03453 cps`.

That is not enough margin against old `new_geo_re` once n/mu are included, and
the W-only route had already shown n prompt can rise.  Treat VariantB as a
diagnostic, not a corrected geometry.

## Finding 2: Active-CsI Collar Evidence Was Superseded

I built `outputs/reports/prompt511_active_csi_collar_20260620`, replacing the
previous repack W liner envelope with `CsI_Active_Shield_Prompt511_Collar_*`.

This section originally mixed an early `geometry_active_collar_csi` directory
without collar `.det` entries, a later `geometry_active_csi_collar` directory,
and a `cli_seed` run that retained multiple isotope-store increments. The stale
intermediate claim that a native rerun gave `0.0773771 cps` comes from parsing
12 e+ SIM files in `runs/active_csi_collar_eplus_g10m_r4_cli_seed` while the
rate normalization corresponds to the 4 requested e+ jobs. It is an increment
glob / normalization mismatch, not the current prompt-only gate.

The current `geometry_active_csi_collar` setup has explicit Scintillator
entries for the four `CsI_Active_Shield_Prompt511_Collar_*` volumes and source
cards pointing at that setup. Its dedicated prompt-only L1 proxy gives:

| particle | current L1-like cps | active-CsI collar L1-like cps |
|---|---:|---:|
| e+ | `0.0543377` | `0.0257843` |
| n | `0.00407166` | `0.00203561` |
| mu+ | `0.000673320` | `0.000271415` |

The resulting prompt projection is `0.0280914 cps`, or `0.869037x` old
`new_geo_re` prompt. Treat that as the current prompt/isotope candidate result,
not as a final delayed-source or Step06/07/08 authority.

## Finding 3: Upper CsI Wall Alone Fails

I built `outputs/reports/prompt511_upper_csi_wall_20260620`, adding an old-like
upper side-wall CsI band on the current geometry:

- r: `13.6..18.0 cm`;
- z: `5.55..13.35 cm`;
- added CsI mass: about `15.366 kg`;
- overlap: clean except the expected no-trigger warning.

Without new `.det` entries, e+ fell only to `0.0420802 cps`, not enough.  With
low-threshold sensitive entries added for the new wall, e+ worsened to
`0.0800881 cps`.

One inspected surviving e+ event still annihilated in
`Vacuum_Jacket_Al_266mmClass_side_port_side_wall_above_side_port` and showed
only `PM CsI 6.331 keV`, below veto threshold.  So simply placing an upper wall
does not recreate the old topology or produce sufficient active veto.

## Interpretation

The current issue is not solved by VariantB's short W liner or by the upper
CsI wall alone. The evidence points to a topology/material mismatch:

- current has an exposed/tall upper OVC and service/lid topology that can
  create 511-keV prompt events without depositing enough energy in active CsI;
- old `new_geo_re` avoided this through a different material/topology column,
  not by an ROI cut;
- detector coupling matters: new active material must have native detector
  entries before a prompt suppression claim is credible;
- the current active-CsI collar result is promising but still needs signal
  replay and delayed-source rebuild before any authority promotion.

## Recommended Next Route

1. Compare current vs `new_geo_re` around the upper OVC/top-service geometry,
   especially the z extent and shielding between the source sphere and
   `Vacuum_Jacket_...side_wall_above_side_port`.
2. Build the next candidate from that topology difference, not from a local
   W/CsI add-on:
   - either shorten/remove unrealistic exposed upper OVC material if it is a
     modeling artifact, or
   - surround the full exposed upper OVC/service region with an old-like active
     shield and accept that mass/activation must be re-audited.
3. For all future prompt smokes, add native `.det` entries at geometry build
   time and use a prompt-only source card without isotope production.  Run
   activation/isotope storage separately.
4. Do not run delayed/Step06-08 promotion until prompt passes with native
   detector coupling for e+, n, and mu+.

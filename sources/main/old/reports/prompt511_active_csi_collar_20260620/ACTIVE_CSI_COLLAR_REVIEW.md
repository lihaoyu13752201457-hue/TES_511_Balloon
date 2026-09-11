# Prompt-511 Active-CsI Collar Review 2026-06-20

Status: `PROMPT_PASS__LOW_ADDED_ISOTOPE_SMOKE__SIGNAL_REPLAY_PASS__NO_AUTHORITY_PROMOTION`

This review covers:

`outputs/reports/prompt511_active_csi_collar_20260620`

It supersedes the stale active-collar discussion in
`outputs/reports/prompt511_variant_review_20260620/REVIEW.md`.

Use the `active_csi_collar` artifacts as the current branch. The older
`active_collar_csi` manifest/directory is a retained intermediate copy and is
not the review target.

## Geometry

The candidate replaces the previous local repack W liner envelope with active
CsI collar volumes:

- setup:
  `geometry_active_csi_collar/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_active_csi_collar_r4p25_5p95.geo.setup`
- added volumes:
  `CsI_Active_Shield_Prompt511_Collar_z1_a`,
  `CsI_Active_Shield_Prompt511_Collar_z1_b`,
  `CsI_Active_Shield_Prompt511_Collar_z2_a`,
  `CsI_Active_Shield_Prompt511_Collar_z2_b`
- material: `CsI`
- radius: `r=4.25..5.95 cm`
- z segments: `[-8.75,-0.65] cm` and `[0.65,4.65] cm`
- signal gap: `phi=160..200 deg`
- added collar mass: `2.6416338276441684 kg`

The signal gap is wider than the previous narrow side-port proxy and no ROI or
source spot is used.

The current `.det` includes Scintillator entries for all four collar volumes.
This is still a Step05-like proxy treatment, not a native trigger/veto
authority: the proxy scaffold still has no native MEGAlib Trigger/Veto block.

## Source / Load Checks

Source cards:

- directory: `source_cards_active_csi_collar`
- 8 full-sphere particle source cards
- 20 `FarFieldAreaSource` beams per card
- `farfield_radius_cm=60`
- no `ROI`, focal spot, `PointSource`, or `HomogeneousBeam`
- all cards point to `geometry_active_csi_collar/...geo.setup`

Overlap/load smoke:

- source: `overlap_active_csi_collar.source`
- log: `overlap_active_csi_collar.log`
- result: geometry loads and the overlap smoke completes without a retained
  `GeomVol`/overlap/error diagnostic in the checked log path.

## Prompt-Only L1 Proxy

Prompt runs used full-sphere source cards and `--disable-isotope-store`.

| particle | jobs | failures | generated particles |
|---|---:|---:|---:|
| e+ | 4 | 0 | 974,908 |
| n | 16 | 0 | 15,409,056 |
| mu+ | 80 | 0 | 928,400 |

Window: `510.58 <= TES_total_keV < 511.42`.
Active-veto threshold in the proxy: `50 keV`.

| particle | current L1-like cps | active-CsI collar L1-like cps |
|---|---:|---:|
| e+ | `0.0543377485` | `0.0257843379` |
| n | `0.00407165571` | `0.00203560893` |
| mu+ | `0.000673320419` | `0.000271414687` |

Total prompt projection:

- current official prompt total: `0.0590827246 cps`
- active-CsI collar projection: `0.0280913615 cps`
- old `new_geo_re` prompt total: `0.0323247092 cps`
- projected/old ratio: `0.869036789`
- current-carried prompt tags: none in the high-stat projection

This passes the prompt-oldlike gate for the tested e+/n/mu+ channels.

The stale `0.0773771 cps` e+ number is not the prompt-only gate. Re-reading the
same proxy code shows:

- `runs/active_csi_collar_eplus_g10m_r4_promptonly`: 4 SIM files, 19 L1-like
  events, `0.0257843379 cps`.
- `runs/active_csi_collar_eplus_g10m_r4_cli_seed`: 12 SIM files from three
  retained increments, 57 L1-like events, `0.0773771062 cps`.

Both runs load and hit the `CsI_Active_Shield_Prompt511_Collar_*` scintillator
volumes. The `cli_seed` value is a file-glob/normalization mismatch: it parses
three increments but keeps the single-increment job normalization. It should not
override the prompt-only result.

## All-Particle Prompt Gross Smoke

Low-stat all-particle smoke:

- run: `runs/active_csi_collar_allparticle_smoke_g1m_r2_promptonly`
- generated particles: `1,380,258`
- L1-like total in the smoke: `0 cps`
- nonzero L1-like tags: none
- unexpected nonzero L1-like tags outside e+/n/mu+: none

This is only a gross screen. It is not a high-stat upper limit.

## Isotope-Store Smoke

Buildup isotope-store run:

- run: `runs/active_csi_collar_buildup_isotope_g1m_r2`
- jobs: `16/16 PASS`
- generated particles: `1,380,258`
- DAT files: `16`
- all-volume total smoke value: `6638`
- added collar RP rows: `22`
- added collar total smoke value: `198`
- added collar fraction of all smoke value: `2.983%`

Added-volume records are dominated by neutrons:

| particle | value |
|---|---:|
| n | 197 |
| muminus | 1 |

Top added-volume nuclides:

| nuclide | value |
|---|---:|
| Cs-134 | 111 |
| I-128 | 82 |
| Sb-119 | 1 |
| Sn-113 | 1 |
| I-121 | 1 |
| Te-123 | 1 |
| Cs-127 | 1 |

This isotope smoke is much smaller than the hybrid W/CsI shroud's added-volume
fraction (`28.339%`) and avoids the large W activation burden seen in the
upper-W-shadow diagnostic. It is not a delayed-rate result: no half-life
folding, RPIP delayed source, delayed transport, or day-20 rate is inferred.

## Delay-Risk Audit

The follow-up activity/decay-line audit uses only the existing isotope-store
DAT files, the RPIP source-builder div/mean-TT convention, local NUBASE
half-lives, and the local Geant4 W1/511 decay-line scanner:

- audit:
  `prompt511_active_csi_collar_delay_risk_audit.md`
- day-15 added-collar activity estimate: `2.33674 Bq`
- current v3p5 fullstat fixed-source total: `85.6367 Bq`
- added/current total activity ratio: `2.729%`
- added/current CsI activity ratio: `3.372%`
- added W1/511 line-rate equivalent from local Geant4 decay lines:
  `0.00747717 Bq-equiv`

The dominant added activities are `I-128` (`2.21256 Bq`) and `Cs-134`
(`0.0409842 Bq`). The small W1/511 line estimate is dominated by rare
low-count `I-121` and `Cs-127` records in this smoke. The existing W2 delayed
511 table remains `Cu64/Cu62/Cu61` dominated, so this audit supports a
low-delay-risk interpretation for the active-CsI collar, but it is still not a
delayed-source rebuild or delayed transport authority.

## Focused Signal Smoke

Focused EventList replay was run through the active-CsI-collar geometry to
check that the `phi=160..200 deg` signal gap does not clip the Laue spot:

- source:
  `runs/active_csi_collar_focus_smoke/Opticsim_laue_f10m_a1_prompt511_active_csi_collar.source`
- SIM:
  `runs/active_csi_collar_focus_smoke/Opticsim_laue_f10m_a1_prompt511_active_csi_collar.inc1.id1.sim.gz`
- generated/stored: `37194/37194`
- geometry:
  `geometry_active_csi_collar/...prompt511_active_csi_collar_r4p25_5p95.geo.setup`

Step05-like W2 focused-signal proxy:

| case | generated | TES kept | W2 raw | active pass | side-Compton/FoV pass |
|---|---:|---:|---:|---:|---:|
| current baseline | 37194 | 35707 | 30234 | 30234 | 29597 |
| active-CsI collar | 37194 | 35761 | 30303 | 30303 | 29706 |

Signal retention ratios relative to current:

- W2 raw: `1.00228`
- active-veto pass: `1.00228`
- side-Compton/FoV pass: `1.00368`

This passes the focused-signal clipping smoke. It is still not a Step05/06/07/08
authority because prompt, delayed, and signal are not rebuilt together on a
common production chain.

## Interpretation

The active-CsI collar is the best current prompt/isotope candidate among the
tested variants:

- VariantB is not fixed because its W liner stops at `z=1 cm` and catches only
  `33/80` selected current e+ prompt rays.
- Upper-W-shadow passes prompt (`0.0252415 cps`) but adds about `27.4494 kg` W,
  raises neutron prompt, and records many W activation products.
- Hybrid W/CsI shroud is old-like but remains above old prompt
  (`0.0349446 cps`, `1.08105x` old) and has a large added isotope-store
  fraction (`28.339%`).
- Active-CsI collar projects below old prompt (`0.0280914 cps`, `0.869x` old)
  while adding only `2.6416 kg` CsI, recording `2.983%` added-volume isotope
  smoke in this low-stat buildup test, giving a `2.33674 Bq` day-15
  added-activity estimate (`2.729%` of the current fixed source), and retaining
  the focused W2 signal in the EventList smoke.

Do not promote this to the paper or mission authority yet. The required next
checks before authority promotion are:

1. delayed-source rebuild and delayed transport if this geometry becomes the
   chosen design branch;
2. final Step05/06/07/08 chain only after the prompt and delayed branches both
   close.

For the current prompt-repair objective, this candidate is the most defensible
tested branch to carry forward.

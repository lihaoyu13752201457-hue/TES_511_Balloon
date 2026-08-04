# S3a/S3b/S3c dominant-background review - 2026-07-09

## Scope

This review covers only the requested dominant effective-background subset:

- Prompt positron (`eplus`) same-stat replay.
- Prompt neutron (`n`) same-stat replay.
- `atm511` 4pi sidecar replay.

No gamma, alpha, electron, muon, proton, delayed/activation, focused-source,
or Step05-08 promotion run is included in this package.

## Geometry variants

| Variant | Geometry-only change relative to S3 |
|---|---|
| S3a | CsI barrel scintillator changed to BGO; original 8 mm Al shell retained. |
| S3b | CsI retained; 8 mm Al shell changed to 2 mm W + 3 mm Al; leftover gap retained. |
| S3c | S3a + S3b combined: BGO scintillator and 2 mm W + 3 mm Al shell; leftover gap retained. |

## Run products

| Variant | Prompt eplus/n run | Atm511 sidecar run | Dominant summary |
|---|---|---|---|
| S3a | `runs/geometry_optimization_20260704/s3a_bgo_barrel_eqstats_prompt_eplus_n_20260709` | `runs/geometry_optimization_20260704/s3a_bgo_barrel_atm511_sidecar_3m_20260709` | `engineering/geometry_optimization_20260704/30_s3a_dominant_backgrounds_20260709/dominant_background_summary.json` |
| S3b | `runs/geometry_optimization_20260704/s3b_w2mm_al3mm_shell_eqstats_prompt_eplus_n_20260709` | `runs/geometry_optimization_20260704/s3b_w2mm_al3mm_shell_atm511_sidecar_3m_20260709` | `engineering/geometry_optimization_20260704/31_s3b_dominant_backgrounds_20260709/dominant_background_summary.json` |
| S3c | `runs/geometry_optimization_20260704/s3c_bgo_w2mm_al3mm_shell_eqstats_prompt_eplus_n_20260709` | `runs/geometry_optimization_20260704/s3c_bgo_w2mm_al3mm_shell_atm511_sidecar_3m_20260709` | `engineering/geometry_optimization_20260704/32_s3c_dominant_backgrounds_20260709/dominant_background_summary.json` |

## Validation gates

Parent validator:
`engineering/geometry_optimization_20260704/validate_s3abc_dominant_backgrounds_20260709.py`

Validator status:
`PASS_S3ABC_DOMINANT_BACKGROUND_REVIEW_INPUTS`

Validated checks:

- All S3a/S3b/S3c prompt source cards point to their intended geometry.
- All selected prompt SIM headers point to their intended geometry.
- All three prompt runs have 16 selected jobs with no failures.
- All `atm511` source cards and SIM headers point to their intended geometry.
- All three dominant-background summaries are present and PASS.

## Final W2 side-Compton/FOV rates

Rates below are for the `510.58-511.42 keV` W2 window after active-veto and
side-Compton/FOV selection. Ratios are against the retained S3 baseline using
the same component and stage. Uncertainties are counting-only 1 sigma from the
summary files.

| Variant | Component | Events | Rate cps | Variant/S3 | Counting-only 1 sigma | S3 events | S3 rate cps |
|---|---:|---:|---:|---:|---:|---:|---:|
| S3a | eplus | 1 | 0.000678454 | 0.0713758 | 0.0738810 | 14 | 0.00950537 |
| S3a | n | 4 | 0.00271376 | 3.99949 | 4.47157 | 1 | 0.000678527 |
| S3a | atm511 | 9 | 0.00174823 | 0.160636 | 0.0576879 | 56 | 0.0108831 |
| S3b | eplus | 10 | 0.00678757 | 0.714077 | 0.295656 | 14 | 0.00950537 |
| S3b | n | 3 | 0.00203630 | 3.00106 | 3.46533 | 1 | 0.000678527 |
| S3b | atm511 | 48 | 0.00931889 | 0.856268 | 0.168427 | 56 | 0.0108831 |
| S3c | eplus | 2 | 0.00135997 | 0.143074 | 0.108154 | 14 | 0.00950537 |
| S3c | n | 2 | 0.00135670 | 1.99948 | 2.44885 | 1 | 0.000678527 |
| S3c | atm511 | 6 | 0.00116688 | 0.107219 | 0.0460574 | 56 | 0.0108831 |

Dominant-subset summed final rates:

| Variant | Sum of eplus+n+atm511 final rates | Sum/S3 same subset |
|---|---:|---:|
| S3a | 0.00514045 cps | 0.2440 |
| S3b | 0.01814276 cps | 0.8612 |
| S3c | 0.00388356 cps | 0.1843 |

S3 same-subset sum: `0.02106705 cps`.

## Review interpretation

S3c is the best of the three under this limited dominant-background replay:
it gives the lowest summed final rate and suppresses both `eplus` and
`atm511` strongly relative to S3.

S3a also suppresses `eplus` and `atm511`, but its neutron final count is higher
than the S3 neutron baseline. The neutron comparison is low-statistics on both
sides, so this should be treated as a warning flag rather than a stable design
ranking by itself.

S3b alone gives only a modest improvement in this subset. Its `atm511` rate is
near the S3 baseline, and its neutron final count is also above S3 in the
low-count comparison.

## Caveats

- This is not a full-background closure. It intentionally excludes the
  non-dominant prompt components and delayed/activation chains.
- The neutron final window has very small selected counts. More neutron
  statistics are needed before treating the neutron ratio as precise.
- W/Al mechanical shell volumes remain excluded from the active-veto rule, as
  planned; active volumes are BGO/CsI, ActiveShield/CEBR3, and
  `GeoOpt_S2B_CryoShell_Plastic*`.

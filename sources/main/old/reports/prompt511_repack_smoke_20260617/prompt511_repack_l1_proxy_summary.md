# Prompt-511 Repack L1-like Proxy

Status: `PASS_PROMPT511_REPACK_L1_PROXY`

This is a prompt-only Step05-like diagnostic. It reuses the official v3p5
TES line window, CsI active-veto threshold, and side-entry Compton/FoV
proxy, but it is not a delayed, signal, Step06, Step07, or Step08
authority.

Seed policy: the repack rows below use command-line
`cosima -s <seed>` runs. The companion seed audit documents why
the older source-card-Seed repack rows were not independent.

Window: `510.58 <= TES_total_keV < 511.42`.
Active-veto threshold: `50.0 keV`.

| case | raw events | raw cps | active events | active cps | L1-like events | L1-like cps |
|---|---:|---:|---:|---:|---:|---:|
| current_baseline | 97 | 0.0658845 | 85 | 0.0577339 | 80 | 0.0543377 |
| w_liner_repack | 13 | 0.0176495 | 11 | 0.0149342 | 10 | 0.0135766 |

Current/repack suppression factors:

- raw: `3.73294 +/- 1.1`
- active_veto_pass: `3.86588 +/- 1.24`
- side_compton_fov_pass: `4.00232 +/- 1.34`

Follow-up particle cases included in this run:

| tag | current L1-like events | current cps | repack L1-like events | repack cps | current/repack |
|---|---:|---:|---:|---:|---:|
| eplus | 80 | 0.0543377 | 10 | 0.0135766 | 4.00232 |
| n | 6 | 0.00407166 | 59 | 0.0200251 | 0.203328 |

Total prompt projection:

- current official Step05-like prompt total: `0.0590827 cps`.
- projected prompt total with available repack particle runs: `0.034275 cps`.
- old `new_geo_re` prompt total: `0.0323247 cps`.
- projected/old ratio: `1.06033`.
- repack-replaced tags: `eplus, n`.
- current-carried tags: `muplus`.

Interpretation:

- The W liner still suppresses the current eplus leakage after applying
  active-veto and side Compton/FoV proxy stages.
- The seed-correct n follow-up strengthens the hardware-risk interpretation:
  W-only raises the surviving n component enough that the eplus+n projection
  remains above old `new_geo_re` at the central value.
- Follow-up particle rows are included only when their repack run has a
  completed run summary; otherwise the projection carries the current
  official prompt contribution for that tag.
- The result remains a geometry/prompt diagnostic only because new W
  activation and delayed-source rebuild are not included.


# Prompt-511 Active-CsI Collar All-Particle Smoke L1-like Proxy

Status: `PASS_PROMPT511_ACTIVE_CSI_COLLAR_ALLPARTICLE_SMOKE_L1_PROXY`

This is a low-stat all-particle gross check for the active-CsI collar.
It is used only to catch unexpected prompt particle channels. It does
not replace the high-stat eplus/n/muplus projection.

Run summary: `outputs/reports/prompt511_active_csi_collar_20260620/runs/active_csi_collar_allparticle_smoke_g1m_r2_promptonly/run_summary.md`.
Window: `510.58 <= TES_total_keV < 511.42`.
Active-veto threshold: `50.0 keV`.

| tag | raw events | raw cps | active events | active cps | L1-like events | L1-like cps |
|---|---:|---:|---:|---:|---:|---:|
| alpha | 0 | 0 | 0 | 0 | 0 | 0 |
| eminus | 0 | 0 | 0 | 0 | 0 | 0 |
| eplus | 1 | 0.0271411 | 0 | 0 | 0 | 0 |
| gamma | 0 | 0 | 0 | 0 | 0 | 0 |
| muminus | 0 | 0 | 0 | 0 | 0 | 0 |
| muplus | 0 | 0 | 0 | 0 | 0 | 0 |
| n | 2 | 0.0542827 | 0 | 0 | 0 | 0 |
| p | 0 | 0 | 0 | 0 | 0 | 0 |

- all-particle smoke L1-like total: `0 cps`.
- nonzero L1-like tags: `(none)`.
- unexpected nonzero L1-like tags outside eplus/n/muplus: `(none)`.

Interpretation:

- This supports the high-stat projection only if no non-eplus/n/muplus
  prompt channel appears in the all-particle smoke.
- Because this is g1m/r2 smoke, absence of a channel is not a high-stat
  upper limit.

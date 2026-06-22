# Prompt-511 Active BGO Collar All-Particle Smoke L1-like Proxy

Status: `PASS_PROMPT511_ACTIVE_COLLAR_BGO_ALLPARTICLE_SMOKE_L1_PROXY`

This is a low-replica all-particle gross check for the active BGO collar.
It is used to catch unexpected prompt particle channels. It does not
replace the high-stat eplus/n/muplus active-collar projection.

Run summary: `outputs/reports/prompt511_repack_smoke_20260617/runs/active_collar_bgo_allparticle_smoke_g10m_r4_cli_seed/run_summary.md`.
Window: `510.58 <= TES_total_keV < 511.42`.
Active-veto threshold: `50.0 keV`.

| tag | raw events | raw cps | active events | active cps | L1-like events | L1-like cps |
|---|---:|---:|---:|---:|---:|---:|
| alpha | 0 | 0 | 0 | 0 | 0 | 0 |
| eminus | 0 | 0 | 0 | 0 | 0 | 0 |
| eplus | 26 | 0.0352883 | 22 | 0.0298593 | 21 | 0.0285021 |
| gamma | 0 | 0 | 0 | 0 | 0 | 0 |
| muminus | 2 | 0.00270438 | 0 | 0 | 0 | 0 |
| muplus | 5 | 0.00680015 | 0 | 0 | 0 | 0 |
| n | 50 | 0.0678291 | 9 | 0.0122092 | 7 | 0.00949607 |
| p | 0 | 0 | 0 | 0 | 0 | 0 |

- all-particle smoke L1-like total: `0.0379981 cps`.
- nonzero L1-like tags: `eplus, n`.
- unexpected nonzero L1-like tags outside eplus/n/muplus: `(none)`.

Interpretation:

- This supports the active-collar projection if no new non-eplus/n/muplus
  prompt channel appears in the all-particle smoke.
- Because this is r4 for most non-gamma particles, absence of a channel is
  a gross-screen result, not a high-stat upper limit.
- The high-stat eplus/n/muplus rows remain the central prompt-only design
  smoke evidence.

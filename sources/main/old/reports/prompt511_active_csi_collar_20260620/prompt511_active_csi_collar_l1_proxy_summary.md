# Prompt-511 Active-CsI Collar L1-like Proxy

Status: `PASS_PROMPT511_ACTIVE_CSI_COLLAR_L1_PROXY`

This is a prompt-only Step05-like diagnostic for the local active-CsI
collar candidate. It reuses the official v3p5 line window, active-veto
matching, and side-entry Compton/FoV proxy. It is not a delayed-source,
science-signal, Step06, Step07, or Step08 authority.

Window: `510.58 <= TES_total_keV < 511.42`.
Active-veto threshold used by this proxy: `50.0 keV`.

| tag | case | raw events | raw cps | active events | active cps | L1-like events | L1-like cps |
|---|---|---:|---:|---:|---:|---:|---:|
| eplus | current_baseline | 97 | 0.0658845 | 85 | 0.0577339 | 80 | 0.0543377 |
| eplus | active_csi_collar | 25 | 0.0339268 | 20 | 0.0271414 | 19 | 0.0257843 |
| n | current_baseline | 115 | 0.0780401 | 6 | 0.00407166 | 6 | 0.00407166 |
| n | active_csi_collar | 220 | 0.074639 | 7 | 0.00237488 | 6 | 0.00203561 |
| muplus | current_baseline | 11 | 0.00740652 | 1 | 0.00067332 | 1 | 0.00067332 |
| muplus | active_csi_collar | 93 | 0.00631039 | 4 | 0.000271415 | 4 | 0.000271415 |

Current/active-CsI-collar suppression factors:

- eplus raw: `1.94196 +/- 0.436`
- eplus active_veto_pass: `2.12715 +/- 0.529`
- eplus side_compton_fov_pass: `2.10739 +/- 0.538`
- n raw: `1.04557 +/- 0.12`
- n active_veto_pass: `1.71447 +/- 0.954`
- n side_compton_fov_pass: `2.00022 +/- 1.15`
- muplus raw: `1.1737 +/- 0.374`
- muplus active_veto_pass: `2.48078 +/- 2.77`
- muplus side_compton_fov_pass: `2.48078 +/- 2.77`

Total prompt projection:

- current official prompt total: `0.0590827 cps`.
- projected prompt total with active-CsI-collar replaced tags: `0.0280914 cps`.
- old `new_geo_re` prompt total: `0.0323247 cps`.
- projected/old ratio: `0.869037`.
- active-CsI-collar replaced tags: `eplus, muplus, n`.
- current-carried tags: `(none)`.

Limitations:

- Only completed active-CsI-collar prompt particle runs are parsed.
- The current baseline is replayed from the official Step05 event_catalog cache.
- No delayed activation, no rebuilt delayed source, no science signal, and no mission time axis are included.
- This tests prompt suppression and active-veto correlation only; it is not final sensitivity.

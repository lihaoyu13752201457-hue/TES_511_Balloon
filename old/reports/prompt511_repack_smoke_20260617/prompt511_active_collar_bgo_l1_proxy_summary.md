# Prompt-511 Active BGO Collar L1-like Proxy

Status: `PASS_PROMPT511_ACTIVE_COLLAR_BGO_L1_PROXY`

This is a prompt-only Step05-like diagnostic for the local active BGO
collar variant. It reuses the official v3p5 line window, active-veto
matching, and side-entry Compton/FoV proxy. It is not a delayed-source,
science-signal, Step06, Step07, or Step08 authority.

Window: `510.58 <= TES_total_keV < 511.42`.
Active-veto threshold used by this proxy: `50.0 keV`.

| tag | case | raw events | raw cps | active events | active cps | L1-like events | L1-like cps |
|---|---|---:|---:|---:|---:|---:|---:|
| eplus | current_baseline | 97 | 0.0658845 | 85 | 0.0577339 | 80 | 0.0543377 |
| eplus | active_collar_bgo | 18 | 0.0244236 | 14 | 0.0189961 | 12 | 0.0162824 |
| n | current_baseline | 115 | 0.0780401 | 6 | 0.00407166 | 6 | 0.00407166 |
| n | active_collar_bgo | 172 | 0.0583701 | 29 | 0.00984146 | 28 | 0.0095021 |
| muplus | current_baseline | 11 | 0.00740652 | 1 | 0.00067332 | 1 | 0.00067332 |
| muplus | active_collar_bgo | 65 | 0.00441468 | 1 | 6.79182e-05 | 0 | 0 |

Current/active-collar suppression factors:

- eplus raw: `2.69758 +/- 0.692`
- eplus active_veto_pass: `3.03925 +/- 0.877`
- eplus side_compton_fov_pass: `3.33721 +/- 1.03`
- n raw: `1.33699 +/- 0.161`
- n active_veto_pass: `0.413725 +/- 0.186`
- n side_compton_fov_pass: `0.4285 +/- 0.193`
- muplus raw: `1.6777 +/- 0.547`
- muplus active_veto_pass: `9.9137 +/- 14`

Total prompt projection:

- current official prompt total: `0.0590827 cps`.
- projected prompt total with active-collar replaced tags: `0.0257845 cps`.
- old `new_geo_re` prompt total: `0.0323247 cps`.
- projected/old ratio: `0.797671`.
- active-collar replaced tags: `eplus, muplus, n`.
- current-carried tags: `(none)`.

Limitations:

- Only completed active-collar prompt particle runs are parsed.
- The current baseline is replayed from the official Step05 event_catalog cache.
- No delayed activation, no rebuilt delayed source, no science signal, and no mission time axis are included.
- The BGO active-collar threshold is the Step05 proxy 50 keV threshold, not the Bgo_sample 70 keV material-control threshold.
- This tests prompt suppression and active-veto correlation only; it is not final sensitivity.

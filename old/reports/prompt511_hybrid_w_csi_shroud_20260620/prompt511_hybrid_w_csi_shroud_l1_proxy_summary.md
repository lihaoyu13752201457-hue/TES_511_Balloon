# Prompt-511 Hybrid W/CsI Shroud L1-like Proxy

Status: `PASS_PROMPT511_HYBRID_W_CSI_SHROUD_L1_PROXY`

This is a prompt-only Step05-like diagnostic for the hybrid thin-W
+ active-CsI shroud candidate. It is not a delayed-source, science-signal,
Step06, Step07, or Step08 authority.

Window: `510.58 <= TES_total_keV < 511.42`.
Active-veto threshold used by this proxy: `50.0 keV`.

| tag | case | raw events | raw cps | active events | active cps | L1-like events | L1-like cps |
|---|---|---:|---:|---:|---:|---:|---:|
| eplus | current_baseline | 97 | 0.0658845 | 85 | 0.0577339 | 80 | 0.0543377 |
| eplus | hybrid_w_csi_shroud | 20 | 0.0271414 | 17 | 0.0230702 | 17 | 0.0230702 |
| n | current_baseline | 115 | 0.0780401 | 6 | 0.00407166 | 6 | 0.00407166 |
| n | hybrid_w_csi_shroud | 206 | 0.0698892 | 36 | 0.0122137 | 35 | 0.0118744 |
| muplus | current_baseline | 11 | 0.00740652 | 1 | 0.00067332 | 1 | 0.00067332 |
| muplus | hybrid_w_csi_shroud | 63 | 0.00427478 | 0 | 0 | 0 | 0 |

Current/hybrid suppression factors:

- eplus raw: `2.42745 +/- 0.596`
- eplus active_veto_pass: `2.50253 +/- 0.665`
- eplus side_compton_fov_pass: `2.35532 +/- 0.629`
- n raw: `1.11662 +/- 0.13`
- n active_veto_pass: `0.333369 +/- 0.147`
- n side_compton_fov_pass: `0.342894 +/- 0.152`
- muplus raw: `1.73261 +/- 0.566`

Total prompt projection:

- current official prompt total: `0.0590827 cps`.
- projected prompt total with hybrid replaced tags: `0.0349446 cps`.
- old `new_geo_re` prompt total: `0.0323247 cps`.
- projected/old ratio: `1.08105`.
- hybrid replaced tags: `eplus, muplus, n`.
- current-carried tags: `(none)`.

Limitations:

- Prompt-only replacement is valid only for the particles actually run.
- No delayed-source, isotope inventory, focused-signal, Step06, Step07, or Step08 conclusion is made here.
- Added W and CsI activation must be inspected separately if prompt gates pass.
- If eplus does not pass, do not spend n/mu/isotope budget on this candidate.

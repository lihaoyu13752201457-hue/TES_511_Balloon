# Prompt-511 Inner Active-CsI Shroud L1-like Proxy

Status: `PASS_PROMPT511_INNER_CSI_SHROUD_L1_PROXY_PARTIAL`

This is a prompt-only Step05-like diagnostic for the inner active-CsI
shroud candidate. It is not a delayed-source, science-signal, Step06,
Step07, or Step08 authority.

Window: `510.58 <= TES_total_keV < 511.42`.
Active-veto threshold used by this proxy: `50.0 keV`.

| tag | case | raw events | raw cps | active events | active cps | L1-like events | L1-like cps |
|---|---|---:|---:|---:|---:|---:|---:|
| eplus | current_baseline | 97 | 0.0658845 | 85 | 0.0577339 | 80 | 0.0543377 |
| eplus | inner_csi_shroud | 40 | 0.0542828 | 33 | 0.0447833 | 30 | 0.0407121 |

Current/inner-CsI-shroud suppression factors:

- eplus raw: `1.21373 +/- 0.228`
- eplus active_veto_pass: `1.28918 +/- 0.264`
- eplus side_compton_fov_pass: `1.33468 +/- 0.286`

Total prompt projection:

- current official prompt total: `0.0590827 cps`.
- projected prompt total with inner-CsI-shroud replaced tags: `0.0454571 cps`.
- old `new_geo_re` prompt total: `0.0323247 cps`.
- projected/old ratio: `1.40626`.
- inner-CsI-shroud replaced tags: `eplus`.
- current-carried tags: `muplus, n`.

Limitations:

- Prompt-only replacement is valid only for the particles actually run.
- No delayed-source, isotope inventory, focused-signal, Step06, Step07, or Step08 conclusion is made here.
- New active CsI has native low-threshold detector entries, but authority trigger wiring is not promoted by this proxy.
- If eplus does not pass, do not spend n/mu/isotope budget on this candidate.

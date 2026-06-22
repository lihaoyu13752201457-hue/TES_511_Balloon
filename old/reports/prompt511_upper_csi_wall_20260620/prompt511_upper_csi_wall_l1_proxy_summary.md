# Prompt-511 Upper CsI Wall L1-like Proxy

Status: `PASS_PROMPT511_UPPER_CSI_WALL_L1_PROXY_PARTIAL`

This is a prompt-only Step05-like diagnostic for the local upper-CsI-wall
variant. It reuses the official v3p5 line window, active-veto matching,
and side-entry Compton/FoV proxy. It is not a delayed-source, science-signal,
Step06, Step07, or Step08 authority.

Window: `510.58 <= TES_total_keV < 511.42`.
Active-veto threshold used by this proxy: `50.0 keV`.

| tag | case | raw events | raw cps | active events | active cps | L1-like events | L1-like cps |
|---|---|---:|---:|---:|---:|---:|---:|
| eplus | current_baseline | 97 | 0.0658845 | 85 | 0.0577339 | 80 | 0.0543377 |
| eplus | upper_csi_wall | 76 | 0.103164 | 67 | 0.0909475 | 59 | 0.0800881 |

Current/upper-CsI-wall suppression factors:

- eplus raw: `0.638637 +/- 0.0978`
- eplus active_veto_pass: `0.634804 +/- 0.104`
- eplus side_compton_fov_pass: `0.678475 +/- 0.116`

Total prompt projection:

- current official prompt total: `0.0590827 cps`.
- projected prompt total with upper-CsI-wall replaced tags: `0.084833 cps`.
- old `new_geo_re` prompt total: `0.0323247 cps`.
- projected/old ratio: `2.6244`.
- upper-CsI-wall replaced tags: `eplus`.
- current-carried tags: `muplus, n`.

Limitations:

- Only completed upper-CsI-wall prompt particle runs are parsed.
- The current baseline is replayed from the official Step05 event_catalog cache.
- No delayed transport, no rebuilt delayed source, no science signal, and no mission time axis are included.
- The added wall is matched by Step05 proxy volume names starting with CsI_; native detector wiring is not yet an authority implementation.
- This tests prompt suppression and active-veto correlation only; it is not final sensitivity.

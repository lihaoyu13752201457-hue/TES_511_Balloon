# Prompt-511 Compact Upper-Service L1-like Proxy

Status: `PASS_PROMPT511_COMPACT_UPPER_SERVICE_L1_PROXY_PARTIAL`

This is a prompt-only Step05-like diagnostic for the compact
upper-service geometry candidate. It reuses the official v3p5 line
window, active-veto matching, and side-entry Compton/FoV proxy. It is
not a delayed-source, science-signal, Step06, Step07, or Step08 authority.

Window: `510.58 <= TES_total_keV < 511.42`.
Active-veto threshold used by this proxy: `50.0 keV`.

| tag | case | raw events | raw cps | active events | active cps | L1-like events | L1-like cps |
|---|---|---:|---:|---:|---:|---:|---:|
| eplus | current_baseline | 97 | 0.0658845 | 85 | 0.0577339 | 80 | 0.0543377 |
| eplus | compact_upper_service | 107 | 0.145207 | 89 | 0.120779 | 84 | 0.113994 |

Current/compact-upper-service suppression factors:

- eplus raw: `0.45373 +/- 0.0636`
- eplus active_veto_pass: `0.478011 +/- 0.0725`
- eplus side_compton_fov_pass: `0.476672 +/- 0.0745`

Total prompt projection:

- current official prompt total: `0.0590827 cps`.
- projected prompt total with compact-upper-service replaced tags: `0.118739 cps`.
- old `new_geo_re` prompt total: `0.0323247 cps`.
- projected/old ratio: `3.67332`.
- compact-upper-service replaced tags: `eplus`.
- current-carried tags: `muplus, n`.

Limitations:

- Only completed compact-upper-service prompt particle runs are parsed.
- The current baseline is replayed from the official Step05 event_catalog cache.
- Prompt-only candidate runs may omit isotope dat files; rates then come from flux, far-field area, and generated event counts.
- No delayed transport, no rebuilt delayed source, no science signal, and no mission time axis are included.
- This tests prompt suppression and active-veto correlation only; it is not final sensitivity.

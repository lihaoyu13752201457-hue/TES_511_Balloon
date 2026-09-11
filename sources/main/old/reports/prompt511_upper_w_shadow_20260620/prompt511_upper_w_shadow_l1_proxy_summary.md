# Prompt-511 Upper W Shadow L1-like Proxy

Status: `PASS_PROMPT511_UPPER_W_SHADOW_L1_PROXY`

This is a prompt-only Step05-like diagnostic for the upper-W-shadow
candidate. It is not a delayed-source, science-signal, Step06, Step07,
or Step08 authority. W-only candidates must still pass n/mu and isotope
recording gates before any design promotion.

Window: `510.58 <= TES_total_keV < 511.42`.
Active-veto threshold used by this proxy: `50.0 keV`.

| tag | case | raw events | raw cps | active events | active cps | L1-like events | L1-like cps |
|---|---|---:|---:|---:|---:|---:|---:|
| eplus | current_baseline | 97 | 0.0658845 | 85 | 0.0577339 | 80 | 0.0543377 |
| eplus | upper_w_shadow | 13 | 0.0176419 | 11 | 0.0149278 | 11 | 0.0149278 |
| n | current_baseline | 115 | 0.0780401 | 6 | 0.00407166 | 6 | 0.00407166 |
| n | upper_w_shadow | 230 | 0.0780317 | 33 | 0.0111958 | 30 | 0.010178 |
| muplus | current_baseline | 11 | 0.00740652 | 1 | 0.00067332 | 1 | 0.00067332 |
| muplus | upper_w_shadow | 71 | 0.00481761 | 3 | 0.000203561 | 2 | 0.000135707 |

Current/upper-W-shadow suppression factors:

- eplus raw: `3.73454 +/- 1.1`
- eplus active_veto_pass: `3.86755 +/- 1.24`
- eplus side_compton_fov_pass: `3.64004 +/- 1.17`
- n raw: `1.00011 +/- 0.114`
- n active_veto_pass: `0.363675 +/- 0.161`
- n side_compton_fov_pass: `0.400043 +/- 0.179`
- muplus raw: `1.53739 +/- 0.498`
- muplus active_veto_pass: `3.30771 +/- 3.82`
- muplus side_compton_fov_pass: `4.96156 +/- 6.08`

Total prompt projection:

- current official prompt total: `0.0590827 cps`.
- projected prompt total with upper-W-shadow replaced tags: `0.0252415 cps`.
- old `new_geo_re` prompt total: `0.0323247 cps`.
- projected/old ratio: `0.780874`.
- upper-W-shadow replaced tags: `eplus, muplus, n`.
- current-carried tags: `(none)`.

Limitations:

- Only completed upper-W-shadow prompt particle runs are parsed.
- The current baseline is replayed from the official Step05 event_catalog cache.
- No delayed transport, no rebuilt delayed source, no science signal, and no mission time axis are included.
- The added W is passive and has no native active-veto detector entries.
- W-only candidates can reduce e+ while raising neutron prompt or activation; n/mu and isotope-record gates are mandatory.

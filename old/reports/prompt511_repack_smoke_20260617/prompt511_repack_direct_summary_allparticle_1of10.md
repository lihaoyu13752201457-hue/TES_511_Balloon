# Prompt-511 Repack Direct Smoke Summary

Status: `PASS_PROMPT511_REPACK_DIRECT_PARSE`

| stream | events | raw line-window rate [s^-1] |
|---|---:|---:|
| delayed | 0 | 0 |
| prompt | 1 | 0.0547537 |

By stream/tag:

| stream:tag | events | rate [s^-1] |
|---|---:|---:|
| delayed:activation | 0 | 0 |
| prompt:alpha | 0 | 0 |
| prompt:eminus | 0 | 0 |
| prompt:eplus | 0 | 0 |
| prompt:gamma | 0 | 0 |
| prompt:muminus | 0 | 0 |
| prompt:muplus | 0 | 0 |
| prompt:n | 1 | 0.0547537 |
| prompt:p | 0 | 0 |

Limitations:

- Raw TES line-window only; no active veto or Compton/FoV rejection.
- If delayed_sim is the replay source, new W-liner activation is not included.
- Low-stat event counts are not rate authority.

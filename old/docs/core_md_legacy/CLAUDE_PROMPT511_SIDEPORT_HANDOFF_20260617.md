# Claude Handoff: Prompt 511 Side-Port Leakage, 2026-06-17

Purpose: this handoff lets Claude quickly re-enter the prompt-511 discussion
without repeating the earlier confusion about "window leakage". The task is to
understand why the current side-entry chain has much larger absolute prompt
eplus cps than old `new_geo_re`, while the selected current events are mostly
not nominal window-disc crossings.

## First Files To Read

Read in this order:

1. `core_md/HANDOFF_20260617.md` for global authority and manuscript rules.
2. `outputs/reports/prompt511_entry_audit_20260617/prompt511_entry_audit.md`
   for the full prompt-511 audit.
3. `outputs/reports/prompt511_entry_audit_20260617/prompt511_raytrace_ledger.md`
   for the geometry chord test.
4. `outputs/reports/prompt511_entry_audit_20260617/prompt511_material_ledger.md`
   for the interaction/material endpoint diagnostic.
5. Optional figures:
   - `outputs/reports/prompt511_entry_audit_20260617/prompt511_prompt_incidence_xz_comparison.png`
   - `outputs/reports/prompt511_entry_audit_20260617/prompt511_track_interactions_xz_comparison.png`
   - `outputs/reports/prompt511_entry_audit_20260617/prompt511_material_path_stacks.png`

The whole `outputs/reports/prompt511_entry_audit_20260617/` directory is git
ignored in the current workspace, so normal `git status` will not show these
artifacts unless `--ignored` is used.

## Core Answer

Do not describe the current prompt excess as "nominal Be/Al window leakage".
The selected current prompt-eplus sample is dominated by non-window side-port
and side-wall paths.

The geometric picture is:

- Old `new_geo_re` is a top/axial-entry geometry. Its side barrel remains a
  continuous material wall: side CsI plus cryostat/passive material.
- Current v3p5 is not merely the same top window moved to the side. It cuts a
  side-entry aperture through the barrel/side shield neighborhood, leaving a
  local side-port topology with edge paths, side-wall material, and aperture
  neighborhood line-of-sight to TES.
- Most selected prompt-eplus survivors are 511 photons born in or near the
  side-port/side-wall material after the outer blocker has already been
  bypassed. They then reach TES through non-window geometry near the aperture.

Short analogy: old side wall is a thick continuous wall; current side-entry is
a hole and edge structure cut into that wall. The main leak is not through the
center of the designed window disc, but around/in the local side-port topology.

## Rate And Normalization Facts

Hard-window prompt/delayed decomposition:

- Old final prompt/delayed:
  `0.0323247092031 / 0.151456825339 cps`.
- Current final prompt/delayed:
  `0.0590827246325 / 0.00389763720735 cps`.
- Old final prompt eplus:
  `0.0244744226824 cps`, `106` events.
- Current final prompt eplus:
  `0.0543377485018 cps`, `80` events.

Important: the absolute current/old prompt-eplus cps ratio is not because the
current geometry selects more prompt-eplus events. It selects fewer:

- event ratio: `80/106 = 0.754717`.
- current/old final prompt-eplus cps ratio: `2.22019`.
- per-event source weight ratio: about `2.94175`, matching the far-field area
  ratio `(60/35)^2 = 2.93878`.
- eplus flux is identical in source cards:
  `0.116980545723 cm^-2 s^-1`.
- base eplus events are identical:
  `243727` old/current.

Therefore there are two separate statements:

1. Absolute cps rise is dominated by source-surface normalization / enclosing
   far-field radius, not by a higher selected-event count.
2. Geometry still matters because it changes the surviving event topology:
   current survivors are side-port/side-wall dominated, whereas old survivors
   belong mostly to old axial/top geometry.

Do not collapse these into "source definition is wrong" or "window is too
thin". The source normalization and the side-port topology are separate issues.

## Window Versus Non-Window

Use the audit definitions exactly:

- Strict nominal window crossing: selected eplus annihilation-to-TES line must
  cross both the current outer Al filter and Be side-window discs inside
  `r=1.898 cm`.
- Strict window leakage: `1/80` events,
  `0.000679221856273 cps`.
- Broad any window/foil disc proxy: `3/80` events,
  `0.00203766556882 cps`.
- Non-window leakage: `77/80` events,
  `0.052300082933 cps`.

The current selected events are dominated by side-port/side-wall or outer-shell
primary volumes:

- current first/last primary categories: `61/80` side-port-or-side;
  `14/80` outer-shell-or-jacket; `5/80` missing.
- strict non-window selected events: side-port/side-wall or outer-shell
  primary categories dominate, with `59` side-port/side-wall, `14`
  outer-shell/jacket, `4` missing in the audit summary.

The phrase "current side-window segment is thin" is only a fixed-line geometry
contrast. It does not mean the selected excess is nominal window-disc leakage.

## Old Versus Current Side-Line Blocker

Key ray-trace result:

- Current intended side-window segment:
  `Be:0.015 cm; Aluminium:0.013 cm`.
- Old corresponding outer-to-inner side line:
  `CsI:4.0 cm; Copper:1.63 cm; LowCarbonSteel:1.17 cm; Aluminium:1.10 cm; StainlessSteel:0.25 cm; G10:0.16 cm; W:0.06 cm; Kapton:0.05 cm`.

This is the most compact geometric proof. Old `new_geo_re` blocks the current
high-leakage side region with a real side-shield material column. Current v3p5
exposes a side-window/side-port path in that same side-barrel region.

Ray-trace implementation detail:

- Script: `outputs/reports/prompt511_entry_audit_20260617/build_prompt511_raytrace_ledger.py`.
- Output: `prompt511_raytrace_ledger.md`, `prompt511_raytrace_summary.json`,
  `prompt511_raytrace_line_chords.csv`,
  `prompt511_raytrace_event_chords.csv`.
- It uses the deepest placed volume on each line segment, so mother/child
  geometry overlaps are not double-counted.
- It is a geometry chord audit only, not an attenuation/scattering/Geant4 step
  replay.
- Sanity check already passed: no event has passive chord greater than ray
  length.

## Event-Level Material And Track Evidence

Material ledger:

- Report:
  `outputs/reports/prompt511_entry_audit_20260617/prompt511_material_ledger.md`.
- Current selected sample: `32/32` TES stops.
- Current selected median path proxy: `47.8 cm`.
- Current selected median shield/material CC energy deposition: `56.6 keV`.
- Current no-TES side/shield sample: `0/100` TES stops.
- Current no-TES stop materials: `CsI 49/100`, `Aluminium 37/100`, `W 6/100`,
  `other 8/100`.
- Current no-TES median shield/material energy deposition: `517 keV`.

Interpretation:

- Stopped side-region events are stopped by side shield/material.
- Selected survivors are not traversing a continuous old-style side material
  column before TES.
- SIM files do not contain full material-boundary step logs, so the material
  ledger is a transport/endpoint diagnostic, not an exact chord integral.

Interaction-track schematic:

- Figure:
  `outputs/reports/prompt511_entry_audit_20260617/prompt511_track_interactions_xz_comparison.png`.
- It samples up to `32` selected final W2 prompt-eplus events and `100`
  no-TES side/shield events per geometry.
- It shows old side-line/no-TES events concentrating in solid old side shield
  material, while current no-TES events concentrate around the side-port and
  side-wall neighborhood.

## Old Geometry Current-Like Region Checks

Old final eplus in the current final-eplus 10-90% TES global x/z envelope:

- Current envelope:
  `x=[-5.558087982764141, -1.7700753374726166]`,
  `z=[-5.3493099839098806, -1.1107841320592435]`.
- Old final eplus in that region:
  `0` events, `0 s^-1`.

Direction-filtered check:

- Filter: `dot(annihilation_to_TES, current_side_axis) >= 0.8`.
- Old: `11` events, `0.00253979858025 s^-1`; TES z quantiles
  `[1.084, 1.084, 2.343, 5.359, 7.227]`; dominated by
  `Outer_Al_Mech_Shell` last-primary volumes (`10/11`).
- Current: `13` events, `0.00882988413154 s^-1`; TES z quantiles
  `[-6.783, -2.863, -2.464, -1.746, -0.491]`; dominated by side-wall/side-port
  last-primary volumes.

Meaning: even when old events are forced into a current-like direction subset,
they still deposit in old axial/top-stack geometry, not the current side-port
TES region.

## Do-Not-Say List

Avoid these statements:

- "The prompt excess is Be-window leakage." Wrong: strict nominal window is
  `1/80`; non-window is `77/80`.
- "The current geometry has more selected prompt-eplus events." Wrong:
  current has `80`, old has `106`; cps rises because per-event normalization is
  larger.
- "Old `new_geo_re` proves side-entry is safe." Wrong: old did not implement
  the current side-port topology; its corresponding side line is blocked by
  solid side material.
- "The ray trace proves transport attenuation." Wrong: it proves deterministic
  geometry chord differences only.
- "Global passive shielding is simply insufficient." Too broad. The evidence
  points to a local side-port/side-wall aperture topology problem. Global mass
  additions, especially Cu/CsI near the detector, can affect delayed activation.

## Best Next Analysis Direction

If continuing design work, focus on local side-port closure, not generic global
mass:

- map the local aperture annulus, side-wall, W sleeve, CsI segmentation, and
  cryostat/liner discontinuities around the side entry;
- test local shadow plug / graded-Z collar / CsI collar / liner continuity
  variants around the aperture;
- keep a delayed-activation cost metric for added Cu/CsI/W mass;
- rerun prompt-only quick diagnostics first, then delayed/source authority only
  after a local design candidate actually suppresses non-window prompt paths.

When explaining to the user, keep the mental picture simple:

"We did not just move a top window to the side. We cut a hole through the side
barrel. Old geometry still had a thick side wall there; current geometry has a
side-port edge region. The selected prompt 511s mostly come from that edge/side
wall neighborhood, not through the center of the nominal window disc."


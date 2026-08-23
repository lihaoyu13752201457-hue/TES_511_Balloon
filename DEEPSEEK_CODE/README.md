# DEEPSEEK_CODE — SH3 OptV3 signal re-pointing and M05 statistical closure

## 2026-08-20 audit update

The 2026-08-19 OpenCode session completed all 32 requested gamma transport
rounds overnight, but it did not rebuild the event catalog, replay the mature
timeline, or report the final sensitivity.  The follow-up audit found two
production-contract problems:

- the original analysis config pointed at
  `/mnt/data/TES_Balloon_511_data/...`, while the expansion driver wrote to
  `/mnt/data/TES_511_Balloon_511_data/...`; and
- `round005` reused deterministic seeds between its canary and full run.

`round005` is therefore excluded.  The valid `round006`--`round036` expansion
contains 99,439,878 primaries; together with the original four rounds the
catalog uses 112,421,262 gamma primaries.  The strict receipt audit, rebuilt
exact-position Step05 catalog, 5 x 200,000 s common-time replay, and independent
arithmetic/code-contract validation all pass.

The resulting candidate-own 20-day W2 sensitivity is

`Fmin(3 sigma, Gaussian) = (2.22937 +/- 0.20862) x 10^-5 ph cm^-2 s^-1`

where `+/-` is the propagated 1-sigma statistical standard error (9.358%).
The Cowan-Asimov 3-sigma threshold is `2.23829 x 10^-5 ph cm^-2 s^-1`.
Model/geometry/response/atmosphere/optics systematics are not included.

See `OPENCODE_SESSION_M05_AUDIT_20260820.md` for the complete review.

## Context

The previous session (Claude 870aea37, 2026-08-18) computed the OptV3 stage-3
signal gate and got **Aeff = 0** from the 37,194-ray signal SIM. Review proved
this is a **geometry-vs-optics contract break**, not a parser bug:

- The step09 EventList injects a ~collimated beam (world direction
  (0.707,0,-0.707), r99=1.23 cm) at world x=-13.1, travelling along instrument
  local +x at **local z = -5.2**.
- SG3B/SE3 placed the TES at local (3, 0, -5.2) — 0.004 cm from the beam axis.
- OptV3 translated the TES/chimney to local (-32.55, 0, -2.8): the beam line
  z=-5.2 misses it by 2.4 cm **and** the chimney points in -x, i.e. the TES is
  behind the injection plane. 99.7% of the 37,194 photons escaped with zero
  interaction.

User decision: **option B — the new focal plane at chimney axis z=-2.8 is the
design intent.** The signal beam must be re-pointed there; the background
campaign (unchanged geometry) is unaffected.

## The fix

The EventList rays are (to first order) a rigid bundle: nearly parallel with a
tiny convergence. Re-pointing is a pure translation in world coordinates:

| axis | old (SG3B contract) | new (OptV3 chimney) | delta |
|---|---|---:|---:|
| local x (injection plane) | -13.1 | -46.0 | -32.9 cm |
| local z (beam line) | -5.2 | -2.8 | +2.4 cm |

World translation  T = R_y(45) * (-32.9, 0, 2.4) = (-21.566757, 0, +24.960869)

Verified on the transformed bundle (37,194 rays):

- beam centroid (y, z) = (-0.003, -2.799) — exactly on the chimney axis z=-2.8
- r99 = 1.23 cm, max = 1.56–1.65 cm along the full path
- W box (opening |y|<2.775, -4.15<z<-1.45 at x=-44.7): **all 37,194 rays pass,
  zero clips**
- layer windows (r = 2.7 at x=-39.4..-42.0): no clipping (beam max 1.60 cm)
- TES array (half-extents 1.8×1.8 at x=-32.55): beam fully within footprint

## Transport result (seed 83718195, cosima rc=0)

- 37,194 events, 36,608 with CC HIT (98.4%)
- 402,892 TES CC HIT lines across all six layers (L0..L5)
- 36,315 BGO CC HIT lines (SideShield/RearColdPort/FrontOptical)
- **W-box CC HIT lines = 0** (structural confirmation of the opening check)
- SIM SHA-256 `eaa36830...`, EventList SHA-256 `2cfbeaf7...`
- data: `/mnt/data/TES_Balloon_511_data/SH3/sh3_optv3_signal_37194_focal_z2p8_v1/`

## Files

```
copy_previous/
  66_signal_configs/            original signal-gate sources + config
  67_timeline_code/             original build_event_catalog_sh3.py
                                run_mature_timeline_sh3.py
  analysis_inputs.json          original analysis contract
modified/
  transform_eventlist.py        generate re-pointed eventlist + geometry checks
  signal_smoke1000_focal_z2p8.source
  signal_full37194_focal_z2p8.source
  analysis_inputs_optv3_B.json  modified analysis contract (points at new SIM)
  run_mature_timeline_sh3_optv3_B.py   modified timeline+Aeff+Fmin script
outputs/
  eventlists/                   re-pointed eventlist (sha 2cfbeaf7...)
  signal_full37194_focal_z2p8_receipt.json
  02_mature_timeline_B/         final result (Aeff, Fmin, per-anchor rates)
  03_gamma_expansion_audit_20260820.json
                                strict audit; round005 excluded
  04_event_catalog_step05_m05_fixed_20260820/
                                exact-position Step05 catalog
  05_mature_timeline_m05_fixed_20260820/
                                five 200 ks anchors and final sensitivity
  06_final_statistics_validation_20260820.json
                                independent numerical and code-contract closure
```

## Boundaries

- The old `outputs/01_event_catalog/` and `outputs/02_mature_timeline_B/` are
  historical diagnostics, not the final statistical result.  The audited
  result uses the new exact-position catalog and real Step05 topology above.
- The M05 common-time replay uses isotope-resolved delayed activity, a 1 us
  transitive grouping window, 45-degree slant atmospheric transmission, and a
  signal accidental-coincidence survival probe.
- The W2 Aeff is a **candidate-own** value for OptV3; a matched SG3B signal
  transport with the same re-pointed ray bundle is required before any
  relative SG3B-vs-OptV3 sensitivity claim.
- The reported uncertainty is statistical only.  It is not a restoration of
  full-chain physics authority and does not include response, geometry,
  atmosphere, source-model, optics, or Step05-disk systematics.

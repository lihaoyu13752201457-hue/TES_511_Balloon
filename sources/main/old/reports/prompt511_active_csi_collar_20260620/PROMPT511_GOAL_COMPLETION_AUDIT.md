# Prompt-511 Geometry-Repair Goal Completion Audit

Date: 2026-06-20

Status: `USER_LIMITED_SMOKE_SCOPE_COMPLETE__NO_RATE_AUTHORITY`

This audits the user-scoped goal: repair the current geometry against old
`new_geo_re` so prompt is reduced to the same order, preserve the current
low-delay advantage as far as the requested prompt/isotope smoke scope can
show, avoid ROI/source tricks, keep the window no smaller than the Laue focused
spot, avoid geometry overlap/pathology, run atmospheric prompt smoke, and
record activation nuclides. The user explicitly limited the required
post-repair checks to prompt plus isotope recording, not delayed/veto/time-axis
production authority.

Current branch under audit:

`outputs/reports/prompt511_active_csi_collar_20260620`

Current candidate:

`active_csi_collar`

## Requirement Audit

| Requirement | Verdict | Evidence |
|---|---|---|
| Repair geometry instead of relying on ROI/spot/source narrowing | `PASS` | Geometry adds four `CsI_Active_Shield_Prompt511_Collar_*` active-CsI collar volumes, `r=4.25..5.95 cm`, z segments `[-8.75,-0.65]` and `[0.65,4.65]`, signal gap `phi=160..200 deg`, mass `2.6416338276441684 kg`; see `prompt511_active_csi_collar_manifest.json` and `ACTIVE_CSI_COLLAR_REVIEW.md`. |
| Compare against old `new_geo_re` and lower prompt to same order | `PASS` | Prompt L1 proxy: current official prompt `0.0590827246 cps`, active-CsI collar projection `0.0280913615 cps`, old `new_geo_re` prompt `0.0323247092 cps`, projected/old ratio `0.869036789`; see `prompt511_active_csi_collar_l1_proxy_summary.json`. |
| Use full-sphere atmospheric sources, not ROI/spot/PointSource/HomogeneousBeam | `PASS` | All 8 active source cards contain 20 `FarFieldAreaSource` beams each, point to the active-csi-collar setup, and contain no `ROI`, `PointSource`, or `HomogeneousBeam`; verified by source-card audit command in this completion pass. |
| Window/signal gap not smaller than Laue focused spot | `PASS` | Focused EventList replay stores `37194/37194`; side-Compton/FoV pass ratio active/current is `1.00368`, so the candidate does not clip the current focused W2 signal in the Step05-like replay; see `prompt511_active_csi_collar_focus_smoke_summary.json`. |
| Geometry overlap/load sanity | `PASS_WITH_BOUNDARY` | `overlap_active_csi_collar.log` loads the geometry and completes validation; no retained `GeomVol`, overlap, `G4Exception`, fatal, or error diagnostic was found. The only warning is the expected proxy warning: no native trigger criteria. |
| Atmospheric prompt smoke ran after repair | `PASS` | High-stat prompt-only channel runs passed for e+ (`4/4`, `974908` generated), n (`16/16`, `15409056` generated), and mu+ (`80/80`, `928400` generated), all with no DAT because isotope store was disabled. All-particle gross prompt smoke also passed (`16/16`, `1380258` generated), with L1-like total `0 cps`; see run summaries and `prompt511_active_csi_collar_allparticle_smoke_l1_proxy_summary.json`. |
| Activation nuclides recorded | `PASS` | Isotope-store smoke `runs/active_csi_collar_buildup_isotope_g1m_r2` passed `16/16`, produced `16` DAT files and `1380258` generated particles. Added collar RP rows: `22`; added total value: `198`; top added nuclides: `Cs-134`, `I-128`, `Sb-119`, `Sn-113`, `I-121`, `Te-123`, `Cs-127`; see `prompt511_active_csi_collar_isotope_smoke_summary.json`. |
| Preserve low-delay advantage within requested non-delayed scope | `PASS_WITH_BOUNDARY` | Delay-risk audit uses existing isotope DAT, RPIP div/mean-TT convention, local NUBASE half-lives, and local Geant4 W1/511 line scanner. Added collar day-15 activity estimate: `2.3367416673951054 Bq`, `2.7286686434564243%` of current v3p5 fixed-source total and `3.371636091380706%` of current CsI activity. W1 line-rate proxy: `0.007477169638556496 Bq-equiv`. This supports low-delay risk, but is not delayed transport or day-20 rate authority. |
| Avoid BGO/material-control detour | `PASS` | Active branch is CsI-on-CsI geometry; BGO remains only a material-control branch per `core_md/HANDOFF_20260617.md` and is not used in this candidate. |
| Do not promote paper/mission authority | `PASS` | Manifest claim level is `PROMPT511_ACTIVE_CSI_COLLAR_DESIGN_SMOKE_NO_RATE_AUTHORITY`; review explicitly says not to promote to paper/mission authority and lists delayed-source rebuild plus Step05/06/07/08 as future authority checks only. |
| Multiple subagent/loop-engineering involvement | `PASS` | This thread used independent subagents for constraint guarding, route selection, and active-collar evidence audit before this completion pass. The current completion pass also spawned two explorer agents for constraint and deliverable audit; their final notes are external conversation-level evidence, not repo-local simulation artifacts. |

## Boundaries

- This closes the user-requested prompt/isotope smoke-stage geometry-repair
  objective. It does not close a new paper-facing rate authority.
- The active-CsI collar uses Step05-like proxy handling, not native MEGAlib
  Trigger/Veto authority.
- The delay-risk audit is an isotope/activity and local decay-line risk screen.
  It is not a delayed-source rebuild, delayed transport, day-20 rate, or
  sensitivity result.
- The stale `0.0773771 cps` e+ value remains excluded because it comes from a
  file-glob/normalization mismatch in the retained `cli_seed` run.

## Next Authority Work, If This Candidate Is Promoted Later

1. Build the delayed source for the active-CsI-collar geometry.
2. Run delayed transport.
3. Re-run the common Step05/06/07/08 chain with prompt, delayed, and focused
   signal on the same production branch.

Those steps are outside the user-limited prompt plus isotope-recording scope of
this goal.

# CC 4.8 Review Prompt

Review this local project deeply but token-efficiently:

```text
/home/ubuntu/codex_tes_511_sim/new_geo_re
```

Do not edit files. Do not run large Cosima simulations. Use only lightweight inspection commands such as `rg`, `sed`, `jq`, `python` JSON readers, `ls`, and `find`. Do not paste large file contents. Cite evidence with file paths and line numbers.

## Goal

Find real technical risks that could affect the physics or analysis conclusion: geometry/window mismatches, stale paths, wrong normalization, delayed-source errors, active-shield/BGO veto errors, Poisson time-axis mistakes, Compton/FoV logic mistakes, or docs disagreeing with code.

## Read First

```text
README.md
MEMORY.md
workflow.md
stepwise_maintenance/CURRENT_PROGRESS_STEP_BREAKDOWN.md
```

## Step Docs

```text
stepwise_maintenance/step01_geo/README.md
stepwise_maintenance/step02_raw_background_simulation/README.md
stepwise_maintenance/step03_delay_source/README.md
stepwise_maintenance/step04_opticsim/README.md
stepwise_maintenance/step05_veto_time_axis/README.md
```

## Key Code

Inspect only relevant ranges:

```text
code/geometry/GenerateGeo_ADR_v4c_mkflange.py
code/tools/build_cm_geometry.py
code/tools/make_day15_report_ADR.py
code/tools/make_complete_day15_report_ADR.py
stepwise_maintenance/step03_delay_source/code/build_step03_delay_source_audit.py
```

## Key Outputs

```text
outputs/geometry/XZTES_ADR_v4c_mkflange_cm/bounds.json
stepwise_maintenance/step03_delay_source/outputs/delay_source_audit.json
outputs/reports/science_511_ADR_100k/science_511_100k_summary.json
outputs/reports/day15_complete_report/complete_day15_summary.json
```

## Checks

Geometry:
- Be window radius/thickness/z, Nb/4K/50K windows, and cavity apertures match docs and `bounds.json`.
- Vacuum jacket has only the Be window.
- A4K/Cryoperm is absent.
- No cm/mm or old coordinate-scale mismatch.

Step02/03:
- All production paths point to `step02_*_aligned`.
- Event counts, delayed source blocks, activity, and ground-state fix numbers are consistent across docs and JSON.
- Delayed source uses RPIP/profile spatial support, not an unintended uniform prior.
- `no_rpip` and unknown-isotope caveats remain explicit.

Step04:
- It is clearly only reused temporary Laue evidence/scaffold.
- It does not claim detailed mechanical Laue design or a fresh detector-coupled EventList bridge.
- It does not use channel optics.

Step05:
- `make_complete_day15_report_ADR.py` uses correct prompt/delayed/science paths.
- Delayed observation time comes from `cosima_delayed_transport_1m.log`.
- Coincidence window is `1e-6 s`.
- Active veto threshold is `50 keV`.
- Volume names containing `BGO`, `ACTIVE_SHIELD`, or `CEBR3` are counted as active-shield/BGO veto.
- Active-shield/BGO veto sums over the time-window candidate group, not only one original event.
- Compton/FoV runs on TES hits aggregated over the same candidate group.
- Be-window disk is still the Compton/FoV reference, not the Laue spot.
- Direct expectation vs Poisson timeline relationship is reasonable.

Docs:
- No stale `*_ADR_cmfix`, old 2602, old delay-fix, `cosima_full1m`, or `1094 s` claims remain unless explicitly labeled legacy.
- Step02 says no veto; Step05 says veto is included. These boundaries should not conflict.

## Output Format

Use exactly this structure:

```text
1. Executive Summary
Max 8 lines. Say whether the project is internally consistent and name the largest risk.

2. Findings
Only real issues, ordered Critical / High / Medium / Low.
For each:
- Severity:
- File/line:
- Evidence:
- Why it matters:
- Suggested fix:
- Confidence:

3. Non-Issues / Confirmed Correct
5-10 important confirmed-correct points, especially geometry, active-shield/BGO, Poisson, and Compton/FoV.

4. Questions
Only blockers; max 5.

5. Minimal Next Actions
Max 8, priority ordered.
```

If evidence is missing, label it as an assumption. Do not invent facts.

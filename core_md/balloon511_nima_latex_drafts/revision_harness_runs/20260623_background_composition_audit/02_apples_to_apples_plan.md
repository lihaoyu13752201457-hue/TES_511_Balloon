# Apples-To-Apples Comparison Plan

INDEPENDENCE = SINGLE_SESSION_DEGRADED
ROLE = Orchestrator
SCOPE = comparison protocol only; no physics/gate verdict is made here.

## Contract Guardrails

- Old `new_geo_re` is a historical 1/10 screen target only; it is not a full-stat promotion bar. Evidence: `core_md/fix5_benchmarks.json:13-17` and `/decision_bar`.
- Any pass/fail comparison to old `new_geo_re` requires benchmark alignment decision `ALIGNED`. Evidence: `core_md/fix5_benchmarks.json:37-52`, `/required_artifacts/benchmark_alignment`.
- Current promotion bar is v3p5 current authority, not old `new_geo_re`. Evidence: `core_md/fix5_benchmarks.json:99-113`, `/benchmarks/v3p5_current_authority`.
- Delayed claims require NUBASE ground-state correction, per-family TT division guard, and M-sampling inventory audit. Evidence: `core_md/METHOD_FIX5_SIM_CLOSURE.md:73-110` and `core_md/fix5_benchmarks.json:188-203`.

## Dimensions To Compare

| Dimension | Levels | Handling rule |
|---|---|---|
| Energy/window | all/100--10000, broad 480--550, W1 design passband, W2 `510.58--511.42 keV` | Never compare broad 480--550 directly to W2 as if equal. If no current same-window value exists, mark `NOT_AVAILABLE`. |
| Stage | raw, active-veto/scintillator, Compton-FoV, both/final | Map old `scintillator` to active-shield veto only; map old `both` to active-shield plus Compton/FoV. Map current `side_compton_fov_pass` to final only after checking window and stream definitions. |
| Stream | prompt, delayed, science, mixed | Keep prompt/delayed pure-stream decompositions separate from timeline mixed candidates. Report mixed only if source table provides it. |
| Value | cps, selected events, effective N, relative uncertainty | Include selected event counts and Poisson uncertainty where available; if old table only has effective catalog events, label it as such. |
| Normalization | prompt TT/exposure, delayed Bq/TE/decays, source surface/solid angle | Do not treat old and current source surfaces as aligned unless benchmark artifact proves it. Current fix5 uses 60 cm full-sphere far field; old review log records 35 cm far-field. |

## Primary Matrix Rows For Artifact 03

1. Old `new_geo_re` day15 broad 480--550, expectation final, prompt/delayed/science: source `complete_day15_summary.json` `/expectation_rates_by_stream_cps`.
2. Old `new_geo_re` day15 broad 480--550, component table total and ActivationDelay(day15): source `image8_like_component_rates_with_science.csv` rows 8--10.
3. Old `new_geo_re` Step09 W1 design passband, raw/scintillator/Compton-FoV/both, prompt/delayed: source `non_xray_background_w1_w2_veto_table.csv` rows 2--5.
4. Old `new_geo_re` Step09 W2 `510.58--511.42 keV`, raw/scintillator/Compton-FoV/both, prompt/delayed: source `non_xray_background_w1_w2_veto_table.csv` rows 6--9.
5. Current fix5 Step05 broad 480--550, raw/active-veto/final, prompt/delayed/science: source current Step05 summary `/windows/broad_480_550/by_stream` and rates CSV rows 2--10.
6. Current fix5 Step05 W2 `510.58--511.42 keV`, raw/active-veto/final, prompt/delayed/science: source current Step05 summary `/windows/w2_510p58_511p42/by_stream` and rates CSV rows 11--19.
7. Current fix5 vs v3p5 promotion-bar comparison: source `fix5_promotion_decision.json` `/comparison_vs_v3p5`; source `fix5_benchmarks.json` `/benchmarks/v3p5_current_authority`.
8. Old `new_geo_re` report-only benchmark comparison: source `fix5_benchmarks.json` `/benchmarks/new_geo_re`; source current `fix5_benchmark_alignment.json` `/decision`.

## Primary Normalization Rows For Artifact 04

1. Old `new_geo_re` prompt normalization: read `complete_day15_summary.json` `/normalization/prompt_time_s`; read review log prompt far-field source-surface note at `/home/ubuntu/codex_tes_511_sim/new_geo_re/CC48_REVIEW_LOG.md:82`.
2. Old `new_geo_re` delayed source/activity: read `complete_day15_summary.json` `/delay_fix`; read activation inventory grouped by `nuclide` and `VN` from `activation_inventory_day15_after_groundstate_fix.csv`.
3. Current fix5 prompt normalization: read Step05 summary `/normalization/prompt_normalization_audit`; read source normalization audit `/source_classes/0/source_plane`.
4. Current fix5 delayed source/activity: read `fix5_groundstate_half_life_audit_summary.json` `/checks`; read `normalization_audit_groundstate_fix.json` `/rows`; read `fix5_delayed_source_exactpos_summary.json` `/fixed_total_activity_Bq`, `/sampling_audit`, `/activity_slices`, `/delayed_transport`.
5. Current fix5 W/collimator selected-rate audit: read `fix5_w_activation_selected_w2_audit.json` `/checks` and event table rows.
6. Current fix5 delayed convergence: read `delayed_selected_rate_convergence.json` `/combined` and `/between_sampling_check`.

## Hypothesis Categories For Artifact 05

- `DEFINITION_ONLY`: window/stage/source-stream differences such as old broad 480--550 final versus current W2 final.
- `PHYSICAL_MODEL_DIFFERENCE`: material/geometry/veto/source-position differences such as old CsI active-shield I-128 dominance versus current exact-position selected origins.
- `STATISTICAL_LIMITATION`: selected delayed/prompt event counts and relative uncertainty limits.
- `STALE_OR_PROVENANCE_RISK`: old source-surface and selection equivalence is unverified; old benchmark alignment is `NOT_ALIGNED` until proven otherwise.
- `PROBABLE_BUG`: only if a concrete source/header/formula/unit mismatch is supported by file/field/line evidence and independently identified by at least two roles.

## No-Shortcut Rules

- Do not use `delayed < 0.1515 cps` as a meaningful current delayed pass; it is only a loose historical screen and report-only without benchmark alignment.
- Do not promote current fix5 because it is close to old `new_geo_re`; use v3p5 current authority and promotion decision fields.
- Do not compare current full-stat W2 selected delayed to old broad 480--550 final delayed without labeling the window and stage mismatch.
- Do not infer a bug merely because old `new_geo_re` delayed is large; first trace activity inventory, selection/veto, source-surface normalization, and exact-position sampling.

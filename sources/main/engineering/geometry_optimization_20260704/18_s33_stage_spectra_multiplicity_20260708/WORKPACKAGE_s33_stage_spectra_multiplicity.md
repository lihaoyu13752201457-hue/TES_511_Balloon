# Work package — §3.3 stage-wise spectra + hit-multiplicity split (for paper figures)

**Author:** Claude (harness). **Executor:** Codex. **Date:** 2026-07-08.
**Consumer:** balloon511 EA draft §3.3 (Detector event selection and veto definitions),
subsections 3.3.1 / 3.3.2 / 3.3.3. Claude will build the matplotlib figures from your
CSV/JSON outputs; you only produce the data.

## Why
The paper §3.3 cut-flow table (`tab:phase2_cutflow`, fix5 authority: prompt 161→60→54,
delayed 54→33→30, signal 30323→30323→29715) has **only aggregate counts**, no per-energy
spectrum and no 2-hit-vs-3+-hit split. The fix5/v3p5-centerfinger **prompt/delayed `.sim`
source has been cleaned** from the workspace, so those exact catalogues cannot be re-parsed.
The user has decided (explicitly) to **re-derive the spectra + multiplicity split from the
surviving `Mass_model_511_fullstat_v1` `.sim` catalogues**, accepting that this is a
different geometry lineage than the locked fix5 numbers. Every output MUST be labelled
`Mass_model_511_fullstat_v1` lineage so the paper figure captions can state
"shape-diagnostic; rates authoritative in the fix5 cut-flow table."

## Hard constraints (HONOR — do not soften)
- **REUSE existing classification code; do NOT reinvent** the window/active-veto/Compton
  logic. The driver `old/code/tools/build_v3p5_centerfinger_step05_l1_response.py` already
  loads each `.sim` into a per-event catalogue and calls `summarize_window(...)`, which
  imports `classify_compton` (8+1 pixel points, 81 trajectories, side Be-disk test) from
  `old/code/tools/make_day15_report_ADR.py`. Import/adapt these; keep the SAME
  `active_veto_threshold_keV=50`, `coincidence_window_s=1e-6`, `reject_policy='keep'`,
  and the SAME two windows.
- **Do NOT run Geant4/Cosima/revan.** This is pure post-processing of existing `.sim.gz`.
- **Do NOT overwrite any fix5/v3p5/authority output** (nothing under `stepwise_maintenance/`,
  `old/reports/`, `core_md/`). Write ONLY into this work-package directory:
  `engineering/geometry_optimization_20260704/18_s33_stage_spectra_multiplicity_20260708/`.
- **Sandbox is read-only** for you: emit a single self-contained Python script into this
  dir; Claude/the user will run it locally. If you can run it, run it; otherwise leave the
  script + a run command.

## Inputs (exact paths, all relative to repo root `/home/ubuntu/TES_511_Balloon`)
- PROMPT_DIR = `runs/Mass_model_511_nearfield_migration_20260701/step02_instant_candidate_Mass_model_511_fullstat_v1/` (68 `*.sim.gz`)
- DELAYED_SIM = the single `*.sim.gz` in `runs/Mass_model_511_nearfield_migration_20260701/step02_delayed_transport_candidate_Mass_model_511_fullstat_v1/`
- SCIENCE_SIM = prefer a Mass_model_511 full-stat optics signal sim if one exists; the only
  Mass_model_511 signal found is SMOKE
  (`runs/Mass_model_511_nearfield_migration_20260701/step09_focus_candidate_Mass_model_511_Mass_model_511_smoke/Opticsim_laue_f10m_a1_candidate_Mass_model_511_Mass_model_511_signal_smoke.inc1.id1.sim.gz`).
  If only smoke is available, ALSO produce the signal spectrum from the full-stat v3p5 optics
  sim `old/runs/step09_optics_bridge/Opticsim_laue_f10m_a1_v3p5_centerfinger.inc1.id1.sim.gz`
  and label each signal curve with which sim it came from. Reuse the driver's science
  normalization if convenient, but the SHAPE is what matters here.
- Geometry/disk (Be side-window) params: take from the same source the driver uses
  (`side_window_look_elevation_deg≈45`, Be disk radius 1.898 cm). Match `classify_compton`'s
  current side-entry tilt handling.

## Deliverables (exact filenames, into the work-package dir)
1. `s33_stage_spectra_480_550.csv` — broad-window (480–550 keV) energy spectrum, bin width
   **0.5 keV** (140 bins). Columns:
   `energy_lo_keV,energy_hi_keV,energy_center_keV,` then for each stream in
   {prompt,delayed,signal} and each stage in {raw, active (post-anticoincidence),
   compton (post-active AND passing Compton/FoV)}:
   `<stream>_<stage>_cps_per_keV` (physical cps/keV, using the driver's per-stream rate
   normalization) AND `<stream>_<stage>_events_per_bin` (raw event counts). 18 stream×stage
   data columns of each kind. "raw" = in-window, pre-veto; "active" = passes 50 keV shield
   gate; "compton" = active AND Compton/FoV-consistent (i.e. the final selected set,
   unreconstructed-retained per `reject_policy='keep'`).
2. `s33_multiplicity_split.json` — for the **w2 window (510.58–511.42 keV)** AND for the
   broad window, per stream, the candidate-event counts split by TES hit multiplicity
   bucket {`n1` (single-pixel), `n2` (two-hit), `n3plus` (≥3-hit)} at each stage
   {raw, active, compton}. Also give, within the multi-hit (≥2) events, how many are
   Compton-FoV `keep` vs `veto` vs `reject_kept`, split by n2 / n3plus. This is the data for
   "2-hit candidate count" and "3+hit candidate count" in §3.3.3.
3. `s33_manifest.json` — records: geometry lineage string `Mass_model_511_fullstat_v1`, the
   exact sim inputs used per stream, code modules reused, window defs, bin width, per-stream
   total raw/active/compton event counts and rates, and a one-line diff note comparing your
   w2 totals to the fix5 cut-flow (161/54/30323 raw) so Claude can sanity-check magnitude.
4. `build_s33_stage_spectra.py` — the self-contained script that produced 1–3 (re-runnable).

## Acceptance (DONE contract — all must hold)
- Files 1–4 exist in the work-package dir and parse (CSV has header + 140 rows; JSON loads).
- Per-stream, the sum over the w2-window `compton`-stage multiplicity buckets equals the
  w2 `compton`-stage total, and single ≤ raw for every stream (monotone veto).
- `s33_manifest.json` states the lineage is `Mass_model_511_fullstat_v1` (NOT fix5) and lists
  the actual event totals. Print those totals to stdout at the end.
- No file outside the work-package dir is created or modified.

Report back: the per-stream w2 raw/active/compton totals, the 2-hit vs 3+hit counts per
stream, and the paths of the four deliverables.

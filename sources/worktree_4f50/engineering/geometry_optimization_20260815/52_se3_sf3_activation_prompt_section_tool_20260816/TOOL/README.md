# Reusable detailed-section TOOL

## Run

From the repository root:

```bash
python3 engineering/geometry_optimization_20260815/52_se3_sf3_activation_prompt_section_tool_20260816/TOOL/build_activation_prompt_sections.py
```

The default run is self-contained and reads only [`inputs/`](inputs/). It does not open SIM
payloads, start transport, or compute large-payload hashes. The script fails if the SE3 rate
reaggregation, MXC reference, SF3 event count, W-region classification, or active-veto-zero
contract drifts.

Alternative compact inputs can be supplied with:

```text
--se3-origins CSV
--se3-volume-report CSV
--se3-parent-report CSV
--se3-family-report CSV
--se3-mesh NPZ
--sf3-routes JSON
--output DIRECTORY
--audit JSON
```

## What the code reuses

- The exact native-mesh `y'=0` triangle/plane section method comes from the validated SE3
  `build_se3_visuals.py`; its minimal read-only subset is vendored as
  [`se3_section_adapter.py`](se3_section_adapter.py).
- IA parent/child track construction and process-marker semantics follow the earlier detailed
  `build_prompt511_track_interaction_figure.py` implementation.
- SF3 coordinate conversion, axial-radius definition, and exact passive-W membership come from
  `build_sf3_background_routes_2d.py`.

The audit records those source paths as provenance, but they are not runtime dependencies.

## Figures

- `se3_activation_sf3_prompt_global_detailed_section.*`: complete instrument-frame section.
- `se3_activation_sf3_prompt_local_nearfield_section.*`: local near-field enlargement with
  prompt routes and V2A/V2B proposal-only ROIs.
- `se3_activation_sf3_prompt_axial_radius.*`: true radial W-membership diagnostic; use this view
  when an `x'-z'` projection appears outside the `y'=0` W outline.

Figure conventions:

- colored circles are SE3 delayed-W2 contributing activation source positions; marker area
  follows selected cps;
- black outer rings mark MXC source points;
- colored lines are the three SF3 prompt survivors and symbols are IA processes;
- gray hatching is SF3 passive W, **not** an active veto;
- magenta/purple dashed boxes are proposal regions, not implemented solids.

The exact mesh is a `y'=0` section, while source and route markers are projected from their true
3D positions. Therefore axial-radius is the authoritative view for side-sleeve/front/rear W
membership.

## Tables and report

- `activation_nuclide_stats.csv`
- `activation_volume_stats.csv`
- `activation_incident_family_stats.csv`
- `activation_plot_points.csv`
- `sf3_prompt_event_routes.csv`
- `sf3_prompt_process_regions.csv`
- `optimization_summary.json`
- `ANALYSIS_REPORT.md`
- `audit/tool_validation.json`

The activation points represent sources of the selected delayed W2 rate, not every atom in the
full activation inventory. SF3 prompt statistics are three-event mechanism evidence, not a
full-stat rate authority.

## Physics/optimization boundary

No result here promotes a geometry. Any V2 candidate still requires:

1. corrected-keV prompt;
2. candidate-owned activation/inventory and actual-position delayed transport;
3. the independent 37,194-ray focused-signal sample;
4. shared response, active-veto policy, and Step05;
5. the 81-node / 20-day F3 comparison.

Mono-511 remains disabled, passive W is never counted as veto, SF3 is not full-stat, and no final
optimal geometry currently exists.

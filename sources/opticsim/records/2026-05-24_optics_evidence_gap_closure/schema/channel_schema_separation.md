# Channel schema separation validation

- calibrated_summary: `runs/channel/geant4_4ring_multibounce_schema_smoke/summary.json`
- wallbywall_summaries: `['runs/channel_wallbywall_schema_smoke/summary.json', 'runs/channel_wallbywall_roughness_sweep/summary_roughness_0p0nm.json', 'runs/channel_wallbywall_roughness_sweep/summary_roughness_0p2nm.json', 'runs/channel_wallbywall_roughness_sweep/summary_roughness_0p5nm.json', 'runs/channel_wallbywall_roughness_sweep/summary_roughness_1p0nm.json', 'runs/channel_wallbywall_roughness_sweep/summary_roughness_2p0nm.json', 'runs/channel_wallbywall_roughness_sweep/summary_roughness_5p0nm.json', 'runs/channel_wallbywall_roughness_sweep/summary_roughness_10p0nm.json']`
- summary_json: `records/2026-05-24_optics_evidence_gap_closure/schema/channel_schema_separation.json`
- overall_status: **PASS**

## Calibrated Handoff

| field | value |
|---|---|
| model_class | `calibrated_detector_handoff` |
| is_calibrated_handoff | `True` |
| is_public_wallbywall_geometry | `False` |
| is_first_principles_80pct_closure | `False` |
| transmissivity | `0.813` |
| errors | `[]` |

## Public Wall-By-Wall

| path | model_class | calibrated | public_wallbywall | first_principles_80pct | transmissivity | errors |
|---|---|---|---|---|---:|---|
| `runs/channel_wallbywall_schema_smoke/summary.json` | `public_geometry_wallbywall_reconstruction` | `False` | `True` | `False` | 0.3 | `[]` |
| `runs/channel_wallbywall_roughness_sweep/summary_roughness_0p0nm.json` | `public_geometry_wallbywall_reconstruction` | `False` | `True` | `False` | 0.3773 | `[]` |
| `runs/channel_wallbywall_roughness_sweep/summary_roughness_0p2nm.json` | `public_geometry_wallbywall_reconstruction` | `False` | `True` | `False` | 0.37505 | `[]` |
| `runs/channel_wallbywall_roughness_sweep/summary_roughness_0p5nm.json` | `public_geometry_wallbywall_reconstruction` | `False` | `True` | `False` | 0.37095 | `[]` |
| `runs/channel_wallbywall_roughness_sweep/summary_roughness_1p0nm.json` | `public_geometry_wallbywall_reconstruction` | `False` | `True` | `False` | 0.3659 | `[]` |
| `runs/channel_wallbywall_roughness_sweep/summary_roughness_2p0nm.json` | `public_geometry_wallbywall_reconstruction` | `False` | `True` | `False` | 0.3558 | `[]` |
| `runs/channel_wallbywall_roughness_sweep/summary_roughness_5p0nm.json` | `public_geometry_wallbywall_reconstruction` | `False` | `True` | `False` | 0.2963 | `[]` |
| `runs/channel_wallbywall_roughness_sweep/summary_roughness_10p0nm.json` | `public_geometry_wallbywall_reconstruction` | `False` | `True` | `False` | 0.16705 | `[]` |

## Interpretation

- The calibrated handoff schema is explicitly separate from public wall-by-wall reconstruction schema.
- Both schemas set `is_first_principles_80pct_closure=false`.
- This check does not tune or compare public wall-by-wall transmission to 0.80; it only prevents semantic mixing.

# Channel wall-by-wall roughness systematic sweep

- config: `config/cam511_channel_baseline.yaml`
- n_per_roughness: 20000
- roughness_nm: `[0.0, 0.2, 0.5, 1.0, 2.0, 5.0, 10.0]`
- run_dir: `runs/channel_wallbywall_roughness_sweep`
- summary_csv: `records/2026-05-24_optics_evidence_gap_closure/channel/channel_wallbywall_roughness_sweep_summary.csv`
- per_ring_csv: `records/2026-05-24_optics_evidence_gap_closure/channel/channel_wallbywall_roughness_sweep_per_ring.csv`
- grazing_hist_csv: `records/2026-05-24_optics_evidence_gap_closure/channel/channel_wallbywall_roughness_sweep_grazing_hist.csv`
- summary_json: `records/2026-05-24_optics_evidence_gap_closure/channel/channel_wallbywall_roughness_sweep.json`

## Summary

| roughness_nm | T | Aeff_cm2 | spot_d90_cm | event-weighted R | bounce-weighted R | theta_p90_rad | schema | first-principles 80% |
|---:|---:|---:|---:|---:|---:|---:|---|---|
| 0.0 | 0.3773 | 24.0028 | 1.04523 | 0.985902 | 0.99495 | 0.000141794 | `public_geometry_wallbywall_reconstruction` | `False` |
| 0.2 | 0.37505 | 23.8597 | 1.03787 | 0.985425 | 0.994754 | 0.000142175 | `public_geometry_wallbywall_reconstruction` | `False` |
| 0.5 | 0.37095 | 23.5988 | 1.05207 | 0.985757 | 0.994857 | 0.000141298 | `public_geometry_wallbywall_reconstruction` | `False` |
| 1.0 | 0.3659 | 23.2776 | 1.03831 | 0.982344 | 0.994208 | 0.000141269 | `public_geometry_wallbywall_reconstruction` | `False` |
| 2.0 | 0.3558 | 22.635 | 1.04165 | 0.97819 | 0.992836 | 0.000141011 | `public_geometry_wallbywall_reconstruction` | `False` |
| 5.0 | 0.2963 | 18.8498 | 1.03426 | 0.97253 | 0.985323 | 0.000138483 | `public_geometry_wallbywall_reconstruction` | `False` |
| 10.0 | 0.16705 | 10.6273 | 1.03489 | 0.929754 | 0.958826 | 0.00013405 | `public_geometry_wallbywall_reconstruction` | `False` |

## Interpretation

- This sweep changes W/Si roughness in the public-geometry wall-by-wall line and reports the resulting detector-handoff observables.
- It is not calibrated against the 0.80 handoff line and does not tune transmission toward 0.80.
- `event-weighted R` is the mean per-event bounce-reflectivity average for events with at least one reflected bounce; `bounce-weighted R` is the mean over all bounce rows.
- Grazing-angle histograms are in the companion CSV and use per-roughness fixed-width bins from 0 to that run's maximum bounce grazing angle.
- External IMD/DarpanX/CXRO/Henke provenance remains open; this uses the local xraydb/manual-Parratt backend.

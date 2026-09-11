# SH3 open vs W-grid mono-511 static report generator

This folder contains a read-only analysis/report step. It does **not** run
Cosima, modify geometry, combine broadband components, update activation, or
calculate total background/Fmin.

## Preferred input contract

Use JSON for the comparison authority:

```json
{
  "schema_version": 1,
  "metadata": {
    "data_status": "actual",
    "line_energy_keV": 510.99895,
    "parma_day15_full_space_flux_ph_cm2_s": 0.16651547160226118,
    "angular_components_equal_mu": 80,
    "common_parma_source": true,
    "common_response_selection_time": true,
    "independent_mc_samples": true,
    "window_id": "w2_510p58_511p42",
    "source_fragment_sha256": "...",
    "source_contract_sha256": "...",
    "line_transport_contract_sha256": "..."
  },
  "open_frame": {
    "label": "SH3 开放框",
    "geometry_id": "...",
    "incident_photons": 15709417,
    "physical_exposure_s": 8343.62808,
    "selected_events": 186,
    "effective_selected_events": 186,
    "rate_cps": 0.02229246057190028,
    "sigma_cps": 0.0016345625147982216
  },
  "w_grid": {
    "label": "SH3 + W-grid",
    "geometry_id": "...",
    "incident_photons": 15709417,
    "physical_exposure_s": 8343.62808,
    "selected_events": 0,
    "effective_selected_events": 0,
    "rate_cps": 0.0,
    "sigma_cps": 0.0
  }
}
```

The final W-grid values above are placeholders and must be replaced by the
completed matched run. Existing `summary.json` key aliases such as
`w2_final_rate_cps` are also accepted.

A comparison CSV is accepted when it contains one `role=open_frame` row and
one `role=w_grid` row, all model fields shown above, and the metadata fields
repeated on each row. Missing physical metadata is rejected by default. The
explicit `--allow-metadata-defaults` option exists only for controlled recovery
and records every inserted value as a warning.

The two cut-flow files should use the existing columns:

```text
model,window_id,stage,selected_events,event_weight_cps,weighted_rate_cps,weighted_mc_sigma_cps,effective_selected_events
```

For `w2_510p58_511p42`, all five stages must be present. Each bin-80 file must
contain exactly bins 0--79 with columns:

```text
source_bin80,selected_events,weighted_rate_cps
```

The script requires exact matched incident counts and the same PARMA source
normalization. Independent Cosima source realizations retain their own
observation times and `1/sum(T)` event weights; their exposures must agree
within the frozen 0.2% sanity band, not bit-for-bit. It also checks
that each bin-80 sum closes to the final cut-flow count/rate and that the final
cut-flow closes to the comparison authority.

## Actual-data invocation

Use a fresh output directory; the script refuses to overwrite any generated
artifact.

```bash
python3 build_mono511_report.py \
  --comparison /absolute/path/comparison.json \
  --open-cutflow /absolute/path/open_cutflow.csv \
  --grid-cutflow /absolute/path/grid_cutflow.csv \
  --open-bins /absolute/path/open_bin80.csv \
  --grid-bins /absolute/path/grid_bin80.csv \
  --output-dir /absolute/path/new_report_output
```

Outputs:

- `mono511_open_vs_wgrid.png`
- `mono511_open_vs_wgrid.pdf`
- `mono511_technical_report_zh.md`
- `mono511_report_data.json`
- `mono511_stage_ratios.csv`
- `qa_receipt.json`

## Synthetic smoke test

The fixture and its figure/report are visibly marked as synthetic, so they
cannot be mistaken for a physics result:

```bash
python3 build_mono511_report.py \
  --make-synthetic-fixture /tmp/wgrid_report_agent_20260825/synthetic_fixture
```

## Uncertainty convention

The final and stage ratios use independent-sample first-order propagation:

```text
R = rate_grid / rate_open
sigma_R^2 = (sigma_grid / rate_open)^2
          + (rate_grid * sigma_open / rate_open^2)^2
```

The 80-bin normalized-shape total-variation distance is retained only as a
descriptive audit diagnostic because selected counts per angular component can
be sparse.

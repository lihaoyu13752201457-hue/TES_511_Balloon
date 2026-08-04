# S3c atmospheric-511 Knob0 event replay

Status: `PASS_S3C_ATM511_KNOB0_VALIDATION`  
Date: 2026-07-10

## Answer

The frozen Knob0 fluorescence/lever-arm policy provides no observed
atmospheric-511 benefit on the retained S3c 3M sample.

- Current W2 active-pass/final events: `8 / 6`.
- Literal brief policy (`S0/S1` always retained): `6 -> 7`, a `+16.7%`
  atmospheric-511 rate change. It resurrects current-veto event `30621`.
- Monotonic frozen policy: `6 -> 6`; no event changes for `k=2, 2.5, 3`.
- One of five W2 multihit events is a Ta Kalpha1-tagged event supported by the
  IA PHOT truth record, but it is already retained by the current selection.
- The only S3 long-arm event has `L=25.67 mm` and a cone-to-window residual of
  `0.000300 deg`, so it passes every frozen tight threshold.

Decision: do not promote the literal Knob0 rule for atmospheric-511. Retain
the current selection. This result does not test or rule out a separate
prompt/delayed application.

## Primary artifact

- `report/s3c_atm511_knob0_report.html`: self-contained technical report with
  interactive charts and same-data static fallbacks.

## Supporting evidence

- `data/s3c_atm511_knob0_summary.json`: definitions, data-quality profile,
  policy yields, uncertainty, validation gates, and decision.
- `data/s3c_atm511_w2_event_audit.csv`: all eight W2 active-pass events.
- `data/s3c_atm511_w2_event_truth.json`: aggregated TP hits plus retained CC and
  IA records for event-level audit.
- `data/s3c_atm511_knob0_policy_yields.csv`: current/literal/monotonic yields
  for all frozen `k` values.
- `data/s3c_atm511_knob0_transitions.csv`: paired event transition matrix.
- `data/s3c_atm511_low_hit_spectrum_1kev.csv`: diagnostic two-hit low-energy
  spectrum. It is intentionally not plotted because only four bins are
  populated.
- `data/s3c_atm511_lever_strata.csv`: two-hit lever-arm strata by scope.
- `data/s3c_atm511_knob0_chart_map.json`: chart contracts and omitted-chart
  rationale.

## Reproduce

The analysis is read-only and scans the retained 806 MB gzip SIM once. It does
not run Cosima or alter the retained S3c products.

```bash
python3 code/analyze_s3c_atm511_knob0.py
python3 code/build_atm511_knob0_report.py
python3 /home/ubuntu/.codex/plugins/cache/openai-curated-remote/data-analytics/0.2.6-d37358633e00/skills/build-report/scripts/embed_html_report_runtime.py \
  --input report/s3c_atm511_knob0_report_shell.html \
  --payload report/s3c_atm511_knob0_report_payload.json \
  --output report/s3c_atm511_knob0_report.html
node code/validate_atm511_knob0_report.mjs
python3 code/validate_s3c_atm511_knob0.py
```

The event scan takes roughly two minutes in the current workspace. The browser
validator writes QA screenshots to `/tmp` only.

## Statistical boundary

The monotonic rule rejected `0/6` current survivors, whose Wilson 95% interval
is `0-39.0%`. The result is therefore "no benefit observed in this sample",
not proof that the population rejection rate is exactly zero. Linear yield
scaling suggests about 17.5M total generated events would be needed for a zero-
rejection Wilson upper bound at or below 10%, or 36.5M for 5%.


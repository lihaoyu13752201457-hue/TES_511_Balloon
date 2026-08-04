# S3c mainline and lightweight review

Status: `PASS_S3C_MAINLINE_AND_LEGACY_CLEANUP`  
As of: 2026-07-10

This package consolidates S3c as the retained mainline design family after the
legacy S3/S3a/S3b simulation cleanup. No new transport was launched for this
review. The analysis reuses retained S3c prompt, atmospheric-511, and clean
neutron-only delayed products, plus compact frozen conclusion snapshots for
the deleted legacy branches.

## Decision

- Keep `S3c-C0` (BGO40 + W2 + Al3) as the measured performance reference, not
  as the only mainline geometry.
- Rehome the retained BGO40 + Al8 + no-W design point as `S3c-LW1` and make it
  the first lightweight promotion candidate.
- Screen `S3c-LW2` (BGO40 + Al5 + no W) next, followed by `S3c-LW3` as the
  mechanical lower-bound candidate.
- Test graded BGO only after the no-W/full-BGO candidates. The current
  ten-event direction proxy has eight side entries, so the first graded design
  keeps the side BGO at 40 mm.
- Keep LW5/LW6 exploratory until veto efficiency, focused-signal acceptance,
  delayed activation, and structure are demonstrated.

The current pre-relief mass is 391.20 kg: 325.35 kg BGO, 53.88 kg W,
11.39 kg Al, and 0.58 kg Kapton. LW1 is 356.57 kg, a 34.63 kg (8.85%)
reduction. LW1 has retained transport evidence: its historical
estimated 20-day F3 is 11.75% higher than C0, while its neutron-only delayed
activity is 45.85% lower. These are screening comparisons, not a final
publication-matched closure.

## Main artifact

- [Self-contained technical HTML report](report/s3c_lightweight_report.html)

The report includes source tooltips, three interactive Recharts views, and
same-data inline SVG fallbacks. It has no remote script, stylesheet, or sibling
image dependency.

## Evidence and reproducibility

- `data/s3c_mainline_analysis_summary.json`: decision-ready summary and claim
  boundaries.
- `data/s3c_w2_background_distribution.csv`: prompt/atm511 W2 composition.
- `data/s3c_final_event_entry_distribution.csv`: low-stat entry-surface proxy.
- `data/s3c_neutron_delayed_by_volume_class.csv`: neutron-only source-side
  activity distribution.
- `data/s3c_lightweight_candidates.csv`: mass/evidence trade space.
- `data/s3c_lightweight_run_matrix.csv`: staged promotion gates.
- `retained_conclusions/`: compact machine-readable conclusion snapshots that
  allow S3c comparisons without restoring deleted legacy simulations.
- [Cleanup audit](CLEANUP_MANIFEST.md): deletion scope and post-cleanup checks.

Rebuild the derived analysis and report from the retained artifacts:

```bash
python3 code/build_s3c_lightweight_analysis.py
python3 code/build_s3c_lightweight_report.py
python3 /home/ubuntu/.codex/plugins/cache/openai-curated-remote/data-analytics/0.2.6-d37358633e00/skills/build-report/scripts/embed_html_report_runtime.py \
  --input report/s3c_lightweight_report_shell.html \
  --payload report/s3c_lightweight_report_payload.json \
  --output report/s3c_lightweight_report.html
node code/validate_s3c_lightweight_report.mjs
python3 code/validate_s3c_mainline.py
```

`build_s3c_lightweight_analysis.py` scans the selected gzip SIM events and can
take about a minute. Both validators are read-only. The browser validator uses
the retained local headless Chrome and writes QA screenshots only to `/tmp`.

## Interpretation boundary

- The estimated total prompt background contains an S3-derived non-dominant
  residual; it is not yet a full S3c prompt-family closure.
- The final W2 component counts are small: e+ and neutron have two events each;
  atm511 has six. Treat their ordering as unresolved.
- Delayed activity is clean neutron-only source-side Bq, not detector-selected
  W2 cps.
- LW2 through LW6 masses are pre-relief bookkeeping estimates and are not
  structural qualification.

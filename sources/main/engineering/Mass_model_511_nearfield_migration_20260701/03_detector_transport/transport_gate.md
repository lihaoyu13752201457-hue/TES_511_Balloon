# Mass_model_511 G3/G4 Detector Transport Gate

generated_at_utc: `2026-07-01T16:13:24Z`
status: `PASS_G3_G4_DETECTOR_TRANSPORT_SMOKE`

- branches: `baseline_detector`, `candidate_Mass_model_511`
- source authority edited: `false`
- old nearfield engineering edited: `false`

## Prompt / Buildup

| Branch | Mode | Status | Jobs | Events requested | Events generated | Geometry headers |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `baseline_detector` | `instant` | `PASS` | 68 | 2521032 | 2521032 | 68/68 |
| `baseline_detector` | `buildup` | `PASS` | 68 | 2521032 | 2521032 | 68/68 |
| `candidate_Mass_model_511` | `instant` | `PASS` | 68 | 2521022 | 2521022 | 68/68 |
| `candidate_Mass_model_511` | `buildup` | `PASS` | 68 | 2521022 | 2521022 | 68/68 |

Note: baseline prompt/buildup were run with the shared equiv2602 runner and
landed 10 events above the planning matrix. Step05 normalization uses the
actual run summaries.

## Delayed

Evidence: `03_detector_transport/delayed_transport_campaign_manifest.json`

- ground-state normalization audit: `PASS` for available branch payloads
- M point-source blocks: `50000`
- seed: `260613`

| Branch | Stage | Status | SE | ID | TS | TE_s |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| `baseline_detector` | `S0` | `PASS_MASS_MODEL_511_BASELINE_DETECTOR_S0_SMOKE_EXACTPOS_DELAYED_TRANSPORT` | 100000 | 100000 | 1 | 1211.50624 |
| `baseline_detector` | `S1` | `PASS_MASS_MODEL_511_BASELINE_DETECTOR_S1_SMOKE_EXACTPOS_DELAYED_TRANSPORT` | 1000000 | 1000000 | 1 | 12051.496408 |
| `candidate_Mass_model_511` | `S0` | `PASS_MASS_MODEL_511_CANDIDATE_MASS_MODEL_511_S0_SMOKE_EXACTPOS_DELAYED_TRANSPORT` | 100000 | 100000 | 1 | 739.607401 |
| `candidate_Mass_model_511` | `S1` | `PASS_MASS_MODEL_511_CANDIDATE_MASS_MODEL_511_S1_SMOKE_EXACTPOS_DELAYED_TRANSPORT` | 1000000 | 1000000 | 1 | 7371.163696 |

## Focused Signal Transport

Evidence: `06_smoke_closure/signal_transport_manifest.json`

- status: `PASS_SIGNAL_TRANSPORT`
- triggers per branch: `37194`

## Log Scan

No matches in `.log` files for `G4Exception`, `***  Error`,
`Segmentation fault`, `Unable to parse`, or nonzero `returncode=`.

Boundary: this gate records transport/focused-signal artifacts. Step05
detector-response smoke closure is recorded under `06_smoke_closure/`. Full-stat
background/no-effect release and regenerated Step06--Step08 mission products
are not claimed.

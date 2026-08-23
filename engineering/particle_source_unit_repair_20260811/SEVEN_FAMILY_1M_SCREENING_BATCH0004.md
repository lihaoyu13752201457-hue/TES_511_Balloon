# Corrected-keV 1M-equivalent screening batch0004

Status: controller, validator, documentation, and tests implemented;
`--print-plan` passes while the required batch0003 predecessor authority is
still reported as `WAIT`. No batch0004 transport has been launched.

Batch0004 is a bounded, reduced-statistics non-proton checkpoint for
Mass_model_511 and S3d-O8. It is not the historical full-stat target. Gamma is
added only in activation-buildup mode because batch0003 supplies a separate
canonical instant-gamma prefix or stage5 sample. Alpha, electron, positron, negative muon, positive muon,
and neutron use independent instant and buildup campaigns. Every
geometry+mode+family remains a separate normalization domain.

## Exact cumulative targets and increments

The target is ten times the batch0001 flux-scaled exposure, conventionally
called 1M gamma-equivalent screening. Existing batch0000 and batch0001 credit
is deducted exactly. Batch0002 contributes 10,000 additional instant negative
muons per geometry, so that cell already has 10,105 histories and receives no
new transport.

| Family/mode | Prior per geometry | New per geometry | Cumulative target | Paired shards |
|---|---:|---:|---:|---:|
| gamma buildup | 101,000 | 899,000 | 1,000,000 | 35x25k + 24k |
| n instant | 9,727 | 86,583 | 96,310 | 17x5k + 1,583 |
| n buildup | 9,727 | 86,583 | 96,310 | 17x5k + 1,583 |
| eplus instant | 2,461 | 21,909 | 24,370 | 8x2.5k + 1,909 |
| eplus buildup | 2,461 | 21,909 | 24,370 | 8x2.5k + 1,909 |
| alpha instant | 241 | 2,149 | 2,390 | 8x250 + 149 |
| alpha buildup | 241 | 2,149 | 2,390 | 8x250 + 149 |
| eminus instant | 4,187 | 37,273 | 41,460 | 7x5k + 2,273 |
| eminus buildup | 4,187 | 37,273 | 41,460 | 7x5k + 2,273 |
| muplus instant | 117 | 1,043 | 1,160 | 1x1,043 |
| muplus buildup | 117 | 1,043 | 1,160 | 1x1,043 |
| muminus buildup | 105 | 935 | 1,040 | 1x935 |
| muminus instant | 10,105 | 0 | target 1,040 already exceeded | prior-only |

The new plan contains 127 paired ordinals, 254 Cosima jobs, and 2,395,698
new primaries. The fixed execution priority is gamma buildup, neutron,
positron, alpha, electron, then muons. Each family/mode publishes its own
write-once report and ledger before the next checkpoint begins. This allows a
completed prefix to remain auditable if the inherited deadline stops later
work.

Same-seed cross-geometry pairing is operational provenance only. Geometry
transport consumes random streams differently, so these shards do not support
a paired estimator, common-random-number variance reduction, or cross-geometry
raw-count pooling.

## Parent gate and inherited deadline

Transport is fail-closed until one explicit predecessor profile is frozen.
Selection is deterministic: prefer the canonical ordinal-76 prefix report and
ledger (`PARTIAL_PREFIX_MERGE_ELIGIBLE`, 2,001,000 cumulative instant-gamma
events per geometry); if that pair is absent, accept canonical batch0003
stage5. An incomplete or malformed pair fails rather than falling through.
The prefix publisher path and SHA-256 are pinned, and prefix consumption reads
only its canonical report and ledger—never batch0003 attempt directories.

Batch0004 inherits, rather than resets, the batch0003 state window:

- started: `2026-08-11T14:31:43.664883+00:00`;
- deadline: `2026-08-12T02:31:43.664883+00:00`;
- no new launch after T+8h;
- transport drains by T+9h;
- T+9h through T+12h is reserved for validation and authority publication.

The parent contract and actually selected report/ledger hashes, profile,
instant-gamma exposure, and full batch0003 planned-seed exclusion are frozen
into the actual batch0004 contract. Prefix instant exposure is never deducted
from gamma buildup or a non-gamma target. Stage5 retains its existing exact
read-only validator path; prefix76 is rechecked from canonical authority only.

## Resource envelope

The read-only plan uses actual batch0001 geometry+mode+family artifacts as its
calibration. At the current point estimate:

- output: 17,436,923,168 bytes (17.44 GB decimal);
- run phase: 24,828 s (6.90 CPU h);
- default workers: 4;
- absolute cap: 6, reachable only after at least eight signed shard RSS
  observations and a measured-memory gate;
- disk reserve: 20 GiB, not 20 GB decimal;
- 2x remaining-output gate plus the larger of active-attempt burst and a
  5.15 GB emergency margin;
- no automatic deletion of raw SIM, DAT, log, source, code, paper, or prior
  authority.

The successful plan snapshot saw 133.68 GB free and required 61.50 GB, so the
disk gate passed. These are point estimates, not guarantees: most non-gamma
cells have one small calibration job, and S3d-O8 gamma buildup has a large
rare-shower tail. Every active attempt therefore has a calibrated output cap,
a two-second disk/RAM watchdog, a 15-minute no-CPU plus no-growth hang rule,
same-seed retry, process-group cleanup, and input hashes before, during, and
after transport.

## Gamma buildup interpretation

Gamma buildup is not used for prompt/veto or prompt-only TES spectra. It is
required for activation/delayed work: the corrected 101k buildup sample has
nonzero gamma-induced isotope production in both geometries. The 1M target is
only a screening checkpoint; it does not provide isotope-volume-resolved
delayed authority. A later 5M buildup checkpoint and separate delayed
transport/response closure are still needed for quantitative delayed claims.

Buildup DAT and SIM are both retained. The delayed-source chain uses DAT rates
and SIM/RPIP position/volume provenance; an instant DAT cannot substitute for
`DecayMode ActivationBuildUp`.

## Commands

Read-only planning is output-free and never launches transport. It may invoke
Cosima `--help` only for fingerprinting. While batch0003 is incomplete, the
plan succeeds with an explicit `WAIT` dependency gate:

```bash
python3 engineering/particle_source_unit_repair_20260811/code/run_mergeable_seven_family_1m_screening_batch0004.py \
  --print-plan --workers 4
```

The following command is intentionally not run by harness preparation. It can
transport only after canonical prefix76 or stage5 is exact PASS and before the
inherited stop-launch time:

```bash
python3 engineering/particle_source_unit_repair_20260811/code/run_mergeable_seven_family_1m_screening_batch0004.py \
  --workers 4
```

Checkpoint and final read-only revalidation examples:

```bash
python3 engineering/particle_source_unit_repair_20260811/code/validate_mergeable_seven_family_1m_screening_batch0004.py \
  --stage gamma_buildup --check
python3 engineering/particle_source_unit_repair_20260811/code/validate_mergeable_seven_family_1m_screening_batch0004.py \
  --final --check
```

Canonical reports and ledgers are published only on PASS. Failed validation
writes no canonical authority and therefore cannot poison a later resume.

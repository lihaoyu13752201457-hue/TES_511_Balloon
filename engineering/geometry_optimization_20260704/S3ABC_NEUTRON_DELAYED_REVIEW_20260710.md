# S3a/S3b/S3c Neutron-Only Delayed Comparison - 2026-07-10

## Scope

This review covers the clean neutron-only delayed activation chains for the
three S3-derived geometry branches:

- S3a: CsI scintillator replaced by BGO; original 8 mm Al outer shell retained.
- S3b: CsI retained; 8 mm Al outer shell replaced by 2 mm W + 3 mm Al.
- S3c: S3a + S3b combined; BGO scintillator and 2 mm W + 3 mm Al shell.

Only the clean directories are review inputs:

- `engineering/geometry_optimization_20260704/36_s3a_neutron_delayed_chain_m50000_clean_20260710/`
- `engineering/geometry_optimization_20260704/37_s3b_neutron_delayed_chain_m50000_clean_20260710/`
- `engineering/geometry_optimization_20260704/38_s3c_neutron_delayed_chain_m50000_clean_20260710/`

The interrupted earlier directories `33_*`, `34_*`, and `35_*` are not review
inputs. Their partial outputs were left in place only as run-history evidence.

## Validation

Validator command:

```bash
python3 engineering/geometry_optimization_20260704/validate_s3abc_neutron_delayed_20260710.py
```

Result: `PASS_S3ABC_NEUTRON_DELAYED_REVIEW_INPUTS`.

Common statistics and normalization:

- transported activation driver: `Background_n_fullsphere20` only
- gamma source card retained only as the `run_equiv2602` flux normalization anchor
- buildup: 8 neutron replicate jobs, 7,704,528 generated events per branch
- fixed source: NUBASE ground-state correction applied
- per-family TT division guard: neutron family has 8 files, division 8, and 8 TT lines
- delayed source: M=50,000 exact-position point-source blocks
- delayed transport: 1,000,000 source events per branch

## Main Comparison

| Branch | Geometry delta from S3 | Fixed neutron-delayed activity (Bq) | Relative to S3a | Delayed transport TE (s) | Transport SE/ID | Main sampled delayed contributors |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| S3a | BGO + 8 mm Al shell | 31.308 | 1.00x | 30135.674 | 1,000,000 / 1,000,000 | Al-28 in supports/window, Ge-71/Ge-75 window, W-187 bottom plate, Cu-64 cold plates |
| S3b | CsI + 2 mm W + 3 mm Al shell | 99.895 | 3.19x | 9378.900 | 1,000,000 / 1,000,000 | I-128 in window/CsI, W-187 in window and W shell, Al-28 supports |
| S3c | BGO + 2 mm W + 3 mm Al shell | 57.824 | 1.85x | 14578.654 | 1,000,000 / 1,000,000 | W-187 in window/W shell, Al-28 supports, Ge-71/Ge-75 window, Cu-64 cold plates |

Activity ranking for neutron-only delayed activation:

1. S3a is lowest: 31.308 Bq.
2. S3c is intermediate: 57.824 Bq, 1.85x S3a and 42.1% lower than S3b.
3. S3b is highest: 99.895 Bq, 3.19x S3a.

Interpretation:

- The W shell strongly increases neutron-delayed activation. This is clearest
  from S3b and S3c, where W-187 becomes one of the dominant sampled delayed
  species.
- Replacing CsI with BGO reduces the iodine activation channel. That is why S3c
  is much lower than S3b even though both include the W shell.
- S3a is best on neutron-delayed activation among the three branches because it
  removes the CsI iodine channel without adding the W shell activation burden.

## S3 Context

The retained S3 delayed chain at
`engineering/geometry_optimization_20260704/23_s3_delayed_chain_m50000_20260709/`
is a full-particle delayed chain, not a neutron-only delayed baseline.

Its delayed source summary has:

- fixed total activity: 96.958 Bq
- M=50,000 exact-position source
- transport SE/ID: 1,000,000 / 1,000,000
- transport TE: 10227.144 s
- top sampled contributors: I-128 in window/CsI, Al-28 supports, Cs isotopes

Because this S3 chain includes all delayed contributors, it should not be used
as a strict denominator for the neutron-only S3a/S3b/S3c runs. As context only,
the neutron-only branch activities are 0.323x, 1.030x, and 0.596x of the full
S3 delayed activity for S3a, S3b, and S3c respectively. A strict relative-to-S3
neutron comparison would require a clean S3 neutron-only delayed chain with the
same settings.

## 20-Day 3-Sigma Implication

This neutron-delay run does not replace the detector-coupled full-chain
3-sigma/20-day estimate. It is still a source/transport-side delayed activation
comparison.

For the earlier dominant-background estimate, the neutron-delayed correction
pushes in this direction:

- S3a remains the most favorable branch for neutron-delayed activation.
- S3b is penalized the most; the W shell plus retained CsI produces the largest
  delayed activity.
- S3c remains better than S3b on neutron-delayed activation because BGO removes
  much of the iodine channel, but it still carries a W-shell delayed penalty
  relative to S3a.

Thus, if prompt-background performance alone favored S3c, this delayed result
does not automatically overturn that conclusion, but it adds a real activation
cost to the W-shell options. A final 3-sigma/20-day claim still needs the
detector-response/full-chain delayed coupling.

## Artifact Map

| Branch | Campaign manifest | Delayed source summary | Delayed transport sim |
| --- | --- | --- | --- |
| S3a | `engineering/geometry_optimization_20260704/36_s3a_neutron_delayed_chain_m50000_clean_20260710/s3a_bgo_barrel_neutron_delay_m50000_clean_20260710_campaign_manifest.json` | `engineering/geometry_optimization_20260704/36_s3a_neutron_delayed_chain_m50000_clean_20260710/delayed_source/delayed_source_exactpos_summary.json` | `runs/geometry_optimization_20260704/step02_delayed_transport_s3a_bgo_barrel_neutron_delay_m50000_clean_20260710/DelayedDecayS3aBgoBarrelNeutronDelayM50000.inc1.id1.sim.gz` |
| S3b | `engineering/geometry_optimization_20260704/37_s3b_neutron_delayed_chain_m50000_clean_20260710/s3b_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710_campaign_manifest.json` | `engineering/geometry_optimization_20260704/37_s3b_neutron_delayed_chain_m50000_clean_20260710/delayed_source/delayed_source_exactpos_summary.json` | `runs/geometry_optimization_20260704/step02_delayed_transport_s3b_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710/DelayedDecayS3bW2mmAl3mmShellNeutronDelayM50000.inc1.id1.sim.gz` |
| S3c | `engineering/geometry_optimization_20260704/38_s3c_neutron_delayed_chain_m50000_clean_20260710/s3c_bgo_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710_campaign_manifest.json` | `engineering/geometry_optimization_20260704/38_s3c_neutron_delayed_chain_m50000_clean_20260710/delayed_source/delayed_source_exactpos_summary.json` | `runs/geometry_optimization_20260704/step02_delayed_transport_s3c_bgo_w2mm_al3mm_shell_neutron_delay_m50000_clean_20260710/DelayedDecayS3cBgoW2mmAl3mmShellNeutronDelayM50000.inc1.id1.sim.gz` |

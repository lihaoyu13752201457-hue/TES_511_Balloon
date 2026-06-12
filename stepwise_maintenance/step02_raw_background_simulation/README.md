# Step02 Raw Background Simulation

## Scope

This checkpoint conceptually aligns `new_geo_re` with `fix` Step02: freeze the atmospheric source definition, run native COSIMA smoke simulations, and write reproducible summary artifacts.

Unlike `fix` Step02, this branch also records the first raw delayed-background simulation because the current design question needs both prompt and delayed streams before later time-axis work.

Included here:

- prompt `instant` atmospheric transport;
- activation `buildup` atmospheric transport;
- delayed-decay source construction from buildup `.dat` and SIM RPIP records;
- ground-state half-life correction;
- delayed-decay COSIMA transport.

Not included here:

- Poisson time-axis merging;
- BGO veto;
- Compton veto;
- event-selection or sensitivity analysis.

## Authority

- Prompt/buildup source cards: `config/megalib_sources_fullsphere20/Background_*_fullsphere20.source`
- Geometry: `outputs/geometry/XZTES_ADR_v4c_mkflange_cm/TibetTES_ADR_v4c_mkflange_cm.geo.setup`
- Smoke prompt run output: `runs/step02_instant_smoke1k/`
- Smoke activation-buildup run output: `runs/step02_buildup_smoke1k/`
- Smoke delayed source output: `runs/step02_decay_source_smoke1k/activation_decay_day15.source`
- Smoke fixed delayed source: `runs/step02_delay_fix_smoke1k/activation_decay_day15_groundstate_fixed.source`
- Smoke delayed transport SIM: `runs/step02_delayed_transport_smoke1k/DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz`
- Event-aligned prompt run output: `runs/step02_instant_equiv2602_aligned/`
- Event-aligned activation-buildup run output: `runs/step02_buildup_equiv2602_aligned/`
- Event-aligned delayed source output: `runs/step02_decay_source_equiv2602_aligned/activation_decay_day15.source`
- Event-aligned fixed delayed source: `runs/step02_delay_fix_equiv2602_aligned/activation_decay_day15_groundstate_fixed.source`
- Event-aligned delayed transport SIM: `runs/step02_delayed_transport_equiv2602_aligned/DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz`
- Archived NUBASE2020 ASCII input: `inputs/nubase/nubase_2020.txt`
- Ground-state half-life unit audit: `outputs/reports/half_life_unit_audit/half_life_unit_audit.md`

## v3p5 Center-Finger Low-Stat Checkpoint

Current v3p5 simulation input authority:

- source cards: `config/megalib_sources_fullsphere20_v3p5_centerfinger_tilt45/Background_*_fullsphere20.source`
- source manifest: `config/megalib_sources_fullsphere20_v3p5_centerfinger_tilt45/source_migration_manifest.json`
- geometry: `outputs/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- geometry frame: `InstrumentFrame.Rotation 0 45 0`; local side-window `-x` looks `45 deg` upward in the global zenith-frame source coordinates
- far-field/setup sphere: `60 cm`
- W side collimator: `2 cm` thick square-bore sleeve; not a 376-hole pixel collimator

Low-stat all-particle smoke closure:

- instant run: `runs/step02_instant_v3p5_centerfinger_lowstat10k/`
- buildup run: `runs/step02_buildup_v3p5_centerfinger_lowstat10k/`
- delayed source: `runs/step02_decay_source_v3p5_centerfinger_lowstat10k/activation_decay_day15.source`
- ground-state fixed source: `runs/step02_delay_fix_v3p5_centerfinger_lowstat10k/activation_decay_day15_groundstate_fixed.source`
- delayed transport: `runs/step02_delayed_transport_v3p5_centerfinger_lowstat10k/DelayedDecayRPIPGroundStateFixed.inc2.id1.sim.gz`
- Step02 summary: `outputs_v3p5_centerfinger_lowstat10k/step02_v3p5_centerfinger_lowstat10k_summary.md`

Result status: `PASS_LOWSTAT10K_TRANSPORT_CLOSURE`.

This checkpoint uses `gamma_events=10000`, not the requested final 1/10-statistics
run. It is retained as a syntax/geometry/source-chain closure before spending
the much larger 1/10 compute budget.

1/10-statistics all-particle closure:

- instant run: `runs/step02_instant_v3p5_centerfinger_1of10/`
- buildup run: `runs/step02_buildup_v3p5_centerfinger_1of10/`
- delayed source: `runs/step02_decay_source_v3p5_centerfinger_1of10/activation_decay_day15.source`
- ground-state fixed source: `runs/step02_delay_fix_v3p5_centerfinger_1of10/activation_decay_day15_groundstate_fixed.source`
- delayed transport: `runs/step02_delayed_transport_v3p5_centerfinger_1of10/DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz`
- Step02 summary: `outputs_v3p5_centerfinger_1of10/step02_v3p5_centerfinger_1of10_summary.md`

Result status: `PASS_1OF10_TRANSPORT_CLOSURE`.

Current 1/10 result:

- instant: `19/19` jobs passed, `1,190,129` generated particles.
- buildup: `19/19` jobs passed, `1,190,129` generated particles.
- delayed source: `787` source blocks, raw activity `86.437919 Bq`.
- ground-state fixed source: `786` source blocks, fixed activity `86.382997 Bq`; `1` W-180 block removed as negligible after NUBASE ground-state correction.
- delayed transport: SIM `TS=1`, `SE=100,000`, `ID=100,000`, `TE=1140.447373 s`.

Known limitation: the delayed source still uses the existing axisymmetric
`RadialProfileBeam` profile builder. For the tilted geometry, exact-position
delayed source sampling is the next confidence upgrade before paper-facing
numbers.

## Rebuild Summary Products

```bash
python3 stepwise_maintenance/step02_raw_background_simulation/code/build_step02_raw_background_summary.py
```

The script reads the run products above and regenerates:

- `outputs/step02_raw_simulation_summary.md`
- `outputs/step02_raw_simulation_summary.json`
- `outputs/step02_raw_simulation_summary.png`
- `outputs/step02_run_matrix.csv`
- `outputs/step02_particle_counts.csv`
- `outputs/step02_activation_inventory.csv`

The event-aligned production report is built separately so the smoke checkpoint remains reproducible:

```bash
python3 stepwise_maintenance/step02_raw_background_simulation/code/build_step02_event_aligned_summary.py
```

It regenerates:

- `outputs/step02_event_aligned_summary.md`
- `outputs/step02_event_aligned_summary.json`
- `outputs/step02_event_aligned_summary.png`
- `outputs/step02_event_aligned_particle_counts.csv`

The v3p5 1/10-statistics report is regenerated separately:

```bash
python3 stepwise_maintenance/step02_raw_background_simulation/code/build_v3p5_centerfinger_1of10_summary.py
```

It regenerates:

- `outputs_v3p5_centerfinger_1of10/step02_v3p5_centerfinger_1of10_summary.md`
- `outputs_v3p5_centerfinger_1of10/step02_v3p5_centerfinger_1of10_summary.json`
- `outputs_v3p5_centerfinger_1of10/step02_v3p5_centerfinger_1of10_particle_counts.csv`
- `outputs_v3p5_centerfinger_1of10/step02_v3p5_centerfinger_1of10_source_blocks.csv`

The ground-state half-life unit audit is regenerated from the fixed-source corrections CSV and the archived NUBASE table:

```bash
python3 code/tools/audit_groundstate_half_life_units.py
```

## Simulation Commands Used

Prompt instant smoke run:

```bash
python3 code/tools/run_equiv2602_pipeline_NEW_GEO.py --mode instant --outdir runs/step02_instant_smoke1k --gamma-events 1000 --gamma-splits 1 --non-gamma-replicas 1 --workers 4 --force --keep-sources
```

Activation buildup smoke run:

```bash
python3 code/tools/run_equiv2602_pipeline_NEW_GEO.py --mode buildup --outdir runs/step02_buildup_smoke1k --gamma-events 1000 --gamma-splits 1 --non-gamma-replicas 1 --workers 4 --force --keep-sources
```

Delayed source construction:

```bash
python3 /home/ubuntu/codex_tes_511_sim/COSMOSRAY_BALLOON_SIM/tools/makedecaysourcewithplot_rpip.py --dat 'runs/step02_buildup_smoke1k/Background_*_fullsphere20_rep*_part*.dat.inc1.dat' --sim 'runs/step02_buildup_smoke1k/Background_*_fullsphere20_rep*_part*.inc1.id1.sim.gz' --geo outputs/geometry/XZTES_ADR_v4c_mkflange_cm/TibetTES_ADR_v4c_mkflange_cm.geo.setup --non-gamma-div 1.0 --t-ground-days 0 --t-flight-days 15 --t-after-days 0 --outdir runs/step02_decay_source_smoke1k --outfile-prefix runs/step02_delayed_transport_smoke1k/DelayedDecayRPIP --triggers 1000 --z-bins 10 --r-bins 20 --min-points 1 --n-sample 1000 --workers 4 --cache half_life_cache.json --nubase /home/ubuntu/codex_tes_511_sim/COSMOSRAY_BALLOON_SIM/cosmosray_buildup_rpmpia/decay_rpip_out/nubase_2020.txt --bounds outputs/geometry/XZTES_ADR_v4c_mkflange_cm/bounds.json --plot-check --plot-max-points 4000
```

Ground-state half-life fix:

```bash
python3 /home/ubuntu/codex_tes_511_sim/COSMOSRAY_BALLOON_SIM/tools/build_fixed_delay_source.py --source runs/step02_decay_source_smoke1k/activation_decay_day15.source --dat-glob '/home/ubuntu/codex_tes_511_sim/new_geo_re/runs/step02_buildup_smoke1k/Background_*_fullsphere20_rep*_part*.dat.inc1.dat' --nubase /home/ubuntu/codex_tes_511_sim/COSMOSRAY_BALLOON_SIM/cosmosray_buildup_rpmpia/decay_rpip_out/nubase_2020.txt --outdir runs/step02_delay_fix_smoke1k --outfile-prefix runs/step02_delayed_transport_smoke1k/DelayedDecayRPIPGroundStateFixed --output-source-name activation_decay_day15_groundstate_fixed.source --triggers 1000 --geometry outputs/geometry/XZTES_ADR_v4c_mkflange_cm/TibetTES_ADR_v4c_mkflange_cm.geo.setup --non-gamma-div 1.0 --t-flight-days 15.0
```

Delayed transport:

```bash
/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima runs/step02_delay_fix_smoke1k/activation_decay_day15_groundstate_fixed.source
```

## Current Result

Smoke result:

- Instant: `8/8` particle jobs passed, `1188` generated particles.
- Buildup: `8/8` particle jobs passed, `1188` generated particles.
- Delayed source: `8` source blocks, total activity about `175.273 Bq`.
- Ground-state fix: `0` removed blocks, total activity about `175.273 Bq`.
- Delayed transport: SIM `TS 1000`, `SE` event blocks `1000`, `TE 5.784061 s`.

COSIMA stdout for the delayed transport contained repeated `Energy type not yet implemented: -99999987` messages. The run still exited successfully and wrote a complete 1000-event SIM, so Step02 records it as a smoke-run transport product, not as a final physics validation.

Event-count-aligned production result:

- Instant: `60/60` jobs passed, `25,210,216` generated particles.
- Buildup: `60/60` jobs passed, `25,210,216` generated particles.
- Per-particle counts match old `COSMOSRAY_BALLOON_SIM`: gamma `10,000,000`, n `7,704,528`, eminus `3,316,936`, eplus `1,949,816`, p `1,871,808`, alpha `191,464`, muplus `92,840`, muminus `82,824`.
- Delayed source: `6008` source blocks, total activity `624.55914 Bq`.
- Ground-state fix: `40` removed blocks; fixed source `5968` source blocks, total activity `624.27109 Bq`.
- Half-life audit: `74` prefix-year rows (`Ey/Gy/My/Ty/ky`) match archived NUBASE line references; W-180 is reduced to `5.09e-21 Bq` and absent from the fixed source.
- Delayed transport: SIM `TS 1,000,000`, `SE 1,000,000`, `TE 1584.60761 s`.
- The alignment target is event count, not physical exposure time. The old production normalization uses a `150 cm` far-field radius; `new_geo_re` uses `35 cm`, so equivalent prompt gamma time differs.

`source_snapshots/` contains only lightweight source cards, manifests, source-builder scripts, and CSV/JSON evidence. It intentionally does not contain `.sim.gz` or `.dat` simulation products.

# Step09 Opticsim EventList Bridge (f10m_a1_v3p5)

Status: `PASS_EVENTLIST_BRIDGE_FULL_TRANSPORTED`.

This step converts the current Step04 B-FULL Laue tracked diffracted focal-plane crossings (`focal_crossings.csv`, `source_tag=laue_bfull_diffracted`, restricted to the Be window) into a MEGAlib EventList source at the selected detector Be-window plane. The analytic `phase_space.csv` projection is NOT used because it overcounts the focused flux (it ignores the EM exit attenuation of the diffracted beam).

## Coordinate Policy

- axis policy: `v3p5_side_entry_tilt45`.
- transverse scale: `0.1 cm per opticsim mm`.
- max EventList radius: `1.55356 cm`.
- EventList r95: `1.10335 cm`.
- Be radius: `1.898 cm`.
- local Be x plane: `-13.1 cm`; local axis center `(y,z)=(0.0, -5.2) cm`.
- instrument rotation: `0 45.0 0` degrees.
- side-window look elevation: `45 deg`.
- direction policy: opticsim longitudinal direction maps to detector local `+x`, then the full EventList is rotated with the v3p5 `InstrumentFrame`.

## Smoke Transport

- source: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/run_configs/Opticsim_laue_f10m_a1_v3p5_centerfinger_smoke1000.source`
- sim exists: `True`
- stored events: `1000`

## Full Transport

- source: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/run_configs/Opticsim_laue_f10m_a1_v3p5_centerfinger.source`
- sim exists: `True`
- stored events: `37194`
- ID events: `37194`
- observation time from SIM: `3.7e-05 s`

## Outputs

- EventList: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/eventlists/Opticsim_laue_f10m_a1_v3p5_centerfinger.eventlist.dat`
- full source: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/run_configs/Opticsim_laue_f10m_a1_v3p5_centerfinger.source`
- smoke source: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/run_configs/Opticsim_laue_f10m_a1_v3p5_centerfinger_smoke1000.source`
- manifest: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/step09_optics_bridge_summary.json`

## Rebuild

```bash
STEP09_OPTICS_PROFILE=f10m_a1_v3p5 python3 stepwise_maintenance/step09_optics_bridge/code/build_step09_optics_bridge.py
```

Smoke transport command:

```bash
/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/run_configs/Opticsim_laue_f10m_a1_v3p5_centerfinger_smoke1000.source
```

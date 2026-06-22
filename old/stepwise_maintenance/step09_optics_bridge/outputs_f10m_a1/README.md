# Step09 Opticsim EventList Bridge (f10m_a1)

Status: `PASS_EVENTLIST_BRIDGE_SMOKE_TRANSPORTED`.

This step converts the current Step04 B-FULL Laue tracked diffracted focal-plane crossings (`focal_crossings.csv`, `source_tag=laue_bfull_diffracted`, restricted to the Be window) into a MEGAlib EventList source at the current `new_geo_re` cm Be-window plane. The analytic `phase_space.csv` projection is NOT used because it overcounts the focused flux (it ignores the EM exit attenuation of the diffracted beam).

## Coordinate Policy

- z plane: `16.051 cm`.
- x/y scale: `0.1 cm per opticsim mm`.
- max EventList radius: `1.55356 cm`.
- EventList r95: `1.10335 cm`.
- Be radius: `1.898 cm`.
- direction policy: keep x/y direction and reverse z, so opticsim rays are injected toward the detector.

## Smoke Transport

- source: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1/run_configs/Opticsim_laue_f10m_a1_new_geo_re_smoke1000.source`
- sim exists: `True`
- stored events: `1000`

## Outputs

- EventList: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1/eventlists/Opticsim_laue_f10m_a1_new_geo_re.eventlist.dat`
- full source: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1/run_configs/Opticsim_laue_f10m_a1_new_geo_re.source`
- smoke source: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1/run_configs/Opticsim_laue_f10m_a1_new_geo_re_smoke1000.source`
- manifest: `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1/step09_optics_bridge_summary.json`

## Rebuild

```bash
STEP09_OPTICS_PROFILE=f10m_a1 python3 stepwise_maintenance/step09_optics_bridge/code/build_step09_optics_bridge.py
```

Smoke transport command:

```bash
/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1/run_configs/Opticsim_laue_f10m_a1_new_geo_re_smoke1000.source
```

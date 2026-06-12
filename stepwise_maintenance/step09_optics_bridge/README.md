# Step09 Opticsim EventList Bridge (f9m)

Status: `PASS_EVENTLIST_BRIDGE_SMOKE_TRANSPORTED`.

This step converts the current Step04 B-FULL Laue tracked diffracted focal-plane crossings (`focal_crossings.csv`, `source_tag=laue_bfull_diffracted`, restricted to the Be window) into a MEGAlib EventList source at the current `new_geo_re` cm Be-window plane. The analytic `phase_space.csv` projection is NOT used because it overcounts the focused flux (it ignores the EM exit attenuation of the diffracted beam).

## Coordinate Policy

- z plane: `16.051 cm`.
- x/y scale: `0.1 cm per opticsim mm`.
- max EventList radius: `1.45767 cm`.
- EventList r95: `0.217638 cm`.
- Be radius: `1.898 cm`.
- direction policy: keep x/y direction and reverse z, so opticsim rays are injected toward the detector.

## Smoke Transport

- source: `stepwise_maintenance/step09_optics_bridge/outputs/run_configs/Opticsim_laue_new_geo_re_smoke1000.source`
- sim exists: `True`
- stored events: `1000`

## Full Detector-Coupled Response

- full focused source: `stepwise_maintenance/step09_optics_bridge/outputs/run_configs/Opticsim_laue_new_geo_re.source`
- full focused SIM: `runs/step09_optics_bridge/Opticsim_laue_new_geo_re.inc1.id1.sim.gz`
- parsed response: `stepwise_maintenance/step09_optics_bridge/outputs/detector_coupled_focus_response.json`
- status: `PASS_DETECTOR_COUPLED_FOCUSED_EVENTLIST`
- W1 final signal at `1e-4 ph cm^-2 s^-1`: `9.009895e-04 cps`; W1 final non-X-ray background: `0.783047 cps`.
- W2 final signal at `1e-4 ph cm^-2 s^-1`: `8.982878e-04 cps`; W2 final non-X-ray background: `0.184347 cps`.
- detector-coupled W2 signal radii: `r90=0.523692 cm`, `r99=1.2168 cm`, `rmax=1.69655 cm`.
- headline spatial cut is `spot_r90`: background `0.0551005 cps`, `Z20d=4.52748`.

## Outputs

- EventList: `stepwise_maintenance/step09_optics_bridge/outputs/eventlists/Opticsim_laue_new_geo_re.eventlist.dat`
- full source: `stepwise_maintenance/step09_optics_bridge/outputs/run_configs/Opticsim_laue_new_geo_re.source`
- smoke source: `stepwise_maintenance/step09_optics_bridge/outputs/run_configs/Opticsim_laue_new_geo_re_smoke1000.source`
- manifest: `stepwise_maintenance/step09_optics_bridge/outputs/step09_optics_bridge_summary.json`
- detector-coupled response: `stepwise_maintenance/step09_optics_bridge/outputs/detector_coupled_focus_response.json`

## Rebuild

```bash
python3 stepwise_maintenance/step09_optics_bridge/code/build_step09_optics_bridge.py
```

Smoke transport command:

```bash
/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima stepwise_maintenance/step09_optics_bridge/outputs/run_configs/Opticsim_laue_new_geo_re_smoke1000.source
```

# Optics global 2D schematics

Generated on 2026-05-24 from local opticsim configuration and run summaries.

## Outputs

- `laue_optics_global_2d.png` / `laue_optics_global_2d.svg`
- `channel_optics_global_2d.png` / `channel_optics_global_2d.svg`

## What the figures show

- The left aperture panel shows the entrance/lens plane ring geometry.
- The right panel is a global side schematic of source incidence and focusing.
- The longitudinal axis is compressed and the radial axis is expanded so the
  global geometry is readable despite meter-scale focal lengths and centimeter-
  scale apertures.
- These are review schematics, not CAD/WRL replacements.

## Source facts used

Laue:

- Ring config: `data/laue/ge111_480_550keV_multiring_darwin_config.csv`
- Focal length: 8.3 m
- Mainline spot D90: 0.2206 cm
- Guan-style spot D90: 0.2194 cm
- Source convention: primary gamma rays are generated upstream and travel
  approximately along `u=(0,0,+1)` into the lens plane.

Channel:

- Ring config: `data/channel/cam511_channel_rings.csv`
- Focal length: 12.0 m
- Calibrated Geant4 spot D90: 3.6133 cm
- Public wall-by-wall reconstruction spot D90: 1.0329 cm
- Source convention: primary gamma rays are generated upstream of each selected
  channel tile and travel along `u=(0,0,+1)`.

## Rebuild

```bash
python3 records/2026-05-24_optics_global_schematics/build_optics_global_schematics.py
```

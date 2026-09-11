# Reflectivity Tables

The current implementation ships a constant toy/calibrated W/Si row so the
ray-tracing and output pipeline can be validated before a physical
IMD/Parratt/XOP table is available.

Important convention: `open_fraction` is metadata in the baseline table.
The channel baseline uses `raytrace.total_transmissivity` as the total
survival probability, so `open_fraction` must not be multiplied again.

`generate_wsi_parratt_table.py` can generate a first physical candidate table
with `xraydb.multilayer_reflectivity` for W/Si 30/150 nm at 511 keV. It writes
`R/A/T` rows where `R` comes from xraydb and the non-reflected part is split into
absorption/leakage with a simple stack-attenuation estimate. This is still not a
511-CAM reproduction by itself; the channel geometry must supply physically
consistent grazing angles.

```bash
python3 data/reflectivity/generate_wsi_parratt_table.py
```

`analysis/crosscheck_wsi_parratt.py` recomputes the same W/Si stack with a local
s-polarization Parratt recursion. This does not call
`xraydb.multilayer_reflectivity`; it uses xraydb only for material optical
constants. The current 511 keV table cross-check passes with zero numerical
difference on the stored theta grid, so the table-generation arithmetic is now
covered by an independent implementation path. Publication-level claims should
still add provenance from a second optical-constant/table tool such as
IMD/DarpanX.

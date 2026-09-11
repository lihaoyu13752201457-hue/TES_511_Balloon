# HEART Adapter Feasibility

Status: `audited_not_directly_comparable`
HEART commit checked: `d54196aaa787eaefef6df7c66255803f50ea8517`
Direct HEART runner ready as current-lens oracle: `False`

## Finding

HEART's flat-crystal model uses the crystal surface normal as the mean mosaic crystallite/diffracting-plane normal, while the current Laue lens needs a mechanical slab normal separate from each tile's Ge(111) diffracting-plane normal.

A comparable external full-lens run must keep the mechanical slab normal and the Ge(111) diffracting-plane normal independently controllable.

## Source Evidence

| evidence | found | source |
|---|---:|---|
| `flat_axis_n_is_surface_normal` | `True` | `HEART/components/FlatCrystal.py:53` |
| `miller_indices_do_not_define_orientation` | `True` | `docs/files/start.rst:178` |
| `mosaic_distribution_centered_on_surface_normal` | `True` | `docs/files/start.rst:205` |
| `ray_tracer_reads_crystal_surface_normal` | `True` | `HEART/ray_tracer.py:498` |
| `ray_tracer_rotates_crystallite_from_surface_normal` | `True` | `HEART/ray_tracer.py:729` |

## Tile Geometry

- tile rows: `360`
- focal z: `8300.0 mm`
- min slab-vs-plane-normal angle: `89.773559 deg`
- max slab-vs-plane-normal angle: `89.802399 deg`

## Required Next Step

The external runner must map external_lens_oracle_tiles.csv ideal_plane_normal_* to the Ge(111) diffracting-plane normal independently of slab_normal_*.

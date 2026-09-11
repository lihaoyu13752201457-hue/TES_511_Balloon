# HEART Independent Plane Normal Patch

Patch file:

```text
benchmarks/reference_outputs/heart_independent_plane_normal.patch
```

Purpose:

The current Laue lens handoff needs the mechanical tile slab normal and the
Ge(111) diffracting-plane normal to be independently controllable. HEART commit
`d54196aaa787eaefef6df7c66255803f50ea8517` currently uses the crystal surface
normal as the mean mosaic crystallite/diffracting-plane normal for flat
crystals.

The patch adds an optional `diff_plane_N` argument to
`Spectrometer.add_flat_crystal()` and `FlatCrystal`. If omitted, HEART keeps the
existing behavior. If provided, geometry and thickness still use `axis_N`, while
the ray tracer uses `diff_plane_N` as the mean mosaic/diffracting-plane normal.
It also makes the flat-crystal cuboid intersection robust for rays parallel to
one or more crystal-axis slabs, which is required for the current parallel
on-axis Laue-lens source.

Expected Laue-lens use:

```python
spec.add_flat_crystal(
    x_center_mm=center,
    axis_L=tangential_axis,
    length=tile_size_mm,
    axis_W=radial_axis,
    width=tile_size_mm,
    axis_N=slab_normal,
    Tc_mm=thickness_mm,
    diff_plane_N=ideal_plane_normal,
)
```

Validation status:

- Generated against HEART commit `d54196aaa787eaefef6df7c66255803f50ea8517`.
- Syntax checked with `python3 -m py_compile` on the modified HEART files.
- Checked with `git diff --check`.
- Applied in the local isolated HEART run used to generate
  `heart_patched_full_lens.h5` and
  `heart_patched_full_lens_guan_direction.h5`.
- The imported full-lens summary is
  `benchmarks/reference_outputs/external_lens_observables/summary.json`
  with `ok=true`.

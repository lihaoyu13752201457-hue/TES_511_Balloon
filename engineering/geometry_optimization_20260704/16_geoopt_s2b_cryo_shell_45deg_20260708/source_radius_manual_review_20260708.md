# Source Radius Manual Review

Date: 2026-07-08

MEGAlib/Geomega guidance checked:

- `SurroundingSphere <radius> <x> <y> <z> <distance>` is mandatory for Cosima/GMega far-field simulations.
- The distance parameter should normally equal the radius.
- For far-field sources, particles are started from the disk defined by the surrounding sphere.
- The sphere should be as small as possible while enclosing the complete detector geometry and not intersecting any volume.
- Far-field normalization uses the start area `A = pi * radius^2`, so increasing radius changes the simulated event normalization and wastes statistics.

Current geometry check:

- Current retained center: `(4.49012806, 0, 4.49012806) cm`
- With that center, max visible-geometry distance is `60.931916 cm`, at `NF2_OuterSupport_Al_TopMountAnnulus`.
- Therefore `SurroundingSphere 60 4.49012806 0 4.49012806 60` is not strictly valid if the NF2 support volumes are part of the geometry to be illuminated.

Applied production choice in this S2b branch:

```text
SurroundingSphere 60 5.0 0.0 9.0 60
```

Rationale:

- Re-centering to approximately `(5.0, 0.0, 9.0) cm` gives a max visible-geometry distance of about `58.03 cm`.
- A radius of `60 cm` then leaves about `1.97 cm` clearance.
- This keeps the same far-field start area as the retained R60 source cards, avoiding a normalization change.
- It is more consistent with the manual than simply increasing to R65, because R65 increases start area by `(65/60)^2 = 1.174`, or `+17.4%`.

Fallback if the center must not change:

```text
SurroundingSphere 62 4.49012806 0 4.49012806 62
```

This is the smallest practical rounded choice with the old center.  It leaves about `1.07 cm` clearance and increases start area by `(62/60)^2 = 1.068`, or `+6.8%`.

Conclusion:

- Applied option: keep `R=60 cm`, change center to `(5.0, 0.0, 9.0) cm`.
- If retaining the old center is mandatory: use `R=62 cm`.
- Do not use `R=65 cm` for production unless a deliberately conservative debug sphere is desired.

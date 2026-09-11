# SG3A — SG3 material-only 50 mK aluminium-can candidate

## Status

`SG3A` is the strict material-only child of `SG3`.  The only physical change is
that all four pieces of the 2 mm 50 mK Still-like cold can use `Aluminium`
instead of `Copper`.  Shapes, dimensions, positions, rotations, mothers,
openings, and passive status are unchanged.  The four volume/detector names are
renamed to `SG3A_Al_*` only to prevent future activation-lineage reports from
misidentifying their material.

Everything else is retained: the SG3 L0 Cu heat-sink ring, its four inherited
off-axis Cu cold-finger chains, the compact passive Bi umbrella, all cold plates
and holes, and all BGO/plastic response definitions.  The Al can is passive and
is not added to the active-veto whitelist.  No independent atmospheric
mono-511 source is enabled.

## Material and mass delta

- inherited four-piece can volume: `323.741922 cm3`;
- SG3 Cu-can mass: `2.900728 kg`;
- SG3A Al-can mass: `0.873779 kg`;
- SG3A minus SG3: `-2.026948 kg`.

`audit/sg3a_geometry_validation.json` reverses the four material/lineage edits
to the pinned SG3 `.geo` and `.det` bytes.  The materials and intro files remain
byte-identical.  Because no shape or placement changes, the completed SG3
overlap/navigation/37,194-ray geometry audits are inherited; this does not
replace a fresh SG3A signal transport.

## Pre-transport F3 estimate

`data/sg3a_f3_pretransport_estimate.json` is explicitly a sensitivity estimate,
not a physics result.  It combines three retained SE3 volume-share levers:

1. the old L0 solid-disk selected share targeted by the SG3 ring;
2. the old Cu-can selected share targeted by the Al substitution;
3. a fractional realization of the Bi umbrella's MXC geometric upper bound.

Conditional on no new accepted prompt and unchanged selected signal, the
central estimate is approximately

`F3 ~= 5.8e-5 ph cm^-2 s^-1`,

with a deliberately broad engineering range of about
`5.1e-5` to `6.6e-5 ph cm^-2 s^-1`.  This does **not** establish `<5e-5` and
does not promote SG3A.  Al activation, a new prompt survivor population, or a
different isotope time profile can place the final result outside that range.

## Reproduction

```bash
python3 code/build_sg3a_geometry.py
python3 code/estimate_sg3a_f3.py
```

The required physics closure remains candidate-own corrected prompt,
buildup/inventory, actual-position delayed, fresh 37,194-ray signal transport,
the common response/veto/Step05 chain, and the 81-node/20-day mission fold.

## Residual-coupling diagnostic

`RESIDUAL_COUPLING_AUDIT.md` and
`code/build_sg3a_residual_coupling_sections.py` document the retained one-event
NbTi K-38 and L3 Cu-64 terms and test a conceptual curved-Bi envelope against
the focused-ray aperture.  This diagnostic adds figures and a mass ledger only;
it does not change SG3A geometry and does not launch transport.

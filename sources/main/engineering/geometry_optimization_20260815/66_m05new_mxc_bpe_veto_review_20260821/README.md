# M05NEW MXC/TES cross-section and BPE/plastic-veto review

This package is a RAM-safe, non-transport derivation for the M05NEW paper
replacement.  It answers two bounded questions:

1. Does moving the TES from directly below the DR/MXC cold-stage stack (SG3B)
   into the SH3 side chimney reduce geometric coupling to those activated
   structures?
2. Can an exterior plastic positron-veto layer and at most 5 cm BPE plausibly
   move the current `2.2294e-5` 20-day Gaussian 3-sigma threshold to `1.5e-5`?

## Figure contract

- **Question:** how do the MXC/upper cold plates project relative to the TES
  active layers in SG3B and SH3 OptV3?
- **Takeaway:** SG3B places the TES directly below the cold-stage footprint,
  while SH3 laterally displaces it into the chimney; the central selected
  delayed-W2 share from `DR/MXC + staged cold plates` falls from about 32% to
  about 4%.
- **Form:** two dimensionally aligned `InstrumentFrame x'-z'` engineering
  sections on the same axes, with exact selected delayed-source positions.
- **Renderer:** reproducible Matplotlib PNG/SVG/PDF.
- **Palette:** two non-neutral roots (blue and gold), with red TES and
  line-style/marker-shape distinctions so the figure is not color-only.
- **Scope:** cold plates, mixing chamber, TES active layers and shield
  envelopes are dimensionally aligned to retained geometry properties.  CSG
  holes and small supports are intentionally omitted; this is not a CAD view.

## Numerical conclusion

With effective area held fixed, reaching `1.5e-5` requires about a 55%
reduction of the mature background.  The corrected-keV OptV3 final prompt
sample is gamma-only: the primary-positron and primary-neutron prompt-final
rates are both zero.  Neutron-induced delayed events contribute only about 8%
of the direct final rate.  Even the deliberately impossible upper bound in
which BPE removes **all** neutron-induced delayed background leaves the flux
threshold near `2.14e-5`; removing all delayed background still leaves it near
`1.75e-5` because prompt gamma remains.

Therefore an exterior plastic layer or 5 cm BPE may be useful as a secondary
engineering knob, but the retained data do not support them as a route to
`1.5e-5`.  The paper should retain the compact causal logic
`SG3B under-cold-plate baseline -> source/coupling diagnosis -> SH3 off-axis
TES geometry -> matched sensitivity comparison`.

## Existing corrected-keV BPE evidence

The repository already contains a 100,000-history corrected-neutron boundary
diagnostic for the historical 20 mm, 5 wt% BPE bodies.  Of primaries that first
entered the BPE, 67.55% reached an inner surface.  Transmission increased from
1.61% below 0.5 eV to 76.09% at 1--10 MeV and 85.55% above 39 MeV: 2 cm is an
effective absorber for slow neutrons but only a partial moderator for the
current fast spectrum.  The direct Cu-61/Cu-62/Cu-64 reaction-current indices
were 0.885/0.842/0.897.  Thus the retained calculation shows a modest favorable
direct-Cu tendency, not the feared central activation increase, while leaving
bypass paths, high-energy cascades, activation location and final detector cuts
unclosed.  It does not justify extrapolating 5 cm BPE to a final W2 rate.

The physical ordering still matters.  If BPE is tested later, placing it outside
the BGO is the sensible candidate: moderation and boron capture occur before
inward transport, while the BGO remains between capture products/gammas and the
TES.  An incomplete inner moderator could leak lower-energy neutrons toward Cu
and Al, where neutron capture can create radioactive nuclei; this is a design
risk to test, not an effect observed in the existing 2 cm direct-Cu fold.

External mechanism references: IAEA *Neutron monitoring for radiation
protection* (https://www-pub.iaea.org/MTCD/Publications/PDF/PUB1987_web.pdf)
and Pan, Lin & Pan (2013), DOI 10.13491/j.cnki.issn.1004-714x.2013.04.001.

## Authority boundary

- No SIM payload is opened and no Cosima/Geant4 process is started.
- Old factor-1000 or separate mono-511 rates are not used.
- Historical SG3B plastic/BPE files are used only to identify the physical
  layer arrangement.  Quantitative bounds come from current corrected-keV
  OptV3 cutflow and exact-position selected-event data.
- The BPE/plastic scenarios are transparent component-removal upper bounds,
  not new transport predictions.

Run:

```bash
python3 code/build_mxc_bpe_veto_review.py
```

The paper copy of the figure is written under `M05NEW/figures/`; source data,
the same figure, and `assessment.json` remain in this package.

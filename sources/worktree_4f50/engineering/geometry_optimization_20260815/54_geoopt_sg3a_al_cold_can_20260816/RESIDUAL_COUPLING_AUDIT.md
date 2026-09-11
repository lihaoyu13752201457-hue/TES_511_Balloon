# SG3A residual-coupling audit — NbTi, MXC/Bi, and L3

This is a compact-evidence geometry audit, not SG3A-own transport.  The
activation points are retained SE3 delayed-W2 origins, the prompt tracks are
retained SF3 diagnostics, and the curved Bi shell is only a counterfactual
overlay.  No transport was launched and the SG3A geometry was not changed.

## NbTi K-38 term

The quoted `11.4%` is not a direct cable measurement.  SE3 contains one
selected K-38 event from `NbTi_Bundle_Still_4K`, at
`0.004211161842 cps`, with `Neff = 1`.  It is `7.005%` of the original SE3
selected delayed rate and becomes approximately `11.4%` only after dividing by
the central SG3A estimated remaining-background fraction.  It is therefore a
high-variance residual projection.

The geometry does not model individual wires.  It uses five 61.2-degree
annular-sector volumes with a homogeneous 1:1-atomic Nb/Ti proxy at
`6.5 g cm^-3`.  Their total proxy mass is `567.70 g`; the selected Still-to-4 K
sector alone is `159.69 g`.  Until the actual harness wire count, conductor and
insulation diameters, NbTi fill fraction, and routed lengths are supplied, this
term cannot be treated as a flight-mass-normalized prediction.  A first-order
inventory correction should scale the Still-to-4 K activation source by
`actual NbTi-bearing mass / 159.69 g`, followed by candidate-own activation and
delayed transport.

## MXC term and curved Bi

The retained MXC selected share is `25.071%` of SE3 and is about `30.0%` only
after the same SG3A residual renormalization.  It has seven selected events but
only `Neff = 2.36`, so it is more supported than either one-event term but still
not precise.

The current flat Bi umbrella is `7.8 cm x 4.5 cm x 4.796 mm`, `164.08 g`, and
passive.  A same-thickness full upper semicylinder spanning the same rectangle
would be about `257.74 g`, or `1.571` times the Bi mass.  The local section shows
that its side arcs intersect the retained 37,194 focused-ray envelope.  A full
half-cylinder therefore cannot be adopted without losing signal; it also adds
near-field high-Z pair-production target mass.

The better next geometry is a ray-derived segmented curved visor: construct
the envelope of lines from the retained MXC activation points to the TES,
subtract the 37,194 focused-ray aperture with clearance, and retain Bi only in
the remaining shadow regions.  Curved side lips may be used only outside that
aperture.  Relative to the existing central estimate, even realizing the full
retained Bi geometric upper bound would change the conditional F3 only from
about `5.77e-5` to `5.45e-5 ph cm^-2 s^-1`, assuming unchanged signal and no new
accepted prompt.

## L3 Cu ring identity

`Cu_SubstrateSupport_OpenRing_L3_ZM_panel` is not the large 50 mK can and is not
the L0 heat-sink ring.  It is one of four small Cu bars around the L3 substrate
stage.  All four bars total only `13.02 g`; the ZM bar is about `3.255 g`.
The retained Cu-64 term is again one selected event at `Neff = 1`, so its
residual-renormalized `11.4%` must not be read as a precise component fraction.

A matched L3 material/geometry ablation is reasonable, but an automatic Cu to
Al promotion is not: millikelvin thermal conductance, superconductivity, flux
trapping, support stiffness, and the replacement material's own activation
must close.  The physically safer concept is to keep minimal Cu thermal-contact
pads/straps and remove or replace only non-contact ring span.  Because the ring
is small and the present evidence is one weighted event, this ranks behind
repairing the NbTi mass model and designing the aperture-preserving MXC visor.

# SE3 activation + SF3 prompt section diagnosis

## What is plotted

The geometry background is the validated SE3 native mesh.  Activation points are the
47 SE3 delayed-W2 selected-event production origins,
weighted to 0.0601133620585 cps.  They are a distribution of
rate-contributing sources, not a map of every activated atom.  Prompt routes are the three SF3
prompt-W2 survivors from the compact route JSON.  The SF3 W overlays are passive material and
are **not** active veto volumes.

## Quantitative result

Cu-61/Cu-62/Cu-64 account for 92.995% of the SE3 delayed-W2
rate.  The MXC plate retains 7 selected events and
0.015071195046 cps (25.071%); therefore the MXC term
must not be dismissed using SF3 delayed activation, whose added W can perturb its irradiation.
The 50 mK bottom cap plus L0 disk cover 38.985%
of the observed residual rate; adding the MXC plate raises the covered share to
64.056%.

The SF3 prompt sample is 3 events / 0.152255126811
cps.  Two pair vertices lie in the new side W, while the third pairs outside the new W and then
has a Rayleigh interaction in the new front W.  Every event has zero active-veto deposit.  This
is direct negative evidence against near-field passive high-Z material in the focused acceptance
path; it is not a full-stat rate estimate.

## Optimization order

1. V2A: turn the L0 solid Cu disk into an open ring and test an aperture/ring-cap replacement for
   the broad 50 mK bottom cap, while preserving thermal/mechanical requirements.
2. V2B: add staggered line-of-sight relief to the MXC plate.  Do not remove the whole MXC plate;
   treat the dashed box as a design ROI and constrain the relief thermally.
3. Keep the 4 K plate as a later, higher-engineering-risk branch.
4. Reject near-field W concepts unless the complete matched chain reverses the observed prompt
   failure without harming focused signal.

No geometry is promoted here.  A candidate still needs corrected prompt, candidate-owned
activation/inventory, actual-position delayed transport, the independent 37,194-ray signal,
shared response/veto/Step05, and 81-node/20-day F3.  Mono-511 remains disabled, SF3 is not
full-stat, and there is no final optimal geometry.

# SG3B M05 common-time response and conditional flux reach

This package reuses the corrected M05 compact-event parser, keyed TES response,
and retained Step05 Compton/FoV selector for SG3B's accepted prompt and day-15
exact-position delayed transports.  It is non-overwriting and does not modify
the manuscript.

The nominal event chain is:

1. per-family physical-time normalization (`1/sum(TT)` for prompt and
   transported day-15 family activity divided by one million delayed triggers);
2. keyed 420 eV FWHM pixel response and 0.3 keV post-noise pixel threshold;
3. separate 10 mm plastic charged-particle/positron veto and BGO active-shield
   veto, both using the retained strict `<50 keV` offline rule;
4. their logical conjunction;
5. the retained Step05 single-photon Compton/FoV selector;
6. superposed prompt/delayed Poisson occupancy on the common 1 microsecond time
   axis and the retained weak-source live factor;
7. 81-node, 20-day signal/background integration and Gaussian plus Poisson-
   Asimov flux thresholds.

The repaired broadband gamma profile already contains the annihilation bump.
The standalone PARMA mono-511 sidecar is therefore excluded from every
broadband background sum in this package.

SG3B has no candidate-own 37,194-ray signal transport in the accepted data
root.  Flux thresholds use the retained SE3 full-envelope selected effective
area only as a conditional proxy, supported by the SG3B static zero-primary-ray
intersection audit.  They are not final SG3B sensitivity authority.

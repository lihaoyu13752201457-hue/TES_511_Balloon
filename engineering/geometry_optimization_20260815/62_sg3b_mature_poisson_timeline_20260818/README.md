# SG3B mature common-Poisson timeline replay

This non-overwriting package migrates the retained M05/Step05 common-time
method to SG3B:

1. stream the canonical accepted prompt and delayed SIM payloads once into a
   compact raw-deposit event catalog;
2. normalize each prompt family by `1/sum(TT_family)` and each delayed family
   by `A_family(day15)/1e6`, retaining delayed parent-ZA identity;
3. generate chronological arrivals using exponential inter-arrival times at
   the total detector-positive rate (equivalent to independent per-stream
   Poisson draws followed by merge/sort);
4. group adjacent arrivals separated by no more than 1 microsecond;
5. sum TES pixels, plastic energy, and BGO energy inside each group, then apply
   the 50 keV plastic/BGO vetoes and retained Compton/FoV selection;
6. compare the replay with package 58's direct rates and analytic live-factor
   mission fold.

The standalone PARMA mono-511 sidecar is excluded from broadband background.
No Cosima transport is run and no SIM payload is hashed.

## Closed result

- compact catalog: 55 jobs, 11,842,079 analyzed prompt-instant plus delayed
  events, 8,505,399 detector-positive templates, 66,870 raw TES pixel hits;
- direct package-58 closure: maximum absolute rate difference
  `4.440892098500626e-16 cps`;
- mature replay: five 20,000 s anchors at mission days 0, 5, 10, 15, and 20,
  totaling 2,115,936,204 sampled arrivals;
- conditional signal accidental survival: 0.967052--0.969368;
- 20-day conditional-proxy result: 88,217.12053 background counts and
  `Fmin_3sigma,Gaussian = 7.04717764e-5 ph cm^-2 s^-1`;
- package-58 analytic comparison: `7.06350747e-5 ph cm^-2 s^-1`, so the mature
  replay differs by -0.231% and does not explain the gap to `5e-5`;
- finite weighted transport diagnostic: 395 selected templates but only 9.971
  weighted effective survivors, giving 31.67% relative uncertainty on the
  integrated background estimate.

The sensitivity denominator remains the SE3 full-envelope conditional signal
proxy (`Aeff_W2,final = 11.69478 cm2`).  This package is not a final SG3B signal
or promotion authority.

# SH3 active-BGO small-aperture conditional Fmin approximation

This is a **conditional approximation**, not a full new-geometry background,
signal, or activation closure.  It uses the flux-conserving combination
`frozen other + frozen de-lined broadband gamma + new PARMA mono-511 line`.

## 20-day results

Primary, frozen SH3 signal kernel:

- Gaussian 3 sigma: `3.99874715e-05 +/- 2.24163796986e-06 ph cm^-2 s^-1`
- Poisson Asimov 3 sigma: `4.00767576216e-05 +/- 2.24165772266e-06 ph cm^-2 s^-1`

Conservative geometric signal scenario (kernel x `0.795773511857`):

- Gaussian 3 sigma: `5.02498146825e-05 +/- 2.81692961184e-06 ph cm^-2 s^-1`
- Poisson Asimov 3 sigma: `5.03620151016e-05 +/- 2.81695443397e-06 ph cm^-2 s^-1`

The geometric scenario is only a ray-clearance scaling (`29598/37194`),
not a transported signal response.  Reported errors are statistical only and do
not quantify the approximation error from frozen non-line/signal responses.

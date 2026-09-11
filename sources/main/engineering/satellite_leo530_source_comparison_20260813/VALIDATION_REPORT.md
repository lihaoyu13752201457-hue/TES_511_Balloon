# Validation report

Status: `PASS`

This validation reopens the pinned inputs and generated tables/spectra/figures. It does not grant detector-physics authority.

## Checked

- 26 hash-pinned COSI input/evidence files at commit `eec0dbf1aaabc79fea2706946434e30f7060a59a`.
- 160 corrected-keV balloon family/bin spectra; every `IP LIN` PDF closes to one.
- 20 equal-mu bins close to `4π = 12.5663706144 sr`; down/up/full source-card flux anchors close for all eight families.
- 10 LEO continuum components and 1 independent mono-line component.
- All normal COSI component card rates restore the 1000-way parallelization factor; atmospheric 511 closes at `0.028207 cm^-2 s^-1`.
- 10 physical-restored satellite unit-PDF spectra close under their declared `IP LOGLOG` interpolation.
- Invalid/unavailable bands are emitted as `NA`, never as an imputed zero; missing satellite muons stay explicitly unavailable.
- Three PNG/PDF figure pairs are nonblank and meet the minimum raster dimensions.

## Warnings retained by design

- Pinned COSI DC4 AlbedoNeutrons.source names a missing 12.6-GV file; the available 10-GV spectrum is diagnostic-only.
- COSI DC4 normal-background source-card rates are per one of 1000 parallel simulations; physical comparison rates restore ×1000. SAA is excluded and is not scaled here.
- Secondary electron/positron inputs retain 10-GV file labels and the secondary-proton card normalization differs from its spectrum-header integral.
- No orbit-time weighting, SAA residence, Galactic diffuse sky-map collapse, pointing history, or detector response is included.
- Balloon gamma is a broadband-total table with a coarse annihilation bump; the 450–600 keV result is not a line-only ratio.

# Source and normalization contract

## Energy axis

All canonical outputs use total kinetic energy in `keV_total`.

- Corrected balloon non-alpha inputs: raw MeV × 1000.
- Corrected balloon alpha inputs: raw MeV/nucleon × 4 × 1000.
- COSI DC4 alpha: already whole-particle total kinetic keV; do not multiply by four again.

## Balloon reconstruction

Each corrected balloon spectrum is a unit PDF `p_i(E)` under its declared `IP LIN` interpolation. For angular bin `i`, the source card supplies the angular-domain integrated rate `F_i` in `cm^-2 s^-1`:

```text
dF_i/dE = F_i p_i(E)
```

Each of the 20 equal-μ bins has `ΔΩ = 4π/20 = 0.6283185307 sr`. The support-average intensity is:

```text
<I_i(E)> = F_i p_i(E) / ΔΩ
```

The full/down/up curves are sums of `F_i p_i(E)`, not averages of the 20 PDFs. The far-field radius of 60 cm is not multiplied into a source-field flux comparison.

## Satellite reconstruction

COSI DC4 normal-background source cards are configured for 1000 parallel simulation shards. The physical component rate is:

```text
F_physical = 1000 F_card
```

The pinned `DP` tables provide a spectral shape under `IP LOGLOG`. This package normalizes each shape using the declared interpolation and reconstructs the card-consistent physical spectrum as:

```text
p(E) = DP(E) / integral_IP_LOGLOG DP(E) dE
dF/dE = (1000 F_card) p(E)
```

This preserves the actual DC4 card normalization even where a spectrum-header analytic integral and the card rate differ. Both values and their ratio are retained in `component_inventory.csv`.

The alternative intensity reading `1000 DP(E)` is retained only as upstream model context; it is not substituted for the card normalization in the comparison curves.

## Angular domains

- Earth-visible/albedo cone: `3.958990876756658 sr`.
- Unocculted sky: `8.607379737602514 sr`.
- Secondary-proton upstream spectrum header: `2π sr`; its DC4 Beam declaration does not preserve that interpretation exactly, so this package compares angular-domain integrated flux rather than claiming a local intensity.
- Balloon down/up hemispheres: `2π sr` each.

Components with different angular domains may be added only as angular-domain integrated incident rates. Their sum is not described as a uniform per-sr intensity.

## Gamma policy

- Balloon `unit_only_total_gamma` is broadband total and already contains a coarse annihilation bump. No mono-511 may be added.
- Satellite atmospheric 511 is an independent delta line with restored integrated flux `0.028207 cm^-2 s^-1`.
- A delta line is never plotted as a finite continuous `dF/dE`. The 450–600 keV result is explicitly an annihilation-region proxy, not a line-only flux ratio.

## Profile exclusions

- SAA proton: excluded from static normal-science prompt; requires orbit residence, instrument-off policy, activation, and post-SAA delayed treatment.
- Galactic diffuse: excluded from the local environmental family sum; requires directional sky and pointing integration.
- Muons: unavailable in the pinned COSI DC4 library and emitted as `NA`, never zero.
- Neutron: pinned 10-GV file is diagnostic-only because the DC4 source card declares a missing 12.6-GV filename.

## Interpolation and integration

- `IP LIN` / `IP LinLin`: linear in energy and density; integrate by the exact segment trapezoid.
- `IP LOGLOG`: power-law interpolation and analytic segment integral where both endpoints are positive; zero-boundary segments use linear interpolation.
- No extrapolation outside file support.
- Band ratios require nonempty cited model-valid support. Missing or invalid bands are `NA`.


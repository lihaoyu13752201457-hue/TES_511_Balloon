# ATM511 EXPACS-Like Sidecar Source Model - 2026-07-08

Status: `PAPER_IMPLEMENTABLE_SEMI_EMPIRICAL_4PI_ATM511_SIDECAR`

## Purpose

This file defines the atmospheric 511-keV line background model to supplement
the EXPACS/PARMA atmospheric gamma continuum.

The modeled component is:

```text
atmospheric e+e- annihilation 511-keV line background
```

It is not:

```text
Galactic/celestial 511-keV signal
instrument-internal positron annihilation
EXPACS/PARMA native photon continuum
```

The source is implemented as a separate mono-energetic line source. Do not insert
it into the EXPACS gamma continuum PDF as a `keV^-1` table point.

Local evidence that the EXPACS gamma table skips the line is archived at:

```text
engineering/geometry_optimization_20260704/11_expacs_atm511_line_gap_20260707/
```

## Environment Hook

The model can use the same latitude, longitude, altitude, and date information
as the EXPACS/PARMA source generation.

For each trajectory point or static source condition:

```text
input: latitude, longitude, altitude, date/solar condition
from EXPACS/PARMA or trajectory metadata:
  Rc_GV = geomagnetic cutoff rigidity
  X_g_cm2 = residual atmospheric depth
```

Then:

```text
Phi511_4pi(lat, lon, alt, date)
  = Phi_ref * f_R(Rc_GV) * g_X(X_g_cm2) * f_solar(date)
```

So the latitude/longitude/altitude dependence enters through `Rc_GV` and
`X_g_cm2`. The 511-keV line is not a native EXPACS database output; it is an
EXPACS-like sidecar evaluated on the same environmental grid.

Current project reference metadata examples:

```text
static EXPACS source inventory:
  latitude = 34 deg
  longitude = 100 deg
  altitude = 38 km
  Rc = 11.6 GV

Step06 trajectory driver:
  calls PARMA with latitude, longitude, altitude
  reads Rc_GV_parma and depth_g_cm2_parma
```

Use the actual `Rc_GV` and `depth_g_cm2` attached to the run being evaluated.
Do not hard-code one depth for all trajectory points.

## Coordinate Convention

Use the same incident zenith convention as the current MEGAlib/Cosima source
cards:

```text
theta = 0 deg      photon enters from above / residual atmosphere
theta = 90 deg     horizon
theta = 180 deg    photon enters from below / Earth albedo
```

Define:

```text
downward residual-atmosphere component: 0 <= theta < 90 deg
upward Earth-albedo component:          90 <= theta <= 180 deg

mu_d = cos(theta)       for 0--90 deg
mu_u = -cos(theta)      for 90--180 deg
```

## Total Line Flux

Use a line-integrated flux, not a per-keV differential continuum value.

Reference normalization:

```text
Phi_ref = 0.10 ph cm^-2 s^-1
X_ref = 3.6 g cm^-2
Rc_ref = <7 GV / low-cutoff balloon reference
```

This is anchored to balloon measurements of the atmospheric 0.51-MeV line at
near-float residual depth. It should be treated as a quasi-omnidirectional
balloon normalization with systematic uncertainty.

Recommended normalization scenarios:

| Scenario | Phi_ref [ph cm^-2 s^-1] | Role |
|---|---:|---|
| low | 0.03 | conservative low |
| nominal | 0.10 | paper baseline |
| high | 0.20 | conservative high |
| extreme | 0.60 | low-cutoff/high-latitude stress only |

For the current `Rc~11--13 GV` reference condition, the nominal total line flux
before angular splitting is roughly:

```text
Phi511_4pi ~= 0.10 * 0.532 = 5.32e-2 ph cm^-2 s^-1
```

at `X ~= X_ref` and `f_solar = 1`.

## Rigidity Dependence

Use the Harris/SMM 0.511-MeV line rigidity factors:

| Vertical cutoff rigidity | f_R |
|---|---:|
| `<7 GV` | 1.000 |
| `7--9 GV` | 0.805 |
| `9--11 GV` | 0.624 |
| `11--13 GV` | 0.532 |
| `>13 GV` | 0.479 |

Reproducible step-function implementation:

```python
def f_R_harris(Rc_GV):
    if Rc_GV < 7:
        return 1.000
    if Rc_GV < 9:
        return 0.805
    if Rc_GV < 11:
        return 0.624
    if Rc_GV < 13:
        return 0.532
    return 0.479
```

This factor is directly measured for the atmospheric 0.511-MeV line in the SMM
Earth-albedo context. Applying it to the total balloon 4pi line sidecar is the
baseline assumption.

## Altitude / Depth Dependence

For balloon float conditions, use:

```text
g_X(X) = (X / X_ref)^eta
X_ref = 3.6 g cm^-2
eta_nominal = 0.8
eta_systematic = 0.5--1.0
```

This is an empirical depth parameterization, not a native EXPACS output and not
a recovered universal Ling `F511(X)` table. It is paper-usable only with the
systematic bracket above.

Do not use the EXPACS smooth gamma continuum depth dependence as the 511-line
depth law unless it is explicitly declared as a cross-check proxy.

## Solar / Date Dependence

Nominal:

```text
f_solar(date) = 1.0
```

Systematic:

```text
f_solar = 1.0 +/- 0.10
```

If a trajectory-specific EXPACS/PARMA secondary electromagnetic proxy is later
used, document whether that proxy already contains solar/rigidity trends to
avoid double counting.

## Upward / Downward Split

Split the total line flux into upward albedo and downward residual-atmosphere
components:

```text
r_down(X) = Phi_down / Phi_up
          = min(1, r0 * (X / X_ref)^beta)

r0_nominal = 0.20
r0_systematic = 0.05--0.50
beta_nominal = 0.5
beta_systematic = 0.5--1.0

Phi_up = Phi511_4pi / (1 + r_down)
Phi_down = r_down * Phi511_4pi / (1 + r_down)
```

At `X=X_ref`, `Rc=11--13 GV`, and nominal parameters:

```text
Phi511_4pi = 5.32e-2 ph cm^-2 s^-1
r_down = 0.20
Phi_up = 4.433e-2 ph cm^-2 s^-1
Phi_down = 8.867e-3 ph cm^-2 s^-1
```

The nonzero downward component is required because the residual atmosphere above
the payload can produce 511-keV photons. Its exact angular law is less directly
measured than the albedo law, so it must remain a systematic model component.

## Angular Distribution

### Upward / Albedo: 90--180 deg

Use the HEAO-3 / Harris limb-darkening law over the albedo hemisphere:

```text
a = 1.7
mu_u = -cos(theta)

I_up(theta)
  = Phi_up / [2*pi*(1 + a/2)] * (1 + a*mu_u)
```

This is normalized so that:

```text
integral over 90--180 deg of I_up dOmega = Phi_up
```

This part has the strongest literature support. It is an albedo/Earth-disk law,
not a full-4pi law by itself.

### Downward / Residual Atmosphere: 0--90 deg

Use a conservative slab-production/escape kernel:

```text
mu_d = cos(theta)
Lambda_511 = 11.5 g cm^-2

K_down(theta, X)
  = 1 - exp[-X / (Lambda_511 * mu_d)]

A(X) = integral_0^1 K_down(mu, X) dmu

I_down(theta)
  = Phi_down / [2*pi*A(X)] * K_down(theta, X)
```

`Lambda_511` comes from the air mass attenuation scale near 511 keV:

```text
mu/rho ~= 8.7e-2 cm^2 g^-1
Lambda_511 ~= 1/(mu/rho) ~= 11.5 g cm^-2
```

This downward kernel is a physics-motivated systematic model. It is not a
dedicated measured 511-keV downward angular law.

## Bin Conversion

For each source-card zenith bin:

```text
theta1 <= theta <= theta2
phi = 0--360 deg
```

the bin-integrated line flux is:

```text
Phi_i = 2*pi * integral_theta1^theta2 I_511(theta) sin(theta) dtheta
```

and the solid angle is:

```text
DeltaOmega_i = 2*pi * [cos(theta1) - cos(theta2)]
```

Use `Phi_i` as the Cosima source `Flux` if the source card is configured with
integrated flux per source component.

Important:

```text
Phi_i is line-integrated ph cm^-2 s^-1.
Do not divide by the TES energy window.
Do not convert it into keV^-1.
```

Use the actual EXPACS bin edges used in the run. The current full-sphere source
inventory uses equal-mu bins, not uniform 9-degree bins.

## Cosima Source Pattern

For each bin:

```text
Atm511_binXX.ParticleType 1
Atm511_binXX.Beam FarFieldAreaSource theta1 theta2 0.000 360.000
Atm511_binXX.Spectrum Mono 511
Atm511_binXX.Flux Phi_i
```

Keep the EXPACS/PARMA atmospheric gamma continuum source unchanged and add this
ATM511 sidecar as a separate run or separately tagged source component.

Recommended bookkeeping categories:

```text
EXPACS atmospheric gamma continuum
ATM511 upward/albedo line
ATM511 downward/residual-atmosphere line
EXPACS e+ / e- / proton / neutron / muon / alpha components
Delayed activation
Instrument-internal 511
Celestial 511 signal
```

## Claim Boundary

Paper-safe statement:

```text
We supplement the PARMA/EXPACS atmospheric photon continuum with a separate
semi-empirical atmospheric positron-annihilation line background at 511 keV.
The line normalization is anchored to balloon measurements, scaled with the
Harris/SMM 0.511-MeV cutoff-rigidity dependence, and evaluated on the same
latitude/longitude/altitude environmental grid as the EXPACS/PARMA sources.
The upward albedo angular distribution follows the HEAO-3/SMM limb-darkening
law. The downward residual-atmosphere contribution is included with a
conservative slab kernel and propagated as a systematic bracket.
```

Do not claim:

```text
EXPACS/PARMA natively predicts this narrow line.
The true full-4pi atmospheric 511-keV angular distribution is known.
The downward residual-atmosphere law is directly measured at the same quality as
the albedo limb-darkening law.
The total line normalization is known better than the systematic bracket.
```

## Minimum Systematic Runs

| Run | Phi_ref | eta | r0 | Description |
|---|---:|---:|---:|---|
| S0 | 0 | - | - | no ATM511 control |
| S1 | 0.10 | 0.8 | 0.20 | nominal |
| S2 | 0.03 | 0.5 | 0.05 | conservative low |
| S3 | 0.20 | 1.0 | 0.50 | conservative high |
| S4 | 0.10 | 0.8 | 0.00 | albedo-only comparison |
| S5 | 0.60 | 0.8 | 0.20 | low-cutoff/high-latitude stress only |

All nonzero runs still multiply by `f_R(Rc_GV)` and `g_X(X_g_cm2)` for the
actual environment.

## References

- Peterson, Schwartz & Ling 1973, balloon atmospheric gamma spectrum to 10 MeV:
  `https://ntrs.nasa.gov/citations/19740032603`
- Ling & Gruber 1977, atmospheric gamma angular distributions at 2.5 and
  70 g cm^-2:
  `https://ntrs.nasa.gov/citations/19770044477`
- Mahoney, Ling & Jacobson 1981, HEAO-3 atmospheric positron annihilation line:
  `https://ntrs.nasa.gov/citations/19820033317`
- Harris, Share & Leising 2003, SMM atmospheric gamma-ray line variability:
  `https://arxiv.org/abs/physics/0308082`
- Takada et al. 2011, balloon gamma-ray growth-curve treatment with explicit
  atmospheric 511-keV line term:
  `https://arxiv.org/abs/1103.3436`
- NIST XCOM air attenuation coefficients:
  `https://physics.nist.gov/PhysRefData/XrayMassCoef/ComTab/air.html`
- Local EXPACS missing-line evidence:
  `engineering/geometry_optimization_20260704/11_expacs_atm511_line_gap_20260707/README.md`

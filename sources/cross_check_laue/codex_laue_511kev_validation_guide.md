# Codex Guide: 511 keV Ge(111) Laue Optics Validation and MEGAlib Bridge

This guide is meant for Codex to turn the current `opticsim` Laue prototype into a validated, reproducible simulation chain.

## 0. High-level goal

Build a defensible simulation workflow for a 480-550 keV, Ge(111), five-ring Laue front-end optics model for a balloon 511 keV TES detector project.

The correct architecture is:

```text
Independent Laue reference / oracle
    -> validates optics kernel and phase-space
Custom Geant4 boundary process
    -> implements the optics kernel inside the current opticsim app
MEGAlib/Cosima detector simulation
    -> consumes phase-space and simulates detector/mass/background response
```

Do **not** rely on Geant4 alone to validate Laue diffraction. Geant4 official `G4XrayReflection` is low-energy surface reflection, not 511 keV bulk Laue diffraction. Guan/Reiazi-style Geant4 Bragg processes are useful design references, but no mature public 511 keV Ge(111) Laue-lens package should be assumed.

## 1. Existing implementation summary

Current implementation, based on the project notes:

- source: `/home/ubuntu/opticsim/geant4_app/src/laue_multiring_darwin_guan_demo.cc`
- ring CSV: `/home/ubuntu/opticsim/data/laue/ge111_480_550keV_multiring_darwin_config.csv`
- model: strongly forced Geant4 discrete process registered for gamma
- trigger: only at `LaueCrystal` geometry boundaries
- branches: `ABSORB`, `TRANSMIT`, `DIFFRACT`
- probability: online Darwin-Hamilton mosaic probabilities
- outputs:
  - `optics_history.csv`
  - `phase_space.csv`
  - `transmitted_space.csv`

Current important limitation:

```text
latest opticsim phase_space.csv -> MEGAlib/Cosima EventList source
```

is not yet a production bridge. Build it as a first-class module.

## 2. Repository layout to create

Create this structure under the project root or a new `laue511_validation/` folder:

```text
laue511_validation/
  README.md
  pyproject.toml
  data/
    laue/
      ge111_480_550keV_multiring_darwin_config.csv
    external/
      README.md
  laue511/
    __init__.py
    constants.py
    geometry.py
    materials.py
    bragg.py
    mosaic.py
    probabilities.py
    sampling.py
    phase_space.py
    cosima_bridge.py
    metrics.py
  tools/
    laue_sanity.py
    single_tile_scan.py
    single_ring_benchmark.py
    full_lens_benchmark.py
    convert_phase_space_to_cosima.py
    plot_optics_outputs.py
    compare_geant4_vs_reference.py
  benchmarks/
    reference_outputs/
      README.md
    xop_crystal/
      README.md
    xrt_pytte/
      README.md
    heart/
      README.md
  tests/
    test_bragg_geometry.py
    test_probabilities.py
    test_sampling_conservation.py
    test_phase_space_schema.py
    test_cosima_bridge_schema.py
  reports/
    README.md
```

## 3. Dependencies

Use Python first for the reference kernel.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install numpy pandas scipy matplotlib pydantic pytest click rich
```

Optional later:

```bash
pip install xraylib
```

Only add external tools such as XOP/SHADOW/xrt/pyTTE/HEART after the pure reference kernel and schema tests are stable.

## 4. Core data schema

### 4.1 Ring configuration

Input CSV columns:

```text
ring_id,design_energy_keV,radius_mm,n_tiles,material,h,k,l,d_spacing_A,tile_size_mm,thickness_mm
```

Known Ge(111) rows:

```text
0,480.0,65.644327,72,Ge,1,1,1,3.266590088,0.8,9.452263
1,500.0,63.018438,72,Ge,1,1,1,3.266590088,0.8,9.947306
2,511.0,61.661820,72,Ge,1,1,1,3.266590088,0.8,10.218801
3,530.0,59.451215,72,Ge,1,1,1,3.266590088,0.8,10.686285
4,550.0,57.289274,72,Ge,1,1,1,3.266590088,0.8,11.176250
```

### 4.2 Photon input schema

Use a dataframe or Pydantic model with:

```text
event_id:int
photon_id:int
E_keV:float
x_mm:float
y_mm:float
z_mm:float
dx:float
dy:float
dz:float
time_s:float
weight:float
source_tag:str
offaxis_x_rad:float
offaxis_y_rad:float
```

### 4.3 Optics history schema

Every intercepted photon should output:

```text
event_id,photon_id,mode,branch
ring_id,tile_id
E_actual_keV,E_design_keV
x_mm,y_mm,z_mm
dx_in,dy_in,dz_in
dx_out,dy_out,dz_out
path_length_cm,mu_cm_inv,attenuation
p_diff_raw,p_trans_raw,p_abs_raw,prob_sum_raw,prob_residual,renormalized_flag
thetaB_design_rad,thetaB_actual_rad
delta_theta_design_rad,delta_theta_actual_rad
mosaic_mode,microcrystal_dx,microcrystal_dy,microcrystal_dz
random_seed
```

### 4.4 Phase-space output schema

For `DIFFRACT` branch:

```text
event_id,photon_id,parent_id
E_keV
x_mm,y_mm,z_mm
dx,dy,dz
time_s
weight
ring_id,tile_id
branch
source_tag
offaxis_x_rad,offaxis_y_rad
```

For `TRANSMIT` branch, use the same schema and write to `transmitted_space.csv`.

## 5. Implement the pure reference kernel first

Do not start by editing the Geant4 process. First implement a pure reference kernel in `laue511/`.

### 5.1 Bragg geometry

In `bragg.py`:

```python
def wavelength_A(E_keV: float) -> float:
    return 12.398419843320026 / E_keV


def bragg_angle_rad(E_keV: float, d_spacing_A: float, order: int = 1) -> float:
    lam = wavelength_A(E_keV)
    arg = order * lam / (2.0 * d_spacing_A)
    if abs(arg) > 1.0:
        raise ValueError("No Bragg solution")
    return np.arcsin(arg)


def ring_radius_mm(focal_length_mm: float, thetaB_rad: float) -> float:
    return focal_length_mm * np.tan(2.0 * thetaB_rad)
```

Test the 511 keV ring:

```text
E = 511 keV
lambda ≈ 0.02426 Å
d111 = 3.266590088 Å
thetaB ≈ 0.213 deg
2thetaB ≈ 0.426 deg
R = 61.661820 mm
f ≈ 8.30 m
```

### 5.2 Path length

In `geometry.py`, compute true slab chord length:

```python
def slab_path_length_cm(thickness_mm: float, incoming_dir: np.ndarray, slab_normal: np.ndarray) -> float:
    cos_inc = abs(np.dot(unit(incoming_dir), unit(slab_normal)))
    if cos_inc <= 0:
        return np.inf
    return (thickness_mm / 10.0) / cos_inc
```

Do not hard-code `thickness / cos(thetaB)` as the only path-length model. Keep it as a legacy option for comparison.

### 5.3 Absorption

In `materials.py`, start with hard-coded NIST/XCOM interpolation values for Ge, then add xraylib or a table loader later.

At minimum include values around 0.5-0.6 MeV from NIST Germanium table, and expose:

```python
def ge_mu_cm_inv(E_keV: float, density_g_cm3: float = 5.323) -> float:
    """Return linear attenuation coefficient mu in 1/cm."""
```

### 5.4 Mosaic sampling

Implement two modes:

```text
probability_only
microcrystal_sampled
```

Recommended default: `microcrystal_sampled`.

Algorithm:

1. Sample a microcrystal plane-normal perturbation from the mosaic FWHM.
2. Use the sampled normal to compute actual Bragg mismatch.
3. Use the same sampled normal to compute outgoing diffracted direction.
4. Do not also apply an independent mosaic Gaussian weight unless explicitly in a comparison mode.

### 5.5 Probability kernel

In `probabilities.py`, implement current model but keep raw terms visible:

```python
def darwin_hamilton_mosaic_probabilities(...):
    # return raw p_diff, p_trans, p_abs, attenuation, residual diagnostics
```

Rules:

- Never silently normalize by default.
- If normalization is requested, set `renormalized_flag=True` and record raw sum.
- Add strict mode: fail if `abs(1 - prob_sum_raw) > threshold`.

### 5.6 Branch sampling

In `sampling.py`:

```python
def sample_branch(p_abs, p_diff, p_trans, rng):
    u = rng.random()
    if u < p_abs:
        return "ABSORB"
    if u < p_abs + p_diff:
        return "DIFFRACT"
    return "TRANSMIT"
```

Keep branch ordering consistent across reference and Geant4.

## 6. Unit tests

Run:

```bash
pytest -q
```

Required tests:

### 6.1 Bragg geometry

`tests/test_bragg_geometry.py`:

- 511 keV Ge(111) Bragg angle near 0.213 deg
- 511 keV ring radius recovers focal length near 8.30 m
- all five ring rows pass radius consistency check

### 6.2 Probability conservation

`tests/test_probabilities.py`:

- `p_abs >= 0`, `p_trans >= 0`, `p_diff >= 0`
- raw sum recorded
- strict mode warns/fails on large residual
- no silent normalization

### 6.3 Sampling reproducibility

`tests/test_sampling_conservation.py`:

- fixed random seed produces identical branch counts
- Monte Carlo branch fractions converge to input probabilities

### 6.4 Phase-space schema

`tests/test_phase_space_schema.py`:

- all mandatory columns present
- direction vectors are normalized
- weights are positive
- event provenance preserved

### 6.5 Cosima bridge schema

`tests/test_cosima_bridge_schema.py`:

- phase-space rows convert to a source/EventList format
- no loss of energy, position, direction, weight, time
- ring/tile provenance preserved in sidecar metadata

## 7. Benchmarks

### 7.1 Single-tile benchmark

Command:

```bash
python tools/single_tile_scan.py \
  --material Ge --hkl 1 1 1 \
  --energy-kev 511 \
  --thickness-mm 10.218801 \
  --mosaic-fwhm-arcsec 30 \
  --delta-theta-range-arcsec -300 300 \
  --n-angle 601 \
  --out reports/single_tile_ge111_511keV.csv
```

Plot:

```bash
python tools/plot_optics_outputs.py \
  --input reports/single_tile_ge111_511keV.csv \
  --kind single_tile \
  --out reports/single_tile_ge111_511keV.png
```

Metrics:

```text
peak_reflectivity
integrated_reflectivity
rocking_fwhm
attenuation/transmission
```

Compare against any available one or more of:

- XOP/CRYSTAL/SHADOW
- xrt/pyTTE
- HEART
- analytic/Darwin-Hamilton notebook

### 7.2 Single-ring benchmark

Command:

```bash
python tools/single_ring_benchmark.py \
  --ring-id 2 \
  --config data/laue/ge111_480_550keV_multiring_darwin_config.csv \
  --energy-kev 511 \
  --n-photons 100000 \
  --seed 12345 \
  --out-dir reports/single_ring_511
```

Metrics:

```text
N_diff/N_total
N_trans/N_total
N_abs/N_total
focal_centroid_x/y
PSF_FWHM
HPD
p_diff distribution
p_trans distribution
p_abs distribution
delta_theta distribution
```

### 7.3 Five-ring full-lens benchmark

Command:

```bash
python tools/full_lens_benchmark.py \
  --config data/laue/ge111_480_550keV_multiring_darwin_config.csv \
  --energy-range-kev 480 550 \
  --spectrum flat \
  --n-photons 500000 \
  --seed 12345 \
  --out-dir reports/full_lens_480_550
```

Metrics:

```text
effective_area_vs_energy
PSF_vs_energy
ring_contribution_vs_energy
branch_fractions_vs_energy
focal_plane_hit_map
phase_space_direction_distribution
```

## 8. Geant4 integration changes

After the pure reference kernel is stable, refactor the Geant4 process.

### 8.1 Extract kernel

Move physics logic out of `PostStepDoIt` into a reusable module.

Ideal C++ API:

```cpp
struct LauePhotonInput {
  double E_keV;
  Vec3 position_mm;
  Vec3 direction;
  double time_s;
  double weight;
  int event_id;
  int photon_id;
};

struct LaueTileConfig {
  int ring_id;
  int tile_id;
  double design_energy_keV;
  double d_spacing_A;
  double thickness_mm;
  double tile_size_mm;
  std::array<int,3> hkl;
  std::string material;
};

struct LaueResult {
  std::string branch;
  Vec3 output_direction;
  double p_diff_raw;
  double p_trans_raw;
  double p_abs_raw;
  double prob_sum_raw;
  double path_length_cm;
  double delta_theta_actual_rad;
  bool renormalized;
};

LaueResult EvaluateLaueInteraction(const LauePhotonInput&, const LaueTileConfig&, const LaueOptions&);
```

`PostStepDoIt` should only:

1. detect valid boundary;
2. construct input structs;
3. call `EvaluateLaueInteraction`;
4. apply `G4ParticleChange` according to mode;
5. write diagnostics.

### 8.2 Add mode switch

Add runtime option:

```text
--laue-mode optics-phase-space
--laue-mode full-transport
```

Behavior:

```text
optics-phase-space:
  ABSORB    -> kill
  DIFFRACT  -> add secondary, kill primary
  TRANSMIT  -> record transmitted_space, kill or optionally stop at scorer

full-transport:
  ABSORB    -> kill
  DIFFRACT  -> add secondary, kill primary
  TRANSMIT  -> continue primary or add equivalent transmitted secondary
```

### 8.3 Add diagnostics

Every event must include:

```text
mode
E_actual_keV,E_design_keV
thetaB_actual,thetaB_design
delta_theta_actual,delta_theta_design
path_length_cm
prob_sum_raw
prob_residual
renormalized_flag
mosaic_mode
random_seed
```

## 9. MEGAlib/Cosima bridge

Create:

```text
tools/convert_phase_space_to_cosima.py
```

Inputs:

```text
phase_space.csv
transmitted_space.csv optional
metadata.json
```

Outputs:

```text
cosima_eventlist.source or equivalent
phase_space_sidecar.json
bridge_summary.json
```

The bridge must preserve:

```text
event_id
photon_id
energy
position
direction
time
weight
ring_id
tile_id
branch
source_tag
off-axis metadata
random seed/provenance
```

Bridge validation:

```bash
python tools/convert_phase_space_to_cosima.py \
  --input reports/full_lens_480_550/phase_space.csv \
  --output reports/full_lens_480_550/cosima_eventlist.source \
  --metadata reports/full_lens_480_550/bridge_summary.json

pytest -q tests/test_cosima_bridge_schema.py
```

## 10. External reference plan

### 10.1 Try to obtain LLL

Document the status in:

```text
benchmarks/reference_outputs/LLL_STATUS.md
```

Include:

```text
source/contact
version/commit if available
license/access status
input config used
output files generated
known differences from our kernel
```

If LLL is unavailable, write:

```text
benchmarks/reference_outputs/LLL_NOT_AVAILABLE.md
```

and proceed with the LLL-compatible reference kernel.

### 10.2 XOP/CRYSTAL benchmark

Store manually or automatically exported reference curves in:

```text
benchmarks/xop_crystal/ge111_511keV_rocking_curve.csv
```

Required columns:

```text
delta_theta_rad,reflectivity,transmittivity,absorption,source_tool,source_version
```

### 10.3 xrt/pyTTE benchmark

Store output in:

```text
benchmarks/xrt_pytte/ge111_511keV_rocking_curve.csv
```

### 10.4 HEART benchmark

Store output in:

```text
benchmarks/heart/ge111_511keV_mosaic_curve.csv
```

## 11. Acceptance criteria

Use these as initial gates:

```text
Bragg geometry:
  ring radius/focal length consistency < 1e-6 relative

Single-crystal physics:
  peak reflectivity within 5-10% vs reference
  integrated reflectivity within 5-10% vs reference
  rocking FWHM within 5-10% vs reference
  attenuation/transmission within 3-5% vs NIST/XCOM-based calculation

Single-ring optics:
  focal centroid within 0.1 mm or one-tenth detector pixel pitch
  PSF FWHM within 5-10% vs reference
  branch fractions within Monte Carlo 3 sigma

Full-lens optics:
  effective area within 10% vs reference
  PSF/HPD within 10% vs reference
  ring-wise contribution trend consistent

Bridge:
  zero schema loss for energy/position/direction/time/weight/provenance
  Cosima source sanity run completes
```

## 12. Reports to generate

Every benchmark run must produce:

```text
run_config.json
provenance.json
optics_history.csv
phase_space.csv
transmitted_space.csv
metrics.json
summary.md
plots/*.png
```

For Geant4/reference comparison:

```bash
python tools/compare_geant4_vs_reference.py \
  --reference reports/full_lens_480_550/reference_metrics.json \
  --geant4 stepwise_maintenance/step04_opticsim/outputs/opticsim_laue_guan_smoke5000/metrics.json \
  --out reports/geant4_vs_reference
```

## 13. Important writing boundary

When documenting this project, use this wording:

```text
We implement a custom Laue optics kernel and couple it to Geant4/MEGAlib through a phase-space bridge. The kernel is benchmarked against independent Laue-lens and single-crystal diffraction tools.
```

Avoid this wording:

```text
Geant4/MEGAlib natively supports 511 keV Laue diffraction.
```

## 14. Reference URLs for documentation

- Laue Lens Library: https://larixfacility.unife.it/?page_id=309
- ASTENA: https://larixfacility.unife.it/?page_id=506
- ASTENA AHEAD presentation: https://indico.lip.pt/event/750/contributions/2547/attachments/2169/2985/ASTENA_AHEAD_Coimbra_Online_Meeting_1-2_October_2020.pdf
- Frontera 2025 Laue lens review: https://arxiv.org/abs/2502.10845
- LaueGen: https://arxiv.org/abs/1405.7269
- XOP / SHADOW BRAGG: https://www.esrf.fr/computing/scientific/people/srio/publications/sri95_xop.pdf
- CRYSTAL: https://github.com/srio/CRYSTAL
- xrt tests: https://xrt.readthedocs.io/test_materials.html
- pyTTE: https://github.com/aripekka/pyTTE
- HEART: https://gitlab.com/heart-ray-tracing/HEART
- NIST XCOM: https://www.nist.gov/pml/x-ray-mass-attenuation-coefficients
- NIST Germanium table: https://physics.nist.gov/PhysRefData/XrayMassCoef/ElemTab/z32.html
- Geant4 X-Ray Reflection: https://geant4.web.cern.ch/documentation/dev/prm_html/PhysicsReferenceManual/electromagnetic/gamma_incident/xrayreflection/G4XrayReflection.html
- Guan et al. G4CrystalBraggReflection: https://pubmed.ncbi.nlm.nih.gov/40336621/
- Reiazi et al. G4BraggReflection: https://mdanderson.elsevierpure.com/en/publications/g4braggreflection-for-accurate-modeling-of-bragg-reflection-in-pe-2/
- MEGAlib: https://megalibtoolkit.com/

# Claude Fable 5 Review Prompt: Can `opticsim_full` Simulate Laue Option 3?

Date: 2026-06-11

Reviewer target: Claude Fable 5

Purpose: review whether the current GitHub/local `opticsim_full` simulation
system can credibly simulate the proposed Laue lens "Option 3"
(`GE_MULTIHKL_LINE200_STRETCH`) and what minimum changes are needed before using
it as an optical authority for `TES_511_Balloon`.

Do not treat this prompt as a request to run a full production simulation. The
task is a technical review and implementation plan.

## 1. The Decision We Need

The user has a design slide `laue.png` and states that the lens effective area
is a known design parameter:

- `A_eff = 200 cm^2`

We need to decide:

1. Is the GPT_pro "Option 3" geometry physically and computationally suitable as
   the 511-keV `A_eff ~200 cm^2` Laue lens model?
2. Can the current `opticsim_full` code simulate Option 3 with credible
   `A_eff`, PSF, focal-crossing, and Be-window handoff products?
3. If not yet, what exact minimal code/data changes are required?
4. What is safe to use now for `TES_511_Balloon`: mass model only, optical
   source model, or full science authority?

## 2. Important Local Paths

Main optical simulation repo:

- `/home/ubuntu/opticsim/opticsim_full`

Key files:

- `/home/ubuntu/opticsim/opticsim_full/Project_Introduction.md`
- `/home/ubuntu/opticsim/opticsim_full/docs/laue_latest_discussion_20260611.md`
- `/home/ubuntu/opticsim/opticsim_full/CMakeLists.txt`
- `/home/ubuntu/opticsim/opticsim_full/analysis/run_bfull_f9m.sh`
- `/home/ubuntu/opticsim/opticsim_full/analysis/run_with_geant4_114.sh`
- `/home/ubuntu/opticsim/opticsim_full/geant4_app/src/laue_multiring_bfull_demo.cc`
- `/home/ubuntu/opticsim/opticsim_full/geant4_app/src/optics/LaueEfficiencyTable.cc`
- `/home/ubuntu/opticsim/opticsim_full/data/laue/`

Design slide and old project context:

- `/home/ubuntu/codex_tes_511_sim/new_geo_re/laue.png`
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/Project_Memory.md`
- `/home/ubuntu/codex_tes_511_sim/new_geo_re/Project_List.md`

GPT_pro Laue design package:

- `/home/ubuntu/laue_design/opticsim_full_laue_geometry_system/README.md`
- `/home/ubuntu/laue_design/opticsim_full_laue_geometry_system/configs/laue_design_constraints_200cm2.json`
- `/home/ubuntu/laue_design/opticsim_full_laue_geometry_system/outputs/laue_geometry/bundle_summary.json`
- `/home/ubuntu/laue_design/opticsim_full_laue_geometry_system/outputs/laue_geometry/GE_MULTIHKL_LINE200_STRETCH.json`
- `/home/ubuntu/laue_design/opticsim_full_laue_geometry_system/outputs/laue_geometry/GE_MULTIHKL_LINE200_STRETCH_rings.csv`
- `/home/ubuntu/laue_design/opticsim_full_laue_geometry_system/outputs/laue_geometry/GE_MULTIHKL_LINE200_STRETCH_crystals.csv`
- `/home/ubuntu/laue_design/opticsim_full_laue_geometry_system/figures/effective_area_summary.png`
- `/home/ubuntu/laue_design/opticsim_full_laue_geometry_system/figures/GE_MULTIHKL_LINE200_STRETCH_layout.png`

Target detector/background project:

- `/home/ubuntu/TES_511_Balloon`
- `/home/ubuntu/TES_511_Balloon/MIGRATION_DIRECTORY.md`

## 3. What `laue.png` Says

The slide `laue.png` gives these design-level requirements:

- Material of focus lens: `Ge(111)`
- Energy range: `450 keV ~ 550 keV`
- Field of view: `5 arcmin`
- Spatial resolution: `2 arcmin (5.8 mm)` at 10 m
- Pointing accuracy: `15 arcsec`
- Pointing stability: `10 arcsec`
- Focus area: `100 cm^2`
- Focus length: `10 m`
- Size: diameter `40 cm` by axial envelope `30 cm`
- Working temperature: `20 +/- 5 C`

User-supplied extra authority:

- `A_eff = 200 cm^2` is known and should be treated as a design parameter.

Important distinction for review:

- `Focus area = 100 cm^2` is not automatically `A_eff`.
- The user is now explicitly stating `A_eff = 200 cm^2`; review whether and how
  a simulation model can represent that, not whether the slide text alone proves
  it.

## 4. Existing Current `opticsim_full` Model

The clean `opticsim_full` repo currently represents the old/current B-FULL
Ge(111) f=9 m authority:

- Model name in docs: `balloon511_f9m_ge111_511line`
- Geant4 executable: `laue_multiring_bfull_demo`
- Physics implementation:
  - application-level `G4VDiscreteProcess`
  - process name: `BFullLaueBraggProcess`
  - finite equivalent Laue diffraction mean free path
  - competes with standard Geant4 EM processes
  - not a Geant4 toolkit patch
  - not MEGAlib native Laue physics
- Current authority numbers in docs:
  - `A_eff(511) = 15.29928 cm^2`
  - focal length `9000 mm`
  - single 511-keV Ge(111) ring
  - 27 tiles of `15 mm`
  - optical focal `r99 = 0.291410 cm`
  - Be window radius `1.898 cm`

Current default input files:

- `data/laue/ge111_balloon511_f9m_511keV_line_config.csv`
- `data/laue/ge111_balloon511_f9m_511keV_xop_map.csv`
- `data/laue/ge111_511keV_rocking_curve.csv`
- `data/laue/Ge111_480_550keV_darwin_mosaic_table.csv`

Current run command:

```bash
cd /home/ubuntu/opticsim/opticsim_full
analysis/run_bfull_f9m.sh
```

Outputs from one run:

- `summary.json`
- `per_ring_summary.csv`
- `per_ring_summary.json`
- `phase_space.csv`
- `focal_crossings.csv`
- `transmitted_space.csv`
- `optics_history.csv`
- `laue_multiring_scene.wrl`

Downstream rule:

- Science handoff should use tracked `focal_crossings.csv`, especially
  `source_tag=laue_bfull_diffracted`, not `phase_space.csv`.

## 5. What GPT_pro Option 3 Is

Option 3 ID:

- `GE_MULTIHKL_LINE200_STRETCH`

Claim level from GPT_pro package:

- `STRETCH_LINE_511_200CM2_CLASS__RELAXES_SINGLE_GE111_AND_RESOLUTION_RISK`

Core parameters from
`/home/ubuntu/laue_design/opticsim_full_laue_geometry_system/outputs/laue_geometry/GE_MULTIHKL_LINE200_STRETCH.json`:

- Material: Ge
- HKL set: `111`, `220`, `311`, `400`
- Energy range: `450-550 keV`
- Line energy: `511 keV`
- Focal length: `1000 cm`
- Lens outer diameter: `40 cm`
- Axial envelope: `30 cm`
- Crystal thickness: `0.2 cm`
- Tile size: `0.5 cm` radial by `1.0 cm` tangential
- Mosaic FWHM: `2.0 arcmin`
- Axial layers: `4`
- Mean reflectivity assumption: `0.30`
- Number of ring-layer rows: `68`
- Number of crystal tiles: `5752`
- Projected crystal area: `2876.0 cm^2`
- Estimated band effective area: `862.8 cm^2`
- Estimated 511-keV line effective area: `253.498 cm^2`
- Total Ge mass: `3.062 kg`
- Max outer radius: `19.088 cm`

Ring coverage summary from `GE_MULTIHKL_LINE200_STRETCH_rings.csv`:

- `111`: 8 ring-layer rows; energy range about `494-531 keV`
- `220`: 16 ring-layer rows; energy range about `473-538 keV`
- `311`: 20 ring-layer rows; energy range about `466-540 keV`
- `400`: 24 ring-layer rows; energy range about `465-542 keV`
- All four HKL sets use layer indices `0,1,2,3`

Important: Option 3 is not strict Ge(111). It is a multi-HKL, multi-layer,
line-511 stretch geometry.

## 6. Critical Physics Warning Already Found Locally

The GPT_pro package explicitly states:

- Strict first-order Ge(111), focal length 10 m, diameter 40 cm, over 450-550
  keV cannot provide `200 cm^2` effective area.
- The first-order Ge(111) annulus for 450-550 keV is only about `74 cm^2`
  before reflectivity and packing losses.

Therefore:

- If `Ge(111)` is non-negotiable, Option 3 is not valid as written.
- If `A_eff ~200 cm^2 at 511 keV` is non-negotiable, Option 3 is a possible
  stretch/trade-study because it relaxes to multiple Ge HKL and multiple axial
  layers.

Review whether this relaxation is acceptable for the science claim and
instrument concept.

## 7. Current Capability Gap Assessment

Preliminary Codex assessment before Claude review:

The current `opticsim_full` is a suitable foundation but probably not enough
out of the box to make Option 3 a fully validated optical authority.

Likely existing capabilities:

- Multi-ring ring config is supported.
- Per-ring `h,k,l,d_spacing_A` is supported.
- Per-ring `z_offset_mm` is supported.
- Per-ring `design_energy_keV` is supported.
- Per-ring rocking curve map is supported.
- Geant4 standard EM competition is supported.
- Focal-plane crossing output is supported.

Likely missing or incomplete for Option 3:

1. No importer/converter from GPT_pro `GE_MULTIHKL_LINE200_STRETCH_rings.csv`
   or `*_crystals.csv` into `opticsim_full` ring config.
2. Current `opticsim_full` tile geometry is square via one `tile_size_mm`; Option
   3 uses rectangular `0.5 cm x 1.0 cm` tiles.
3. Current rocking curve map only covers Ge(111) 511 keV. Option 3 needs
   multi-HKL and probably multi-energy/thickness/mosaic curves.
4. Current primary generator sets primary energy to each ring's
   `design_energy_keV`. This is good for band/design-energy scans but not
   sufficient to prove `A_eff(511)` for every ring in a 511-keV line model.
   A mono-energy mode such as `--mono-energy-kev 511` may be needed.
5. Four axial layers require explicit `z_offset_mm` mapping and a check of
   layer-to-layer shadowing/attenuation. The GPT_pro CSV has `layer_index`, but
   review whether it encodes distinct `z_cm` adequately and whether
   `opticsim_full` uses it.
6. The current online Darwin backend is mostly anchored to Ge(111) and the
   current f=9 m design. Review whether it is safe for `220/311/400`, or
   whether external XOP/CRYSTAL rocking curves are mandatory before claims.

## 8. What We Need Claude To Answer

Please answer these questions directly.

### A. Physics Validity

1. Is `GE_MULTIHKL_LINE200_STRETCH` a physically coherent design candidate for
   a 511-keV `A_eff ~200 cm^2` Laue lens?
2. Are `111/220/311/400` all acceptable Ge diamond-cubic reflections for this
   purpose?
3. Does the 4-layer approach make sense, or does it risk double-counting area
   unless shadowing/attenuation is simulated?
4. Does the `2 arcmin` mosaic/acceptance assumption violate or merely saturate
   the slide's `2 arcmin` spatial-resolution requirement?

### B. Simulation Sufficiency

1. Can current `opticsim_full` simulate Option 3 without code changes?
2. If not, what exact code changes are required?
3. Which current approximations are acceptable for a first smoke test, and
   which would invalidate an `A_eff=200 cm^2` claim?

### C. Required Data

1. Are external XOP/CRYSTAL rocking curves required for each HKL/energy ring?
2. Can the current online backend be extended safely to `220/311/400`, or
   should it be considered non-authoritative for those reflections?
3. What minimal set of rocking curves/tables would make Option 3 reviewable?

### D. Implementation Plan

Propose a minimal implementation plan with specific files to add or modify.
Candidate files include:

- `geant4_app/src/laue_multiring_bfull_demo.cc`
- `data/laue/`
- `analysis/run_bfull_f9m.sh` or a new `analysis/run_option3_line200.sh`
- converter script from GPT_pro CSV/JSON into `opticsim_full` ring config
- new output validation script

Please specify:

- exact config schema needed
- whether to use ring-level or crystal-level geometry
- how to encode rectangular tiles
- how to encode four axial layers
- how to run mono-511 line mode
- how to compute `A_eff(511)` from outputs
- how to generate Step09-compatible `focal_crossings.csv`

### E. Acceptance Gates

Define numerical and structural acceptance gates before Option 3 can be called
an optical authority. Suggested gates:

- geometry fits inside diameter `40 cm`
- axial envelope stays within `30 cm`
- all HKL reflections allowed
- mono-511 run produces `A_eff(511)` near 200 cm^2 after normalization
- focal spot / `r90` compatible with `5.8 mm` requirement or explicitly worse
- within-Be fraction for the TES detector Be window is reported
- `phase_space.csv` is not used as science authority
- `focal_crossings.csv` has tracked diffracted photons with source tags
- layer shadowing/attenuation is included or bounded
- statistical uncertainty on `A_eff` and PSF is reported

### F. Integration With `TES_511_Balloon`

What can be used immediately?

- A lens mass proxy in the detector/background model?
- A separate upstream lens self-background mass/source term?
- A focused photon EventList source?
- A new `optics_aeff_authority.json`?

Please distinguish:

1. safe now
2. safe after smoke test
3. safe only after full Option 3 optical validation

## 9. Claims To Avoid Unless Proven

Do not recommend claiming any of the following unless the reviewed evidence
supports it:

- Strict Ge(111) alone provides `A_eff=200 cm^2`.
- `Focus area=100 cm^2` equals `A_eff`.
- Current f=9 m B-FULL `A_eff=15.29928 cm^2` is still the final optics
  authority after adopting Option 3.
- `GE_MULTIHKL_LINE200_STRETCH` has paper-grade PSF or resolution before a
  tracked Geant4/Step09 run.
- The 4 axial layers increase Aeff linearly without shadowing or attenuation.
- `phase_space.csv` can replace tracked `focal_crossings.csv`.
- Lens hardware prompt/self-activation background is already included in
  `TES_511_Balloon`.

## 10. Expected Claude Output Format

Please return a structured review with this shape:

1. Executive verdict:
   - "enough as-is", "enough after small adapter", or "not enough until physics
     tables/code changes"
2. Evidence table:
   - claim
   - supporting local file/line or data file
   - confidence
3. Capability matrix:
   - current `opticsim_full`
   - Option 3 requirement
   - gap
   - fix
4. Implementation plan:
   - exact files to add/modify
   - minimal smoke-test command
   - full validation command sequence
5. Acceptance gates:
   - must-pass checks before using as mass model
   - must-pass checks before using as optical source
   - must-pass checks before quoting `A_eff=200 cm^2`
6. Claim wording:
   - allowed wording
   - forbidden wording
7. Final recommendation:
   - whether to adopt Option 3 as nominal, optimistic branch, or rejected

## 11. Current Codex Recommendation For Claude To Challenge

Codex's current provisional recommendation:

- Use Option 3 immediately as an optimistic lens mass-model branch:
  - Ge mass about `3.06 kg`
  - outer radius under `20 cm`
  - axial envelope target `30 cm`
- Do not yet use Option 3 as optical authority.
- First implement a converter and a mono-511 Option 3 run mode in
  `opticsim_full`.
- Treat `A_eff=200 cm^2` as an external design target until a tracked
  `focal_crossings.csv` and `optics_aeff_authority.json` are generated.
- Keep the current f=9 m Ge(111) B-FULL result (`15.29928 cm^2`) as historical
  baseline, not as the final design if Option 3 is adopted.

Claude should explicitly agree, refine, or reject this recommendation.

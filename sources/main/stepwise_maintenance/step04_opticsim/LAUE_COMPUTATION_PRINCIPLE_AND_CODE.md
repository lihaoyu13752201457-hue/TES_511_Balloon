# Laue Computation Principle And Code Notes

Purpose: record the Step04 optical model now wired into `new_geo_re`.

## Current Short Answer

Step04 now uses the B-FULL Laue implementation:

- source: `/home/ubuntu/opticsim/geant4_app/src/laue_multiring_bfull_demo.cc`
- process: non-forced `G4VDiscreteProcess`
- physics: finite equivalent Laue diffraction mean free path competing with standard Geant4 EM processes
- nominal backend: external 511-keV XOP/CRYSTAL rocking-curve map
- design authority: `optics_aeff_authority.json`

This is still application-level opticsim code. It is not a Geant4 toolkit patch.

## Geometry

The retained lens is a 511-keV line-focused Ge(111) Laue optic. The `480-550 keV`
interval is a TES spectral analysis window for line fitting and continuum
baseline, not the optical focusing band:

```text
ring_id,design_energy_keV,radius_mm,n_tiles,material,h,k,l,d_spacing_A,tile_size_mm,thickness_mm,z_offset_mm
0,511.0,61.650681,24,Ge,1,1,1,3.266590088,15.000000,10.218801,0.000000
```

The focal length is `8300 mm`. Ring radius is tied to Bragg geometry, not drawn arbitrarily.

## B-FULL Event Flow

1. A primary gamma is aimed at a selected crystal tile.
2. Standard Geant4 EM physics remains enabled.
3. The B-FULL Laue process supplies a finite diffraction MFP when the gamma is in a crystal.
4. Geant4 competition decides whether standard EM or Laue diffraction happens first.
5. Diffracted photons are reflected from the fixed tile plane normal with mosaic perturbation.
6. `phase_space.csv` records one projected row per diffraction interaction and is retained for diagnostics only.
7. `focal_crossings.csv` records tracked focal-plane crossings; Step09 bridges the within-Be diffracted rows.
8. `transmitted_space.csv` records actual primary/transmitted focal-plane crossings.

The old forced Guan smoke run and the earlier 20k five-ring demo are no longer the Step04 handoff authority.

## Current Evidence

Current run:

- `outputs/opticsim_laue_bfull_xopmap_real/`

The XOP-map run is nominal because it uses the external 511-keV XOP/CRYSTAL rocking curve with `--require-rocking-curve-map`.

The B-FULL tracked diffracted focal crossings are inside the `new_geo_re` Be window:

- Be radius: `1.898 cm`
- diffracted focal rows: `12566`
- within-Be focused rows: `12552`
- tracked focal spot `r95`: `0.204197 cm`
- tracked focal spot `r99`: `0.270588 cm`
- max within-Be focal radius: `1.33961 cm`
- exact 511-keV optical A_eff: `13.5562 cm2`

## Scope

This replacement only changes focused-photon optics handoff and documentation in `new_geo_re`.

It does not yet place the Laue-lens hardware mass into the MEGAlib detector geometry, so prompt charged particles and neutron/proton activation in the optics solid angle remain future full-chain work.

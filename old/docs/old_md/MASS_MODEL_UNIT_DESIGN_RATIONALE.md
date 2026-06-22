# NEW_GEO_RE Mass Model Unit Design Rationale

Purpose: compact review note for deciding whether the `new_geo_re` detector mass
model is defensible in a paper. This is not a detailed mechanical design record.
It documents the simulation mass model, the local code authority, the design
criteria used for each unit, and the remaining publication risks.

## Code Authority

- DEMO2 source generator, authored directly in cm:
  `tmp_mass_model_review_bundle/DEMO2/build_demo2_mass_model.py`
- Transport geometry actually used by runs:
  `outputs/geometry/XZTES_ADR_v4c_mkflange_cm/TibetTES_ADR_v4c_mkflange_cm.geo.setup`
- cm geometry body:
  `outputs/geometry/XZTES_ADR_v4c_mkflange_cm/TibetTES_ADR_v4c_mkflange_cm.geo`
- detector map:
  `outputs/geometry/XZTES_ADR_v4c_mkflange_cm/TibetTES_ADR_v4c_mkflange_cm.det`
- machine-readable geometry authority:
  `outputs/geometry/XZTES_ADR_v4c_mkflange_cm/bounds.json`
- human Step01 record:
  `stepwise_maintenance/step01_geo/README.md`
  and `records/00_geometry/geo.md`
- legacy v4c generator/provenance file, not the current DEMO2 source to rerun:
  `code/geometry/GenerateGeo_ADR_v4c_mkflange.py`

The installed compatibility path still contains the old `v4c_mkflange_cm`
tokens so existing source cards and analysis scripts keep working. Its contents
are DEMO2, and `bounds.json` records `length_unit=cm` and
`source_design_unit=cm`.

## Recommended Paper Wording

Use wording like:

> We used an engineering ADR/TES detector mass model for Geant4/Cosima
> background transport. The model is intended to preserve the dominant local
> material distribution, entrance apertures, active-veto envelope, and passive
> cryostat layers, not to represent a fabrication-ready cryostat mechanical
> drawing.

Avoid wording like:

> The final cryostat mechanical design consists of ...

That stronger statement is not supported by the current prototype model.

## Global Design Rules

- All active axial holes and window clear radii are matched to the Be cryostat
  window radius: `1.898 cm`.
- Be cryostat window: radius `1.898 cm`, thickness `0.015 cm`,
  center z `12.8425 cm`.
- The full A4K/Cryoperm magnetic-shield stack is not modeled. The current
  geometry includes one simplified `Cryoperm_Inner_Mag_Shield` proxy around the
  Nb can, so high-Ni shielding is represented only at proxy level.
- The vacuum-jacket aperture is represented by the Be window plus the thin
  `Win_Vacuum_Al_Filter` proxy; this is not a full certified window/filter
  assembly.
- The current active shield authority is `CsI_Active_Shield`
  (`mat=CsI` in `bounds.json`). The Step05 analysis keeps a `50 keV` veto
  threshold for comparison with the earlier `fix` baseline.
- The model includes current detector/cryostat mass only. Step09 optics bridge
  does not yet add prompt/delayed activation from the Laue optics hardware mass.

## Local Reference Sources Recorded In The Generator

These references are recorded in the geometry generator as design motivation.
They should be externally checked again before final paper submission:

- Danaher Cryogenics / HPD Model 103 Rainier ADR: experimental space, cold
  stages, vacuum jacket, 50 K / 4 K radiation shields.
- 511-CAM paper: active BGO outside cryostat, passive shielding concepts,
  Nb/A4K discussion, focal plane detector context.
- Kurt J. Lesker aluminum vacuum chamber note: aluminum chamber motivation.
- Oxford Instruments Be-window note: order-of-magnitude Be exit-window
  thickness motivation.
- Advatech CeBr3 note: historical generator reference only; the current
  science authority has moved to the CsI active-shield branch.

## Unit-by-Unit Rationale

| Unit | Material | cm dimensions from `bounds.json` | Design criterion | Paper confidence | Main risk / what GPT Pro should check |
| --- | --- | --- | --- | --- | --- |
| TES pixels, 6 layers | Ta | 6 layers; z centers `1.165` to `7.165`; r max `1.8`; half-thickness `0.15`; 376 pixels/layer | Retain six-layer TES stack footprint and thickness as detector response anchor. | Medium-high as simulation geometry. | Confirm Ta pixel thickness and fill pattern match the intended TES microcalorimeter stack or describe as simplified absorber array. |
| Si substrates | Si | 6 substrates; z centers `1.0` to `7.0`; r `2.2`; half-thickness `0.015` | Include nearby low-Z substrate mass behind each TES layer. | Medium. | Substrate thickness and radius are placeholders unless tied to a detector design drawing. |
| `ColdPlate_50mK` | Cu | r `4.5`; h `0.5`; z `0.0` | 50 mK mounting plate, sized to support sample box and detector can seating. | Medium as mass placeholder. | Needs mechanical/cold-stage reference if paper claims exact dimensions. |
| `ColdPlate_1K` | Cu | r `5.5`; h `0.5`; z `-3.2` | 1 K intercept stage separated from 50 mK plate. | Medium-low. | Stage spacing is engineering proxy, not an ADR CAD-derived value. |
| `ColdPlate_4K` | Cu | r `7.0`; h `0.6`; z `-7.2` | 4 K / pulse-tube-stage analog with routing margin. | Medium-low. | Check whether real ADR uses Cu here and whether radius is realistic. |
| `ColdPlate_60K` | Al | r `8.35`; h `0.6`; z `-10.8` | 60 K interface plate aligned with the warm radiation-shield stage. | Medium-low. | Material/thickness/radius should be treated as proxy unless backed by CAD. |
| `TES_SampleBox_Cu` | Cu | r in/out `3.4/3.7`; z outer bottom/top `0.25/8.7`; aperture `1.898` | 3 mm Cu sample box surrounding TES stack; bottom disk contacts 50 mK plate; top aperture aligned to Be window. | Medium as local shielding/sample-box proxy. | Need check whether Cu wall and open/apertured top are mechanically plausible and not over-shielding. |
| `SampleBox_Al_Window` | Al | r `1.898`; thickness `0.0025`; z `8.55` | Thin sample-box foil/window placeholder, clear radius matched to Be aperture. | Low-medium. | 25 um Al is a placeholder; paper should say "thin Al foil/window approximation" unless supported. |
| `Nb_SC_Detector_Can` | Nb | r in/out `4.505/4.535`; z in bottom/top `-0.25/9.2`; top `9.23`; aperture `1.898` | Removable open-bottom superconducting detector can seated on 50 mK plate edge. | Medium as magnetic/passive mass proxy. | 0.3 mm Nb thickness and open-bottom geometry need review for magnetic-shield realism. |
| `Cryoperm_Inner_Mag_Shield` | Cryoperm | r in/out `4.75/5.2`; z out bottom/top `-0.9/9.95`; aperture `1.898` | Simplified Ni-rich magnetic shield around the Nb can. | Medium-low. | High-Ni activation/background impact should be treated as proxy-level, not final magnetic-shield design. |
| ADR passive proxies | Cu / Fe / SaltProxy / SS | magnet coil r `5.7/7.25`, z `-6.7/-2.45`; Fe yoke r `7.48/8.65`, z `-8.75/-2.25`; salt pill r `2.3`, z `-6.55/-4.25` | Preserve dominant ADR magnet, yoke, salt-pill, thermal-bus, heat-switch, and cold-head interface masses below the aperture. | Medium as mass proxies. | These are not CAD-derived ADR internals; material choices and exact dimensions need careful wording. |
| `Thermal_50mK_Al_Shield`, `Thermal_1K_Al_Shield`, `Thermal_4K_Al_Shield`, `Thermal_60K_Al_Shield` | Al | r out `4.66`, `5.62`, `7.42`, `8.95`; all apertures `1.898` | Staged aluminum thermal/radiation shields. | Medium as mass proxies. | Shield thicknesses and z envelopes are baseline assumptions, not verified CAD. |
| Al shield/window/filter stack | Al | `Win_50mK_Al_Shield`, `Win_1K_Al_Shield`, `Win_4K_Al_Shield`, `Win_60K_Al_Shield` each r `1.898`, thickness `0.0025`; `Win_Vacuum_Al_Filter` thickness `0.003` | Thin aperture-closure/filter placeholders aligned to the Be radius. | Low-medium. | Foil/filter presence and thickness need review; open-aperture variants may be needed. |
| `Vacuum_Jacket_Al` | Al | r in/out `9.25/9.65`; z out bottom/top `-13.65/12.9`; aperture `1.898` | Aluminum vacuum-jacket mass model; Be window and thin Al filter represent the aperture closure. | Medium-low. | 4 mm Al is not pressure-vessel certification. Paper should not imply certified vacuum vessel design. |
| `Win_Be_Cryostat` | Be | r `1.898`; thickness `0.015`; z `12.8425` | Be entrance window and aperture reference for all internal holes/windows. | Medium-high as model convention. | Check whether 150 um Be and 1.898 cm radius are acceptable for 511 keV gamma transport and pressure boundary assumptions. |
| `CsI_Active_Shield` | CsI | r in/out `10.05/14.05`; z out bottom/top `-21.95/15.35`; side thickness `4.0`; bottom thickness `8.0`; top thickness `2.0`; aperture `1.898` | Segmented CsI(Tl)-like active well outside the cryostat. | Medium as veto mass model. | Packaging, segmentation, threshold, and intrinsic-background assumptions should be clearly stated. |
| `Outer_Al_Mech_Shell` | Al | r in/out `14.25/14.45`; z out bottom/top `-22.35/15.75`; aperture `1.898` | Outer mechanical cover outside scintillator, not the vacuum boundary. | Low-medium. | Structural shell placeholder; do not claim final outer-housing design. |
| `W_Collimator_Aperture_Stop` | W | z `16.0`; r inner/max `1.898/3.1`; thickness `0.1` | Annular entrance aperture stop retained as first passive entrance proxy; not a Laue optic. | Low-medium. | Do not describe this as the focusing optics or a final collimator design. |

## Omitted Or Simplified Units

| Omission / simplification | Current policy | Why it matters |
| --- | --- | --- |
| Detailed A4K/multi-layer magnetic-shield stack | Not modeled; only `Cryoperm_Inner_Mag_Shield` is retained as a simplified proxy. | High-Ni magnetic shielding can affect activation/background and should not be described as finalized. |
| Detailed internal heat-switch CAD / W baffle | No detailed CAD; only simplified thermal-bus and heat-switch/link proxies are retained. | Keeps dominant ADR service masses without claiming exact internal mechanics. |
| Full vacuum-window/filter assembly | Simplified to `Win_Be_Cryostat` plus `Win_Vacuum_Al_Filter`. | Reviewer may ask whether real cryostat needs additional window/filter material or open-aperture variants. |
| Optics hardware mass | Not included in prompt/delayed background transport. | Important if the paper claims total instrument background including Laue lens activation/scattering. |
| Detailed packaging/cables/supports | Only limited readout, harness, G10 post, active-shield packaging, and feedthrough proxies are included. | Missing or approximate support/cabling mass can affect activation and local Compton backgrounds. |

## Publication Risk Classification

Safe claims:

- The simulations use a cm-scaled ADR/TES engineering mass model generated by
  `GenerateGeo_ADR_v4c_mkflange.py` and audited by `bounds.json`.
- Apertures and thin windows are consistently matched to the Be-window clear
  radius of `1.898 cm`.
- The full A4K/multi-layer magnetic-shield stack is intentionally not modeled;
  only the simplified `Cryoperm_Inner_Mag_Shield` proxy is included.
- The active-veto volume is modeled as a segmented CsI shell outside the
  cryostat, with Step05 analysis applying a 50 keV veto threshold for comparison
  with `fix`.

Claims needing careful wording:

- Cold-plate, thermal-shield, sample-box, Nb-can, and outer-shell dimensions are
  engineering mass-model assumptions, not final CAD.
- Thin Al internal windows/filter proxies are aperture-closure placeholders.
- The vacuum jacket is an aluminum mass model, not a pressure-vessel design.
- The W aperture stop is not the detailed Laue optical element.

Claims to avoid until upgraded:

- "This is the final mechanical design."
- "The mass model includes all optics hardware activation."
- "The magnetic shielding design is complete."
- "The CsI active shield is mechanically packaged and optimized."

## Suggested GPT Pro Review Prompt

Please review `MASS_MODEL_UNIT_DESIGN_RATIONALE.md` for whether this detector
mass model can be described in a scientific paper as an engineering Geant4/Cosima
background model. Focus on whether each unit's material, dimensions, and
omissions are defensible if worded as a prototype mass model, not a final
mechanical design. Flag any unit that is physically implausible, likely to bias
511 keV background/veto estimates, or needs a stronger reference before
publication. Pay special attention to: thin Al shield/filter windows, CsI
active-shield envelope, simplified Cryoperm proxy, aluminum vacuum jacket, W
aperture stop, approximate supports/cables/optics hardware mass, and whether the
1.898 cm Be-window-matched aperture convention is reasonable.

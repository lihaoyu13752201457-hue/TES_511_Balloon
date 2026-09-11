# S3d-O8 geometry/BOM engineering review (read-only, pre-transport)

Date: 2026-08-14  
Reviewer scope: independent geometry and engineering-boundary audit only. No transport was run and no optimum is declared. The prior third-party-review hypotheses were not treated as authority.

## 1. Bottom line

1. The exact S3d-O8 transport authority is the setup selected by `analysis_inputs.json`; it is an S3c minimal-delta descendant. S3d changes only bottom BGO 40 -> 30 mm, top BGO 40 -> 10 mm, and deletes three *outer* W2 shell volumes. TES, cryostat, BPE, plastic, side BGO, internal Cu, Nb/Mu, bottom W and multihole W remain inherited.
2. This is a valid transport geometry, but it is **not a manufacturable CAD/BOM authority**. The package itself calls it a minimal-delta transport geometry rather than structural qualification. Its upstream mass model calls itself a derived draft; several solids are equivalent-cylinder/coarse proxies, brackets are omitted, and top pipes were not copied from actual solids.
3. Two geometry facts are especially important for physics interpretation:
   - The BGO side shell has a 37.96 x 37.96 mm negative-x optical opening, but the enclosing BPE and plastic shells are full annuli/caps with only NF2 support reliefs. They have **no corresponding optical side opening** in this geometry.
   - The comment that the 50 mK Cu can “touches” the MXC plate is only nominal. The solids are coplanar at `z=-0.3 cm`, but the plate ends at `r=15.0 cm` and the can starts at `r=15.1 cm`, leaving a 1 mm radial gap and no modeled joint.
4. Exactly one simple topology is advanced: **G-Nb-S1, reduce only the inner Nb cylindrical sleeve from 2.0 to 1.0 mm while leaving its 2 mm back cap and the complete outer Mu layer unchanged**. It directly overlaps the two observed prompt pair sites in the Nb cylinder and a delayed component with separately tabulated production Bq and W2/Bq. It does not solve the observed DR-mixing-Cu branch by assumption: migration into DR Cu/Mu/Ag/MXC is its registered falsifier. This is a geometry-screen candidate, not an optimum declaration.

## 2. Evidence paths and coordinate convention

Path aliases used below:

- `INPUTS` = `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/m05_corrected_reanalysis_20260813/analysis_inputs.json`
- `SETUP` = `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- `GEO` = `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo`
- `DET` = `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.det`
- `INTRO` = `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/Intro_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo`
- `MAT` = `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/Materials_DEMO2_DR_v3p5.geo`
- `MEGAMAT` = `/home/ubuntu/MEGAlib_Install/megalib-main/resource/examples/geomega/materials/Materials.geo`
- `MANIFEST` = `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/s3d_o8_geometry_manifest.json`
- `LEDGER` = `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/s3d_o8_mass_ledger.json`
- `BASE_README` = `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/README.md`
- `OLD_BUDGET` = `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/old/geometry/references/geo_refer/DEMO2_DR_v3p5_minpatch_centerfinger_mass_budget.csv`
- `CORE_TRACE` = `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/s3d_o8_low_grammage_core_20260814/REPORT.md` (historical event trace/smoke evidence only, not geometry or optimization authority)
- `DELAYED_COMPONENT` = `/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/agents/delayed/delayed_component_summary.csv`
- `DELAYED_FLOW` = `/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/agents/delayed/delayed_key_flow.csv`

Authority chain and coordinates:

- `INPUTS:169-179` selects `SETUP` and exactly six analysis-active veto volumes.
- `SETUP:1-5` includes `GEO` and `DET` and defines `SurroundingSphere 60 5 0 9 60`.
- `GEO:1` includes `INTRO`; `INTRO:4` includes `MAT`.
- `INTRO:13-19` makes all listed component coordinates children of `InstrumentFrame`, which is rotated `0 45 0` in world coordinates. Unless explicitly stated otherwise, dimensions and positions below are **InstrumentFrame-local**, not world-axis values.
- `MANIFEST:45-50` is the exact S3d physical-delta list; `MANIFEST:94-99` says TES/cryostat/BPE/plastic and other named systems are unchanged.

## 3. Material authority

| Transport material | Density (g cm^-3) | Transport composition | Evidence |
|---|---:|---|---|
| BGO | 7.1 | Bi4Ge3O12 | `MEGAMAT:41-45` |
| Copper | 8.954 | standard MEGAlib Cu | `MEGAMAT:73-75` |
| Aluminium | 2.7 | standard MEGAlib Al | `MEGAMAT:24-26` |
| Silicon | 2.33 | Si | `MEGAMAT:267-269` |
| Nb | 8.57 | Nb | `MAT:6-8` |
| W | 19.3 | W | `MAT:10-12` |
| Ta | 16.69 | Ta | `MAT:14-16` |
| MuMetal | 8.7 | Ni:Fe = 4:1 atom-count proxy | `MAT:23-26` |
| Cryoperm | 8.7 | Ni:Fe = 4:1 atom-count proxy | `MAT:27-30` |
| SilverSinterProxy | 5.0 | Ag | `MAT:58-60` |
| PlasticScintillator | 1.03 | C8H8 | `MAT:71-76` |
| BoratedPolyethylene5wtB | 0.95 | approximate C:H:B = 1000:2000:68 | `MAT:78-83` |

MuMetal and Cryoperm are materially indistinguishable in this transport definition. Any isotope-production difference attributed to the real alloys is therefore outside the present model.

## 4. Outer active/passive shield inventory

All masses marked “pre-relief” are analytic base-solid masses. The quoted comment volumes equal the uncut primitive volumes exactly, even where the volume is assigned a Boolean shape. Therefore exact post-window/post-NF2 CSG masses are **UNKNOWN** from the supplied ledger.

| Component | Active? | Exact primitive and local span | Explicit holes/reliefs | Density | Analytic pre-relief mass |
|---|---|---|---|---:|---:|
| Side BGO | yes | annulus `r=21.2..25.2 cm`, `z=-19.4..40.9 cm`, 40 mm radial thickness | negative-x rectangular opening 37.96 x 37.96 mm centered at `z=-5.2`; pump relief 15 x 15 mm; six NF2 rod reliefs | 7.1 | 249.634 kg |
| Bottom BGO | yes | disk `r=0..25.2 cm`, `z=-22.4..-19.4 cm`, 30 mm | six NF2 rod reliefs | 7.1 | 42.4943 kg |
| Top BGO | yes | annulus `r=20.9..25.2 cm`, `z=40.9..41.9 cm`, 10 mm | central service opening plus six NF2 rod reliefs | 7.1 | 4.42158 kg |
| Side BPE | no | annulus `r=27..29 cm`, `z=-24.5..46.0 cm`, 20 mm radial | base/top-mount and six NF2 rod reliefs; **no optical window** | 0.95 | 23.5657 kg |
| Bottom/top BPE | no | full disks `r=0..29 cm`; bottom `z=-26.5..-24.5`, top `z=46..48 cm` | NF2 relief chain; **no optical window** | 0.95 | 5.01995 kg each |
| Side plastic | yes | annulus `r=29..30 cm`, `z=-26.5..48.0 cm`, 10 mm radial | base/top-mount and six NF2 rod reliefs; **no optical window** | 1.03 | 14.2231 kg |
| Bottom/top plastic | yes | full disks `r=0..30 cm`; bottom `z=-27.5..-26.5`, top `z=48..49 cm` | NF2 relief chain; **no optical window** | 1.03 | 2.91226 kg each |

Line evidence:

- Side BGO primitive/window/pump/rod reliefs: `GEO:16770-16824`; declared volume/material/position: `GEO:16825-16830`.
- Bottom BGO: `GEO:17168-17217`; top BGO: `GEO:17220-17269`.
- BPE patch boundary/status: `GEO:16360-16365`; side: `GEO:16367-16430`; bottom: `GEO:16432-16496`; top summary: `GEO:16556-16561`.
- Plastic side: `GEO:16564-16628`; bottom: `GEO:16630-16694`; top: `GEO:16696-16760`.
- Downstream-active list is exactly BGO side/bottom/top and plastic side/bottom/top: `INPUTS:169-179`. BPE has no detector scorer.
- Native thresholds are plastic `0.001 keV` (`DET:1080-1099`) and BGO `80 keV` (`DET:1105-1111`, `DET:1167-1183`). The frozen analysis veto is 50 keV, not the BGO-native 80 keV (`MANIFEST:89-92`).

Mass-ledger inconsistency: `LEDGER:3-4` uses BGO density 7.13 and explicitly calls itself pre-relief bookkeeping. Its side/bottom/top values (`LEDGER:7-18`) are respectively about 1.0548, 0.1796 and 0.0187 kg above the same primitives evaluated with the actual transport density 7.1. `LEDGER:20-22` is not an exact post-CSG or structural mass.

## 5. TES and near-TES Cu support

### TES / substrate

- Each Ta pixel is a BRIK with half-sizes `(0.15, 0.075, 0.075) cm`, i.e. full size 3.0 x 1.5 x 1.5 mm (`GEO:3-7`; repeated at `GEO:1898-1902`, etc.).
- There are 376 copies per layer (e.g. L0 terminates at copy 375 in `GEO:1888-1896`) and six layers: 2256 pixels total.
- Layer envelope centers are `x=[-3.0,-1.8,-0.6,0.6,1.8,3.0] cm`, all at `(y,z)=(0,-5.2)`, with full layer depth 3 mm and 36 x 36 mm envelope (`GEO:13-15`, `1908-1910`, `3803-3805`, `5698-5700`, `7593-7595`, `9488-9490`).
- Ta total: 15.228 cm3 and 0.254155 kg.
- Each Si substrate is a **square BRIK**, full size 0.3 x 36 x 36 mm, at x `[-2.82,-1.62,-0.42,0.78,1.98,3.18] cm` (`GEO:11373-11425`). Si total: 2.3328 cm3 and 5.435 g.

### Cu detector support actually transported

| Family | Actual transport solid | Count | Total Cu mass |
|---|---|---:|---:|
| L1-L5 open supports | each is four BRIK panels forming a square frame: outer 44 x 44 mm, inner 37 x 37 mm, x-depth 3 mm | 5 frames | 65.060 g |
| deepest L0 support | BRIK, full 3.5 x 44 x 44 mm; despite the name it is not a disk | 1 | 60.672 g |
| edge rods | BRIK, full length 58.85 mm, square cross-section 1.414 x 1.414 mm | 4 | 4.216 g |
| off-axis fingers | BRIK equivalents at `y=+/-1.1 cm`, two lengths | 4 | 4.905 g |
| vertical stems | cylinders `r=1.6 mm`, two 38 mm and two 60 mm long | 4 | 14.114 g |
| MXC clamp pads | annuli `r=1.8..3.5 mm`, 2 mm thick, centered at `(x,y)=(6.05,+/-1.1)` and `(6.85,+/-1.1) cm` | 4 | 2.028 g |
| **total** | ideal solids only | | **150.995 g** |

Evidence: support panels `GEO:11427-11604`; L0 BRIK and edge rods `GEO:11607-11649`; fingers/stems/pads `GEO:11652-11757`.

Bolts, straps, braids, fasteners, harness anchors, solder/braze, real joints, tolerances, and contact conductances are not represented. Their geometry/material/mass is **UNKNOWN**.

## 6. Cold plates, Cu can, and DR proxy

| Component | Transport geometry and position | Transport density | Analytic mass |
|---|---|---:|---:|
| MXC 50 mK Cu plate | solid disk `R=15 cm`, `t=6 mm`, center `z=0`; no holes | 8.954 | 3.797526 kg |
| CP 100 mK Cu plate | solid disk `R=15 cm`, `t=6 mm`, center `z=5 cm`; no holes | 8.954 | 3.797526 kg |
| Still Cu plate | solid disk `R=15 cm`, `t=6 mm`, center `z=11 cm`; no holes | 8.954 | 3.797526 kg |
| 4 K Cu plate | solid disk `R=17.5 cm`, `t=6 mm`, center `z=20 cm`; no holes | 8.954 | 5.16885 kg |
| 50 mK Cu can | bottom disk `R=15.3 cm`, 2 mm; wall `r=15.1..15.3 cm`, `z=-9.7..-0.3 cm`; negative-x 37.96 mm square side opening centered at `z=-5.2` | 8.954 | about 2.89879 kg after the explicit rectangular CSG cut |
| DR mixing Cu | solid disk `R=2.2 cm`, `h=1.8 cm`, center `z=1.21 cm` | 8.954 | 0.245067 kg |
| DR Ag sinter proxy | annulus `r=2.5..3.5 cm`, `h=1.8 cm`, center `z=1.3 cm` | 5.0 | 0.169646 kg |

Plate evidence: `GEO:11847-11881`. Cu-can solids/window: `GEO:11779-11820`. DR Cu/Ag: `GEO:12556-12572`.

Engineering observations:

- The full 6 mm Cu-plate through-grammage is 5.3724 g cm^-2.
- MXC plate top is `z=+0.3 cm`. The DR Cu lower face is `z=+0.31 cm`: a 0.1 mm modeled gap, although `OLD_BUDGET:45` says “1 mm”. The geometry wins.
- Ag and CuNi proxy lower faces are at `z=+0.4 cm`, a 1 mm gap (`GEO:12565-12580`).
- The first XS400-equivalent support rods extend to `z=+0.32 cm`, a 0.2 mm gap. Their centers and radii occupy projected radius about 5.72..7.41 cm (`GEO:11901-11935`). They are mass-preserving equivalent cylinders based on declared CAD volumes; small pads/brackets are explicitly omitted (`GEO:11901-11905`).
- The Cu can top edge and plate underside are both at `z=-0.3 cm`, but `R_plate=15.0 cm < r_can,in=15.1 cm`; no volume or face is shared. The real mount is **UNKNOWN**.

## 7. Nb/Mu topology and retained W

### Magnetic shields

- Nb sleeve: x-axis annulus, axial range `x=-3.85..4.10 cm`, `r=4.0..4.2 cm`, 2 mm wall (`GEO:11760-11768`).
- MuMetal sleeve: `x=-4.35..4.30 cm`, `r=4.25..4.45 cm`, 2 mm wall (`GEO:11770-11777`).
- Downstream (+x) annular caps are 2 mm thick with a central `r=1.85 cm` hole (`GEO:11822-11838`). There is no upstream Nb/Mu cap: both sleeves are open toward the side-entry beam. A 25 micrometre Al foil is at `x=-4.35125 cm` (`GEO:11840-11846`).
- Ideal masses including sleeve plus back cap: Nb about 0.427585 kg; MuMetal about 0.500911 kg.
- The old reference budget is stale here: it describes 0.5 mm Nb and 1.2 mm Cryoperm (`OLD_BUDGET:26-27`), whereas transported S3d has 2 mm Nb and 2 mm MuMetal.

Seams, fasteners, overlap tabs, magnetic-shield heat treatment/permeability, trapped-field strategy, SQUID penetration layout, and real service feedthroughs are **UNKNOWN**.

### Retained W

- Bottom W plate: solid disk `R=13.62 cm`, `t=1.9 mm`, center `z=-14.3 cm`, mass 2.13705 kg (`GEO:12781-12788`).
- Side multihole W grid: vacuum envelope full size 8 x 37.96 x 37.96 mm centered at `(x,z)=(-25.9,-5.2) cm`; bars are defined at `GEO:12790-12812`. Counting instances gives 24 horizontal, 552 center-vertical and 48 edge-vertical bars, about 34.665 g W in total.
- S3d removed only three **outer W2 mechanical-shell** volumes (`MANIFEST:45-49`); these bottom/grid W components remain.

No candidate below adds, enlarges, or moves W/Pb near TES.

### Transport-proxy mass and reallocation boundary

| Family | Present proxy mass | What can actually be treated as reallocatable now? |
|---|---:|---|
| BGO side + bottom + top | 296.5499 kg at the actual 7.1 g cm^-3 transport density, pre-relief | **0 kg certified**. Exact post-CSG and structural/readout mass is unknown; changing it also changes active-veto and secondary production. |
| BPE side + two caps | 33.6056 kg, pre-relief | **0 kg certified**. Exact post-CSG mass and real support/optical topology are unknown. |
| Plastic side + two caps | 20.0476 kg, pre-relief | **0 kg certified**; it is active and outside the permitted candidate chosen here. |
| Named cold Cu plates + 50 mK can + DR Cu + modeled detector supports | 19.8563 kg (of which 7.0924 kg is MXC plate/can/DR/support and 12.7639 kg is CP/Still/4 K plates) | **0 kg certified**. These are coarse thermal/structural proxies and the real interfaces are absent. |
| Nb inner sleeve + back cap | 0.427585 kg | G-Nb-S1 conditionally releases **0.177654 kg**, only if the magnetic gate passes. |
| Mu outer sleeve + back cap | 0.500911 kg | 0 kg in G-Nb-S1; it is deliberately frozen as the retained high-permeability layer. |

The 0.177654 kg Nb delta is a ceiling, not a free shield budget. Even if it were reassigned uniformly, it corresponds to only 0.151 mm over the full BPE side shell or 0.0285 mm over the full BGO side shell; on one complete end cap it is 0.708 mm BPE or 0.125 mm BGO. A local sector could be thicker, but its azimuth and energy benefit cannot be selected from three survivors. Therefore G-Nb-S1 leaves the saved mass **unassigned** until denominator-complete direction/energy statistics exist.

## 8. CAD/BOM versus transport proxy

### What is actually supported

- Upstream mass-model README: generated by a builder and explicitly a “derived draft, not a promoted mainline geometry authority” (`BASE_README:1-5`).
- It fixes staged diameters/thicknesses (`BASE_README:9-10`), keeps detector/magnetic/lattice dimensions (`BASE_README:12-13`), refits XS400 rods as volume-preserving equivalents (`BASE_README:14`), and adds top-pipe proxies not copied from actual solids (`BASE_README:15-16`).
- S3d itself says the BGO/Kapton clearances are deliberate and that the result is not support/manufacturing/structural qualification (`MANIFEST:76-87`; package README `:94-104`).
- The old mass budget records conceptual provenance, not present-solid truth. Examples: old Si disks (`OLD_BUDGET:3`) versus current square BRIKs; old analytic Cu annuli/disks (`OLD_BUDGET:4-9`) versus current BRIK frames/square L0; old `R=7.4 cm` MXC plate (`OLD_BUDGET:29`) versus current `R=15 cm`; and an Ag “50% dense” description (`OLD_BUDGET:46`) versus only a fixed 5 g cm^-3 transport material.

### Explicit UNKNOWN

- No `.step`, `.stp`, `.iges`, `.igs`, or `.FCStd` file was found anywhere under the supplied source root.
- No current, assembly-level procurement/manufacturing BOM was found. Only historical proxy `mass_budget` files were found under `old/`.
- `BASE_README:30-33` points to manifest/summary/WRL files under `outputs/reports/...`, but that directory is absent from this source worktree.
- Real cold-plate holes, bolt circles, can attachment, material grade/RRR, structural load path, thermal-contact budget, cable/service penetrations, BGO segmentation/photodetectors/supports, BPE/plastic optical port, and shield seams are all unknown.

Conclusion: candidates can be screened against the present transport proxy, but machining release or structural/thermal acceptance requires a real CAD/BOM/thermal-structural authority not present here.

## 9. Single candidate topology after origin and engineering screening

### Why this component, and what the evidence does not say

`CORE_TRACE:29-39` records three prompt active-veto leaks: events 3883 and 8081 first pair in `Nb_MagShield_Inner_Cylinder_2mm`, while event 19932 pairs in `DR_MixingChamber_Cu`. All three cross active material with zero recorded active deposit. These three numerator events establish direct geometric overlap but are **not** an incident-angle/energy denominator and cannot support a 2/3 sky-rate claim.

The independent delayed component fold gives the Nb cylinder production `4.3115 s^-1`, day-15 activity `1.0163 Bq`, observed selected rate `0.0078086 cps`, and supported-inventory coupling `0.0096299 W2/Bq` (`DELAYED_COMPONENT:8`). This is attractive per Bq, but position Neff is only 2.95 and event Neff 2.97, so it is a localization signal, not a precise expected reduction. For comparison, the MXC Cu plate is the larger production/selected hotspot (`28.5124 s^-1`, `20.2809 Bq`, `0.0167715 cps`) but has low Neff too (`DELAYED_COMPONENT:6`); Mu is already a nearby migration host (`DELAYED_COMPONENT:7`). Summing the DR-mixing-Cu rows gives production `1.93979 s^-1` and day-15 activity `1.41346 Bq`, led by p, n and alpha; all have zero selected rows in this realized fold (representative n Cu-64 at `DELAYED_FLOW:3920`, p Cu-61/62/64 at `DELAYED_FLOW:6583-6585`, alpha Cu-62/64 at `DELAYED_FLOW:1207-1208`). Therefore its delayed W2/Bq coupling is **unsupported/UNKNOWN**, not zero.

The prior multi-knob LC screen is used only as a failure-mode warning: its low-count directed test moved pair hosts into Ag, Mu and MXC and did not demonstrate a prompt reduction (`CORE_TRACE:87-89`). It cannot quantify G-Nb-S1 and is not treated as candidate authority.

### G-Nb-S1 — inner Nb sleeve wall 2.0 -> 1.0 mm, cap unchanged

**Exact geometry delta**

- Change only `Nb_MagShield_Inner_Cylinder_2mm.Shape` from `PCON ... -3.85 4.0 4.2  4.10 4.0 4.2` to a 1 mm-wall cylinder `PCON ... -3.85 4.0 4.1  4.10 4.0 4.1` (`GEO:11760-11768`). Rename the volume to encode 1 mm and update candidate provenance mappings.
- Keep the inner clear radius `4.0 cm`, axial range `-3.85..4.10 cm`, rotation, position, and open upstream end unchanged.
- Keep `Nb_MagShield_Inner_Back_ColdFingerCap_2mm` exactly unchanged at 2 mm (`GEO:11822-11829`). Keep the full 2 mm Mu sleeve and cap unchanged (`GEO:11770-11777`, `11831-11838`). All BGO/BPE/plastic, TES, Cu, Ag, W and readout topology remains unchanged.

**Mass and grammage**

- Nb sleeve mass: `0.351028 -> 0.173374 kg`; radial Nb grammage: `1.714 -> 0.857 g cm^-2`.
- Total modeled Nb sleeve+cap: `0.427585 -> 0.249930 kg`.
- Conditional mass release: `0.177654 kg`, or 50.61% of the sleeve and 41.55% of the modeled Nb system. It is left unassigned as described above.

**Function retained versus not proven**

- Geometrically retained: same TES clear bore, same shield length/open end, unchanged 2 mm Nb back cap, and unchanged complete outer Mu layer. The Nb-to-Mu radial gap increases from 0.5 to 1.5 mm; no new solid approaches TES. A 1 mm axisymmetric sleeve is conventional sheet/form/machining scale, not microfabrication.
- **Not proven:** magnetic attenuation, field-cooling/flux-trapping behavior, seam and penetration performance, mechanical robustness, Nb grade/RRR, thermal anchoring, and TES/SQUID cold noise. No real magnetic CAD or magnetic-material specification is supplied. Thus “function retained” means topology and clearances only, not qualified performance.

**Registered host migration**

- Prompt: the known residual pair host is DR mixing Cu; other immediate candidates are the retained Nb cap, outer Mu cylinder/cap, Ag proxy and MXC Cu plate. Reduction of Nb grammage is not credited unless the *sum over all hosts* falls.
- Delayed: candidate-own n/p/alpha production and direction/energy denominators must be rebuilt. The Nb production Bq and W2/Bq are separate quantities; neither is assumed to scale linearly with the 41.55% Nb-system mass change. Mu, Cu and Ag activities/couplings are tracked as migration channels.

**Direct falsifiers and verdict**

1. **Engineering KILL:** real CAD/BOM shows the sleeve is not a separable 2 mm part, requires a >=2 mm thickness, or 1 mm fails agreed static/dynamic magnetic FEM plus transition-through-Tc field-cool and cold TES/SQUID field/noise tests.
2. **Prompt KILL:** with fixed geometry x mode x family denominators and the denominator-complete 4--10 MeV/corrected-gamma angle-energy set, candidate-own S20 shows that lost Nb pairs migrate primarily to DR Cu/Mu/Ag/MXC or that total active-veto-clean W2 is not reduced. The three historical survivors cannot pass this gate.
3. **Delayed KILL:** candidate-own BUILDUP -> day-15 inventory -> delayed transport yields no net reduction after separately recomputing production Bq and W2/Bq for Nb and migration hosts, with low-Neff/single-high-weight cells explicitly exposed.
4. **Mission KILL:** candidate-own focused signal and common response give central `F3 > 3e-5 photon cm^-2 s^-1`.

Verdict: **MODIFY / ENGINEERING-CONDITIONAL KEEP FOR A SINGLE FOCUSED S20 TEST; not an optimum and not a promotion.** It is the only simple candidate retained by this geometry review because it directly intersects both an observed prompt pair host and a delayed high-coupling host without touching active veto, TES supports, thermal Cu, W/Pb, or readout. The observed DR-Cu prompt branch and dominant delayed MXC-Cu branch are deliberately treated as falsifiers rather than hidden by adding more simultaneous knobs.

## 10. Status and next evidence

Status: **ONE CANDIDATE FROZEN FOR FALSIFICATION; NO TRANSPORT OR OPTIMUM CLAIM.**

The unique engineering blocker is qualified 1 mm Nb magnetic performance in the real seam/penetration/field-cool topology. If that clears, the next physics action is one paired, candidate-own focused S20 calculation with fixed denominators and explicit host migration; no second geometry branch is proposed here.

# NEW_GEO_RE Memory

Current authority is `/home/ubuntu/codex_tes_511_sim/new_geo_re`.

## 2026-06-01 B-FULL Optics Replacement

- Step04 optical handoff now uses the B-FULL Laue model from `/home/ubuntu/opticsim/geant4_app/src/laue_multiring_bfull_demo.cc`, not the old reused Guan smoke scaffold.
- Nominal retained run is `stepwise_maintenance/step04_opticsim/outputs/opticsim_laue_bfull_xopmap_20k/`: external per-ring XOP/CRYSTAL rocking-curve map, `20000` primaries, `6358` analytic phase-space rows, `4977` tracked diffracted focal crossings, energy range `480-550 keV`, Ge(111) five-ring demo, focal length `8300 mm`.
- Online Darwin-Hamilton B-FULL closure run is retained at `stepwise_maintenance/step04_opticsim/outputs/opticsim_laue_bfull_online_20k/`.
- Be-window gate passes against current geometry authority: Be radius `1.898 cm`, Step09 injection plane `z=16.051 cm`, B-FULL XOP-map tracked EventList `r95≈0.2015 cm`, `r99≈0.2661 cm`, max injected radius `1.4291 cm`.
- Step09 now builds the MEGAlib EventList from B-FULL XOP-map tracked `focal_crossings.csv` rows (`source_tag=laue_bfull_diffracted`, within Be), not from analytic `phase_space.csv`, and has a fresh Cosima smoke result: `PASS_EVENTLIST_BRIDGE_SMOKE_TRANSPORTED`, `1000` stored events.
- Rebuilt the optics-derived Step08 spatial-line proxy so the 511-keV line uses only the `995`-row 511-keV EventList subset. Current best robust proxy is `spot_r90=0.1718 cm`: background `0.01632 cps`, `Z20d=22.10`, gain vs line-only `3.02`.
- Removed the old Guan smoke output directory and its smoke5000 visualization files as redundant old-optics artifacts.
- Follow-up checklist for a full new_geo_re rerun is `stepwise_maintenance/step04_opticsim/BFULL_OPTICS_REPLACEMENT_FOLLOWUP.md`. Key remaining work: add lens mass geometry, rerun prompt/proton/neutron and activation through optics solid angle, rebuild delayed source/transport, rebuild day-15 and Step06-Step08 with the optics mass included.
- Current validator authority after this pass: `python3 code/tools/validate_new_geo_re.py` status `PASS`.

## 2026-05-31 Review Follow-Up And Priority Fixes

- `review_20260531.html` was reviewed against current local artifacts. The P0 documentation inconsistency was real: root `README.md`, `workflow.md`, `stepwise_maintenance/CURRENT_PROGRESS_STEP_BREAKDOWN.md`, and Step05/Step02 maintenance README files still quoted old CeBr3-era values. These are now rewritten to the current DEMO2 mainline: fixed delayed activity `624.27109184 Bq`, delayed transport `1584.61 s`, broad final background about `2.35-2.37 cps`, Step08 A-reference `Z20d=2.0466`, and `T3=42.97 day` explicitly labeled as beyond the 20-day mission.
- Added deterministic 511 line-window sidecar at `stepwise_maintenance/step08_significance/code/build_line_window_sensitivity.py`. It reuses the current day-15 event catalog, applies the final active-shield+Compton/FoV selection for background, folds a Gaussian TES response with `.det` authority `sigma=0.14 keV`, and writes `stepwise_maintenance/step08_significance/outputs/line_window_sensitivity.{csv,json,md}`.
- Current line-window sidecar result: broad `480-550 keV` direct proxy `Z20d=2.0505`; `511 +/- 3 sigma_TES` gives background `0.18435 cps`, `Z20d=7.309`, `T3=3.37 day`, and 20-day 3-sigma flux `4.10e-5 ph cm^-2 s^-1`. This is still direct-expectation only, with no spatial/PSF likelihood.
- Added focused-spot spatial proxy at `stepwise_maintenance/step08_significance/code/build_spatial_line_proxy.py`. It uses current final-selected prompt+delayed background TES centroids and, for the 511-keV line, only the 511-keV Step09 EventList subset. Current B-FULL L1 proxy result: 511-keV rows `995`, `r95=0.205 cm`, `rmax=0.3725 cm`; robust `spot_r90=0.1718 cm` cut keeps `0.8995` of the 511-keV signal, reduces line-window background to `0.01632 cps`, gives `Z20d=22.10`, and gives a 20-day 3-sigma flux proxy `1.36e-5 ph cm^-2 s^-1`. This is not a detector-coupled optics PSF transport rerun.
- Added project-local NUBASE2020 archive at `inputs/nubase/nubase_2020.txt` and deterministic half-life unit audit at `code/tools/audit_groundstate_half_life_units.py`. Current audit status is `PASS`: `74` prefix-year rows (`Ey/Gy/My/Ty/ky`) match archived NUBASE line references, unit self-tests cover `ky/My/Gy/Ty/Py/Ey`, W-180 is reduced from `0.28452 Bq` to `5.09e-21 Bq`, and no `74180/74183` source blocks remain in the fixed delayed source.
- Added current CsI activation baseline at `code/tools/audit_csi_activation_baseline.py` with outputs under `outputs/reports/csi_activation_baseline/`. Current baseline status is `PASS`: CsI active-shield volumes contribute `561.13 Bq` (`89.89%` of fixed source activity), I-128 contributes `533.28 Bq` (`85.42%` of total), and `BGO_control_status=NOT_RUN`. This is evidence for the current CsI burden only, not a BGO replacement/control simulation.
- Added BGO control geometry scaffold at `code/tools/build_bgo_control_geometry.py` with outputs under `outputs/geometry/XZTES_ADR_v4c_mkflange_bgo_control/`. Current scaffold status is `PASS`: same DEMO2 geometry/segmentation, `20` BGO active segments, `20` native BGO veto triggers, BGO active mass `102.57 kg` using local MEGAlib `BGO.Density 7.1`, and Cosima overlap check `PASS`. The BGO source/transport/selection/significance chain remains `NOT_RUN`.
- Added review closure matrix builder at `code/tools/build_review_20260531_closure.py` with outputs under `outputs/reports/review_20260531_closure/`. The closure matrix is designed to pass only if no P0 item remains open and live current-doc sections do not contain stale CeBr3 numbers; it explicitly leaves BGO control, detector-coupled PSF transport, and profile likelihood as open/partial lower-priority paper upgrades.
- Added `native_csi_veto_trigger` to `code/tools/validate_new_geo_re.py` so the `.det` claim is enforced: one TES main trigger, 20 CsI veto triggers, each CsI segment threshold `50 keV`, and `NoiseThresholdEqualsTriggerThreshold true`.
- Updated Step07 source-case generation so the V404 `z=0.10` narrow redshift proxy clamps physically negligible response below `1e-100` to exactly zero; `source_case_summary.json` now reports `V404_redshift_narrow_response_fraction=0` and the validator requires this.
- `stepwise_maintenance/step08_significance/code/build_step08_significance.py` now records `A_reference_T3_status=extrapolated_beyond_20d` and separates mission-internal crossing from constant-profile extrapolation in README/headline notes.
- `code/tools/make_complete_day15_report_ADR.py` no longer falls back to the stale legacy delayed-observation constant if the delayed log is unavailable; it derives delayed observation time from fixed-source triggers/activity or fails explicitly.
- `code/tools/validate_new_geo_re.py` now validates the native CsI veto trigger structure, line-window sidecar, spatial line proxy, half-life prefix-unit audit, CsI activation baseline, BGO control geometry scaffold, and review closure matrix. Current `python3 code/tools/validate_new_geo_re.py` status is `PASS`.

## 2026-05-31 DEMO2 Mainline Replacement And Full Rerun

- DEMO2 is now installed into the mainline compatibility authority path:
  `outputs/geometry/XZTES_ADR_v4c_mkflange_cm/TibetTES_ADR_v4c_mkflange_cm.geo.setup`.
  The filename/path intentionally remain the old v4c tokens so existing source cards and code keep running; the content is DEMO2 (`ADR_v6_demo2_adrpassive_csi`) with `CsI_Active_Shield`, staged 50mK/1K/4K/60K Al windows, Cu/W passive shielding, and DEMO2 bounds.
- Old derived `.sim.gz`, `.dat`, and report/output products were cleaned before rerun; current SIM/DAT products are newly generated DEMO2 products unless explicitly marked as smoke-test evidence.
- Cosima geometry load/overlap smoke for the mainline setup passed with no `GeomVol1002`, duplicate material, or geometry-init failure signatures. Native trigger/veto blocks were later added to the `.det` as a formal detector-model statement; downstream Step05 active-shield/Compton veto remains the quantitative analysis authority.
- Step02 event-aligned production completed for both prompt modes:
  `runs/step02_instant_equiv2602_aligned/` and `runs/step02_buildup_equiv2602_aligned/` each have `60/60` jobs passed, `25,210,216` generated particles, and `60` SIM + `60` DAT files.
- DEMO2 delayed source production completed:
  raw source blocks `6008`, fixed source blocks `5968`, fixed activity `624.27109184 Bq`, removed source blocks `40`.
  The fixed source is `runs/step02_delay_fix_equiv2602_aligned/activation_decay_day15_groundstate_fixed.source`.
- DEMO2 delayed transport completed:
  `runs/step02_delayed_transport_equiv2602_aligned/DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz`,
  `1,000,000` generated/stored events, cosima observation time `1584.61 s`.
- DEMO2 science 511 on-axis production completed:
  `runs/science_511_onaxis_source/Science_511_onaxis_ADR_cmfix.inc1.id1.sim.gz`,
  `100,000` triggers/stored events; science summary reports event-summed `480-550 keV = 86,916` and `506-516 keV = 86,210`.
- Complete day-15 Poisson report rebuilt at `outputs/reports/day15_complete_report/`.
  Current active veto authority is `CsI_Active_Shield`; code treats `BGO`, `ACTIVE_SHIELD`, and `CEBR3` tokens as the same active-veto channel for compatibility.
  Observation time is `1584.61 s`, coincidence window `1e-6 s`, veto threshold `50 keV`, reject policy `keep`.
  Current 480-550 keV timeline rates are raw `3.8589937 cps`, active-shield/BGO `3.3471958 cps`, final active-shield/BGO+Compton/FoV `2.3501051 cps`.
  Direct expectation closure is within `0.8%`.
- Step06/07/08/09 were rebuilt after DEMO2:
  Step06 `PASS`, Step07 `PASS`, Step08 `PASS` with A-reference final `Z20d=2.0466` and `T3≈42.97 d`, Step09 `PASS_EVENTLIST_BRIDGE_SMOKE_TRANSPORTED` with `1000` smoke events.
- Validator authority is now `code/tools/validate_new_geo_re.py`; current root `VALIDATION.md` status is `PASS`.
- Older Step01-Step10 notes below this section are historical pre-DEMO2 or intermediate-run records unless explicitly updated above. Do not quote their CeBr3 active-shield name, 110 Bq delayed activity, 9003.74 s delayed observation time, or old 0.3996 cps final background as current DEMO2 results.

## 2026-05-30 DEMO2 Geometry Review Update

- New reviewed demo geometry is under `tmp_mass_model_review_bundle/DEMO2/`, generated by `build_demo2_mass_model.py`.
- DEMO2 keeps the TES stack, Cu sample box, and `SampleBox_Al_Window` from the first demo, but adds staged 50 mK / 1 K / 4 K / 60 K Al aperture-window foils.
- DEMO2 includes an open-aperture `Nb_SC_Detector_Can` with no continuous Nb entrance foil, plus `Cryoperm_Inner_Mag_Shield` as the Ni-rich magnetic-shield proxy.
- DEMO2 adds ADR/cryostat passive proxies: Cu ADR coil, Fe yoke, salt-pill proxy, salt-pill Cu can, stainless heat-switch link, thermal bus, reinforced vacuum jacket/flanges, cold-head interface, SQUID/readout box, harness bundles, and G10 supports.
- Final DEMO2 also adds active-shield packaging/readout/feedthrough proxies: Al backplane/retainers, Kapton flex layer, four external Al readout boxes, and two stainless feedthroughs. These add 1.253 kg and prevent the nominal CsI well from being a bare-crystal-only model.
- DEMO2 adds nominal Cu/W passive shielding inside the CsI active-shield cavity but outside the dewar: Cu inner liner, W outer liner, bottom W shield, and top annular W aperture stop. W is intentionally not the nearest material to the TES; Sn is removed from nominal and kept only as a graded-Z systematic variant.
- Nominal active shield is segmented CsI(Tl) represented as standard MEGAlib `CsI`: side 4 cm, bottom 8 cm, top annulus 2 cm, aperture 1.898 cm, segments 8/4/8, threshold scan 30/50/70/80/100 keV.
- Validation status in `tmp_mass_model_review_bundle/DEMO2/outputs/validation.json` is `PASS`: volume count 90, active CsI mass 65.155 kg, passive mass 24.883 kg, ADR/magnetic/cryostat/service/shield-packaging proxy mass 10.069 kg, active-shield packaging/readout proxy mass 1.253 kg, Cu/W passive-shield mass 5.750 kg, total local modeled mass 90.038 kg.
- Cosima evidence is saved at `tmp_mass_model_review_bundle/DEMO2/outputs/evidence/cosima_overlapcheck_1000pts.txt`; it has a run summary and no `GeomVol1002`, duplicate-material, or detector-initialization failure matches.
- DEMO2 generator now writes `outputs/evidence/overlap_check.source`, runs `/home/ubuntu/MEGAlib_Install/megalib-main/bin/cosima`, inspects the resulting overlap log, and includes the result in `validation.json` and `mass_model_summary.md`; it also validates explicit design requirements for four staged Al-windowed cans, open Nb can, Cryoperm, ADR proxies, active-shield packaging/readout proxies, and Cu/W passive shielding with no Sn nominal side liner.
- DEMO2 design rationale notes are in `tmp_mass_model_review_bundle/DEMO2/outputs/design_review_notes.md`.
- Updated final Chinese reports are `tmp_mass_model_review_bundle/DEMO2/outputs/DEMO2_中文设计审阅报告.md` and `.html`; they directly answer that DEMO2 has the open Nb can/Cryoperm magnetic shield, W passive shield elements, and all four staged Al windows.
- Important caveat: DEMO2 `.det` still marks passive hardware as sensitive for energy-deposition bookkeeping; final TES trigger plus CsI anticoincidence/veto logic remains a downstream Step05-style analysis requirement.
- Physics chain has not been rerun for DEMO2. Prompt transport, buildup activation, delayed source/transport, Poisson day-15 merge, active-shield veto, Compton/FoV veto, time variation, and significance must be rerun before quoting new background or 3-sigma performance numbers.

## 2026-05-30 DEMO2 Independent Review (Claude Opus, tool-verified)

- Reproduced MEGAlib 4.02 cosima load on DEMO2 geometry: clean init, NO duplicate-CsI failure (demo1 P0-1 fixed). Ran `CheckForOverlaps` at BOTH 1000 and 10000 points/tol 1um -> ZERO `GeomVol1002`/overlap signatures (demo1's 7 overlaps P0-2 fixed; TES envelope half-z now pix_z/2=0.15, ColdPlate_60K r=8.35 clears PulseTube r_in=8.98). Logs in /tmp/demo2_review/.
- DEMO2 `validate()` now DOES inspect a real cosima overlap log (P0-3 partially fixed) but only greps the saved log; it still never launches cosima itself, so the gate depends on the log being regenerated. Recommend wiring an actual cosima/CheckForOverlaps subprocess into validate().
- P0-4 NOT changed: `.det` marks all 65 passive volumes as Scintillator (SensitiveVolume+DetectorVolume), only 6 TES layers are MDCalorimeter, and there is NO Trigger/Veto statement (cosima prints "You have not defined any trigger criteria"). This is energy-deposition bookkeeping; real TES-trigger + CsI-veto remains a downstream step05 name-matching task. Documented honestly but must be stated in paper.
- 511-CAM (arXiv:2206.14652) ground truth: passive W INSIDE cryostat + active BGO OUTSIDE; Nb superconducting shield + 0.062in (1.57mm) Amumetal-4K (A4K) magnetic shield; ADR or mini-DR, pre-cooler 300mK -> ~85-100mK, wet LHe (4.2K); entrance window 110nm Al/200nm polyimide (Luxel LEX-HT), 25.4mm aperture, NOT Be; FULL cryostat+detector+shield assembly ~250 kg; their MEGAlib sim used BGO-only (5cm bottom/2cm side, 70keV thr) and explicitly NEGLECTED Nb+A4K+passive-W. So DEMO2 (89.3 kg local head, all proxies present) is MORE complete than the published 511-CAM mass model.
- Key fidelity verdict: DEMO2 nominal now uses Cu->W (Cu nearest TES, W farther out, inside CsI) rather than Cu->Sn->W. This better follows Gehrels' minimize-passive-material guidance for the 480-550 keV use case; Sn is kept only as a graded-Z fluorescence systematic. The first high-Z W remains ~8cm out from r~2cm TES. This intentionally softens 511-CAM's literal "bare W inside cryostat"; defensible, but recommend a systematic that also places some W inside the cold volume to bracket near-field activation.
- Divergences to flag as systematics, not errors: (a) CsI nominal vs 511-CAM BGO reference (oxygen/15O argument still unproven in-project; keep BGO as primary control); (b) Be window vs 511-CAM Al/polyimide (negligible at 511 keV); (c) DEMO2 CsI well 65 kg and ~28cm dia is much larger than 511-CAM's 7cm sim box because it wraps the full ADR head - mass/threshold/efficiency tradeoff needs justification; (d) side liners are thin (Cu 0.8mm/W 0.6mm) so they are modest passive shielding, not bulk passive shield - the CsI is the primary shield; Sn graded-Z fluorescence liner is now a systematic only; (e) ADR magnet/yoke/salt proxies (5.4kg magnet+yoke, 0.271kg GGG-like salt) are plausible but on the light side - bracket with a heavier Full case; Cryoperm 4.5mm (vs A4K 1.57mm) is a conservative proxy.
- Engineering-reasonableness check PASSED for user's two hard asks: (1) ADR/activation mass largely present and shell dims/masses plausible; (2) four staged cans 50mK/1K/4K/60K each with Be-radius-matched aperture + thin Al foil window present and overlap-clean. TES core + Cu sample box + SampleBox_Al_Window retained unchanged per instruction (the across-aperture Al foil is now a deliberate user choice; still recommend open-aperture systematic).
- ADR reality-check (public data, for user who hasn't seen an ADR): real space ADRs (Astro-H SXS / XRISM Resolve) use FAA (rho~1.7) + GGG (rho~7.1) salt pills in stainless cans with internal Au/Cu thermal matrix, NbTi superconducting magnet (few Tesla), mechanical/gas-gap stainless heat switch, and substantial Nb+high-Ni(A4K/Cryoperm) magnetic shielding. XRISM cold mass ~35 kg to 4K; full cooling system (dewar+~30L superfluid He+JT+4 Stirling+vacuum vessel) = hundreds of kg. 511-CAM uses a SIMPLER single-stage ADR or mini-DR (pre-cooler 300mK -> ~100mK), wet LHe. DEMO2 ADR proxies (GGG-like salt 0.271kg+Cu can; magnet solid-Cu-ring 2.4kg; Fe yoke 3.0kg; Cryoperm 1.58kg; stainless heat switch 0.04kg; Cu bus 0.63kg; cold-head 0.26kg; plus packaging) = correct part inventory, sensible materials, topologically correct (salt inside magnet bore, below detector, yoke around magnet), aggregate mass reasonable for a single-stage ADR; but shapes are simplified cylinders/annuli and masses are order-of-magnitude PROXIES (solid Cu ring not NbTi windings; salt light-ish; no internal wire matrix) - faithful as a background mass model, NOT an ADR CAD.
- The 89 kg vs 250 kg gap is BY DESIGN, not an error: 89 kg = near-field detector-head mass that drives 511 keV background (TES+shields+ADR+CsI). 250 kg (511-CAM full assembly) additionally includes the wet-LHe dewar/He-tank/vacuum-vessel structure, pre-cooler/cryocooler, full ADR support+plumbing, full warm+cold readout/harness/electronics, flight BGO+readout housing, and margin - mostly far-field structural/cryo/electronics mass with low 511 keV background relevance. DEMO2 deliberately models the background-relevant subset. The still-near-field part of the gap (readout/harness/support, only ~32 g modeled) is exactly what the Low/Mid/Full passive-mass systematic is meant to bracket.
- "W-into-cold-volume systematic" = an OPTIONAL separate comparison geometry (not adding mass to nominal): make a sibling .geo with some W relocated inside the cold volume per 511-CAM's literal "W inside cryostat", run the same transport, compare 511 keV background; low priority / future work to bound a sensitivity, not a defect to fix.
- SOURCE-VERIFIED (MEGAlib 4.02 src) activation/sensitivity finding: `MCRun::AddIsotope` (src/cosima/src/MCRun.cc:292) keys produced radioactive isotopes by LOGICAL VOLUME NAME (strips trailing "Log"), with NO sensitive-detector check; `MCSteppingAction::GetDetectorId` (MCSteppingAction.cc:2034) returns c_Unknown for non-sensitive volumes and is only a diagnostic field. => Activation localization is volume-resolved natively via `StoreIsotopes true`/`IsotopeProductionFile` for ALL volumes regardless of `.det` sensitivity. So the user's premise "mark all non-TES as Scintillator to record activation nuclide positions" is NOT necessary; it is also NOT a physics error (sensitivity doesn't change Geant4 transport; no Trigger defined so no spurious triggers); it IS a NIM-A referee liability (calling Cu/W/Fe "Scintillator" is misleading + bloats sim). The "everything sensitive" convention is INHERITED from the original v4c `.det` (which marks Outer_Al_Mech_Shell, Vacuum_Jacket_Al, cold plates, Nb can, etc. as Scintillator). Step03 delayed source is built per-volume from RP records + isotope inventory keyed by VN. Recommendation: keep but add a one-line note that activation is native/volume-resolved (least disruptive), OR clean `.det` to TES(MDCalorimeter)+CsI(Scintillator+veto) only.
- NIM-A referee-readiness verdict (review report rev.2, updated after user pushback): as a "representative engineering background mass model (not final/optimized)" there is NO fatal flaw. CORRECTED stance on structural-as-Scintillator: user is right - code/.det is not normally submitted to referees, and it is neither misconduct nor a physics error; moreover in MEGAlib only sensitive volumes write hits, so declaring passive volumes sensitive IS the correct/necessary way to record per-volume energy deposition if wanted (activation localization separately does NOT need it). => DOWNGRADED from P0 to a non-issue ("澄清0"); keep as-is, only ensure paper text describes detectors physically (TES=calorimeter, CsI=veto, rest=passive). Real paper-facing P0s are now just two: P0-1 describe the anticoincidence in text, P0-2 CsI-over-BGO unsimulated vs 511-CAM BGO heritage (soften or run BGO-vs-CsI delayed-activation). P1: validate() self-run cosima; service mass/readout Full case.
- MEGAlib DOES have native anticoincidence/veto: a `Trigger <name>` block with `.Veto true` + `.TriggerByDetector True` + `.Detector <det> 1`. Exact CsI-shield analog exists at `$MEGALIB/resource/examples/geomega/cosiballoon/CsIShield.geo` (CsI_Shield.TriggerThreshold 80.0; CsI_Shield_Trigger.Veto true). COSI Ge guard-ring uses `.Veto True` likewise (GeD_DetectorBuild_*.det). It is threshold-only (energy-over-threshold veto); it does NOT model coincidence-window timing/dead-time/self-veto/accidentals - that is what the user's custom step05 layer adds. Recommendation: add native `Trigger CsI_*.Veto true` (citable, ecosystem use) AND keep the custom downstream timing layer.
- Compton/FoV veto assessment: user's custom FoV/back-projection (not MEGAlib Revan/Mimrec) is JUSTIFIED - Revan(Compton-sequence)/Mimrec(ARM/FoV imaging) target scatterer+absorber Compton cameras with multi-site events; a focusing-optic + TES focal-plane stack is mostly single-pixel photoabsorption, so the native Compton chain is a mismatch. Paper should (a) state this reason to pre-empt referees, (b) optionally cross-check the >=2-pixel subset with Mimrec (511-CAM itself says >=2px events allow Compton imaging), (c) cite the existing validation (CC48 fixed the p1-p2 back-projection sign bug; tests/compton_fov_geometry.py).
- SaltProxy fix completed in DEMO2: material card is now GGG-like Gd3Ga5O12 with density 7.08 g/cm3. Physics note: GGG suits a 1-4K/regenerator-like stage; the ~100mK coldest stage typically uses FAA (rho~1.71) or CPA (rho~1.83), so FAA/CPA remains a future systematic if modeling the exact coldest salt chemistry.
- Independent closing review written to `tmp_mass_model_review_bundle/review_demo2_adrpassive_csi/REVIEW_REPORT_CN.md` (rev.2 adds §3.5 ADR reality, §3.6 89-vs-250 + W-systematic explanation, §4 priority-ordered NIM-A readiness with source-verified §4.1) with reproduced cosima logs in that folder's `evidence/`. Verdict: DEMO2 PASSES geometry acceptance and is paper-defensible; residual actions are P1 (make `validate()` actually launch cosima/CheckForOverlaps, not just grep a saved log) and P2 (`.det` has no Trigger/Veto and marks all passive as Scintillator -> implement TES-trigger+CsI-veto or audit downstream), then rerun the full physics chain before quoting any new background/3-sigma numbers.

## Step01 Geometry Revision

- Source copied from `new_geo`, excluding `.sim.gz` and `.dat` products.
- Clean layout uses `code/`, `config/`, `outputs/`, `records/`, `tests/`, and `stepwise_maintenance/`.
- Raw geometry is generated under `outputs/geometry/raw_mm/`.
- Cosima cm geometry is generated under `outputs/geometry/XZTES_ADR_v4c_mkflange_cm/`.
- Mass-model publication review note is `MASS_MODEL_UNIT_DESIGN_RATIONALE.md`; it lists the geometry code authority, every modeled unit, design criteria, and paper-risk wording for GPT Pro review.
- Be-window reference is taken from `fix`: `Win_Be` radius `1.898 cm`, thickness `0.015 cm`.
- All axial cavity holes and window radii in the revised geometry are set to `1.898 cm`.
- Added thin superconducting can window:
  - `Win_Nb_SC_Detector_Can`
- Added two thin Al thermal-shield windows:
  - `Win_4K_Al_Shield`
  - `Win_50K_Al_Shield`
- A4K/Cryoperm is omitted from the gamma-background prototype; the vacuum-jacket aperture is closed only by `Win_Be_Cryostat`.
- Existing ADR envelope, TES stack, cold plates, Nb can, thermal shields, active shield, and outer shell are otherwise kept close to `new_geo`.

## Step02 Raw Background Simulation

- Step02 is a raw-simulation checkpoint only; it does not include Poisson timeline merging, BGO veto, Compton veto, or downstream event selection.
- Atmospheric source cards are `config/megalib_sources_fullsphere20/Background_*_fullsphere20.source`.
- Original Step02 smoke products were cleaned as redundant after event-count-aligned production completed. The current Step02 data authority is the `runs/step02_*_equiv2602_aligned/` production set plus the stepwise summaries.
- Event-count-aligned production run is complete against the old `COSMOSRAY_BALLOON_SIM` production event budget.
- Aligned prompt `instant`: `runs/step02_instant_equiv2602_aligned/`, `60/60` jobs passed, `25,210,216` generated particles.
- Aligned activation `buildup`: `runs/step02_buildup_equiv2602_aligned/`, `60/60` jobs passed, `25,210,216` generated particles.
- Aligned per-particle counts match the old target exactly: gamma `10,000,000`, n `7,704,528`, eminus `3,316,936`, eplus `1,949,816`, p `1,871,808`, alpha `191,464`, muplus `92,840`, muminus `82,824`.
- Aligned delayed source: `runs/step02_decay_source_equiv2602_aligned/activation_decay_day15.source`; fixed source `runs/step02_delay_fix_equiv2602_aligned/activation_decay_day15_groundstate_fixed.source`; fixed activity about `110.0882 Bq`, source blocks `4674`, removed blocks `54`.
- Aligned delayed transport: `runs/step02_delayed_transport_equiv2602_aligned/DelayedDecayRPIPGroundStateFixed.inc1.id1.sim.gz`; SIM reports `TS 1000000`, `SE 1000000`, `TE 9003.74091 s`.
- Event alignment matches input event counts, not physical exposure time; new `new_geo_re` far-field radius is `35 cm`, while the old production normalization used `150 cm`.
- Step02 summary outputs are under `stepwise_maintenance/step02_raw_background_simulation/outputs/`.

## Step03-05 Alignment Status

- Current task status: `new_geo_re` is aligned with `fix` Step03/Step04/Step05 granularity while keeping the detector mass model as `new_geo_re`.
- Step03 completed: `stepwise_maintenance/step03_delay_source/` now contains delayed-source audit outputs matching `fix` granularity: fixed source-block CSV, activity saturation CSV, 1k/10k sampled source CSVs, WRL, 2D schematic, unknown half-life remap ledger, JSON audit, snapshots, and README.
- Step03 key numbers: raw source blocks `4728`, fixed source blocks/listed sources `4674`, fixed activity `110.088197271 Bq`, removed/rescaled blocks `54`, fixed profile files referenced/present `4674/4674`, rank for 95%/99% activity `3/23`.
- Step04 status is superseded by the 2026-06-01 B-FULL replacement above: `stepwise_maintenance/step04_opticsim/` now audits the B-FULL XOP-map/online Laue runs. It is still not a detailed mechanical lens mass design.
- Step05 completed: generated `runs/science_511_onaxis_source/Science_511_onaxis_ADR_cmfix.inc1.id1.sim.gz` with `100000` triggers/stored events and science summary under `outputs/reports/science_511_ADR_100k/`.
- Step05 completed output authority: `outputs/reports/day15_complete_report/complete_day15_summary.json`, PDF report, CSV/DAT tables, and figures; maintenance note is `stepwise_maintenance/step05_veto_time_axis/README.md`.
- Step05 key settings: `obs_time_s=9003.74`, `coincidence_window_s=1e-6`, `BGO_THR_KEV=50`, `reject_policy=keep`, `rng_seed=260511`.
- Step05 Poisson draw: prompt `6982799`, delayed `607839`, science `40`; total instances `7590678`, candidates with TES `154970`, mixed candidates `954`.
- Step05 480-550 keV timeline rates after Compton/FoV back-projection fix: raw `0.8319875963 cps`, active-shield/BGO `0.4716928743 cps`, final active-shield/BGO+Compton/FoV `0.3996117169 cps`; direct expectation cross-check raw/BGO/final `0.8343517405/0.4650986141/0.3887707531 cps`.
- Important detector-model difference for Step05: `new_geo_re` active veto volume is `CeBr3_Active_Shield`; the analysis will treat names containing `BGO`, `ACTIVE_SHIELD`, or `CEBR3` as the active-shield/BGO-veto channel while retaining the fix baseline threshold of `50 keV`.
- CC48 review accepted fix: Compton/FoV back-projection must point from the first hit back toward the source plane (`p1 - p2`), not along the scattered direction (`p2 - p1`). A synthetic Be-window-center 2-hit test now lives at `tests/compton_fov_geometry.py`.
- Threshold note: `bounds.json` CeBr3 design recommendation remains `30 keV`; Step05 analysis baseline remains `50 keV` for comparison with `fix`.
- Naming note: `cmfix` in the live science SIM filename is the current cm-scaled source-card token, not the old stale background-production path family.
- CC48 review hygiene fix: `code/tools/make_new_geo_closure_report.py` now points to `step02_*_aligned` paths and `cosima_delayed_transport_1m.log`; the generated `outputs/reports/full_flow_closure/` report was later cleaned as a redundant derived report and can be regenerated.

## Step06/Step07/Step08/Step09/Step10 Closure Roadmap Progress

- Step06 completed at `L0_PROXY_COMPLETE`: `stepwise_maintenance/step06_mission_time_variation/` now contains the mission time-variation layer with no new Cosima transport.
- User trajectory constraint is enforced: max `|latitude_offset|=0.25 deg`, max `|longitude_offset|=0.25 deg`, max `|altitude_offset|=2.5 km`.
- Step06 remains a rate-level mission-time fold with no new Cosima transport; it has not yet rerun detector response or optics-mass activation after the B-FULL handoff.
- Step06 atmospheric correction is explicitly audited: Beer-Lambert residual-depth proxy calibrated to Step05 `T_atm=0.7390423888027`; day-15 `T_atm=0.739042388803`, absolute closure error about `3.0e-13`, range `0.6461226` to `0.811095`.
- Step06 prompt/delayed-production L0 driver sign was corrected after the Claude review: the secondary-dominated proxy now increases with residual atmospheric depth and decreases with altitude; low-altitude prompt scale `1.05298763053`, high-altitude scale `0.965181809612`, altitude-vs-prompt correlation `-0.9946100642388752`.
- Step06 delayed activity is per-nuclide ODE anchored to Step03 day-15 inventory; max per-nuclide day-15 relative error `1.18e-16`, max total activity closure `9.24e-14`.
- Step06 day-15 rate closure against Step05 expectation is `1.18e-13`; prompt/delayed/science final cps at day15 are `0.09258720278901`, `0.2938778774154`, `0.002305672906623`.
- Step07 completed at `L1_SOURCE_CASE_RATE_FOLDING`: `stepwise_maintenance/step07_source_cases/` now contains A/B/C source cases, literature-anchor YAML, spectra, diffuse sky models, cm source cards, folded rates, point-vs-diffuse diagnostics, and figures.
- Step07 remains a source-case rate-folding layer over the existing Step05 detector response; it has not yet been rebuilt as production detector-coupled optics transport or optics-mass background production.
- Step07 authority: `A_opt=50.89 cm2`, `T_atm_ref=0.7390423888027`, plane rate per flux `37.6098671661694 cps/(ph cm^-2 s^-1)`, final science response `23.056729066227867 cps/(ph cm^-2 s^-1)`.
- Step07 closure: A on-axis mono `1e-4 ph cm^-2 s^-1` final rate and plane rate both close exactly to Step05 (`0.0023056729066227868 cps` final, `0.0037609867166169403 cps` plane).
- Step07 diffuse policy: B bulge/disk is aperture-integrated and skipped as a focal-spot Cosima card until a real optics focal map exists; default B final rate is `1.9101607361936473e-05 cps`, `4.9426476906620075e-05` of the instrument final background.
- Step07 generated four point-source transport candidate cards under `stepwise_maintenance/step07_source_cases/outputs/run_configs/`; all use `z=16.051 cm`, `r=1.8 cm`.
- Step08 completed at `L1_COUNTING_TIME_DEP_WITH_ANALYTIC_ACCIDENTAL`: `stepwise_maintenance/step08_significance/` now contains time-dependent cumulative significance, T3/T5 summaries, rate-independent veto efficiencies, accidental live-factor ledgers, and figures.
- Step08 accidental model is analytic: `live_factor = exp(-R_coincidence_hz * 1e-6 s)`, where `R_coincidence` is the time-dependent prompt+delayed catalog event occupancy rate from Step06 scaling.
- Step08 accidental loss range over the synthetic mission is `0.0008046129834964333` to `0.0008860077736297933`; day-15 scale loss is `0.0008427610548547015`, matching the expected order for about `843 Hz` and `1 us`.
- Step08 source significance after the Step06 sign correction: A compact-GC anchor `8e-5 ph cm^-2 s^-1` reaches final 20-day counting `Z=3.9085358786535704`; A reference `1e-4 ph cm^-2 s^-1` reaches `Z=4.88566984831696` and crosses 3 sigma at `6.784446087481758 day`.
- Step08 template/proxy policy: `template_proxy_Z` is intentionally equal to counting `Z` (`template_proxy_gain=1.0`) until a selection-consistent profile likelihood is implemented.
- Step08 bootstrap note: `accidental_representative_anchor.csv` is a fast energy/BGO catalog sanity anchor at min/mean/max representative rates; Compton is not recomputed there and it is not a full per-bin MC timeline.
- Step09 completed at `L1_OPTICS_EVENTLIST_BRIDGE`: `stepwise_maintenance/step09_optics_bridge/` converts the Step04 Laue `phase_space.csv` to a MEGAlib EventList at the current cm Be-window plane and runs a 1000-trigger Cosima smoke transport.
- Step09 EventList bridge numbers after B-FULL XOP-map replacement: tracked within-Be rows seen/written `4968/4968`, energy range `480-550 keV`, z plane `16.051 cm`, x/y scale `0.1 cm per opticsim mm`, max radius `1.4290581370555617 cm` within Be radius `1.898 cm`, direction `uz<0`.
- Step09 smoke transport output: `runs/step09_optics_bridge/Opticsim_laue_new_geo_re_smoke1000.inc1.id1.sim.gz`, stored events `1000`, observation time `9.99e-07 s`.
- Step09 scope caveat: this bridges focused Laue phase space into the detector; it still does not include prompt/delayed activation or scattering from the optics hardware mass itself.
- Step10 validator added and extended through Step09: `code/tools/validate_new_geo_re.py`; current root `VALIDATION.md` status is `PASS`.

## 2026-05-26 NEW_GEO_RE complete day-15 report update

- Generated complete report with science+prompt+fixed-delayed Poisson common timeline: `outputs/reports/day15_complete_report/cosmosray_bg_NEW_GEO_RE_ADR_complete_day15_report.pdf`.
- Observation time 9003.74 s, coincidence window 1.0e-06 s, BGO threshold 50 keV, reject_policy `keep`.
- Timeline 480-550 keV rates after Compton/FoV back-projection fix: raw 0.831988 cps, BGO 0.471693 cps, final 0.399612 cps.
- Direct expectation cross-check after Compton/FoV back-projection fix: raw 0.834352 cps, BGO 0.465099 cps, final 0.388771 cps.
- Science reference flux 0.0001 ph cm^-2 s^-1 is included as an independent stream; expected science final rate 0.00230567 cps.
- Audit confirmed fixed delayed source has no W183/W180 source-block residual.

## 2026-05-31 DEMO2 complete day-15 report update

- Generated complete report with science+prompt+fixed-delayed Poisson common timeline: `outputs/reports/day15_complete_report/cosmosray_bg_NEW_GEO_RE_ADR_complete_day15_report.pdf`.
- Observation time 1584.61 s, coincidence window 1.0e-06 s, BGO threshold 50 keV, reject_policy `keep`.
- Timeline 480-550 keV rates: raw 3.85899 cps, BGO 3.3472 cps, final 2.35011 cps.
- Direct expectation cross-check: raw 3.86466 cps, BGO 3.37085 cps, final 2.36821 cps.
- Science reference flux 0.0001 ph cm^-2 s^-1 is included as an independent stream; expected science final rate 0.00239928 cps.
- Audit confirmed fixed delayed source has no W183/W180 source-block residual.

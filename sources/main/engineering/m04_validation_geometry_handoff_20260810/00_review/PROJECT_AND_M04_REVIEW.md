# M04 project and manuscript review

- Review time: 2026-08-10 (Asia/Shanghai)
- Contract: `engineering/m04_validation_geometry_handoff_20260810/SESSION_BOOTSTRAP.md`
- Contract SHA-256: `f907243451a83bb9c496628e337c63fb328beb7a85e96c26c5342913b4af33f9`
- Review mode: read-only review of retained products; no transport, BUILDUP, delayed, prompt, response, or Cosima run was started.

## Executive result

`WP0_AUDIT_COMPLETE_WITH_EXPLICIT_BLOCKERS`

The protected M04 manuscripts, historical PDFs, frozen workflow figures, other
pre-Results figures, and the three O8 geometry authority files all match the
handoff hashes.  The English and Chinese manuscripts have one-to-one section,
equation/table/figure-label, and headline-result structure.  Every current
project-generated headline-number cluster is represented in
`manuscript_claim_to_source_matrix.csv`; traceability coverage is therefore
100%, but traceability must not be confused with scientific validity.

The present headline background and mission numbers are conditional old-model
results.  They combine a single `M=50000, seed=260613` delayed-source
realization with the historical semi-empirical atmospheric-511 sidecar.  A
later raw-SIM audit found a more fundamental legacy photon-input problem: the
O8 broadband-gamma card points to `_2602units` spectra whose already-correct
keV abscissae were divided by 1000 a second time.  The old PARMA broad-bin
annihilation bump was therefore transported at 0.44965--0.71264 keV, not near
511 keV.  It represents the same source-level annihilation family as the
sidecar, but it does **not** double-count the detector W511 response.  Offline
removal of that misplaced term changes both Broad480--550 and W511 by exactly
zero.  The old sidecar still must be replaced by the corrected PARMA
monoenergetic module, and the broader prompt-photon energy-axis defect prevents
the retained module from becoming publication-grade physical authority.  No
continuum rerun is authorized or inferred from this finding.

## User scope clarification that supersedes run recommendations

The user clarified on 2026-08-10 that this project is modular and that the
handoff must **not** be interpreted as authorization to rerun the full particle
field or full chain:

1. finite-`M` validation is an offline/source-data analysis and starts no new
   simulation;
2. the PARMA correction changes only the independent atmospheric-annihilation
   511 keV monoenergetic module;
3. prompt, delayed, focused-signal, continuum, geometry-response, and other
   particle modules are retained and reused;
4. downstream totals may be recomposed from retained modules plus the corrected
   511-keV module;
5. where existing modular evidence cannot close a requested A/B, the claim is
   weakened or marked unclosed; no other-particle or full-chain rerun is inferred.

This explicit instruction governs execution.  Consequently, the transport
matrix in handoff Section 7.3B, continuum transport in Section 8.4.6, and the
new other-particle A/B runs proposed in Section 9.4 are not part of the present
authorized workflow.  No such run has been launched.

## Worktree safety snapshot

- Branch: `delayed-source-authority-v2-20260624`
- HEAD: `11ae2af2cdf5129b70d631565a0b306815a5ecfe`
- Upstream: `origin/delayed-source-authority-v2-20260624`
- Pre-WP0 `git status --short`: 152 entries: 20 tracked modifications and
  132 untracked entries.
- The whole handoff package was already untracked at the snapshot boundary.
- Existing user modifications were neither cleaned nor overwritten.
- No `git reset`, `git clean`, destructive checkout, or package-44 `--force`
  path was used.

The working tree is intentionally dirty.  Task scope is audited by new paths
under this handoff package and by protected hashes, not by assuming a clean Git
baseline.

## Frozen baseline

`protected_file_hashes.sha256` verifies 19 files: two M04 TeX files, two
historical PDFs, six EN/ZH Figure-2 source/render files, six other pre-Results
figures, and the O8 setup/geometry/detector triplet.  A direct
`sha256sum -c` check passed all 19 entries.

The content prefixes before Results also match the handoff:

| Manuscript | Frozen range | SHA-256 | Result |
| --- | --- | --- | --- |
| EN | lines 1--1199, before `\\section{Results}` | `c72137b78a66e45add8c4d5c25dfd07261a873862b7c202916b73d0c125f5e50` | PASS |
| ZH | lines 1--669, before `\\section{结果}` | `1b11acad70efd5f10df6adba63a993462466954d052a2bab12f441f70276fc47` | PASS |

No protected file was edited or rebuilt.

## TeX/PDF version mismatch

The current sources are newer than their same-name PDFs:

| Item | TeX mtime | PDF mtime | Consequence |
| --- | --- | --- | --- |
| M04 EN | 2026-08-10 18:10:30 +0800 | 2026-08-10 17:42:03 +0800 | PDF is stale and not review evidence |
| M04 ZH | 2026-08-10 18:10:30 +0800 | 2026-08-10 17:42:04 +0800 | PDF is stale and not review evidence |
| Figure 2 EN | 2026-08-10 18:11:28 +0800 | 2026-08-10 17:40:23 +0800 | rendered PDF predates source |
| Figure 2 ZH | 2026-08-10 18:10:29 +0800 | 2026-08-10 17:41:16 +0800 | rendered PDF predates source |

The stale PDFs were not used to judge current Section 3 content.  If an M05
copy is later authorized by the data gates, the copied Figure 2 and copied main
documents must first be rebuilt inside the isolated copy without writing into
M04.

## EN/ZH structural correspondence

The manuscripts have 22 corresponding numbered section headings in the same
order.  Both contain 43 displayed equation/align/table/figure environments and
17 `eq`/`tab`/`fig` labels.

| EN location | ZH location | Correspondence |
| --- | --- | --- |
| Introduction, line 93 | 引言, line 78 | PASS |
| Science and instrument requirements, line 177 | 科学目标与仪器要求, line 93 | PASS |
| Detector and cryostat mass model, line 241 | 探测器与低温系统质量模型, line 114 | PASS |
| Simulation framework, line 328 | 模拟框架, line 136 | PASS |
| Source construction and three source subsections, lines 379--682 | 源构建及三个源小节, lines 175--381 | PASS |
| Geometry/statistics and detector selection, lines 742--1089 | 几何/统计与事例选择, lines 420--586 | PASS |
| Mission-time fold, line 1090 | 任务时间轨迹折叠, line 587 | PASS |
| Results plus four subsections, lines 1200--1505 | 结果及四个小节, lines 670--861 | PASS |
| Discussion, limitations, conclusions, lines 1506--1590 | 讨论、适用范围、结论, lines 862--882 | PASS |

The bilingual structure passes.  Scientific synchronization does not: both
languages consistently repeat the same old atmospheric-line model, single-M
boundary, incomplete final-stack description, and BGO-only veto wording.

## O8 geometry authority

The retained setup includes the expected O8 `.geo` and `.det`, and all three
hashes match:

| Authority | SHA-256 | Result |
| --- | --- | --- |
| `.geo.setup` | `86a9e56e54dc86834dfe2a9b03a5f71373fb40f2ef24e3889fa66f216058fbec` | PASS |
| `.geo` | `ff4e8402df702501e0112fe377d837a74c39100317146b09e9569b7bd615c37c` | PASS |
| `.det` | `dd2c1d68cd474f8b0c7489f2cbbfc924eb69beb14d3ce360d9437c319a33d6cb` | PASS |

The final geometry is the O8 `side40/bottom30/top10/no-outer-W2/Al3`
configuration, not a BGO-only object.  Instrument-local dimensions are:

| Layer | Actual final definition |
| --- | --- |
| 5 wt% BPE side | 20 mm, `r=27--29 cm`, `z=-24.5--46.0 cm` |
| 5 wt% BPE bottom/top | 20 mm caps, `r=0--29 cm`, `z=-26.5---24.5 cm` and `46--48 cm` |
| Active plastic side | 10 mm, `r=29--30 cm`, `z=-26.5--48 cm` |
| Active plastic bottom/top | 10 mm caps, `r=0--30 cm`, `z=-27.5---26.5 cm` and `48--49 cm` |
| BGO side | 40 mm, `r=21.2--25.2 cm`, `z=-19.4--40.9 cm` |
| BGO bottom | 30 mm, `r=0--25.2 cm`, `z=-22.4---19.4 cm` |
| BGO top | 10 mm annulus, `r=20.9--25.2 cm`, `z=40.9--41.9 cm` |
| Kapton | 0.3 mm side/bottom/top wrappers; top is an annulus |
| Al | 3 mm side/bottom/top enclosure; top is an annulus |
| W statement | the continuous outer W2 volumes are removed; the W bottom plate and multihole collimator remain |

The whole `InstrumentFrame` is rotated by 45 degrees.  BGO, Kapton, and Al
side volumes contain the aligned optical Boolean cut; the BGO side also has a
pump-line relief.  BGO/Kapton/Al top volumes have the `r_inner=20.9 cm`
service opening.  All listed volumes retain six NF2 rod reliefs.

The BPE/plastic side and cap primitives retain NF2 mount/rod reliefs, but have
no named `RectWindowCut`, `PumpLineRelief`, or `r_inner=20.9 cm` central-service
subtraction.  Therefore the BGO/Kapton/Al optical aperture cannot be assumed to
continue as a vacuum opening through the BPE/plastic outer envelope.  The
retained focused EventList begins at the Be-window plane and establishes only
the downstream detector acceptance, not transmission through the complete
outer envelope.

The BGO-to-Kapton gaps are 0.17/1.17/3.17 cm for side/bottom/top; the
Kapton-to-Al gap is 0.30 cm.  These are transport-geometry clearances, not a
structurally qualified fitted shell.  Reported masses are pre-relief analytic
bookkeeping only.

## Selection authority

The final Step05/response predicate is a string-based offline mask.  It includes
BGO and the outer active plastic volumes, but it also accepts every scored
volume whose name contains `ACTIVE_SHIELD`.  The passive Kapton wrappers are
named `ActiveShield_S3C_BGO_Kapton_*`, and retained raw SIM files contain `CC
HIT` rows under those names.  Consequently their deposits are also summed into
the implemented 50 keV veto, despite the package-44 description saying that
Kapton is excluded.  Al remains excluded.  This is a pre-existing selection
implementation defect, not a material-property statement.

The common threshold is an offline event-level sum of 50 keV, not the native
hardware trigger threshold.  The `.det` carries 80 keV BGO scorer thresholds
and very low plastic scorer thresholds, while native MEGAlib Trigger/Veto
blocks are absent.  Thus M04 EN line 1328 / ZH line 746 (`BGO offline
anticoincidence`) is incomplete, and the review's earlier shorthand
`BGO+plastic` was also too narrow.  The exact frozen implementation is
`BGO + plastic + passively named ActiveShield/Kapton scorer volumes`.

## Headline-result dependency boundary

The detailed chain is in `manuscript_claim_to_source_matrix.csv`.  The key
dependency groups are:

1. **Reference diagnostic**: traceable to the reference response breakdown and
   mass-model selected-event catalogue.  It excludes atmospheric 511 by design
   and is not a matched shield-gain comparison.
2. **Final prompt**: retained all-eight O8 prompt catalogue; reusable without
   rerunning.
3. **Final delayed**: retained all-eight package-44 catalogue; normalized by
   family and NUBASE ground-state correction, but based on one finite-M source
   realization for every positive family.
4. **Atmospheric 511**: retained old 3M semi-empirical sidecar and its response;
   this is the only physical transport module to be replaced under the current
   instruction.
5. **Focused signal**: retained Be-plane EventList and detector response;
   reusable for downstream acceptance, not evidence for outer-envelope optical
   transmission.
6. **Mission fold**: analytic composition of the above modules over 81 time
   bins.  It may be recomputed after swapping only the atmospheric-511 module.

Current final values (`B=6.96486e-3 cps`, `S=9.86228e-4 cps`, `Z20=15.199`,
`F3sigma=1.9738e-5 ph cm^-2 s^-1`, and the conditional endpoint bundle) are
therefore traceable but not final-authority values after the PARMA repair.

## Finite-M implementation audit

The source builder reads and records `exc_keV`, but distributes activity and
constructs sampling weights using only `(VN, ZA)` keys.  M04 EN lines 578--580
and ZH lines 321--322 state that the fixed population is matched by volume,
isotope, **and excitation state**; that is not the implemented allocation key.

For each positive family, package 44 uses `M=50000`, source seed `260613`, and
one retained delayed transport.  The neutron source audit reports 58,672
eligible RPIP rows and 0.157388 Bq (0.515% of neutron activity) in undrawn
`(VN,ZA)` groups.  The 0.515% is a source-support diagnostic, not an upper bound
on the selected W511-rate error.

M04 also alternates between “one million delayed decays” and the actual Cosima
`Triggers`/pre-trigger request semantics.  `TE` supplies component rate
normalization and is not physical balloon exposure.  These terms must remain
separate:

- finite BUILDUP yield uncertainty;
- finite-M source-support uncertainty;
- finite retained transport-count uncertainty;
- 64-seed detector-response numerical integration variability.

Per the user scope clarification, WP1 will use the retained weighted tables,
source realizations, catalogues, and response products only.  It will not
launch a transport matrix.  Any detector-selected convergence statement not
identifiable from those retained modular products will be reported as an
unclosed systematic rather than manufactured by a new run.

## Atmospheric-511 and retained prompt-photon audit

M04 EN lines 333 and 458--467 (ZH corresponding source-framework passages)
describe the local EXPACS/PARMA photon tables as smooth continuum without a
discrete 511-line entry, then add a full independent semi-empirical mono line.
The raw table does have a 0.56608 MeV enhancement containing the PARMA
annihilation contribution, and official PARMA exposes the native 511-line
term.  However, the retained O8 source card does not use the correctly converted
keV DP.  It uses `cosima_spectra_dp_2602units/`, whose abscissae were divided by
1000 after the MeV-to-keV conversion.  Cosima interprets file abscissae as keV,
and 10 million retained `IA INIT` records confirm that the enhancement was
actually sampled around 0.56608 keV.

The source model therefore contains the annihilation family twice in its
nominal bookkeeping, but at detector level the broadband occurrence is
misenergized into a sub-keV active-only population.  The offline event-level
audit identifies 858,044 generated events on that interpolation support and
317,048 retained catalog rows, all with zero TES energy.  Its line-term
deduplication changes Broad480--550 and W511 by exactly 0 cps.  The detailed
machine-readable authority is
`../02_parma_atm511_repair_20260810/data/o8_prompt_gamma_line_dedup_audit.json`.

The retained inputs also mix day-15 metadata:

- prompt manifest: `W=118.3`, `Rc=11.6 GV`, nominal 38 km;
- line source: `Rc=11.0 GV`, `X=3.461468972 g cm^-2`;
- another phase-2 reference: `W=114.6`, `Rc=11.6 GV`, 38 km,
  `X=3.865098532 g cm^-2`;
- the paper trajectory day-15 state uses 38.75 km and
  `X=3.461468972 g cm^-2`.

WP2 freezes one day-15 authority and changes only the native PARMA
monoenergetic atmospheric-annihilation module.  Existing continuum and all
non-atmospheric-line products remain read-only.  For Broad and W511 the modular
recomposition is therefore exact and simple: retain the old broadband-gamma
selected rate, remove the historical sidecar, and add the corrected PARMA line.
The misplaced broad-table line term has zero selected-rate contribution in
those windows.  This operational correction does not certify the remaining
legacy broadband-gamma energy axis.

## Manuscript consistency findings

The answer-first, Methods-to-Results, and Abstract-to-Results checks identify:

1. Abstract, Results, Discussion, and Conclusions carry the same final central
   and conditional headline bundle, but it depends on the old atmospheric-line
   module and single-M delayed sources.
2. Requirements EN lines 193--203 derive a payload-plane reference
   `1.565e-4 ph cm^-2 s^-1`, while the simulation/mission headline uses the
   rounded top-of-atmosphere `F0=1e-4 ph cm^-2 s^-1`.  These are different
   reference definitions and must not be presented as one benchmark.
3. Methods claim excitation-state matching although the builder keys only on
   `(VN,ZA)`.
4. Methods call the delayed request physical “decays” in places where the run
   authority specifies Cosima triggers.
5. The final-geometry table omits the retained BPE and active plastic layers.
6. The final selection is described as BGO-only, while the predicate includes
   BGO, plastic, and unintentionally the passive Kapton wrappers through the
   `ACTIVE_SHIELD` substring rule.
7. The claim that the focused beam passes through aligned surrounding-shell
   apertures is not established for the BPE/plastic outer envelope.
8. `no W` must always mean `no continuous outer W2`; other tungsten remains.

Because the affected source and method statements lie in the frozen prefix,
they are recorded here and not silently edited.

## Provenance conflicts and blockers

| ID | Severity | Finding | Required handling under current scope |
| --- | --- | --- | --- |
| B01 | RED | Current same-name M04 PDFs predate their TeX and Figure-2 sources. | Do not review/rebuild M04 PDFs; rebuild only inside a future isolated M05 copy. |
| B02 | RED | The raw prompt table contains the PARMA annihilation term and a full old sidecar was also added, but the retained DP misenergized the broad term to 0.45--0.71 keV. | Offline line-term removal has zero Broad/W511 effect; replace only the old sidecar with the corrected mono-line module. |
| B03 | RED | Day-15 `W/Rc/X/altitude` values are not unique across retained inputs. | Freeze one authority before producing a corrected line rate. |
| B04 | RED | All final delayed families use one `M=50000, seed=260613` realization. | Offline M audit only; if retained data cannot identify selected-rate convergence, label it unclosed. |
| B05 | RED | Manuscript says `(volume,isotope,excitation)` matching; builder uses `(VN,ZA)`. | Prepare a frozen-prefix correction proposal; no M04 edit. |
| B06 | RED | M04 describes BGO-only veto; the offline 50-keV string predicate includes BGO + plastic and unintentionally passive `ActiveShield_*_Kapton_*` volumes. | Freeze and disclose the exact historical predicate for comparison; do not call it a pure scintillator veto or silently change it. |
| B07 | RED | M04 final-geometry table omits 20 mm BPE and 10 mm plastic. | Include the complete stack in any future new section. |
| B08 | RED | BPE/plastic do not contain the BGO/Kapton/Al optical/service cuts. | Exclude full-envelope optical-transmission claims; retained Be-plane signal proves downstream acceptance only. |
| B09 | RED | Figure-story provenance records five obsolete hashes: current slant45 summary/validation/timeline plus response and mission validations. | Do not cite rendered story figures as hash-closed until rebuilt in an isolated successor package. |
| B10 | RED | Mass-model status documents conflict: early claim/status files say products/gates were not run while later retained gate/closure products exist, with no unique supersession declaration. | Use actual retained gates for engineering provenance but keep the conservative manuscript boundary. |
| B11 | RED | Some original old config/fix5/NF2 inputs are absent by cleanup policy. | Do not restore or infer them; cite retained authority snapshots only. |
| B12 | AMBER | `3 mm Al + Kapton` wording can imply a fitted enclosure, but geometry has deliberate clearances. | State actual coordinates/gaps and `transport geometry, not structural qualification`. |
| B13 | AMBER | `no outer W2` can be misread as no tungsten anywhere. | Explicitly retain the W bottom plate and W collimator. |
| B14 | AMBER | `1e6 delayed decays` is not consistently distinguished from requested triggers and `TE` normalization. | Use precise run semantics in the correction proposal. |
| B15 | AMBER | Root bilingual-alignment validations target root drafts, not the named M04 pair. | This WP0 uses direct M04 structural comparison; do not cite stale validators as M04 authority. |
| B16 | RED | The retained O8 broadband-gamma `_2602units` DP abscissae are lower than the physically converted keV axis by a factor of 1000. | Keep it only as a user-frozen legacy module; do not claim physical prompt-photon fidelity and do not infer a continuum rerun from this audit. |

The stale story-provenance values are concrete:

| Input | Provenance-recorded hash | Current hash |
| --- | --- | --- |
| slant45 summary | `4275b9b6...f19c0b` | `f7ec57c9...c148ba` |
| slant45 validation | `c4c09d4f...696f84` | `cba48162...5cc` |
| slant45 timeline | `b04a1b41...2bb` | `00f3c8ed...f8ce` |
| response validation | `ed359c2a...8ba15` | `8a7f2cf9...fa64a` |
| mission validation | `089bdb51...2a15` | `94acc3b9...d674` |

## Evidence grades retained for later writing

| Grade | Permitted use |
| --- | --- |
| A | Exact O8 geometry/material/hash facts and retained selection-code facts. |
| B | Internally closed but conditional package-44 prompt/delayed/response modules; disclose single-M limitation. |
| C | Historical matched/low-count O9/O8/C0 screening used only to explain the design decision; atmospheric sidecar is old. |
| D | S1/S2b stack changes, proxies, and pre-relief masses used as motivation, never as single-layer causal effects. |

Examples: the S1 `0.0484939 -> 0.0353806 cps` plastic replay isolates
offline veto information, not plastic material transport; the
`141.833 -> 106.482 Bq` change belongs to a combined shield-stack change, not
BPE alone.  O8 historical screening supports why O8 was promoted, not the
post-repair atmospheric rate.

## WP0 gate disposition

- protected hashes: PASS;
- O8 authority hashes: PASS;
- M04 EN/ZH structure mapping: PASS;
- project-generated headline-number source coverage: PASS at 100%;
- scientific readiness of present headline bundle: FAIL/CONDITIONAL because of
  B02--B08 and B16;
- permission to modify or compile M04: NOT GRANTED;
- permission to run a full or other-particle simulation chain: NOT GRANTED;
- next minimum actions: offline M audit and corrected native-PARMA
  atmospheric-511 mono-module construction, in new dated directories.

WP0 therefore completes the review requirement without treating the current
paper numbers as final and without expanding the user's modular execution
scope.

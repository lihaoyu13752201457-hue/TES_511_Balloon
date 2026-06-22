# Manuscript Review and Refinement Log

Date: 2026-06-17.

Scope: reviewer-style refinement of the current English and Chinese LaTeX
drafts in `core_md/balloon511_nima_latex_drafts/`, using the current manuscript,
the local Claude R4 review, and public instrument papers/pages as evidence.

## Public Anchors Checked

- COSI 511 keV balloon result: 46 d balloon flight, background-separated
  511 keV detection, broad emission relative to a point source.
- INTEGRAL/SPI 511 keV spectroscopy: morphology and spectral decomposition are
  model- and background-dependent, so focused point-source sensitivity must not
  be presented as a diffuse-sky replacement.
- 511-CAM JATIS paper: the focused-optics plus TES argument is a credible
  published framing; the reference entry was updated from arXiv-only text to the
  journal citation and DOI.
- NASA/HEASARC COSI pages: COSI is listed as a 2027 NASA SMEX soft gamma-ray
  mission; HEASARC lists the Ge detector range as 0.2--5 MeV and 6.0 keV
  energy resolution at 511 keV.
- NIM-A Guide for Authors: the journal scope includes detector systems,
  spectrometry, astrophysics instrumentation, simulation codes, and analysis
  tools, but explicitly cautions against submissions that use standard codes in
  a black-box way without adequate validation.

## Reviewer Questions and Actions

### Q1. Does the manuscript read like an instrument paper or like an internal report?

Finding: The workflow figure and table still exposed internal step numbers
(`Step00--Step08`) as if they were physical method names. This was traceable but
not appropriate as the main manuscript language.

Action: Replaced the workflow figure labels and simulation-workflow table with
method-layer names: geometry model, prompt/activation transport, delayed
activity source, Laue optics, optics-detector coupling, detector response,
mission-time fold, source normalization, counting significance, and robustness
checks. The surrounding text now describes inputs, operations, outputs, and
claim boundaries without internal audit numbering.

### Q2. Is the Compton/FoV `reject-kept` policy described with the correct sign?

Finding: Claude R4 correctly noted that retaining reconstruction-reject
multi-hit events is not a conservative lower bound on the final sensitivity.
Using the current M=50000 W2 class counts, discarding all `reject-kept` events
would retain 59.2% of the focused signal and 66.8% of the selected background,
lowering simple `S/sqrt(B)` to 0.724 of the baseline value.

Action: Added this diagnostic to both drafts. The text now states that the
baseline keep policy is a reconstruction-model boundary requiring validation,
not a sensitivity gain from aggressive rejection and not a conservative
lower-bound result.

### Q3. Is the atmospheric-transmission assumption clear enough?

Finding: The primary signal normalization uses the reference atmospheric
transmission. R4 correctly flagged that low-elevation pointings, including
Galactic-center pointings from northern mid-latitude balloon trajectories, may
need slant-column transmission rather than the reference case.

Action: Added a signal-normalization statement in both drafts. The primary
response is now described as the baseline pointing normalization; the 45 degree
line-of-sight rows in the results table are explicitly identified as the
current slant-column boundary calculation.

### Q4. Are secondary analyses and material controls separated from the primary result?

Finding: The paper already kept spatial rows, 45 degree LOS rows, and BGO
material control out of the primary hard-window headline. This matches the
published-instrument style: boundary tests are useful, but they should not
become headline sensitivity until their nuisance/background treatment is mature.

Action: Kept the primary hard-window exact-position chain as the headline and
tightened limitation wording. The BGO comparison remains explicitly tied to
material-specific thresholds (CsI 50 keV, BGO 70 keV) and is not presented as a
same-threshold veto scan.

### Q5. Are the abstract and discussion over-claiming?

Finding: Several phrases had generic manuscript language (`results indicate`,
`main contribution`, `promising`, `limitations do not invalidate`). These do not
change the physics, but they weaken a technical manuscript.

Action: Rewrote those phrases into specific claims: the output is a closed rate
calculation, focused TES spectroscopy is a balloon-platform approach to
narrow-line point-source searches, spatial analyses are diagnostics, and the
limitations define the next engineering/reconstruction work.

### Q6. Does the rendered manuscript still expose draft-only metadata?

Finding: The English and Chinese PDFs still contained visible draft scaffolding:
title notes describing the file as a first draft, CRediT and acknowledgment
placeholders, and a data-availability sentence about internal path names. Those
sentences are useful in a project note but weaken the paper as a manuscript.
The radial-profile cross-check was also called "conservative" without defining
the reference class.

Action: Removed the visible draft title notes, CRediT placeholder paragraphs,
acknowledgment placeholders, and internal-path warning from the manuscript
body. The author and affiliation fields now use review-anonymized placeholders
rather than incomplete-author wording. The radial-profile row is described as a
comparison cross-check, and the primary hard-window result is described as less
model-dependent than the spatial analyses rather than generically
conservative.

### Q7. Does Claude R4 still identify active authority inconsistencies?

Finding: Most R4 manuscript-facing physics issues had already been absorbed:
the BGO comparison is now labeled as a material-design-threshold control rather
than a same-threshold scan, the convergence claim is limited to total W2
background and Z20d rather than the delayed subcomponent alone, the keep-policy
sign is described correctly, and the atmospheric-transmission normalization is
identified as a baseline pointing case. Two metadata issues were still active.
The exact-position convergence report used `w2_signal_cps_at_1e_4` for a
unit-area proxy value, and the f10m optical authority still described f9m as
the published headline.

Action: Updated `code/tools/build_v3p5_exactpos_convergence_report.py` so
`w2_signal_cps_at_1e_4` is the physical reference-flux signal rate, with the
unit-EventList pass rate and unit-area proxy written under separate names. The
convergence report and M-sampling audit were regenerated. Also updated
`stepwise_maintenance/step04_opticsim/optics_aeff_authority_f10m_a1.json` and
its installer template so f10m is described as the current paper-facing optical
authority after downstream detector-coupling, source-normalization, and
significance reruns.

### Q8. Is the bibliography support stronger than in the initial pass?

Finding: The main public anchors now have verified publication metadata and
DOIs where appropriate. The 511-CAM reference was corrected to the journal
author order, NASA/HEASARC access dates were refreshed, and the remaining weak
entries flagged in this pass--XOP, Gehrels, and AMEGO--were resolved against
publisher/Crossref/PoS/INSPIRE metadata rather than guessed records.

Action: Added `reference_verification_20260617.md` to record the checked
references, actions applied, and remaining citation checks before submission.

### Q9. Does the discussion overstate the upstream Laue-lens self-background closure?

Finding: The optics-background paragraph could be read as saying that the
upstream Laue-lens hardware background budget is already final. The current
evidence is narrower: an equal-mass active-Ge proxy has been transported for
prompt and activation-production boundary closure, and the isolated delayed
Ge-proxy component produces zero selected W2 events in the present detector
transport. The prompt optics self-background is not yet folded into the primary
background budget because provenance isolation or subtraction is still required,
and explicit lens support hardware is not yet modeled.

Action: Reworded the discussion in both drafts so the upstream optics branch is
described as a boundary calculation for an equal-mass active-Ge proxy, not as a
finalized optics-background budget. The main limitations now separate this
boundary result from the primary detector-background budget.

### Q10. Does the abstract still read like an internal project summary?

Finding: The abstract exposed implementation details too early, including the
`exact-position` branch name and the 50,000 support-element source construction.
Those details are important in Methods and convergence sections, but in the
abstract they made the manuscript read more like a project report than an
instrument paper.

Action: Rewrote the English and Chinese abstracts to use paper-facing language:
the source model is described as delayed activity emitted from sampled
production positions recorded during activation transport, secondary
spatial/line-of-sight rows are described as diagnostics, and the hard-window
calculation is named as the primary rate result. The main numerical result and
the downstream support-size/seed stability statement were preserved.

### Q11. Does the introduction funnel like an instrument paper rather than a broad 511 keV review?

Finding: The introduction had a defensible literature base, but some phrasing
still read like a broad source-origin review or a mission-proposal claim. In
particular, the detailed source-class paragraph and strong language around
pointed follow-up risked distracting from the instrument-paper story arc used
by mature COSI/SPI/511-CAM papers: current observations and background limits,
the focused-TES niche, and the detector-coupled rate calculation presented here.

Action: Tightened the English and Chinese introduction. The source discussion
was compressed to the observables that motivate the instrument; "cleanest" and
"feasibility" style language was replaced by more testable wording; V404 Cygni
is retained only as an example motivating targeted compact-object follow-up;
and the discussion/conclusion now state that the simulated chain supports
continued evaluation rather than claiming final flight feasibility.

### Q12. Do the Results sections stay factual and matched to Methods?

Finding: A second pass against Claude R4 showed that several Results paragraphs
still had interpretation-like wording. The primary-sensitivity paragraph
described the hard-window row as less model-dependent and the spatial rows as a
possible gain, although those rows are better treated as different boundary
calculations. The background-composition paragraph drew optimization
implications directly in Results. The BGO table also used "matched comparison"
while the same caption correctly stated that it is not a same-threshold veto
scan.

Action: Rewrote the primary-sensitivity boundary paragraph as factual row
definitions; removed the background-composition interpretation from Results
because the same point is already handled in Discussion; and renamed the BGO
comparison as a material-control comparison using material-specific active-veto
thresholds.

### Q13. Does the BGO control imply the same authority level as the CsI headline?

Finding: The BGO material-control subsection correctly stated that it uses
material-specific active-veto thresholds and no BGO spatial likelihood, but it
could still be read as equal in authority to the CsI headline because it is
compared against the current CsI M=50000 chain. The local BGO chain uses its
transported 5000-support delayed source and has not been promoted by a
BGO-specific M/seed convergence sweep.

Action: Tightened the English and Chinese BGO Results and Discussion wording.
The BGO row is now explicitly a material-control row using the corresponding
hard-window chain and the transported 5000-support BGO delayed source, not a
replacement sensitivity authority. The BGO comparison generator and tracked
report wording were also changed from "matched" to corresponding
material-control language.

### Q14. Do the benchmark and conclusion paragraphs still sound like a proposal?

Finding: The instrument-benchmark subsection is still inside Results, so its
language should define comparison scope rather than argue that the payload is
"most competitive" for selected targets. The Discussion and Conclusion also
used "highest-leverage" and "most important" phrasing that reads more like a
proposal priority claim than a manuscript result unless backed by an explicit
optimization study.

Action: Rewrote the English and Chinese benchmark paragraph to state the
relevant comparison class--compact targets, central-core searches, and
position-constrained transient follow-up--without claiming competitiveness.
The follow-up list is now framed as validation work, and the conclusion says
the calculation provides a detector-coupled basis for continued evaluation
rather than making a broad performance claim.

### Q15. Do rendered symbols and event-class names expose internal labels?

Finding: The manuscript still rendered the analysis line-window shorthand as
`W2`, which was convenient in the project but reads like an unexplained
internal cut label. The event-selection section also displayed the
`reject-kept` class name in monospace, making a reconstruction policy look like
code documentation.

Action: Changed the rendered line-window symbol to \(W_{511}\) while preserving
the same numerical window, \(510.58\)--\(511.42\) keV. Replaced `reject-kept`
with retained reconstruction-reject terminology in both English and Chinese
drafts. These edits do not change any rate, selection, or sensitivity value.

### Q16. Do engineering workflow terms still make the manuscript read like a project report?

Finding: A terminology scan of the main drafts and included table resources
still found several project-facing expressions in rendered manuscript text:
`rate authority`, `branch`, `M/seed`, `support-size`, and MEGAlib-style
`source cards`. These are useful in audit documents but are not the usual
language of a NIM A instrument paper.

Action: Replaced those terms with paper-facing descriptions without changing
the underlying calculations: `rate definition`, `calculation` or
`configuration`, `support-count and seed`, `support-count`, and `source
definition` or `transport input`. The BGO and upstream-optics sections now
refer to controls/calculations rather than branches, and the table resources
use the same terminology as the main text.

### Q17. Are the most visible overfull lines caused by manuscript wording rather than unavoidable tables?

Finding: The current TeX logs still had several visible overfull lines in the
abstract, science-requirements paragraph, detector-model description, and
exact-position sampling discussion. The worst cases were caused by long
technical phrases such as `transport/activation`, dense inline isotope/activity
lists, and an unbreakable `INTEGRAL/SPI` token in the Chinese draft.

Action: Applied a layout pass without changing numerical content: shortened
the abstract wording, rewrote the compact-source science-case sentence, changed
`transport/activation material` to a breakable phrase, split the convergence
paragraph, rewrote the activity list in the exact-position sampling test, added
a break point to `INTEGRAL/SPI` in the Chinese text, and set a modest
`\emergencystretch` in both drafts. This is a typesetting/readability pass, not
a physics or rate-authority change. The post-pass compile leaves only a
0.9-pt overfull box in the requirements table in each draft; the previous
double-digit overfull body-text cases are removed.

### Q18. Do the abstract and conclusion quote more precision than a paper reader can use?

Finding: The Results tables and equations need enough digits to remain
traceable to the current rate authority, but the abstract and conclusion should
not read like JSON summaries. The previous abstract and conclusion repeated
five to seven significant digits for \(A_{\mathrm{eff}}\), \(B\), \(S\),
\(Z\), detection time, and flux thresholds. That precision is useful for
auditability in tables, but it weakens the manuscript-facing hierarchy: readers
should first see the scale and claim, then find exact values in the Results
tables.

Action: Rounded the narrative headline values in the English and Chinese
abstracts and conclusions while leaving the Results tables and equations at the
current authority precision. The abstract/conclusion now use, for example,
\(A_{\mathrm{eff}}=20.08\,\mathrm{cm^2}\), \(B=6.30\times10^{-2}\,\mathrm{s^{-1}}\),
\(S=1.18\times10^{-3}\,\mathrm{s^{-1}}\), \(Z_{20\mathrm{d}}=6.13\),
\(T_{3\sigma}=4.78\) d, and \(F_{3\sigma}(20\,\mathrm{d})=4.89\times10^{-5}\).
The convergence sentence is similarly rounded to 1.12\% and 0.55\%. This is a
writing and effective-precision pass only; no source rate, table entry, or
simulation authority file was changed.

### Q19. Is the COSI benchmark wording aligned with current public mission pages?

Finding: The benchmark paragraph correctly treats COSI as the wide-field
comparison class, but the previous sentence compressed two public-page facts in
a way that could be read as saying both NASA and HEASARC independently list the
same launch and energy-resolution details. The current NASA Science COSI page
lists COSI as a future mission with launch in 2027 and describes the 0.2--5 MeV
mission band. The HEASARC COSI page lists the Ge detector 0.2--5 MeV energy
range and the 6.0 keV energy resolution at 511 keV.

Action: Rewrote the English and Chinese benchmark sentence to separate the
source of each public fact: NASA for the future-mission/2027 launch statement,
and HEASARC for the Ge detector energy-resolution value. The surrounding
comparison remains intentionally conservative: COSI and SPI are the diffuse-sky
mapping references, while the TES Laue-lens calculation is presented only as a
pointed narrow-line compact-source estimate.

### Q20. Does any formal journal reference still lack DOI metadata?

Finding: A bibliography scan showed that most entries without DOI metadata are
intentionally preprint-only or official web-page references. One exception was
`Kierans2020`, the formal Astrophysical Journal paper reporting the COSI 511 keV
detection. It was listed with journal, volume, and page, but without its DOI,
leaving a visible metadata gap in one of the key comparison references.

Action: Queried Crossref by title and verified the ApJ record for
`Kierans2020`: DOI `10.3847/1538-4357/ab89a9`, volume 895, page/article 44.
Added the DOI to both English and Chinese bibliographies and updated
`reference_verification_20260617.md`. The remaining DOI-less entries are either
explicit arXiv preprints or official mission web pages.

### Q21. Is the data/software availability statement specific enough for a simulation paper?

Finding: The previous statement said only that simulation cards, validation
summaries, and scripts would be made available before publication. That is
editorially acceptable as a placeholder, but it does not tell a reviewer what
will actually be sufficient to reproduce the manuscript tables and figures, nor
does it distinguish lightweight provenance products from very large raw
transport files.

Action: Rewrote the English and Chinese availability statements to define the
archival unit: geometry and source inputs, analysis and figure-generation
scripts, LaTeX source, and lightweight JSON/CSV/Markdown validation products.
The text now states that full raw transport outputs, compressed Cosima event
files, and large intermediate event lists are too large for the lightweight
manuscript archive and will either be deposited as a separate large-data package
or represented by exact generation commands, configuration files, and derived
validation summaries. This improves reproducibility wording without changing
any simulation result.

### Q22. Did the Chinese draft still expose internal method labels or English placeholders?

Finding: A Claude-R4-driven terminology scan showed that the English manuscript
can retain defined method labels such as exact-position and radial-profile, but
the Chinese draft still mixed those labels with manuscript prose. It also
retained several English placeholders or project-style terms, including
`claim`, `publication-grade`, `likelihood`, `profile`, `nuisance`, `raw`,
`LOS`, `tagged`, `cuts`, `self-background`, `pile-up`, `EventList`, and
`provenance`. These did not change the physics, but they made the Chinese draft
read like an internal validation report rather than a paper-facing technical
manuscript.

Action: Rewrote the affected Chinese prose, captions, and tables to use
paper-facing terminology: 精确位置, 径向分布, 可信率级结论, 剖面似然,
本底扰动参数, 未筛选, 视线方向, 正电子标记, 拓扑筛选, 自本底, 堆积,
事例列表, and 来源追踪. The pass also changed table labels such as `Base` and
`Seed` to Chinese labels. A post-edit scan of the Chinese manuscript and Chinese
resource tables no longer finds the internal/project terms targeted by this
review. No numerical result or simulation authority file was changed.

### Q23. Does the manuscript answer NIM-A's black-box simulation concern?

Finding: The NIM-A author guide explicitly accepts instrumentation simulations
and analysis tools within scope, but warns that submissions based only on
standard-code simulation of simple concepts, without adequate validation, may
fall below the journal's originality and innovation threshold. The manuscript
already contains the required evidence layers--tracked optical focal crossings,
recorded activation-production positions, common detector-level selection,
mission-time folding, M/support-count convergence, BGO material control, and
upstream-optics boundary checks--but the Introduction did not state this
distinction early enough. A reviewer could therefore read the study as a
Geant4/MEGAlib black-box rate estimate before reaching the validation tables.

Action: Added a short anti-black-box framing sentence to the English and
Chinese introductions. The manuscript now states that the transport code is not
treated as evidence by itself; the rate result is tied to explicit geometry and
source normalizations, tracked focal-plane crossings, recorded activation
positions, common detector-level selections, and downstream convergence or
boundary checks. The opening study statement was also changed from a generic
"simulation and sensitivity study" to an evaluation at the selected-rate level.
No numerical result or simulation product was changed.

### Q24. Does the Introduction follow the story arc used by mature 511 keV instrument papers?

Finding: Mature 511 keV instrument papers such as the COSI balloon detection
paper move quickly from the unresolved positron source problem to the specific
instrumental observable and background-separation method. The current draft had
the same ingredients, but one sentence ("the source problem is not only a
source-inventory problem") read like internal explanatory prose, and the paper
organization sentence still used the generic "future work" label. The risk was
not scientific error; it was that the Introduction could feel less controlled
than the Methods and Results sections.

External writing anchors: COSI frames the 511 keV problem as an unresolved
source/morphology question and then immediately states the balloon instrument,
flight data, background separation method, and detection result
(`https://arxiv.org/abs/1912.00110`). The NIM-A guide also emphasizes that
simulation papers must show validation and originality rather than rely on
standard-code output alone
(`https://www.sciencedirect.com/journal/nuclear-instruments-and-methods-in-physics-research-section-a-accelerators-spectrometers-detectors-and-associated-equipment/publish/guide-for-authors`).

Action: Tightened the English and Chinese Introduction. The source paragraph now
states that the unresolved source population cannot be inferred from source
inventories alone, because the observed morphology also depends on positron
propagation before annihilation. The section roadmap now says that the
Discussion treats interpretation, limitations, and remaining validation steps,
rather than using the broader "future work" label. No citation or numerical
result was changed.

### Q25. Does the Discussion separate the current rate result from a future flight-performance statement?

Finding: The Discussion already contained the right caveats, but several
sentences sounded like a generic limitation/future-work block. A reviewer could
still accept the science, but the writing did not fully match the precision of
the rate calculation. The strongest version is to state what the rate-level
result proves now, what approximation exact-position sampling removes, and what
must be validated before a flight-performance statement.

Action: Rewrote the relevant English and Chinese Discussion paragraphs. The
exact-position paragraph now says it addresses a specific approximation in
radial-profile compression. The background paragraph now identifies the first
engineering targets rather than vaguely saying improvements "may come" from
several places. The limitation paragraph now introduces four immediate
boundaries of the selected-rate result. The final validation paragraph now says
that Revan cross-checks, full-statistics optics self-background with explicit
support hardware, final cryostat geometry, TES saturation/pile-up evidence, and
spatial-spectral nuisance profiling are needed before using this rate study as a
flight-performance statement. No simulation product or headline sensitivity changed.

### Q26. Do Methods and Results stay separated for the upstream optics boundary?

Finding: A reread of Claude R4 showed that the upstream Ge-proxy calculation was
scientifically bounded, but the manuscript still placed the selected-rate result
inside the Laue-optics Methods section. That mixed a method construction
(equal-mass Ge proxy, source surface, full-particle transport, recorded-position
decay source) with a result (two isotope records, zero selected line-window
events, and the 95% upper rate).

Action: Moved the numerical upstream Ge-proxy delayed result into a dedicated
Results subsection in both English and Chinese drafts. The Methods section now
defines only the upstream mass-proxy transport boundary and points forward to
the Results subsection. The Discussion now refers back to that subsection when
stating that this is a boundary calculation, not a finalized optics-hardware
background budget. No simulation product or headline sensitivity changed.

### Q27. Does the instrument benchmark comparison belong in Results?

Finding: A Results subsection compared the focused TES concept with SPI and
COSI. The content was scientifically useful, but it did not report a new
simulation output from this study. It interpreted the comparison class: pointed
narrow-line compact-source sensitivity versus diffuse-sky mapping. In a
standard IMRAD structure, that belongs in Discussion rather than Results.

Action: Moved the benchmark-comparison paragraph from Results into the opening
Discussion flow in both English and Chinese drafts. The wording now frames the
comparison as interpretation of the primary rate result, while Results ends
after the actual simulation outputs: primary sensitivity, background
composition, convergence, BGO material control, and upstream optics mass-proxy
boundary. No citation, numerical result, or sensitivity value changed.

### Q28. Do the Abstract and Conclusion overstate the rate study?

Finding: The Abstract ended by saying that the results "support focused TES
spectroscopy" as a balloon-platform search approach, and the Conclusion called
the study a "first full-chain" calculation. Those phrases were stronger than
the manuscript's own Discussion boundaries, because optics prompt
self-background, explicit lens-support hardware, full Revan/Mimrec
reconstruction, final cryostat geometry, and TES saturation/pile-up validation
remain open.

Action: Softened the English and Chinese Abstract and Conclusion to state that
the manuscript provides a detector-coupled selected-rate basis for evaluating
focused TES spectroscopy. The word "first" was removed from the Conclusion, and
"predicts" was replaced with rate-calculation wording. No numerical result,
table value, citation, or simulation product changed.

### Q29. Are all tables and figures explicitly introduced in the text?

Finding: A structural IMRAD pass found that several manuscript-facing figures
and tables were present as floats but not explicitly introduced by the prose:
the detector-parameter table, the background-source-layer table, the
selection/time-fold diagnostic figure, the Compton/FoV geometry figure, and the
background-composition table. This does not affect the calculation, but it makes
the paper read more like a compiled project artifact than a guided instrument
manuscript.

Action: Added short text references in both English and Chinese drafts before
or near the corresponding floats. The detector-model opening now points to both
the mass-model figure and the detector-parameter table; the delayed-source
section introduces the background-source-layer table before event selections
are applied; the selection section points to the selection/time-fold and
Compton/FoV geometry figures; and the background-composition paragraph points
to its table. No numerical value, figure file, table entry, or simulation
product changed.

### Q30. Does the prose still contain generic AI-like emphasis?

Finding: A humanization pass using the academic writing checklist found no
high-risk English phrases such as "pivotal", "landscape", "underscores",
"serves as", "studies have shown", or generic positive conclusion language.
The Chinese draft still used several broad evaluative words in the Introduction
and requirements framing, including "重要", "关键", "核心", "不可替代", and
"极其困难". Most occurrences were technical, but a few read more like
significance inflation than manuscript evidence.

Action: Rewrote the affected English and Chinese introduction/requirements
sentences into factual wording. Examples include changing COSI from an
"important independent measurement" to an "independent balloon measurement",
changing the background paragraph from a "central/core technical challenge" to
a "main technical limit", replacing "不可替代" with "主要工具" for wide-field
Compton telescopes, and removing "关键点" from the workflow caption. No
calculation, citation, table value, figure, or simulation artifact changed.

Open submission item: Elsevier/NIM-A requires a declaration if generative AI or
AI-assisted tools were used in manuscript preparation. The current manuscript
still lacks final author-team declarations for AI use, CRediT, acknowledgments,
funding, and competing interests. These should be added only with author-team
approved wording before submission.

### Q31. Does Claude R4 still expose an active physics or wording problem?

Finding: A fresh pass against `CLAUDE_REVIEW_TES511_BALLOON_20260616_R4.md`
confirmed that its science warnings remain the right boundaries to carry in the
paper, but not active numerical contradictions. The current authority files use
the M=50000 CsI exact-position chain, not Claude R4's older M=5000 comparison
baseline. Exact-position convergence is closed at the total line-window
background and significance level (`0.0111914918` relative range in background
and `0.00550844085` in `Z20d`), while the delayed subcomponent alone still has
`0.187412720` relative range and should not be described as independently
plateaued. The BGO comparison remains a material-design-threshold control with
CsI/BGO veto thresholds of `50/70 keV`, not a same-threshold veto scan. The
signal-rate metadata issue is fixed: the convergence authority now stores the
physical `w2_signal_cps_at_1e_4 = 0.0011811656293957314` and separates the old
unit-area proxy.

Action: No new manuscript-number change was required. I tightened residual
BGO documentation and generator wording outside the paper so "matched
comparison" is no longer regenerated for the BGO-vs-CsI material-control
branch. The updated check is recorded in
`paper_resource/claude_r4_recheck_20260617.md`.

### Q32. Does the BGO active-shield control overstate engineering readiness?

Finding: The BGO subsection already stated that it is not a same-threshold scan
and not a replacement for the CsI rate authority, but it did not yet name a
specific active-shield response limitation. Public COSI anticoincidence-system
work shows that quantitative BGO shield response can depend on scintillation
light transport, position-dependent light collection, electronics response, and
threshold non-uniformity, with optical-physics simulations or response matrices
benchmarked against laboratory measurements used to model those effects.
Our BGO branch currently treats deposited energy and a material-specific veto
threshold; it does not include optical light collection or SiPM/electronics
response.

Action: Added a Discussion boundary sentence in both English and Chinese drafts
and cited `Ciabattoni2025ACS`. The BGO result is now explicitly framed as a
material and deposited-energy threshold control, not as a complete BGO
anticoincidence-system performance model. This change does not modify any BGO,
CsI, or sensitivity number.

### Q33. Does the Discussion turn background composition into an optimization claim?

Finding: The Discussion still said that the background composition "identifies
the first engineering targets" and that detector iterations "should" test a
specific list. That is a reasonable design inference, but the manuscript has
not yet performed an optimization scan over those detector changes. The same
section also listed remaining validation as one long sentence, which weakened
the distinction between a closed selected-rate calculation and a future
flight-performance statement.

Action: Rewrote the English and Chinese Discussion to frame the prompt
atmospheric component as the first engineering sensitivity to test, not as a
completed optimization result. The validation paragraph now groups the
remaining work into four blocks: Revan/Mimrec reconstruction cross-check,
full-statistics optics self-background with explicit lens hardware, final
cryostat/detector-response update including TES saturation and pile-up, and a
spatial-spectral nuisance-profile likelihood. The conclusion now attributes
the delayed-source stability statement to the transported M-sampling and
alternate-seed checks. No numerical result changed.

### Q34. Do source-construction captions expose audit-log granularity?

Finding: The exact-position source section still carried implementation-audit
granularity in the manuscript text: the number of parsed activation files, raw
production-position records, eligible weighted rows, and stored delayed events.
Those numbers are useful in reproducibility reports, but the main paper should
emphasize the physical source definition: matched production positions,
activity weights, total day-15 activity, sampled point-source size \(M\), and
the transported delayed-decay sample. Similar wording appeared in the BGO
control and workflow tables through phrases such as "particle-list source" and
"stored events".

Action: Removed file/record/row counts from the main source-construction prose
and figure caption while preserving the physical activity
\(85.636696\,\mathrm{Bq}\), the transported sampling size \(M=50000\), the
smaller convergence cases, and the \(10^6\) delayed-decay transport scale.
Reworded "stored events", "delayed triggers", "particle-list source", and
"focal particles" as transported delayed decays, detector transport source,
and tracked focal-plane photons. No rate, activity, convergence, or
sensitivity number changed.

### Q35. Are figures and tables first cited in a manuscript-reading order?

Finding: A float-order check found that all tables and figures are cited, but
the optics Methods section cited the primary sensitivity table before several
source-model and event-selection figures had been introduced. The cited
content was only a forward pointer to the 45 degree line-of-sight boundary row,
not a method needed at that point. This kind of forward table citation can make
the manuscript read like a project report assembled from validation artifacts,
rather than like a paper whose figures and tables appear in the reader's
logical order.

Action: Removed the explicit table reference from the Methods paragraph and
replaced it with a text pointer saying that the 45 degree line-of-sight boundary
calculation is reported with the primary sensitivity results. Also changed the
remaining English "focal-plane particles" phrase to "focal-plane photons" in
the optics-coupling paragraph. No table entry, rate, sensitivity value, or
figure changed.

### Q36. Do the abstract and conclusion mix day-15 rates with mission-folded sensitivity?

Finding: The Results section correctly separates day-15 selected rates
($B_{\wii}=0.0629804\,\mathrm{s^{-1}}$,
$S_{\wii}=0.00118117\,\mathrm{s^{-1}}$ at \(F_0\)) from mission-mean selected
rates and cumulative significance. The abstract and conclusion quoted the
rounded day-15 rates and then immediately reported mission-folded sensitivity.
The numbers were correct, but the prose did not explicitly name the first pair
as day-15 selected rates, leaving a small reader risk that they might be read as
mission-mean rates.

Action: Clarified the English and Chinese abstract and conclusion so the
rounded \(B/S\) pair is explicitly described as day-15 selected rates, while
\(Z_{20\mathrm{d}}\), \(T_{3\sigma}\), and \(\fthree\) are described as outputs
of the mission-time fold. No numerical result changed.

### Q37. Does the title rely on an undefined detector abbreviation?

Finding: The English and Chinese titles used the abbreviation "TES" before the
abstract defined it. The abbreviation is familiar inside the microcalorimeter
community, but the title should remain self-contained for a broader NIM A
instrumentation readership. The cited 511-CAM paper also spells out
transition-edge-sensor technology in its title, so expanding the detector name
is consistent with established public-paper style.

Action: Expanded the English title to "transition-edge sensor" and the Chinese
title to "过渡边缘传感器". The abstract still defines the abbreviation on first
use, and no rate, figure, citation, or section structure changed.

### Q38. Does the Discussion use generic evaluative language where a precise role is available?

Finding: A humanizer-style scan found no major promotional language, but the
Discussion still used two generic phrases: INTEGRAL/SPI and COSI as "key
references" and spatial analyses as "useful diagnostics". The intended meaning
was more specific: the former are the reference measurements for diffuse-sky
mapping, while the latter are cross-checks that do not yet constitute a
nuisance-profile likelihood.

Action: Replaced those phrases in the English Discussion with "reference
measurements" and "diagnostic cross-checks"; the Chinese comparison sentence
was adjusted in parallel. No claim, citation, or numerical result changed.

### Q39. Does the Chinese draft still expose English-first terminology where a paper-facing Chinese term is available?

Finding: After the title expansion in Q37, the Chinese abstract still introduced
the detector as `transition-edge sensor（TES）` and the keyword list still used
`TES 微量热计` without a Chinese detector term. The Chinese prose also retained
many visible `day-15` occurrences. These are not project-internal labels in the
same sense as code branch names, but in the Chinese manuscript they made the
paper read closer to an audit note than to a polished technical article.

Action: Changed the first Chinese abstract use to
过渡边缘传感器（transition-edge sensor, TES）微量热计, changed the keyword to
过渡边缘传感器微量热计, and replaced visible Chinese-manuscript `day-15`
phrasing with 第 15 天 in the abstract, source-model prose, captions, tables,
mission-folding text, upstream-optics boundary result, and conclusion. No
English draft wording, simulation product, rate, activity, or sensitivity value
changed.

### Q40. Does the English draft still contain project-audit wording where a paper-facing term is clearer?

Finding: A follow-up terminology scan found no new numerical inconsistency, but
several English phrases still had an audit-log tone: `topology cuts`, `raw`
detector rates, `positron-tagged` prompt streams, `provenance isolation`, and a
requirements-table phrase describing a `matched Ge volume`. These phrases were
not wrong, but more direct physical language is available.

Action: Replaced them with topology selections, pre-veto rates, atmospheric
\(e^+\) stream or events, source separation, figure source tracing, and
equal-volume Ge proxy wording. The requirements table was updated in the same
pass. No selection definition, source model, rate, figure, table value, or
sensitivity changed.

### Q41. Is the Gaussian counting significance justified in the selected-rate regime?

Finding: The Methods section defined \(Z=N_s/\sqrt{N_b}\) but did not state why
the Gaussian counting approximation is adequate for the primary result. The
current Step08 time-dependent authority gives 20-d selected counts of
approximately \(N_s=2025\) and \(N_b=109106\) for the primary hard-window
reference-flux case, so the main sensitivity row is a high-count
selected-rate calculation. The upstream Ge-proxy delayed boundary is a different
case because it has zero selected line-window events and is already treated
with a Poisson zero-count upper limit.

Action: Added one sentence pair to the English and Chinese significance
sections. The text now states the approximate 20-d count scale for the primary
hard-window result and explicitly separates the Gaussian selected-rate
significance from the Poisson upper limit used for the isolated upstream
zero-count result. No rate, count source, table value, or sensitivity changed.

### Q42. Could the hard-window sensitivity be misread as applying to intrinsically broad source lines?

Finding: Claude R4 correctly pushed the manuscript toward sharper boundary
language. The primary sensitivity uses a fixed \(510.58\)--\(511.42\) keV
analysis window, so it is a narrow-line selected-rate result. The draft already
called the target a narrow-line point-source search, but the event-selection
section did not explicitly say what happens if the astrophysical source line is
intrinsically broader than the window after detector response.

Action: Added one boundary sentence to the English and Chinese selection
sections. The manuscript now states that the quoted flux thresholds apply when
the source line remains narrow compared with the analysis window after detector
response, and that broader source lines require convolving the source line
profile with the detector response and re-optimizing or widening the analysis
window. No source model, background model, rate, or sensitivity number changed.

### Q43. Are figure references introduced before the relevant figure material in the manuscript flow?

Finding: A figure-reference audit found that all 17 figure/table float labels
were referenced, but five figure environments in each language were placed
before the first prose sentence that explicitly referenced them. This is not a
LaTeX closure error, but it weakens the paper-reading flow and can make top
floats appear before they are motivated.

Action: Moved the introductory prose references for the optics schematic and
spot figure, the EXPACS full-sphere flux figure, the delayed exact-position
distribution figure, and the exact-position sampling necessity figure so the
text now introduces the figures before the corresponding figure environments.
No figure file, caption, label, numerical value, source model, or sensitivity
result changed.

### Q44. Do the flux thresholds read like a complete systematic-uncertainty budget?

Finding: The Discussion listed several model boundaries, but a reviewer could
still read the tabulated \(3\sigma\) flux thresholds as a complete
flight-performance uncertainty budget. The current evidence supports statistical
selected-rate thresholds for a defined baseline source, mass, and response
model; it does not yet provide a systematic envelope for atmospheric flux,
activation modeling, geometry/material tolerances, detector response, veto
threshold calibration, or reconstruction efficiency.

Action: Added one boundary paragraph to the English and Chinese Discussion
sections. The manuscript now states explicitly that the tabulated thresholds are
statistical selected-rate thresholds for the baseline model and do not include a
systematic-uncertainty envelope over those effects. No numerical result,
selection definition, source model, or comparison table changed.

### Q45. Does the COSI comparison depend on an avoidable mission-schedule fact?

Finding: The Discussion used the NASA mission page's 2027 launch listing while
contrasting the present TES Laue-lens concept with COSI. The official NASA page
still lists COSI as a future mission with launch in 2027, and the HEASARC page
still lists a 0.2--5 MeV Ge detector payload and 6.0 keV energy resolution at
511 keV. The launch schedule is a current mission-status fact, however, and is
not needed for the instrument-response comparison.

Action: Rephrased the English and Chinese Discussion comparison to cite the
NASA and HEASARC mission pages for COSI's wide-field 0.2--5 MeV Ge Compton
telescope description and HEASARC's 6.0 keV at 511 keV resolution entry,
without foregrounding the launch date. No bibliography entry, comparison class,
rate, or sensitivity value changed.

## Remaining Open Items

- The rendered manuscript no longer exposes CRediT/acknowledgment placeholders,
  but the final author list, affiliations, CRediT statement, acknowledgments,
  competing-interest statement, and archive identifiers still need author-team
  input before submission.
- A first bibliography pass is materially complete for the current manuscript:
  the Claude R4 weak entries `SanchezDelRio2011XOP`, `Caputo2017`, and
  `Gehrels1985` now have verified publication metadata. Systematic retraction
  checks and author-team metadata remain before submission.
- The keep-policy diagnostic is rate-level and based on current line-window class
  counts. A Revan/Mimrec cross-check of the multi-hit subset remains the next
  reconstruction validation.
- The reference atmospheric-transmission case remains the headline. A
  trajectory/source-specific Galactic-center sensitivity should use a
  source-zenith-angle mission model rather than only the current 45 degree
  boundary row.
- The upstream optics mass-proxy branch now has manuscript language consistent
  with the available evidence, but prompt self-background provenance isolation
  and explicit lens support hardware remain validation items.
- The BGO active-shield material-control branch now names the missing
  scintillation/light-collection response model, but a quantitative BGO flight
  shield claim would still require an optical/electronics response model and
  threshold calibration.
- Claude R4's documentation-governance issues remain: dangling paths in active
  core documentation and uncommitted paper-facing artifacts should be cleaned or
  committed separately from the physics-text pass.

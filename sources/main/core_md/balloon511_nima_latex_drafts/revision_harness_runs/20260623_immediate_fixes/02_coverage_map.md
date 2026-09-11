# Coverage Map

Role: Orchestrator.

Source queue: `project_internal_fix_queue_zh.md` and `project_internal_fix_queue.md`.

## Immediate-Fixes Coverage

| Queue item | Judgment evidence | Harness PI | This-round treatment |
|---|---|---|---|
| PI-01 evidence provenance and stale quarantine | Chinese queue lines 44-60; English queue lines 47-76. | PI-01 | In scope. Build `paper_evidence_manifest_20260623.md/json` and `deprecated_manifest_20260623.md`; mark old `1.2534e-4 s^-1` stale. |
| PI-02 delayed selected-rate convergence | Chinese queue lines 65-82; English queue lines 83-114. | PI-02 | In scope. Must satisfy selected-rate convergence predicate or record `BLOCKED_WITH_EVIDENCE`. |
| PI-03 source normalization audit | Chinese queue lines 87-104; English queue lines 121-145. | PI-03 | In scope. Build units-complete `source_normalization_audit_20260623.md/json`. |
| PI-04 simulation configuration authority | Chinese queue lines 109-123; English queue lines 151-169. | PI-04 | In scope. Build `simulation_config_authority_20260623.json` and `simulation_config_table_20260623.md`; no guessed values. |
| PI-05 figure/data pipeline rebuild | Chinese queue lines 128-149; English queue lines 175-201. | PI-05 | In scope for provenance and QA audit. Full visual redraw only if safe and data-preserving; otherwise record remaining action. |

## Deferred Queue Items

| Queue item | Judgment evidence | Treatment |
|---|---|---|
| PI-06 selected delayed decomposition | Chinese queue lines 154-173; English queue lines 207-232. | Deferred. Valuable after PI-02 convergence; not part of immediate-fixes DONE predicate unless needed as PI-02 evidence. |
| PI-07 likelihood/nuisance sensitivity | Chinese queue lines 175-195; English queue lines 234-262. | Deferred. Current manuscript remains diagnostic; no manuscript text edits this round. |
| PI-08 trajectory/visibility/slant column | Chinese queue lines 197-215; English queue lines 264-290. | Deferred. Scope remains reference-exposure estimate. |
| PI-09 full payload/lens-support background | Chinese queue lines 217-236; English queue lines 292-319. | Deferred/out of scope unless claim expands. |
| PI-10 reconstruction validation | Chinese queue lines 238-257; English queue lines 321-345. | Deferred. |
| PI-11 detector-response envelope | Chinese queue lines 259-276; English queue lines 347-374. | Deferred. |
| PI-12 broad-line/centroid cases | Chinese queue lines 278-296; English queue lines 376-399. | Deferred. |
| PI-13 spectra and cut-flow diagnostics | Chinese queue lines 298-316; English queue lines 401-423. | Deferred except as PI-05 figure audit notes. |
| PI-14 CsI alternative shield trade | Chinese queue lines 318-332; English queue lines 425-441. | Out of scope; user did not reopen design optimization. |
| PI-15 diffuse sky/foreground | Chinese queue lines 334-348; English queue lines 443-460. | Out of scope for the instrumental-background estimate. |
| PI-16 full CAD/services model | Chinese queue lines 350-366; English queue lines 462-481. | Out of scope unless flight-design claim expands. |
| PI-17 analysis parameter scan | Chinese queue lines 368-385; English queue lines 483-504. | Deferred. |
| PI-18 activation history/nuclear data | Chinese queue lines 387-404; English queue lines 506-528. | Deferred unless needed as PI-02/PI-03 support evidence. |
| PI-19 reproducible archive packaging | Chinese queue lines 406-425; English queue lines 530-552. | Deferred. Important before submission, but not part of immediate-fixes v2.1 scope. |

## Review Concern Coverage

| Review concern | Harness coverage |
|---|---|
| C4/B4 source normalization | PI-03 |
| C6/B6 delayed statistics and selected-rate convergence | PI-02 |
| C9/B9 simulation configuration | PI-04 |
| C10 numerical provenance/stale debug language risk | PI-01 |
| Figure/table review and Bfig | PI-05 |

No immediate/do-now concern from the fix queue is unmapped.

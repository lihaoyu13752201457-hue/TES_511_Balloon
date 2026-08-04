# S3d O8 fallback geometry — side40 / bottom30 / top10 / no outer W2

Status: `S3D_O8_FALLBACK_GEOMETRY_VALIDATED_COSIMA_OVERLAP_PASS`

Matched-screening status: `PASS_O8_SCREENING_PROMOTION_GATES`

Full-chain status: `PASS_S3D_O8_STEP08_FULLCHAIN_TIME_DEPENDENT`

This package is the preregistered fallback from the retained S3c-C0 geometry.
It is a strict minimal delta: retain the original 40 mm side BGO volume and
scorer blocks byte-for-byte, thin bottom BGO to 30 mm,
thin the top annulus to 10 mm, remove only the three outer W2 shell volumes and
scorers, and preserve Al3, Kapton, and every other geometry/response definition.
The `42_` package is read as shared code/evidence authority; no geometry,
manifest, simulation, or other package output is written there.

## Why O8 is the data-driven fallback

The O9 matched screening gives `e+ + n = 0.002710741516565003 cps` and
atmospheric-511 `= 0.003499800705793143 cps`, for
`0.006210542222358145 cps`.  This exceeds the preregistered `0.0052 cps`
dominant-W2 limit, so O9 fails that transport gate.

Using the retained `IA INIT` parser and `classify_entry` implementation, the
O9 atmospheric final-W2 survivors classify as `17/18 side`, `1/18 bottom`, and
`0/18 top`; C0 classifies as `5/6 side`, `1/6 bottom`, and `0/6 top`.  The O9
atmospheric survivor count is exactly `3x` C0 (normalized-rate ratio
`2.999270875`).  The failure is therefore strongly side-dominated.  O8 restores
the side BGO to 40 mm while keeping bottom/top thinning as the remaining mass
lever.  Reproducible event-level evidence:
`engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/o8_fallback_decision_evidence.json`.

## Matched screening result

The completed, geometry- and seed-audited screen passes both preregistered
promotion gates:

- Final primary-window e+/n/atmospheric-511 subset:
  `0.004463791210 cps`, below the `0.0052 cps` limit. Its matched heavy-control
  value is `0.003883559310 cps`.
- Focused-signal acceptance: `29598/37194` versus `29703/37194` for the matched
  heavy control, a central relative loss of `0.353500%`, below the `2%` limit.

The subset components are one e+ event (`0.000678516735 cps`), three neutron
events (`0.002035605454 cps`), and nine atmospheric-line events
(`0.001749669021 cps`). Exact counting intervals are retained in the JSON and
are diagnostic; the frozen gates use the stated central values. The nine
atmospheric survivors enter through six side and three bottom trajectories in
the retained IA-INIT directional proxy. See `O8_SCREENING_ANALYSIS.md` and
`data/s3d_o8_screening_analysis.json`.

This PASS authorizes the full all-eight-family prompt and neutron activation /
delayed campaign. It does not itself substitute for that full-chain result.

## Full-chain result

The completed closure combines all eight prompt families, the exact-position
neutron-induced delayed source, the explicit atmospheric-511 sidecar, and the
matched focused signal. In the primary 510.58--511.42 keV window at day 15:

- prompt background: `0.003393031514 cps` (5 selected MC events);
- neutron-induced delayed background: `0.000963379097 cps`
  (31 selected MC events);
- atmospheric-511 sidecar: `0.001749669021 cps` (9 selected MC events);
- total background: `0.006106079633 cps` (45 low-stat selected background
  events);
- focused signal at `1e-4 ph cm^-2 s^-1`: `0.001181205538 cps`
  (`29598/37194` accepted).

The independently re-integrated 81-bin, 20-day fold gives central
`Z=19.25580431` and `F3=1.557971794e-5 ph cm^-2 s^-1`. Propagating a
Garwood 95% upper count for every independently normalized background
component and a Clopper--Pearson 95% lower focused-signal acceptance through
the same fold gives `Z=6.878336760` and
`F3=4.361519514e-5 ph cm^-2 s^-1`. The independent reconciliation is
`PASS_O8_FULLCHAIN_INDEPENDENT_VALIDATION` with no problems.

The delayed branch is neutron-induced only. Other incident-family delayed
activation was not transported in this campaign and is not substituted as
zero. The historical paper reference also predates the explicit
atmospheric-511 sidecar, so the central whole-design comparison is contextual;
only the matched screening comparison isolates the shield-mass delta.

## Authorized geometry delta

- Side BGO: original `BGO_S3C_FullWrap_SideShell_WindowCut_40mm` geo and
  detector blocks remain byte-identical (`r=21.2..25.2 cm`, 40 mm).
- Bottom BGO: `z=-23.4..-19.4 -> -22.4..-19.4 cm` (30 mm).
- Top BGO: `z=40.9..44.9 -> 40.9..41.9 cm` (10 mm).
- Remove exactly the three S3c outer W2 side/bottom/top volumes and scorers.
- Preserve byte-identical Al3 and Kapton blocks, aperture/service/relief scheme,
  TES/cryostat/BPE/plastic geometry, materials, thresholds, response, and R60.

## Analytic mass ledger

The pre-relief BGO/Kapton/outer-shell package is
`309.776766716 kg`, down
`81.422080584 kg`
(`20.813477%`) from the retained C0
bookkeeping baseline.  This is not whole-instrument mass and not a structural
qualification.  Unrelated retained tungsten elsewhere in the instrument is
unchanged.  Keeping the external envelope fixed leaves BGO-to-Kapton gaps of
`0.17 cm` side, `1.17 cm` bottom, and `3.17 cm` top; support/manufacturing
closure remains outside this transport-only model.

## Evidence

- Geometry: `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo.setup`
- Manifest: `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/s3d_o8_geometry_manifest.json`
- Mass ledger: `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/s3d_o8_mass_ledger.json`
- Static diff: `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/s3c_to_s3d_o8_static_diff_summary.json`
- Independent semantic validation: `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/s3d_o8_independent_geometry_validation.json`
- Overlap source: `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/overlap_check_s3d_o8.source`
- Overlap summary: `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/cosima_overlap_s3d_o8_summary.json` (`PASS` for current hashes)
- Screening analysis: `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/s3d_o8_screening_analysis.json`
- Independent screening reconciliation: `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/s3d_o8_screening_independent_validation.json` (`PASS`)
- Delayed campaign: `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/s3d_o8_delayed_activation_campaign.json` (`PASS_S3D_O8_NEUTRON_DELAYED_TRANSPORT`)
- Full-chain result: `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/fullchain/step08/step08_s3d_o8_fullchain_time_dependent_summary.json`
- Independent full-chain reconciliation: `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/s3d_o8_fullchain_independent_validation.json` (`PASS`)
- Human-readable validation: `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/FULLCHAIN_DATA_VALIDATION.md`

## Claim boundary

Geometry validation establishes loadability, overlap cleanliness at the
configured check, reference integrity, and analytic mass bookkeeping. The
matched screen supports the stated e+/n/atmospheric subset and focused-signal
promotion decision. The completed closure supports all-family prompt,
neutron-only delayed transport, explicit atmospheric-line, and mission-time
claims under the frozen detector-level selection. It does not close
non-neutron delayed activation, a matched heavy-control all-eight/delayed
full-chain replay, structural qualification, or detector-threshold systematics.
Native BGO scoring remains at 80 keV while the matched analysis veto is 50 keV;
this is a disclosed systematic boundary, not a claimed hardware threshold.

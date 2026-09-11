# O8 PARMA atmospheric-annihilation-line transport harness

This directory is reserved for an isolated `510.99895 keV` atmospheric
annihilation-line module. The harness cannot build a composite source and must
not be used for the continuum, prompt, delayed/activation, focused signal,
other particles, or a full-chain rerun.

The implementation is
`../code/o8_parma511_line_transport_harness.py`. Its normal commands do not
launch Cosima:

```bash
# Read-only authority/hash check plus `cosima -h` runtime/linker probe
python3 ../code/o8_parma511_line_transport_harness.py preflight

# Prepare one 1k smoke source card and manifest; do not run it
python3 ../code/o8_parma511_line_transport_harness.py prepare-smoke

# Prepare a recoverable campaign with unique cards, seeds, and prefixes
python3 ../code/o8_parma511_line_transport_harness.py prepare-campaign \
  --campaign-id o8_parma511_line_wave01 \
  --batches 8 --events-per-batch 1000000

# Read-only retained-SIM closure: 3M -> 69 TES -> 9 unsmeared W2 -> 8 primary
python3 ../code/o8_parma511_line_transport_harness.py self-test-old

# 15-process manifest-lock race; source-card preparation only, no Cosima
python3 ../code/o8_parma511_line_transport_harness.py self-test-concurrency
```

Preparation is not launch authorization. A prepared 1k smoke can be started
only after the main agent explicitly authorizes it, and only with both gates:

```bash
python3 ../code/o8_parma511_line_transport_harness.py run-batch \
  --manifest campaigns/o8_parma511_line_smoke_1k/campaign_manifest.json \
  --batch 0 \
  --authorize-line-only-cosima \
  --confirmation RUN_O8_PARMA511_LINE_ONLY_510.99895 \
  --quiet
```

`--quiet` routes Cosima stdout/stderr through a constant-memory pipe directly
to the batch's unique `*.stdout.log.gz`; no uncompressed log is retained. The
harness records the compressed log SHA/size, then obtains `TS` and `TE` from
the SIM footer, never from stdout.

`preflight` and every real `run-batch` use the complete minimal environment
frozen by the hash-pinned package44 runner. Its `LD_LIBRARY_PATH` is exactly
MEGAlib + ROOT 6.36.6 + Geant4 10.2.3. The preflight records the Cosima binary
hash, complete-environment canonical hash, and a successful source-free
`cosima -h` receipt. The calling shell's linker/physics environment is not
inherited.

## Per-batch closure

After a separately authorized transport finishes:

```bash
python3 ../code/o8_parma511_line_transport_harness.py analyze-batch \
  --manifest campaigns/o8_parma511_line_wave01/campaign_manifest.json \
  --batch 0
```

The parser is streaming. It consumes `ID`, `CC HIT`, and `IA INIT`, and saves:

- `tes_events.csv`: TES event, active-veto total, INIT direction/energy, and
  its 20/40/80 equal-mu bins;
- `tes_pixel_hits.csv`: aggregated per-pixel energy and energy-weighted
  position;
- `angular_counts.json`: all-INIT 20/40/80 counts;
- `provenance.json`: source/hash, SIM raw hash, O8 setup/geo/det hashes,
  transport seed, energy range, header, footer `TS/TE`, `ID/IA` closure, and
  compact artifact hashes;
- `response/`: frozen Step05 topology, the primary and 64 deterministic
  420-eV-FWHM response seeds, same-event 20/40/80 importance weights, and
  `angular_response_coefficients_{20,40,80}bins.csv`. Each angular table has
  `N_init`, `N_TES`, `N_unsmeared_W2`, `N_primary_W2`, `q=N/N_init`, response
  area, two-sided 95% Wilson intervals, exact one-sided 95% zero-count upper
  limits, and target-flux importance response coefficients for offline
  trajectory folding.

The 40/80 diagnostic uses the paired per-event weight difference. The rate
gate records selected count, ESS, RSE, and requires both `count>=400 OR
RSE<=5%` and the configured combined paired 40/80 error `<1.5%`. A failure is
diagnostic; it is not permission to rerun other modules.

The active-veto predicate is intentionally frozen, but it has a naming
blocker. It sums BGO and the S1/S2B plastic volumes, and also every volume whose
name contains `ACTIVE_SHIELD`. In O8 the latter unintentionally includes all
three passive Kapton wrappers:

- `ActiveShield_S3C_BGO_Kapton_SideWrap_WindowCut_0p3mm`;
- `ActiveShield_S3C_BGO_Kapton_BottomCap_0p3mm`;
- `ActiveShield_S3C_BGO_Kapton_TopAnnulus_0p3mm`.

No other final O8 `Volume` name contains `ActiveShield`. The harness does not
repair this policy; it records the blocker in parse/response receipts. In the
retained old line self-test, all 9 unsmeared and all 8 primary W2 survivors
still have summed matched active energy exactly `0 keV`. The complete old 3M
SIM nevertheless contains `40,677` Kapton bottom-cap, `155,840` Kapton
side-wrap, and `7,280` Kapton top-annulus `CC HIT` records that the frozen
predicate counts as active energy. Thus the old W2 integer result is unchanged,
but the naming-policy issue remains a blocker for interpreting the veto as
"BGO + plastic only."

## Compact-only campaign merge and cleanup boundary

Once batches are parsed, merge them without touching raw SIM files:

```bash
python3 ../code/o8_parma511_line_transport_harness.py aggregate-campaign \
  --manifest campaigns/o8_parma511_line_wave01/campaign_manifest.json
```

For an in-progress wave, add `--allow-partial`. The aggregate validates each
compact/provenance/response hash, merges event lineage and angular counts,
sums physical exposure `TE`, reruns the 64-seed response on the pooled compact
events, and writes a campaign gate receipt. Therefore it remains reproducible
after an operator has explicitly removed an already-closed raw SIM.

Every batch state transition takes a campaign-local `fcntl` exclusive lock,
reloads the manifest inside that lock, merges only the target batch update,
and atomically replaces the JSON. Aggregate creation holds the same lock. The
15-process `self-test-concurrency` verifies that no batch update is lost.

Raw files are never removed by this harness. A raw path is merely labelled
`ELIGIBLE_FOR_EXPLICIT_EXTERNAL_CLEANUP_NOT_DELETED` when all of the following
hold:

1. it is the exact manifest path inside this new campaign's `raw/` directory;
2. source, O8 geometry hashes, seed, energy, footer `TS/TE`, `ID/IA`, angular
   counts, compact hashes, and batch response receipt all close;
3. the batch is included in a compact campaign aggregate.

There is intentionally no cleanup/delete command.

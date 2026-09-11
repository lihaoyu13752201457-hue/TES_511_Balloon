# Compact truth to standalone SIM consumer gate

Status: implemented and exercised with zero transport on 2026-08-12. This is
not by itself an `M05_COMPLETE` claim: every production materialization still
requires its own hash-bound MFileEventsSim and Revan attestations.

## Contract

`code/materialize_standalone_sim.py` consumes an already finalized
`m05cc-v2-record-bundle` plus its independent EventList tape and exact tape
root sidecar. It first runs `record_validation.validate_bundle`, imports
`tape_contract.SIDECAR_COLUMNS` and `validate_sidecar` as the sole tape header
and validation authority, and reads record-table headers from
`schema/m05cc_v2.record_schema.json` rather than copying them.

For every root it strictly joins the EventList ID, stable root ID, exact
assigned benchmark driver (`benchmark_driver_id == tape.driver`, while rounded
native-direction inference stays empty/`unavailable`/`[]`), family/mode, raw
line hash, raw-direction EventList binary64 hash, normalized expected-generated
binary64 hash, observed-generated binary64 hash, generated tuple hash, serialized IA
INIT hash, native event time, control bit, lifecycle flags, truth selection,
and footer counts. Native truth ranges must be gap-free, in event order, in
bounds, and byte-hash exact. Every native fragment must have exactly one
`SE`, one `ID`, one `TI`, and one `IA INIT`; all IA IDs/origins and all HT
origins must close. IA INIT record time is checked as zero independently of
the event/source `TI` time.

Selected/control fragments are embedded byte-for-byte. Every other root is
represented by a deterministic, one-INIT/zero-HT event. The final ASCII
envelope has `Type SIM`, `Version 101`, the exact absolute `Geometry`, and one
`EN`. Publication writes `events.sim`, `index.tsv`, and finally
`manifest.json` under `<prefix>.standalone.partial`, fsyncs the members and
directory, then atomically renames it to `<prefix>.standalone`.

The materializer performs no transport and does not call Cosima or EventList.

## Invocation

```bash
python3 code/materialize_standalone_sim.py \
  --record-bundle /path/to/compact-C-final.m05cc/record_bundle.json \
  --tape /path/to/frozen.eventlist \
  --tape-roots /path/to/frozen.tape_roots.tsv \
  --geometry /absolute/path/to/geometry.geo.setup \
  --geometry-sha256 <sha256> \
  --geometry-classification transport_preflight_v1/geometry_classification_manifest.json \
  --output-prefix /new/write-once/output
```

This input is arm-specific. Only the compact `C` arm publishes
`record_bundle.json` and is eligible for materialization. `N1` publishes the
separate `m05cc-n1-v1-commit` marker at `commit.json`; it contains root,
generated-observer, footer, tape, and native-DAT evidence but no compact
event/pixel/veto/truth tables, so the materializer must reject it rather than
infer or synthesize missing C records.

All input paths are explicit, so the consumer accepts files inside the
transactional `<TES511_OUTPUT_PREFIX>.m05cc/` directory and makes no legacy
`prefix.suffix` assumption.

## Real MEGAlib gate

`code/mfileeventssim_roundtrip.cc` reads every event with the installed
`MFileEventsSim`, requires observed Type `sim`, Version `101`, and the exact
geometry, and requires byte-identical `ToSimString(All, 17, 101)` output plus
ID/IA/HT/unique-INIT closure. It then exercises the installed Revan
`MRawEventAnalyzer` initial reader and analysis paths over the hit-populated
subset.

The required fixture calls `code/build_mfileeventssim_roundtrip.py` directly;
it is not conditionally skipped. The helper content-addresses the source,
compiler, ROOT flags and installed MEGAlib root, compiles with `-Werror`,
checks `ldd`, and transactionally publishes the binary plus a hash-bound
build manifest. Its effective compile/link contract is:

```bash
g++ -std=c++17 -O2 -Wall -Wextra -Werror \
  -isystem /home/ubuntu/MEGAlib_Install/megalib-main/include \
  $(/home/ubuntu/MEGAlib_Install/megalib-main/external/root_v6.36.6/bin/root-config --cflags) \
  code/mfileeventssim_roundtrip.cc -L"$MEGALIB/lib" \
  -Wl,-rpath,"$MEGALIB/lib" -Wl,--no-as-needed \
  -lRevan -lSpectralyze -lSivan -lGeomega -lCommonMisc -lCommonGui -lcrypto \
  $(/home/ubuntu/MEGAlib_Install/megalib-main/external/root_v6.36.6/bin/root-config --glibs) \
  -o build/nontransport/real_mfileeventssim_roundtrip/<content-addressed-name>
```

`code/revan_zero_transport_gate.py` is a second, command-line Revan gate. It
requires the supplied bytes to equal the frozen package configuration
`config/revan_zero_transport_fixture_v1.cfg`, copies those bytes into a
quarantined output directory, invokes
`revan -a -n` on the materialized SIM, and distrusts exit status alone: it
also requires the completion marker, exact triggered-input count, output TRA
Type/Version/Geometry, unique reconstructed IDs drawn from the SIM, footer
markers, and all size/hash bindings. It atomically publishes a write-once
`<prefix>.revan/attestation.json` only after those checks pass.
The frozen configuration SHA-256 is
`4f0307d121b40a2a2ff3d1b9481ed7b669e859dd0977263ffd1d80f21610aea9`;
ambient user Revan configurations are rejected byte-for-byte.

```bash
source /home/ubuntu/MEGAlib_Install/megalib-main/bin/source-megalib.sh
python3 code/revan_zero_transport_gate.py \
  --standalone-manifest /path/output.standalone/manifest.json \
  --revan "$MEGALIB/bin/revan" \
  --revan-config config/revan_zero_transport_fixture_v1.cfg \
  --output-prefix /new/write-once/consumer
```

## Zero-transport fixture results

`tests/test_standalone_materializer.py` constructs five roots: the first
three mandatory controls, one nonselected root, and one TES-selected root
with one native HT. The expected standalone representation is four native
events plus one generated INIT-only event. Negative fixtures alter truth,
ID, SE, IA, HT origin, footer count, tape hashes, raw and generated binary64
identities, and required control coverage.

With the Mass-model geometry and the installed MEGAlib environment:

```text
Ran 6 tests in 10.146s
OK
```

The real in-process consumer reported 5 SIM events, 5 IAs, 1 HT, 5 unique
INITs, 1 Revan initial event/RESE, and 1 successful Revan analysis. The real
Revan CLI independently reported 5 triggered inputs, reconstructed event ID
5 as one single-site event, and emitted a valid TRA with the same geometry.
No Cosima/EventList transport was launched by any fixture or consumer gate.

`code/run_standalone_consumer_fixture.py` additionally published durable,
write-once evidence under
`evidence/standalone_consumer_fixture_v1_20260812/`. Its final
`commit.json` SHA-256 is
`ddb998339d6e4fe4581e72e7af6db68d1032d6af65ae16560f3e22f402992158`.
The commit revalidates 17 file size/hash bindings, including the compiled
consumer, real Revan executable, frozen configuration, geometry, standalone
SIM/index/manifest, MFileEventsSim log, Revan log, TRA, and Revan attestation.

The independent tape sampler's Poisson clock is a per-family/per-mode cell
clock (with four shard-local views of that cell). Clocks from the seven
families are not one shared physical timeline and must not be concatenated or
treated as a seven-family accidental-coincidence stream.

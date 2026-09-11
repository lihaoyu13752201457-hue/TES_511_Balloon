# SG3 — SF3-faithful Cu-ring + compact Bi-umbrella candidate

## Status

`SG3` is a geometry-complete, overlap-clean **candidate**, not a promoted optimum and not a physics result. It is a byte-reversible child of the frozen SF3 geometry and makes exactly two physical changes:

1. replace `Cu_SubstrateSupport_SolidDisk_L0_deepest` with a square Cu heat-sink annulus;
2. remove the three passive SF3 W pieces and add one compact passive Bi MXC-to-TES shadow umbrella.

No prompt, activation, inventory, delayed, response, veto, or Step05 transport was launched in this package. Passive Bi is not an active veto. The corrected continuum source remains the only admissible future source; the separate mono-511 source remains disabled.

## Implemented dimensions

### L0 Cu heat-sink ring

- location and axial thickness inherited from the SF3 disk: `x' = 3.42 cm`, thickness `0.35 cm`;
- outer square half-width: `2.80 cm`;
- central square opening half-width: `0.80 cm`;
- in-plane total Cu band width: **2.00 cm**;
- overlap into the nominal TES-substrate projection: **1.00 cm**;
- protrusion beyond the nominal TES-substrate half-width (`1.80 cm`): **1.00 cm**;
- all four inherited edge-rod centres at `|y'|, |z'+5.2| = 1.95 cm` terminate inside the ring band;
- Cu mass changes from `60.713 g` to `90.317 g` (`+29.604 g`). This deliberately pays a small mass penalty to preserve the stricter thermal-contact footprint.

The necessary `.det` reference is migrated from the removed disk to the new ring while preserving its thresholds and energy-resolution lines. Reversing that one coupled detector-map edit reconstructs the SF3 `.det` byte-for-byte.

### Cold-finger/POLE decision

SF3 does not contain one central POLE. It already contains **four off-axis Cu thermal-link chains**, one at each `(y',z'-z'ring)=(+/-1.1,+/-1.1) cm`: four horizontal disk-to-stem rods, four vertical stems, and four MXC clamp pads. SG3 preserves all 12 component definitions exactly from SF3, so their audited Cu mass remains `21.0615 g`; no pole mass was added, removed, or redistributed. Each complete rod foot lies within the new Cu-ring band, with at least `0.1869 cm` clearance from the central cut and `1.5869 cm` from the outer edge.

Therefore SG3 does **not** split or reroute the inherited cold finger. Reducing the existing four paths to two would be a larger and less redundant mechanical change, while passing a pole through the central opening would repopulate the deliberately cleared near-field/signal corridor. At the ring plane, a diagnostic centered `r=1.6 mm` pole footprint contains `947/37,194` focused-ray intersections; this is a geometry screen, not a transport-loss prediction.

The MEGAlib mass model retains small navigation clearances (`0.01 cm` ring-to-rod and rod-to-stem, plus inherited clamp/MXC clearances). These volumes encode the intended thermal-link topology but do not constitute a literal contact or thermal-conductance model. A fabrication design must close those interfaces and prove conductance/stress separately; doing that silently in SG3 would violate the near-field-minimal-change contract. See `audit/sg3_coldfinger_connectivity_and_minimal_delta.json` and `figures/sg3_coldfinger_connectivity.png`.

### Bi MXC-to-TES shadow umbrella

- natural-Bi engineering proxy (`density = 9.747 g cm^-3`);
- bounds in InstrumentFrame: `x'=[-3.8,4.0] cm`, `y'=[-2.25,2.25] cm`, `z'=[-2.39,-1.9104] cm`;
- thickness: **4.796 mm**;
- mass: **0.164081 kg**;
- it covers the local TES projection but does not wrap the TES or occupy the focused-ray corridor;
- the lower surface remains `0.01 cm` above the expanded Cu-ring top; the most restrictive rectangular-corner clearance to the inherited Al inner cylinder is about `0.031 cm`.

The 4.796 mm thickness is the pre-transport material-screen match to the 511-keV attenuation of the SF3 2.9 mm W slab. At the three actual SF3 prompt-parent energies (4.289, 13.628, and 21.734 MeV), the material-only pair-interaction screen is `7.96%, 18.66%, 23.16%` for Bi versus `8.50%, 20.43%, 25.36%` for W. These are per-slab-crossing engineering estimates; geometry-dependent prompt performance is still unknown. See `data/sg3_material_screening.csv`.

## Mass delta

- removed SF3 passive W: `1.894708 kg`;
- added SG3 Bi: `0.164081 kg`;
- Cu disk-to-ring: `+0.029604 kg`;
- **SG3 minus SF3: `-1.701024 kg`**.

## Closed geometry gates

- `audit/sg3_geometry_validation.json`: PASS; the two geometry edits, Bi material suffix, and required detector-map edit reverse to the pinned SF3 bytes.
- `audit/sg3_mesh_ray_static_prefilter.json`: PASS; 804,762 inherited surface samples and 915 candidate-internal probes find no collision after excluding the deliberately replaced SF3 disk.
- `audit/sg3_overlap_validation.json`: PASS; real Cosima/Geant4 construction with `CheckForOverlaps 10000 0.0001`, no `beamOn`, no particle records, and no overlap warning.
- `audit/sg3_native_navigation_audit.json`: PASS; native MDGeometryQuest SF3/SG3 comparison on all 37,194 focused rays.
- `audit/sg3_coldfinger_connectivity_and_minimal_delta.json`: PASS; four inherited thermal-link chains unchanged, all feet captured by the ring, and only the two declared near-field physical changes remain.

The native ray result is especially strong:

- Bi chord: `0` for `37,194/37,194` rays;
- minimum vertical Bi-to-ray clearance: `1.4830 cm`;
- Cu chord never increases: it is reduced for `28,441/37,194` rays (by as much as `0.35001 cm`) and unchanged for the other `8,753`;
- W chord change: `0` for all rays;
- every material other than the deliberately exchanged Cu/Vacuum chord is byte-path equivalent within `2e-5 cm`;
- three native witnesses close the Bi thickness, Cu ring material, and central opening.

## Evidence-based expectation — not a result

The retained SE3 delayed-W2 sample contains one high-weight source in the old L0 disk at `(x',y',z')=(3.420,-0.347,-4.670) cm`; its `0.00883525 cps` is `14.70%` of the retained `0.06011336 cps` delayed-W2 diagnostic rate, and the point lies inside the SG3 ring opening. That makes this a well-targeted change, but SG3 must generate its own activation inventory before any rate can be claimed.

The retained MXC origins contribute `25.07%` of that diagnostic delayed rate. A directly intercepted 511-keV ray sees the material-screen attenuation of about `52.7%`, so `13.2%` of the total delayed rate is only a **geometric upper bound** for the MXC term; the compact umbrella does not intercept every MXC-to-TES direction. The two SF3 prompt survivors whose parent pair conversion occurred in W should lose those exact W-shell topologies, but SG3 can create new Bi or elsewhere pair topologies. Therefore there is deliberately no single quoted “SG3 performance improvement”.

## Diagnostic sections

The two sections reuse the retained TOOL under `52_se3_sf3_activation_prompt_section_tool_20260816/TOOL`. The inherited mesh is exact; SG3 changes are analytic overlays. SE3 activation origins and SF3 prompt tracks are explicitly diagnostic history, not SG3 predictions.

- `figures/sg3_global_diagnostic_section.png`
- `figures/sg3_local_nearfield_diagnostic_section.png`
- `figures/sg3_coldfinger_connectivity.png`

## Reproduction

```bash
python3 code/build_sg3_geometry.py
python3 code/validate_sg3_mesh_and_rays.py --check
python3 code/run_sg3_overlap.py
python3 code/run_sg3_native_navigation_audit.py
python3 code/build_sg3_diagnostic_sections.py
python3 code/audit_sg3_coldfinger_connectivity.py
```

The next physics gate is a small candidate-own corrected prompt screen, followed—only if prompt behavior is acceptable—by candidate-own activation inventory, actual-position delayed transport, the independent 37,194-ray signal run, and the shared response/veto/Step05 closure. SF3 contributes no full-stat pool to SG3.

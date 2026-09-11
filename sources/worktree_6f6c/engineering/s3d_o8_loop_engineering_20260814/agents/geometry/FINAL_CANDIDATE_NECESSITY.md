# S3d-O8 final candidate necessity review

Date: 2026-08-14  
Scope: read-only budget, geometry, mass-authority, and engineering-admissibility review. No transport was run. All numerical reductions below are deliberately optimistic central-value necessity bounds, not candidate predictions.

## Decision

**NO ADMISSIBLE CANDIDATE.**

Within the present evidence, no single, simple, mass-conserving geometry can be specified that both preserves the signal path and has even an optimistic defensible route from `B=0.088322680 cps` to `B<=0.016581810 cps`.

The reason is twofold but has one engineering root:

1. The budget requires a joint prompt and multi-component delayed reduction. Even granting complete prompt removal, no one implicated cold component is sufficient. The smallest rate-ranked arithmetic crossing uses four essential parts—MXC Cu plate, Nb inner shield, Mu outer shield, and L0 Cu support—and requires the impossible idealization that their full delayed contributions simultaneously vanish.
2. The supplied geometry is a transport proxy, not an as-built assembly authority. It provides neither certified reallocation mass nor the real signal/service aperture, BGO readout/support topology, cold thermal/load interfaces, or magnetic design needed to turn that four-function redesign into one exact engineering candidate.

The **single engineering blocker** is therefore:

> **absence of one configuration-controlled as-built CAD/BOM/interface authority mapped volume-by-volume to S3d-O8**, including post-machining masses, the true signal/service and BGO-readout apertures, cold-plate/support interfaces, and Nb/Mu material/seam/performance requirements.

Until that authority exists, an equal-mass CSG edit would be only a bookkeeping-balanced transport sketch. It cannot be certified as mass-conserving, signal-preserving, thermally/structurally viable, magnetically viable, or compatible with the existing readout-channel count.

## 1. Authorities and fitness for this decision

Path aliases:

- `MAINLINE` = `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/particle_source_unit_repair_20260811/s3d_o8_loop_engineering_handoff_20260814/HANDOFF_A_PROJECT_MAINLINE.md`
- `GEO` = `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/geometry/DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy.geo`
- `GEO_README` = `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/README.md`
- `MANIFEST` = `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/s3d_o8_geometry_manifest.json`
- `LEDGER` = `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/s3d_o8_mass_ledger.json`
- `BASE_README` = `/home/ubuntu/.codex/worktrees/104d/TES_511_Balloon/outputs/geometry/DEMO2_DR_v3p5_Mass_model_511_stage_diam_300_300_300_350_350_400_20260701_megalib_proxy/README.md`
- `PROMPT_AUDIT` = `/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/agents/prompt/PROMPT_PHYSICS_AUDIT.md`
- `DELAYED_AUDIT` = `/home/ubuntu/.codex/worktrees/6f6c/TES_511_Balloon/engineering/s3d_o8_loop_engineering_20260814/agents/delayed/FACT_UNKNOWN.md`

Data-quality judgment:

| Evidence | Intended use here | Fitness | Why |
|---|---|---|---|
| Stage-04 central prompt/delayed rates (`MAINLINE:136-150`) | Budget identity and necessary reduction | **Fit, high confidence** | Same S3d geometry and common-response selection; prompt + delayed closes exactly to total. |
| Delayed component fold (`DELAYED_AUDIT:38-69`) | Optimistic component-excision bound | **Fit only as a bound** | Global event Neff is 28.75; every named component has position Neff below 8, so it cannot predict a material-scaling benefit. |
| Complete prompt denominator (`PROMPT_AUDIT:163-235`) | Reject a local outer-shield sector claim | **Fit** | All 3,207,738 incident gamma histories are counted, but each nonzero leak cell still has only one survivor. |
| `.geo` CSG | Transport dimensions and nominal clearances | **Fit for proxy geometry only** | It is not a manufacturing, thermal, structural, magnetic, or readout authority. |
| Shield mass ledger (`LEDGER:1-22`) | Real mass conservation | **Not fit / critical** | It explicitly uses pre-relief axisymmetric bookkeeping, BGO density 7.13 rather than transport 7.1, and excludes whole-instrument/structural mass. |
| Real CAD/BOM | Engineering admissibility | **Absent / critical** | No STEP/IGES/FCStd file and no current assembly BOM were found; all `mass_budget` files found are historical under `old/`. |

## 2. Central budget necessity

The matched day-15 central rates are (`MAINLINE:138-148`):

| Quantity | cps |
|---|---:|
| prompt `P0` | 0.033842928 |
| delayed `D0` | 0.054479752 |
| total `B0=P0+D0` | 0.088322680 |
| required maximum `Bmax` | 0.016581810 |
| required reduction `B0-Bmax` | **0.071740870 (81.2259%)** |

Two unavoidable conditions follow:

- Even if delayed were zero, prompt must fall by at least `0.017261118 cps`, or 51.00%.
- Even if prompt were zero, delayed must fall by at least `0.037897942 cps`, or 69.56%.

The following table is intentionally more favorable than any physical geometry: every listed direct delayed contribution is set to zero and **all prompt is also set to zero**, even where the proposed component does not control all prompt hosts.

| Idealized affected delayed contribution | Delayed set to zero (cps) | Residual `B` after also setting all prompt to zero (cps) | Result vs 0.016581810 |
|---|---:|---:|---:|
| Nb inner cylinder only | 0.007808604 | 0.046671148 | FAIL by 0.030089338 |
| MXC Cu plate only | 0.016771496 | 0.037708256 | FAIL by 0.021126446 |
| three largest modifiable named hosts: MXC + Nb + Mu | 0.032345554 | 0.022134198 | FAIL by 0.005552388 |
| four largest: MXC + Nb + Mu + L0 Cu support | 0.038195061 | 0.016284691 | nominal PASS by only **0.000297119** |

Component rates are from `DELAYED_AUDIT:56-65`. The last row is not a candidate: it assumes 100% prompt removal and 100% removal of delayed W2 from four different functional systems despite finite remaining material and host migration. Its margin is only 1.79% of `Bmax`; because `Bmax=(S20/10)^2`, a signal loss of merely 0.90% would erase it.

Consequences:

- The previously screened G-Nb-S1 one-part change is **KILL by necessity**. Even complete removal of every prompt count plus every Nb delayed count cannot reach the central budget; actual 2 -> 1 mm thinning is much weaker than that bound.
- An MXC-only plate pocket/thinning is also **KILL by necessity** under the same deliberately favorable bound.
- A candidate with a plausible central crossing must act across at least four high-contribution systems; the most favorable four-host set is MXC Cu, Nb, Mu, and L0 Cu, while an alternative that avoids one of these requires still more parts. It must also suppress prompt essentially completely. That is a multi-material, multi-function cold-core redesign, not one simple geometry knob.

This arithmetic does not credit unsupported mass scaling. The delayed audit explicitly separates production Bq from W2/Bq and shows component position Neff below 8 (`DELAYED_AUDIT:51-69,182-210`). The prompt audit likewise finds mixed passive pair hosts and rejects Nb as a universal host (`PROMPT_AUDIT:254-317`).

## 3. Outer BGO/BPE cannot presently supply a certified reallocation candidate

### 3.1 Nominal proxy mass is not certified available mass

| Family | Nominal proxy number | Authority limitation | Certified reallocatable mass now |
|---|---:|---|---:|
| BGO side + bottom + top | 296.5499 kg using actual transport density 7.1, before reliefs | Exact post-CSG mass absent. `LEDGER` instead reports 297.8028 kg at 7.13 and calls itself pre-relief bookkeeping. | **0 kg** |
| BPE side + two caps | 33.6056 kg before reliefs | BPE block is labeled `DRAFT...NOT_TRANSPORT_VALIDATED`; no real support, joint, service, or procurement BOM exists. | **0 kg** |
| Claimed S3d package saving vs C0 | 81.4221 kg (`LEDGER:2-22`) | Excludes BPE/plastic and whole-instrument/structural mass; cannot be treated as a flight allocation reserve. | **0 kg certified** |

`GEO_README:94-104` independently says the 309.7768 kg package is pre-relief, not whole-instrument mass, and not structural qualification. `MANIFEST:76-87` calls S3d a minimal-delta transport geometry and gives only nominal BGO-to-Kapton gaps of 1.7 mm side, 11.7 mm bottom, and 31.7 mm top. These gaps are not certified free volume or load/readout envelope.

### 3.2 The signal/service aperture is not consistently represented

The modeled signal corridor is locally centered at `(y,z)=(0,-5.2 cm)` along the x direction:

- BGO has a 37.96 x 37.96 mm negative-x window (`GEO:16769-16776`).
- The W multihole collimator uses the same 37.96 mm square envelope at `x=-25.9 cm` (`GEO:12790-12812`).
- The 50 mK Cu can has a matching negative-x rectangular cut and the Nb/Mu sleeves are open upstream; the Al foil is 37.96 mm square (`GEO:11779-11820,11840-11846`).
- In contrast, the BPE and plastic side shells are full annuli with only base/top-mount and six NF2 reliefs (`GEO:16360-16430,16564-16628`); there is no corresponding side-window subtraction. Their top/bottom service topology is likewise only a coarse proxy.

Therefore “preserve the signal path” is not an executable engineering constraint from this model alone. One cannot tell whether to preserve a true vacuum aperture, a BPE/plastic transmission layer, photodetector clearance, cable/service space, or a combination. Reshaping active BGO also requires the absent segmentation, optical-collection, photosensor, support, and existing-channel map; preserving the volume scorer is not proof that no new readout channel is needed.

### 3.3 Physics does not select where to move the mass

The three prompt leaks cross 23.4–38.9 g cm^-2 of continuous active material and are uncollided until pair creation in inner passive Nb/Cu (`PROMPT_AUDIT:10-37,98-137`). They are not aperture leaks. All 640 energy × equal-solid-angle cells have denominators, but the three occupied cells each have leak Neff=1 (`PROMPT_AUDIT:208-235`). Removing BGO/BPE from unoccupied directions to build one local sector would therefore be an extrapolation from three numerators and could create a new low-grammage path.

Delayed production is also not a narrow incident-neutron cone: the n/p/alpha parent-production directions are broad, and high-energy p/alpha primaries commonly generate the relevant Cu parents through secondary neutrons (`DELAYED_AUDIT:106-180`). An external BPE sector has no denominator-supported location that can be credited with the required >=69.56% delayed reduction.

Thus an exact equal-volume BGO/BPE CSG redistribution could be drawn, but no placement is both physics-selected and engineering-certified. It is not an admissible candidate.

## 4. The only optimistic crossing requires an undefinable cold-core combination

The four components in the first arithmetic crossing have the following proxy masses:

| Component | Proxy mass (kg) | Required real function that must remain |
|---|---:|---|
| MXC 50 mK Cu plate | 3.797526 | thermalization, temperature uniformity, load path, cold-stage interfaces |
| Nb sleeve + back cap | 0.427585 | superconducting magnetic attenuation and controlled field cooling |
| Mu sleeve + back cap | 0.500911 | low-temperature high-permeability attenuation, seams and penetrations |
| L0 Cu support BRIK | 0.060672 | TES substrate support/alignment and thermal path |
| **total** | **4.786694** | four coupled thermal/structural/magnetic functions |

These values are exact for the ideal transport primitives, not for real hardware. The plate is a solid 300 mm x 6 mm disk with no holes; rods are volume-equivalent proxies; small brackets are omitted; and the modeled can and plate do not actually share a face (`GEO:11779-11820,11847-11935`; `BASE_README:1-17`). The real holes, bosses, joints, braids, fasteners, cables, material grades/RRR, seams, and contact conductances are unknown.

For scale only, moving all 4.786694 kg to the outer proxy would equal about 0.767 mm of uniform BGO-side thickness or 4.062 mm of uniform BPE-side thickness. Those equal-mass numbers do not define a useful sector and do not rescue the destroyed cold functions. Replacing Cu/Nb/Mu with another material is equally undefined without thermal, structural, magnetic and field-cool acceptance floors.

Accordingly there is no exact geometry/mass entry to freeze. Any proposed combined dimensions would be arbitrary cuts through unmodeled interfaces, and calling the aggregate one “topology” would not make it simple or function-preserving.

## 5. Final LOOP verdict

- **KILL** G-Nb-S1 and any other one-component inner thinning as a mission candidate: the perfect-removal lower bound still misses `Bmax`.
- **KILL** MXC-only and directional BGO/BPE-sector candidates on present evidence: the former is budget-insufficient; the latter has neither certified mass/aperture geometry nor a denominator-supported placement.
- **NO ADMISSIBLE CANDIDATE** can be frozen without inventing real hardware.

The sole unblocker is the configuration-controlled as-built CAD/BOM/interface authority stated at the top. It must map each real part to the transport volume and contain post-machining mass, permitted remove/add zones, existing BGO photosensor/channel topology, the true 37.96 mm-class signal/service corridor, cold thermal/load contacts, and Nb/Mu magnetic material/seam/performance floors. These are required fields of one engineering authority, not parallel candidate suggestions.

After that authority exists, the first admissible design must still be proved with candidate-own prompt, affected n/p/alpha production, day-15 inventory, delayed W2/Bq, host migration, focused `S20`, and common response. That future physics proof does not alter the present engineering verdict.

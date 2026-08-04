# EA body-claim audit on the Mass_model_511 → S3d evidence chain

Status: `ONE_TRUE_BODY_SCOPE_OMISSION_REMAINS`.

This audit reads the active English and Chinese EA manuscripts against retained
Mass_model_511 and S3d/O8 products. Outlook items in the manuscripts' “Scope and
next steps” subsection are excluded, as requested. No Monte Carlo transport was
started for this audit.

## Closed from existing products

1. **Reference all-family activation and selected delayed behavior.**
   Mass_model_511 already contains 25,210,216 activation-production primaries,
   the NUBASE-corrected 141.833438 Bq day-15 inventory, 50,000 sampled production
   positions, one million delayed decays, and detector-selected delayed records.
   The active manuscripts now describe this completed chain instead of saying
   that selected-rate behavior remains to be tested.
2. **Reference material and incident-family fractions.**
   The retained 380,872-row weighted production table closes to the source
   authority and gives the material/family fractions reported in Methods and
   Results. The analysis is recorded in
   `data/mass_activation_material_family_audit.json`.
3. **Pixel-level energy response.**
   The retained event catalogues now have the stated 420 eV FWHM per-pixel
   response, 0.3 keV measured-hit threshold, common W2/veto/topology selection,
   and a 64-seed numerical integration audit. This remains validated by the
   detector-response closure package.
4. **Final S3d detector branch.**
   The current final-geometry result is supported by all-eight-family prompt,
   neutron-induced exact-position delayed transport, an explicit atmospheric
   511 keV sidecar, focused-signal replay, and the 81-bin mission fold. The final
   delayed stream is labelled neutron-induced in the paper; the remaining
   activation families occur only in the outlook and are not a missing body
   claim.

## Scope descriptions that are not missing implementations

- The Ta absorber, Si substrate, service-mass proxies, and imposed energy
  response are the declared transport representation of TES thermal/readout
  microphysics. The paper does not claim a thermal-electrical detector model.
- The Compton layer is an aperture-consistency veto. It is now written directly
  as that method rather than as a statement that imaging was not performed.
- The 81-bin trajectory is a synthetic reference exposure, not a named flight
  forecast. Its altitude/rigidity/transmission scaling and cumulative counting
  calculation are implemented as stated.

## Remaining body-scope omission

**Coupled optics-mass prompt and delayed self-background is not part of the S3d
primary background budget.**

The optics package contains a migrated, overlap-clean model with 1245 Ge tiles,
G10 carrier, aluminium mount, and brackets, plus MC smoke verification. The
Step04/Step09 bridge transports focused-signal phase space into the detector.
Neither product couples optics hardware into the atmospheric prompt/activation
background chain or produces a detector-selected S3d optics-background rate.

Evidence boundaries:

- `engineering/Mass_model_511_nearfield_migration_20260701/05_optics_migration/optics_migration.md`
  explicitly limits the optics geometry to migration and smoke verification.
- `stepwise_maintenance/step09_optics_bridge/outputs_f10m_a1_v3p5/step09_optics_bridge_summary.json`
  is a focused-signal EventList handoff, not optics-mass background transport.
- `engineering/geometry_optimization_20260704/42_geoopt_s3d_lightweight_20260712/README.md`
  keeps optics-hardware background outside the detector geometry branch.

The Methods text now states the implemented scope positively: the primary
background budget is the detector/cryostat branch, and the optics branch supplies
the transported focal-plane signal phase space. This does not promote the optics
smoke result into a background closure. Closing the omitted physical term would
require a separately authorized coupled optics-to-detector background campaign;
it cannot be inferred from the existing signal bridge or the archived proxy
bound.

## Conclusion

Within the paper's current detector/cryostat S3d objective, the retained data are
sufficient and no additional activation production is required. The only
remaining non-outlook physical component named by the body but outside the
implemented primary budget is optics-hardware prompt/delayed self-background.

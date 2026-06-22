# Step11 upstream optics hardware background branch

Status: full-particle prompt and activation-production transport closed; Ge-proxy delayed selected-rate contribution closed; prompt self-background selected-rate isolation open.

This branch is the missing calculation for prompt and delayed backgrounds generated in
the upstream Laue-lens hardware itself. It is separate from Step04/Step09:
Step04/Step09 transport the focused 511 keV gamma-ray signal through the optical
model and replay the accepted focal-plane gamma rays through the detector.

The focal-plane crossing table is not enough to close this branch. A complete run
must add a Laue-lens mechanical mass proxy to the prompt and activation transport
geometry, irradiate that geometry with the same balloon atmospheric/cosmic source
families used for the detector background, record prompt detector contributions and
activation products in the optics hardware, build the delayed inventory, and pass the
result through the same Step05--Step08 detector-response and significance chain.

Current geometry/source evidence also prevents a direct reuse of Step02. The
baseline detector background source cards use a 60 cm far-field source sphere around
the detector setup, while the current detector geometry describes the local
detector/cryostat region. A 10 m focal-length Laue lens must therefore be added with
a larger upstream transport geometry and a re-normalized far-field source definition,
not by replaying the existing focal-plane crossing table.

Smoke closure performed on 2026-06-16:

1. `build_step11_optics_background_smoke.py` derives the current detector geometry,
   expands the world, derives the source surface from the combined detector-plus-
   lens envelope, and adds an equal-volume/equal-mass Ge annulus proxy for the
   f = 10 m Laue-ring active crystal mass scale.
2. The builder emits EXPACS/PARMA smoke source cards for `gamma`, `n`, `eminus`,
   `eplus`, `p`, `alpha`, `muplus`, and `muminus`, each with `ActivationBuildup`
   and isotope storage enabled.
3. `run_step11_smokes.py` ran 100 events for each EXPACS/PARMA particle family and
   a separate 1000-event directed Ge activation smoke. All runs returned zero,
   generated the requested event counts, wrote `.sim.gz` files, wrote isotope files,
   and reported zero outside-world messages.
4. The active Ge proxy represents 25 square Ge tiles, 1.8 cm on a side and
   1.0218801 cm thick, for a total active Ge volume of 82.7722881 cm3 and a
   mass of 0.4405969 kg. The lens center is 1000 cm upstream of the detector
   origin and the lens volume bound radius is 8.79931 cm.
5. The far-field source surface radius is 1060 cm. It is derived from the
   detector-plus-upstream-lens enclosing radius of 1008.79931 cm with a 5%
   margin and rounded upward to the next 10 cm. The world half-size is 2500 cm.
6. Summary evidence is stored in
   `smoke_run_r1060/step11_smoke_run_summary.json`.

The smoke run proved the interface route, not the final physics rate. It used a
mass-equivalent annulus and low statistics.

Full-particle transport closure performed on 2026-06-16:

1. `build_step11_production_inputs.py` migrated the full-sphere EXPACS/PARMA
   production source cards to the detector-plus-upstream-lens geometry and the
   1060 cm source surface.
2. The prompt transport run
   `runs/step11_upstream_optics_fullstat_instant_r1060/` completed 68/68 jobs
   with zero failures, generating 25,210,216 requested primary particles.
3. The activation-production run
   `runs/step11_upstream_optics_fullstat_buildup_r1060/` completed 68/68 jobs
   with zero failures, generating 25,210,216 requested primary particles and
   writing isotope inventory files.
4. Both runs use the same eight EXPACS/PARMA particle families as the detector
   background chain: gamma, neutron, electron, positron, proton, alpha,
   negative muon, and positive muon.
5. The production evidence closes the full-particle prompt and activation-
   production transport boundary. The combined prompt SIM still mixes ordinary
   detector/cryostat atmospheric background with any upstream-hardware prompt
   self-background, so a selected-rate prompt contribution requires provenance
   isolation or an explicit subtraction strategy before it can be merged into
   the primary W2 sensitivity budget.

Ge-proxy delayed selected-rate closure performed on 2026-06-16:

1. `build_step11_ge_proxy_delayed_source.py` extracted only the isotope
   inventory produced in `Step11_Laue_Ge_Annulus_Proxy`. Detector/cryostat
   isotope records in the combined geometry were intentionally excluded to avoid
   double-counting the baseline detector delayed background.
2. The target inventory contains two positive true-RPIP production records,
   `Ga-70` and `Ga-73`, from the `muminus` buildup stream. The day-15 Ge-proxy
   activity is `0.42567438 Bq`.
3. Because the target inventory is this small, the delayed source uses all
   true production positions directly: two equal-flux point-source support
   blocks, no M-sampling approximation.
4. The delayed decay transport used 20,000 triggers and naturally completed as
   `DelayedDecayStep11GeProxyExactpos.inc2.id1.sim.gz`, with `SE=ID=20000` and
   `TE=23900.760455 s`.
5. The common detector-level response found zero W2 events before and after the
   active-veto and side-entry Compton/FoV selections. The direct selected W2
   Ge-proxy delayed rate is therefore zero in this transport; the 95% zero-count
   upper rate is `1.2534045848433615e-4 s^-1`.
6. Compared with the current primary exact-position W2 background
   `0.0624651 s^-1`, this 95% upper limit is about 0.20%. It is below the
   exact-position support-size convergence scale, so it does not change the
   quoted primary hard-window sensitivity at the current precision.

Remaining closure gates:

1. Isolate prompt self-background from the combined prompt SIM, or define an
   explicit subtraction strategy against the ordinary detector/cryostat prompt
   background.
2. Optionally run a longer Ge-proxy delayed transport if a tighter zero-count
   upper limit is needed.
3. Replace or bracket the equal-mass active-Ge proxy with explicit lens
   tile/support hardware before making a final flight-design background claim.
4. If a conservative upper-limit variant is desired, merge it as a sidecar line
   item at the selected-rate level, not as the primary background authority.

Until these remaining gates pass, the full optics-hardware self-background budget
must remain outside the primary background budget. The current Step11 evidence can
be cited as full-particle prompt/activation-production transport closure plus a
closed delayed selected-rate side component for the equal-mass active-Ge proxy.

# SH3 OptV3 corrected-keV / PARMA511 transport

Status: `SMOKE_AUTHORIZED__PRODUCTION_REQUIRES_SMOKE_AND_RESOURCE_GATE`

This non-overwriting package prepares SH3 OptV3 transport inputs while reusing
the canonical guarded executor and terminal dashboard at:

`/home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute/`

It does not copy or fork the multiprocessing controller.

## Scope

- Current frozen geometry: `SH3_Assembly_OptV3.geo.setup`.
- Broadband background: all eight corrected-keV families, with the retained
  `unit_only_total_gamma` profile and 20 equal-mu angular cells.
- Production accepted targets: 22 INSTANT jobs / 3,842,079 primaries and
  19 BUILDUP jobs / 3,045,028 primaries. The missing SG3B initial 1,448-event
  alpha BUILDUP cell is deliberately absent.
- Atmospheric annihilation line: standalone PARMA 510.99895-keV, 80-bin,
  0.16651547160226118 ph cm^-2 s^-1 sidecar, 13 jobs / 3,000,000 photons.
- The PARMA branch is `NON_ADDITIVE_SIDECAR`; it must not be added directly to
  broadband gamma, which already contains the retained annihilation bump.
- Detector veto, response, Step05, delayed-source construction, and paper
  updates are outside this transport package.

## Smoke

The smoke is one umbrella gate with two receipt-bound profiles:

- corrected-keV: 16 jobs, one per `mode x family`, 2,376 primaries total;
- PARMA511: one 1,000-photon job.

The corrected-keV family counts per mode are gamma 1,000; n 96; eminus 41;
eplus 24; p 23; alpha 2; muminus 1; and muplus 1. These are the retained
mergeable-smoke counts. The smoke uses the production source physics and only
reduces event counts.

## Workflow

```bash
python3 prepare_optv3_transport.py --kind smoke --output-root <new-root>
python3 /home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute/run.py \
  --config <new-root>/corrected_kev/config.json --workers 6
python3 /home/ubuntu/.codex/worktrees/8633/TES_511_Balloon/tool/execute/progress.py \
  --config <new-root>/corrected_kev/config.json
```

Run the PARMA profile with its sibling config. Production preparation is:

```bash
python3 prepare_optv3_transport.py --kind production --output-root <new-root>
```

Production must not start unless both smoke profiles PASS and the smoke-scaled
artifact upper bound plus the configured reserve fits the destination disk.


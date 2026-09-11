# Laue 511 Cross-Check Summary

Status: `crosscheck_pass_external_lens_observables_imported`
Production validation ready: `False`

## Checks

| check | ok | key evidence |
|---|---:|---|
| `historical_probability_kernel` | `True` | rows=100000, max probability delta=5.14e-11, max |z|=1.36 |
| `rebuilt_probability_kernel_and_vectors` | `True` | rows=5000, max probability delta=5.09e-11, max |z|=1.26 |
| `focal_convention` | `True` | max p_diff shift=4.13e-05, max angle=0.35 arcsec |
| `external_lens_handoff` | `True` | rows=2, import=True, tmp removed=True |
| `full_lens_observables` | `True` | phase hit delta=1.4e-08 mm, spot d90=0.219 cm, Aeff delta=0.00262 cm2 |
| `python_full_lens_reference` | `True` | Aeff ref=0.567 cm2, delta=0.00164 cm2, max |z|=1.24 |
| `cosima_bridge_diffract` | `True` | 24675/24675 rows joined |
| `cosima_bridge_transmit` | `True` | 39560/39560 rows joined |
| `pytte_check` | `True` | cases=4 |
| `kohnle1998_check` | `True` | endpoint max abs error=0.0135 |
| `opticsim_table_lens_closure` | `True` | delta diff frac=0.00037, max per-ring p_diff delta=0.000631, spot d90 delta=-0.00117 cm |
| `crystalpy_curve` | `True` | rows=101, peak=0.571, flux residual=9e-13 |
| `xop_crystal_curve` | `True` | rows=101, peak=0.257, flux residual=0 |
| `external_lens_import_ready` | `True` | ready |
| `external_lens_request_ready` | `True` | ready |
| `external_lens_curve` | `True` | Aeff=0.583 cm2, spot d90=0.222 cm, delta Aeff=0.0146 cm2 |
| `bfull_offaxis_scan` | `True` | n/offset=1000, obs peak/min=23.9, ring2 obs=16, ring2 XOP=24.7, all G4VEm=True, trans rows=True |
| `bfull_single_tile_xop_scan` | `True` | ring/tile=2/0, n/offset=5000, XOP peak=0.257, obs peak=0.213, max p delta=6.76e-11, all G4VEm=True, trans rows=True |
| `bfull_rocking_curve_map_status` | `True` | status=ready, covered=[0, 1, 2, 3, 4], missing=[] |
| `bfull_full_lens_xop_map_scan` | `True` | n/offset=5000, obs peak/min=27.3, max p delta=7.27e-11, all external=True, all G4VEm=True, trans rows=True |

## Interpretation

The current package passes the internal Geant4/Python kernel checks, focal convention audit, external lens handoff audit, full-lens observable audit, Python-only full-lens reference check, bridge provenance audit, a five-ring opticsim table-vs-online closure check, imported single-crystal/XOP-CRYSTAL checks, external full-lens import/request readiness checks, and an imported HEART-derived full-lens detector-image check.
The production validation flag remains false because this repository is a cross-check package; the imported HEART route validates the current package observables but does not turn this directory into the final production validation record.

# S3 vs Mass_model_511 20d 3sigma with ATM511 Sidecar

Status: `PASS_S3_VS_MASS511_20D3SIGMA_WITH_RETAINED_ATM511_SIDECARS`

ATM511 sidecar rates are added to the retained Step05 selected background rates; signal response is unchanged.

| window | S3 F3+ATM511 20d | Mass F3+ATM511 20d | Mass/S3 ratio | S3 reduction | S3 B base | S3 ATM511 | S3 B total | Mass B base | Mass ATM511 | Mass B total |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| w2_510p58_511p42 | 2.85291e-05 | 4.59705e-05 | 1.61136 | 37.940% | 0.0113513 | 0.0108831 | 0.0222344 | 0.0480735 | 0.00887975 | 0.0569533 |
| broad_480_550 | 3.53582e-05 | 5.41742e-05 | 1.53215 | 34.732% | 0.0191088 | 0.0151587 | 0.0342675 | 0.0685203 | 0.0108139 | 0.0793342 |

Best S3 window with ATM511: `w2_510p58_511p42`

Notes:
- S3 ATM511 uses the retained `PASS_S3_ATM511_4PI_SIDECAR_REPLAY` product.
- Mass_model_511 ATM511 uses retained scenario `Harris_Rc_11_13_total_disk_no_alt_scale` from the 2026-07-03 P2 transfer product.
- This is a retained-product recomputation. A strict matched-source comparison still needs the same 4pi sidecar transported through Mass_model_511.

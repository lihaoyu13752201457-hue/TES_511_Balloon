# O8 full-chain independent data validation

Status: `PASS_O8_FULLCHAIN_INDEPENDENT_VALIDATION`

This audit reloads the durable JSON/CSV products and independently reconstructs the 20-day reference fold; it does not import the production runner.

## Recomputed primary result

- Day-15 final background: `0.0061060796325 cps`
- Day-15 signal at the reference flux: `0.00118120553768 cps`
- 20-day central Z / F3: `19.255804314` / `1.55797179441e-05 ph cm^-2 s^-1`
- 20-day conservative-95 Z / F3: `6.87833676017` / `4.36151951351e-05 ph cm^-2 s^-1`

## Problems

- None.

Machine-readable audit: `engineering/geometry_optimization_20260704/43_geoopt_s3d_o8_fallback_20260712/data/s3d_o8_fullchain_independent_validation.json`

# Compact input snapshots

These are immutable, compact derived inputs copied into the TOOL for reproducible reuse. They are
not SIM payloads and the TOOL does not hash them.

| Snapshot | Original authority/source |
|---|---|
| `se3_geometry_mesh_products.npz` | `44_geoopt_se3_minimal_20260815/data/se3_geometry_mesh_products.npz` |
| `selected_delayed_event_origins.csv` | `48_se3_background_optimization_review_20260816/data/selected_delayed_event_origins.csv` |
| `activation_origin_by_volume.csv` | same SE3 review package |
| `activation_origin_by_parent.csv` | same SE3 review package |
| `activation_origin_by_incident_family.csv` | same SE3 review package |
| `sf3_background_routes_2d.json` | `49_sf3_plan1_transport_20260816/diagnostics/sf3_background_routes_2d/` |

The SE3 activation snapshots are used deliberately instead of SF3 delayed activation because
SF3's added passive W can perturb irradiation and suppress or redistribute MXC activation. SF3 is
used only for the retained prompt route mechanism evidence.


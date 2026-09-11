| component_id | family | kind | nominal | angular_domain | physical_flux_cm2_s | source_link_status | comparison_grade | note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| albedo_photons_continuum | gamma | continuum | True | earth_visible_cone | 0.7568194027630226 | match | B |  |
| atmospheric_511_line | gamma | mono | True | earth_visible_cone | 0.028207 | inline_mono | C | Line-resolved satellite component; the balloon broadband table cannot provide a line-only normalization. |
| cosmic_photons | gamma | continuum | True | unocculted_sky | 1.2235089686672167 | match | B |  |
| primary_alpha | alpha | continuum | True | unocculted_sky | 0.017755030668705027 | match | B |  |
| primary_electron | eminus | continuum | True | unocculted_sky | 0.0006419376852490416 | match | B |  |
| primary_positron | eplus | continuum | True | unocculted_sky | 4.1571911328815755e-05 | match | B |  |
| primary_proton | p | continuum | True | unocculted_sky | 0.09113187635181248 | match | B |  |
| secondary_electron | eminus | continuum | True | earthward_secondary_support | 0.06460216831003572 | match | B |  |
| secondary_positron | eplus | continuum | True | earthward_secondary_support | 0.21318715542311786 | match | B |  |
| secondary_proton | p | continuum | True | upward_secondary_hemisphere | 0.046913580599957344 | match | B |  |
| albedo_neutrons_10gv_proxy | n | continuum | False | earth_visible_cone | 0.039067890668122704 | mismatch | C | Upstream DC4 source card points to a missing 12.6-GV filename; the included 10-GV spectrum is retained only as a clearly labeled diagnostic proxy. |
| saa_protons_reference | p | time_dependent_reference | False | zenith_dependent_trapped_radiation |  | not_applicable | NA | Excluded from static nominal science. Requires orbit residence and shutdown/activation policy. |
| galactic_diffuse_directional | gamma | directional_energy_beam_function | False | galactic_sky_map |  | not_applicable | NA | Astrophysical sky component, intentionally not collapsed into the local environmental continuum comparison. |

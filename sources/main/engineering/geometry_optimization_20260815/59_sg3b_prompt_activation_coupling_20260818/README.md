# SG3B prompt/activation-to-TES coupling diagnostic

This package reuses the retained selected-event IA parent/child route method and
the exact inherited SE3 `y'=0` mesh section to diagnose the completed SG3B
transport.  It is a read-only, non-overwriting analysis of accepted SG3B SIM
files; it launches no transport, computes no large-payload hashes, and changes
neither geometry nor manuscript text.

The activation markers are exact-position delayed-source locations for events
that survive the shared measured W2 response.  They answer where the decaying
nuclide was sampled and how its decay products reached TES.  They are **not**
BUILDUP primary-particle production tracks.  Reconstructing those earlier
tracks would require a separate BUILDUP RP/IP-to-event lineage product.

The prompt route sample is statistically sparse: the final SG3B W2 selection
contains one prompt event.  Its route is direct mechanism evidence, not a
precise prompt-rate decomposition.


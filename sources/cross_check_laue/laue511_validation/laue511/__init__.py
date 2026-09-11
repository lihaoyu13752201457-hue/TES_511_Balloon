"""Small reference kernel for 511 keV Ge(111) Laue optics checks."""

from .bragg import bragg_angle_rad, ring_radius_mm, wavelength_A
from .probabilities import darwin_hamilton_mosaic_probabilities
from .rings import RingSpec, load_ring_config
from .sampling import sample_branch

__all__ = [
    "RingSpec",
    "bragg_angle_rad",
    "darwin_hamilton_mosaic_probabilities",
    "load_ring_config",
    "ring_radius_mm",
    "sample_branch",
    "wavelength_A",
]

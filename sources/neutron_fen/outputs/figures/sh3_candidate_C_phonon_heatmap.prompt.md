# SH3 candidate-C phonon heat-map prompt

- Generator: built-in `image_gen`
- Use case: `scientific-educational`
- Output: `sh3_candidate_C_phonon_heatmap.png`
- SHA-256: `58c5646ab315fef84ec25dff78d68dbde1f0206c4fb0a9327ff102c0b75c0e09`

## Prompt

Create a publication-quality, oblique top-down scientific visualization of the
SH3 detector: one 36 mm x 36 mm x 0.30 mm silicon substrate carrying a dense
array representing 376 square TES absorber pixels, each 1.5 mm x 1.5 mm. Keep
the silicon visibly continuous beneath and between pixels. Show a localized
athermal phonon energy cloud spreading anisotropically inside the substrate
from a neutron recoil, fading from white/yellow through orange, red, purple,
and blue. Show coupling into several nearby surface pixels while most pixels
remain cool. Highlight and label pixels `P231` and `P147` in gold.

Use a dark neutral scientific background, semi-transparent blue-gray silicon,
metallic cyan-gray pixels, crisp technical geometry, and controlled studio
lighting. Add readable Chinese callouts `Si 衬底`, `TES 像素阵列`, and
`中子反冲热点`, a color bar titled `相对声子能量密度` with endpoints `低` and
`高`, and the caption `候选 C，代表时刻 t ≈ 0.7 μs`. Include the dimensions
36 mm x 36 mm x 0.30 mm.

This is a schematic relative energy distribution only. Do not show absolute
temperature in kelvin, equations, people, logos, watermarks, extra detector
layers, uniformly hot pixels, artistic smoke, or excessive bloom.

## Interpretation boundary

This raster is a schematic communication figure constrained by the assessed
geometry and candidate-C timing. It is not a numerical FEniCS temperature
solution and its colors must not be read as calibrated temperature.

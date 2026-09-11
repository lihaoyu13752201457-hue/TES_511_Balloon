# SH3 + W-grid conditional Fmin approximation

+This is a **conditional approximation**, not a full W-grid background/signal closure.
+It freezes the SH3 non-line background, five-anchor timeline correction, signal
+effective area, atmospheric transmission, and accidental-survival response; only
+the matched PARMA monoenergetic 510.99895-keV template is replaced by the W-grid
+result. Per the requested assumption, no W-grid activation component near 511 keV
+is added.

+## 20-day result

+- Gaussian 3 sigma: `3.89014866215e-05 +/- 1.59685773931e-06 ph cm^-2 s^-1`
+- Poisson Asimov 3 sigma: `3.89907699742e-05 +/- 1.59688130485e-06 ph cm^-2 s^-1`
+- Old SH3 Gaussian 3 sigma: `4.18515771565e-05 ph cm^-2 s^-1`
+- Threshold reduction: `7.04894%`
+- Sensitivity improvement factor: `1.0758349`
+- Approximate cumulative background: `47351.8125955` counts

+The quoted uncertainty is statistical only and does not quantify the approximation
+error caused by freezing the W-grid broadband and signal responses.
+
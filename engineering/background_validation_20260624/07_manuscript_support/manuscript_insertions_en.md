# Candidate Manuscript Insertions

Do not insert automatically. These are suggestions only.

## Methods

As an engineering control on active-shield material assumptions, we generated a same-envelope BGO variant by replacing only the active-shield material assignments while preserving the detector segmentation, geometry envelope, source model, and Step05 selection. The BGO control used the same atmospheric source tables, far-field radius, statistics matrix, delayed-source construction workflow, focused EventList signal replay, and `50 keV` / `1 us` post-processing veto definition as the fix5 authority chain.

## Results/Validation

The BGO control run completed the staged P0/P1/P2 workflow. In the W2 line window (`510.58-511.42 keV`) after active-veto and side-entry Compton/FoV selection, the BGO P2 background rate was `0.03749 cps`, compared with `0.03922 cps` for the current fix5 authority. The BGO reference-flux signal rate was `0.0011806 cps`, within 1% of the fix5 value. The BGO-minus-fix5 background difference corresponds to only `0.24 sigma` under a simple independent-sample Poisson approximation, so no material preference is inferred.

## Discussion

This material-control branch did not reveal a hidden large material-driven contribution to the selected 511 keV background. Because the BGO/fix5 difference is not statistically resolved and the BGO selected-event source-origin decomposition was not promoted to manuscript authority, the BGO run is treated as an engineering validation rather than a design-selection result.

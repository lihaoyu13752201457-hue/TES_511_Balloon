Name SH3_Chimney_Component_Standalone
Version 1

Include Materials_SH3.geo
AbsorptionFileDirectory crossections

Volume WorldVolume
WorldVolume.Visibility 0
WorldVolume.Material Vacuum
WorldVolume.Shape BRIK 30 30 30
WorldVolume.Mother 0

// Production merge replaces this placement only; component internals stay local.
Volume SH3_ChimneyFrame
SH3_ChimneyFrame.Visibility 0
SH3_ChimneyFrame.Material Vacuum
SH3_ChimneyFrame.Shape BRIK 12.000000 12.000000 12.000000
SH3_ChimneyFrame.Position 0 0 0
SH3_ChimneyFrame.Mother WorldVolume

Include SH3_Chimney_Component.geo

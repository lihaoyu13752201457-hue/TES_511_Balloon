Name Massmodel_DEMO2_DR_v3p5_minpatch_centerfinger_megalib_proxy_prompt511_inner_csi_shroud_r11p6_12p8
Version 1

Include Materials_DEMO2_DR_v3p5.geo
AbsorptionFileDirectory crossections

Volume WorldVolume
WorldVolume.Visibility 0
WorldVolume.Material Vacuum
WorldVolume.Shape BRIK 1000 1000 1000
WorldVolume.Mother 0

Volume InstrumentFrame
InstrumentFrame.Visibility 0
InstrumentFrame.Material Vacuum
InstrumentFrame.Shape BRIK 80 80 80
InstrumentFrame.Position 0 0 0
InstrumentFrame.Rotation 0 45 0
InstrumentFrame.Mother WorldVolume

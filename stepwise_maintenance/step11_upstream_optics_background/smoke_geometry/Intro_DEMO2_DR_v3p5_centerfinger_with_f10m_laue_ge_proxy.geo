Name Massmodel_DEMO2_DR_v3p5_centerfinger_with_f10m_laue_ge_proxy
Version 1

Include Materials_DEMO2_DR_v3p5.geo
AbsorptionFileDirectory crossections

Volume WorldVolume
WorldVolume.Visibility 0
WorldVolume.Material Vacuum
WorldVolume.Shape BRIK 2500 2500 2500
WorldVolume.Mother 0

Volume InstrumentFrame
InstrumentFrame.Visibility 0
InstrumentFrame.Material Vacuum
InstrumentFrame.Shape BRIK 80 80 80
InstrumentFrame.Position 0 0 0
InstrumentFrame.Rotation 0 45 0
InstrumentFrame.Mother WorldVolume

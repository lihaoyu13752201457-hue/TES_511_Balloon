// f10m Ge(111) MULTIBAND lens + support MASS PROXY (design-stage).
// Local coordinate: focused beam along +x, lens plane at x=0.
// Ge = equal-volume annulus over the 6-ring tile band (mass proxy,
// NOT the optical tile geometry). Support scaled from project OF1 model.

Volume MB_GeActiveMass_EqualVolumeAnnulus
MB_GeActiveMass_EqualVolumeAnnulus.Material GeProxy
MB_GeActiveMass_EqualVolumeAnnulus.Visibility 1
MB_GeActiveMass_EqualVolumeAnnulus.Shape PCON 0 360 2 -0.366441 6.778550 8.526019 0.366441 6.778550 8.526019
MB_GeActiveMass_EqualVolumeAnnulus.Rotation 0 90 0
MB_GeActiveMass_EqualVolumeAnnulus.Position 0 0 0
MB_GeActiveMass_EqualVolumeAnnulus.Mother InstrumentFrame

Volume MB_LensCarrier_G10_Annulus
MB_LensCarrier_G10_Annulus.Material G10
MB_LensCarrier_G10_Annulus.Visibility 1
MB_LensCarrier_G10_Annulus.Shape PCON 0 360 2 -0.050000 5.500000 8.800000 0.050000 5.500000 8.800000
MB_LensCarrier_G10_Annulus.Rotation 0 90 0
MB_LensCarrier_G10_Annulus.Position 0.70 0 0
MB_LensCarrier_G10_Annulus.Mother InstrumentFrame

Volume MB_LensOuterMount_Al_Annulus
MB_LensOuterMount_Al_Annulus.Material Aluminium
MB_LensOuterMount_Al_Annulus.Visibility 1
MB_LensOuterMount_Al_Annulus.Shape PCON 0 360 2 -0.250000 8.800000 11.500000 0.250000 8.800000 11.500000
MB_LensOuterMount_Al_Annulus.Rotation 0 90 0
MB_LensOuterMount_Al_Annulus.Position 0 0 0
MB_LensOuterMount_Al_Annulus.Mother InstrumentFrame

Volume MB_LensMountBracket_Al
MB_LensMountBracket_Al.Material Aluminium
MB_LensMountBracket_Al.Visibility 1
MB_LensMountBracket_Al.Shape BRIK 0.5 1.0 2.0
MB_LensMountBracket_Al.Copy MB_LensMountBracket_YP
MB_LensMountBracket_YP.Position 0 15.0 0.0
MB_LensMountBracket_YP.Mother InstrumentFrame
MB_LensMountBracket_Al.Copy MB_LensMountBracket_YM
MB_LensMountBracket_YM.Position 0 -15.0 0.0
MB_LensMountBracket_YM.Mother InstrumentFrame
MB_LensMountBracket_Al.Copy MB_LensMountBracket_ZP
MB_LensMountBracket_ZP.Position 0 0.0 15.0
MB_LensMountBracket_ZP.Mother InstrumentFrame
MB_LensMountBracket_Al.Copy MB_LensMountBracket_ZM
MB_LensMountBracket_ZM.Position 0 0.0 -15.0
MB_LensMountBracket_ZM.Mother InstrumentFrame

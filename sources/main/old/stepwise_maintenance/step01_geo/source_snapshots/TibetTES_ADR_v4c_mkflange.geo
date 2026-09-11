Include Intro_TibetTES.geo

// NEW_GEO_RE ADR v4c: Be-window-matched apertures plus added thin Al windows; internal W baffle removed.

// Volume ColdPlate_50mK; material=Copper
Volume ColdPlate_50mK
ColdPlate_50mK.Material Copper
ColdPlate_50mK.Visibility 1
ColdPlate_50mK.Shape PCON 0 360 2 -2.5 0 45 2.5 0 45

// Volume ColdPlate_1K; material=Copper
Volume ColdPlate_1K
ColdPlate_1K.Material Copper
ColdPlate_1K.Visibility 1
ColdPlate_1K.Shape PCON 0 360 2 -2.5 0 55 2.5 0 55

// Volume ColdPlate_4K; material=Copper
Volume ColdPlate_4K
ColdPlate_4K.Material Copper
ColdPlate_4K.Visibility 1
ColdPlate_4K.Shape PCON 0 360 2 -3 0 70 3 0 70

// Volume ColdPlate_50K; material=Aluminium
Volume ColdPlate_50K
ColdPlate_50K.Material Aluminium
ColdPlate_50K.Visibility 1
ColdPlate_50K.Shape PCON 0 360 2 -3 0 85 3 0 85

// Volume Substrate_L0; material=Silicon
Volume Substrate_L0
Substrate_L0.Material Silicon
Substrate_L0.Visibility 1
Substrate_L0.Shape PCON 0 360 2 -0.15 0 22 0.15 0 22

// Volume TES_Pixel_L0; material=Ta
Volume TES_Pixel_L0
TES_Pixel_L0.Material Ta
TES_Pixel_L0.Visibility 1
TES_Pixel_L0.Shape BRIK 0.75 0.75 1.5

// Volume TES_L0; material=Vacuum
Volume TES_L0
TES_L0.Material Vacuum
TES_L0.Visibility 0
TES_L0.Shape BRIK 24 24 1.6

// Volume Substrate_L1; material=Silicon
Volume Substrate_L1
Substrate_L1.Material Silicon
Substrate_L1.Visibility 1
Substrate_L1.Shape PCON 0 360 2 -0.15 0 22 0.15 0 22

// Volume TES_Pixel_L1; material=Ta
Volume TES_Pixel_L1
TES_Pixel_L1.Material Ta
TES_Pixel_L1.Visibility 1
TES_Pixel_L1.Shape BRIK 0.75 0.75 1.5

// Volume TES_L1; material=Vacuum
Volume TES_L1
TES_L1.Material Vacuum
TES_L1.Visibility 0
TES_L1.Shape BRIK 24 24 1.6

// Volume Substrate_L2; material=Silicon
Volume Substrate_L2
Substrate_L2.Material Silicon
Substrate_L2.Visibility 1
Substrate_L2.Shape PCON 0 360 2 -0.15 0 22 0.15 0 22

// Volume TES_Pixel_L2; material=Ta
Volume TES_Pixel_L2
TES_Pixel_L2.Material Ta
TES_Pixel_L2.Visibility 1
TES_Pixel_L2.Shape BRIK 0.75 0.75 1.5

// Volume TES_L2; material=Vacuum
Volume TES_L2
TES_L2.Material Vacuum
TES_L2.Visibility 0
TES_L2.Shape BRIK 24 24 1.6

// Volume Substrate_L3; material=Silicon
Volume Substrate_L3
Substrate_L3.Material Silicon
Substrate_L3.Visibility 1
Substrate_L3.Shape PCON 0 360 2 -0.15 0 22 0.15 0 22

// Volume TES_Pixel_L3; material=Ta
Volume TES_Pixel_L3
TES_Pixel_L3.Material Ta
TES_Pixel_L3.Visibility 1
TES_Pixel_L3.Shape BRIK 0.75 0.75 1.5

// Volume TES_L3; material=Vacuum
Volume TES_L3
TES_L3.Material Vacuum
TES_L3.Visibility 0
TES_L3.Shape BRIK 24 24 1.6

// Volume Substrate_L4; material=Silicon
Volume Substrate_L4
Substrate_L4.Material Silicon
Substrate_L4.Visibility 1
Substrate_L4.Shape PCON 0 360 2 -0.15 0 22 0.15 0 22

// Volume TES_Pixel_L4; material=Ta
Volume TES_Pixel_L4
TES_Pixel_L4.Material Ta
TES_Pixel_L4.Visibility 1
TES_Pixel_L4.Shape BRIK 0.75 0.75 1.5

// Volume TES_L4; material=Vacuum
Volume TES_L4
TES_L4.Material Vacuum
TES_L4.Visibility 0
TES_L4.Shape BRIK 24 24 1.6

// Volume Substrate_L5; material=Silicon
Volume Substrate_L5
Substrate_L5.Material Silicon
Substrate_L5.Visibility 1
Substrate_L5.Shape PCON 0 360 2 -0.15 0 22 0.15 0 22

// Volume TES_Pixel_L5; material=Ta
Volume TES_Pixel_L5
TES_Pixel_L5.Material Ta
TES_Pixel_L5.Visibility 1
TES_Pixel_L5.Shape BRIK 0.75 0.75 1.5

// Volume TES_L5; material=Vacuum
Volume TES_L5
TES_L5.Material Vacuum
TES_L5.Visibility 0
TES_L5.Shape BRIK 24 24 1.6

// Volume TES_SampleBox_Cu; material=Copper
Volume TES_SampleBox_Cu
TES_SampleBox_Cu.Material Copper
TES_SampleBox_Cu.Visibility 1
TES_SampleBox_Cu.Shape PCON 0 360 6 2.5 0 37 5.5 0 37 5.5 34 37 84 34 37 84 18.98 37 87 18.98 37

// Volume SampleBox_Al_Window; material=Aluminium
Volume SampleBox_Al_Window
SampleBox_Al_Window.Material Aluminium
SampleBox_Al_Window.Visibility 1
SampleBox_Al_Window.Shape PCON 0 360 2 -0.025 0 18.98 0.025 0 18.98

// Volume Nb_SC_Detector_Can; material=Nb
Volume Nb_SC_Detector_Can
Nb_SC_Detector_Can.Material Nb
Nb_SC_Detector_Can.Visibility 1
Nb_SC_Detector_Can.Shape PCON 0 360 4 -2.5 45.05 45.35 92 45.05 45.35 92 18.98 45.35 92.3 18.98 45.35

// Volume Win_Nb_SC_Detector_Can; material=Nb
Volume Win_Nb_SC_Detector_Can
Win_Nb_SC_Detector_Can.Material Nb
Win_Nb_SC_Detector_Can.Visibility 1
Win_Nb_SC_Detector_Can.Shape PCON 0 360 2 -0.025 0 18.98 0.025 0 18.98

// Volume Thermal_4K_Al_Shield; material=Aluminium
Volume Thermal_4K_Al_Shield
Thermal_4K_Al_Shield.Material Aluminium
Thermal_4K_Al_Shield.Visibility 1
Thermal_4K_Al_Shield.Shape PCON 0 360 6 -90.8 0 73.8 -90 0 73.8 -90 73 73.8 114 73 73.8 114 18.98 73.8 114.8 18.98 73.8

// Volume Thermal_50K_Al_Shield; material=Aluminium
Volume Thermal_50K_Al_Shield
Thermal_50K_Al_Shield.Material Aluminium
Thermal_50K_Al_Shield.Visibility 1
Thermal_50K_Al_Shield.Shape PCON 0 360 6 -124.8 0 88.8 -124 0 88.8 -124 88 88.8 122 88 88.8 122 18.98 88.8 122.8 18.98 88.8

// Volume Vacuum_Jacket_Al; material=Aluminium
Volume Vacuum_Jacket_Al
Vacuum_Jacket_Al.Material Aluminium
Vacuum_Jacket_Al.Visibility 1
Vacuum_Jacket_Al.Shape PCON 0 360 6 -134.5 0 95.5 -132 0 95.5 -132 93 95.5 126 93 95.5 126 18.98 95.5 128.5 18.98 95.5

// Volume Win_4K_Al_Shield; material=Aluminium
Volume Win_4K_Al_Shield
Win_4K_Al_Shield.Material Aluminium
Win_4K_Al_Shield.Visibility 1
Win_4K_Al_Shield.Shape PCON 0 360 2 -0.025 0 18.98 0.025 0 18.98

// Volume Win_50K_Al_Shield; material=Aluminium
Volume Win_50K_Al_Shield
Win_50K_Al_Shield.Material Aluminium
Win_50K_Al_Shield.Visibility 1
Win_50K_Al_Shield.Shape PCON 0 360 2 -0.025 0 18.98 0.025 0 18.98

// Volume CeBr3_Active_Shield; material=CeBr3
Volume CeBr3_Active_Shield
CeBr3_Active_Shield.Material CeBr3
CeBr3_Active_Shield.Visibility 1
CeBr3_Active_Shield.Shape PCON 0 360 6 -214.5 0 132.5 -139.5 0 132.5 -139.5 100.5 132.5 133.5 100.5 132.5 133.5 18.98 132.5 153.5 18.98 132.5

// Volume Outer_Al_Mech_Shell; material=Aluminium
Volume Outer_Al_Mech_Shell
Outer_Al_Mech_Shell.Material Aluminium
Outer_Al_Mech_Shell.Visibility 1
Outer_Al_Mech_Shell.Shape PCON 0 360 6 -218.5 0 136.5 -216.5 0 136.5 -216.5 134.5 136.5 155.5 134.5 136.5 155.5 18.98 136.5 157.5 18.98 136.5

// Volume Win_Be_Cryostat; material=Be
Volume Win_Be_Cryostat
Win_Be_Cryostat.Material Be
Win_Be_Cryostat.Visibility 1
Win_Be_Cryostat.Shape PCON 0 360 2 -0.075 0 18.98 0.075 0 18.98

// Volume CollimatorVac; material=Vacuum
Volume CollimatorVac
CollimatorVac.Material Vacuum
CollimatorVac.Visibility 0
CollimatorVac.Shape BRIK 32.55 32.55 0.5

CollimatorVac.Position 0 0 160
CollimatorVac.Mother WorldVolume
CollimatorVac.Visibility 0

// Volume CollBarX; material=W
Volume CollBarX
CollBarX.Material W
CollBarX.Visibility 1
CollBarX.Shape BRIK 32.55 0.065 0.5

// Volume CollBarY; material=W
Volume CollBarY
CollBarY.Material W
CollBarY.Visibility 1
CollBarY.Shape BRIK 0.065 32.55 0.5

CollBarX.Copy CollBarX_0000
CollBarX_0000.Position 0 -30.225 0
CollBarX_0000.Mother CollimatorVac
CollBarX_0000.Visibility 1

CollBarY.Copy CollBarY_0000
CollBarY_0000.Position -30.225 0 0
CollBarY_0000.Mother CollimatorVac
CollBarY_0000.Visibility 1

CollBarX.Copy CollBarX_0001
CollBarX_0001.Position 0 -28.675 0
CollBarX_0001.Mother CollimatorVac
CollBarX_0001.Visibility 1

CollBarY.Copy CollBarY_0001
CollBarY_0001.Position -28.675 0 0
CollBarY_0001.Mother CollimatorVac
CollBarY_0001.Visibility 1

CollBarX.Copy CollBarX_0002
CollBarX_0002.Position 0 -27.125 0
CollBarX_0002.Mother CollimatorVac
CollBarX_0002.Visibility 1

CollBarY.Copy CollBarY_0002
CollBarY_0002.Position -27.125 0 0
CollBarY_0002.Mother CollimatorVac
CollBarY_0002.Visibility 1

CollBarX.Copy CollBarX_0003
CollBarX_0003.Position 0 -25.575 0
CollBarX_0003.Mother CollimatorVac
CollBarX_0003.Visibility 1

CollBarY.Copy CollBarY_0003
CollBarY_0003.Position -25.575 0 0
CollBarY_0003.Mother CollimatorVac
CollBarY_0003.Visibility 1

CollBarX.Copy CollBarX_0004
CollBarX_0004.Position 0 -24.025 0
CollBarX_0004.Mother CollimatorVac
CollBarX_0004.Visibility 1

CollBarY.Copy CollBarY_0004
CollBarY_0004.Position -24.025 0 0
CollBarY_0004.Mother CollimatorVac
CollBarY_0004.Visibility 1

CollBarX.Copy CollBarX_0005
CollBarX_0005.Position 0 -22.475 0
CollBarX_0005.Mother CollimatorVac
CollBarX_0005.Visibility 1

CollBarY.Copy CollBarY_0005
CollBarY_0005.Position -22.475 0 0
CollBarY_0005.Mother CollimatorVac
CollBarY_0005.Visibility 1

CollBarX.Copy CollBarX_0006
CollBarX_0006.Position 0 -20.925 0
CollBarX_0006.Mother CollimatorVac
CollBarX_0006.Visibility 1

CollBarY.Copy CollBarY_0006
CollBarY_0006.Position -20.925 0 0
CollBarY_0006.Mother CollimatorVac
CollBarY_0006.Visibility 1

CollBarX.Copy CollBarX_0007
CollBarX_0007.Position 0 -19.375 0
CollBarX_0007.Mother CollimatorVac
CollBarX_0007.Visibility 1

CollBarY.Copy CollBarY_0007
CollBarY_0007.Position -19.375 0 0
CollBarY_0007.Mother CollimatorVac
CollBarY_0007.Visibility 1

CollBarX.Copy CollBarX_0008
CollBarX_0008.Position 0 -17.825 0
CollBarX_0008.Mother CollimatorVac
CollBarX_0008.Visibility 1

CollBarY.Copy CollBarY_0008
CollBarY_0008.Position -17.825 0 0
CollBarY_0008.Mother CollimatorVac
CollBarY_0008.Visibility 1

CollBarX.Copy CollBarX_0009
CollBarX_0009.Position 0 -16.275 0
CollBarX_0009.Mother CollimatorVac
CollBarX_0009.Visibility 1

CollBarY.Copy CollBarY_0009
CollBarY_0009.Position -16.275 0 0
CollBarY_0009.Mother CollimatorVac
CollBarY_0009.Visibility 1

CollBarX.Copy CollBarX_0010
CollBarX_0010.Position 0 -14.725 0
CollBarX_0010.Mother CollimatorVac
CollBarX_0010.Visibility 1

CollBarY.Copy CollBarY_0010
CollBarY_0010.Position -14.725 0 0
CollBarY_0010.Mother CollimatorVac
CollBarY_0010.Visibility 1

CollBarX.Copy CollBarX_0011
CollBarX_0011.Position 0 -13.175 0
CollBarX_0011.Mother CollimatorVac
CollBarX_0011.Visibility 1

CollBarY.Copy CollBarY_0011
CollBarY_0011.Position -13.175 0 0
CollBarY_0011.Mother CollimatorVac
CollBarY_0011.Visibility 1

CollBarX.Copy CollBarX_0012
CollBarX_0012.Position 0 -11.625 0
CollBarX_0012.Mother CollimatorVac
CollBarX_0012.Visibility 1

CollBarY.Copy CollBarY_0012
CollBarY_0012.Position -11.625 0 0
CollBarY_0012.Mother CollimatorVac
CollBarY_0012.Visibility 1

CollBarX.Copy CollBarX_0013
CollBarX_0013.Position 0 -10.075 0
CollBarX_0013.Mother CollimatorVac
CollBarX_0013.Visibility 1

CollBarY.Copy CollBarY_0013
CollBarY_0013.Position -10.075 0 0
CollBarY_0013.Mother CollimatorVac
CollBarY_0013.Visibility 1

CollBarX.Copy CollBarX_0014
CollBarX_0014.Position 0 -8.525 0
CollBarX_0014.Mother CollimatorVac
CollBarX_0014.Visibility 1

CollBarY.Copy CollBarY_0014
CollBarY_0014.Position -8.525 0 0
CollBarY_0014.Mother CollimatorVac
CollBarY_0014.Visibility 1

CollBarX.Copy CollBarX_0015
CollBarX_0015.Position 0 -6.975 0
CollBarX_0015.Mother CollimatorVac
CollBarX_0015.Visibility 1

CollBarY.Copy CollBarY_0015
CollBarY_0015.Position -6.975 0 0
CollBarY_0015.Mother CollimatorVac
CollBarY_0015.Visibility 1

CollBarX.Copy CollBarX_0016
CollBarX_0016.Position 0 -5.425 0
CollBarX_0016.Mother CollimatorVac
CollBarX_0016.Visibility 1

CollBarY.Copy CollBarY_0016
CollBarY_0016.Position -5.425 0 0
CollBarY_0016.Mother CollimatorVac
CollBarY_0016.Visibility 1

CollBarX.Copy CollBarX_0017
CollBarX_0017.Position 0 -3.875 0
CollBarX_0017.Mother CollimatorVac
CollBarX_0017.Visibility 1

CollBarY.Copy CollBarY_0017
CollBarY_0017.Position -3.875 0 0
CollBarY_0017.Mother CollimatorVac
CollBarY_0017.Visibility 1

CollBarX.Copy CollBarX_0018
CollBarX_0018.Position 0 -2.325 0
CollBarX_0018.Mother CollimatorVac
CollBarX_0018.Visibility 1

CollBarY.Copy CollBarY_0018
CollBarY_0018.Position -2.325 0 0
CollBarY_0018.Mother CollimatorVac
CollBarY_0018.Visibility 1

CollBarX.Copy CollBarX_0019
CollBarX_0019.Position 0 -0.775 0
CollBarX_0019.Mother CollimatorVac
CollBarX_0019.Visibility 1

CollBarY.Copy CollBarY_0019
CollBarY_0019.Position -0.775 0 0
CollBarY_0019.Mother CollimatorVac
CollBarY_0019.Visibility 1

CollBarX.Copy CollBarX_0020
CollBarX_0020.Position 0 0.775 0
CollBarX_0020.Mother CollimatorVac
CollBarX_0020.Visibility 1

CollBarY.Copy CollBarY_0020
CollBarY_0020.Position 0.775 0 0
CollBarY_0020.Mother CollimatorVac
CollBarY_0020.Visibility 1

CollBarX.Copy CollBarX_0021
CollBarX_0021.Position 0 2.325 0
CollBarX_0021.Mother CollimatorVac
CollBarX_0021.Visibility 1

CollBarY.Copy CollBarY_0021
CollBarY_0021.Position 2.325 0 0
CollBarY_0021.Mother CollimatorVac
CollBarY_0021.Visibility 1

CollBarX.Copy CollBarX_0022
CollBarX_0022.Position 0 3.875 0
CollBarX_0022.Mother CollimatorVac
CollBarX_0022.Visibility 1

CollBarY.Copy CollBarY_0022
CollBarY_0022.Position 3.875 0 0
CollBarY_0022.Mother CollimatorVac
CollBarY_0022.Visibility 1

CollBarX.Copy CollBarX_0023
CollBarX_0023.Position 0 5.425 0
CollBarX_0023.Mother CollimatorVac
CollBarX_0023.Visibility 1

CollBarY.Copy CollBarY_0023
CollBarY_0023.Position 5.425 0 0
CollBarY_0023.Mother CollimatorVac
CollBarY_0023.Visibility 1

CollBarX.Copy CollBarX_0024
CollBarX_0024.Position 0 6.975 0
CollBarX_0024.Mother CollimatorVac
CollBarX_0024.Visibility 1

CollBarY.Copy CollBarY_0024
CollBarY_0024.Position 6.975 0 0
CollBarY_0024.Mother CollimatorVac
CollBarY_0024.Visibility 1

CollBarX.Copy CollBarX_0025
CollBarX_0025.Position 0 8.525 0
CollBarX_0025.Mother CollimatorVac
CollBarX_0025.Visibility 1

CollBarY.Copy CollBarY_0025
CollBarY_0025.Position 8.525 0 0
CollBarY_0025.Mother CollimatorVac
CollBarY_0025.Visibility 1

CollBarX.Copy CollBarX_0026
CollBarX_0026.Position 0 10.075 0
CollBarX_0026.Mother CollimatorVac
CollBarX_0026.Visibility 1

CollBarY.Copy CollBarY_0026
CollBarY_0026.Position 10.075 0 0
CollBarY_0026.Mother CollimatorVac
CollBarY_0026.Visibility 1

CollBarX.Copy CollBarX_0027
CollBarX_0027.Position 0 11.625 0
CollBarX_0027.Mother CollimatorVac
CollBarX_0027.Visibility 1

CollBarY.Copy CollBarY_0027
CollBarY_0027.Position 11.625 0 0
CollBarY_0027.Mother CollimatorVac
CollBarY_0027.Visibility 1

CollBarX.Copy CollBarX_0028
CollBarX_0028.Position 0 13.175 0
CollBarX_0028.Mother CollimatorVac
CollBarX_0028.Visibility 1

CollBarY.Copy CollBarY_0028
CollBarY_0028.Position 13.175 0 0
CollBarY_0028.Mother CollimatorVac
CollBarY_0028.Visibility 1

CollBarX.Copy CollBarX_0029
CollBarX_0029.Position 0 14.725 0
CollBarX_0029.Mother CollimatorVac
CollBarX_0029.Visibility 1

CollBarY.Copy CollBarY_0029
CollBarY_0029.Position 14.725 0 0
CollBarY_0029.Mother CollimatorVac
CollBarY_0029.Visibility 1

CollBarX.Copy CollBarX_0030
CollBarX_0030.Position 0 16.275 0
CollBarX_0030.Mother CollimatorVac
CollBarX_0030.Visibility 1

CollBarY.Copy CollBarY_0030
CollBarY_0030.Position 16.275 0 0
CollBarY_0030.Mother CollimatorVac
CollBarY_0030.Visibility 1

CollBarX.Copy CollBarX_0031
CollBarX_0031.Position 0 17.825 0
CollBarX_0031.Mother CollimatorVac
CollBarX_0031.Visibility 1

CollBarY.Copy CollBarY_0031
CollBarY_0031.Position 17.825 0 0
CollBarY_0031.Mother CollimatorVac
CollBarY_0031.Visibility 1

CollBarX.Copy CollBarX_0032
CollBarX_0032.Position 0 19.375 0
CollBarX_0032.Mother CollimatorVac
CollBarX_0032.Visibility 1

CollBarY.Copy CollBarY_0032
CollBarY_0032.Position 19.375 0 0
CollBarY_0032.Mother CollimatorVac
CollBarY_0032.Visibility 1

CollBarX.Copy CollBarX_0033
CollBarX_0033.Position 0 20.925 0
CollBarX_0033.Mother CollimatorVac
CollBarX_0033.Visibility 1

CollBarY.Copy CollBarY_0033
CollBarY_0033.Position 20.925 0 0
CollBarY_0033.Mother CollimatorVac
CollBarY_0033.Visibility 1

CollBarX.Copy CollBarX_0034
CollBarX_0034.Position 0 22.475 0
CollBarX_0034.Mother CollimatorVac
CollBarX_0034.Visibility 1

CollBarY.Copy CollBarY_0034
CollBarY_0034.Position 22.475 0 0
CollBarY_0034.Mother CollimatorVac
CollBarY_0034.Visibility 1

CollBarX.Copy CollBarX_0035
CollBarX_0035.Position 0 24.025 0
CollBarX_0035.Mother CollimatorVac
CollBarX_0035.Visibility 1

CollBarY.Copy CollBarY_0035
CollBarY_0035.Position 24.025 0 0
CollBarY_0035.Mother CollimatorVac
CollBarY_0035.Visibility 1

CollBarX.Copy CollBarX_0036
CollBarX_0036.Position 0 25.575 0
CollBarX_0036.Mother CollimatorVac
CollBarX_0036.Visibility 1

CollBarY.Copy CollBarY_0036
CollBarY_0036.Position 25.575 0 0
CollBarY_0036.Mother CollimatorVac
CollBarY_0036.Visibility 1

CollBarX.Copy CollBarX_0037
CollBarX_0037.Position 0 27.125 0
CollBarX_0037.Mother CollimatorVac
CollBarX_0037.Visibility 1

CollBarY.Copy CollBarY_0037
CollBarY_0037.Position 27.125 0 0
CollBarY_0037.Mother CollimatorVac
CollBarY_0037.Visibility 1

CollBarX.Copy CollBarX_0038
CollBarX_0038.Position 0 28.675 0
CollBarX_0038.Mother CollimatorVac
CollBarX_0038.Visibility 1

CollBarY.Copy CollBarY_0038
CollBarY_0038.Position 28.675 0 0
CollBarY_0038.Mother CollimatorVac
CollBarY_0038.Visibility 1

CollBarX.Copy CollBarX_0039
CollBarX_0039.Position 0 30.225 0
CollBarX_0039.Mother CollimatorVac
CollBarX_0039.Visibility 1

CollBarY.Copy CollBarY_0039
CollBarY_0039.Position 30.225 0 0
CollBarY_0039.Mother CollimatorVac
CollBarY_0039.Visibility 1

ColdPlate_50mK.Position 0 0 0
ColdPlate_50mK.Mother WorldVolume

ColdPlate_1K.Position 0 0 -32
ColdPlate_1K.Mother WorldVolume

ColdPlate_4K.Position 0 0 -72
ColdPlate_4K.Mother WorldVolume

ColdPlate_50K.Position 0 0 -108
ColdPlate_50K.Mother WorldVolume

Substrate_L0.Position 0 0 10
Substrate_L0.Mother WorldVolume

TES_L0.Position 0 0 11.65
TES_L0.Mother WorldVolume
TES_L0.Visibility 0

TES_Pixel_L0.Copy TP_L0_00000
TP_L0_00000.Position -14.725 -10.075 0
TP_L0_00000.Mother TES_L0
TP_L0_00000.Visibility 0

TES_Pixel_L0.Copy TP_L0_00001
TP_L0_00001.Position -14.725 -8.525 0
TP_L0_00001.Mother TES_L0
TP_L0_00001.Visibility 0

TES_Pixel_L0.Copy TP_L0_00002
TP_L0_00002.Position -14.725 -6.975 0
TP_L0_00002.Mother TES_L0
TP_L0_00002.Visibility 0

TES_Pixel_L0.Copy TP_L0_00003
TP_L0_00003.Position -14.725 -5.425 0
TP_L0_00003.Mother TES_L0
TP_L0_00003.Visibility 0

TES_Pixel_L0.Copy TP_L0_00004
TP_L0_00004.Position -14.725 -3.875 0
TP_L0_00004.Mother TES_L0
TP_L0_00004.Visibility 0

TES_Pixel_L0.Copy TP_L0_00005
TP_L0_00005.Position -14.725 -2.325 0
TP_L0_00005.Mother TES_L0
TP_L0_00005.Visibility 0

TES_Pixel_L0.Copy TP_L0_00006
TP_L0_00006.Position -14.725 -0.775 0
TP_L0_00006.Mother TES_L0
TP_L0_00006.Visibility 0

TES_Pixel_L0.Copy TP_L0_00007
TP_L0_00007.Position -14.725 0.775 0
TP_L0_00007.Mother TES_L0
TP_L0_00007.Visibility 0

TES_Pixel_L0.Copy TP_L0_00008
TP_L0_00008.Position -14.725 2.325 0
TP_L0_00008.Mother TES_L0
TP_L0_00008.Visibility 0

TES_Pixel_L0.Copy TP_L0_00009
TP_L0_00009.Position -14.725 3.875 0
TP_L0_00009.Mother TES_L0
TP_L0_00009.Visibility 0

TES_Pixel_L0.Copy TP_L0_00010
TP_L0_00010.Position -14.725 5.425 0
TP_L0_00010.Mother TES_L0
TP_L0_00010.Visibility 0

TES_Pixel_L0.Copy TP_L0_00011
TP_L0_00011.Position -14.725 6.975 0
TP_L0_00011.Mother TES_L0
TP_L0_00011.Visibility 0

TES_Pixel_L0.Copy TP_L0_00012
TP_L0_00012.Position -14.725 8.525 0
TP_L0_00012.Mother TES_L0
TP_L0_00012.Visibility 0

TES_Pixel_L0.Copy TP_L0_00013
TP_L0_00013.Position -14.725 10.075 0
TP_L0_00013.Mother TES_L0
TP_L0_00013.Visibility 0

TES_Pixel_L0.Copy TP_L0_00014
TP_L0_00014.Position -13.175 -11.625 0
TP_L0_00014.Mother TES_L0
TP_L0_00014.Visibility 0

TES_Pixel_L0.Copy TP_L0_00015
TP_L0_00015.Position -13.175 -10.075 0
TP_L0_00015.Mother TES_L0
TP_L0_00015.Visibility 0

TES_Pixel_L0.Copy TP_L0_00016
TP_L0_00016.Position -13.175 -8.525 0
TP_L0_00016.Mother TES_L0
TP_L0_00016.Visibility 0

TES_Pixel_L0.Copy TP_L0_00017
TP_L0_00017.Position -13.175 -6.975 0
TP_L0_00017.Mother TES_L0
TP_L0_00017.Visibility 0

TES_Pixel_L0.Copy TP_L0_00018
TP_L0_00018.Position -13.175 -5.425 0
TP_L0_00018.Mother TES_L0
TP_L0_00018.Visibility 0

TES_Pixel_L0.Copy TP_L0_00019
TP_L0_00019.Position -13.175 -3.875 0
TP_L0_00019.Mother TES_L0
TP_L0_00019.Visibility 0

TES_Pixel_L0.Copy TP_L0_00020
TP_L0_00020.Position -13.175 -2.325 0
TP_L0_00020.Mother TES_L0
TP_L0_00020.Visibility 0

TES_Pixel_L0.Copy TP_L0_00021
TP_L0_00021.Position -13.175 -0.775 0
TP_L0_00021.Mother TES_L0
TP_L0_00021.Visibility 0

TES_Pixel_L0.Copy TP_L0_00022
TP_L0_00022.Position -13.175 0.775 0
TP_L0_00022.Mother TES_L0
TP_L0_00022.Visibility 0

TES_Pixel_L0.Copy TP_L0_00023
TP_L0_00023.Position -13.175 2.325 0
TP_L0_00023.Mother TES_L0
TP_L0_00023.Visibility 0

TES_Pixel_L0.Copy TP_L0_00024
TP_L0_00024.Position -13.175 3.875 0
TP_L0_00024.Mother TES_L0
TP_L0_00024.Visibility 0

TES_Pixel_L0.Copy TP_L0_00025
TP_L0_00025.Position -13.175 5.425 0
TP_L0_00025.Mother TES_L0
TP_L0_00025.Visibility 0

TES_Pixel_L0.Copy TP_L0_00026
TP_L0_00026.Position -13.175 6.975 0
TP_L0_00026.Mother TES_L0
TP_L0_00026.Visibility 0

TES_Pixel_L0.Copy TP_L0_00027
TP_L0_00027.Position -13.175 8.525 0
TP_L0_00027.Mother TES_L0
TP_L0_00027.Visibility 0

TES_Pixel_L0.Copy TP_L0_00028
TP_L0_00028.Position -13.175 10.075 0
TP_L0_00028.Mother TES_L0
TP_L0_00028.Visibility 0

TES_Pixel_L0.Copy TP_L0_00029
TP_L0_00029.Position -13.175 11.625 0
TP_L0_00029.Mother TES_L0
TP_L0_00029.Visibility 0

TES_Pixel_L0.Copy TP_L0_00030
TP_L0_00030.Position -11.625 -13.175 0
TP_L0_00030.Mother TES_L0
TP_L0_00030.Visibility 0

TES_Pixel_L0.Copy TP_L0_00031
TP_L0_00031.Position -11.625 -11.625 0
TP_L0_00031.Mother TES_L0
TP_L0_00031.Visibility 0

TES_Pixel_L0.Copy TP_L0_00032
TP_L0_00032.Position -11.625 -10.075 0
TP_L0_00032.Mother TES_L0
TP_L0_00032.Visibility 0

TES_Pixel_L0.Copy TP_L0_00033
TP_L0_00033.Position -11.625 -8.525 0
TP_L0_00033.Mother TES_L0
TP_L0_00033.Visibility 0

TES_Pixel_L0.Copy TP_L0_00034
TP_L0_00034.Position -11.625 -6.975 0
TP_L0_00034.Mother TES_L0
TP_L0_00034.Visibility 0

TES_Pixel_L0.Copy TP_L0_00035
TP_L0_00035.Position -11.625 -5.425 0
TP_L0_00035.Mother TES_L0
TP_L0_00035.Visibility 0

TES_Pixel_L0.Copy TP_L0_00036
TP_L0_00036.Position -11.625 -3.875 0
TP_L0_00036.Mother TES_L0
TP_L0_00036.Visibility 0

TES_Pixel_L0.Copy TP_L0_00037
TP_L0_00037.Position -11.625 -2.325 0
TP_L0_00037.Mother TES_L0
TP_L0_00037.Visibility 0

TES_Pixel_L0.Copy TP_L0_00038
TP_L0_00038.Position -11.625 -0.775 0
TP_L0_00038.Mother TES_L0
TP_L0_00038.Visibility 0

TES_Pixel_L0.Copy TP_L0_00039
TP_L0_00039.Position -11.625 0.775 0
TP_L0_00039.Mother TES_L0
TP_L0_00039.Visibility 0

TES_Pixel_L0.Copy TP_L0_00040
TP_L0_00040.Position -11.625 2.325 0
TP_L0_00040.Mother TES_L0
TP_L0_00040.Visibility 0

TES_Pixel_L0.Copy TP_L0_00041
TP_L0_00041.Position -11.625 3.875 0
TP_L0_00041.Mother TES_L0
TP_L0_00041.Visibility 0

TES_Pixel_L0.Copy TP_L0_00042
TP_L0_00042.Position -11.625 5.425 0
TP_L0_00042.Mother TES_L0
TP_L0_00042.Visibility 0

TES_Pixel_L0.Copy TP_L0_00043
TP_L0_00043.Position -11.625 6.975 0
TP_L0_00043.Mother TES_L0
TP_L0_00043.Visibility 0

TES_Pixel_L0.Copy TP_L0_00044
TP_L0_00044.Position -11.625 8.525 0
TP_L0_00044.Mother TES_L0
TP_L0_00044.Visibility 0

TES_Pixel_L0.Copy TP_L0_00045
TP_L0_00045.Position -11.625 10.075 0
TP_L0_00045.Mother TES_L0
TP_L0_00045.Visibility 0

TES_Pixel_L0.Copy TP_L0_00046
TP_L0_00046.Position -11.625 11.625 0
TP_L0_00046.Mother TES_L0
TP_L0_00046.Visibility 0

TES_Pixel_L0.Copy TP_L0_00047
TP_L0_00047.Position -11.625 13.175 0
TP_L0_00047.Mother TES_L0
TP_L0_00047.Visibility 0

TES_Pixel_L0.Copy TP_L0_00048
TP_L0_00048.Position -10.075 -14.725 0
TP_L0_00048.Mother TES_L0
TP_L0_00048.Visibility 0

TES_Pixel_L0.Copy TP_L0_00049
TP_L0_00049.Position -10.075 -13.175 0
TP_L0_00049.Mother TES_L0
TP_L0_00049.Visibility 0

TES_Pixel_L0.Copy TP_L0_00050
TP_L0_00050.Position -10.075 -11.625 0
TP_L0_00050.Mother TES_L0
TP_L0_00050.Visibility 0

TES_Pixel_L0.Copy TP_L0_00051
TP_L0_00051.Position -10.075 -10.075 0
TP_L0_00051.Mother TES_L0
TP_L0_00051.Visibility 0

TES_Pixel_L0.Copy TP_L0_00052
TP_L0_00052.Position -10.075 -8.525 0
TP_L0_00052.Mother TES_L0
TP_L0_00052.Visibility 0

TES_Pixel_L0.Copy TP_L0_00053
TP_L0_00053.Position -10.075 -6.975 0
TP_L0_00053.Mother TES_L0
TP_L0_00053.Visibility 0

TES_Pixel_L0.Copy TP_L0_00054
TP_L0_00054.Position -10.075 -5.425 0
TP_L0_00054.Mother TES_L0
TP_L0_00054.Visibility 0

TES_Pixel_L0.Copy TP_L0_00055
TP_L0_00055.Position -10.075 -3.875 0
TP_L0_00055.Mother TES_L0
TP_L0_00055.Visibility 0

TES_Pixel_L0.Copy TP_L0_00056
TP_L0_00056.Position -10.075 -2.325 0
TP_L0_00056.Mother TES_L0
TP_L0_00056.Visibility 0

TES_Pixel_L0.Copy TP_L0_00057
TP_L0_00057.Position -10.075 -0.775 0
TP_L0_00057.Mother TES_L0
TP_L0_00057.Visibility 0

TES_Pixel_L0.Copy TP_L0_00058
TP_L0_00058.Position -10.075 0.775 0
TP_L0_00058.Mother TES_L0
TP_L0_00058.Visibility 0

TES_Pixel_L0.Copy TP_L0_00059
TP_L0_00059.Position -10.075 2.325 0
TP_L0_00059.Mother TES_L0
TP_L0_00059.Visibility 0

TES_Pixel_L0.Copy TP_L0_00060
TP_L0_00060.Position -10.075 3.875 0
TP_L0_00060.Mother TES_L0
TP_L0_00060.Visibility 0

TES_Pixel_L0.Copy TP_L0_00061
TP_L0_00061.Position -10.075 5.425 0
TP_L0_00061.Mother TES_L0
TP_L0_00061.Visibility 0

TES_Pixel_L0.Copy TP_L0_00062
TP_L0_00062.Position -10.075 6.975 0
TP_L0_00062.Mother TES_L0
TP_L0_00062.Visibility 0

TES_Pixel_L0.Copy TP_L0_00063
TP_L0_00063.Position -10.075 8.525 0
TP_L0_00063.Mother TES_L0
TP_L0_00063.Visibility 0

TES_Pixel_L0.Copy TP_L0_00064
TP_L0_00064.Position -10.075 10.075 0
TP_L0_00064.Mother TES_L0
TP_L0_00064.Visibility 0

TES_Pixel_L0.Copy TP_L0_00065
TP_L0_00065.Position -10.075 11.625 0
TP_L0_00065.Mother TES_L0
TP_L0_00065.Visibility 0

TES_Pixel_L0.Copy TP_L0_00066
TP_L0_00066.Position -10.075 13.175 0
TP_L0_00066.Mother TES_L0
TP_L0_00066.Visibility 0

TES_Pixel_L0.Copy TP_L0_00067
TP_L0_00067.Position -10.075 14.725 0
TP_L0_00067.Mother TES_L0
TP_L0_00067.Visibility 0

TES_Pixel_L0.Copy TP_L0_00068
TP_L0_00068.Position -8.525 -14.725 0
TP_L0_00068.Mother TES_L0
TP_L0_00068.Visibility 0

TES_Pixel_L0.Copy TP_L0_00069
TP_L0_00069.Position -8.525 -13.175 0
TP_L0_00069.Mother TES_L0
TP_L0_00069.Visibility 0

TES_Pixel_L0.Copy TP_L0_00070
TP_L0_00070.Position -8.525 -11.625 0
TP_L0_00070.Mother TES_L0
TP_L0_00070.Visibility 0

TES_Pixel_L0.Copy TP_L0_00071
TP_L0_00071.Position -8.525 -10.075 0
TP_L0_00071.Mother TES_L0
TP_L0_00071.Visibility 0

TES_Pixel_L0.Copy TP_L0_00072
TP_L0_00072.Position -8.525 -8.525 0
TP_L0_00072.Mother TES_L0
TP_L0_00072.Visibility 0

TES_Pixel_L0.Copy TP_L0_00073
TP_L0_00073.Position -8.525 -6.975 0
TP_L0_00073.Mother TES_L0
TP_L0_00073.Visibility 0

TES_Pixel_L0.Copy TP_L0_00074
TP_L0_00074.Position -8.525 -5.425 0
TP_L0_00074.Mother TES_L0
TP_L0_00074.Visibility 0

TES_Pixel_L0.Copy TP_L0_00075
TP_L0_00075.Position -8.525 -3.875 0
TP_L0_00075.Mother TES_L0
TP_L0_00075.Visibility 0

TES_Pixel_L0.Copy TP_L0_00076
TP_L0_00076.Position -8.525 -2.325 0
TP_L0_00076.Mother TES_L0
TP_L0_00076.Visibility 0

TES_Pixel_L0.Copy TP_L0_00077
TP_L0_00077.Position -8.525 -0.775 0
TP_L0_00077.Mother TES_L0
TP_L0_00077.Visibility 0

TES_Pixel_L0.Copy TP_L0_00078
TP_L0_00078.Position -8.525 0.775 0
TP_L0_00078.Mother TES_L0
TP_L0_00078.Visibility 0

TES_Pixel_L0.Copy TP_L0_00079
TP_L0_00079.Position -8.525 2.325 0
TP_L0_00079.Mother TES_L0
TP_L0_00079.Visibility 0

TES_Pixel_L0.Copy TP_L0_00080
TP_L0_00080.Position -8.525 3.875 0
TP_L0_00080.Mother TES_L0
TP_L0_00080.Visibility 0

TES_Pixel_L0.Copy TP_L0_00081
TP_L0_00081.Position -8.525 5.425 0
TP_L0_00081.Mother TES_L0
TP_L0_00081.Visibility 0

TES_Pixel_L0.Copy TP_L0_00082
TP_L0_00082.Position -8.525 6.975 0
TP_L0_00082.Mother TES_L0
TP_L0_00082.Visibility 0

TES_Pixel_L0.Copy TP_L0_00083
TP_L0_00083.Position -8.525 8.525 0
TP_L0_00083.Mother TES_L0
TP_L0_00083.Visibility 0

TES_Pixel_L0.Copy TP_L0_00084
TP_L0_00084.Position -8.525 10.075 0
TP_L0_00084.Mother TES_L0
TP_L0_00084.Visibility 0

TES_Pixel_L0.Copy TP_L0_00085
TP_L0_00085.Position -8.525 11.625 0
TP_L0_00085.Mother TES_L0
TP_L0_00085.Visibility 0

TES_Pixel_L0.Copy TP_L0_00086
TP_L0_00086.Position -8.525 13.175 0
TP_L0_00086.Mother TES_L0
TP_L0_00086.Visibility 0

TES_Pixel_L0.Copy TP_L0_00087
TP_L0_00087.Position -8.525 14.725 0
TP_L0_00087.Mother TES_L0
TP_L0_00087.Visibility 0

TES_Pixel_L0.Copy TP_L0_00088
TP_L0_00088.Position -6.975 -14.725 0
TP_L0_00088.Mother TES_L0
TP_L0_00088.Visibility 0

TES_Pixel_L0.Copy TP_L0_00089
TP_L0_00089.Position -6.975 -13.175 0
TP_L0_00089.Mother TES_L0
TP_L0_00089.Visibility 0

TES_Pixel_L0.Copy TP_L0_00090
TP_L0_00090.Position -6.975 -11.625 0
TP_L0_00090.Mother TES_L0
TP_L0_00090.Visibility 0

TES_Pixel_L0.Copy TP_L0_00091
TP_L0_00091.Position -6.975 -10.075 0
TP_L0_00091.Mother TES_L0
TP_L0_00091.Visibility 0

TES_Pixel_L0.Copy TP_L0_00092
TP_L0_00092.Position -6.975 -8.525 0
TP_L0_00092.Mother TES_L0
TP_L0_00092.Visibility 0

TES_Pixel_L0.Copy TP_L0_00093
TP_L0_00093.Position -6.975 -6.975 0
TP_L0_00093.Mother TES_L0
TP_L0_00093.Visibility 0

TES_Pixel_L0.Copy TP_L0_00094
TP_L0_00094.Position -6.975 -5.425 0
TP_L0_00094.Mother TES_L0
TP_L0_00094.Visibility 0

TES_Pixel_L0.Copy TP_L0_00095
TP_L0_00095.Position -6.975 -3.875 0
TP_L0_00095.Mother TES_L0
TP_L0_00095.Visibility 0

TES_Pixel_L0.Copy TP_L0_00096
TP_L0_00096.Position -6.975 -2.325 0
TP_L0_00096.Mother TES_L0
TP_L0_00096.Visibility 0

TES_Pixel_L0.Copy TP_L0_00097
TP_L0_00097.Position -6.975 -0.775 0
TP_L0_00097.Mother TES_L0
TP_L0_00097.Visibility 0

TES_Pixel_L0.Copy TP_L0_00098
TP_L0_00098.Position -6.975 0.775 0
TP_L0_00098.Mother TES_L0
TP_L0_00098.Visibility 0

TES_Pixel_L0.Copy TP_L0_00099
TP_L0_00099.Position -6.975 2.325 0
TP_L0_00099.Mother TES_L0
TP_L0_00099.Visibility 0

TES_Pixel_L0.Copy TP_L0_00100
TP_L0_00100.Position -6.975 3.875 0
TP_L0_00100.Mother TES_L0
TP_L0_00100.Visibility 0

TES_Pixel_L0.Copy TP_L0_00101
TP_L0_00101.Position -6.975 5.425 0
TP_L0_00101.Mother TES_L0
TP_L0_00101.Visibility 0

TES_Pixel_L0.Copy TP_L0_00102
TP_L0_00102.Position -6.975 6.975 0
TP_L0_00102.Mother TES_L0
TP_L0_00102.Visibility 0

TES_Pixel_L0.Copy TP_L0_00103
TP_L0_00103.Position -6.975 8.525 0
TP_L0_00103.Mother TES_L0
TP_L0_00103.Visibility 0

TES_Pixel_L0.Copy TP_L0_00104
TP_L0_00104.Position -6.975 10.075 0
TP_L0_00104.Mother TES_L0
TP_L0_00104.Visibility 0

TES_Pixel_L0.Copy TP_L0_00105
TP_L0_00105.Position -6.975 11.625 0
TP_L0_00105.Mother TES_L0
TP_L0_00105.Visibility 0

TES_Pixel_L0.Copy TP_L0_00106
TP_L0_00106.Position -6.975 13.175 0
TP_L0_00106.Mother TES_L0
TP_L0_00106.Visibility 0

TES_Pixel_L0.Copy TP_L0_00107
TP_L0_00107.Position -6.975 14.725 0
TP_L0_00107.Mother TES_L0
TP_L0_00107.Visibility 0

TES_Pixel_L0.Copy TP_L0_00108
TP_L0_00108.Position -5.425 -14.725 0
TP_L0_00108.Mother TES_L0
TP_L0_00108.Visibility 0

TES_Pixel_L0.Copy TP_L0_00109
TP_L0_00109.Position -5.425 -13.175 0
TP_L0_00109.Mother TES_L0
TP_L0_00109.Visibility 0

TES_Pixel_L0.Copy TP_L0_00110
TP_L0_00110.Position -5.425 -11.625 0
TP_L0_00110.Mother TES_L0
TP_L0_00110.Visibility 0

TES_Pixel_L0.Copy TP_L0_00111
TP_L0_00111.Position -5.425 -10.075 0
TP_L0_00111.Mother TES_L0
TP_L0_00111.Visibility 0

TES_Pixel_L0.Copy TP_L0_00112
TP_L0_00112.Position -5.425 -8.525 0
TP_L0_00112.Mother TES_L0
TP_L0_00112.Visibility 0

TES_Pixel_L0.Copy TP_L0_00113
TP_L0_00113.Position -5.425 -6.975 0
TP_L0_00113.Mother TES_L0
TP_L0_00113.Visibility 0

TES_Pixel_L0.Copy TP_L0_00114
TP_L0_00114.Position -5.425 -5.425 0
TP_L0_00114.Mother TES_L0
TP_L0_00114.Visibility 0

TES_Pixel_L0.Copy TP_L0_00115
TP_L0_00115.Position -5.425 -3.875 0
TP_L0_00115.Mother TES_L0
TP_L0_00115.Visibility 0

TES_Pixel_L0.Copy TP_L0_00116
TP_L0_00116.Position -5.425 -2.325 0
TP_L0_00116.Mother TES_L0
TP_L0_00116.Visibility 0

TES_Pixel_L0.Copy TP_L0_00117
TP_L0_00117.Position -5.425 -0.775 0
TP_L0_00117.Mother TES_L0
TP_L0_00117.Visibility 0

TES_Pixel_L0.Copy TP_L0_00118
TP_L0_00118.Position -5.425 0.775 0
TP_L0_00118.Mother TES_L0
TP_L0_00118.Visibility 0

TES_Pixel_L0.Copy TP_L0_00119
TP_L0_00119.Position -5.425 2.325 0
TP_L0_00119.Mother TES_L0
TP_L0_00119.Visibility 0

TES_Pixel_L0.Copy TP_L0_00120
TP_L0_00120.Position -5.425 3.875 0
TP_L0_00120.Mother TES_L0
TP_L0_00120.Visibility 0

TES_Pixel_L0.Copy TP_L0_00121
TP_L0_00121.Position -5.425 5.425 0
TP_L0_00121.Mother TES_L0
TP_L0_00121.Visibility 0

TES_Pixel_L0.Copy TP_L0_00122
TP_L0_00122.Position -5.425 6.975 0
TP_L0_00122.Mother TES_L0
TP_L0_00122.Visibility 0

TES_Pixel_L0.Copy TP_L0_00123
TP_L0_00123.Position -5.425 8.525 0
TP_L0_00123.Mother TES_L0
TP_L0_00123.Visibility 0

TES_Pixel_L0.Copy TP_L0_00124
TP_L0_00124.Position -5.425 10.075 0
TP_L0_00124.Mother TES_L0
TP_L0_00124.Visibility 0

TES_Pixel_L0.Copy TP_L0_00125
TP_L0_00125.Position -5.425 11.625 0
TP_L0_00125.Mother TES_L0
TP_L0_00125.Visibility 0

TES_Pixel_L0.Copy TP_L0_00126
TP_L0_00126.Position -5.425 13.175 0
TP_L0_00126.Mother TES_L0
TP_L0_00126.Visibility 0

TES_Pixel_L0.Copy TP_L0_00127
TP_L0_00127.Position -5.425 14.725 0
TP_L0_00127.Mother TES_L0
TP_L0_00127.Visibility 0

TES_Pixel_L0.Copy TP_L0_00128
TP_L0_00128.Position -3.875 -14.725 0
TP_L0_00128.Mother TES_L0
TP_L0_00128.Visibility 0

TES_Pixel_L0.Copy TP_L0_00129
TP_L0_00129.Position -3.875 -13.175 0
TP_L0_00129.Mother TES_L0
TP_L0_00129.Visibility 0

TES_Pixel_L0.Copy TP_L0_00130
TP_L0_00130.Position -3.875 -11.625 0
TP_L0_00130.Mother TES_L0
TP_L0_00130.Visibility 0

TES_Pixel_L0.Copy TP_L0_00131
TP_L0_00131.Position -3.875 -10.075 0
TP_L0_00131.Mother TES_L0
TP_L0_00131.Visibility 0

TES_Pixel_L0.Copy TP_L0_00132
TP_L0_00132.Position -3.875 -8.525 0
TP_L0_00132.Mother TES_L0
TP_L0_00132.Visibility 0

TES_Pixel_L0.Copy TP_L0_00133
TP_L0_00133.Position -3.875 -6.975 0
TP_L0_00133.Mother TES_L0
TP_L0_00133.Visibility 0

TES_Pixel_L0.Copy TP_L0_00134
TP_L0_00134.Position -3.875 -5.425 0
TP_L0_00134.Mother TES_L0
TP_L0_00134.Visibility 0

TES_Pixel_L0.Copy TP_L0_00135
TP_L0_00135.Position -3.875 -3.875 0
TP_L0_00135.Mother TES_L0
TP_L0_00135.Visibility 0

TES_Pixel_L0.Copy TP_L0_00136
TP_L0_00136.Position -3.875 -2.325 0
TP_L0_00136.Mother TES_L0
TP_L0_00136.Visibility 0

TES_Pixel_L0.Copy TP_L0_00137
TP_L0_00137.Position -3.875 -0.775 0
TP_L0_00137.Mother TES_L0
TP_L0_00137.Visibility 0

TES_Pixel_L0.Copy TP_L0_00138
TP_L0_00138.Position -3.875 0.775 0
TP_L0_00138.Mother TES_L0
TP_L0_00138.Visibility 0

TES_Pixel_L0.Copy TP_L0_00139
TP_L0_00139.Position -3.875 2.325 0
TP_L0_00139.Mother TES_L0
TP_L0_00139.Visibility 0

TES_Pixel_L0.Copy TP_L0_00140
TP_L0_00140.Position -3.875 3.875 0
TP_L0_00140.Mother TES_L0
TP_L0_00140.Visibility 0

TES_Pixel_L0.Copy TP_L0_00141
TP_L0_00141.Position -3.875 5.425 0
TP_L0_00141.Mother TES_L0
TP_L0_00141.Visibility 0

TES_Pixel_L0.Copy TP_L0_00142
TP_L0_00142.Position -3.875 6.975 0
TP_L0_00142.Mother TES_L0
TP_L0_00142.Visibility 0

TES_Pixel_L0.Copy TP_L0_00143
TP_L0_00143.Position -3.875 8.525 0
TP_L0_00143.Mother TES_L0
TP_L0_00143.Visibility 0

TES_Pixel_L0.Copy TP_L0_00144
TP_L0_00144.Position -3.875 10.075 0
TP_L0_00144.Mother TES_L0
TP_L0_00144.Visibility 0

TES_Pixel_L0.Copy TP_L0_00145
TP_L0_00145.Position -3.875 11.625 0
TP_L0_00145.Mother TES_L0
TP_L0_00145.Visibility 0

TES_Pixel_L0.Copy TP_L0_00146
TP_L0_00146.Position -3.875 13.175 0
TP_L0_00146.Mother TES_L0
TP_L0_00146.Visibility 0

TES_Pixel_L0.Copy TP_L0_00147
TP_L0_00147.Position -3.875 14.725 0
TP_L0_00147.Mother TES_L0
TP_L0_00147.Visibility 0

TES_Pixel_L0.Copy TP_L0_00148
TP_L0_00148.Position -2.325 -14.725 0
TP_L0_00148.Mother TES_L0
TP_L0_00148.Visibility 0

TES_Pixel_L0.Copy TP_L0_00149
TP_L0_00149.Position -2.325 -13.175 0
TP_L0_00149.Mother TES_L0
TP_L0_00149.Visibility 0

TES_Pixel_L0.Copy TP_L0_00150
TP_L0_00150.Position -2.325 -11.625 0
TP_L0_00150.Mother TES_L0
TP_L0_00150.Visibility 0

TES_Pixel_L0.Copy TP_L0_00151
TP_L0_00151.Position -2.325 -10.075 0
TP_L0_00151.Mother TES_L0
TP_L0_00151.Visibility 0

TES_Pixel_L0.Copy TP_L0_00152
TP_L0_00152.Position -2.325 -8.525 0
TP_L0_00152.Mother TES_L0
TP_L0_00152.Visibility 0

TES_Pixel_L0.Copy TP_L0_00153
TP_L0_00153.Position -2.325 -6.975 0
TP_L0_00153.Mother TES_L0
TP_L0_00153.Visibility 0

TES_Pixel_L0.Copy TP_L0_00154
TP_L0_00154.Position -2.325 -5.425 0
TP_L0_00154.Mother TES_L0
TP_L0_00154.Visibility 0

TES_Pixel_L0.Copy TP_L0_00155
TP_L0_00155.Position -2.325 -3.875 0
TP_L0_00155.Mother TES_L0
TP_L0_00155.Visibility 0

TES_Pixel_L0.Copy TP_L0_00156
TP_L0_00156.Position -2.325 -2.325 0
TP_L0_00156.Mother TES_L0
TP_L0_00156.Visibility 0

TES_Pixel_L0.Copy TP_L0_00157
TP_L0_00157.Position -2.325 -0.775 0
TP_L0_00157.Mother TES_L0
TP_L0_00157.Visibility 0

TES_Pixel_L0.Copy TP_L0_00158
TP_L0_00158.Position -2.325 0.775 0
TP_L0_00158.Mother TES_L0
TP_L0_00158.Visibility 0

TES_Pixel_L0.Copy TP_L0_00159
TP_L0_00159.Position -2.325 2.325 0
TP_L0_00159.Mother TES_L0
TP_L0_00159.Visibility 0

TES_Pixel_L0.Copy TP_L0_00160
TP_L0_00160.Position -2.325 3.875 0
TP_L0_00160.Mother TES_L0
TP_L0_00160.Visibility 0

TES_Pixel_L0.Copy TP_L0_00161
TP_L0_00161.Position -2.325 5.425 0
TP_L0_00161.Mother TES_L0
TP_L0_00161.Visibility 0

TES_Pixel_L0.Copy TP_L0_00162
TP_L0_00162.Position -2.325 6.975 0
TP_L0_00162.Mother TES_L0
TP_L0_00162.Visibility 0

TES_Pixel_L0.Copy TP_L0_00163
TP_L0_00163.Position -2.325 8.525 0
TP_L0_00163.Mother TES_L0
TP_L0_00163.Visibility 0

TES_Pixel_L0.Copy TP_L0_00164
TP_L0_00164.Position -2.325 10.075 0
TP_L0_00164.Mother TES_L0
TP_L0_00164.Visibility 0

TES_Pixel_L0.Copy TP_L0_00165
TP_L0_00165.Position -2.325 11.625 0
TP_L0_00165.Mother TES_L0
TP_L0_00165.Visibility 0

TES_Pixel_L0.Copy TP_L0_00166
TP_L0_00166.Position -2.325 13.175 0
TP_L0_00166.Mother TES_L0
TP_L0_00166.Visibility 0

TES_Pixel_L0.Copy TP_L0_00167
TP_L0_00167.Position -2.325 14.725 0
TP_L0_00167.Mother TES_L0
TP_L0_00167.Visibility 0

TES_Pixel_L0.Copy TP_L0_00168
TP_L0_00168.Position -0.775 -14.725 0
TP_L0_00168.Mother TES_L0
TP_L0_00168.Visibility 0

TES_Pixel_L0.Copy TP_L0_00169
TP_L0_00169.Position -0.775 -13.175 0
TP_L0_00169.Mother TES_L0
TP_L0_00169.Visibility 0

TES_Pixel_L0.Copy TP_L0_00170
TP_L0_00170.Position -0.775 -11.625 0
TP_L0_00170.Mother TES_L0
TP_L0_00170.Visibility 0

TES_Pixel_L0.Copy TP_L0_00171
TP_L0_00171.Position -0.775 -10.075 0
TP_L0_00171.Mother TES_L0
TP_L0_00171.Visibility 0

TES_Pixel_L0.Copy TP_L0_00172
TP_L0_00172.Position -0.775 -8.525 0
TP_L0_00172.Mother TES_L0
TP_L0_00172.Visibility 0

TES_Pixel_L0.Copy TP_L0_00173
TP_L0_00173.Position -0.775 -6.975 0
TP_L0_00173.Mother TES_L0
TP_L0_00173.Visibility 0

TES_Pixel_L0.Copy TP_L0_00174
TP_L0_00174.Position -0.775 -5.425 0
TP_L0_00174.Mother TES_L0
TP_L0_00174.Visibility 0

TES_Pixel_L0.Copy TP_L0_00175
TP_L0_00175.Position -0.775 -3.875 0
TP_L0_00175.Mother TES_L0
TP_L0_00175.Visibility 0

TES_Pixel_L0.Copy TP_L0_00176
TP_L0_00176.Position -0.775 -2.325 0
TP_L0_00176.Mother TES_L0
TP_L0_00176.Visibility 0

TES_Pixel_L0.Copy TP_L0_00177
TP_L0_00177.Position -0.775 -0.775 0
TP_L0_00177.Mother TES_L0
TP_L0_00177.Visibility 0

TES_Pixel_L0.Copy TP_L0_00178
TP_L0_00178.Position -0.775 0.775 0
TP_L0_00178.Mother TES_L0
TP_L0_00178.Visibility 0

TES_Pixel_L0.Copy TP_L0_00179
TP_L0_00179.Position -0.775 2.325 0
TP_L0_00179.Mother TES_L0
TP_L0_00179.Visibility 0

TES_Pixel_L0.Copy TP_L0_00180
TP_L0_00180.Position -0.775 3.875 0
TP_L0_00180.Mother TES_L0
TP_L0_00180.Visibility 0

TES_Pixel_L0.Copy TP_L0_00181
TP_L0_00181.Position -0.775 5.425 0
TP_L0_00181.Mother TES_L0
TP_L0_00181.Visibility 0

TES_Pixel_L0.Copy TP_L0_00182
TP_L0_00182.Position -0.775 6.975 0
TP_L0_00182.Mother TES_L0
TP_L0_00182.Visibility 0

TES_Pixel_L0.Copy TP_L0_00183
TP_L0_00183.Position -0.775 8.525 0
TP_L0_00183.Mother TES_L0
TP_L0_00183.Visibility 0

TES_Pixel_L0.Copy TP_L0_00184
TP_L0_00184.Position -0.775 10.075 0
TP_L0_00184.Mother TES_L0
TP_L0_00184.Visibility 0

TES_Pixel_L0.Copy TP_L0_00185
TP_L0_00185.Position -0.775 11.625 0
TP_L0_00185.Mother TES_L0
TP_L0_00185.Visibility 0

TES_Pixel_L0.Copy TP_L0_00186
TP_L0_00186.Position -0.775 13.175 0
TP_L0_00186.Mother TES_L0
TP_L0_00186.Visibility 0

TES_Pixel_L0.Copy TP_L0_00187
TP_L0_00187.Position -0.775 14.725 0
TP_L0_00187.Mother TES_L0
TP_L0_00187.Visibility 0

TES_Pixel_L0.Copy TP_L0_00188
TP_L0_00188.Position 0.775 -14.725 0
TP_L0_00188.Mother TES_L0
TP_L0_00188.Visibility 0

TES_Pixel_L0.Copy TP_L0_00189
TP_L0_00189.Position 0.775 -13.175 0
TP_L0_00189.Mother TES_L0
TP_L0_00189.Visibility 0

TES_Pixel_L0.Copy TP_L0_00190
TP_L0_00190.Position 0.775 -11.625 0
TP_L0_00190.Mother TES_L0
TP_L0_00190.Visibility 0

TES_Pixel_L0.Copy TP_L0_00191
TP_L0_00191.Position 0.775 -10.075 0
TP_L0_00191.Mother TES_L0
TP_L0_00191.Visibility 0

TES_Pixel_L0.Copy TP_L0_00192
TP_L0_00192.Position 0.775 -8.525 0
TP_L0_00192.Mother TES_L0
TP_L0_00192.Visibility 0

TES_Pixel_L0.Copy TP_L0_00193
TP_L0_00193.Position 0.775 -6.975 0
TP_L0_00193.Mother TES_L0
TP_L0_00193.Visibility 0

TES_Pixel_L0.Copy TP_L0_00194
TP_L0_00194.Position 0.775 -5.425 0
TP_L0_00194.Mother TES_L0
TP_L0_00194.Visibility 0

TES_Pixel_L0.Copy TP_L0_00195
TP_L0_00195.Position 0.775 -3.875 0
TP_L0_00195.Mother TES_L0
TP_L0_00195.Visibility 0

TES_Pixel_L0.Copy TP_L0_00196
TP_L0_00196.Position 0.775 -2.325 0
TP_L0_00196.Mother TES_L0
TP_L0_00196.Visibility 0

TES_Pixel_L0.Copy TP_L0_00197
TP_L0_00197.Position 0.775 -0.775 0
TP_L0_00197.Mother TES_L0
TP_L0_00197.Visibility 0

TES_Pixel_L0.Copy TP_L0_00198
TP_L0_00198.Position 0.775 0.775 0
TP_L0_00198.Mother TES_L0
TP_L0_00198.Visibility 0

TES_Pixel_L0.Copy TP_L0_00199
TP_L0_00199.Position 0.775 2.325 0
TP_L0_00199.Mother TES_L0
TP_L0_00199.Visibility 0

TES_Pixel_L0.Copy TP_L0_00200
TP_L0_00200.Position 0.775 3.875 0
TP_L0_00200.Mother TES_L0
TP_L0_00200.Visibility 0

TES_Pixel_L0.Copy TP_L0_00201
TP_L0_00201.Position 0.775 5.425 0
TP_L0_00201.Mother TES_L0
TP_L0_00201.Visibility 0

TES_Pixel_L0.Copy TP_L0_00202
TP_L0_00202.Position 0.775 6.975 0
TP_L0_00202.Mother TES_L0
TP_L0_00202.Visibility 0

TES_Pixel_L0.Copy TP_L0_00203
TP_L0_00203.Position 0.775 8.525 0
TP_L0_00203.Mother TES_L0
TP_L0_00203.Visibility 0

TES_Pixel_L0.Copy TP_L0_00204
TP_L0_00204.Position 0.775 10.075 0
TP_L0_00204.Mother TES_L0
TP_L0_00204.Visibility 0

TES_Pixel_L0.Copy TP_L0_00205
TP_L0_00205.Position 0.775 11.625 0
TP_L0_00205.Mother TES_L0
TP_L0_00205.Visibility 0

TES_Pixel_L0.Copy TP_L0_00206
TP_L0_00206.Position 0.775 13.175 0
TP_L0_00206.Mother TES_L0
TP_L0_00206.Visibility 0

TES_Pixel_L0.Copy TP_L0_00207
TP_L0_00207.Position 0.775 14.725 0
TP_L0_00207.Mother TES_L0
TP_L0_00207.Visibility 0

TES_Pixel_L0.Copy TP_L0_00208
TP_L0_00208.Position 2.325 -14.725 0
TP_L0_00208.Mother TES_L0
TP_L0_00208.Visibility 0

TES_Pixel_L0.Copy TP_L0_00209
TP_L0_00209.Position 2.325 -13.175 0
TP_L0_00209.Mother TES_L0
TP_L0_00209.Visibility 0

TES_Pixel_L0.Copy TP_L0_00210
TP_L0_00210.Position 2.325 -11.625 0
TP_L0_00210.Mother TES_L0
TP_L0_00210.Visibility 0

TES_Pixel_L0.Copy TP_L0_00211
TP_L0_00211.Position 2.325 -10.075 0
TP_L0_00211.Mother TES_L0
TP_L0_00211.Visibility 0

TES_Pixel_L0.Copy TP_L0_00212
TP_L0_00212.Position 2.325 -8.525 0
TP_L0_00212.Mother TES_L0
TP_L0_00212.Visibility 0

TES_Pixel_L0.Copy TP_L0_00213
TP_L0_00213.Position 2.325 -6.975 0
TP_L0_00213.Mother TES_L0
TP_L0_00213.Visibility 0

TES_Pixel_L0.Copy TP_L0_00214
TP_L0_00214.Position 2.325 -5.425 0
TP_L0_00214.Mother TES_L0
TP_L0_00214.Visibility 0

TES_Pixel_L0.Copy TP_L0_00215
TP_L0_00215.Position 2.325 -3.875 0
TP_L0_00215.Mother TES_L0
TP_L0_00215.Visibility 0

TES_Pixel_L0.Copy TP_L0_00216
TP_L0_00216.Position 2.325 -2.325 0
TP_L0_00216.Mother TES_L0
TP_L0_00216.Visibility 0

TES_Pixel_L0.Copy TP_L0_00217
TP_L0_00217.Position 2.325 -0.775 0
TP_L0_00217.Mother TES_L0
TP_L0_00217.Visibility 0

TES_Pixel_L0.Copy TP_L0_00218
TP_L0_00218.Position 2.325 0.775 0
TP_L0_00218.Mother TES_L0
TP_L0_00218.Visibility 0

TES_Pixel_L0.Copy TP_L0_00219
TP_L0_00219.Position 2.325 2.325 0
TP_L0_00219.Mother TES_L0
TP_L0_00219.Visibility 0

TES_Pixel_L0.Copy TP_L0_00220
TP_L0_00220.Position 2.325 3.875 0
TP_L0_00220.Mother TES_L0
TP_L0_00220.Visibility 0

TES_Pixel_L0.Copy TP_L0_00221
TP_L0_00221.Position 2.325 5.425 0
TP_L0_00221.Mother TES_L0
TP_L0_00221.Visibility 0

TES_Pixel_L0.Copy TP_L0_00222
TP_L0_00222.Position 2.325 6.975 0
TP_L0_00222.Mother TES_L0
TP_L0_00222.Visibility 0

TES_Pixel_L0.Copy TP_L0_00223
TP_L0_00223.Position 2.325 8.525 0
TP_L0_00223.Mother TES_L0
TP_L0_00223.Visibility 0

TES_Pixel_L0.Copy TP_L0_00224
TP_L0_00224.Position 2.325 10.075 0
TP_L0_00224.Mother TES_L0
TP_L0_00224.Visibility 0

TES_Pixel_L0.Copy TP_L0_00225
TP_L0_00225.Position 2.325 11.625 0
TP_L0_00225.Mother TES_L0
TP_L0_00225.Visibility 0

TES_Pixel_L0.Copy TP_L0_00226
TP_L0_00226.Position 2.325 13.175 0
TP_L0_00226.Mother TES_L0
TP_L0_00226.Visibility 0

TES_Pixel_L0.Copy TP_L0_00227
TP_L0_00227.Position 2.325 14.725 0
TP_L0_00227.Mother TES_L0
TP_L0_00227.Visibility 0

TES_Pixel_L0.Copy TP_L0_00228
TP_L0_00228.Position 3.875 -14.725 0
TP_L0_00228.Mother TES_L0
TP_L0_00228.Visibility 0

TES_Pixel_L0.Copy TP_L0_00229
TP_L0_00229.Position 3.875 -13.175 0
TP_L0_00229.Mother TES_L0
TP_L0_00229.Visibility 0

TES_Pixel_L0.Copy TP_L0_00230
TP_L0_00230.Position 3.875 -11.625 0
TP_L0_00230.Mother TES_L0
TP_L0_00230.Visibility 0

TES_Pixel_L0.Copy TP_L0_00231
TP_L0_00231.Position 3.875 -10.075 0
TP_L0_00231.Mother TES_L0
TP_L0_00231.Visibility 0

TES_Pixel_L0.Copy TP_L0_00232
TP_L0_00232.Position 3.875 -8.525 0
TP_L0_00232.Mother TES_L0
TP_L0_00232.Visibility 0

TES_Pixel_L0.Copy TP_L0_00233
TP_L0_00233.Position 3.875 -6.975 0
TP_L0_00233.Mother TES_L0
TP_L0_00233.Visibility 0

TES_Pixel_L0.Copy TP_L0_00234
TP_L0_00234.Position 3.875 -5.425 0
TP_L0_00234.Mother TES_L0
TP_L0_00234.Visibility 0

TES_Pixel_L0.Copy TP_L0_00235
TP_L0_00235.Position 3.875 -3.875 0
TP_L0_00235.Mother TES_L0
TP_L0_00235.Visibility 0

TES_Pixel_L0.Copy TP_L0_00236
TP_L0_00236.Position 3.875 -2.325 0
TP_L0_00236.Mother TES_L0
TP_L0_00236.Visibility 0

TES_Pixel_L0.Copy TP_L0_00237
TP_L0_00237.Position 3.875 -0.775 0
TP_L0_00237.Mother TES_L0
TP_L0_00237.Visibility 0

TES_Pixel_L0.Copy TP_L0_00238
TP_L0_00238.Position 3.875 0.775 0
TP_L0_00238.Mother TES_L0
TP_L0_00238.Visibility 0

TES_Pixel_L0.Copy TP_L0_00239
TP_L0_00239.Position 3.875 2.325 0
TP_L0_00239.Mother TES_L0
TP_L0_00239.Visibility 0

TES_Pixel_L0.Copy TP_L0_00240
TP_L0_00240.Position 3.875 3.875 0
TP_L0_00240.Mother TES_L0
TP_L0_00240.Visibility 0

TES_Pixel_L0.Copy TP_L0_00241
TP_L0_00241.Position 3.875 5.425 0
TP_L0_00241.Mother TES_L0
TP_L0_00241.Visibility 0

TES_Pixel_L0.Copy TP_L0_00242
TP_L0_00242.Position 3.875 6.975 0
TP_L0_00242.Mother TES_L0
TP_L0_00242.Visibility 0

TES_Pixel_L0.Copy TP_L0_00243
TP_L0_00243.Position 3.875 8.525 0
TP_L0_00243.Mother TES_L0
TP_L0_00243.Visibility 0

TES_Pixel_L0.Copy TP_L0_00244
TP_L0_00244.Position 3.875 10.075 0
TP_L0_00244.Mother TES_L0
TP_L0_00244.Visibility 0

TES_Pixel_L0.Copy TP_L0_00245
TP_L0_00245.Position 3.875 11.625 0
TP_L0_00245.Mother TES_L0
TP_L0_00245.Visibility 0

TES_Pixel_L0.Copy TP_L0_00246
TP_L0_00246.Position 3.875 13.175 0
TP_L0_00246.Mother TES_L0
TP_L0_00246.Visibility 0

TES_Pixel_L0.Copy TP_L0_00247
TP_L0_00247.Position 3.875 14.725 0
TP_L0_00247.Mother TES_L0
TP_L0_00247.Visibility 0

TES_Pixel_L0.Copy TP_L0_00248
TP_L0_00248.Position 5.425 -14.725 0
TP_L0_00248.Mother TES_L0
TP_L0_00248.Visibility 0

TES_Pixel_L0.Copy TP_L0_00249
TP_L0_00249.Position 5.425 -13.175 0
TP_L0_00249.Mother TES_L0
TP_L0_00249.Visibility 0

TES_Pixel_L0.Copy TP_L0_00250
TP_L0_00250.Position 5.425 -11.625 0
TP_L0_00250.Mother TES_L0
TP_L0_00250.Visibility 0

TES_Pixel_L0.Copy TP_L0_00251
TP_L0_00251.Position 5.425 -10.075 0
TP_L0_00251.Mother TES_L0
TP_L0_00251.Visibility 0

TES_Pixel_L0.Copy TP_L0_00252
TP_L0_00252.Position 5.425 -8.525 0
TP_L0_00252.Mother TES_L0
TP_L0_00252.Visibility 0

TES_Pixel_L0.Copy TP_L0_00253
TP_L0_00253.Position 5.425 -6.975 0
TP_L0_00253.Mother TES_L0
TP_L0_00253.Visibility 0

TES_Pixel_L0.Copy TP_L0_00254
TP_L0_00254.Position 5.425 -5.425 0
TP_L0_00254.Mother TES_L0
TP_L0_00254.Visibility 0

TES_Pixel_L0.Copy TP_L0_00255
TP_L0_00255.Position 5.425 -3.875 0
TP_L0_00255.Mother TES_L0
TP_L0_00255.Visibility 0

TES_Pixel_L0.Copy TP_L0_00256
TP_L0_00256.Position 5.425 -2.325 0
TP_L0_00256.Mother TES_L0
TP_L0_00256.Visibility 0

TES_Pixel_L0.Copy TP_L0_00257
TP_L0_00257.Position 5.425 -0.775 0
TP_L0_00257.Mother TES_L0
TP_L0_00257.Visibility 0

TES_Pixel_L0.Copy TP_L0_00258
TP_L0_00258.Position 5.425 0.775 0
TP_L0_00258.Mother TES_L0
TP_L0_00258.Visibility 0

TES_Pixel_L0.Copy TP_L0_00259
TP_L0_00259.Position 5.425 2.325 0
TP_L0_00259.Mother TES_L0
TP_L0_00259.Visibility 0

TES_Pixel_L0.Copy TP_L0_00260
TP_L0_00260.Position 5.425 3.875 0
TP_L0_00260.Mother TES_L0
TP_L0_00260.Visibility 0

TES_Pixel_L0.Copy TP_L0_00261
TP_L0_00261.Position 5.425 5.425 0
TP_L0_00261.Mother TES_L0
TP_L0_00261.Visibility 0

TES_Pixel_L0.Copy TP_L0_00262
TP_L0_00262.Position 5.425 6.975 0
TP_L0_00262.Mother TES_L0
TP_L0_00262.Visibility 0

TES_Pixel_L0.Copy TP_L0_00263
TP_L0_00263.Position 5.425 8.525 0
TP_L0_00263.Mother TES_L0
TP_L0_00263.Visibility 0

TES_Pixel_L0.Copy TP_L0_00264
TP_L0_00264.Position 5.425 10.075 0
TP_L0_00264.Mother TES_L0
TP_L0_00264.Visibility 0

TES_Pixel_L0.Copy TP_L0_00265
TP_L0_00265.Position 5.425 11.625 0
TP_L0_00265.Mother TES_L0
TP_L0_00265.Visibility 0

TES_Pixel_L0.Copy TP_L0_00266
TP_L0_00266.Position 5.425 13.175 0
TP_L0_00266.Mother TES_L0
TP_L0_00266.Visibility 0

TES_Pixel_L0.Copy TP_L0_00267
TP_L0_00267.Position 5.425 14.725 0
TP_L0_00267.Mother TES_L0
TP_L0_00267.Visibility 0

TES_Pixel_L0.Copy TP_L0_00268
TP_L0_00268.Position 6.975 -14.725 0
TP_L0_00268.Mother TES_L0
TP_L0_00268.Visibility 0

TES_Pixel_L0.Copy TP_L0_00269
TP_L0_00269.Position 6.975 -13.175 0
TP_L0_00269.Mother TES_L0
TP_L0_00269.Visibility 0

TES_Pixel_L0.Copy TP_L0_00270
TP_L0_00270.Position 6.975 -11.625 0
TP_L0_00270.Mother TES_L0
TP_L0_00270.Visibility 0

TES_Pixel_L0.Copy TP_L0_00271
TP_L0_00271.Position 6.975 -10.075 0
TP_L0_00271.Mother TES_L0
TP_L0_00271.Visibility 0

TES_Pixel_L0.Copy TP_L0_00272
TP_L0_00272.Position 6.975 -8.525 0
TP_L0_00272.Mother TES_L0
TP_L0_00272.Visibility 0

TES_Pixel_L0.Copy TP_L0_00273
TP_L0_00273.Position 6.975 -6.975 0
TP_L0_00273.Mother TES_L0
TP_L0_00273.Visibility 0

TES_Pixel_L0.Copy TP_L0_00274
TP_L0_00274.Position 6.975 -5.425 0
TP_L0_00274.Mother TES_L0
TP_L0_00274.Visibility 0

TES_Pixel_L0.Copy TP_L0_00275
TP_L0_00275.Position 6.975 -3.875 0
TP_L0_00275.Mother TES_L0
TP_L0_00275.Visibility 0

TES_Pixel_L0.Copy TP_L0_00276
TP_L0_00276.Position 6.975 -2.325 0
TP_L0_00276.Mother TES_L0
TP_L0_00276.Visibility 0

TES_Pixel_L0.Copy TP_L0_00277
TP_L0_00277.Position 6.975 -0.775 0
TP_L0_00277.Mother TES_L0
TP_L0_00277.Visibility 0

TES_Pixel_L0.Copy TP_L0_00278
TP_L0_00278.Position 6.975 0.775 0
TP_L0_00278.Mother TES_L0
TP_L0_00278.Visibility 0

TES_Pixel_L0.Copy TP_L0_00279
TP_L0_00279.Position 6.975 2.325 0
TP_L0_00279.Mother TES_L0
TP_L0_00279.Visibility 0

TES_Pixel_L0.Copy TP_L0_00280
TP_L0_00280.Position 6.975 3.875 0
TP_L0_00280.Mother TES_L0
TP_L0_00280.Visibility 0

TES_Pixel_L0.Copy TP_L0_00281
TP_L0_00281.Position 6.975 5.425 0
TP_L0_00281.Mother TES_L0
TP_L0_00281.Visibility 0

TES_Pixel_L0.Copy TP_L0_00282
TP_L0_00282.Position 6.975 6.975 0
TP_L0_00282.Mother TES_L0
TP_L0_00282.Visibility 0

TES_Pixel_L0.Copy TP_L0_00283
TP_L0_00283.Position 6.975 8.525 0
TP_L0_00283.Mother TES_L0
TP_L0_00283.Visibility 0

TES_Pixel_L0.Copy TP_L0_00284
TP_L0_00284.Position 6.975 10.075 0
TP_L0_00284.Mother TES_L0
TP_L0_00284.Visibility 0

TES_Pixel_L0.Copy TP_L0_00285
TP_L0_00285.Position 6.975 11.625 0
TP_L0_00285.Mother TES_L0
TP_L0_00285.Visibility 0

TES_Pixel_L0.Copy TP_L0_00286
TP_L0_00286.Position 6.975 13.175 0
TP_L0_00286.Mother TES_L0
TP_L0_00286.Visibility 0

TES_Pixel_L0.Copy TP_L0_00287
TP_L0_00287.Position 6.975 14.725 0
TP_L0_00287.Mother TES_L0
TP_L0_00287.Visibility 0

TES_Pixel_L0.Copy TP_L0_00288
TP_L0_00288.Position 8.525 -14.725 0
TP_L0_00288.Mother TES_L0
TP_L0_00288.Visibility 0

TES_Pixel_L0.Copy TP_L0_00289
TP_L0_00289.Position 8.525 -13.175 0
TP_L0_00289.Mother TES_L0
TP_L0_00289.Visibility 0

TES_Pixel_L0.Copy TP_L0_00290
TP_L0_00290.Position 8.525 -11.625 0
TP_L0_00290.Mother TES_L0
TP_L0_00290.Visibility 0

TES_Pixel_L0.Copy TP_L0_00291
TP_L0_00291.Position 8.525 -10.075 0
TP_L0_00291.Mother TES_L0
TP_L0_00291.Visibility 0

TES_Pixel_L0.Copy TP_L0_00292
TP_L0_00292.Position 8.525 -8.525 0
TP_L0_00292.Mother TES_L0
TP_L0_00292.Visibility 0

TES_Pixel_L0.Copy TP_L0_00293
TP_L0_00293.Position 8.525 -6.975 0
TP_L0_00293.Mother TES_L0
TP_L0_00293.Visibility 0

TES_Pixel_L0.Copy TP_L0_00294
TP_L0_00294.Position 8.525 -5.425 0
TP_L0_00294.Mother TES_L0
TP_L0_00294.Visibility 0

TES_Pixel_L0.Copy TP_L0_00295
TP_L0_00295.Position 8.525 -3.875 0
TP_L0_00295.Mother TES_L0
TP_L0_00295.Visibility 0

TES_Pixel_L0.Copy TP_L0_00296
TP_L0_00296.Position 8.525 -2.325 0
TP_L0_00296.Mother TES_L0
TP_L0_00296.Visibility 0

TES_Pixel_L0.Copy TP_L0_00297
TP_L0_00297.Position 8.525 -0.775 0
TP_L0_00297.Mother TES_L0
TP_L0_00297.Visibility 0

TES_Pixel_L0.Copy TP_L0_00298
TP_L0_00298.Position 8.525 0.775 0
TP_L0_00298.Mother TES_L0
TP_L0_00298.Visibility 0

TES_Pixel_L0.Copy TP_L0_00299
TP_L0_00299.Position 8.525 2.325 0
TP_L0_00299.Mother TES_L0
TP_L0_00299.Visibility 0

TES_Pixel_L0.Copy TP_L0_00300
TP_L0_00300.Position 8.525 3.875 0
TP_L0_00300.Mother TES_L0
TP_L0_00300.Visibility 0

TES_Pixel_L0.Copy TP_L0_00301
TP_L0_00301.Position 8.525 5.425 0
TP_L0_00301.Mother TES_L0
TP_L0_00301.Visibility 0

TES_Pixel_L0.Copy TP_L0_00302
TP_L0_00302.Position 8.525 6.975 0
TP_L0_00302.Mother TES_L0
TP_L0_00302.Visibility 0

TES_Pixel_L0.Copy TP_L0_00303
TP_L0_00303.Position 8.525 8.525 0
TP_L0_00303.Mother TES_L0
TP_L0_00303.Visibility 0

TES_Pixel_L0.Copy TP_L0_00304
TP_L0_00304.Position 8.525 10.075 0
TP_L0_00304.Mother TES_L0
TP_L0_00304.Visibility 0

TES_Pixel_L0.Copy TP_L0_00305
TP_L0_00305.Position 8.525 11.625 0
TP_L0_00305.Mother TES_L0
TP_L0_00305.Visibility 0

TES_Pixel_L0.Copy TP_L0_00306
TP_L0_00306.Position 8.525 13.175 0
TP_L0_00306.Mother TES_L0
TP_L0_00306.Visibility 0

TES_Pixel_L0.Copy TP_L0_00307
TP_L0_00307.Position 8.525 14.725 0
TP_L0_00307.Mother TES_L0
TP_L0_00307.Visibility 0

TES_Pixel_L0.Copy TP_L0_00308
TP_L0_00308.Position 10.075 -14.725 0
TP_L0_00308.Mother TES_L0
TP_L0_00308.Visibility 0

TES_Pixel_L0.Copy TP_L0_00309
TP_L0_00309.Position 10.075 -13.175 0
TP_L0_00309.Mother TES_L0
TP_L0_00309.Visibility 0

TES_Pixel_L0.Copy TP_L0_00310
TP_L0_00310.Position 10.075 -11.625 0
TP_L0_00310.Mother TES_L0
TP_L0_00310.Visibility 0

TES_Pixel_L0.Copy TP_L0_00311
TP_L0_00311.Position 10.075 -10.075 0
TP_L0_00311.Mother TES_L0
TP_L0_00311.Visibility 0

TES_Pixel_L0.Copy TP_L0_00312
TP_L0_00312.Position 10.075 -8.525 0
TP_L0_00312.Mother TES_L0
TP_L0_00312.Visibility 0

TES_Pixel_L0.Copy TP_L0_00313
TP_L0_00313.Position 10.075 -6.975 0
TP_L0_00313.Mother TES_L0
TP_L0_00313.Visibility 0

TES_Pixel_L0.Copy TP_L0_00314
TP_L0_00314.Position 10.075 -5.425 0
TP_L0_00314.Mother TES_L0
TP_L0_00314.Visibility 0

TES_Pixel_L0.Copy TP_L0_00315
TP_L0_00315.Position 10.075 -3.875 0
TP_L0_00315.Mother TES_L0
TP_L0_00315.Visibility 0

TES_Pixel_L0.Copy TP_L0_00316
TP_L0_00316.Position 10.075 -2.325 0
TP_L0_00316.Mother TES_L0
TP_L0_00316.Visibility 0

TES_Pixel_L0.Copy TP_L0_00317
TP_L0_00317.Position 10.075 -0.775 0
TP_L0_00317.Mother TES_L0
TP_L0_00317.Visibility 0

TES_Pixel_L0.Copy TP_L0_00318
TP_L0_00318.Position 10.075 0.775 0
TP_L0_00318.Mother TES_L0
TP_L0_00318.Visibility 0

TES_Pixel_L0.Copy TP_L0_00319
TP_L0_00319.Position 10.075 2.325 0
TP_L0_00319.Mother TES_L0
TP_L0_00319.Visibility 0

TES_Pixel_L0.Copy TP_L0_00320
TP_L0_00320.Position 10.075 3.875 0
TP_L0_00320.Mother TES_L0
TP_L0_00320.Visibility 0

TES_Pixel_L0.Copy TP_L0_00321
TP_L0_00321.Position 10.075 5.425 0
TP_L0_00321.Mother TES_L0
TP_L0_00321.Visibility 0

TES_Pixel_L0.Copy TP_L0_00322
TP_L0_00322.Position 10.075 6.975 0
TP_L0_00322.Mother TES_L0
TP_L0_00322.Visibility 0

TES_Pixel_L0.Copy TP_L0_00323
TP_L0_00323.Position 10.075 8.525 0
TP_L0_00323.Mother TES_L0
TP_L0_00323.Visibility 0

TES_Pixel_L0.Copy TP_L0_00324
TP_L0_00324.Position 10.075 10.075 0
TP_L0_00324.Mother TES_L0
TP_L0_00324.Visibility 0

TES_Pixel_L0.Copy TP_L0_00325
TP_L0_00325.Position 10.075 11.625 0
TP_L0_00325.Mother TES_L0
TP_L0_00325.Visibility 0

TES_Pixel_L0.Copy TP_L0_00326
TP_L0_00326.Position 10.075 13.175 0
TP_L0_00326.Mother TES_L0
TP_L0_00326.Visibility 0

TES_Pixel_L0.Copy TP_L0_00327
TP_L0_00327.Position 10.075 14.725 0
TP_L0_00327.Mother TES_L0
TP_L0_00327.Visibility 0

TES_Pixel_L0.Copy TP_L0_00328
TP_L0_00328.Position 11.625 -13.175 0
TP_L0_00328.Mother TES_L0
TP_L0_00328.Visibility 0

TES_Pixel_L0.Copy TP_L0_00329
TP_L0_00329.Position 11.625 -11.625 0
TP_L0_00329.Mother TES_L0
TP_L0_00329.Visibility 0

TES_Pixel_L0.Copy TP_L0_00330
TP_L0_00330.Position 11.625 -10.075 0
TP_L0_00330.Mother TES_L0
TP_L0_00330.Visibility 0

TES_Pixel_L0.Copy TP_L0_00331
TP_L0_00331.Position 11.625 -8.525 0
TP_L0_00331.Mother TES_L0
TP_L0_00331.Visibility 0

TES_Pixel_L0.Copy TP_L0_00332
TP_L0_00332.Position 11.625 -6.975 0
TP_L0_00332.Mother TES_L0
TP_L0_00332.Visibility 0

TES_Pixel_L0.Copy TP_L0_00333
TP_L0_00333.Position 11.625 -5.425 0
TP_L0_00333.Mother TES_L0
TP_L0_00333.Visibility 0

TES_Pixel_L0.Copy TP_L0_00334
TP_L0_00334.Position 11.625 -3.875 0
TP_L0_00334.Mother TES_L0
TP_L0_00334.Visibility 0

TES_Pixel_L0.Copy TP_L0_00335
TP_L0_00335.Position 11.625 -2.325 0
TP_L0_00335.Mother TES_L0
TP_L0_00335.Visibility 0

TES_Pixel_L0.Copy TP_L0_00336
TP_L0_00336.Position 11.625 -0.775 0
TP_L0_00336.Mother TES_L0
TP_L0_00336.Visibility 0

TES_Pixel_L0.Copy TP_L0_00337
TP_L0_00337.Position 11.625 0.775 0
TP_L0_00337.Mother TES_L0
TP_L0_00337.Visibility 0

TES_Pixel_L0.Copy TP_L0_00338
TP_L0_00338.Position 11.625 2.325 0
TP_L0_00338.Mother TES_L0
TP_L0_00338.Visibility 0

TES_Pixel_L0.Copy TP_L0_00339
TP_L0_00339.Position 11.625 3.875 0
TP_L0_00339.Mother TES_L0
TP_L0_00339.Visibility 0

TES_Pixel_L0.Copy TP_L0_00340
TP_L0_00340.Position 11.625 5.425 0
TP_L0_00340.Mother TES_L0
TP_L0_00340.Visibility 0

TES_Pixel_L0.Copy TP_L0_00341
TP_L0_00341.Position 11.625 6.975 0
TP_L0_00341.Mother TES_L0
TP_L0_00341.Visibility 0

TES_Pixel_L0.Copy TP_L0_00342
TP_L0_00342.Position 11.625 8.525 0
TP_L0_00342.Mother TES_L0
TP_L0_00342.Visibility 0

TES_Pixel_L0.Copy TP_L0_00343
TP_L0_00343.Position 11.625 10.075 0
TP_L0_00343.Mother TES_L0
TP_L0_00343.Visibility 0

TES_Pixel_L0.Copy TP_L0_00344
TP_L0_00344.Position 11.625 11.625 0
TP_L0_00344.Mother TES_L0
TP_L0_00344.Visibility 0

TES_Pixel_L0.Copy TP_L0_00345
TP_L0_00345.Position 11.625 13.175 0
TP_L0_00345.Mother TES_L0
TP_L0_00345.Visibility 0

TES_Pixel_L0.Copy TP_L0_00346
TP_L0_00346.Position 13.175 -11.625 0
TP_L0_00346.Mother TES_L0
TP_L0_00346.Visibility 0

TES_Pixel_L0.Copy TP_L0_00347
TP_L0_00347.Position 13.175 -10.075 0
TP_L0_00347.Mother TES_L0
TP_L0_00347.Visibility 0

TES_Pixel_L0.Copy TP_L0_00348
TP_L0_00348.Position 13.175 -8.525 0
TP_L0_00348.Mother TES_L0
TP_L0_00348.Visibility 0

TES_Pixel_L0.Copy TP_L0_00349
TP_L0_00349.Position 13.175 -6.975 0
TP_L0_00349.Mother TES_L0
TP_L0_00349.Visibility 0

TES_Pixel_L0.Copy TP_L0_00350
TP_L0_00350.Position 13.175 -5.425 0
TP_L0_00350.Mother TES_L0
TP_L0_00350.Visibility 0

TES_Pixel_L0.Copy TP_L0_00351
TP_L0_00351.Position 13.175 -3.875 0
TP_L0_00351.Mother TES_L0
TP_L0_00351.Visibility 0

TES_Pixel_L0.Copy TP_L0_00352
TP_L0_00352.Position 13.175 -2.325 0
TP_L0_00352.Mother TES_L0
TP_L0_00352.Visibility 0

TES_Pixel_L0.Copy TP_L0_00353
TP_L0_00353.Position 13.175 -0.775 0
TP_L0_00353.Mother TES_L0
TP_L0_00353.Visibility 0

TES_Pixel_L0.Copy TP_L0_00354
TP_L0_00354.Position 13.175 0.775 0
TP_L0_00354.Mother TES_L0
TP_L0_00354.Visibility 0

TES_Pixel_L0.Copy TP_L0_00355
TP_L0_00355.Position 13.175 2.325 0
TP_L0_00355.Mother TES_L0
TP_L0_00355.Visibility 0

TES_Pixel_L0.Copy TP_L0_00356
TP_L0_00356.Position 13.175 3.875 0
TP_L0_00356.Mother TES_L0
TP_L0_00356.Visibility 0

TES_Pixel_L0.Copy TP_L0_00357
TP_L0_00357.Position 13.175 5.425 0
TP_L0_00357.Mother TES_L0
TP_L0_00357.Visibility 0

TES_Pixel_L0.Copy TP_L0_00358
TP_L0_00358.Position 13.175 6.975 0
TP_L0_00358.Mother TES_L0
TP_L0_00358.Visibility 0

TES_Pixel_L0.Copy TP_L0_00359
TP_L0_00359.Position 13.175 8.525 0
TP_L0_00359.Mother TES_L0
TP_L0_00359.Visibility 0

TES_Pixel_L0.Copy TP_L0_00360
TP_L0_00360.Position 13.175 10.075 0
TP_L0_00360.Mother TES_L0
TP_L0_00360.Visibility 0

TES_Pixel_L0.Copy TP_L0_00361
TP_L0_00361.Position 13.175 11.625 0
TP_L0_00361.Mother TES_L0
TP_L0_00361.Visibility 0

TES_Pixel_L0.Copy TP_L0_00362
TP_L0_00362.Position 14.725 -10.075 0
TP_L0_00362.Mother TES_L0
TP_L0_00362.Visibility 0

TES_Pixel_L0.Copy TP_L0_00363
TP_L0_00363.Position 14.725 -8.525 0
TP_L0_00363.Mother TES_L0
TP_L0_00363.Visibility 0

TES_Pixel_L0.Copy TP_L0_00364
TP_L0_00364.Position 14.725 -6.975 0
TP_L0_00364.Mother TES_L0
TP_L0_00364.Visibility 0

TES_Pixel_L0.Copy TP_L0_00365
TP_L0_00365.Position 14.725 -5.425 0
TP_L0_00365.Mother TES_L0
TP_L0_00365.Visibility 0

TES_Pixel_L0.Copy TP_L0_00366
TP_L0_00366.Position 14.725 -3.875 0
TP_L0_00366.Mother TES_L0
TP_L0_00366.Visibility 0

TES_Pixel_L0.Copy TP_L0_00367
TP_L0_00367.Position 14.725 -2.325 0
TP_L0_00367.Mother TES_L0
TP_L0_00367.Visibility 0

TES_Pixel_L0.Copy TP_L0_00368
TP_L0_00368.Position 14.725 -0.775 0
TP_L0_00368.Mother TES_L0
TP_L0_00368.Visibility 0

TES_Pixel_L0.Copy TP_L0_00369
TP_L0_00369.Position 14.725 0.775 0
TP_L0_00369.Mother TES_L0
TP_L0_00369.Visibility 0

TES_Pixel_L0.Copy TP_L0_00370
TP_L0_00370.Position 14.725 2.325 0
TP_L0_00370.Mother TES_L0
TP_L0_00370.Visibility 0

TES_Pixel_L0.Copy TP_L0_00371
TP_L0_00371.Position 14.725 3.875 0
TP_L0_00371.Mother TES_L0
TP_L0_00371.Visibility 0

TES_Pixel_L0.Copy TP_L0_00372
TP_L0_00372.Position 14.725 5.425 0
TP_L0_00372.Mother TES_L0
TP_L0_00372.Visibility 0

TES_Pixel_L0.Copy TP_L0_00373
TP_L0_00373.Position 14.725 6.975 0
TP_L0_00373.Mother TES_L0
TP_L0_00373.Visibility 0

TES_Pixel_L0.Copy TP_L0_00374
TP_L0_00374.Position 14.725 8.525 0
TP_L0_00374.Mother TES_L0
TP_L0_00374.Visibility 0

TES_Pixel_L0.Copy TP_L0_00375
TP_L0_00375.Position 14.725 10.075 0
TP_L0_00375.Mother TES_L0
TP_L0_00375.Visibility 0

Substrate_L1.Position 0 0 22
Substrate_L1.Mother WorldVolume

TES_L1.Position 0 0 23.65
TES_L1.Mother WorldVolume
TES_L1.Visibility 0

TES_Pixel_L1.Copy TP_L1_00000
TP_L1_00000.Position -14.725 -10.075 0
TP_L1_00000.Mother TES_L1
TP_L1_00000.Visibility 0

TES_Pixel_L1.Copy TP_L1_00001
TP_L1_00001.Position -14.725 -8.525 0
TP_L1_00001.Mother TES_L1
TP_L1_00001.Visibility 0

TES_Pixel_L1.Copy TP_L1_00002
TP_L1_00002.Position -14.725 -6.975 0
TP_L1_00002.Mother TES_L1
TP_L1_00002.Visibility 0

TES_Pixel_L1.Copy TP_L1_00003
TP_L1_00003.Position -14.725 -5.425 0
TP_L1_00003.Mother TES_L1
TP_L1_00003.Visibility 0

TES_Pixel_L1.Copy TP_L1_00004
TP_L1_00004.Position -14.725 -3.875 0
TP_L1_00004.Mother TES_L1
TP_L1_00004.Visibility 0

TES_Pixel_L1.Copy TP_L1_00005
TP_L1_00005.Position -14.725 -2.325 0
TP_L1_00005.Mother TES_L1
TP_L1_00005.Visibility 0

TES_Pixel_L1.Copy TP_L1_00006
TP_L1_00006.Position -14.725 -0.775 0
TP_L1_00006.Mother TES_L1
TP_L1_00006.Visibility 0

TES_Pixel_L1.Copy TP_L1_00007
TP_L1_00007.Position -14.725 0.775 0
TP_L1_00007.Mother TES_L1
TP_L1_00007.Visibility 0

TES_Pixel_L1.Copy TP_L1_00008
TP_L1_00008.Position -14.725 2.325 0
TP_L1_00008.Mother TES_L1
TP_L1_00008.Visibility 0

TES_Pixel_L1.Copy TP_L1_00009
TP_L1_00009.Position -14.725 3.875 0
TP_L1_00009.Mother TES_L1
TP_L1_00009.Visibility 0

TES_Pixel_L1.Copy TP_L1_00010
TP_L1_00010.Position -14.725 5.425 0
TP_L1_00010.Mother TES_L1
TP_L1_00010.Visibility 0

TES_Pixel_L1.Copy TP_L1_00011
TP_L1_00011.Position -14.725 6.975 0
TP_L1_00011.Mother TES_L1
TP_L1_00011.Visibility 0

TES_Pixel_L1.Copy TP_L1_00012
TP_L1_00012.Position -14.725 8.525 0
TP_L1_00012.Mother TES_L1
TP_L1_00012.Visibility 0

TES_Pixel_L1.Copy TP_L1_00013
TP_L1_00013.Position -14.725 10.075 0
TP_L1_00013.Mother TES_L1
TP_L1_00013.Visibility 0

TES_Pixel_L1.Copy TP_L1_00014
TP_L1_00014.Position -13.175 -11.625 0
TP_L1_00014.Mother TES_L1
TP_L1_00014.Visibility 0

TES_Pixel_L1.Copy TP_L1_00015
TP_L1_00015.Position -13.175 -10.075 0
TP_L1_00015.Mother TES_L1
TP_L1_00015.Visibility 0

TES_Pixel_L1.Copy TP_L1_00016
TP_L1_00016.Position -13.175 -8.525 0
TP_L1_00016.Mother TES_L1
TP_L1_00016.Visibility 0

TES_Pixel_L1.Copy TP_L1_00017
TP_L1_00017.Position -13.175 -6.975 0
TP_L1_00017.Mother TES_L1
TP_L1_00017.Visibility 0

TES_Pixel_L1.Copy TP_L1_00018
TP_L1_00018.Position -13.175 -5.425 0
TP_L1_00018.Mother TES_L1
TP_L1_00018.Visibility 0

TES_Pixel_L1.Copy TP_L1_00019
TP_L1_00019.Position -13.175 -3.875 0
TP_L1_00019.Mother TES_L1
TP_L1_00019.Visibility 0

TES_Pixel_L1.Copy TP_L1_00020
TP_L1_00020.Position -13.175 -2.325 0
TP_L1_00020.Mother TES_L1
TP_L1_00020.Visibility 0

TES_Pixel_L1.Copy TP_L1_00021
TP_L1_00021.Position -13.175 -0.775 0
TP_L1_00021.Mother TES_L1
TP_L1_00021.Visibility 0

TES_Pixel_L1.Copy TP_L1_00022
TP_L1_00022.Position -13.175 0.775 0
TP_L1_00022.Mother TES_L1
TP_L1_00022.Visibility 0

TES_Pixel_L1.Copy TP_L1_00023
TP_L1_00023.Position -13.175 2.325 0
TP_L1_00023.Mother TES_L1
TP_L1_00023.Visibility 0

TES_Pixel_L1.Copy TP_L1_00024
TP_L1_00024.Position -13.175 3.875 0
TP_L1_00024.Mother TES_L1
TP_L1_00024.Visibility 0

TES_Pixel_L1.Copy TP_L1_00025
TP_L1_00025.Position -13.175 5.425 0
TP_L1_00025.Mother TES_L1
TP_L1_00025.Visibility 0

TES_Pixel_L1.Copy TP_L1_00026
TP_L1_00026.Position -13.175 6.975 0
TP_L1_00026.Mother TES_L1
TP_L1_00026.Visibility 0

TES_Pixel_L1.Copy TP_L1_00027
TP_L1_00027.Position -13.175 8.525 0
TP_L1_00027.Mother TES_L1
TP_L1_00027.Visibility 0

TES_Pixel_L1.Copy TP_L1_00028
TP_L1_00028.Position -13.175 10.075 0
TP_L1_00028.Mother TES_L1
TP_L1_00028.Visibility 0

TES_Pixel_L1.Copy TP_L1_00029
TP_L1_00029.Position -13.175 11.625 0
TP_L1_00029.Mother TES_L1
TP_L1_00029.Visibility 0

TES_Pixel_L1.Copy TP_L1_00030
TP_L1_00030.Position -11.625 -13.175 0
TP_L1_00030.Mother TES_L1
TP_L1_00030.Visibility 0

TES_Pixel_L1.Copy TP_L1_00031
TP_L1_00031.Position -11.625 -11.625 0
TP_L1_00031.Mother TES_L1
TP_L1_00031.Visibility 0

TES_Pixel_L1.Copy TP_L1_00032
TP_L1_00032.Position -11.625 -10.075 0
TP_L1_00032.Mother TES_L1
TP_L1_00032.Visibility 0

TES_Pixel_L1.Copy TP_L1_00033
TP_L1_00033.Position -11.625 -8.525 0
TP_L1_00033.Mother TES_L1
TP_L1_00033.Visibility 0

TES_Pixel_L1.Copy TP_L1_00034
TP_L1_00034.Position -11.625 -6.975 0
TP_L1_00034.Mother TES_L1
TP_L1_00034.Visibility 0

TES_Pixel_L1.Copy TP_L1_00035
TP_L1_00035.Position -11.625 -5.425 0
TP_L1_00035.Mother TES_L1
TP_L1_00035.Visibility 0

TES_Pixel_L1.Copy TP_L1_00036
TP_L1_00036.Position -11.625 -3.875 0
TP_L1_00036.Mother TES_L1
TP_L1_00036.Visibility 0

TES_Pixel_L1.Copy TP_L1_00037
TP_L1_00037.Position -11.625 -2.325 0
TP_L1_00037.Mother TES_L1
TP_L1_00037.Visibility 0

TES_Pixel_L1.Copy TP_L1_00038
TP_L1_00038.Position -11.625 -0.775 0
TP_L1_00038.Mother TES_L1
TP_L1_00038.Visibility 0

TES_Pixel_L1.Copy TP_L1_00039
TP_L1_00039.Position -11.625 0.775 0
TP_L1_00039.Mother TES_L1
TP_L1_00039.Visibility 0

TES_Pixel_L1.Copy TP_L1_00040
TP_L1_00040.Position -11.625 2.325 0
TP_L1_00040.Mother TES_L1
TP_L1_00040.Visibility 0

TES_Pixel_L1.Copy TP_L1_00041
TP_L1_00041.Position -11.625 3.875 0
TP_L1_00041.Mother TES_L1
TP_L1_00041.Visibility 0

TES_Pixel_L1.Copy TP_L1_00042
TP_L1_00042.Position -11.625 5.425 0
TP_L1_00042.Mother TES_L1
TP_L1_00042.Visibility 0

TES_Pixel_L1.Copy TP_L1_00043
TP_L1_00043.Position -11.625 6.975 0
TP_L1_00043.Mother TES_L1
TP_L1_00043.Visibility 0

TES_Pixel_L1.Copy TP_L1_00044
TP_L1_00044.Position -11.625 8.525 0
TP_L1_00044.Mother TES_L1
TP_L1_00044.Visibility 0

TES_Pixel_L1.Copy TP_L1_00045
TP_L1_00045.Position -11.625 10.075 0
TP_L1_00045.Mother TES_L1
TP_L1_00045.Visibility 0

TES_Pixel_L1.Copy TP_L1_00046
TP_L1_00046.Position -11.625 11.625 0
TP_L1_00046.Mother TES_L1
TP_L1_00046.Visibility 0

TES_Pixel_L1.Copy TP_L1_00047
TP_L1_00047.Position -11.625 13.175 0
TP_L1_00047.Mother TES_L1
TP_L1_00047.Visibility 0

TES_Pixel_L1.Copy TP_L1_00048
TP_L1_00048.Position -10.075 -14.725 0
TP_L1_00048.Mother TES_L1
TP_L1_00048.Visibility 0

TES_Pixel_L1.Copy TP_L1_00049
TP_L1_00049.Position -10.075 -13.175 0
TP_L1_00049.Mother TES_L1
TP_L1_00049.Visibility 0

TES_Pixel_L1.Copy TP_L1_00050
TP_L1_00050.Position -10.075 -11.625 0
TP_L1_00050.Mother TES_L1
TP_L1_00050.Visibility 0

TES_Pixel_L1.Copy TP_L1_00051
TP_L1_00051.Position -10.075 -10.075 0
TP_L1_00051.Mother TES_L1
TP_L1_00051.Visibility 0

TES_Pixel_L1.Copy TP_L1_00052
TP_L1_00052.Position -10.075 -8.525 0
TP_L1_00052.Mother TES_L1
TP_L1_00052.Visibility 0

TES_Pixel_L1.Copy TP_L1_00053
TP_L1_00053.Position -10.075 -6.975 0
TP_L1_00053.Mother TES_L1
TP_L1_00053.Visibility 0

TES_Pixel_L1.Copy TP_L1_00054
TP_L1_00054.Position -10.075 -5.425 0
TP_L1_00054.Mother TES_L1
TP_L1_00054.Visibility 0

TES_Pixel_L1.Copy TP_L1_00055
TP_L1_00055.Position -10.075 -3.875 0
TP_L1_00055.Mother TES_L1
TP_L1_00055.Visibility 0

TES_Pixel_L1.Copy TP_L1_00056
TP_L1_00056.Position -10.075 -2.325 0
TP_L1_00056.Mother TES_L1
TP_L1_00056.Visibility 0

TES_Pixel_L1.Copy TP_L1_00057
TP_L1_00057.Position -10.075 -0.775 0
TP_L1_00057.Mother TES_L1
TP_L1_00057.Visibility 0

TES_Pixel_L1.Copy TP_L1_00058
TP_L1_00058.Position -10.075 0.775 0
TP_L1_00058.Mother TES_L1
TP_L1_00058.Visibility 0

TES_Pixel_L1.Copy TP_L1_00059
TP_L1_00059.Position -10.075 2.325 0
TP_L1_00059.Mother TES_L1
TP_L1_00059.Visibility 0

TES_Pixel_L1.Copy TP_L1_00060
TP_L1_00060.Position -10.075 3.875 0
TP_L1_00060.Mother TES_L1
TP_L1_00060.Visibility 0

TES_Pixel_L1.Copy TP_L1_00061
TP_L1_00061.Position -10.075 5.425 0
TP_L1_00061.Mother TES_L1
TP_L1_00061.Visibility 0

TES_Pixel_L1.Copy TP_L1_00062
TP_L1_00062.Position -10.075 6.975 0
TP_L1_00062.Mother TES_L1
TP_L1_00062.Visibility 0

TES_Pixel_L1.Copy TP_L1_00063
TP_L1_00063.Position -10.075 8.525 0
TP_L1_00063.Mother TES_L1
TP_L1_00063.Visibility 0

TES_Pixel_L1.Copy TP_L1_00064
TP_L1_00064.Position -10.075 10.075 0
TP_L1_00064.Mother TES_L1
TP_L1_00064.Visibility 0

TES_Pixel_L1.Copy TP_L1_00065
TP_L1_00065.Position -10.075 11.625 0
TP_L1_00065.Mother TES_L1
TP_L1_00065.Visibility 0

TES_Pixel_L1.Copy TP_L1_00066
TP_L1_00066.Position -10.075 13.175 0
TP_L1_00066.Mother TES_L1
TP_L1_00066.Visibility 0

TES_Pixel_L1.Copy TP_L1_00067
TP_L1_00067.Position -10.075 14.725 0
TP_L1_00067.Mother TES_L1
TP_L1_00067.Visibility 0

TES_Pixel_L1.Copy TP_L1_00068
TP_L1_00068.Position -8.525 -14.725 0
TP_L1_00068.Mother TES_L1
TP_L1_00068.Visibility 0

TES_Pixel_L1.Copy TP_L1_00069
TP_L1_00069.Position -8.525 -13.175 0
TP_L1_00069.Mother TES_L1
TP_L1_00069.Visibility 0

TES_Pixel_L1.Copy TP_L1_00070
TP_L1_00070.Position -8.525 -11.625 0
TP_L1_00070.Mother TES_L1
TP_L1_00070.Visibility 0

TES_Pixel_L1.Copy TP_L1_00071
TP_L1_00071.Position -8.525 -10.075 0
TP_L1_00071.Mother TES_L1
TP_L1_00071.Visibility 0

TES_Pixel_L1.Copy TP_L1_00072
TP_L1_00072.Position -8.525 -8.525 0
TP_L1_00072.Mother TES_L1
TP_L1_00072.Visibility 0

TES_Pixel_L1.Copy TP_L1_00073
TP_L1_00073.Position -8.525 -6.975 0
TP_L1_00073.Mother TES_L1
TP_L1_00073.Visibility 0

TES_Pixel_L1.Copy TP_L1_00074
TP_L1_00074.Position -8.525 -5.425 0
TP_L1_00074.Mother TES_L1
TP_L1_00074.Visibility 0

TES_Pixel_L1.Copy TP_L1_00075
TP_L1_00075.Position -8.525 -3.875 0
TP_L1_00075.Mother TES_L1
TP_L1_00075.Visibility 0

TES_Pixel_L1.Copy TP_L1_00076
TP_L1_00076.Position -8.525 -2.325 0
TP_L1_00076.Mother TES_L1
TP_L1_00076.Visibility 0

TES_Pixel_L1.Copy TP_L1_00077
TP_L1_00077.Position -8.525 -0.775 0
TP_L1_00077.Mother TES_L1
TP_L1_00077.Visibility 0

TES_Pixel_L1.Copy TP_L1_00078
TP_L1_00078.Position -8.525 0.775 0
TP_L1_00078.Mother TES_L1
TP_L1_00078.Visibility 0

TES_Pixel_L1.Copy TP_L1_00079
TP_L1_00079.Position -8.525 2.325 0
TP_L1_00079.Mother TES_L1
TP_L1_00079.Visibility 0

TES_Pixel_L1.Copy TP_L1_00080
TP_L1_00080.Position -8.525 3.875 0
TP_L1_00080.Mother TES_L1
TP_L1_00080.Visibility 0

TES_Pixel_L1.Copy TP_L1_00081
TP_L1_00081.Position -8.525 5.425 0
TP_L1_00081.Mother TES_L1
TP_L1_00081.Visibility 0

TES_Pixel_L1.Copy TP_L1_00082
TP_L1_00082.Position -8.525 6.975 0
TP_L1_00082.Mother TES_L1
TP_L1_00082.Visibility 0

TES_Pixel_L1.Copy TP_L1_00083
TP_L1_00083.Position -8.525 8.525 0
TP_L1_00083.Mother TES_L1
TP_L1_00083.Visibility 0

TES_Pixel_L1.Copy TP_L1_00084
TP_L1_00084.Position -8.525 10.075 0
TP_L1_00084.Mother TES_L1
TP_L1_00084.Visibility 0

TES_Pixel_L1.Copy TP_L1_00085
TP_L1_00085.Position -8.525 11.625 0
TP_L1_00085.Mother TES_L1
TP_L1_00085.Visibility 0

TES_Pixel_L1.Copy TP_L1_00086
TP_L1_00086.Position -8.525 13.175 0
TP_L1_00086.Mother TES_L1
TP_L1_00086.Visibility 0

TES_Pixel_L1.Copy TP_L1_00087
TP_L1_00087.Position -8.525 14.725 0
TP_L1_00087.Mother TES_L1
TP_L1_00087.Visibility 0

TES_Pixel_L1.Copy TP_L1_00088
TP_L1_00088.Position -6.975 -14.725 0
TP_L1_00088.Mother TES_L1
TP_L1_00088.Visibility 0

TES_Pixel_L1.Copy TP_L1_00089
TP_L1_00089.Position -6.975 -13.175 0
TP_L1_00089.Mother TES_L1
TP_L1_00089.Visibility 0

TES_Pixel_L1.Copy TP_L1_00090
TP_L1_00090.Position -6.975 -11.625 0
TP_L1_00090.Mother TES_L1
TP_L1_00090.Visibility 0

TES_Pixel_L1.Copy TP_L1_00091
TP_L1_00091.Position -6.975 -10.075 0
TP_L1_00091.Mother TES_L1
TP_L1_00091.Visibility 0

TES_Pixel_L1.Copy TP_L1_00092
TP_L1_00092.Position -6.975 -8.525 0
TP_L1_00092.Mother TES_L1
TP_L1_00092.Visibility 0

TES_Pixel_L1.Copy TP_L1_00093
TP_L1_00093.Position -6.975 -6.975 0
TP_L1_00093.Mother TES_L1
TP_L1_00093.Visibility 0

TES_Pixel_L1.Copy TP_L1_00094
TP_L1_00094.Position -6.975 -5.425 0
TP_L1_00094.Mother TES_L1
TP_L1_00094.Visibility 0

TES_Pixel_L1.Copy TP_L1_00095
TP_L1_00095.Position -6.975 -3.875 0
TP_L1_00095.Mother TES_L1
TP_L1_00095.Visibility 0

TES_Pixel_L1.Copy TP_L1_00096
TP_L1_00096.Position -6.975 -2.325 0
TP_L1_00096.Mother TES_L1
TP_L1_00096.Visibility 0

TES_Pixel_L1.Copy TP_L1_00097
TP_L1_00097.Position -6.975 -0.775 0
TP_L1_00097.Mother TES_L1
TP_L1_00097.Visibility 0

TES_Pixel_L1.Copy TP_L1_00098
TP_L1_00098.Position -6.975 0.775 0
TP_L1_00098.Mother TES_L1
TP_L1_00098.Visibility 0

TES_Pixel_L1.Copy TP_L1_00099
TP_L1_00099.Position -6.975 2.325 0
TP_L1_00099.Mother TES_L1
TP_L1_00099.Visibility 0

TES_Pixel_L1.Copy TP_L1_00100
TP_L1_00100.Position -6.975 3.875 0
TP_L1_00100.Mother TES_L1
TP_L1_00100.Visibility 0

TES_Pixel_L1.Copy TP_L1_00101
TP_L1_00101.Position -6.975 5.425 0
TP_L1_00101.Mother TES_L1
TP_L1_00101.Visibility 0

TES_Pixel_L1.Copy TP_L1_00102
TP_L1_00102.Position -6.975 6.975 0
TP_L1_00102.Mother TES_L1
TP_L1_00102.Visibility 0

TES_Pixel_L1.Copy TP_L1_00103
TP_L1_00103.Position -6.975 8.525 0
TP_L1_00103.Mother TES_L1
TP_L1_00103.Visibility 0

TES_Pixel_L1.Copy TP_L1_00104
TP_L1_00104.Position -6.975 10.075 0
TP_L1_00104.Mother TES_L1
TP_L1_00104.Visibility 0

TES_Pixel_L1.Copy TP_L1_00105
TP_L1_00105.Position -6.975 11.625 0
TP_L1_00105.Mother TES_L1
TP_L1_00105.Visibility 0

TES_Pixel_L1.Copy TP_L1_00106
TP_L1_00106.Position -6.975 13.175 0
TP_L1_00106.Mother TES_L1
TP_L1_00106.Visibility 0

TES_Pixel_L1.Copy TP_L1_00107
TP_L1_00107.Position -6.975 14.725 0
TP_L1_00107.Mother TES_L1
TP_L1_00107.Visibility 0

TES_Pixel_L1.Copy TP_L1_00108
TP_L1_00108.Position -5.425 -14.725 0
TP_L1_00108.Mother TES_L1
TP_L1_00108.Visibility 0

TES_Pixel_L1.Copy TP_L1_00109
TP_L1_00109.Position -5.425 -13.175 0
TP_L1_00109.Mother TES_L1
TP_L1_00109.Visibility 0

TES_Pixel_L1.Copy TP_L1_00110
TP_L1_00110.Position -5.425 -11.625 0
TP_L1_00110.Mother TES_L1
TP_L1_00110.Visibility 0

TES_Pixel_L1.Copy TP_L1_00111
TP_L1_00111.Position -5.425 -10.075 0
TP_L1_00111.Mother TES_L1
TP_L1_00111.Visibility 0

TES_Pixel_L1.Copy TP_L1_00112
TP_L1_00112.Position -5.425 -8.525 0
TP_L1_00112.Mother TES_L1
TP_L1_00112.Visibility 0

TES_Pixel_L1.Copy TP_L1_00113
TP_L1_00113.Position -5.425 -6.975 0
TP_L1_00113.Mother TES_L1
TP_L1_00113.Visibility 0

TES_Pixel_L1.Copy TP_L1_00114
TP_L1_00114.Position -5.425 -5.425 0
TP_L1_00114.Mother TES_L1
TP_L1_00114.Visibility 0

TES_Pixel_L1.Copy TP_L1_00115
TP_L1_00115.Position -5.425 -3.875 0
TP_L1_00115.Mother TES_L1
TP_L1_00115.Visibility 0

TES_Pixel_L1.Copy TP_L1_00116
TP_L1_00116.Position -5.425 -2.325 0
TP_L1_00116.Mother TES_L1
TP_L1_00116.Visibility 0

TES_Pixel_L1.Copy TP_L1_00117
TP_L1_00117.Position -5.425 -0.775 0
TP_L1_00117.Mother TES_L1
TP_L1_00117.Visibility 0

TES_Pixel_L1.Copy TP_L1_00118
TP_L1_00118.Position -5.425 0.775 0
TP_L1_00118.Mother TES_L1
TP_L1_00118.Visibility 0

TES_Pixel_L1.Copy TP_L1_00119
TP_L1_00119.Position -5.425 2.325 0
TP_L1_00119.Mother TES_L1
TP_L1_00119.Visibility 0

TES_Pixel_L1.Copy TP_L1_00120
TP_L1_00120.Position -5.425 3.875 0
TP_L1_00120.Mother TES_L1
TP_L1_00120.Visibility 0

TES_Pixel_L1.Copy TP_L1_00121
TP_L1_00121.Position -5.425 5.425 0
TP_L1_00121.Mother TES_L1
TP_L1_00121.Visibility 0

TES_Pixel_L1.Copy TP_L1_00122
TP_L1_00122.Position -5.425 6.975 0
TP_L1_00122.Mother TES_L1
TP_L1_00122.Visibility 0

TES_Pixel_L1.Copy TP_L1_00123
TP_L1_00123.Position -5.425 8.525 0
TP_L1_00123.Mother TES_L1
TP_L1_00123.Visibility 0

TES_Pixel_L1.Copy TP_L1_00124
TP_L1_00124.Position -5.425 10.075 0
TP_L1_00124.Mother TES_L1
TP_L1_00124.Visibility 0

TES_Pixel_L1.Copy TP_L1_00125
TP_L1_00125.Position -5.425 11.625 0
TP_L1_00125.Mother TES_L1
TP_L1_00125.Visibility 0

TES_Pixel_L1.Copy TP_L1_00126
TP_L1_00126.Position -5.425 13.175 0
TP_L1_00126.Mother TES_L1
TP_L1_00126.Visibility 0

TES_Pixel_L1.Copy TP_L1_00127
TP_L1_00127.Position -5.425 14.725 0
TP_L1_00127.Mother TES_L1
TP_L1_00127.Visibility 0

TES_Pixel_L1.Copy TP_L1_00128
TP_L1_00128.Position -3.875 -14.725 0
TP_L1_00128.Mother TES_L1
TP_L1_00128.Visibility 0

TES_Pixel_L1.Copy TP_L1_00129
TP_L1_00129.Position -3.875 -13.175 0
TP_L1_00129.Mother TES_L1
TP_L1_00129.Visibility 0

TES_Pixel_L1.Copy TP_L1_00130
TP_L1_00130.Position -3.875 -11.625 0
TP_L1_00130.Mother TES_L1
TP_L1_00130.Visibility 0

TES_Pixel_L1.Copy TP_L1_00131
TP_L1_00131.Position -3.875 -10.075 0
TP_L1_00131.Mother TES_L1
TP_L1_00131.Visibility 0

TES_Pixel_L1.Copy TP_L1_00132
TP_L1_00132.Position -3.875 -8.525 0
TP_L1_00132.Mother TES_L1
TP_L1_00132.Visibility 0

TES_Pixel_L1.Copy TP_L1_00133
TP_L1_00133.Position -3.875 -6.975 0
TP_L1_00133.Mother TES_L1
TP_L1_00133.Visibility 0

TES_Pixel_L1.Copy TP_L1_00134
TP_L1_00134.Position -3.875 -5.425 0
TP_L1_00134.Mother TES_L1
TP_L1_00134.Visibility 0

TES_Pixel_L1.Copy TP_L1_00135
TP_L1_00135.Position -3.875 -3.875 0
TP_L1_00135.Mother TES_L1
TP_L1_00135.Visibility 0

TES_Pixel_L1.Copy TP_L1_00136
TP_L1_00136.Position -3.875 -2.325 0
TP_L1_00136.Mother TES_L1
TP_L1_00136.Visibility 0

TES_Pixel_L1.Copy TP_L1_00137
TP_L1_00137.Position -3.875 -0.775 0
TP_L1_00137.Mother TES_L1
TP_L1_00137.Visibility 0

TES_Pixel_L1.Copy TP_L1_00138
TP_L1_00138.Position -3.875 0.775 0
TP_L1_00138.Mother TES_L1
TP_L1_00138.Visibility 0

TES_Pixel_L1.Copy TP_L1_00139
TP_L1_00139.Position -3.875 2.325 0
TP_L1_00139.Mother TES_L1
TP_L1_00139.Visibility 0

TES_Pixel_L1.Copy TP_L1_00140
TP_L1_00140.Position -3.875 3.875 0
TP_L1_00140.Mother TES_L1
TP_L1_00140.Visibility 0

TES_Pixel_L1.Copy TP_L1_00141
TP_L1_00141.Position -3.875 5.425 0
TP_L1_00141.Mother TES_L1
TP_L1_00141.Visibility 0

TES_Pixel_L1.Copy TP_L1_00142
TP_L1_00142.Position -3.875 6.975 0
TP_L1_00142.Mother TES_L1
TP_L1_00142.Visibility 0

TES_Pixel_L1.Copy TP_L1_00143
TP_L1_00143.Position -3.875 8.525 0
TP_L1_00143.Mother TES_L1
TP_L1_00143.Visibility 0

TES_Pixel_L1.Copy TP_L1_00144
TP_L1_00144.Position -3.875 10.075 0
TP_L1_00144.Mother TES_L1
TP_L1_00144.Visibility 0

TES_Pixel_L1.Copy TP_L1_00145
TP_L1_00145.Position -3.875 11.625 0
TP_L1_00145.Mother TES_L1
TP_L1_00145.Visibility 0

TES_Pixel_L1.Copy TP_L1_00146
TP_L1_00146.Position -3.875 13.175 0
TP_L1_00146.Mother TES_L1
TP_L1_00146.Visibility 0

TES_Pixel_L1.Copy TP_L1_00147
TP_L1_00147.Position -3.875 14.725 0
TP_L1_00147.Mother TES_L1
TP_L1_00147.Visibility 0

TES_Pixel_L1.Copy TP_L1_00148
TP_L1_00148.Position -2.325 -14.725 0
TP_L1_00148.Mother TES_L1
TP_L1_00148.Visibility 0

TES_Pixel_L1.Copy TP_L1_00149
TP_L1_00149.Position -2.325 -13.175 0
TP_L1_00149.Mother TES_L1
TP_L1_00149.Visibility 0

TES_Pixel_L1.Copy TP_L1_00150
TP_L1_00150.Position -2.325 -11.625 0
TP_L1_00150.Mother TES_L1
TP_L1_00150.Visibility 0

TES_Pixel_L1.Copy TP_L1_00151
TP_L1_00151.Position -2.325 -10.075 0
TP_L1_00151.Mother TES_L1
TP_L1_00151.Visibility 0

TES_Pixel_L1.Copy TP_L1_00152
TP_L1_00152.Position -2.325 -8.525 0
TP_L1_00152.Mother TES_L1
TP_L1_00152.Visibility 0

TES_Pixel_L1.Copy TP_L1_00153
TP_L1_00153.Position -2.325 -6.975 0
TP_L1_00153.Mother TES_L1
TP_L1_00153.Visibility 0

TES_Pixel_L1.Copy TP_L1_00154
TP_L1_00154.Position -2.325 -5.425 0
TP_L1_00154.Mother TES_L1
TP_L1_00154.Visibility 0

TES_Pixel_L1.Copy TP_L1_00155
TP_L1_00155.Position -2.325 -3.875 0
TP_L1_00155.Mother TES_L1
TP_L1_00155.Visibility 0

TES_Pixel_L1.Copy TP_L1_00156
TP_L1_00156.Position -2.325 -2.325 0
TP_L1_00156.Mother TES_L1
TP_L1_00156.Visibility 0

TES_Pixel_L1.Copy TP_L1_00157
TP_L1_00157.Position -2.325 -0.775 0
TP_L1_00157.Mother TES_L1
TP_L1_00157.Visibility 0

TES_Pixel_L1.Copy TP_L1_00158
TP_L1_00158.Position -2.325 0.775 0
TP_L1_00158.Mother TES_L1
TP_L1_00158.Visibility 0

TES_Pixel_L1.Copy TP_L1_00159
TP_L1_00159.Position -2.325 2.325 0
TP_L1_00159.Mother TES_L1
TP_L1_00159.Visibility 0

TES_Pixel_L1.Copy TP_L1_00160
TP_L1_00160.Position -2.325 3.875 0
TP_L1_00160.Mother TES_L1
TP_L1_00160.Visibility 0

TES_Pixel_L1.Copy TP_L1_00161
TP_L1_00161.Position -2.325 5.425 0
TP_L1_00161.Mother TES_L1
TP_L1_00161.Visibility 0

TES_Pixel_L1.Copy TP_L1_00162
TP_L1_00162.Position -2.325 6.975 0
TP_L1_00162.Mother TES_L1
TP_L1_00162.Visibility 0

TES_Pixel_L1.Copy TP_L1_00163
TP_L1_00163.Position -2.325 8.525 0
TP_L1_00163.Mother TES_L1
TP_L1_00163.Visibility 0

TES_Pixel_L1.Copy TP_L1_00164
TP_L1_00164.Position -2.325 10.075 0
TP_L1_00164.Mother TES_L1
TP_L1_00164.Visibility 0

TES_Pixel_L1.Copy TP_L1_00165
TP_L1_00165.Position -2.325 11.625 0
TP_L1_00165.Mother TES_L1
TP_L1_00165.Visibility 0

TES_Pixel_L1.Copy TP_L1_00166
TP_L1_00166.Position -2.325 13.175 0
TP_L1_00166.Mother TES_L1
TP_L1_00166.Visibility 0

TES_Pixel_L1.Copy TP_L1_00167
TP_L1_00167.Position -2.325 14.725 0
TP_L1_00167.Mother TES_L1
TP_L1_00167.Visibility 0

TES_Pixel_L1.Copy TP_L1_00168
TP_L1_00168.Position -0.775 -14.725 0
TP_L1_00168.Mother TES_L1
TP_L1_00168.Visibility 0

TES_Pixel_L1.Copy TP_L1_00169
TP_L1_00169.Position -0.775 -13.175 0
TP_L1_00169.Mother TES_L1
TP_L1_00169.Visibility 0

TES_Pixel_L1.Copy TP_L1_00170
TP_L1_00170.Position -0.775 -11.625 0
TP_L1_00170.Mother TES_L1
TP_L1_00170.Visibility 0

TES_Pixel_L1.Copy TP_L1_00171
TP_L1_00171.Position -0.775 -10.075 0
TP_L1_00171.Mother TES_L1
TP_L1_00171.Visibility 0

TES_Pixel_L1.Copy TP_L1_00172
TP_L1_00172.Position -0.775 -8.525 0
TP_L1_00172.Mother TES_L1
TP_L1_00172.Visibility 0

TES_Pixel_L1.Copy TP_L1_00173
TP_L1_00173.Position -0.775 -6.975 0
TP_L1_00173.Mother TES_L1
TP_L1_00173.Visibility 0

TES_Pixel_L1.Copy TP_L1_00174
TP_L1_00174.Position -0.775 -5.425 0
TP_L1_00174.Mother TES_L1
TP_L1_00174.Visibility 0

TES_Pixel_L1.Copy TP_L1_00175
TP_L1_00175.Position -0.775 -3.875 0
TP_L1_00175.Mother TES_L1
TP_L1_00175.Visibility 0

TES_Pixel_L1.Copy TP_L1_00176
TP_L1_00176.Position -0.775 -2.325 0
TP_L1_00176.Mother TES_L1
TP_L1_00176.Visibility 0

TES_Pixel_L1.Copy TP_L1_00177
TP_L1_00177.Position -0.775 -0.775 0
TP_L1_00177.Mother TES_L1
TP_L1_00177.Visibility 0

TES_Pixel_L1.Copy TP_L1_00178
TP_L1_00178.Position -0.775 0.775 0
TP_L1_00178.Mother TES_L1
TP_L1_00178.Visibility 0

TES_Pixel_L1.Copy TP_L1_00179
TP_L1_00179.Position -0.775 2.325 0
TP_L1_00179.Mother TES_L1
TP_L1_00179.Visibility 0

TES_Pixel_L1.Copy TP_L1_00180
TP_L1_00180.Position -0.775 3.875 0
TP_L1_00180.Mother TES_L1
TP_L1_00180.Visibility 0

TES_Pixel_L1.Copy TP_L1_00181
TP_L1_00181.Position -0.775 5.425 0
TP_L1_00181.Mother TES_L1
TP_L1_00181.Visibility 0

TES_Pixel_L1.Copy TP_L1_00182
TP_L1_00182.Position -0.775 6.975 0
TP_L1_00182.Mother TES_L1
TP_L1_00182.Visibility 0

TES_Pixel_L1.Copy TP_L1_00183
TP_L1_00183.Position -0.775 8.525 0
TP_L1_00183.Mother TES_L1
TP_L1_00183.Visibility 0

TES_Pixel_L1.Copy TP_L1_00184
TP_L1_00184.Position -0.775 10.075 0
TP_L1_00184.Mother TES_L1
TP_L1_00184.Visibility 0

TES_Pixel_L1.Copy TP_L1_00185
TP_L1_00185.Position -0.775 11.625 0
TP_L1_00185.Mother TES_L1
TP_L1_00185.Visibility 0

TES_Pixel_L1.Copy TP_L1_00186
TP_L1_00186.Position -0.775 13.175 0
TP_L1_00186.Mother TES_L1
TP_L1_00186.Visibility 0

TES_Pixel_L1.Copy TP_L1_00187
TP_L1_00187.Position -0.775 14.725 0
TP_L1_00187.Mother TES_L1
TP_L1_00187.Visibility 0

TES_Pixel_L1.Copy TP_L1_00188
TP_L1_00188.Position 0.775 -14.725 0
TP_L1_00188.Mother TES_L1
TP_L1_00188.Visibility 0

TES_Pixel_L1.Copy TP_L1_00189
TP_L1_00189.Position 0.775 -13.175 0
TP_L1_00189.Mother TES_L1
TP_L1_00189.Visibility 0

TES_Pixel_L1.Copy TP_L1_00190
TP_L1_00190.Position 0.775 -11.625 0
TP_L1_00190.Mother TES_L1
TP_L1_00190.Visibility 0

TES_Pixel_L1.Copy TP_L1_00191
TP_L1_00191.Position 0.775 -10.075 0
TP_L1_00191.Mother TES_L1
TP_L1_00191.Visibility 0

TES_Pixel_L1.Copy TP_L1_00192
TP_L1_00192.Position 0.775 -8.525 0
TP_L1_00192.Mother TES_L1
TP_L1_00192.Visibility 0

TES_Pixel_L1.Copy TP_L1_00193
TP_L1_00193.Position 0.775 -6.975 0
TP_L1_00193.Mother TES_L1
TP_L1_00193.Visibility 0

TES_Pixel_L1.Copy TP_L1_00194
TP_L1_00194.Position 0.775 -5.425 0
TP_L1_00194.Mother TES_L1
TP_L1_00194.Visibility 0

TES_Pixel_L1.Copy TP_L1_00195
TP_L1_00195.Position 0.775 -3.875 0
TP_L1_00195.Mother TES_L1
TP_L1_00195.Visibility 0

TES_Pixel_L1.Copy TP_L1_00196
TP_L1_00196.Position 0.775 -2.325 0
TP_L1_00196.Mother TES_L1
TP_L1_00196.Visibility 0

TES_Pixel_L1.Copy TP_L1_00197
TP_L1_00197.Position 0.775 -0.775 0
TP_L1_00197.Mother TES_L1
TP_L1_00197.Visibility 0

TES_Pixel_L1.Copy TP_L1_00198
TP_L1_00198.Position 0.775 0.775 0
TP_L1_00198.Mother TES_L1
TP_L1_00198.Visibility 0

TES_Pixel_L1.Copy TP_L1_00199
TP_L1_00199.Position 0.775 2.325 0
TP_L1_00199.Mother TES_L1
TP_L1_00199.Visibility 0

TES_Pixel_L1.Copy TP_L1_00200
TP_L1_00200.Position 0.775 3.875 0
TP_L1_00200.Mother TES_L1
TP_L1_00200.Visibility 0

TES_Pixel_L1.Copy TP_L1_00201
TP_L1_00201.Position 0.775 5.425 0
TP_L1_00201.Mother TES_L1
TP_L1_00201.Visibility 0

TES_Pixel_L1.Copy TP_L1_00202
TP_L1_00202.Position 0.775 6.975 0
TP_L1_00202.Mother TES_L1
TP_L1_00202.Visibility 0

TES_Pixel_L1.Copy TP_L1_00203
TP_L1_00203.Position 0.775 8.525 0
TP_L1_00203.Mother TES_L1
TP_L1_00203.Visibility 0

TES_Pixel_L1.Copy TP_L1_00204
TP_L1_00204.Position 0.775 10.075 0
TP_L1_00204.Mother TES_L1
TP_L1_00204.Visibility 0

TES_Pixel_L1.Copy TP_L1_00205
TP_L1_00205.Position 0.775 11.625 0
TP_L1_00205.Mother TES_L1
TP_L1_00205.Visibility 0

TES_Pixel_L1.Copy TP_L1_00206
TP_L1_00206.Position 0.775 13.175 0
TP_L1_00206.Mother TES_L1
TP_L1_00206.Visibility 0

TES_Pixel_L1.Copy TP_L1_00207
TP_L1_00207.Position 0.775 14.725 0
TP_L1_00207.Mother TES_L1
TP_L1_00207.Visibility 0

TES_Pixel_L1.Copy TP_L1_00208
TP_L1_00208.Position 2.325 -14.725 0
TP_L1_00208.Mother TES_L1
TP_L1_00208.Visibility 0

TES_Pixel_L1.Copy TP_L1_00209
TP_L1_00209.Position 2.325 -13.175 0
TP_L1_00209.Mother TES_L1
TP_L1_00209.Visibility 0

TES_Pixel_L1.Copy TP_L1_00210
TP_L1_00210.Position 2.325 -11.625 0
TP_L1_00210.Mother TES_L1
TP_L1_00210.Visibility 0

TES_Pixel_L1.Copy TP_L1_00211
TP_L1_00211.Position 2.325 -10.075 0
TP_L1_00211.Mother TES_L1
TP_L1_00211.Visibility 0

TES_Pixel_L1.Copy TP_L1_00212
TP_L1_00212.Position 2.325 -8.525 0
TP_L1_00212.Mother TES_L1
TP_L1_00212.Visibility 0

TES_Pixel_L1.Copy TP_L1_00213
TP_L1_00213.Position 2.325 -6.975 0
TP_L1_00213.Mother TES_L1
TP_L1_00213.Visibility 0

TES_Pixel_L1.Copy TP_L1_00214
TP_L1_00214.Position 2.325 -5.425 0
TP_L1_00214.Mother TES_L1
TP_L1_00214.Visibility 0

TES_Pixel_L1.Copy TP_L1_00215
TP_L1_00215.Position 2.325 -3.875 0
TP_L1_00215.Mother TES_L1
TP_L1_00215.Visibility 0

TES_Pixel_L1.Copy TP_L1_00216
TP_L1_00216.Position 2.325 -2.325 0
TP_L1_00216.Mother TES_L1
TP_L1_00216.Visibility 0

TES_Pixel_L1.Copy TP_L1_00217
TP_L1_00217.Position 2.325 -0.775 0
TP_L1_00217.Mother TES_L1
TP_L1_00217.Visibility 0

TES_Pixel_L1.Copy TP_L1_00218
TP_L1_00218.Position 2.325 0.775 0
TP_L1_00218.Mother TES_L1
TP_L1_00218.Visibility 0

TES_Pixel_L1.Copy TP_L1_00219
TP_L1_00219.Position 2.325 2.325 0
TP_L1_00219.Mother TES_L1
TP_L1_00219.Visibility 0

TES_Pixel_L1.Copy TP_L1_00220
TP_L1_00220.Position 2.325 3.875 0
TP_L1_00220.Mother TES_L1
TP_L1_00220.Visibility 0

TES_Pixel_L1.Copy TP_L1_00221
TP_L1_00221.Position 2.325 5.425 0
TP_L1_00221.Mother TES_L1
TP_L1_00221.Visibility 0

TES_Pixel_L1.Copy TP_L1_00222
TP_L1_00222.Position 2.325 6.975 0
TP_L1_00222.Mother TES_L1
TP_L1_00222.Visibility 0

TES_Pixel_L1.Copy TP_L1_00223
TP_L1_00223.Position 2.325 8.525 0
TP_L1_00223.Mother TES_L1
TP_L1_00223.Visibility 0

TES_Pixel_L1.Copy TP_L1_00224
TP_L1_00224.Position 2.325 10.075 0
TP_L1_00224.Mother TES_L1
TP_L1_00224.Visibility 0

TES_Pixel_L1.Copy TP_L1_00225
TP_L1_00225.Position 2.325 11.625 0
TP_L1_00225.Mother TES_L1
TP_L1_00225.Visibility 0

TES_Pixel_L1.Copy TP_L1_00226
TP_L1_00226.Position 2.325 13.175 0
TP_L1_00226.Mother TES_L1
TP_L1_00226.Visibility 0

TES_Pixel_L1.Copy TP_L1_00227
TP_L1_00227.Position 2.325 14.725 0
TP_L1_00227.Mother TES_L1
TP_L1_00227.Visibility 0

TES_Pixel_L1.Copy TP_L1_00228
TP_L1_00228.Position 3.875 -14.725 0
TP_L1_00228.Mother TES_L1
TP_L1_00228.Visibility 0

TES_Pixel_L1.Copy TP_L1_00229
TP_L1_00229.Position 3.875 -13.175 0
TP_L1_00229.Mother TES_L1
TP_L1_00229.Visibility 0

TES_Pixel_L1.Copy TP_L1_00230
TP_L1_00230.Position 3.875 -11.625 0
TP_L1_00230.Mother TES_L1
TP_L1_00230.Visibility 0

TES_Pixel_L1.Copy TP_L1_00231
TP_L1_00231.Position 3.875 -10.075 0
TP_L1_00231.Mother TES_L1
TP_L1_00231.Visibility 0

TES_Pixel_L1.Copy TP_L1_00232
TP_L1_00232.Position 3.875 -8.525 0
TP_L1_00232.Mother TES_L1
TP_L1_00232.Visibility 0

TES_Pixel_L1.Copy TP_L1_00233
TP_L1_00233.Position 3.875 -6.975 0
TP_L1_00233.Mother TES_L1
TP_L1_00233.Visibility 0

TES_Pixel_L1.Copy TP_L1_00234
TP_L1_00234.Position 3.875 -5.425 0
TP_L1_00234.Mother TES_L1
TP_L1_00234.Visibility 0

TES_Pixel_L1.Copy TP_L1_00235
TP_L1_00235.Position 3.875 -3.875 0
TP_L1_00235.Mother TES_L1
TP_L1_00235.Visibility 0

TES_Pixel_L1.Copy TP_L1_00236
TP_L1_00236.Position 3.875 -2.325 0
TP_L1_00236.Mother TES_L1
TP_L1_00236.Visibility 0

TES_Pixel_L1.Copy TP_L1_00237
TP_L1_00237.Position 3.875 -0.775 0
TP_L1_00237.Mother TES_L1
TP_L1_00237.Visibility 0

TES_Pixel_L1.Copy TP_L1_00238
TP_L1_00238.Position 3.875 0.775 0
TP_L1_00238.Mother TES_L1
TP_L1_00238.Visibility 0

TES_Pixel_L1.Copy TP_L1_00239
TP_L1_00239.Position 3.875 2.325 0
TP_L1_00239.Mother TES_L1
TP_L1_00239.Visibility 0

TES_Pixel_L1.Copy TP_L1_00240
TP_L1_00240.Position 3.875 3.875 0
TP_L1_00240.Mother TES_L1
TP_L1_00240.Visibility 0

TES_Pixel_L1.Copy TP_L1_00241
TP_L1_00241.Position 3.875 5.425 0
TP_L1_00241.Mother TES_L1
TP_L1_00241.Visibility 0

TES_Pixel_L1.Copy TP_L1_00242
TP_L1_00242.Position 3.875 6.975 0
TP_L1_00242.Mother TES_L1
TP_L1_00242.Visibility 0

TES_Pixel_L1.Copy TP_L1_00243
TP_L1_00243.Position 3.875 8.525 0
TP_L1_00243.Mother TES_L1
TP_L1_00243.Visibility 0

TES_Pixel_L1.Copy TP_L1_00244
TP_L1_00244.Position 3.875 10.075 0
TP_L1_00244.Mother TES_L1
TP_L1_00244.Visibility 0

TES_Pixel_L1.Copy TP_L1_00245
TP_L1_00245.Position 3.875 11.625 0
TP_L1_00245.Mother TES_L1
TP_L1_00245.Visibility 0

TES_Pixel_L1.Copy TP_L1_00246
TP_L1_00246.Position 3.875 13.175 0
TP_L1_00246.Mother TES_L1
TP_L1_00246.Visibility 0

TES_Pixel_L1.Copy TP_L1_00247
TP_L1_00247.Position 3.875 14.725 0
TP_L1_00247.Mother TES_L1
TP_L1_00247.Visibility 0

TES_Pixel_L1.Copy TP_L1_00248
TP_L1_00248.Position 5.425 -14.725 0
TP_L1_00248.Mother TES_L1
TP_L1_00248.Visibility 0

TES_Pixel_L1.Copy TP_L1_00249
TP_L1_00249.Position 5.425 -13.175 0
TP_L1_00249.Mother TES_L1
TP_L1_00249.Visibility 0

TES_Pixel_L1.Copy TP_L1_00250
TP_L1_00250.Position 5.425 -11.625 0
TP_L1_00250.Mother TES_L1
TP_L1_00250.Visibility 0

TES_Pixel_L1.Copy TP_L1_00251
TP_L1_00251.Position 5.425 -10.075 0
TP_L1_00251.Mother TES_L1
TP_L1_00251.Visibility 0

TES_Pixel_L1.Copy TP_L1_00252
TP_L1_00252.Position 5.425 -8.525 0
TP_L1_00252.Mother TES_L1
TP_L1_00252.Visibility 0

TES_Pixel_L1.Copy TP_L1_00253
TP_L1_00253.Position 5.425 -6.975 0
TP_L1_00253.Mother TES_L1
TP_L1_00253.Visibility 0

TES_Pixel_L1.Copy TP_L1_00254
TP_L1_00254.Position 5.425 -5.425 0
TP_L1_00254.Mother TES_L1
TP_L1_00254.Visibility 0

TES_Pixel_L1.Copy TP_L1_00255
TP_L1_00255.Position 5.425 -3.875 0
TP_L1_00255.Mother TES_L1
TP_L1_00255.Visibility 0

TES_Pixel_L1.Copy TP_L1_00256
TP_L1_00256.Position 5.425 -2.325 0
TP_L1_00256.Mother TES_L1
TP_L1_00256.Visibility 0

TES_Pixel_L1.Copy TP_L1_00257
TP_L1_00257.Position 5.425 -0.775 0
TP_L1_00257.Mother TES_L1
TP_L1_00257.Visibility 0

TES_Pixel_L1.Copy TP_L1_00258
TP_L1_00258.Position 5.425 0.775 0
TP_L1_00258.Mother TES_L1
TP_L1_00258.Visibility 0

TES_Pixel_L1.Copy TP_L1_00259
TP_L1_00259.Position 5.425 2.325 0
TP_L1_00259.Mother TES_L1
TP_L1_00259.Visibility 0

TES_Pixel_L1.Copy TP_L1_00260
TP_L1_00260.Position 5.425 3.875 0
TP_L1_00260.Mother TES_L1
TP_L1_00260.Visibility 0

TES_Pixel_L1.Copy TP_L1_00261
TP_L1_00261.Position 5.425 5.425 0
TP_L1_00261.Mother TES_L1
TP_L1_00261.Visibility 0

TES_Pixel_L1.Copy TP_L1_00262
TP_L1_00262.Position 5.425 6.975 0
TP_L1_00262.Mother TES_L1
TP_L1_00262.Visibility 0

TES_Pixel_L1.Copy TP_L1_00263
TP_L1_00263.Position 5.425 8.525 0
TP_L1_00263.Mother TES_L1
TP_L1_00263.Visibility 0

TES_Pixel_L1.Copy TP_L1_00264
TP_L1_00264.Position 5.425 10.075 0
TP_L1_00264.Mother TES_L1
TP_L1_00264.Visibility 0

TES_Pixel_L1.Copy TP_L1_00265
TP_L1_00265.Position 5.425 11.625 0
TP_L1_00265.Mother TES_L1
TP_L1_00265.Visibility 0

TES_Pixel_L1.Copy TP_L1_00266
TP_L1_00266.Position 5.425 13.175 0
TP_L1_00266.Mother TES_L1
TP_L1_00266.Visibility 0

TES_Pixel_L1.Copy TP_L1_00267
TP_L1_00267.Position 5.425 14.725 0
TP_L1_00267.Mother TES_L1
TP_L1_00267.Visibility 0

TES_Pixel_L1.Copy TP_L1_00268
TP_L1_00268.Position 6.975 -14.725 0
TP_L1_00268.Mother TES_L1
TP_L1_00268.Visibility 0

TES_Pixel_L1.Copy TP_L1_00269
TP_L1_00269.Position 6.975 -13.175 0
TP_L1_00269.Mother TES_L1
TP_L1_00269.Visibility 0

TES_Pixel_L1.Copy TP_L1_00270
TP_L1_00270.Position 6.975 -11.625 0
TP_L1_00270.Mother TES_L1
TP_L1_00270.Visibility 0

TES_Pixel_L1.Copy TP_L1_00271
TP_L1_00271.Position 6.975 -10.075 0
TP_L1_00271.Mother TES_L1
TP_L1_00271.Visibility 0

TES_Pixel_L1.Copy TP_L1_00272
TP_L1_00272.Position 6.975 -8.525 0
TP_L1_00272.Mother TES_L1
TP_L1_00272.Visibility 0

TES_Pixel_L1.Copy TP_L1_00273
TP_L1_00273.Position 6.975 -6.975 0
TP_L1_00273.Mother TES_L1
TP_L1_00273.Visibility 0

TES_Pixel_L1.Copy TP_L1_00274
TP_L1_00274.Position 6.975 -5.425 0
TP_L1_00274.Mother TES_L1
TP_L1_00274.Visibility 0

TES_Pixel_L1.Copy TP_L1_00275
TP_L1_00275.Position 6.975 -3.875 0
TP_L1_00275.Mother TES_L1
TP_L1_00275.Visibility 0

TES_Pixel_L1.Copy TP_L1_00276
TP_L1_00276.Position 6.975 -2.325 0
TP_L1_00276.Mother TES_L1
TP_L1_00276.Visibility 0

TES_Pixel_L1.Copy TP_L1_00277
TP_L1_00277.Position 6.975 -0.775 0
TP_L1_00277.Mother TES_L1
TP_L1_00277.Visibility 0

TES_Pixel_L1.Copy TP_L1_00278
TP_L1_00278.Position 6.975 0.775 0
TP_L1_00278.Mother TES_L1
TP_L1_00278.Visibility 0

TES_Pixel_L1.Copy TP_L1_00279
TP_L1_00279.Position 6.975 2.325 0
TP_L1_00279.Mother TES_L1
TP_L1_00279.Visibility 0

TES_Pixel_L1.Copy TP_L1_00280
TP_L1_00280.Position 6.975 3.875 0
TP_L1_00280.Mother TES_L1
TP_L1_00280.Visibility 0

TES_Pixel_L1.Copy TP_L1_00281
TP_L1_00281.Position 6.975 5.425 0
TP_L1_00281.Mother TES_L1
TP_L1_00281.Visibility 0

TES_Pixel_L1.Copy TP_L1_00282
TP_L1_00282.Position 6.975 6.975 0
TP_L1_00282.Mother TES_L1
TP_L1_00282.Visibility 0

TES_Pixel_L1.Copy TP_L1_00283
TP_L1_00283.Position 6.975 8.525 0
TP_L1_00283.Mother TES_L1
TP_L1_00283.Visibility 0

TES_Pixel_L1.Copy TP_L1_00284
TP_L1_00284.Position 6.975 10.075 0
TP_L1_00284.Mother TES_L1
TP_L1_00284.Visibility 0

TES_Pixel_L1.Copy TP_L1_00285
TP_L1_00285.Position 6.975 11.625 0
TP_L1_00285.Mother TES_L1
TP_L1_00285.Visibility 0

TES_Pixel_L1.Copy TP_L1_00286
TP_L1_00286.Position 6.975 13.175 0
TP_L1_00286.Mother TES_L1
TP_L1_00286.Visibility 0

TES_Pixel_L1.Copy TP_L1_00287
TP_L1_00287.Position 6.975 14.725 0
TP_L1_00287.Mother TES_L1
TP_L1_00287.Visibility 0

TES_Pixel_L1.Copy TP_L1_00288
TP_L1_00288.Position 8.525 -14.725 0
TP_L1_00288.Mother TES_L1
TP_L1_00288.Visibility 0

TES_Pixel_L1.Copy TP_L1_00289
TP_L1_00289.Position 8.525 -13.175 0
TP_L1_00289.Mother TES_L1
TP_L1_00289.Visibility 0

TES_Pixel_L1.Copy TP_L1_00290
TP_L1_00290.Position 8.525 -11.625 0
TP_L1_00290.Mother TES_L1
TP_L1_00290.Visibility 0

TES_Pixel_L1.Copy TP_L1_00291
TP_L1_00291.Position 8.525 -10.075 0
TP_L1_00291.Mother TES_L1
TP_L1_00291.Visibility 0

TES_Pixel_L1.Copy TP_L1_00292
TP_L1_00292.Position 8.525 -8.525 0
TP_L1_00292.Mother TES_L1
TP_L1_00292.Visibility 0

TES_Pixel_L1.Copy TP_L1_00293
TP_L1_00293.Position 8.525 -6.975 0
TP_L1_00293.Mother TES_L1
TP_L1_00293.Visibility 0

TES_Pixel_L1.Copy TP_L1_00294
TP_L1_00294.Position 8.525 -5.425 0
TP_L1_00294.Mother TES_L1
TP_L1_00294.Visibility 0

TES_Pixel_L1.Copy TP_L1_00295
TP_L1_00295.Position 8.525 -3.875 0
TP_L1_00295.Mother TES_L1
TP_L1_00295.Visibility 0

TES_Pixel_L1.Copy TP_L1_00296
TP_L1_00296.Position 8.525 -2.325 0
TP_L1_00296.Mother TES_L1
TP_L1_00296.Visibility 0

TES_Pixel_L1.Copy TP_L1_00297
TP_L1_00297.Position 8.525 -0.775 0
TP_L1_00297.Mother TES_L1
TP_L1_00297.Visibility 0

TES_Pixel_L1.Copy TP_L1_00298
TP_L1_00298.Position 8.525 0.775 0
TP_L1_00298.Mother TES_L1
TP_L1_00298.Visibility 0

TES_Pixel_L1.Copy TP_L1_00299
TP_L1_00299.Position 8.525 2.325 0
TP_L1_00299.Mother TES_L1
TP_L1_00299.Visibility 0

TES_Pixel_L1.Copy TP_L1_00300
TP_L1_00300.Position 8.525 3.875 0
TP_L1_00300.Mother TES_L1
TP_L1_00300.Visibility 0

TES_Pixel_L1.Copy TP_L1_00301
TP_L1_00301.Position 8.525 5.425 0
TP_L1_00301.Mother TES_L1
TP_L1_00301.Visibility 0

TES_Pixel_L1.Copy TP_L1_00302
TP_L1_00302.Position 8.525 6.975 0
TP_L1_00302.Mother TES_L1
TP_L1_00302.Visibility 0

TES_Pixel_L1.Copy TP_L1_00303
TP_L1_00303.Position 8.525 8.525 0
TP_L1_00303.Mother TES_L1
TP_L1_00303.Visibility 0

TES_Pixel_L1.Copy TP_L1_00304
TP_L1_00304.Position 8.525 10.075 0
TP_L1_00304.Mother TES_L1
TP_L1_00304.Visibility 0

TES_Pixel_L1.Copy TP_L1_00305
TP_L1_00305.Position 8.525 11.625 0
TP_L1_00305.Mother TES_L1
TP_L1_00305.Visibility 0

TES_Pixel_L1.Copy TP_L1_00306
TP_L1_00306.Position 8.525 13.175 0
TP_L1_00306.Mother TES_L1
TP_L1_00306.Visibility 0

TES_Pixel_L1.Copy TP_L1_00307
TP_L1_00307.Position 8.525 14.725 0
TP_L1_00307.Mother TES_L1
TP_L1_00307.Visibility 0

TES_Pixel_L1.Copy TP_L1_00308
TP_L1_00308.Position 10.075 -14.725 0
TP_L1_00308.Mother TES_L1
TP_L1_00308.Visibility 0

TES_Pixel_L1.Copy TP_L1_00309
TP_L1_00309.Position 10.075 -13.175 0
TP_L1_00309.Mother TES_L1
TP_L1_00309.Visibility 0

TES_Pixel_L1.Copy TP_L1_00310
TP_L1_00310.Position 10.075 -11.625 0
TP_L1_00310.Mother TES_L1
TP_L1_00310.Visibility 0

TES_Pixel_L1.Copy TP_L1_00311
TP_L1_00311.Position 10.075 -10.075 0
TP_L1_00311.Mother TES_L1
TP_L1_00311.Visibility 0

TES_Pixel_L1.Copy TP_L1_00312
TP_L1_00312.Position 10.075 -8.525 0
TP_L1_00312.Mother TES_L1
TP_L1_00312.Visibility 0

TES_Pixel_L1.Copy TP_L1_00313
TP_L1_00313.Position 10.075 -6.975 0
TP_L1_00313.Mother TES_L1
TP_L1_00313.Visibility 0

TES_Pixel_L1.Copy TP_L1_00314
TP_L1_00314.Position 10.075 -5.425 0
TP_L1_00314.Mother TES_L1
TP_L1_00314.Visibility 0

TES_Pixel_L1.Copy TP_L1_00315
TP_L1_00315.Position 10.075 -3.875 0
TP_L1_00315.Mother TES_L1
TP_L1_00315.Visibility 0

TES_Pixel_L1.Copy TP_L1_00316
TP_L1_00316.Position 10.075 -2.325 0
TP_L1_00316.Mother TES_L1
TP_L1_00316.Visibility 0

TES_Pixel_L1.Copy TP_L1_00317
TP_L1_00317.Position 10.075 -0.775 0
TP_L1_00317.Mother TES_L1
TP_L1_00317.Visibility 0

TES_Pixel_L1.Copy TP_L1_00318
TP_L1_00318.Position 10.075 0.775 0
TP_L1_00318.Mother TES_L1
TP_L1_00318.Visibility 0

TES_Pixel_L1.Copy TP_L1_00319
TP_L1_00319.Position 10.075 2.325 0
TP_L1_00319.Mother TES_L1
TP_L1_00319.Visibility 0

TES_Pixel_L1.Copy TP_L1_00320
TP_L1_00320.Position 10.075 3.875 0
TP_L1_00320.Mother TES_L1
TP_L1_00320.Visibility 0

TES_Pixel_L1.Copy TP_L1_00321
TP_L1_00321.Position 10.075 5.425 0
TP_L1_00321.Mother TES_L1
TP_L1_00321.Visibility 0

TES_Pixel_L1.Copy TP_L1_00322
TP_L1_00322.Position 10.075 6.975 0
TP_L1_00322.Mother TES_L1
TP_L1_00322.Visibility 0

TES_Pixel_L1.Copy TP_L1_00323
TP_L1_00323.Position 10.075 8.525 0
TP_L1_00323.Mother TES_L1
TP_L1_00323.Visibility 0

TES_Pixel_L1.Copy TP_L1_00324
TP_L1_00324.Position 10.075 10.075 0
TP_L1_00324.Mother TES_L1
TP_L1_00324.Visibility 0

TES_Pixel_L1.Copy TP_L1_00325
TP_L1_00325.Position 10.075 11.625 0
TP_L1_00325.Mother TES_L1
TP_L1_00325.Visibility 0

TES_Pixel_L1.Copy TP_L1_00326
TP_L1_00326.Position 10.075 13.175 0
TP_L1_00326.Mother TES_L1
TP_L1_00326.Visibility 0

TES_Pixel_L1.Copy TP_L1_00327
TP_L1_00327.Position 10.075 14.725 0
TP_L1_00327.Mother TES_L1
TP_L1_00327.Visibility 0

TES_Pixel_L1.Copy TP_L1_00328
TP_L1_00328.Position 11.625 -13.175 0
TP_L1_00328.Mother TES_L1
TP_L1_00328.Visibility 0

TES_Pixel_L1.Copy TP_L1_00329
TP_L1_00329.Position 11.625 -11.625 0
TP_L1_00329.Mother TES_L1
TP_L1_00329.Visibility 0

TES_Pixel_L1.Copy TP_L1_00330
TP_L1_00330.Position 11.625 -10.075 0
TP_L1_00330.Mother TES_L1
TP_L1_00330.Visibility 0

TES_Pixel_L1.Copy TP_L1_00331
TP_L1_00331.Position 11.625 -8.525 0
TP_L1_00331.Mother TES_L1
TP_L1_00331.Visibility 0

TES_Pixel_L1.Copy TP_L1_00332
TP_L1_00332.Position 11.625 -6.975 0
TP_L1_00332.Mother TES_L1
TP_L1_00332.Visibility 0

TES_Pixel_L1.Copy TP_L1_00333
TP_L1_00333.Position 11.625 -5.425 0
TP_L1_00333.Mother TES_L1
TP_L1_00333.Visibility 0

TES_Pixel_L1.Copy TP_L1_00334
TP_L1_00334.Position 11.625 -3.875 0
TP_L1_00334.Mother TES_L1
TP_L1_00334.Visibility 0

TES_Pixel_L1.Copy TP_L1_00335
TP_L1_00335.Position 11.625 -2.325 0
TP_L1_00335.Mother TES_L1
TP_L1_00335.Visibility 0

TES_Pixel_L1.Copy TP_L1_00336
TP_L1_00336.Position 11.625 -0.775 0
TP_L1_00336.Mother TES_L1
TP_L1_00336.Visibility 0

TES_Pixel_L1.Copy TP_L1_00337
TP_L1_00337.Position 11.625 0.775 0
TP_L1_00337.Mother TES_L1
TP_L1_00337.Visibility 0

TES_Pixel_L1.Copy TP_L1_00338
TP_L1_00338.Position 11.625 2.325 0
TP_L1_00338.Mother TES_L1
TP_L1_00338.Visibility 0

TES_Pixel_L1.Copy TP_L1_00339
TP_L1_00339.Position 11.625 3.875 0
TP_L1_00339.Mother TES_L1
TP_L1_00339.Visibility 0

TES_Pixel_L1.Copy TP_L1_00340
TP_L1_00340.Position 11.625 5.425 0
TP_L1_00340.Mother TES_L1
TP_L1_00340.Visibility 0

TES_Pixel_L1.Copy TP_L1_00341
TP_L1_00341.Position 11.625 6.975 0
TP_L1_00341.Mother TES_L1
TP_L1_00341.Visibility 0

TES_Pixel_L1.Copy TP_L1_00342
TP_L1_00342.Position 11.625 8.525 0
TP_L1_00342.Mother TES_L1
TP_L1_00342.Visibility 0

TES_Pixel_L1.Copy TP_L1_00343
TP_L1_00343.Position 11.625 10.075 0
TP_L1_00343.Mother TES_L1
TP_L1_00343.Visibility 0

TES_Pixel_L1.Copy TP_L1_00344
TP_L1_00344.Position 11.625 11.625 0
TP_L1_00344.Mother TES_L1
TP_L1_00344.Visibility 0

TES_Pixel_L1.Copy TP_L1_00345
TP_L1_00345.Position 11.625 13.175 0
TP_L1_00345.Mother TES_L1
TP_L1_00345.Visibility 0

TES_Pixel_L1.Copy TP_L1_00346
TP_L1_00346.Position 13.175 -11.625 0
TP_L1_00346.Mother TES_L1
TP_L1_00346.Visibility 0

TES_Pixel_L1.Copy TP_L1_00347
TP_L1_00347.Position 13.175 -10.075 0
TP_L1_00347.Mother TES_L1
TP_L1_00347.Visibility 0

TES_Pixel_L1.Copy TP_L1_00348
TP_L1_00348.Position 13.175 -8.525 0
TP_L1_00348.Mother TES_L1
TP_L1_00348.Visibility 0

TES_Pixel_L1.Copy TP_L1_00349
TP_L1_00349.Position 13.175 -6.975 0
TP_L1_00349.Mother TES_L1
TP_L1_00349.Visibility 0

TES_Pixel_L1.Copy TP_L1_00350
TP_L1_00350.Position 13.175 -5.425 0
TP_L1_00350.Mother TES_L1
TP_L1_00350.Visibility 0

TES_Pixel_L1.Copy TP_L1_00351
TP_L1_00351.Position 13.175 -3.875 0
TP_L1_00351.Mother TES_L1
TP_L1_00351.Visibility 0

TES_Pixel_L1.Copy TP_L1_00352
TP_L1_00352.Position 13.175 -2.325 0
TP_L1_00352.Mother TES_L1
TP_L1_00352.Visibility 0

TES_Pixel_L1.Copy TP_L1_00353
TP_L1_00353.Position 13.175 -0.775 0
TP_L1_00353.Mother TES_L1
TP_L1_00353.Visibility 0

TES_Pixel_L1.Copy TP_L1_00354
TP_L1_00354.Position 13.175 0.775 0
TP_L1_00354.Mother TES_L1
TP_L1_00354.Visibility 0

TES_Pixel_L1.Copy TP_L1_00355
TP_L1_00355.Position 13.175 2.325 0
TP_L1_00355.Mother TES_L1
TP_L1_00355.Visibility 0

TES_Pixel_L1.Copy TP_L1_00356
TP_L1_00356.Position 13.175 3.875 0
TP_L1_00356.Mother TES_L1
TP_L1_00356.Visibility 0

TES_Pixel_L1.Copy TP_L1_00357
TP_L1_00357.Position 13.175 5.425 0
TP_L1_00357.Mother TES_L1
TP_L1_00357.Visibility 0

TES_Pixel_L1.Copy TP_L1_00358
TP_L1_00358.Position 13.175 6.975 0
TP_L1_00358.Mother TES_L1
TP_L1_00358.Visibility 0

TES_Pixel_L1.Copy TP_L1_00359
TP_L1_00359.Position 13.175 8.525 0
TP_L1_00359.Mother TES_L1
TP_L1_00359.Visibility 0

TES_Pixel_L1.Copy TP_L1_00360
TP_L1_00360.Position 13.175 10.075 0
TP_L1_00360.Mother TES_L1
TP_L1_00360.Visibility 0

TES_Pixel_L1.Copy TP_L1_00361
TP_L1_00361.Position 13.175 11.625 0
TP_L1_00361.Mother TES_L1
TP_L1_00361.Visibility 0

TES_Pixel_L1.Copy TP_L1_00362
TP_L1_00362.Position 14.725 -10.075 0
TP_L1_00362.Mother TES_L1
TP_L1_00362.Visibility 0

TES_Pixel_L1.Copy TP_L1_00363
TP_L1_00363.Position 14.725 -8.525 0
TP_L1_00363.Mother TES_L1
TP_L1_00363.Visibility 0

TES_Pixel_L1.Copy TP_L1_00364
TP_L1_00364.Position 14.725 -6.975 0
TP_L1_00364.Mother TES_L1
TP_L1_00364.Visibility 0

TES_Pixel_L1.Copy TP_L1_00365
TP_L1_00365.Position 14.725 -5.425 0
TP_L1_00365.Mother TES_L1
TP_L1_00365.Visibility 0

TES_Pixel_L1.Copy TP_L1_00366
TP_L1_00366.Position 14.725 -3.875 0
TP_L1_00366.Mother TES_L1
TP_L1_00366.Visibility 0

TES_Pixel_L1.Copy TP_L1_00367
TP_L1_00367.Position 14.725 -2.325 0
TP_L1_00367.Mother TES_L1
TP_L1_00367.Visibility 0

TES_Pixel_L1.Copy TP_L1_00368
TP_L1_00368.Position 14.725 -0.775 0
TP_L1_00368.Mother TES_L1
TP_L1_00368.Visibility 0

TES_Pixel_L1.Copy TP_L1_00369
TP_L1_00369.Position 14.725 0.775 0
TP_L1_00369.Mother TES_L1
TP_L1_00369.Visibility 0

TES_Pixel_L1.Copy TP_L1_00370
TP_L1_00370.Position 14.725 2.325 0
TP_L1_00370.Mother TES_L1
TP_L1_00370.Visibility 0

TES_Pixel_L1.Copy TP_L1_00371
TP_L1_00371.Position 14.725 3.875 0
TP_L1_00371.Mother TES_L1
TP_L1_00371.Visibility 0

TES_Pixel_L1.Copy TP_L1_00372
TP_L1_00372.Position 14.725 5.425 0
TP_L1_00372.Mother TES_L1
TP_L1_00372.Visibility 0

TES_Pixel_L1.Copy TP_L1_00373
TP_L1_00373.Position 14.725 6.975 0
TP_L1_00373.Mother TES_L1
TP_L1_00373.Visibility 0

TES_Pixel_L1.Copy TP_L1_00374
TP_L1_00374.Position 14.725 8.525 0
TP_L1_00374.Mother TES_L1
TP_L1_00374.Visibility 0

TES_Pixel_L1.Copy TP_L1_00375
TP_L1_00375.Position 14.725 10.075 0
TP_L1_00375.Mother TES_L1
TP_L1_00375.Visibility 0

Substrate_L2.Position 0 0 34
Substrate_L2.Mother WorldVolume

TES_L2.Position 0 0 35.65
TES_L2.Mother WorldVolume
TES_L2.Visibility 0

TES_Pixel_L2.Copy TP_L2_00000
TP_L2_00000.Position -14.725 -10.075 0
TP_L2_00000.Mother TES_L2
TP_L2_00000.Visibility 0

TES_Pixel_L2.Copy TP_L2_00001
TP_L2_00001.Position -14.725 -8.525 0
TP_L2_00001.Mother TES_L2
TP_L2_00001.Visibility 0

TES_Pixel_L2.Copy TP_L2_00002
TP_L2_00002.Position -14.725 -6.975 0
TP_L2_00002.Mother TES_L2
TP_L2_00002.Visibility 0

TES_Pixel_L2.Copy TP_L2_00003
TP_L2_00003.Position -14.725 -5.425 0
TP_L2_00003.Mother TES_L2
TP_L2_00003.Visibility 0

TES_Pixel_L2.Copy TP_L2_00004
TP_L2_00004.Position -14.725 -3.875 0
TP_L2_00004.Mother TES_L2
TP_L2_00004.Visibility 0

TES_Pixel_L2.Copy TP_L2_00005
TP_L2_00005.Position -14.725 -2.325 0
TP_L2_00005.Mother TES_L2
TP_L2_00005.Visibility 0

TES_Pixel_L2.Copy TP_L2_00006
TP_L2_00006.Position -14.725 -0.775 0
TP_L2_00006.Mother TES_L2
TP_L2_00006.Visibility 0

TES_Pixel_L2.Copy TP_L2_00007
TP_L2_00007.Position -14.725 0.775 0
TP_L2_00007.Mother TES_L2
TP_L2_00007.Visibility 0

TES_Pixel_L2.Copy TP_L2_00008
TP_L2_00008.Position -14.725 2.325 0
TP_L2_00008.Mother TES_L2
TP_L2_00008.Visibility 0

TES_Pixel_L2.Copy TP_L2_00009
TP_L2_00009.Position -14.725 3.875 0
TP_L2_00009.Mother TES_L2
TP_L2_00009.Visibility 0

TES_Pixel_L2.Copy TP_L2_00010
TP_L2_00010.Position -14.725 5.425 0
TP_L2_00010.Mother TES_L2
TP_L2_00010.Visibility 0

TES_Pixel_L2.Copy TP_L2_00011
TP_L2_00011.Position -14.725 6.975 0
TP_L2_00011.Mother TES_L2
TP_L2_00011.Visibility 0

TES_Pixel_L2.Copy TP_L2_00012
TP_L2_00012.Position -14.725 8.525 0
TP_L2_00012.Mother TES_L2
TP_L2_00012.Visibility 0

TES_Pixel_L2.Copy TP_L2_00013
TP_L2_00013.Position -14.725 10.075 0
TP_L2_00013.Mother TES_L2
TP_L2_00013.Visibility 0

TES_Pixel_L2.Copy TP_L2_00014
TP_L2_00014.Position -13.175 -11.625 0
TP_L2_00014.Mother TES_L2
TP_L2_00014.Visibility 0

TES_Pixel_L2.Copy TP_L2_00015
TP_L2_00015.Position -13.175 -10.075 0
TP_L2_00015.Mother TES_L2
TP_L2_00015.Visibility 0

TES_Pixel_L2.Copy TP_L2_00016
TP_L2_00016.Position -13.175 -8.525 0
TP_L2_00016.Mother TES_L2
TP_L2_00016.Visibility 0

TES_Pixel_L2.Copy TP_L2_00017
TP_L2_00017.Position -13.175 -6.975 0
TP_L2_00017.Mother TES_L2
TP_L2_00017.Visibility 0

TES_Pixel_L2.Copy TP_L2_00018
TP_L2_00018.Position -13.175 -5.425 0
TP_L2_00018.Mother TES_L2
TP_L2_00018.Visibility 0

TES_Pixel_L2.Copy TP_L2_00019
TP_L2_00019.Position -13.175 -3.875 0
TP_L2_00019.Mother TES_L2
TP_L2_00019.Visibility 0

TES_Pixel_L2.Copy TP_L2_00020
TP_L2_00020.Position -13.175 -2.325 0
TP_L2_00020.Mother TES_L2
TP_L2_00020.Visibility 0

TES_Pixel_L2.Copy TP_L2_00021
TP_L2_00021.Position -13.175 -0.775 0
TP_L2_00021.Mother TES_L2
TP_L2_00021.Visibility 0

TES_Pixel_L2.Copy TP_L2_00022
TP_L2_00022.Position -13.175 0.775 0
TP_L2_00022.Mother TES_L2
TP_L2_00022.Visibility 0

TES_Pixel_L2.Copy TP_L2_00023
TP_L2_00023.Position -13.175 2.325 0
TP_L2_00023.Mother TES_L2
TP_L2_00023.Visibility 0

TES_Pixel_L2.Copy TP_L2_00024
TP_L2_00024.Position -13.175 3.875 0
TP_L2_00024.Mother TES_L2
TP_L2_00024.Visibility 0

TES_Pixel_L2.Copy TP_L2_00025
TP_L2_00025.Position -13.175 5.425 0
TP_L2_00025.Mother TES_L2
TP_L2_00025.Visibility 0

TES_Pixel_L2.Copy TP_L2_00026
TP_L2_00026.Position -13.175 6.975 0
TP_L2_00026.Mother TES_L2
TP_L2_00026.Visibility 0

TES_Pixel_L2.Copy TP_L2_00027
TP_L2_00027.Position -13.175 8.525 0
TP_L2_00027.Mother TES_L2
TP_L2_00027.Visibility 0

TES_Pixel_L2.Copy TP_L2_00028
TP_L2_00028.Position -13.175 10.075 0
TP_L2_00028.Mother TES_L2
TP_L2_00028.Visibility 0

TES_Pixel_L2.Copy TP_L2_00029
TP_L2_00029.Position -13.175 11.625 0
TP_L2_00029.Mother TES_L2
TP_L2_00029.Visibility 0

TES_Pixel_L2.Copy TP_L2_00030
TP_L2_00030.Position -11.625 -13.175 0
TP_L2_00030.Mother TES_L2
TP_L2_00030.Visibility 0

TES_Pixel_L2.Copy TP_L2_00031
TP_L2_00031.Position -11.625 -11.625 0
TP_L2_00031.Mother TES_L2
TP_L2_00031.Visibility 0

TES_Pixel_L2.Copy TP_L2_00032
TP_L2_00032.Position -11.625 -10.075 0
TP_L2_00032.Mother TES_L2
TP_L2_00032.Visibility 0

TES_Pixel_L2.Copy TP_L2_00033
TP_L2_00033.Position -11.625 -8.525 0
TP_L2_00033.Mother TES_L2
TP_L2_00033.Visibility 0

TES_Pixel_L2.Copy TP_L2_00034
TP_L2_00034.Position -11.625 -6.975 0
TP_L2_00034.Mother TES_L2
TP_L2_00034.Visibility 0

TES_Pixel_L2.Copy TP_L2_00035
TP_L2_00035.Position -11.625 -5.425 0
TP_L2_00035.Mother TES_L2
TP_L2_00035.Visibility 0

TES_Pixel_L2.Copy TP_L2_00036
TP_L2_00036.Position -11.625 -3.875 0
TP_L2_00036.Mother TES_L2
TP_L2_00036.Visibility 0

TES_Pixel_L2.Copy TP_L2_00037
TP_L2_00037.Position -11.625 -2.325 0
TP_L2_00037.Mother TES_L2
TP_L2_00037.Visibility 0

TES_Pixel_L2.Copy TP_L2_00038
TP_L2_00038.Position -11.625 -0.775 0
TP_L2_00038.Mother TES_L2
TP_L2_00038.Visibility 0

TES_Pixel_L2.Copy TP_L2_00039
TP_L2_00039.Position -11.625 0.775 0
TP_L2_00039.Mother TES_L2
TP_L2_00039.Visibility 0

TES_Pixel_L2.Copy TP_L2_00040
TP_L2_00040.Position -11.625 2.325 0
TP_L2_00040.Mother TES_L2
TP_L2_00040.Visibility 0

TES_Pixel_L2.Copy TP_L2_00041
TP_L2_00041.Position -11.625 3.875 0
TP_L2_00041.Mother TES_L2
TP_L2_00041.Visibility 0

TES_Pixel_L2.Copy TP_L2_00042
TP_L2_00042.Position -11.625 5.425 0
TP_L2_00042.Mother TES_L2
TP_L2_00042.Visibility 0

TES_Pixel_L2.Copy TP_L2_00043
TP_L2_00043.Position -11.625 6.975 0
TP_L2_00043.Mother TES_L2
TP_L2_00043.Visibility 0

TES_Pixel_L2.Copy TP_L2_00044
TP_L2_00044.Position -11.625 8.525 0
TP_L2_00044.Mother TES_L2
TP_L2_00044.Visibility 0

TES_Pixel_L2.Copy TP_L2_00045
TP_L2_00045.Position -11.625 10.075 0
TP_L2_00045.Mother TES_L2
TP_L2_00045.Visibility 0

TES_Pixel_L2.Copy TP_L2_00046
TP_L2_00046.Position -11.625 11.625 0
TP_L2_00046.Mother TES_L2
TP_L2_00046.Visibility 0

TES_Pixel_L2.Copy TP_L2_00047
TP_L2_00047.Position -11.625 13.175 0
TP_L2_00047.Mother TES_L2
TP_L2_00047.Visibility 0

TES_Pixel_L2.Copy TP_L2_00048
TP_L2_00048.Position -10.075 -14.725 0
TP_L2_00048.Mother TES_L2
TP_L2_00048.Visibility 0

TES_Pixel_L2.Copy TP_L2_00049
TP_L2_00049.Position -10.075 -13.175 0
TP_L2_00049.Mother TES_L2
TP_L2_00049.Visibility 0

TES_Pixel_L2.Copy TP_L2_00050
TP_L2_00050.Position -10.075 -11.625 0
TP_L2_00050.Mother TES_L2
TP_L2_00050.Visibility 0

TES_Pixel_L2.Copy TP_L2_00051
TP_L2_00051.Position -10.075 -10.075 0
TP_L2_00051.Mother TES_L2
TP_L2_00051.Visibility 0

TES_Pixel_L2.Copy TP_L2_00052
TP_L2_00052.Position -10.075 -8.525 0
TP_L2_00052.Mother TES_L2
TP_L2_00052.Visibility 0

TES_Pixel_L2.Copy TP_L2_00053
TP_L2_00053.Position -10.075 -6.975 0
TP_L2_00053.Mother TES_L2
TP_L2_00053.Visibility 0

TES_Pixel_L2.Copy TP_L2_00054
TP_L2_00054.Position -10.075 -5.425 0
TP_L2_00054.Mother TES_L2
TP_L2_00054.Visibility 0

TES_Pixel_L2.Copy TP_L2_00055
TP_L2_00055.Position -10.075 -3.875 0
TP_L2_00055.Mother TES_L2
TP_L2_00055.Visibility 0

TES_Pixel_L2.Copy TP_L2_00056
TP_L2_00056.Position -10.075 -2.325 0
TP_L2_00056.Mother TES_L2
TP_L2_00056.Visibility 0

TES_Pixel_L2.Copy TP_L2_00057
TP_L2_00057.Position -10.075 -0.775 0
TP_L2_00057.Mother TES_L2
TP_L2_00057.Visibility 0

TES_Pixel_L2.Copy TP_L2_00058
TP_L2_00058.Position -10.075 0.775 0
TP_L2_00058.Mother TES_L2
TP_L2_00058.Visibility 0

TES_Pixel_L2.Copy TP_L2_00059
TP_L2_00059.Position -10.075 2.325 0
TP_L2_00059.Mother TES_L2
TP_L2_00059.Visibility 0

TES_Pixel_L2.Copy TP_L2_00060
TP_L2_00060.Position -10.075 3.875 0
TP_L2_00060.Mother TES_L2
TP_L2_00060.Visibility 0

TES_Pixel_L2.Copy TP_L2_00061
TP_L2_00061.Position -10.075 5.425 0
TP_L2_00061.Mother TES_L2
TP_L2_00061.Visibility 0

TES_Pixel_L2.Copy TP_L2_00062
TP_L2_00062.Position -10.075 6.975 0
TP_L2_00062.Mother TES_L2
TP_L2_00062.Visibility 0

TES_Pixel_L2.Copy TP_L2_00063
TP_L2_00063.Position -10.075 8.525 0
TP_L2_00063.Mother TES_L2
TP_L2_00063.Visibility 0

TES_Pixel_L2.Copy TP_L2_00064
TP_L2_00064.Position -10.075 10.075 0
TP_L2_00064.Mother TES_L2
TP_L2_00064.Visibility 0

TES_Pixel_L2.Copy TP_L2_00065
TP_L2_00065.Position -10.075 11.625 0
TP_L2_00065.Mother TES_L2
TP_L2_00065.Visibility 0

TES_Pixel_L2.Copy TP_L2_00066
TP_L2_00066.Position -10.075 13.175 0
TP_L2_00066.Mother TES_L2
TP_L2_00066.Visibility 0

TES_Pixel_L2.Copy TP_L2_00067
TP_L2_00067.Position -10.075 14.725 0
TP_L2_00067.Mother TES_L2
TP_L2_00067.Visibility 0

TES_Pixel_L2.Copy TP_L2_00068
TP_L2_00068.Position -8.525 -14.725 0
TP_L2_00068.Mother TES_L2
TP_L2_00068.Visibility 0

TES_Pixel_L2.Copy TP_L2_00069
TP_L2_00069.Position -8.525 -13.175 0
TP_L2_00069.Mother TES_L2
TP_L2_00069.Visibility 0

TES_Pixel_L2.Copy TP_L2_00070
TP_L2_00070.Position -8.525 -11.625 0
TP_L2_00070.Mother TES_L2
TP_L2_00070.Visibility 0

TES_Pixel_L2.Copy TP_L2_00071
TP_L2_00071.Position -8.525 -10.075 0
TP_L2_00071.Mother TES_L2
TP_L2_00071.Visibility 0

TES_Pixel_L2.Copy TP_L2_00072
TP_L2_00072.Position -8.525 -8.525 0
TP_L2_00072.Mother TES_L2
TP_L2_00072.Visibility 0

TES_Pixel_L2.Copy TP_L2_00073
TP_L2_00073.Position -8.525 -6.975 0
TP_L2_00073.Mother TES_L2
TP_L2_00073.Visibility 0

TES_Pixel_L2.Copy TP_L2_00074
TP_L2_00074.Position -8.525 -5.425 0
TP_L2_00074.Mother TES_L2
TP_L2_00074.Visibility 0

TES_Pixel_L2.Copy TP_L2_00075
TP_L2_00075.Position -8.525 -3.875 0
TP_L2_00075.Mother TES_L2
TP_L2_00075.Visibility 0

TES_Pixel_L2.Copy TP_L2_00076
TP_L2_00076.Position -8.525 -2.325 0
TP_L2_00076.Mother TES_L2
TP_L2_00076.Visibility 0

TES_Pixel_L2.Copy TP_L2_00077
TP_L2_00077.Position -8.525 -0.775 0
TP_L2_00077.Mother TES_L2
TP_L2_00077.Visibility 0

TES_Pixel_L2.Copy TP_L2_00078
TP_L2_00078.Position -8.525 0.775 0
TP_L2_00078.Mother TES_L2
TP_L2_00078.Visibility 0

TES_Pixel_L2.Copy TP_L2_00079
TP_L2_00079.Position -8.525 2.325 0
TP_L2_00079.Mother TES_L2
TP_L2_00079.Visibility 0

TES_Pixel_L2.Copy TP_L2_00080
TP_L2_00080.Position -8.525 3.875 0
TP_L2_00080.Mother TES_L2
TP_L2_00080.Visibility 0

TES_Pixel_L2.Copy TP_L2_00081
TP_L2_00081.Position -8.525 5.425 0
TP_L2_00081.Mother TES_L2
TP_L2_00081.Visibility 0

TES_Pixel_L2.Copy TP_L2_00082
TP_L2_00082.Position -8.525 6.975 0
TP_L2_00082.Mother TES_L2
TP_L2_00082.Visibility 0

TES_Pixel_L2.Copy TP_L2_00083
TP_L2_00083.Position -8.525 8.525 0
TP_L2_00083.Mother TES_L2
TP_L2_00083.Visibility 0

TES_Pixel_L2.Copy TP_L2_00084
TP_L2_00084.Position -8.525 10.075 0
TP_L2_00084.Mother TES_L2
TP_L2_00084.Visibility 0

TES_Pixel_L2.Copy TP_L2_00085
TP_L2_00085.Position -8.525 11.625 0
TP_L2_00085.Mother TES_L2
TP_L2_00085.Visibility 0

TES_Pixel_L2.Copy TP_L2_00086
TP_L2_00086.Position -8.525 13.175 0
TP_L2_00086.Mother TES_L2
TP_L2_00086.Visibility 0

TES_Pixel_L2.Copy TP_L2_00087
TP_L2_00087.Position -8.525 14.725 0
TP_L2_00087.Mother TES_L2
TP_L2_00087.Visibility 0

TES_Pixel_L2.Copy TP_L2_00088
TP_L2_00088.Position -6.975 -14.725 0
TP_L2_00088.Mother TES_L2
TP_L2_00088.Visibility 0

TES_Pixel_L2.Copy TP_L2_00089
TP_L2_00089.Position -6.975 -13.175 0
TP_L2_00089.Mother TES_L2
TP_L2_00089.Visibility 0

TES_Pixel_L2.Copy TP_L2_00090
TP_L2_00090.Position -6.975 -11.625 0
TP_L2_00090.Mother TES_L2
TP_L2_00090.Visibility 0

TES_Pixel_L2.Copy TP_L2_00091
TP_L2_00091.Position -6.975 -10.075 0
TP_L2_00091.Mother TES_L2
TP_L2_00091.Visibility 0

TES_Pixel_L2.Copy TP_L2_00092
TP_L2_00092.Position -6.975 -8.525 0
TP_L2_00092.Mother TES_L2
TP_L2_00092.Visibility 0

TES_Pixel_L2.Copy TP_L2_00093
TP_L2_00093.Position -6.975 -6.975 0
TP_L2_00093.Mother TES_L2
TP_L2_00093.Visibility 0

TES_Pixel_L2.Copy TP_L2_00094
TP_L2_00094.Position -6.975 -5.425 0
TP_L2_00094.Mother TES_L2
TP_L2_00094.Visibility 0

TES_Pixel_L2.Copy TP_L2_00095
TP_L2_00095.Position -6.975 -3.875 0
TP_L2_00095.Mother TES_L2
TP_L2_00095.Visibility 0

TES_Pixel_L2.Copy TP_L2_00096
TP_L2_00096.Position -6.975 -2.325 0
TP_L2_00096.Mother TES_L2
TP_L2_00096.Visibility 0

TES_Pixel_L2.Copy TP_L2_00097
TP_L2_00097.Position -6.975 -0.775 0
TP_L2_00097.Mother TES_L2
TP_L2_00097.Visibility 0

TES_Pixel_L2.Copy TP_L2_00098
TP_L2_00098.Position -6.975 0.775 0
TP_L2_00098.Mother TES_L2
TP_L2_00098.Visibility 0

TES_Pixel_L2.Copy TP_L2_00099
TP_L2_00099.Position -6.975 2.325 0
TP_L2_00099.Mother TES_L2
TP_L2_00099.Visibility 0

TES_Pixel_L2.Copy TP_L2_00100
TP_L2_00100.Position -6.975 3.875 0
TP_L2_00100.Mother TES_L2
TP_L2_00100.Visibility 0

TES_Pixel_L2.Copy TP_L2_00101
TP_L2_00101.Position -6.975 5.425 0
TP_L2_00101.Mother TES_L2
TP_L2_00101.Visibility 0

TES_Pixel_L2.Copy TP_L2_00102
TP_L2_00102.Position -6.975 6.975 0
TP_L2_00102.Mother TES_L2
TP_L2_00102.Visibility 0

TES_Pixel_L2.Copy TP_L2_00103
TP_L2_00103.Position -6.975 8.525 0
TP_L2_00103.Mother TES_L2
TP_L2_00103.Visibility 0

TES_Pixel_L2.Copy TP_L2_00104
TP_L2_00104.Position -6.975 10.075 0
TP_L2_00104.Mother TES_L2
TP_L2_00104.Visibility 0

TES_Pixel_L2.Copy TP_L2_00105
TP_L2_00105.Position -6.975 11.625 0
TP_L2_00105.Mother TES_L2
TP_L2_00105.Visibility 0

TES_Pixel_L2.Copy TP_L2_00106
TP_L2_00106.Position -6.975 13.175 0
TP_L2_00106.Mother TES_L2
TP_L2_00106.Visibility 0

TES_Pixel_L2.Copy TP_L2_00107
TP_L2_00107.Position -6.975 14.725 0
TP_L2_00107.Mother TES_L2
TP_L2_00107.Visibility 0

TES_Pixel_L2.Copy TP_L2_00108
TP_L2_00108.Position -5.425 -14.725 0
TP_L2_00108.Mother TES_L2
TP_L2_00108.Visibility 0

TES_Pixel_L2.Copy TP_L2_00109
TP_L2_00109.Position -5.425 -13.175 0
TP_L2_00109.Mother TES_L2
TP_L2_00109.Visibility 0

TES_Pixel_L2.Copy TP_L2_00110
TP_L2_00110.Position -5.425 -11.625 0
TP_L2_00110.Mother TES_L2
TP_L2_00110.Visibility 0

TES_Pixel_L2.Copy TP_L2_00111
TP_L2_00111.Position -5.425 -10.075 0
TP_L2_00111.Mother TES_L2
TP_L2_00111.Visibility 0

TES_Pixel_L2.Copy TP_L2_00112
TP_L2_00112.Position -5.425 -8.525 0
TP_L2_00112.Mother TES_L2
TP_L2_00112.Visibility 0

TES_Pixel_L2.Copy TP_L2_00113
TP_L2_00113.Position -5.425 -6.975 0
TP_L2_00113.Mother TES_L2
TP_L2_00113.Visibility 0

TES_Pixel_L2.Copy TP_L2_00114
TP_L2_00114.Position -5.425 -5.425 0
TP_L2_00114.Mother TES_L2
TP_L2_00114.Visibility 0

TES_Pixel_L2.Copy TP_L2_00115
TP_L2_00115.Position -5.425 -3.875 0
TP_L2_00115.Mother TES_L2
TP_L2_00115.Visibility 0

TES_Pixel_L2.Copy TP_L2_00116
TP_L2_00116.Position -5.425 -2.325 0
TP_L2_00116.Mother TES_L2
TP_L2_00116.Visibility 0

TES_Pixel_L2.Copy TP_L2_00117
TP_L2_00117.Position -5.425 -0.775 0
TP_L2_00117.Mother TES_L2
TP_L2_00117.Visibility 0

TES_Pixel_L2.Copy TP_L2_00118
TP_L2_00118.Position -5.425 0.775 0
TP_L2_00118.Mother TES_L2
TP_L2_00118.Visibility 0

TES_Pixel_L2.Copy TP_L2_00119
TP_L2_00119.Position -5.425 2.325 0
TP_L2_00119.Mother TES_L2
TP_L2_00119.Visibility 0

TES_Pixel_L2.Copy TP_L2_00120
TP_L2_00120.Position -5.425 3.875 0
TP_L2_00120.Mother TES_L2
TP_L2_00120.Visibility 0

TES_Pixel_L2.Copy TP_L2_00121
TP_L2_00121.Position -5.425 5.425 0
TP_L2_00121.Mother TES_L2
TP_L2_00121.Visibility 0

TES_Pixel_L2.Copy TP_L2_00122
TP_L2_00122.Position -5.425 6.975 0
TP_L2_00122.Mother TES_L2
TP_L2_00122.Visibility 0

TES_Pixel_L2.Copy TP_L2_00123
TP_L2_00123.Position -5.425 8.525 0
TP_L2_00123.Mother TES_L2
TP_L2_00123.Visibility 0

TES_Pixel_L2.Copy TP_L2_00124
TP_L2_00124.Position -5.425 10.075 0
TP_L2_00124.Mother TES_L2
TP_L2_00124.Visibility 0

TES_Pixel_L2.Copy TP_L2_00125
TP_L2_00125.Position -5.425 11.625 0
TP_L2_00125.Mother TES_L2
TP_L2_00125.Visibility 0

TES_Pixel_L2.Copy TP_L2_00126
TP_L2_00126.Position -5.425 13.175 0
TP_L2_00126.Mother TES_L2
TP_L2_00126.Visibility 0

TES_Pixel_L2.Copy TP_L2_00127
TP_L2_00127.Position -5.425 14.725 0
TP_L2_00127.Mother TES_L2
TP_L2_00127.Visibility 0

TES_Pixel_L2.Copy TP_L2_00128
TP_L2_00128.Position -3.875 -14.725 0
TP_L2_00128.Mother TES_L2
TP_L2_00128.Visibility 0

TES_Pixel_L2.Copy TP_L2_00129
TP_L2_00129.Position -3.875 -13.175 0
TP_L2_00129.Mother TES_L2
TP_L2_00129.Visibility 0

TES_Pixel_L2.Copy TP_L2_00130
TP_L2_00130.Position -3.875 -11.625 0
TP_L2_00130.Mother TES_L2
TP_L2_00130.Visibility 0

TES_Pixel_L2.Copy TP_L2_00131
TP_L2_00131.Position -3.875 -10.075 0
TP_L2_00131.Mother TES_L2
TP_L2_00131.Visibility 0

TES_Pixel_L2.Copy TP_L2_00132
TP_L2_00132.Position -3.875 -8.525 0
TP_L2_00132.Mother TES_L2
TP_L2_00132.Visibility 0

TES_Pixel_L2.Copy TP_L2_00133
TP_L2_00133.Position -3.875 -6.975 0
TP_L2_00133.Mother TES_L2
TP_L2_00133.Visibility 0

TES_Pixel_L2.Copy TP_L2_00134
TP_L2_00134.Position -3.875 -5.425 0
TP_L2_00134.Mother TES_L2
TP_L2_00134.Visibility 0

TES_Pixel_L2.Copy TP_L2_00135
TP_L2_00135.Position -3.875 -3.875 0
TP_L2_00135.Mother TES_L2
TP_L2_00135.Visibility 0

TES_Pixel_L2.Copy TP_L2_00136
TP_L2_00136.Position -3.875 -2.325 0
TP_L2_00136.Mother TES_L2
TP_L2_00136.Visibility 0

TES_Pixel_L2.Copy TP_L2_00137
TP_L2_00137.Position -3.875 -0.775 0
TP_L2_00137.Mother TES_L2
TP_L2_00137.Visibility 0

TES_Pixel_L2.Copy TP_L2_00138
TP_L2_00138.Position -3.875 0.775 0
TP_L2_00138.Mother TES_L2
TP_L2_00138.Visibility 0

TES_Pixel_L2.Copy TP_L2_00139
TP_L2_00139.Position -3.875 2.325 0
TP_L2_00139.Mother TES_L2
TP_L2_00139.Visibility 0

TES_Pixel_L2.Copy TP_L2_00140
TP_L2_00140.Position -3.875 3.875 0
TP_L2_00140.Mother TES_L2
TP_L2_00140.Visibility 0

TES_Pixel_L2.Copy TP_L2_00141
TP_L2_00141.Position -3.875 5.425 0
TP_L2_00141.Mother TES_L2
TP_L2_00141.Visibility 0

TES_Pixel_L2.Copy TP_L2_00142
TP_L2_00142.Position -3.875 6.975 0
TP_L2_00142.Mother TES_L2
TP_L2_00142.Visibility 0

TES_Pixel_L2.Copy TP_L2_00143
TP_L2_00143.Position -3.875 8.525 0
TP_L2_00143.Mother TES_L2
TP_L2_00143.Visibility 0

TES_Pixel_L2.Copy TP_L2_00144
TP_L2_00144.Position -3.875 10.075 0
TP_L2_00144.Mother TES_L2
TP_L2_00144.Visibility 0

TES_Pixel_L2.Copy TP_L2_00145
TP_L2_00145.Position -3.875 11.625 0
TP_L2_00145.Mother TES_L2
TP_L2_00145.Visibility 0

TES_Pixel_L2.Copy TP_L2_00146
TP_L2_00146.Position -3.875 13.175 0
TP_L2_00146.Mother TES_L2
TP_L2_00146.Visibility 0

TES_Pixel_L2.Copy TP_L2_00147
TP_L2_00147.Position -3.875 14.725 0
TP_L2_00147.Mother TES_L2
TP_L2_00147.Visibility 0

TES_Pixel_L2.Copy TP_L2_00148
TP_L2_00148.Position -2.325 -14.725 0
TP_L2_00148.Mother TES_L2
TP_L2_00148.Visibility 0

TES_Pixel_L2.Copy TP_L2_00149
TP_L2_00149.Position -2.325 -13.175 0
TP_L2_00149.Mother TES_L2
TP_L2_00149.Visibility 0

TES_Pixel_L2.Copy TP_L2_00150
TP_L2_00150.Position -2.325 -11.625 0
TP_L2_00150.Mother TES_L2
TP_L2_00150.Visibility 0

TES_Pixel_L2.Copy TP_L2_00151
TP_L2_00151.Position -2.325 -10.075 0
TP_L2_00151.Mother TES_L2
TP_L2_00151.Visibility 0

TES_Pixel_L2.Copy TP_L2_00152
TP_L2_00152.Position -2.325 -8.525 0
TP_L2_00152.Mother TES_L2
TP_L2_00152.Visibility 0

TES_Pixel_L2.Copy TP_L2_00153
TP_L2_00153.Position -2.325 -6.975 0
TP_L2_00153.Mother TES_L2
TP_L2_00153.Visibility 0

TES_Pixel_L2.Copy TP_L2_00154
TP_L2_00154.Position -2.325 -5.425 0
TP_L2_00154.Mother TES_L2
TP_L2_00154.Visibility 0

TES_Pixel_L2.Copy TP_L2_00155
TP_L2_00155.Position -2.325 -3.875 0
TP_L2_00155.Mother TES_L2
TP_L2_00155.Visibility 0

TES_Pixel_L2.Copy TP_L2_00156
TP_L2_00156.Position -2.325 -2.325 0
TP_L2_00156.Mother TES_L2
TP_L2_00156.Visibility 0

TES_Pixel_L2.Copy TP_L2_00157
TP_L2_00157.Position -2.325 -0.775 0
TP_L2_00157.Mother TES_L2
TP_L2_00157.Visibility 0

TES_Pixel_L2.Copy TP_L2_00158
TP_L2_00158.Position -2.325 0.775 0
TP_L2_00158.Mother TES_L2
TP_L2_00158.Visibility 0

TES_Pixel_L2.Copy TP_L2_00159
TP_L2_00159.Position -2.325 2.325 0
TP_L2_00159.Mother TES_L2
TP_L2_00159.Visibility 0

TES_Pixel_L2.Copy TP_L2_00160
TP_L2_00160.Position -2.325 3.875 0
TP_L2_00160.Mother TES_L2
TP_L2_00160.Visibility 0

TES_Pixel_L2.Copy TP_L2_00161
TP_L2_00161.Position -2.325 5.425 0
TP_L2_00161.Mother TES_L2
TP_L2_00161.Visibility 0

TES_Pixel_L2.Copy TP_L2_00162
TP_L2_00162.Position -2.325 6.975 0
TP_L2_00162.Mother TES_L2
TP_L2_00162.Visibility 0

TES_Pixel_L2.Copy TP_L2_00163
TP_L2_00163.Position -2.325 8.525 0
TP_L2_00163.Mother TES_L2
TP_L2_00163.Visibility 0

TES_Pixel_L2.Copy TP_L2_00164
TP_L2_00164.Position -2.325 10.075 0
TP_L2_00164.Mother TES_L2
TP_L2_00164.Visibility 0

TES_Pixel_L2.Copy TP_L2_00165
TP_L2_00165.Position -2.325 11.625 0
TP_L2_00165.Mother TES_L2
TP_L2_00165.Visibility 0

TES_Pixel_L2.Copy TP_L2_00166
TP_L2_00166.Position -2.325 13.175 0
TP_L2_00166.Mother TES_L2
TP_L2_00166.Visibility 0

TES_Pixel_L2.Copy TP_L2_00167
TP_L2_00167.Position -2.325 14.725 0
TP_L2_00167.Mother TES_L2
TP_L2_00167.Visibility 0

TES_Pixel_L2.Copy TP_L2_00168
TP_L2_00168.Position -0.775 -14.725 0
TP_L2_00168.Mother TES_L2
TP_L2_00168.Visibility 0

TES_Pixel_L2.Copy TP_L2_00169
TP_L2_00169.Position -0.775 -13.175 0
TP_L2_00169.Mother TES_L2
TP_L2_00169.Visibility 0

TES_Pixel_L2.Copy TP_L2_00170
TP_L2_00170.Position -0.775 -11.625 0
TP_L2_00170.Mother TES_L2
TP_L2_00170.Visibility 0

TES_Pixel_L2.Copy TP_L2_00171
TP_L2_00171.Position -0.775 -10.075 0
TP_L2_00171.Mother TES_L2
TP_L2_00171.Visibility 0

TES_Pixel_L2.Copy TP_L2_00172
TP_L2_00172.Position -0.775 -8.525 0
TP_L2_00172.Mother TES_L2
TP_L2_00172.Visibility 0

TES_Pixel_L2.Copy TP_L2_00173
TP_L2_00173.Position -0.775 -6.975 0
TP_L2_00173.Mother TES_L2
TP_L2_00173.Visibility 0

TES_Pixel_L2.Copy TP_L2_00174
TP_L2_00174.Position -0.775 -5.425 0
TP_L2_00174.Mother TES_L2
TP_L2_00174.Visibility 0

TES_Pixel_L2.Copy TP_L2_00175
TP_L2_00175.Position -0.775 -3.875 0
TP_L2_00175.Mother TES_L2
TP_L2_00175.Visibility 0

TES_Pixel_L2.Copy TP_L2_00176
TP_L2_00176.Position -0.775 -2.325 0
TP_L2_00176.Mother TES_L2
TP_L2_00176.Visibility 0

TES_Pixel_L2.Copy TP_L2_00177
TP_L2_00177.Position -0.775 -0.775 0
TP_L2_00177.Mother TES_L2
TP_L2_00177.Visibility 0

TES_Pixel_L2.Copy TP_L2_00178
TP_L2_00178.Position -0.775 0.775 0
TP_L2_00178.Mother TES_L2
TP_L2_00178.Visibility 0

TES_Pixel_L2.Copy TP_L2_00179
TP_L2_00179.Position -0.775 2.325 0
TP_L2_00179.Mother TES_L2
TP_L2_00179.Visibility 0

TES_Pixel_L2.Copy TP_L2_00180
TP_L2_00180.Position -0.775 3.875 0
TP_L2_00180.Mother TES_L2
TP_L2_00180.Visibility 0

TES_Pixel_L2.Copy TP_L2_00181
TP_L2_00181.Position -0.775 5.425 0
TP_L2_00181.Mother TES_L2
TP_L2_00181.Visibility 0

TES_Pixel_L2.Copy TP_L2_00182
TP_L2_00182.Position -0.775 6.975 0
TP_L2_00182.Mother TES_L2
TP_L2_00182.Visibility 0

TES_Pixel_L2.Copy TP_L2_00183
TP_L2_00183.Position -0.775 8.525 0
TP_L2_00183.Mother TES_L2
TP_L2_00183.Visibility 0

TES_Pixel_L2.Copy TP_L2_00184
TP_L2_00184.Position -0.775 10.075 0
TP_L2_00184.Mother TES_L2
TP_L2_00184.Visibility 0

TES_Pixel_L2.Copy TP_L2_00185
TP_L2_00185.Position -0.775 11.625 0
TP_L2_00185.Mother TES_L2
TP_L2_00185.Visibility 0

TES_Pixel_L2.Copy TP_L2_00186
TP_L2_00186.Position -0.775 13.175 0
TP_L2_00186.Mother TES_L2
TP_L2_00186.Visibility 0

TES_Pixel_L2.Copy TP_L2_00187
TP_L2_00187.Position -0.775 14.725 0
TP_L2_00187.Mother TES_L2
TP_L2_00187.Visibility 0

TES_Pixel_L2.Copy TP_L2_00188
TP_L2_00188.Position 0.775 -14.725 0
TP_L2_00188.Mother TES_L2
TP_L2_00188.Visibility 0

TES_Pixel_L2.Copy TP_L2_00189
TP_L2_00189.Position 0.775 -13.175 0
TP_L2_00189.Mother TES_L2
TP_L2_00189.Visibility 0

TES_Pixel_L2.Copy TP_L2_00190
TP_L2_00190.Position 0.775 -11.625 0
TP_L2_00190.Mother TES_L2
TP_L2_00190.Visibility 0

TES_Pixel_L2.Copy TP_L2_00191
TP_L2_00191.Position 0.775 -10.075 0
TP_L2_00191.Mother TES_L2
TP_L2_00191.Visibility 0

TES_Pixel_L2.Copy TP_L2_00192
TP_L2_00192.Position 0.775 -8.525 0
TP_L2_00192.Mother TES_L2
TP_L2_00192.Visibility 0

TES_Pixel_L2.Copy TP_L2_00193
TP_L2_00193.Position 0.775 -6.975 0
TP_L2_00193.Mother TES_L2
TP_L2_00193.Visibility 0

TES_Pixel_L2.Copy TP_L2_00194
TP_L2_00194.Position 0.775 -5.425 0
TP_L2_00194.Mother TES_L2
TP_L2_00194.Visibility 0

TES_Pixel_L2.Copy TP_L2_00195
TP_L2_00195.Position 0.775 -3.875 0
TP_L2_00195.Mother TES_L2
TP_L2_00195.Visibility 0

TES_Pixel_L2.Copy TP_L2_00196
TP_L2_00196.Position 0.775 -2.325 0
TP_L2_00196.Mother TES_L2
TP_L2_00196.Visibility 0

TES_Pixel_L2.Copy TP_L2_00197
TP_L2_00197.Position 0.775 -0.775 0
TP_L2_00197.Mother TES_L2
TP_L2_00197.Visibility 0

TES_Pixel_L2.Copy TP_L2_00198
TP_L2_00198.Position 0.775 0.775 0
TP_L2_00198.Mother TES_L2
TP_L2_00198.Visibility 0

TES_Pixel_L2.Copy TP_L2_00199
TP_L2_00199.Position 0.775 2.325 0
TP_L2_00199.Mother TES_L2
TP_L2_00199.Visibility 0

TES_Pixel_L2.Copy TP_L2_00200
TP_L2_00200.Position 0.775 3.875 0
TP_L2_00200.Mother TES_L2
TP_L2_00200.Visibility 0

TES_Pixel_L2.Copy TP_L2_00201
TP_L2_00201.Position 0.775 5.425 0
TP_L2_00201.Mother TES_L2
TP_L2_00201.Visibility 0

TES_Pixel_L2.Copy TP_L2_00202
TP_L2_00202.Position 0.775 6.975 0
TP_L2_00202.Mother TES_L2
TP_L2_00202.Visibility 0

TES_Pixel_L2.Copy TP_L2_00203
TP_L2_00203.Position 0.775 8.525 0
TP_L2_00203.Mother TES_L2
TP_L2_00203.Visibility 0

TES_Pixel_L2.Copy TP_L2_00204
TP_L2_00204.Position 0.775 10.075 0
TP_L2_00204.Mother TES_L2
TP_L2_00204.Visibility 0

TES_Pixel_L2.Copy TP_L2_00205
TP_L2_00205.Position 0.775 11.625 0
TP_L2_00205.Mother TES_L2
TP_L2_00205.Visibility 0

TES_Pixel_L2.Copy TP_L2_00206
TP_L2_00206.Position 0.775 13.175 0
TP_L2_00206.Mother TES_L2
TP_L2_00206.Visibility 0

TES_Pixel_L2.Copy TP_L2_00207
TP_L2_00207.Position 0.775 14.725 0
TP_L2_00207.Mother TES_L2
TP_L2_00207.Visibility 0

TES_Pixel_L2.Copy TP_L2_00208
TP_L2_00208.Position 2.325 -14.725 0
TP_L2_00208.Mother TES_L2
TP_L2_00208.Visibility 0

TES_Pixel_L2.Copy TP_L2_00209
TP_L2_00209.Position 2.325 -13.175 0
TP_L2_00209.Mother TES_L2
TP_L2_00209.Visibility 0

TES_Pixel_L2.Copy TP_L2_00210
TP_L2_00210.Position 2.325 -11.625 0
TP_L2_00210.Mother TES_L2
TP_L2_00210.Visibility 0

TES_Pixel_L2.Copy TP_L2_00211
TP_L2_00211.Position 2.325 -10.075 0
TP_L2_00211.Mother TES_L2
TP_L2_00211.Visibility 0

TES_Pixel_L2.Copy TP_L2_00212
TP_L2_00212.Position 2.325 -8.525 0
TP_L2_00212.Mother TES_L2
TP_L2_00212.Visibility 0

TES_Pixel_L2.Copy TP_L2_00213
TP_L2_00213.Position 2.325 -6.975 0
TP_L2_00213.Mother TES_L2
TP_L2_00213.Visibility 0

TES_Pixel_L2.Copy TP_L2_00214
TP_L2_00214.Position 2.325 -5.425 0
TP_L2_00214.Mother TES_L2
TP_L2_00214.Visibility 0

TES_Pixel_L2.Copy TP_L2_00215
TP_L2_00215.Position 2.325 -3.875 0
TP_L2_00215.Mother TES_L2
TP_L2_00215.Visibility 0

TES_Pixel_L2.Copy TP_L2_00216
TP_L2_00216.Position 2.325 -2.325 0
TP_L2_00216.Mother TES_L2
TP_L2_00216.Visibility 0

TES_Pixel_L2.Copy TP_L2_00217
TP_L2_00217.Position 2.325 -0.775 0
TP_L2_00217.Mother TES_L2
TP_L2_00217.Visibility 0

TES_Pixel_L2.Copy TP_L2_00218
TP_L2_00218.Position 2.325 0.775 0
TP_L2_00218.Mother TES_L2
TP_L2_00218.Visibility 0

TES_Pixel_L2.Copy TP_L2_00219
TP_L2_00219.Position 2.325 2.325 0
TP_L2_00219.Mother TES_L2
TP_L2_00219.Visibility 0

TES_Pixel_L2.Copy TP_L2_00220
TP_L2_00220.Position 2.325 3.875 0
TP_L2_00220.Mother TES_L2
TP_L2_00220.Visibility 0

TES_Pixel_L2.Copy TP_L2_00221
TP_L2_00221.Position 2.325 5.425 0
TP_L2_00221.Mother TES_L2
TP_L2_00221.Visibility 0

TES_Pixel_L2.Copy TP_L2_00222
TP_L2_00222.Position 2.325 6.975 0
TP_L2_00222.Mother TES_L2
TP_L2_00222.Visibility 0

TES_Pixel_L2.Copy TP_L2_00223
TP_L2_00223.Position 2.325 8.525 0
TP_L2_00223.Mother TES_L2
TP_L2_00223.Visibility 0

TES_Pixel_L2.Copy TP_L2_00224
TP_L2_00224.Position 2.325 10.075 0
TP_L2_00224.Mother TES_L2
TP_L2_00224.Visibility 0

TES_Pixel_L2.Copy TP_L2_00225
TP_L2_00225.Position 2.325 11.625 0
TP_L2_00225.Mother TES_L2
TP_L2_00225.Visibility 0

TES_Pixel_L2.Copy TP_L2_00226
TP_L2_00226.Position 2.325 13.175 0
TP_L2_00226.Mother TES_L2
TP_L2_00226.Visibility 0

TES_Pixel_L2.Copy TP_L2_00227
TP_L2_00227.Position 2.325 14.725 0
TP_L2_00227.Mother TES_L2
TP_L2_00227.Visibility 0

TES_Pixel_L2.Copy TP_L2_00228
TP_L2_00228.Position 3.875 -14.725 0
TP_L2_00228.Mother TES_L2
TP_L2_00228.Visibility 0

TES_Pixel_L2.Copy TP_L2_00229
TP_L2_00229.Position 3.875 -13.175 0
TP_L2_00229.Mother TES_L2
TP_L2_00229.Visibility 0

TES_Pixel_L2.Copy TP_L2_00230
TP_L2_00230.Position 3.875 -11.625 0
TP_L2_00230.Mother TES_L2
TP_L2_00230.Visibility 0

TES_Pixel_L2.Copy TP_L2_00231
TP_L2_00231.Position 3.875 -10.075 0
TP_L2_00231.Mother TES_L2
TP_L2_00231.Visibility 0

TES_Pixel_L2.Copy TP_L2_00232
TP_L2_00232.Position 3.875 -8.525 0
TP_L2_00232.Mother TES_L2
TP_L2_00232.Visibility 0

TES_Pixel_L2.Copy TP_L2_00233
TP_L2_00233.Position 3.875 -6.975 0
TP_L2_00233.Mother TES_L2
TP_L2_00233.Visibility 0

TES_Pixel_L2.Copy TP_L2_00234
TP_L2_00234.Position 3.875 -5.425 0
TP_L2_00234.Mother TES_L2
TP_L2_00234.Visibility 0

TES_Pixel_L2.Copy TP_L2_00235
TP_L2_00235.Position 3.875 -3.875 0
TP_L2_00235.Mother TES_L2
TP_L2_00235.Visibility 0

TES_Pixel_L2.Copy TP_L2_00236
TP_L2_00236.Position 3.875 -2.325 0
TP_L2_00236.Mother TES_L2
TP_L2_00236.Visibility 0

TES_Pixel_L2.Copy TP_L2_00237
TP_L2_00237.Position 3.875 -0.775 0
TP_L2_00237.Mother TES_L2
TP_L2_00237.Visibility 0

TES_Pixel_L2.Copy TP_L2_00238
TP_L2_00238.Position 3.875 0.775 0
TP_L2_00238.Mother TES_L2
TP_L2_00238.Visibility 0

TES_Pixel_L2.Copy TP_L2_00239
TP_L2_00239.Position 3.875 2.325 0
TP_L2_00239.Mother TES_L2
TP_L2_00239.Visibility 0

TES_Pixel_L2.Copy TP_L2_00240
TP_L2_00240.Position 3.875 3.875 0
TP_L2_00240.Mother TES_L2
TP_L2_00240.Visibility 0

TES_Pixel_L2.Copy TP_L2_00241
TP_L2_00241.Position 3.875 5.425 0
TP_L2_00241.Mother TES_L2
TP_L2_00241.Visibility 0

TES_Pixel_L2.Copy TP_L2_00242
TP_L2_00242.Position 3.875 6.975 0
TP_L2_00242.Mother TES_L2
TP_L2_00242.Visibility 0

TES_Pixel_L2.Copy TP_L2_00243
TP_L2_00243.Position 3.875 8.525 0
TP_L2_00243.Mother TES_L2
TP_L2_00243.Visibility 0

TES_Pixel_L2.Copy TP_L2_00244
TP_L2_00244.Position 3.875 10.075 0
TP_L2_00244.Mother TES_L2
TP_L2_00244.Visibility 0

TES_Pixel_L2.Copy TP_L2_00245
TP_L2_00245.Position 3.875 11.625 0
TP_L2_00245.Mother TES_L2
TP_L2_00245.Visibility 0

TES_Pixel_L2.Copy TP_L2_00246
TP_L2_00246.Position 3.875 13.175 0
TP_L2_00246.Mother TES_L2
TP_L2_00246.Visibility 0

TES_Pixel_L2.Copy TP_L2_00247
TP_L2_00247.Position 3.875 14.725 0
TP_L2_00247.Mother TES_L2
TP_L2_00247.Visibility 0

TES_Pixel_L2.Copy TP_L2_00248
TP_L2_00248.Position 5.425 -14.725 0
TP_L2_00248.Mother TES_L2
TP_L2_00248.Visibility 0

TES_Pixel_L2.Copy TP_L2_00249
TP_L2_00249.Position 5.425 -13.175 0
TP_L2_00249.Mother TES_L2
TP_L2_00249.Visibility 0

TES_Pixel_L2.Copy TP_L2_00250
TP_L2_00250.Position 5.425 -11.625 0
TP_L2_00250.Mother TES_L2
TP_L2_00250.Visibility 0

TES_Pixel_L2.Copy TP_L2_00251
TP_L2_00251.Position 5.425 -10.075 0
TP_L2_00251.Mother TES_L2
TP_L2_00251.Visibility 0

TES_Pixel_L2.Copy TP_L2_00252
TP_L2_00252.Position 5.425 -8.525 0
TP_L2_00252.Mother TES_L2
TP_L2_00252.Visibility 0

TES_Pixel_L2.Copy TP_L2_00253
TP_L2_00253.Position 5.425 -6.975 0
TP_L2_00253.Mother TES_L2
TP_L2_00253.Visibility 0

TES_Pixel_L2.Copy TP_L2_00254
TP_L2_00254.Position 5.425 -5.425 0
TP_L2_00254.Mother TES_L2
TP_L2_00254.Visibility 0

TES_Pixel_L2.Copy TP_L2_00255
TP_L2_00255.Position 5.425 -3.875 0
TP_L2_00255.Mother TES_L2
TP_L2_00255.Visibility 0

TES_Pixel_L2.Copy TP_L2_00256
TP_L2_00256.Position 5.425 -2.325 0
TP_L2_00256.Mother TES_L2
TP_L2_00256.Visibility 0

TES_Pixel_L2.Copy TP_L2_00257
TP_L2_00257.Position 5.425 -0.775 0
TP_L2_00257.Mother TES_L2
TP_L2_00257.Visibility 0

TES_Pixel_L2.Copy TP_L2_00258
TP_L2_00258.Position 5.425 0.775 0
TP_L2_00258.Mother TES_L2
TP_L2_00258.Visibility 0

TES_Pixel_L2.Copy TP_L2_00259
TP_L2_00259.Position 5.425 2.325 0
TP_L2_00259.Mother TES_L2
TP_L2_00259.Visibility 0

TES_Pixel_L2.Copy TP_L2_00260
TP_L2_00260.Position 5.425 3.875 0
TP_L2_00260.Mother TES_L2
TP_L2_00260.Visibility 0

TES_Pixel_L2.Copy TP_L2_00261
TP_L2_00261.Position 5.425 5.425 0
TP_L2_00261.Mother TES_L2
TP_L2_00261.Visibility 0

TES_Pixel_L2.Copy TP_L2_00262
TP_L2_00262.Position 5.425 6.975 0
TP_L2_00262.Mother TES_L2
TP_L2_00262.Visibility 0

TES_Pixel_L2.Copy TP_L2_00263
TP_L2_00263.Position 5.425 8.525 0
TP_L2_00263.Mother TES_L2
TP_L2_00263.Visibility 0

TES_Pixel_L2.Copy TP_L2_00264
TP_L2_00264.Position 5.425 10.075 0
TP_L2_00264.Mother TES_L2
TP_L2_00264.Visibility 0

TES_Pixel_L2.Copy TP_L2_00265
TP_L2_00265.Position 5.425 11.625 0
TP_L2_00265.Mother TES_L2
TP_L2_00265.Visibility 0

TES_Pixel_L2.Copy TP_L2_00266
TP_L2_00266.Position 5.425 13.175 0
TP_L2_00266.Mother TES_L2
TP_L2_00266.Visibility 0

TES_Pixel_L2.Copy TP_L2_00267
TP_L2_00267.Position 5.425 14.725 0
TP_L2_00267.Mother TES_L2
TP_L2_00267.Visibility 0

TES_Pixel_L2.Copy TP_L2_00268
TP_L2_00268.Position 6.975 -14.725 0
TP_L2_00268.Mother TES_L2
TP_L2_00268.Visibility 0

TES_Pixel_L2.Copy TP_L2_00269
TP_L2_00269.Position 6.975 -13.175 0
TP_L2_00269.Mother TES_L2
TP_L2_00269.Visibility 0

TES_Pixel_L2.Copy TP_L2_00270
TP_L2_00270.Position 6.975 -11.625 0
TP_L2_00270.Mother TES_L2
TP_L2_00270.Visibility 0

TES_Pixel_L2.Copy TP_L2_00271
TP_L2_00271.Position 6.975 -10.075 0
TP_L2_00271.Mother TES_L2
TP_L2_00271.Visibility 0

TES_Pixel_L2.Copy TP_L2_00272
TP_L2_00272.Position 6.975 -8.525 0
TP_L2_00272.Mother TES_L2
TP_L2_00272.Visibility 0

TES_Pixel_L2.Copy TP_L2_00273
TP_L2_00273.Position 6.975 -6.975 0
TP_L2_00273.Mother TES_L2
TP_L2_00273.Visibility 0

TES_Pixel_L2.Copy TP_L2_00274
TP_L2_00274.Position 6.975 -5.425 0
TP_L2_00274.Mother TES_L2
TP_L2_00274.Visibility 0

TES_Pixel_L2.Copy TP_L2_00275
TP_L2_00275.Position 6.975 -3.875 0
TP_L2_00275.Mother TES_L2
TP_L2_00275.Visibility 0

TES_Pixel_L2.Copy TP_L2_00276
TP_L2_00276.Position 6.975 -2.325 0
TP_L2_00276.Mother TES_L2
TP_L2_00276.Visibility 0

TES_Pixel_L2.Copy TP_L2_00277
TP_L2_00277.Position 6.975 -0.775 0
TP_L2_00277.Mother TES_L2
TP_L2_00277.Visibility 0

TES_Pixel_L2.Copy TP_L2_00278
TP_L2_00278.Position 6.975 0.775 0
TP_L2_00278.Mother TES_L2
TP_L2_00278.Visibility 0

TES_Pixel_L2.Copy TP_L2_00279
TP_L2_00279.Position 6.975 2.325 0
TP_L2_00279.Mother TES_L2
TP_L2_00279.Visibility 0

TES_Pixel_L2.Copy TP_L2_00280
TP_L2_00280.Position 6.975 3.875 0
TP_L2_00280.Mother TES_L2
TP_L2_00280.Visibility 0

TES_Pixel_L2.Copy TP_L2_00281
TP_L2_00281.Position 6.975 5.425 0
TP_L2_00281.Mother TES_L2
TP_L2_00281.Visibility 0

TES_Pixel_L2.Copy TP_L2_00282
TP_L2_00282.Position 6.975 6.975 0
TP_L2_00282.Mother TES_L2
TP_L2_00282.Visibility 0

TES_Pixel_L2.Copy TP_L2_00283
TP_L2_00283.Position 6.975 8.525 0
TP_L2_00283.Mother TES_L2
TP_L2_00283.Visibility 0

TES_Pixel_L2.Copy TP_L2_00284
TP_L2_00284.Position 6.975 10.075 0
TP_L2_00284.Mother TES_L2
TP_L2_00284.Visibility 0

TES_Pixel_L2.Copy TP_L2_00285
TP_L2_00285.Position 6.975 11.625 0
TP_L2_00285.Mother TES_L2
TP_L2_00285.Visibility 0

TES_Pixel_L2.Copy TP_L2_00286
TP_L2_00286.Position 6.975 13.175 0
TP_L2_00286.Mother TES_L2
TP_L2_00286.Visibility 0

TES_Pixel_L2.Copy TP_L2_00287
TP_L2_00287.Position 6.975 14.725 0
TP_L2_00287.Mother TES_L2
TP_L2_00287.Visibility 0

TES_Pixel_L2.Copy TP_L2_00288
TP_L2_00288.Position 8.525 -14.725 0
TP_L2_00288.Mother TES_L2
TP_L2_00288.Visibility 0

TES_Pixel_L2.Copy TP_L2_00289
TP_L2_00289.Position 8.525 -13.175 0
TP_L2_00289.Mother TES_L2
TP_L2_00289.Visibility 0

TES_Pixel_L2.Copy TP_L2_00290
TP_L2_00290.Position 8.525 -11.625 0
TP_L2_00290.Mother TES_L2
TP_L2_00290.Visibility 0

TES_Pixel_L2.Copy TP_L2_00291
TP_L2_00291.Position 8.525 -10.075 0
TP_L2_00291.Mother TES_L2
TP_L2_00291.Visibility 0

TES_Pixel_L2.Copy TP_L2_00292
TP_L2_00292.Position 8.525 -8.525 0
TP_L2_00292.Mother TES_L2
TP_L2_00292.Visibility 0

TES_Pixel_L2.Copy TP_L2_00293
TP_L2_00293.Position 8.525 -6.975 0
TP_L2_00293.Mother TES_L2
TP_L2_00293.Visibility 0

TES_Pixel_L2.Copy TP_L2_00294
TP_L2_00294.Position 8.525 -5.425 0
TP_L2_00294.Mother TES_L2
TP_L2_00294.Visibility 0

TES_Pixel_L2.Copy TP_L2_00295
TP_L2_00295.Position 8.525 -3.875 0
TP_L2_00295.Mother TES_L2
TP_L2_00295.Visibility 0

TES_Pixel_L2.Copy TP_L2_00296
TP_L2_00296.Position 8.525 -2.325 0
TP_L2_00296.Mother TES_L2
TP_L2_00296.Visibility 0

TES_Pixel_L2.Copy TP_L2_00297
TP_L2_00297.Position 8.525 -0.775 0
TP_L2_00297.Mother TES_L2
TP_L2_00297.Visibility 0

TES_Pixel_L2.Copy TP_L2_00298
TP_L2_00298.Position 8.525 0.775 0
TP_L2_00298.Mother TES_L2
TP_L2_00298.Visibility 0

TES_Pixel_L2.Copy TP_L2_00299
TP_L2_00299.Position 8.525 2.325 0
TP_L2_00299.Mother TES_L2
TP_L2_00299.Visibility 0

TES_Pixel_L2.Copy TP_L2_00300
TP_L2_00300.Position 8.525 3.875 0
TP_L2_00300.Mother TES_L2
TP_L2_00300.Visibility 0

TES_Pixel_L2.Copy TP_L2_00301
TP_L2_00301.Position 8.525 5.425 0
TP_L2_00301.Mother TES_L2
TP_L2_00301.Visibility 0

TES_Pixel_L2.Copy TP_L2_00302
TP_L2_00302.Position 8.525 6.975 0
TP_L2_00302.Mother TES_L2
TP_L2_00302.Visibility 0

TES_Pixel_L2.Copy TP_L2_00303
TP_L2_00303.Position 8.525 8.525 0
TP_L2_00303.Mother TES_L2
TP_L2_00303.Visibility 0

TES_Pixel_L2.Copy TP_L2_00304
TP_L2_00304.Position 8.525 10.075 0
TP_L2_00304.Mother TES_L2
TP_L2_00304.Visibility 0

TES_Pixel_L2.Copy TP_L2_00305
TP_L2_00305.Position 8.525 11.625 0
TP_L2_00305.Mother TES_L2
TP_L2_00305.Visibility 0

TES_Pixel_L2.Copy TP_L2_00306
TP_L2_00306.Position 8.525 13.175 0
TP_L2_00306.Mother TES_L2
TP_L2_00306.Visibility 0

TES_Pixel_L2.Copy TP_L2_00307
TP_L2_00307.Position 8.525 14.725 0
TP_L2_00307.Mother TES_L2
TP_L2_00307.Visibility 0

TES_Pixel_L2.Copy TP_L2_00308
TP_L2_00308.Position 10.075 -14.725 0
TP_L2_00308.Mother TES_L2
TP_L2_00308.Visibility 0

TES_Pixel_L2.Copy TP_L2_00309
TP_L2_00309.Position 10.075 -13.175 0
TP_L2_00309.Mother TES_L2
TP_L2_00309.Visibility 0

TES_Pixel_L2.Copy TP_L2_00310
TP_L2_00310.Position 10.075 -11.625 0
TP_L2_00310.Mother TES_L2
TP_L2_00310.Visibility 0

TES_Pixel_L2.Copy TP_L2_00311
TP_L2_00311.Position 10.075 -10.075 0
TP_L2_00311.Mother TES_L2
TP_L2_00311.Visibility 0

TES_Pixel_L2.Copy TP_L2_00312
TP_L2_00312.Position 10.075 -8.525 0
TP_L2_00312.Mother TES_L2
TP_L2_00312.Visibility 0

TES_Pixel_L2.Copy TP_L2_00313
TP_L2_00313.Position 10.075 -6.975 0
TP_L2_00313.Mother TES_L2
TP_L2_00313.Visibility 0

TES_Pixel_L2.Copy TP_L2_00314
TP_L2_00314.Position 10.075 -5.425 0
TP_L2_00314.Mother TES_L2
TP_L2_00314.Visibility 0

TES_Pixel_L2.Copy TP_L2_00315
TP_L2_00315.Position 10.075 -3.875 0
TP_L2_00315.Mother TES_L2
TP_L2_00315.Visibility 0

TES_Pixel_L2.Copy TP_L2_00316
TP_L2_00316.Position 10.075 -2.325 0
TP_L2_00316.Mother TES_L2
TP_L2_00316.Visibility 0

TES_Pixel_L2.Copy TP_L2_00317
TP_L2_00317.Position 10.075 -0.775 0
TP_L2_00317.Mother TES_L2
TP_L2_00317.Visibility 0

TES_Pixel_L2.Copy TP_L2_00318
TP_L2_00318.Position 10.075 0.775 0
TP_L2_00318.Mother TES_L2
TP_L2_00318.Visibility 0

TES_Pixel_L2.Copy TP_L2_00319
TP_L2_00319.Position 10.075 2.325 0
TP_L2_00319.Mother TES_L2
TP_L2_00319.Visibility 0

TES_Pixel_L2.Copy TP_L2_00320
TP_L2_00320.Position 10.075 3.875 0
TP_L2_00320.Mother TES_L2
TP_L2_00320.Visibility 0

TES_Pixel_L2.Copy TP_L2_00321
TP_L2_00321.Position 10.075 5.425 0
TP_L2_00321.Mother TES_L2
TP_L2_00321.Visibility 0

TES_Pixel_L2.Copy TP_L2_00322
TP_L2_00322.Position 10.075 6.975 0
TP_L2_00322.Mother TES_L2
TP_L2_00322.Visibility 0

TES_Pixel_L2.Copy TP_L2_00323
TP_L2_00323.Position 10.075 8.525 0
TP_L2_00323.Mother TES_L2
TP_L2_00323.Visibility 0

TES_Pixel_L2.Copy TP_L2_00324
TP_L2_00324.Position 10.075 10.075 0
TP_L2_00324.Mother TES_L2
TP_L2_00324.Visibility 0

TES_Pixel_L2.Copy TP_L2_00325
TP_L2_00325.Position 10.075 11.625 0
TP_L2_00325.Mother TES_L2
TP_L2_00325.Visibility 0

TES_Pixel_L2.Copy TP_L2_00326
TP_L2_00326.Position 10.075 13.175 0
TP_L2_00326.Mother TES_L2
TP_L2_00326.Visibility 0

TES_Pixel_L2.Copy TP_L2_00327
TP_L2_00327.Position 10.075 14.725 0
TP_L2_00327.Mother TES_L2
TP_L2_00327.Visibility 0

TES_Pixel_L2.Copy TP_L2_00328
TP_L2_00328.Position 11.625 -13.175 0
TP_L2_00328.Mother TES_L2
TP_L2_00328.Visibility 0

TES_Pixel_L2.Copy TP_L2_00329
TP_L2_00329.Position 11.625 -11.625 0
TP_L2_00329.Mother TES_L2
TP_L2_00329.Visibility 0

TES_Pixel_L2.Copy TP_L2_00330
TP_L2_00330.Position 11.625 -10.075 0
TP_L2_00330.Mother TES_L2
TP_L2_00330.Visibility 0

TES_Pixel_L2.Copy TP_L2_00331
TP_L2_00331.Position 11.625 -8.525 0
TP_L2_00331.Mother TES_L2
TP_L2_00331.Visibility 0

TES_Pixel_L2.Copy TP_L2_00332
TP_L2_00332.Position 11.625 -6.975 0
TP_L2_00332.Mother TES_L2
TP_L2_00332.Visibility 0

TES_Pixel_L2.Copy TP_L2_00333
TP_L2_00333.Position 11.625 -5.425 0
TP_L2_00333.Mother TES_L2
TP_L2_00333.Visibility 0

TES_Pixel_L2.Copy TP_L2_00334
TP_L2_00334.Position 11.625 -3.875 0
TP_L2_00334.Mother TES_L2
TP_L2_00334.Visibility 0

TES_Pixel_L2.Copy TP_L2_00335
TP_L2_00335.Position 11.625 -2.325 0
TP_L2_00335.Mother TES_L2
TP_L2_00335.Visibility 0

TES_Pixel_L2.Copy TP_L2_00336
TP_L2_00336.Position 11.625 -0.775 0
TP_L2_00336.Mother TES_L2
TP_L2_00336.Visibility 0

TES_Pixel_L2.Copy TP_L2_00337
TP_L2_00337.Position 11.625 0.775 0
TP_L2_00337.Mother TES_L2
TP_L2_00337.Visibility 0

TES_Pixel_L2.Copy TP_L2_00338
TP_L2_00338.Position 11.625 2.325 0
TP_L2_00338.Mother TES_L2
TP_L2_00338.Visibility 0

TES_Pixel_L2.Copy TP_L2_00339
TP_L2_00339.Position 11.625 3.875 0
TP_L2_00339.Mother TES_L2
TP_L2_00339.Visibility 0

TES_Pixel_L2.Copy TP_L2_00340
TP_L2_00340.Position 11.625 5.425 0
TP_L2_00340.Mother TES_L2
TP_L2_00340.Visibility 0

TES_Pixel_L2.Copy TP_L2_00341
TP_L2_00341.Position 11.625 6.975 0
TP_L2_00341.Mother TES_L2
TP_L2_00341.Visibility 0

TES_Pixel_L2.Copy TP_L2_00342
TP_L2_00342.Position 11.625 8.525 0
TP_L2_00342.Mother TES_L2
TP_L2_00342.Visibility 0

TES_Pixel_L2.Copy TP_L2_00343
TP_L2_00343.Position 11.625 10.075 0
TP_L2_00343.Mother TES_L2
TP_L2_00343.Visibility 0

TES_Pixel_L2.Copy TP_L2_00344
TP_L2_00344.Position 11.625 11.625 0
TP_L2_00344.Mother TES_L2
TP_L2_00344.Visibility 0

TES_Pixel_L2.Copy TP_L2_00345
TP_L2_00345.Position 11.625 13.175 0
TP_L2_00345.Mother TES_L2
TP_L2_00345.Visibility 0

TES_Pixel_L2.Copy TP_L2_00346
TP_L2_00346.Position 13.175 -11.625 0
TP_L2_00346.Mother TES_L2
TP_L2_00346.Visibility 0

TES_Pixel_L2.Copy TP_L2_00347
TP_L2_00347.Position 13.175 -10.075 0
TP_L2_00347.Mother TES_L2
TP_L2_00347.Visibility 0

TES_Pixel_L2.Copy TP_L2_00348
TP_L2_00348.Position 13.175 -8.525 0
TP_L2_00348.Mother TES_L2
TP_L2_00348.Visibility 0

TES_Pixel_L2.Copy TP_L2_00349
TP_L2_00349.Position 13.175 -6.975 0
TP_L2_00349.Mother TES_L2
TP_L2_00349.Visibility 0

TES_Pixel_L2.Copy TP_L2_00350
TP_L2_00350.Position 13.175 -5.425 0
TP_L2_00350.Mother TES_L2
TP_L2_00350.Visibility 0

TES_Pixel_L2.Copy TP_L2_00351
TP_L2_00351.Position 13.175 -3.875 0
TP_L2_00351.Mother TES_L2
TP_L2_00351.Visibility 0

TES_Pixel_L2.Copy TP_L2_00352
TP_L2_00352.Position 13.175 -2.325 0
TP_L2_00352.Mother TES_L2
TP_L2_00352.Visibility 0

TES_Pixel_L2.Copy TP_L2_00353
TP_L2_00353.Position 13.175 -0.775 0
TP_L2_00353.Mother TES_L2
TP_L2_00353.Visibility 0

TES_Pixel_L2.Copy TP_L2_00354
TP_L2_00354.Position 13.175 0.775 0
TP_L2_00354.Mother TES_L2
TP_L2_00354.Visibility 0

TES_Pixel_L2.Copy TP_L2_00355
TP_L2_00355.Position 13.175 2.325 0
TP_L2_00355.Mother TES_L2
TP_L2_00355.Visibility 0

TES_Pixel_L2.Copy TP_L2_00356
TP_L2_00356.Position 13.175 3.875 0
TP_L2_00356.Mother TES_L2
TP_L2_00356.Visibility 0

TES_Pixel_L2.Copy TP_L2_00357
TP_L2_00357.Position 13.175 5.425 0
TP_L2_00357.Mother TES_L2
TP_L2_00357.Visibility 0

TES_Pixel_L2.Copy TP_L2_00358
TP_L2_00358.Position 13.175 6.975 0
TP_L2_00358.Mother TES_L2
TP_L2_00358.Visibility 0

TES_Pixel_L2.Copy TP_L2_00359
TP_L2_00359.Position 13.175 8.525 0
TP_L2_00359.Mother TES_L2
TP_L2_00359.Visibility 0

TES_Pixel_L2.Copy TP_L2_00360
TP_L2_00360.Position 13.175 10.075 0
TP_L2_00360.Mother TES_L2
TP_L2_00360.Visibility 0

TES_Pixel_L2.Copy TP_L2_00361
TP_L2_00361.Position 13.175 11.625 0
TP_L2_00361.Mother TES_L2
TP_L2_00361.Visibility 0

TES_Pixel_L2.Copy TP_L2_00362
TP_L2_00362.Position 14.725 -10.075 0
TP_L2_00362.Mother TES_L2
TP_L2_00362.Visibility 0

TES_Pixel_L2.Copy TP_L2_00363
TP_L2_00363.Position 14.725 -8.525 0
TP_L2_00363.Mother TES_L2
TP_L2_00363.Visibility 0

TES_Pixel_L2.Copy TP_L2_00364
TP_L2_00364.Position 14.725 -6.975 0
TP_L2_00364.Mother TES_L2
TP_L2_00364.Visibility 0

TES_Pixel_L2.Copy TP_L2_00365
TP_L2_00365.Position 14.725 -5.425 0
TP_L2_00365.Mother TES_L2
TP_L2_00365.Visibility 0

TES_Pixel_L2.Copy TP_L2_00366
TP_L2_00366.Position 14.725 -3.875 0
TP_L2_00366.Mother TES_L2
TP_L2_00366.Visibility 0

TES_Pixel_L2.Copy TP_L2_00367
TP_L2_00367.Position 14.725 -2.325 0
TP_L2_00367.Mother TES_L2
TP_L2_00367.Visibility 0

TES_Pixel_L2.Copy TP_L2_00368
TP_L2_00368.Position 14.725 -0.775 0
TP_L2_00368.Mother TES_L2
TP_L2_00368.Visibility 0

TES_Pixel_L2.Copy TP_L2_00369
TP_L2_00369.Position 14.725 0.775 0
TP_L2_00369.Mother TES_L2
TP_L2_00369.Visibility 0

TES_Pixel_L2.Copy TP_L2_00370
TP_L2_00370.Position 14.725 2.325 0
TP_L2_00370.Mother TES_L2
TP_L2_00370.Visibility 0

TES_Pixel_L2.Copy TP_L2_00371
TP_L2_00371.Position 14.725 3.875 0
TP_L2_00371.Mother TES_L2
TP_L2_00371.Visibility 0

TES_Pixel_L2.Copy TP_L2_00372
TP_L2_00372.Position 14.725 5.425 0
TP_L2_00372.Mother TES_L2
TP_L2_00372.Visibility 0

TES_Pixel_L2.Copy TP_L2_00373
TP_L2_00373.Position 14.725 6.975 0
TP_L2_00373.Mother TES_L2
TP_L2_00373.Visibility 0

TES_Pixel_L2.Copy TP_L2_00374
TP_L2_00374.Position 14.725 8.525 0
TP_L2_00374.Mother TES_L2
TP_L2_00374.Visibility 0

TES_Pixel_L2.Copy TP_L2_00375
TP_L2_00375.Position 14.725 10.075 0
TP_L2_00375.Mother TES_L2
TP_L2_00375.Visibility 0

Substrate_L3.Position 0 0 46
Substrate_L3.Mother WorldVolume

TES_L3.Position 0 0 47.65
TES_L3.Mother WorldVolume
TES_L3.Visibility 0

TES_Pixel_L3.Copy TP_L3_00000
TP_L3_00000.Position -14.725 -10.075 0
TP_L3_00000.Mother TES_L3
TP_L3_00000.Visibility 0

TES_Pixel_L3.Copy TP_L3_00001
TP_L3_00001.Position -14.725 -8.525 0
TP_L3_00001.Mother TES_L3
TP_L3_00001.Visibility 0

TES_Pixel_L3.Copy TP_L3_00002
TP_L3_00002.Position -14.725 -6.975 0
TP_L3_00002.Mother TES_L3
TP_L3_00002.Visibility 0

TES_Pixel_L3.Copy TP_L3_00003
TP_L3_00003.Position -14.725 -5.425 0
TP_L3_00003.Mother TES_L3
TP_L3_00003.Visibility 0

TES_Pixel_L3.Copy TP_L3_00004
TP_L3_00004.Position -14.725 -3.875 0
TP_L3_00004.Mother TES_L3
TP_L3_00004.Visibility 0

TES_Pixel_L3.Copy TP_L3_00005
TP_L3_00005.Position -14.725 -2.325 0
TP_L3_00005.Mother TES_L3
TP_L3_00005.Visibility 0

TES_Pixel_L3.Copy TP_L3_00006
TP_L3_00006.Position -14.725 -0.775 0
TP_L3_00006.Mother TES_L3
TP_L3_00006.Visibility 0

TES_Pixel_L3.Copy TP_L3_00007
TP_L3_00007.Position -14.725 0.775 0
TP_L3_00007.Mother TES_L3
TP_L3_00007.Visibility 0

TES_Pixel_L3.Copy TP_L3_00008
TP_L3_00008.Position -14.725 2.325 0
TP_L3_00008.Mother TES_L3
TP_L3_00008.Visibility 0

TES_Pixel_L3.Copy TP_L3_00009
TP_L3_00009.Position -14.725 3.875 0
TP_L3_00009.Mother TES_L3
TP_L3_00009.Visibility 0

TES_Pixel_L3.Copy TP_L3_00010
TP_L3_00010.Position -14.725 5.425 0
TP_L3_00010.Mother TES_L3
TP_L3_00010.Visibility 0

TES_Pixel_L3.Copy TP_L3_00011
TP_L3_00011.Position -14.725 6.975 0
TP_L3_00011.Mother TES_L3
TP_L3_00011.Visibility 0

TES_Pixel_L3.Copy TP_L3_00012
TP_L3_00012.Position -14.725 8.525 0
TP_L3_00012.Mother TES_L3
TP_L3_00012.Visibility 0

TES_Pixel_L3.Copy TP_L3_00013
TP_L3_00013.Position -14.725 10.075 0
TP_L3_00013.Mother TES_L3
TP_L3_00013.Visibility 0

TES_Pixel_L3.Copy TP_L3_00014
TP_L3_00014.Position -13.175 -11.625 0
TP_L3_00014.Mother TES_L3
TP_L3_00014.Visibility 0

TES_Pixel_L3.Copy TP_L3_00015
TP_L3_00015.Position -13.175 -10.075 0
TP_L3_00015.Mother TES_L3
TP_L3_00015.Visibility 0

TES_Pixel_L3.Copy TP_L3_00016
TP_L3_00016.Position -13.175 -8.525 0
TP_L3_00016.Mother TES_L3
TP_L3_00016.Visibility 0

TES_Pixel_L3.Copy TP_L3_00017
TP_L3_00017.Position -13.175 -6.975 0
TP_L3_00017.Mother TES_L3
TP_L3_00017.Visibility 0

TES_Pixel_L3.Copy TP_L3_00018
TP_L3_00018.Position -13.175 -5.425 0
TP_L3_00018.Mother TES_L3
TP_L3_00018.Visibility 0

TES_Pixel_L3.Copy TP_L3_00019
TP_L3_00019.Position -13.175 -3.875 0
TP_L3_00019.Mother TES_L3
TP_L3_00019.Visibility 0

TES_Pixel_L3.Copy TP_L3_00020
TP_L3_00020.Position -13.175 -2.325 0
TP_L3_00020.Mother TES_L3
TP_L3_00020.Visibility 0

TES_Pixel_L3.Copy TP_L3_00021
TP_L3_00021.Position -13.175 -0.775 0
TP_L3_00021.Mother TES_L3
TP_L3_00021.Visibility 0

TES_Pixel_L3.Copy TP_L3_00022
TP_L3_00022.Position -13.175 0.775 0
TP_L3_00022.Mother TES_L3
TP_L3_00022.Visibility 0

TES_Pixel_L3.Copy TP_L3_00023
TP_L3_00023.Position -13.175 2.325 0
TP_L3_00023.Mother TES_L3
TP_L3_00023.Visibility 0

TES_Pixel_L3.Copy TP_L3_00024
TP_L3_00024.Position -13.175 3.875 0
TP_L3_00024.Mother TES_L3
TP_L3_00024.Visibility 0

TES_Pixel_L3.Copy TP_L3_00025
TP_L3_00025.Position -13.175 5.425 0
TP_L3_00025.Mother TES_L3
TP_L3_00025.Visibility 0

TES_Pixel_L3.Copy TP_L3_00026
TP_L3_00026.Position -13.175 6.975 0
TP_L3_00026.Mother TES_L3
TP_L3_00026.Visibility 0

TES_Pixel_L3.Copy TP_L3_00027
TP_L3_00027.Position -13.175 8.525 0
TP_L3_00027.Mother TES_L3
TP_L3_00027.Visibility 0

TES_Pixel_L3.Copy TP_L3_00028
TP_L3_00028.Position -13.175 10.075 0
TP_L3_00028.Mother TES_L3
TP_L3_00028.Visibility 0

TES_Pixel_L3.Copy TP_L3_00029
TP_L3_00029.Position -13.175 11.625 0
TP_L3_00029.Mother TES_L3
TP_L3_00029.Visibility 0

TES_Pixel_L3.Copy TP_L3_00030
TP_L3_00030.Position -11.625 -13.175 0
TP_L3_00030.Mother TES_L3
TP_L3_00030.Visibility 0

TES_Pixel_L3.Copy TP_L3_00031
TP_L3_00031.Position -11.625 -11.625 0
TP_L3_00031.Mother TES_L3
TP_L3_00031.Visibility 0

TES_Pixel_L3.Copy TP_L3_00032
TP_L3_00032.Position -11.625 -10.075 0
TP_L3_00032.Mother TES_L3
TP_L3_00032.Visibility 0

TES_Pixel_L3.Copy TP_L3_00033
TP_L3_00033.Position -11.625 -8.525 0
TP_L3_00033.Mother TES_L3
TP_L3_00033.Visibility 0

TES_Pixel_L3.Copy TP_L3_00034
TP_L3_00034.Position -11.625 -6.975 0
TP_L3_00034.Mother TES_L3
TP_L3_00034.Visibility 0

TES_Pixel_L3.Copy TP_L3_00035
TP_L3_00035.Position -11.625 -5.425 0
TP_L3_00035.Mother TES_L3
TP_L3_00035.Visibility 0

TES_Pixel_L3.Copy TP_L3_00036
TP_L3_00036.Position -11.625 -3.875 0
TP_L3_00036.Mother TES_L3
TP_L3_00036.Visibility 0

TES_Pixel_L3.Copy TP_L3_00037
TP_L3_00037.Position -11.625 -2.325 0
TP_L3_00037.Mother TES_L3
TP_L3_00037.Visibility 0

TES_Pixel_L3.Copy TP_L3_00038
TP_L3_00038.Position -11.625 -0.775 0
TP_L3_00038.Mother TES_L3
TP_L3_00038.Visibility 0

TES_Pixel_L3.Copy TP_L3_00039
TP_L3_00039.Position -11.625 0.775 0
TP_L3_00039.Mother TES_L3
TP_L3_00039.Visibility 0

TES_Pixel_L3.Copy TP_L3_00040
TP_L3_00040.Position -11.625 2.325 0
TP_L3_00040.Mother TES_L3
TP_L3_00040.Visibility 0

TES_Pixel_L3.Copy TP_L3_00041
TP_L3_00041.Position -11.625 3.875 0
TP_L3_00041.Mother TES_L3
TP_L3_00041.Visibility 0

TES_Pixel_L3.Copy TP_L3_00042
TP_L3_00042.Position -11.625 5.425 0
TP_L3_00042.Mother TES_L3
TP_L3_00042.Visibility 0

TES_Pixel_L3.Copy TP_L3_00043
TP_L3_00043.Position -11.625 6.975 0
TP_L3_00043.Mother TES_L3
TP_L3_00043.Visibility 0

TES_Pixel_L3.Copy TP_L3_00044
TP_L3_00044.Position -11.625 8.525 0
TP_L3_00044.Mother TES_L3
TP_L3_00044.Visibility 0

TES_Pixel_L3.Copy TP_L3_00045
TP_L3_00045.Position -11.625 10.075 0
TP_L3_00045.Mother TES_L3
TP_L3_00045.Visibility 0

TES_Pixel_L3.Copy TP_L3_00046
TP_L3_00046.Position -11.625 11.625 0
TP_L3_00046.Mother TES_L3
TP_L3_00046.Visibility 0

TES_Pixel_L3.Copy TP_L3_00047
TP_L3_00047.Position -11.625 13.175 0
TP_L3_00047.Mother TES_L3
TP_L3_00047.Visibility 0

TES_Pixel_L3.Copy TP_L3_00048
TP_L3_00048.Position -10.075 -14.725 0
TP_L3_00048.Mother TES_L3
TP_L3_00048.Visibility 0

TES_Pixel_L3.Copy TP_L3_00049
TP_L3_00049.Position -10.075 -13.175 0
TP_L3_00049.Mother TES_L3
TP_L3_00049.Visibility 0

TES_Pixel_L3.Copy TP_L3_00050
TP_L3_00050.Position -10.075 -11.625 0
TP_L3_00050.Mother TES_L3
TP_L3_00050.Visibility 0

TES_Pixel_L3.Copy TP_L3_00051
TP_L3_00051.Position -10.075 -10.075 0
TP_L3_00051.Mother TES_L3
TP_L3_00051.Visibility 0

TES_Pixel_L3.Copy TP_L3_00052
TP_L3_00052.Position -10.075 -8.525 0
TP_L3_00052.Mother TES_L3
TP_L3_00052.Visibility 0

TES_Pixel_L3.Copy TP_L3_00053
TP_L3_00053.Position -10.075 -6.975 0
TP_L3_00053.Mother TES_L3
TP_L3_00053.Visibility 0

TES_Pixel_L3.Copy TP_L3_00054
TP_L3_00054.Position -10.075 -5.425 0
TP_L3_00054.Mother TES_L3
TP_L3_00054.Visibility 0

TES_Pixel_L3.Copy TP_L3_00055
TP_L3_00055.Position -10.075 -3.875 0
TP_L3_00055.Mother TES_L3
TP_L3_00055.Visibility 0

TES_Pixel_L3.Copy TP_L3_00056
TP_L3_00056.Position -10.075 -2.325 0
TP_L3_00056.Mother TES_L3
TP_L3_00056.Visibility 0

TES_Pixel_L3.Copy TP_L3_00057
TP_L3_00057.Position -10.075 -0.775 0
TP_L3_00057.Mother TES_L3
TP_L3_00057.Visibility 0

TES_Pixel_L3.Copy TP_L3_00058
TP_L3_00058.Position -10.075 0.775 0
TP_L3_00058.Mother TES_L3
TP_L3_00058.Visibility 0

TES_Pixel_L3.Copy TP_L3_00059
TP_L3_00059.Position -10.075 2.325 0
TP_L3_00059.Mother TES_L3
TP_L3_00059.Visibility 0

TES_Pixel_L3.Copy TP_L3_00060
TP_L3_00060.Position -10.075 3.875 0
TP_L3_00060.Mother TES_L3
TP_L3_00060.Visibility 0

TES_Pixel_L3.Copy TP_L3_00061
TP_L3_00061.Position -10.075 5.425 0
TP_L3_00061.Mother TES_L3
TP_L3_00061.Visibility 0

TES_Pixel_L3.Copy TP_L3_00062
TP_L3_00062.Position -10.075 6.975 0
TP_L3_00062.Mother TES_L3
TP_L3_00062.Visibility 0

TES_Pixel_L3.Copy TP_L3_00063
TP_L3_00063.Position -10.075 8.525 0
TP_L3_00063.Mother TES_L3
TP_L3_00063.Visibility 0

TES_Pixel_L3.Copy TP_L3_00064
TP_L3_00064.Position -10.075 10.075 0
TP_L3_00064.Mother TES_L3
TP_L3_00064.Visibility 0

TES_Pixel_L3.Copy TP_L3_00065
TP_L3_00065.Position -10.075 11.625 0
TP_L3_00065.Mother TES_L3
TP_L3_00065.Visibility 0

TES_Pixel_L3.Copy TP_L3_00066
TP_L3_00066.Position -10.075 13.175 0
TP_L3_00066.Mother TES_L3
TP_L3_00066.Visibility 0

TES_Pixel_L3.Copy TP_L3_00067
TP_L3_00067.Position -10.075 14.725 0
TP_L3_00067.Mother TES_L3
TP_L3_00067.Visibility 0

TES_Pixel_L3.Copy TP_L3_00068
TP_L3_00068.Position -8.525 -14.725 0
TP_L3_00068.Mother TES_L3
TP_L3_00068.Visibility 0

TES_Pixel_L3.Copy TP_L3_00069
TP_L3_00069.Position -8.525 -13.175 0
TP_L3_00069.Mother TES_L3
TP_L3_00069.Visibility 0

TES_Pixel_L3.Copy TP_L3_00070
TP_L3_00070.Position -8.525 -11.625 0
TP_L3_00070.Mother TES_L3
TP_L3_00070.Visibility 0

TES_Pixel_L3.Copy TP_L3_00071
TP_L3_00071.Position -8.525 -10.075 0
TP_L3_00071.Mother TES_L3
TP_L3_00071.Visibility 0

TES_Pixel_L3.Copy TP_L3_00072
TP_L3_00072.Position -8.525 -8.525 0
TP_L3_00072.Mother TES_L3
TP_L3_00072.Visibility 0

TES_Pixel_L3.Copy TP_L3_00073
TP_L3_00073.Position -8.525 -6.975 0
TP_L3_00073.Mother TES_L3
TP_L3_00073.Visibility 0

TES_Pixel_L3.Copy TP_L3_00074
TP_L3_00074.Position -8.525 -5.425 0
TP_L3_00074.Mother TES_L3
TP_L3_00074.Visibility 0

TES_Pixel_L3.Copy TP_L3_00075
TP_L3_00075.Position -8.525 -3.875 0
TP_L3_00075.Mother TES_L3
TP_L3_00075.Visibility 0

TES_Pixel_L3.Copy TP_L3_00076
TP_L3_00076.Position -8.525 -2.325 0
TP_L3_00076.Mother TES_L3
TP_L3_00076.Visibility 0

TES_Pixel_L3.Copy TP_L3_00077
TP_L3_00077.Position -8.525 -0.775 0
TP_L3_00077.Mother TES_L3
TP_L3_00077.Visibility 0

TES_Pixel_L3.Copy TP_L3_00078
TP_L3_00078.Position -8.525 0.775 0
TP_L3_00078.Mother TES_L3
TP_L3_00078.Visibility 0

TES_Pixel_L3.Copy TP_L3_00079
TP_L3_00079.Position -8.525 2.325 0
TP_L3_00079.Mother TES_L3
TP_L3_00079.Visibility 0

TES_Pixel_L3.Copy TP_L3_00080
TP_L3_00080.Position -8.525 3.875 0
TP_L3_00080.Mother TES_L3
TP_L3_00080.Visibility 0

TES_Pixel_L3.Copy TP_L3_00081
TP_L3_00081.Position -8.525 5.425 0
TP_L3_00081.Mother TES_L3
TP_L3_00081.Visibility 0

TES_Pixel_L3.Copy TP_L3_00082
TP_L3_00082.Position -8.525 6.975 0
TP_L3_00082.Mother TES_L3
TP_L3_00082.Visibility 0

TES_Pixel_L3.Copy TP_L3_00083
TP_L3_00083.Position -8.525 8.525 0
TP_L3_00083.Mother TES_L3
TP_L3_00083.Visibility 0

TES_Pixel_L3.Copy TP_L3_00084
TP_L3_00084.Position -8.525 10.075 0
TP_L3_00084.Mother TES_L3
TP_L3_00084.Visibility 0

TES_Pixel_L3.Copy TP_L3_00085
TP_L3_00085.Position -8.525 11.625 0
TP_L3_00085.Mother TES_L3
TP_L3_00085.Visibility 0

TES_Pixel_L3.Copy TP_L3_00086
TP_L3_00086.Position -8.525 13.175 0
TP_L3_00086.Mother TES_L3
TP_L3_00086.Visibility 0

TES_Pixel_L3.Copy TP_L3_00087
TP_L3_00087.Position -8.525 14.725 0
TP_L3_00087.Mother TES_L3
TP_L3_00087.Visibility 0

TES_Pixel_L3.Copy TP_L3_00088
TP_L3_00088.Position -6.975 -14.725 0
TP_L3_00088.Mother TES_L3
TP_L3_00088.Visibility 0

TES_Pixel_L3.Copy TP_L3_00089
TP_L3_00089.Position -6.975 -13.175 0
TP_L3_00089.Mother TES_L3
TP_L3_00089.Visibility 0

TES_Pixel_L3.Copy TP_L3_00090
TP_L3_00090.Position -6.975 -11.625 0
TP_L3_00090.Mother TES_L3
TP_L3_00090.Visibility 0

TES_Pixel_L3.Copy TP_L3_00091
TP_L3_00091.Position -6.975 -10.075 0
TP_L3_00091.Mother TES_L3
TP_L3_00091.Visibility 0

TES_Pixel_L3.Copy TP_L3_00092
TP_L3_00092.Position -6.975 -8.525 0
TP_L3_00092.Mother TES_L3
TP_L3_00092.Visibility 0

TES_Pixel_L3.Copy TP_L3_00093
TP_L3_00093.Position -6.975 -6.975 0
TP_L3_00093.Mother TES_L3
TP_L3_00093.Visibility 0

TES_Pixel_L3.Copy TP_L3_00094
TP_L3_00094.Position -6.975 -5.425 0
TP_L3_00094.Mother TES_L3
TP_L3_00094.Visibility 0

TES_Pixel_L3.Copy TP_L3_00095
TP_L3_00095.Position -6.975 -3.875 0
TP_L3_00095.Mother TES_L3
TP_L3_00095.Visibility 0

TES_Pixel_L3.Copy TP_L3_00096
TP_L3_00096.Position -6.975 -2.325 0
TP_L3_00096.Mother TES_L3
TP_L3_00096.Visibility 0

TES_Pixel_L3.Copy TP_L3_00097
TP_L3_00097.Position -6.975 -0.775 0
TP_L3_00097.Mother TES_L3
TP_L3_00097.Visibility 0

TES_Pixel_L3.Copy TP_L3_00098
TP_L3_00098.Position -6.975 0.775 0
TP_L3_00098.Mother TES_L3
TP_L3_00098.Visibility 0

TES_Pixel_L3.Copy TP_L3_00099
TP_L3_00099.Position -6.975 2.325 0
TP_L3_00099.Mother TES_L3
TP_L3_00099.Visibility 0

TES_Pixel_L3.Copy TP_L3_00100
TP_L3_00100.Position -6.975 3.875 0
TP_L3_00100.Mother TES_L3
TP_L3_00100.Visibility 0

TES_Pixel_L3.Copy TP_L3_00101
TP_L3_00101.Position -6.975 5.425 0
TP_L3_00101.Mother TES_L3
TP_L3_00101.Visibility 0

TES_Pixel_L3.Copy TP_L3_00102
TP_L3_00102.Position -6.975 6.975 0
TP_L3_00102.Mother TES_L3
TP_L3_00102.Visibility 0

TES_Pixel_L3.Copy TP_L3_00103
TP_L3_00103.Position -6.975 8.525 0
TP_L3_00103.Mother TES_L3
TP_L3_00103.Visibility 0

TES_Pixel_L3.Copy TP_L3_00104
TP_L3_00104.Position -6.975 10.075 0
TP_L3_00104.Mother TES_L3
TP_L3_00104.Visibility 0

TES_Pixel_L3.Copy TP_L3_00105
TP_L3_00105.Position -6.975 11.625 0
TP_L3_00105.Mother TES_L3
TP_L3_00105.Visibility 0

TES_Pixel_L3.Copy TP_L3_00106
TP_L3_00106.Position -6.975 13.175 0
TP_L3_00106.Mother TES_L3
TP_L3_00106.Visibility 0

TES_Pixel_L3.Copy TP_L3_00107
TP_L3_00107.Position -6.975 14.725 0
TP_L3_00107.Mother TES_L3
TP_L3_00107.Visibility 0

TES_Pixel_L3.Copy TP_L3_00108
TP_L3_00108.Position -5.425 -14.725 0
TP_L3_00108.Mother TES_L3
TP_L3_00108.Visibility 0

TES_Pixel_L3.Copy TP_L3_00109
TP_L3_00109.Position -5.425 -13.175 0
TP_L3_00109.Mother TES_L3
TP_L3_00109.Visibility 0

TES_Pixel_L3.Copy TP_L3_00110
TP_L3_00110.Position -5.425 -11.625 0
TP_L3_00110.Mother TES_L3
TP_L3_00110.Visibility 0

TES_Pixel_L3.Copy TP_L3_00111
TP_L3_00111.Position -5.425 -10.075 0
TP_L3_00111.Mother TES_L3
TP_L3_00111.Visibility 0

TES_Pixel_L3.Copy TP_L3_00112
TP_L3_00112.Position -5.425 -8.525 0
TP_L3_00112.Mother TES_L3
TP_L3_00112.Visibility 0

TES_Pixel_L3.Copy TP_L3_00113
TP_L3_00113.Position -5.425 -6.975 0
TP_L3_00113.Mother TES_L3
TP_L3_00113.Visibility 0

TES_Pixel_L3.Copy TP_L3_00114
TP_L3_00114.Position -5.425 -5.425 0
TP_L3_00114.Mother TES_L3
TP_L3_00114.Visibility 0

TES_Pixel_L3.Copy TP_L3_00115
TP_L3_00115.Position -5.425 -3.875 0
TP_L3_00115.Mother TES_L3
TP_L3_00115.Visibility 0

TES_Pixel_L3.Copy TP_L3_00116
TP_L3_00116.Position -5.425 -2.325 0
TP_L3_00116.Mother TES_L3
TP_L3_00116.Visibility 0

TES_Pixel_L3.Copy TP_L3_00117
TP_L3_00117.Position -5.425 -0.775 0
TP_L3_00117.Mother TES_L3
TP_L3_00117.Visibility 0

TES_Pixel_L3.Copy TP_L3_00118
TP_L3_00118.Position -5.425 0.775 0
TP_L3_00118.Mother TES_L3
TP_L3_00118.Visibility 0

TES_Pixel_L3.Copy TP_L3_00119
TP_L3_00119.Position -5.425 2.325 0
TP_L3_00119.Mother TES_L3
TP_L3_00119.Visibility 0

TES_Pixel_L3.Copy TP_L3_00120
TP_L3_00120.Position -5.425 3.875 0
TP_L3_00120.Mother TES_L3
TP_L3_00120.Visibility 0

TES_Pixel_L3.Copy TP_L3_00121
TP_L3_00121.Position -5.425 5.425 0
TP_L3_00121.Mother TES_L3
TP_L3_00121.Visibility 0

TES_Pixel_L3.Copy TP_L3_00122
TP_L3_00122.Position -5.425 6.975 0
TP_L3_00122.Mother TES_L3
TP_L3_00122.Visibility 0

TES_Pixel_L3.Copy TP_L3_00123
TP_L3_00123.Position -5.425 8.525 0
TP_L3_00123.Mother TES_L3
TP_L3_00123.Visibility 0

TES_Pixel_L3.Copy TP_L3_00124
TP_L3_00124.Position -5.425 10.075 0
TP_L3_00124.Mother TES_L3
TP_L3_00124.Visibility 0

TES_Pixel_L3.Copy TP_L3_00125
TP_L3_00125.Position -5.425 11.625 0
TP_L3_00125.Mother TES_L3
TP_L3_00125.Visibility 0

TES_Pixel_L3.Copy TP_L3_00126
TP_L3_00126.Position -5.425 13.175 0
TP_L3_00126.Mother TES_L3
TP_L3_00126.Visibility 0

TES_Pixel_L3.Copy TP_L3_00127
TP_L3_00127.Position -5.425 14.725 0
TP_L3_00127.Mother TES_L3
TP_L3_00127.Visibility 0

TES_Pixel_L3.Copy TP_L3_00128
TP_L3_00128.Position -3.875 -14.725 0
TP_L3_00128.Mother TES_L3
TP_L3_00128.Visibility 0

TES_Pixel_L3.Copy TP_L3_00129
TP_L3_00129.Position -3.875 -13.175 0
TP_L3_00129.Mother TES_L3
TP_L3_00129.Visibility 0

TES_Pixel_L3.Copy TP_L3_00130
TP_L3_00130.Position -3.875 -11.625 0
TP_L3_00130.Mother TES_L3
TP_L3_00130.Visibility 0

TES_Pixel_L3.Copy TP_L3_00131
TP_L3_00131.Position -3.875 -10.075 0
TP_L3_00131.Mother TES_L3
TP_L3_00131.Visibility 0

TES_Pixel_L3.Copy TP_L3_00132
TP_L3_00132.Position -3.875 -8.525 0
TP_L3_00132.Mother TES_L3
TP_L3_00132.Visibility 0

TES_Pixel_L3.Copy TP_L3_00133
TP_L3_00133.Position -3.875 -6.975 0
TP_L3_00133.Mother TES_L3
TP_L3_00133.Visibility 0

TES_Pixel_L3.Copy TP_L3_00134
TP_L3_00134.Position -3.875 -5.425 0
TP_L3_00134.Mother TES_L3
TP_L3_00134.Visibility 0

TES_Pixel_L3.Copy TP_L3_00135
TP_L3_00135.Position -3.875 -3.875 0
TP_L3_00135.Mother TES_L3
TP_L3_00135.Visibility 0

TES_Pixel_L3.Copy TP_L3_00136
TP_L3_00136.Position -3.875 -2.325 0
TP_L3_00136.Mother TES_L3
TP_L3_00136.Visibility 0

TES_Pixel_L3.Copy TP_L3_00137
TP_L3_00137.Position -3.875 -0.775 0
TP_L3_00137.Mother TES_L3
TP_L3_00137.Visibility 0

TES_Pixel_L3.Copy TP_L3_00138
TP_L3_00138.Position -3.875 0.775 0
TP_L3_00138.Mother TES_L3
TP_L3_00138.Visibility 0

TES_Pixel_L3.Copy TP_L3_00139
TP_L3_00139.Position -3.875 2.325 0
TP_L3_00139.Mother TES_L3
TP_L3_00139.Visibility 0

TES_Pixel_L3.Copy TP_L3_00140
TP_L3_00140.Position -3.875 3.875 0
TP_L3_00140.Mother TES_L3
TP_L3_00140.Visibility 0

TES_Pixel_L3.Copy TP_L3_00141
TP_L3_00141.Position -3.875 5.425 0
TP_L3_00141.Mother TES_L3
TP_L3_00141.Visibility 0

TES_Pixel_L3.Copy TP_L3_00142
TP_L3_00142.Position -3.875 6.975 0
TP_L3_00142.Mother TES_L3
TP_L3_00142.Visibility 0

TES_Pixel_L3.Copy TP_L3_00143
TP_L3_00143.Position -3.875 8.525 0
TP_L3_00143.Mother TES_L3
TP_L3_00143.Visibility 0

TES_Pixel_L3.Copy TP_L3_00144
TP_L3_00144.Position -3.875 10.075 0
TP_L3_00144.Mother TES_L3
TP_L3_00144.Visibility 0

TES_Pixel_L3.Copy TP_L3_00145
TP_L3_00145.Position -3.875 11.625 0
TP_L3_00145.Mother TES_L3
TP_L3_00145.Visibility 0

TES_Pixel_L3.Copy TP_L3_00146
TP_L3_00146.Position -3.875 13.175 0
TP_L3_00146.Mother TES_L3
TP_L3_00146.Visibility 0

TES_Pixel_L3.Copy TP_L3_00147
TP_L3_00147.Position -3.875 14.725 0
TP_L3_00147.Mother TES_L3
TP_L3_00147.Visibility 0

TES_Pixel_L3.Copy TP_L3_00148
TP_L3_00148.Position -2.325 -14.725 0
TP_L3_00148.Mother TES_L3
TP_L3_00148.Visibility 0

TES_Pixel_L3.Copy TP_L3_00149
TP_L3_00149.Position -2.325 -13.175 0
TP_L3_00149.Mother TES_L3
TP_L3_00149.Visibility 0

TES_Pixel_L3.Copy TP_L3_00150
TP_L3_00150.Position -2.325 -11.625 0
TP_L3_00150.Mother TES_L3
TP_L3_00150.Visibility 0

TES_Pixel_L3.Copy TP_L3_00151
TP_L3_00151.Position -2.325 -10.075 0
TP_L3_00151.Mother TES_L3
TP_L3_00151.Visibility 0

TES_Pixel_L3.Copy TP_L3_00152
TP_L3_00152.Position -2.325 -8.525 0
TP_L3_00152.Mother TES_L3
TP_L3_00152.Visibility 0

TES_Pixel_L3.Copy TP_L3_00153
TP_L3_00153.Position -2.325 -6.975 0
TP_L3_00153.Mother TES_L3
TP_L3_00153.Visibility 0

TES_Pixel_L3.Copy TP_L3_00154
TP_L3_00154.Position -2.325 -5.425 0
TP_L3_00154.Mother TES_L3
TP_L3_00154.Visibility 0

TES_Pixel_L3.Copy TP_L3_00155
TP_L3_00155.Position -2.325 -3.875 0
TP_L3_00155.Mother TES_L3
TP_L3_00155.Visibility 0

TES_Pixel_L3.Copy TP_L3_00156
TP_L3_00156.Position -2.325 -2.325 0
TP_L3_00156.Mother TES_L3
TP_L3_00156.Visibility 0

TES_Pixel_L3.Copy TP_L3_00157
TP_L3_00157.Position -2.325 -0.775 0
TP_L3_00157.Mother TES_L3
TP_L3_00157.Visibility 0

TES_Pixel_L3.Copy TP_L3_00158
TP_L3_00158.Position -2.325 0.775 0
TP_L3_00158.Mother TES_L3
TP_L3_00158.Visibility 0

TES_Pixel_L3.Copy TP_L3_00159
TP_L3_00159.Position -2.325 2.325 0
TP_L3_00159.Mother TES_L3
TP_L3_00159.Visibility 0

TES_Pixel_L3.Copy TP_L3_00160
TP_L3_00160.Position -2.325 3.875 0
TP_L3_00160.Mother TES_L3
TP_L3_00160.Visibility 0

TES_Pixel_L3.Copy TP_L3_00161
TP_L3_00161.Position -2.325 5.425 0
TP_L3_00161.Mother TES_L3
TP_L3_00161.Visibility 0

TES_Pixel_L3.Copy TP_L3_00162
TP_L3_00162.Position -2.325 6.975 0
TP_L3_00162.Mother TES_L3
TP_L3_00162.Visibility 0

TES_Pixel_L3.Copy TP_L3_00163
TP_L3_00163.Position -2.325 8.525 0
TP_L3_00163.Mother TES_L3
TP_L3_00163.Visibility 0

TES_Pixel_L3.Copy TP_L3_00164
TP_L3_00164.Position -2.325 10.075 0
TP_L3_00164.Mother TES_L3
TP_L3_00164.Visibility 0

TES_Pixel_L3.Copy TP_L3_00165
TP_L3_00165.Position -2.325 11.625 0
TP_L3_00165.Mother TES_L3
TP_L3_00165.Visibility 0

TES_Pixel_L3.Copy TP_L3_00166
TP_L3_00166.Position -2.325 13.175 0
TP_L3_00166.Mother TES_L3
TP_L3_00166.Visibility 0

TES_Pixel_L3.Copy TP_L3_00167
TP_L3_00167.Position -2.325 14.725 0
TP_L3_00167.Mother TES_L3
TP_L3_00167.Visibility 0

TES_Pixel_L3.Copy TP_L3_00168
TP_L3_00168.Position -0.775 -14.725 0
TP_L3_00168.Mother TES_L3
TP_L3_00168.Visibility 0

TES_Pixel_L3.Copy TP_L3_00169
TP_L3_00169.Position -0.775 -13.175 0
TP_L3_00169.Mother TES_L3
TP_L3_00169.Visibility 0

TES_Pixel_L3.Copy TP_L3_00170
TP_L3_00170.Position -0.775 -11.625 0
TP_L3_00170.Mother TES_L3
TP_L3_00170.Visibility 0

TES_Pixel_L3.Copy TP_L3_00171
TP_L3_00171.Position -0.775 -10.075 0
TP_L3_00171.Mother TES_L3
TP_L3_00171.Visibility 0

TES_Pixel_L3.Copy TP_L3_00172
TP_L3_00172.Position -0.775 -8.525 0
TP_L3_00172.Mother TES_L3
TP_L3_00172.Visibility 0

TES_Pixel_L3.Copy TP_L3_00173
TP_L3_00173.Position -0.775 -6.975 0
TP_L3_00173.Mother TES_L3
TP_L3_00173.Visibility 0

TES_Pixel_L3.Copy TP_L3_00174
TP_L3_00174.Position -0.775 -5.425 0
TP_L3_00174.Mother TES_L3
TP_L3_00174.Visibility 0

TES_Pixel_L3.Copy TP_L3_00175
TP_L3_00175.Position -0.775 -3.875 0
TP_L3_00175.Mother TES_L3
TP_L3_00175.Visibility 0

TES_Pixel_L3.Copy TP_L3_00176
TP_L3_00176.Position -0.775 -2.325 0
TP_L3_00176.Mother TES_L3
TP_L3_00176.Visibility 0

TES_Pixel_L3.Copy TP_L3_00177
TP_L3_00177.Position -0.775 -0.775 0
TP_L3_00177.Mother TES_L3
TP_L3_00177.Visibility 0

TES_Pixel_L3.Copy TP_L3_00178
TP_L3_00178.Position -0.775 0.775 0
TP_L3_00178.Mother TES_L3
TP_L3_00178.Visibility 0

TES_Pixel_L3.Copy TP_L3_00179
TP_L3_00179.Position -0.775 2.325 0
TP_L3_00179.Mother TES_L3
TP_L3_00179.Visibility 0

TES_Pixel_L3.Copy TP_L3_00180
TP_L3_00180.Position -0.775 3.875 0
TP_L3_00180.Mother TES_L3
TP_L3_00180.Visibility 0

TES_Pixel_L3.Copy TP_L3_00181
TP_L3_00181.Position -0.775 5.425 0
TP_L3_00181.Mother TES_L3
TP_L3_00181.Visibility 0

TES_Pixel_L3.Copy TP_L3_00182
TP_L3_00182.Position -0.775 6.975 0
TP_L3_00182.Mother TES_L3
TP_L3_00182.Visibility 0

TES_Pixel_L3.Copy TP_L3_00183
TP_L3_00183.Position -0.775 8.525 0
TP_L3_00183.Mother TES_L3
TP_L3_00183.Visibility 0

TES_Pixel_L3.Copy TP_L3_00184
TP_L3_00184.Position -0.775 10.075 0
TP_L3_00184.Mother TES_L3
TP_L3_00184.Visibility 0

TES_Pixel_L3.Copy TP_L3_00185
TP_L3_00185.Position -0.775 11.625 0
TP_L3_00185.Mother TES_L3
TP_L3_00185.Visibility 0

TES_Pixel_L3.Copy TP_L3_00186
TP_L3_00186.Position -0.775 13.175 0
TP_L3_00186.Mother TES_L3
TP_L3_00186.Visibility 0

TES_Pixel_L3.Copy TP_L3_00187
TP_L3_00187.Position -0.775 14.725 0
TP_L3_00187.Mother TES_L3
TP_L3_00187.Visibility 0

TES_Pixel_L3.Copy TP_L3_00188
TP_L3_00188.Position 0.775 -14.725 0
TP_L3_00188.Mother TES_L3
TP_L3_00188.Visibility 0

TES_Pixel_L3.Copy TP_L3_00189
TP_L3_00189.Position 0.775 -13.175 0
TP_L3_00189.Mother TES_L3
TP_L3_00189.Visibility 0

TES_Pixel_L3.Copy TP_L3_00190
TP_L3_00190.Position 0.775 -11.625 0
TP_L3_00190.Mother TES_L3
TP_L3_00190.Visibility 0

TES_Pixel_L3.Copy TP_L3_00191
TP_L3_00191.Position 0.775 -10.075 0
TP_L3_00191.Mother TES_L3
TP_L3_00191.Visibility 0

TES_Pixel_L3.Copy TP_L3_00192
TP_L3_00192.Position 0.775 -8.525 0
TP_L3_00192.Mother TES_L3
TP_L3_00192.Visibility 0

TES_Pixel_L3.Copy TP_L3_00193
TP_L3_00193.Position 0.775 -6.975 0
TP_L3_00193.Mother TES_L3
TP_L3_00193.Visibility 0

TES_Pixel_L3.Copy TP_L3_00194
TP_L3_00194.Position 0.775 -5.425 0
TP_L3_00194.Mother TES_L3
TP_L3_00194.Visibility 0

TES_Pixel_L3.Copy TP_L3_00195
TP_L3_00195.Position 0.775 -3.875 0
TP_L3_00195.Mother TES_L3
TP_L3_00195.Visibility 0

TES_Pixel_L3.Copy TP_L3_00196
TP_L3_00196.Position 0.775 -2.325 0
TP_L3_00196.Mother TES_L3
TP_L3_00196.Visibility 0

TES_Pixel_L3.Copy TP_L3_00197
TP_L3_00197.Position 0.775 -0.775 0
TP_L3_00197.Mother TES_L3
TP_L3_00197.Visibility 0

TES_Pixel_L3.Copy TP_L3_00198
TP_L3_00198.Position 0.775 0.775 0
TP_L3_00198.Mother TES_L3
TP_L3_00198.Visibility 0

TES_Pixel_L3.Copy TP_L3_00199
TP_L3_00199.Position 0.775 2.325 0
TP_L3_00199.Mother TES_L3
TP_L3_00199.Visibility 0

TES_Pixel_L3.Copy TP_L3_00200
TP_L3_00200.Position 0.775 3.875 0
TP_L3_00200.Mother TES_L3
TP_L3_00200.Visibility 0

TES_Pixel_L3.Copy TP_L3_00201
TP_L3_00201.Position 0.775 5.425 0
TP_L3_00201.Mother TES_L3
TP_L3_00201.Visibility 0

TES_Pixel_L3.Copy TP_L3_00202
TP_L3_00202.Position 0.775 6.975 0
TP_L3_00202.Mother TES_L3
TP_L3_00202.Visibility 0

TES_Pixel_L3.Copy TP_L3_00203
TP_L3_00203.Position 0.775 8.525 0
TP_L3_00203.Mother TES_L3
TP_L3_00203.Visibility 0

TES_Pixel_L3.Copy TP_L3_00204
TP_L3_00204.Position 0.775 10.075 0
TP_L3_00204.Mother TES_L3
TP_L3_00204.Visibility 0

TES_Pixel_L3.Copy TP_L3_00205
TP_L3_00205.Position 0.775 11.625 0
TP_L3_00205.Mother TES_L3
TP_L3_00205.Visibility 0

TES_Pixel_L3.Copy TP_L3_00206
TP_L3_00206.Position 0.775 13.175 0
TP_L3_00206.Mother TES_L3
TP_L3_00206.Visibility 0

TES_Pixel_L3.Copy TP_L3_00207
TP_L3_00207.Position 0.775 14.725 0
TP_L3_00207.Mother TES_L3
TP_L3_00207.Visibility 0

TES_Pixel_L3.Copy TP_L3_00208
TP_L3_00208.Position 2.325 -14.725 0
TP_L3_00208.Mother TES_L3
TP_L3_00208.Visibility 0

TES_Pixel_L3.Copy TP_L3_00209
TP_L3_00209.Position 2.325 -13.175 0
TP_L3_00209.Mother TES_L3
TP_L3_00209.Visibility 0

TES_Pixel_L3.Copy TP_L3_00210
TP_L3_00210.Position 2.325 -11.625 0
TP_L3_00210.Mother TES_L3
TP_L3_00210.Visibility 0

TES_Pixel_L3.Copy TP_L3_00211
TP_L3_00211.Position 2.325 -10.075 0
TP_L3_00211.Mother TES_L3
TP_L3_00211.Visibility 0

TES_Pixel_L3.Copy TP_L3_00212
TP_L3_00212.Position 2.325 -8.525 0
TP_L3_00212.Mother TES_L3
TP_L3_00212.Visibility 0

TES_Pixel_L3.Copy TP_L3_00213
TP_L3_00213.Position 2.325 -6.975 0
TP_L3_00213.Mother TES_L3
TP_L3_00213.Visibility 0

TES_Pixel_L3.Copy TP_L3_00214
TP_L3_00214.Position 2.325 -5.425 0
TP_L3_00214.Mother TES_L3
TP_L3_00214.Visibility 0

TES_Pixel_L3.Copy TP_L3_00215
TP_L3_00215.Position 2.325 -3.875 0
TP_L3_00215.Mother TES_L3
TP_L3_00215.Visibility 0

TES_Pixel_L3.Copy TP_L3_00216
TP_L3_00216.Position 2.325 -2.325 0
TP_L3_00216.Mother TES_L3
TP_L3_00216.Visibility 0

TES_Pixel_L3.Copy TP_L3_00217
TP_L3_00217.Position 2.325 -0.775 0
TP_L3_00217.Mother TES_L3
TP_L3_00217.Visibility 0

TES_Pixel_L3.Copy TP_L3_00218
TP_L3_00218.Position 2.325 0.775 0
TP_L3_00218.Mother TES_L3
TP_L3_00218.Visibility 0

TES_Pixel_L3.Copy TP_L3_00219
TP_L3_00219.Position 2.325 2.325 0
TP_L3_00219.Mother TES_L3
TP_L3_00219.Visibility 0

TES_Pixel_L3.Copy TP_L3_00220
TP_L3_00220.Position 2.325 3.875 0
TP_L3_00220.Mother TES_L3
TP_L3_00220.Visibility 0

TES_Pixel_L3.Copy TP_L3_00221
TP_L3_00221.Position 2.325 5.425 0
TP_L3_00221.Mother TES_L3
TP_L3_00221.Visibility 0

TES_Pixel_L3.Copy TP_L3_00222
TP_L3_00222.Position 2.325 6.975 0
TP_L3_00222.Mother TES_L3
TP_L3_00222.Visibility 0

TES_Pixel_L3.Copy TP_L3_00223
TP_L3_00223.Position 2.325 8.525 0
TP_L3_00223.Mother TES_L3
TP_L3_00223.Visibility 0

TES_Pixel_L3.Copy TP_L3_00224
TP_L3_00224.Position 2.325 10.075 0
TP_L3_00224.Mother TES_L3
TP_L3_00224.Visibility 0

TES_Pixel_L3.Copy TP_L3_00225
TP_L3_00225.Position 2.325 11.625 0
TP_L3_00225.Mother TES_L3
TP_L3_00225.Visibility 0

TES_Pixel_L3.Copy TP_L3_00226
TP_L3_00226.Position 2.325 13.175 0
TP_L3_00226.Mother TES_L3
TP_L3_00226.Visibility 0

TES_Pixel_L3.Copy TP_L3_00227
TP_L3_00227.Position 2.325 14.725 0
TP_L3_00227.Mother TES_L3
TP_L3_00227.Visibility 0

TES_Pixel_L3.Copy TP_L3_00228
TP_L3_00228.Position 3.875 -14.725 0
TP_L3_00228.Mother TES_L3
TP_L3_00228.Visibility 0

TES_Pixel_L3.Copy TP_L3_00229
TP_L3_00229.Position 3.875 -13.175 0
TP_L3_00229.Mother TES_L3
TP_L3_00229.Visibility 0

TES_Pixel_L3.Copy TP_L3_00230
TP_L3_00230.Position 3.875 -11.625 0
TP_L3_00230.Mother TES_L3
TP_L3_00230.Visibility 0

TES_Pixel_L3.Copy TP_L3_00231
TP_L3_00231.Position 3.875 -10.075 0
TP_L3_00231.Mother TES_L3
TP_L3_00231.Visibility 0

TES_Pixel_L3.Copy TP_L3_00232
TP_L3_00232.Position 3.875 -8.525 0
TP_L3_00232.Mother TES_L3
TP_L3_00232.Visibility 0

TES_Pixel_L3.Copy TP_L3_00233
TP_L3_00233.Position 3.875 -6.975 0
TP_L3_00233.Mother TES_L3
TP_L3_00233.Visibility 0

TES_Pixel_L3.Copy TP_L3_00234
TP_L3_00234.Position 3.875 -5.425 0
TP_L3_00234.Mother TES_L3
TP_L3_00234.Visibility 0

TES_Pixel_L3.Copy TP_L3_00235
TP_L3_00235.Position 3.875 -3.875 0
TP_L3_00235.Mother TES_L3
TP_L3_00235.Visibility 0

TES_Pixel_L3.Copy TP_L3_00236
TP_L3_00236.Position 3.875 -2.325 0
TP_L3_00236.Mother TES_L3
TP_L3_00236.Visibility 0

TES_Pixel_L3.Copy TP_L3_00237
TP_L3_00237.Position 3.875 -0.775 0
TP_L3_00237.Mother TES_L3
TP_L3_00237.Visibility 0

TES_Pixel_L3.Copy TP_L3_00238
TP_L3_00238.Position 3.875 0.775 0
TP_L3_00238.Mother TES_L3
TP_L3_00238.Visibility 0

TES_Pixel_L3.Copy TP_L3_00239
TP_L3_00239.Position 3.875 2.325 0
TP_L3_00239.Mother TES_L3
TP_L3_00239.Visibility 0

TES_Pixel_L3.Copy TP_L3_00240
TP_L3_00240.Position 3.875 3.875 0
TP_L3_00240.Mother TES_L3
TP_L3_00240.Visibility 0

TES_Pixel_L3.Copy TP_L3_00241
TP_L3_00241.Position 3.875 5.425 0
TP_L3_00241.Mother TES_L3
TP_L3_00241.Visibility 0

TES_Pixel_L3.Copy TP_L3_00242
TP_L3_00242.Position 3.875 6.975 0
TP_L3_00242.Mother TES_L3
TP_L3_00242.Visibility 0

TES_Pixel_L3.Copy TP_L3_00243
TP_L3_00243.Position 3.875 8.525 0
TP_L3_00243.Mother TES_L3
TP_L3_00243.Visibility 0

TES_Pixel_L3.Copy TP_L3_00244
TP_L3_00244.Position 3.875 10.075 0
TP_L3_00244.Mother TES_L3
TP_L3_00244.Visibility 0

TES_Pixel_L3.Copy TP_L3_00245
TP_L3_00245.Position 3.875 11.625 0
TP_L3_00245.Mother TES_L3
TP_L3_00245.Visibility 0

TES_Pixel_L3.Copy TP_L3_00246
TP_L3_00246.Position 3.875 13.175 0
TP_L3_00246.Mother TES_L3
TP_L3_00246.Visibility 0

TES_Pixel_L3.Copy TP_L3_00247
TP_L3_00247.Position 3.875 14.725 0
TP_L3_00247.Mother TES_L3
TP_L3_00247.Visibility 0

TES_Pixel_L3.Copy TP_L3_00248
TP_L3_00248.Position 5.425 -14.725 0
TP_L3_00248.Mother TES_L3
TP_L3_00248.Visibility 0

TES_Pixel_L3.Copy TP_L3_00249
TP_L3_00249.Position 5.425 -13.175 0
TP_L3_00249.Mother TES_L3
TP_L3_00249.Visibility 0

TES_Pixel_L3.Copy TP_L3_00250
TP_L3_00250.Position 5.425 -11.625 0
TP_L3_00250.Mother TES_L3
TP_L3_00250.Visibility 0

TES_Pixel_L3.Copy TP_L3_00251
TP_L3_00251.Position 5.425 -10.075 0
TP_L3_00251.Mother TES_L3
TP_L3_00251.Visibility 0

TES_Pixel_L3.Copy TP_L3_00252
TP_L3_00252.Position 5.425 -8.525 0
TP_L3_00252.Mother TES_L3
TP_L3_00252.Visibility 0

TES_Pixel_L3.Copy TP_L3_00253
TP_L3_00253.Position 5.425 -6.975 0
TP_L3_00253.Mother TES_L3
TP_L3_00253.Visibility 0

TES_Pixel_L3.Copy TP_L3_00254
TP_L3_00254.Position 5.425 -5.425 0
TP_L3_00254.Mother TES_L3
TP_L3_00254.Visibility 0

TES_Pixel_L3.Copy TP_L3_00255
TP_L3_00255.Position 5.425 -3.875 0
TP_L3_00255.Mother TES_L3
TP_L3_00255.Visibility 0

TES_Pixel_L3.Copy TP_L3_00256
TP_L3_00256.Position 5.425 -2.325 0
TP_L3_00256.Mother TES_L3
TP_L3_00256.Visibility 0

TES_Pixel_L3.Copy TP_L3_00257
TP_L3_00257.Position 5.425 -0.775 0
TP_L3_00257.Mother TES_L3
TP_L3_00257.Visibility 0

TES_Pixel_L3.Copy TP_L3_00258
TP_L3_00258.Position 5.425 0.775 0
TP_L3_00258.Mother TES_L3
TP_L3_00258.Visibility 0

TES_Pixel_L3.Copy TP_L3_00259
TP_L3_00259.Position 5.425 2.325 0
TP_L3_00259.Mother TES_L3
TP_L3_00259.Visibility 0

TES_Pixel_L3.Copy TP_L3_00260
TP_L3_00260.Position 5.425 3.875 0
TP_L3_00260.Mother TES_L3
TP_L3_00260.Visibility 0

TES_Pixel_L3.Copy TP_L3_00261
TP_L3_00261.Position 5.425 5.425 0
TP_L3_00261.Mother TES_L3
TP_L3_00261.Visibility 0

TES_Pixel_L3.Copy TP_L3_00262
TP_L3_00262.Position 5.425 6.975 0
TP_L3_00262.Mother TES_L3
TP_L3_00262.Visibility 0

TES_Pixel_L3.Copy TP_L3_00263
TP_L3_00263.Position 5.425 8.525 0
TP_L3_00263.Mother TES_L3
TP_L3_00263.Visibility 0

TES_Pixel_L3.Copy TP_L3_00264
TP_L3_00264.Position 5.425 10.075 0
TP_L3_00264.Mother TES_L3
TP_L3_00264.Visibility 0

TES_Pixel_L3.Copy TP_L3_00265
TP_L3_00265.Position 5.425 11.625 0
TP_L3_00265.Mother TES_L3
TP_L3_00265.Visibility 0

TES_Pixel_L3.Copy TP_L3_00266
TP_L3_00266.Position 5.425 13.175 0
TP_L3_00266.Mother TES_L3
TP_L3_00266.Visibility 0

TES_Pixel_L3.Copy TP_L3_00267
TP_L3_00267.Position 5.425 14.725 0
TP_L3_00267.Mother TES_L3
TP_L3_00267.Visibility 0

TES_Pixel_L3.Copy TP_L3_00268
TP_L3_00268.Position 6.975 -14.725 0
TP_L3_00268.Mother TES_L3
TP_L3_00268.Visibility 0

TES_Pixel_L3.Copy TP_L3_00269
TP_L3_00269.Position 6.975 -13.175 0
TP_L3_00269.Mother TES_L3
TP_L3_00269.Visibility 0

TES_Pixel_L3.Copy TP_L3_00270
TP_L3_00270.Position 6.975 -11.625 0
TP_L3_00270.Mother TES_L3
TP_L3_00270.Visibility 0

TES_Pixel_L3.Copy TP_L3_00271
TP_L3_00271.Position 6.975 -10.075 0
TP_L3_00271.Mother TES_L3
TP_L3_00271.Visibility 0

TES_Pixel_L3.Copy TP_L3_00272
TP_L3_00272.Position 6.975 -8.525 0
TP_L3_00272.Mother TES_L3
TP_L3_00272.Visibility 0

TES_Pixel_L3.Copy TP_L3_00273
TP_L3_00273.Position 6.975 -6.975 0
TP_L3_00273.Mother TES_L3
TP_L3_00273.Visibility 0

TES_Pixel_L3.Copy TP_L3_00274
TP_L3_00274.Position 6.975 -5.425 0
TP_L3_00274.Mother TES_L3
TP_L3_00274.Visibility 0

TES_Pixel_L3.Copy TP_L3_00275
TP_L3_00275.Position 6.975 -3.875 0
TP_L3_00275.Mother TES_L3
TP_L3_00275.Visibility 0

TES_Pixel_L3.Copy TP_L3_00276
TP_L3_00276.Position 6.975 -2.325 0
TP_L3_00276.Mother TES_L3
TP_L3_00276.Visibility 0

TES_Pixel_L3.Copy TP_L3_00277
TP_L3_00277.Position 6.975 -0.775 0
TP_L3_00277.Mother TES_L3
TP_L3_00277.Visibility 0

TES_Pixel_L3.Copy TP_L3_00278
TP_L3_00278.Position 6.975 0.775 0
TP_L3_00278.Mother TES_L3
TP_L3_00278.Visibility 0

TES_Pixel_L3.Copy TP_L3_00279
TP_L3_00279.Position 6.975 2.325 0
TP_L3_00279.Mother TES_L3
TP_L3_00279.Visibility 0

TES_Pixel_L3.Copy TP_L3_00280
TP_L3_00280.Position 6.975 3.875 0
TP_L3_00280.Mother TES_L3
TP_L3_00280.Visibility 0

TES_Pixel_L3.Copy TP_L3_00281
TP_L3_00281.Position 6.975 5.425 0
TP_L3_00281.Mother TES_L3
TP_L3_00281.Visibility 0

TES_Pixel_L3.Copy TP_L3_00282
TP_L3_00282.Position 6.975 6.975 0
TP_L3_00282.Mother TES_L3
TP_L3_00282.Visibility 0

TES_Pixel_L3.Copy TP_L3_00283
TP_L3_00283.Position 6.975 8.525 0
TP_L3_00283.Mother TES_L3
TP_L3_00283.Visibility 0

TES_Pixel_L3.Copy TP_L3_00284
TP_L3_00284.Position 6.975 10.075 0
TP_L3_00284.Mother TES_L3
TP_L3_00284.Visibility 0

TES_Pixel_L3.Copy TP_L3_00285
TP_L3_00285.Position 6.975 11.625 0
TP_L3_00285.Mother TES_L3
TP_L3_00285.Visibility 0

TES_Pixel_L3.Copy TP_L3_00286
TP_L3_00286.Position 6.975 13.175 0
TP_L3_00286.Mother TES_L3
TP_L3_00286.Visibility 0

TES_Pixel_L3.Copy TP_L3_00287
TP_L3_00287.Position 6.975 14.725 0
TP_L3_00287.Mother TES_L3
TP_L3_00287.Visibility 0

TES_Pixel_L3.Copy TP_L3_00288
TP_L3_00288.Position 8.525 -14.725 0
TP_L3_00288.Mother TES_L3
TP_L3_00288.Visibility 0

TES_Pixel_L3.Copy TP_L3_00289
TP_L3_00289.Position 8.525 -13.175 0
TP_L3_00289.Mother TES_L3
TP_L3_00289.Visibility 0

TES_Pixel_L3.Copy TP_L3_00290
TP_L3_00290.Position 8.525 -11.625 0
TP_L3_00290.Mother TES_L3
TP_L3_00290.Visibility 0

TES_Pixel_L3.Copy TP_L3_00291
TP_L3_00291.Position 8.525 -10.075 0
TP_L3_00291.Mother TES_L3
TP_L3_00291.Visibility 0

TES_Pixel_L3.Copy TP_L3_00292
TP_L3_00292.Position 8.525 -8.525 0
TP_L3_00292.Mother TES_L3
TP_L3_00292.Visibility 0

TES_Pixel_L3.Copy TP_L3_00293
TP_L3_00293.Position 8.525 -6.975 0
TP_L3_00293.Mother TES_L3
TP_L3_00293.Visibility 0

TES_Pixel_L3.Copy TP_L3_00294
TP_L3_00294.Position 8.525 -5.425 0
TP_L3_00294.Mother TES_L3
TP_L3_00294.Visibility 0

TES_Pixel_L3.Copy TP_L3_00295
TP_L3_00295.Position 8.525 -3.875 0
TP_L3_00295.Mother TES_L3
TP_L3_00295.Visibility 0

TES_Pixel_L3.Copy TP_L3_00296
TP_L3_00296.Position 8.525 -2.325 0
TP_L3_00296.Mother TES_L3
TP_L3_00296.Visibility 0

TES_Pixel_L3.Copy TP_L3_00297
TP_L3_00297.Position 8.525 -0.775 0
TP_L3_00297.Mother TES_L3
TP_L3_00297.Visibility 0

TES_Pixel_L3.Copy TP_L3_00298
TP_L3_00298.Position 8.525 0.775 0
TP_L3_00298.Mother TES_L3
TP_L3_00298.Visibility 0

TES_Pixel_L3.Copy TP_L3_00299
TP_L3_00299.Position 8.525 2.325 0
TP_L3_00299.Mother TES_L3
TP_L3_00299.Visibility 0

TES_Pixel_L3.Copy TP_L3_00300
TP_L3_00300.Position 8.525 3.875 0
TP_L3_00300.Mother TES_L3
TP_L3_00300.Visibility 0

TES_Pixel_L3.Copy TP_L3_00301
TP_L3_00301.Position 8.525 5.425 0
TP_L3_00301.Mother TES_L3
TP_L3_00301.Visibility 0

TES_Pixel_L3.Copy TP_L3_00302
TP_L3_00302.Position 8.525 6.975 0
TP_L3_00302.Mother TES_L3
TP_L3_00302.Visibility 0

TES_Pixel_L3.Copy TP_L3_00303
TP_L3_00303.Position 8.525 8.525 0
TP_L3_00303.Mother TES_L3
TP_L3_00303.Visibility 0

TES_Pixel_L3.Copy TP_L3_00304
TP_L3_00304.Position 8.525 10.075 0
TP_L3_00304.Mother TES_L3
TP_L3_00304.Visibility 0

TES_Pixel_L3.Copy TP_L3_00305
TP_L3_00305.Position 8.525 11.625 0
TP_L3_00305.Mother TES_L3
TP_L3_00305.Visibility 0

TES_Pixel_L3.Copy TP_L3_00306
TP_L3_00306.Position 8.525 13.175 0
TP_L3_00306.Mother TES_L3
TP_L3_00306.Visibility 0

TES_Pixel_L3.Copy TP_L3_00307
TP_L3_00307.Position 8.525 14.725 0
TP_L3_00307.Mother TES_L3
TP_L3_00307.Visibility 0

TES_Pixel_L3.Copy TP_L3_00308
TP_L3_00308.Position 10.075 -14.725 0
TP_L3_00308.Mother TES_L3
TP_L3_00308.Visibility 0

TES_Pixel_L3.Copy TP_L3_00309
TP_L3_00309.Position 10.075 -13.175 0
TP_L3_00309.Mother TES_L3
TP_L3_00309.Visibility 0

TES_Pixel_L3.Copy TP_L3_00310
TP_L3_00310.Position 10.075 -11.625 0
TP_L3_00310.Mother TES_L3
TP_L3_00310.Visibility 0

TES_Pixel_L3.Copy TP_L3_00311
TP_L3_00311.Position 10.075 -10.075 0
TP_L3_00311.Mother TES_L3
TP_L3_00311.Visibility 0

TES_Pixel_L3.Copy TP_L3_00312
TP_L3_00312.Position 10.075 -8.525 0
TP_L3_00312.Mother TES_L3
TP_L3_00312.Visibility 0

TES_Pixel_L3.Copy TP_L3_00313
TP_L3_00313.Position 10.075 -6.975 0
TP_L3_00313.Mother TES_L3
TP_L3_00313.Visibility 0

TES_Pixel_L3.Copy TP_L3_00314
TP_L3_00314.Position 10.075 -5.425 0
TP_L3_00314.Mother TES_L3
TP_L3_00314.Visibility 0

TES_Pixel_L3.Copy TP_L3_00315
TP_L3_00315.Position 10.075 -3.875 0
TP_L3_00315.Mother TES_L3
TP_L3_00315.Visibility 0

TES_Pixel_L3.Copy TP_L3_00316
TP_L3_00316.Position 10.075 -2.325 0
TP_L3_00316.Mother TES_L3
TP_L3_00316.Visibility 0

TES_Pixel_L3.Copy TP_L3_00317
TP_L3_00317.Position 10.075 -0.775 0
TP_L3_00317.Mother TES_L3
TP_L3_00317.Visibility 0

TES_Pixel_L3.Copy TP_L3_00318
TP_L3_00318.Position 10.075 0.775 0
TP_L3_00318.Mother TES_L3
TP_L3_00318.Visibility 0

TES_Pixel_L3.Copy TP_L3_00319
TP_L3_00319.Position 10.075 2.325 0
TP_L3_00319.Mother TES_L3
TP_L3_00319.Visibility 0

TES_Pixel_L3.Copy TP_L3_00320
TP_L3_00320.Position 10.075 3.875 0
TP_L3_00320.Mother TES_L3
TP_L3_00320.Visibility 0

TES_Pixel_L3.Copy TP_L3_00321
TP_L3_00321.Position 10.075 5.425 0
TP_L3_00321.Mother TES_L3
TP_L3_00321.Visibility 0

TES_Pixel_L3.Copy TP_L3_00322
TP_L3_00322.Position 10.075 6.975 0
TP_L3_00322.Mother TES_L3
TP_L3_00322.Visibility 0

TES_Pixel_L3.Copy TP_L3_00323
TP_L3_00323.Position 10.075 8.525 0
TP_L3_00323.Mother TES_L3
TP_L3_00323.Visibility 0

TES_Pixel_L3.Copy TP_L3_00324
TP_L3_00324.Position 10.075 10.075 0
TP_L3_00324.Mother TES_L3
TP_L3_00324.Visibility 0

TES_Pixel_L3.Copy TP_L3_00325
TP_L3_00325.Position 10.075 11.625 0
TP_L3_00325.Mother TES_L3
TP_L3_00325.Visibility 0

TES_Pixel_L3.Copy TP_L3_00326
TP_L3_00326.Position 10.075 13.175 0
TP_L3_00326.Mother TES_L3
TP_L3_00326.Visibility 0

TES_Pixel_L3.Copy TP_L3_00327
TP_L3_00327.Position 10.075 14.725 0
TP_L3_00327.Mother TES_L3
TP_L3_00327.Visibility 0

TES_Pixel_L3.Copy TP_L3_00328
TP_L3_00328.Position 11.625 -13.175 0
TP_L3_00328.Mother TES_L3
TP_L3_00328.Visibility 0

TES_Pixel_L3.Copy TP_L3_00329
TP_L3_00329.Position 11.625 -11.625 0
TP_L3_00329.Mother TES_L3
TP_L3_00329.Visibility 0

TES_Pixel_L3.Copy TP_L3_00330
TP_L3_00330.Position 11.625 -10.075 0
TP_L3_00330.Mother TES_L3
TP_L3_00330.Visibility 0

TES_Pixel_L3.Copy TP_L3_00331
TP_L3_00331.Position 11.625 -8.525 0
TP_L3_00331.Mother TES_L3
TP_L3_00331.Visibility 0

TES_Pixel_L3.Copy TP_L3_00332
TP_L3_00332.Position 11.625 -6.975 0
TP_L3_00332.Mother TES_L3
TP_L3_00332.Visibility 0

TES_Pixel_L3.Copy TP_L3_00333
TP_L3_00333.Position 11.625 -5.425 0
TP_L3_00333.Mother TES_L3
TP_L3_00333.Visibility 0

TES_Pixel_L3.Copy TP_L3_00334
TP_L3_00334.Position 11.625 -3.875 0
TP_L3_00334.Mother TES_L3
TP_L3_00334.Visibility 0

TES_Pixel_L3.Copy TP_L3_00335
TP_L3_00335.Position 11.625 -2.325 0
TP_L3_00335.Mother TES_L3
TP_L3_00335.Visibility 0

TES_Pixel_L3.Copy TP_L3_00336
TP_L3_00336.Position 11.625 -0.775 0
TP_L3_00336.Mother TES_L3
TP_L3_00336.Visibility 0

TES_Pixel_L3.Copy TP_L3_00337
TP_L3_00337.Position 11.625 0.775 0
TP_L3_00337.Mother TES_L3
TP_L3_00337.Visibility 0

TES_Pixel_L3.Copy TP_L3_00338
TP_L3_00338.Position 11.625 2.325 0
TP_L3_00338.Mother TES_L3
TP_L3_00338.Visibility 0

TES_Pixel_L3.Copy TP_L3_00339
TP_L3_00339.Position 11.625 3.875 0
TP_L3_00339.Mother TES_L3
TP_L3_00339.Visibility 0

TES_Pixel_L3.Copy TP_L3_00340
TP_L3_00340.Position 11.625 5.425 0
TP_L3_00340.Mother TES_L3
TP_L3_00340.Visibility 0

TES_Pixel_L3.Copy TP_L3_00341
TP_L3_00341.Position 11.625 6.975 0
TP_L3_00341.Mother TES_L3
TP_L3_00341.Visibility 0

TES_Pixel_L3.Copy TP_L3_00342
TP_L3_00342.Position 11.625 8.525 0
TP_L3_00342.Mother TES_L3
TP_L3_00342.Visibility 0

TES_Pixel_L3.Copy TP_L3_00343
TP_L3_00343.Position 11.625 10.075 0
TP_L3_00343.Mother TES_L3
TP_L3_00343.Visibility 0

TES_Pixel_L3.Copy TP_L3_00344
TP_L3_00344.Position 11.625 11.625 0
TP_L3_00344.Mother TES_L3
TP_L3_00344.Visibility 0

TES_Pixel_L3.Copy TP_L3_00345
TP_L3_00345.Position 11.625 13.175 0
TP_L3_00345.Mother TES_L3
TP_L3_00345.Visibility 0

TES_Pixel_L3.Copy TP_L3_00346
TP_L3_00346.Position 13.175 -11.625 0
TP_L3_00346.Mother TES_L3
TP_L3_00346.Visibility 0

TES_Pixel_L3.Copy TP_L3_00347
TP_L3_00347.Position 13.175 -10.075 0
TP_L3_00347.Mother TES_L3
TP_L3_00347.Visibility 0

TES_Pixel_L3.Copy TP_L3_00348
TP_L3_00348.Position 13.175 -8.525 0
TP_L3_00348.Mother TES_L3
TP_L3_00348.Visibility 0

TES_Pixel_L3.Copy TP_L3_00349
TP_L3_00349.Position 13.175 -6.975 0
TP_L3_00349.Mother TES_L3
TP_L3_00349.Visibility 0

TES_Pixel_L3.Copy TP_L3_00350
TP_L3_00350.Position 13.175 -5.425 0
TP_L3_00350.Mother TES_L3
TP_L3_00350.Visibility 0

TES_Pixel_L3.Copy TP_L3_00351
TP_L3_00351.Position 13.175 -3.875 0
TP_L3_00351.Mother TES_L3
TP_L3_00351.Visibility 0

TES_Pixel_L3.Copy TP_L3_00352
TP_L3_00352.Position 13.175 -2.325 0
TP_L3_00352.Mother TES_L3
TP_L3_00352.Visibility 0

TES_Pixel_L3.Copy TP_L3_00353
TP_L3_00353.Position 13.175 -0.775 0
TP_L3_00353.Mother TES_L3
TP_L3_00353.Visibility 0

TES_Pixel_L3.Copy TP_L3_00354
TP_L3_00354.Position 13.175 0.775 0
TP_L3_00354.Mother TES_L3
TP_L3_00354.Visibility 0

TES_Pixel_L3.Copy TP_L3_00355
TP_L3_00355.Position 13.175 2.325 0
TP_L3_00355.Mother TES_L3
TP_L3_00355.Visibility 0

TES_Pixel_L3.Copy TP_L3_00356
TP_L3_00356.Position 13.175 3.875 0
TP_L3_00356.Mother TES_L3
TP_L3_00356.Visibility 0

TES_Pixel_L3.Copy TP_L3_00357
TP_L3_00357.Position 13.175 5.425 0
TP_L3_00357.Mother TES_L3
TP_L3_00357.Visibility 0

TES_Pixel_L3.Copy TP_L3_00358
TP_L3_00358.Position 13.175 6.975 0
TP_L3_00358.Mother TES_L3
TP_L3_00358.Visibility 0

TES_Pixel_L3.Copy TP_L3_00359
TP_L3_00359.Position 13.175 8.525 0
TP_L3_00359.Mother TES_L3
TP_L3_00359.Visibility 0

TES_Pixel_L3.Copy TP_L3_00360
TP_L3_00360.Position 13.175 10.075 0
TP_L3_00360.Mother TES_L3
TP_L3_00360.Visibility 0

TES_Pixel_L3.Copy TP_L3_00361
TP_L3_00361.Position 13.175 11.625 0
TP_L3_00361.Mother TES_L3
TP_L3_00361.Visibility 0

TES_Pixel_L3.Copy TP_L3_00362
TP_L3_00362.Position 14.725 -10.075 0
TP_L3_00362.Mother TES_L3
TP_L3_00362.Visibility 0

TES_Pixel_L3.Copy TP_L3_00363
TP_L3_00363.Position 14.725 -8.525 0
TP_L3_00363.Mother TES_L3
TP_L3_00363.Visibility 0

TES_Pixel_L3.Copy TP_L3_00364
TP_L3_00364.Position 14.725 -6.975 0
TP_L3_00364.Mother TES_L3
TP_L3_00364.Visibility 0

TES_Pixel_L3.Copy TP_L3_00365
TP_L3_00365.Position 14.725 -5.425 0
TP_L3_00365.Mother TES_L3
TP_L3_00365.Visibility 0

TES_Pixel_L3.Copy TP_L3_00366
TP_L3_00366.Position 14.725 -3.875 0
TP_L3_00366.Mother TES_L3
TP_L3_00366.Visibility 0

TES_Pixel_L3.Copy TP_L3_00367
TP_L3_00367.Position 14.725 -2.325 0
TP_L3_00367.Mother TES_L3
TP_L3_00367.Visibility 0

TES_Pixel_L3.Copy TP_L3_00368
TP_L3_00368.Position 14.725 -0.775 0
TP_L3_00368.Mother TES_L3
TP_L3_00368.Visibility 0

TES_Pixel_L3.Copy TP_L3_00369
TP_L3_00369.Position 14.725 0.775 0
TP_L3_00369.Mother TES_L3
TP_L3_00369.Visibility 0

TES_Pixel_L3.Copy TP_L3_00370
TP_L3_00370.Position 14.725 2.325 0
TP_L3_00370.Mother TES_L3
TP_L3_00370.Visibility 0

TES_Pixel_L3.Copy TP_L3_00371
TP_L3_00371.Position 14.725 3.875 0
TP_L3_00371.Mother TES_L3
TP_L3_00371.Visibility 0

TES_Pixel_L3.Copy TP_L3_00372
TP_L3_00372.Position 14.725 5.425 0
TP_L3_00372.Mother TES_L3
TP_L3_00372.Visibility 0

TES_Pixel_L3.Copy TP_L3_00373
TP_L3_00373.Position 14.725 6.975 0
TP_L3_00373.Mother TES_L3
TP_L3_00373.Visibility 0

TES_Pixel_L3.Copy TP_L3_00374
TP_L3_00374.Position 14.725 8.525 0
TP_L3_00374.Mother TES_L3
TP_L3_00374.Visibility 0

TES_Pixel_L3.Copy TP_L3_00375
TP_L3_00375.Position 14.725 10.075 0
TP_L3_00375.Mother TES_L3
TP_L3_00375.Visibility 0

Substrate_L4.Position 0 0 58
Substrate_L4.Mother WorldVolume

TES_L4.Position 0 0 59.65
TES_L4.Mother WorldVolume
TES_L4.Visibility 0

TES_Pixel_L4.Copy TP_L4_00000
TP_L4_00000.Position -14.725 -10.075 0
TP_L4_00000.Mother TES_L4
TP_L4_00000.Visibility 0

TES_Pixel_L4.Copy TP_L4_00001
TP_L4_00001.Position -14.725 -8.525 0
TP_L4_00001.Mother TES_L4
TP_L4_00001.Visibility 0

TES_Pixel_L4.Copy TP_L4_00002
TP_L4_00002.Position -14.725 -6.975 0
TP_L4_00002.Mother TES_L4
TP_L4_00002.Visibility 0

TES_Pixel_L4.Copy TP_L4_00003
TP_L4_00003.Position -14.725 -5.425 0
TP_L4_00003.Mother TES_L4
TP_L4_00003.Visibility 0

TES_Pixel_L4.Copy TP_L4_00004
TP_L4_00004.Position -14.725 -3.875 0
TP_L4_00004.Mother TES_L4
TP_L4_00004.Visibility 0

TES_Pixel_L4.Copy TP_L4_00005
TP_L4_00005.Position -14.725 -2.325 0
TP_L4_00005.Mother TES_L4
TP_L4_00005.Visibility 0

TES_Pixel_L4.Copy TP_L4_00006
TP_L4_00006.Position -14.725 -0.775 0
TP_L4_00006.Mother TES_L4
TP_L4_00006.Visibility 0

TES_Pixel_L4.Copy TP_L4_00007
TP_L4_00007.Position -14.725 0.775 0
TP_L4_00007.Mother TES_L4
TP_L4_00007.Visibility 0

TES_Pixel_L4.Copy TP_L4_00008
TP_L4_00008.Position -14.725 2.325 0
TP_L4_00008.Mother TES_L4
TP_L4_00008.Visibility 0

TES_Pixel_L4.Copy TP_L4_00009
TP_L4_00009.Position -14.725 3.875 0
TP_L4_00009.Mother TES_L4
TP_L4_00009.Visibility 0

TES_Pixel_L4.Copy TP_L4_00010
TP_L4_00010.Position -14.725 5.425 0
TP_L4_00010.Mother TES_L4
TP_L4_00010.Visibility 0

TES_Pixel_L4.Copy TP_L4_00011
TP_L4_00011.Position -14.725 6.975 0
TP_L4_00011.Mother TES_L4
TP_L4_00011.Visibility 0

TES_Pixel_L4.Copy TP_L4_00012
TP_L4_00012.Position -14.725 8.525 0
TP_L4_00012.Mother TES_L4
TP_L4_00012.Visibility 0

TES_Pixel_L4.Copy TP_L4_00013
TP_L4_00013.Position -14.725 10.075 0
TP_L4_00013.Mother TES_L4
TP_L4_00013.Visibility 0

TES_Pixel_L4.Copy TP_L4_00014
TP_L4_00014.Position -13.175 -11.625 0
TP_L4_00014.Mother TES_L4
TP_L4_00014.Visibility 0

TES_Pixel_L4.Copy TP_L4_00015
TP_L4_00015.Position -13.175 -10.075 0
TP_L4_00015.Mother TES_L4
TP_L4_00015.Visibility 0

TES_Pixel_L4.Copy TP_L4_00016
TP_L4_00016.Position -13.175 -8.525 0
TP_L4_00016.Mother TES_L4
TP_L4_00016.Visibility 0

TES_Pixel_L4.Copy TP_L4_00017
TP_L4_00017.Position -13.175 -6.975 0
TP_L4_00017.Mother TES_L4
TP_L4_00017.Visibility 0

TES_Pixel_L4.Copy TP_L4_00018
TP_L4_00018.Position -13.175 -5.425 0
TP_L4_00018.Mother TES_L4
TP_L4_00018.Visibility 0

TES_Pixel_L4.Copy TP_L4_00019
TP_L4_00019.Position -13.175 -3.875 0
TP_L4_00019.Mother TES_L4
TP_L4_00019.Visibility 0

TES_Pixel_L4.Copy TP_L4_00020
TP_L4_00020.Position -13.175 -2.325 0
TP_L4_00020.Mother TES_L4
TP_L4_00020.Visibility 0

TES_Pixel_L4.Copy TP_L4_00021
TP_L4_00021.Position -13.175 -0.775 0
TP_L4_00021.Mother TES_L4
TP_L4_00021.Visibility 0

TES_Pixel_L4.Copy TP_L4_00022
TP_L4_00022.Position -13.175 0.775 0
TP_L4_00022.Mother TES_L4
TP_L4_00022.Visibility 0

TES_Pixel_L4.Copy TP_L4_00023
TP_L4_00023.Position -13.175 2.325 0
TP_L4_00023.Mother TES_L4
TP_L4_00023.Visibility 0

TES_Pixel_L4.Copy TP_L4_00024
TP_L4_00024.Position -13.175 3.875 0
TP_L4_00024.Mother TES_L4
TP_L4_00024.Visibility 0

TES_Pixel_L4.Copy TP_L4_00025
TP_L4_00025.Position -13.175 5.425 0
TP_L4_00025.Mother TES_L4
TP_L4_00025.Visibility 0

TES_Pixel_L4.Copy TP_L4_00026
TP_L4_00026.Position -13.175 6.975 0
TP_L4_00026.Mother TES_L4
TP_L4_00026.Visibility 0

TES_Pixel_L4.Copy TP_L4_00027
TP_L4_00027.Position -13.175 8.525 0
TP_L4_00027.Mother TES_L4
TP_L4_00027.Visibility 0

TES_Pixel_L4.Copy TP_L4_00028
TP_L4_00028.Position -13.175 10.075 0
TP_L4_00028.Mother TES_L4
TP_L4_00028.Visibility 0

TES_Pixel_L4.Copy TP_L4_00029
TP_L4_00029.Position -13.175 11.625 0
TP_L4_00029.Mother TES_L4
TP_L4_00029.Visibility 0

TES_Pixel_L4.Copy TP_L4_00030
TP_L4_00030.Position -11.625 -13.175 0
TP_L4_00030.Mother TES_L4
TP_L4_00030.Visibility 0

TES_Pixel_L4.Copy TP_L4_00031
TP_L4_00031.Position -11.625 -11.625 0
TP_L4_00031.Mother TES_L4
TP_L4_00031.Visibility 0

TES_Pixel_L4.Copy TP_L4_00032
TP_L4_00032.Position -11.625 -10.075 0
TP_L4_00032.Mother TES_L4
TP_L4_00032.Visibility 0

TES_Pixel_L4.Copy TP_L4_00033
TP_L4_00033.Position -11.625 -8.525 0
TP_L4_00033.Mother TES_L4
TP_L4_00033.Visibility 0

TES_Pixel_L4.Copy TP_L4_00034
TP_L4_00034.Position -11.625 -6.975 0
TP_L4_00034.Mother TES_L4
TP_L4_00034.Visibility 0

TES_Pixel_L4.Copy TP_L4_00035
TP_L4_00035.Position -11.625 -5.425 0
TP_L4_00035.Mother TES_L4
TP_L4_00035.Visibility 0

TES_Pixel_L4.Copy TP_L4_00036
TP_L4_00036.Position -11.625 -3.875 0
TP_L4_00036.Mother TES_L4
TP_L4_00036.Visibility 0

TES_Pixel_L4.Copy TP_L4_00037
TP_L4_00037.Position -11.625 -2.325 0
TP_L4_00037.Mother TES_L4
TP_L4_00037.Visibility 0

TES_Pixel_L4.Copy TP_L4_00038
TP_L4_00038.Position -11.625 -0.775 0
TP_L4_00038.Mother TES_L4
TP_L4_00038.Visibility 0

TES_Pixel_L4.Copy TP_L4_00039
TP_L4_00039.Position -11.625 0.775 0
TP_L4_00039.Mother TES_L4
TP_L4_00039.Visibility 0

TES_Pixel_L4.Copy TP_L4_00040
TP_L4_00040.Position -11.625 2.325 0
TP_L4_00040.Mother TES_L4
TP_L4_00040.Visibility 0

TES_Pixel_L4.Copy TP_L4_00041
TP_L4_00041.Position -11.625 3.875 0
TP_L4_00041.Mother TES_L4
TP_L4_00041.Visibility 0

TES_Pixel_L4.Copy TP_L4_00042
TP_L4_00042.Position -11.625 5.425 0
TP_L4_00042.Mother TES_L4
TP_L4_00042.Visibility 0

TES_Pixel_L4.Copy TP_L4_00043
TP_L4_00043.Position -11.625 6.975 0
TP_L4_00043.Mother TES_L4
TP_L4_00043.Visibility 0

TES_Pixel_L4.Copy TP_L4_00044
TP_L4_00044.Position -11.625 8.525 0
TP_L4_00044.Mother TES_L4
TP_L4_00044.Visibility 0

TES_Pixel_L4.Copy TP_L4_00045
TP_L4_00045.Position -11.625 10.075 0
TP_L4_00045.Mother TES_L4
TP_L4_00045.Visibility 0

TES_Pixel_L4.Copy TP_L4_00046
TP_L4_00046.Position -11.625 11.625 0
TP_L4_00046.Mother TES_L4
TP_L4_00046.Visibility 0

TES_Pixel_L4.Copy TP_L4_00047
TP_L4_00047.Position -11.625 13.175 0
TP_L4_00047.Mother TES_L4
TP_L4_00047.Visibility 0

TES_Pixel_L4.Copy TP_L4_00048
TP_L4_00048.Position -10.075 -14.725 0
TP_L4_00048.Mother TES_L4
TP_L4_00048.Visibility 0

TES_Pixel_L4.Copy TP_L4_00049
TP_L4_00049.Position -10.075 -13.175 0
TP_L4_00049.Mother TES_L4
TP_L4_00049.Visibility 0

TES_Pixel_L4.Copy TP_L4_00050
TP_L4_00050.Position -10.075 -11.625 0
TP_L4_00050.Mother TES_L4
TP_L4_00050.Visibility 0

TES_Pixel_L4.Copy TP_L4_00051
TP_L4_00051.Position -10.075 -10.075 0
TP_L4_00051.Mother TES_L4
TP_L4_00051.Visibility 0

TES_Pixel_L4.Copy TP_L4_00052
TP_L4_00052.Position -10.075 -8.525 0
TP_L4_00052.Mother TES_L4
TP_L4_00052.Visibility 0

TES_Pixel_L4.Copy TP_L4_00053
TP_L4_00053.Position -10.075 -6.975 0
TP_L4_00053.Mother TES_L4
TP_L4_00053.Visibility 0

TES_Pixel_L4.Copy TP_L4_00054
TP_L4_00054.Position -10.075 -5.425 0
TP_L4_00054.Mother TES_L4
TP_L4_00054.Visibility 0

TES_Pixel_L4.Copy TP_L4_00055
TP_L4_00055.Position -10.075 -3.875 0
TP_L4_00055.Mother TES_L4
TP_L4_00055.Visibility 0

TES_Pixel_L4.Copy TP_L4_00056
TP_L4_00056.Position -10.075 -2.325 0
TP_L4_00056.Mother TES_L4
TP_L4_00056.Visibility 0

TES_Pixel_L4.Copy TP_L4_00057
TP_L4_00057.Position -10.075 -0.775 0
TP_L4_00057.Mother TES_L4
TP_L4_00057.Visibility 0

TES_Pixel_L4.Copy TP_L4_00058
TP_L4_00058.Position -10.075 0.775 0
TP_L4_00058.Mother TES_L4
TP_L4_00058.Visibility 0

TES_Pixel_L4.Copy TP_L4_00059
TP_L4_00059.Position -10.075 2.325 0
TP_L4_00059.Mother TES_L4
TP_L4_00059.Visibility 0

TES_Pixel_L4.Copy TP_L4_00060
TP_L4_00060.Position -10.075 3.875 0
TP_L4_00060.Mother TES_L4
TP_L4_00060.Visibility 0

TES_Pixel_L4.Copy TP_L4_00061
TP_L4_00061.Position -10.075 5.425 0
TP_L4_00061.Mother TES_L4
TP_L4_00061.Visibility 0

TES_Pixel_L4.Copy TP_L4_00062
TP_L4_00062.Position -10.075 6.975 0
TP_L4_00062.Mother TES_L4
TP_L4_00062.Visibility 0

TES_Pixel_L4.Copy TP_L4_00063
TP_L4_00063.Position -10.075 8.525 0
TP_L4_00063.Mother TES_L4
TP_L4_00063.Visibility 0

TES_Pixel_L4.Copy TP_L4_00064
TP_L4_00064.Position -10.075 10.075 0
TP_L4_00064.Mother TES_L4
TP_L4_00064.Visibility 0

TES_Pixel_L4.Copy TP_L4_00065
TP_L4_00065.Position -10.075 11.625 0
TP_L4_00065.Mother TES_L4
TP_L4_00065.Visibility 0

TES_Pixel_L4.Copy TP_L4_00066
TP_L4_00066.Position -10.075 13.175 0
TP_L4_00066.Mother TES_L4
TP_L4_00066.Visibility 0

TES_Pixel_L4.Copy TP_L4_00067
TP_L4_00067.Position -10.075 14.725 0
TP_L4_00067.Mother TES_L4
TP_L4_00067.Visibility 0

TES_Pixel_L4.Copy TP_L4_00068
TP_L4_00068.Position -8.525 -14.725 0
TP_L4_00068.Mother TES_L4
TP_L4_00068.Visibility 0

TES_Pixel_L4.Copy TP_L4_00069
TP_L4_00069.Position -8.525 -13.175 0
TP_L4_00069.Mother TES_L4
TP_L4_00069.Visibility 0

TES_Pixel_L4.Copy TP_L4_00070
TP_L4_00070.Position -8.525 -11.625 0
TP_L4_00070.Mother TES_L4
TP_L4_00070.Visibility 0

TES_Pixel_L4.Copy TP_L4_00071
TP_L4_00071.Position -8.525 -10.075 0
TP_L4_00071.Mother TES_L4
TP_L4_00071.Visibility 0

TES_Pixel_L4.Copy TP_L4_00072
TP_L4_00072.Position -8.525 -8.525 0
TP_L4_00072.Mother TES_L4
TP_L4_00072.Visibility 0

TES_Pixel_L4.Copy TP_L4_00073
TP_L4_00073.Position -8.525 -6.975 0
TP_L4_00073.Mother TES_L4
TP_L4_00073.Visibility 0

TES_Pixel_L4.Copy TP_L4_00074
TP_L4_00074.Position -8.525 -5.425 0
TP_L4_00074.Mother TES_L4
TP_L4_00074.Visibility 0

TES_Pixel_L4.Copy TP_L4_00075
TP_L4_00075.Position -8.525 -3.875 0
TP_L4_00075.Mother TES_L4
TP_L4_00075.Visibility 0

TES_Pixel_L4.Copy TP_L4_00076
TP_L4_00076.Position -8.525 -2.325 0
TP_L4_00076.Mother TES_L4
TP_L4_00076.Visibility 0

TES_Pixel_L4.Copy TP_L4_00077
TP_L4_00077.Position -8.525 -0.775 0
TP_L4_00077.Mother TES_L4
TP_L4_00077.Visibility 0

TES_Pixel_L4.Copy TP_L4_00078
TP_L4_00078.Position -8.525 0.775 0
TP_L4_00078.Mother TES_L4
TP_L4_00078.Visibility 0

TES_Pixel_L4.Copy TP_L4_00079
TP_L4_00079.Position -8.525 2.325 0
TP_L4_00079.Mother TES_L4
TP_L4_00079.Visibility 0

TES_Pixel_L4.Copy TP_L4_00080
TP_L4_00080.Position -8.525 3.875 0
TP_L4_00080.Mother TES_L4
TP_L4_00080.Visibility 0

TES_Pixel_L4.Copy TP_L4_00081
TP_L4_00081.Position -8.525 5.425 0
TP_L4_00081.Mother TES_L4
TP_L4_00081.Visibility 0

TES_Pixel_L4.Copy TP_L4_00082
TP_L4_00082.Position -8.525 6.975 0
TP_L4_00082.Mother TES_L4
TP_L4_00082.Visibility 0

TES_Pixel_L4.Copy TP_L4_00083
TP_L4_00083.Position -8.525 8.525 0
TP_L4_00083.Mother TES_L4
TP_L4_00083.Visibility 0

TES_Pixel_L4.Copy TP_L4_00084
TP_L4_00084.Position -8.525 10.075 0
TP_L4_00084.Mother TES_L4
TP_L4_00084.Visibility 0

TES_Pixel_L4.Copy TP_L4_00085
TP_L4_00085.Position -8.525 11.625 0
TP_L4_00085.Mother TES_L4
TP_L4_00085.Visibility 0

TES_Pixel_L4.Copy TP_L4_00086
TP_L4_00086.Position -8.525 13.175 0
TP_L4_00086.Mother TES_L4
TP_L4_00086.Visibility 0

TES_Pixel_L4.Copy TP_L4_00087
TP_L4_00087.Position -8.525 14.725 0
TP_L4_00087.Mother TES_L4
TP_L4_00087.Visibility 0

TES_Pixel_L4.Copy TP_L4_00088
TP_L4_00088.Position -6.975 -14.725 0
TP_L4_00088.Mother TES_L4
TP_L4_00088.Visibility 0

TES_Pixel_L4.Copy TP_L4_00089
TP_L4_00089.Position -6.975 -13.175 0
TP_L4_00089.Mother TES_L4
TP_L4_00089.Visibility 0

TES_Pixel_L4.Copy TP_L4_00090
TP_L4_00090.Position -6.975 -11.625 0
TP_L4_00090.Mother TES_L4
TP_L4_00090.Visibility 0

TES_Pixel_L4.Copy TP_L4_00091
TP_L4_00091.Position -6.975 -10.075 0
TP_L4_00091.Mother TES_L4
TP_L4_00091.Visibility 0

TES_Pixel_L4.Copy TP_L4_00092
TP_L4_00092.Position -6.975 -8.525 0
TP_L4_00092.Mother TES_L4
TP_L4_00092.Visibility 0

TES_Pixel_L4.Copy TP_L4_00093
TP_L4_00093.Position -6.975 -6.975 0
TP_L4_00093.Mother TES_L4
TP_L4_00093.Visibility 0

TES_Pixel_L4.Copy TP_L4_00094
TP_L4_00094.Position -6.975 -5.425 0
TP_L4_00094.Mother TES_L4
TP_L4_00094.Visibility 0

TES_Pixel_L4.Copy TP_L4_00095
TP_L4_00095.Position -6.975 -3.875 0
TP_L4_00095.Mother TES_L4
TP_L4_00095.Visibility 0

TES_Pixel_L4.Copy TP_L4_00096
TP_L4_00096.Position -6.975 -2.325 0
TP_L4_00096.Mother TES_L4
TP_L4_00096.Visibility 0

TES_Pixel_L4.Copy TP_L4_00097
TP_L4_00097.Position -6.975 -0.775 0
TP_L4_00097.Mother TES_L4
TP_L4_00097.Visibility 0

TES_Pixel_L4.Copy TP_L4_00098
TP_L4_00098.Position -6.975 0.775 0
TP_L4_00098.Mother TES_L4
TP_L4_00098.Visibility 0

TES_Pixel_L4.Copy TP_L4_00099
TP_L4_00099.Position -6.975 2.325 0
TP_L4_00099.Mother TES_L4
TP_L4_00099.Visibility 0

TES_Pixel_L4.Copy TP_L4_00100
TP_L4_00100.Position -6.975 3.875 0
TP_L4_00100.Mother TES_L4
TP_L4_00100.Visibility 0

TES_Pixel_L4.Copy TP_L4_00101
TP_L4_00101.Position -6.975 5.425 0
TP_L4_00101.Mother TES_L4
TP_L4_00101.Visibility 0

TES_Pixel_L4.Copy TP_L4_00102
TP_L4_00102.Position -6.975 6.975 0
TP_L4_00102.Mother TES_L4
TP_L4_00102.Visibility 0

TES_Pixel_L4.Copy TP_L4_00103
TP_L4_00103.Position -6.975 8.525 0
TP_L4_00103.Mother TES_L4
TP_L4_00103.Visibility 0

TES_Pixel_L4.Copy TP_L4_00104
TP_L4_00104.Position -6.975 10.075 0
TP_L4_00104.Mother TES_L4
TP_L4_00104.Visibility 0

TES_Pixel_L4.Copy TP_L4_00105
TP_L4_00105.Position -6.975 11.625 0
TP_L4_00105.Mother TES_L4
TP_L4_00105.Visibility 0

TES_Pixel_L4.Copy TP_L4_00106
TP_L4_00106.Position -6.975 13.175 0
TP_L4_00106.Mother TES_L4
TP_L4_00106.Visibility 0

TES_Pixel_L4.Copy TP_L4_00107
TP_L4_00107.Position -6.975 14.725 0
TP_L4_00107.Mother TES_L4
TP_L4_00107.Visibility 0

TES_Pixel_L4.Copy TP_L4_00108
TP_L4_00108.Position -5.425 -14.725 0
TP_L4_00108.Mother TES_L4
TP_L4_00108.Visibility 0

TES_Pixel_L4.Copy TP_L4_00109
TP_L4_00109.Position -5.425 -13.175 0
TP_L4_00109.Mother TES_L4
TP_L4_00109.Visibility 0

TES_Pixel_L4.Copy TP_L4_00110
TP_L4_00110.Position -5.425 -11.625 0
TP_L4_00110.Mother TES_L4
TP_L4_00110.Visibility 0

TES_Pixel_L4.Copy TP_L4_00111
TP_L4_00111.Position -5.425 -10.075 0
TP_L4_00111.Mother TES_L4
TP_L4_00111.Visibility 0

TES_Pixel_L4.Copy TP_L4_00112
TP_L4_00112.Position -5.425 -8.525 0
TP_L4_00112.Mother TES_L4
TP_L4_00112.Visibility 0

TES_Pixel_L4.Copy TP_L4_00113
TP_L4_00113.Position -5.425 -6.975 0
TP_L4_00113.Mother TES_L4
TP_L4_00113.Visibility 0

TES_Pixel_L4.Copy TP_L4_00114
TP_L4_00114.Position -5.425 -5.425 0
TP_L4_00114.Mother TES_L4
TP_L4_00114.Visibility 0

TES_Pixel_L4.Copy TP_L4_00115
TP_L4_00115.Position -5.425 -3.875 0
TP_L4_00115.Mother TES_L4
TP_L4_00115.Visibility 0

TES_Pixel_L4.Copy TP_L4_00116
TP_L4_00116.Position -5.425 -2.325 0
TP_L4_00116.Mother TES_L4
TP_L4_00116.Visibility 0

TES_Pixel_L4.Copy TP_L4_00117
TP_L4_00117.Position -5.425 -0.775 0
TP_L4_00117.Mother TES_L4
TP_L4_00117.Visibility 0

TES_Pixel_L4.Copy TP_L4_00118
TP_L4_00118.Position -5.425 0.775 0
TP_L4_00118.Mother TES_L4
TP_L4_00118.Visibility 0

TES_Pixel_L4.Copy TP_L4_00119
TP_L4_00119.Position -5.425 2.325 0
TP_L4_00119.Mother TES_L4
TP_L4_00119.Visibility 0

TES_Pixel_L4.Copy TP_L4_00120
TP_L4_00120.Position -5.425 3.875 0
TP_L4_00120.Mother TES_L4
TP_L4_00120.Visibility 0

TES_Pixel_L4.Copy TP_L4_00121
TP_L4_00121.Position -5.425 5.425 0
TP_L4_00121.Mother TES_L4
TP_L4_00121.Visibility 0

TES_Pixel_L4.Copy TP_L4_00122
TP_L4_00122.Position -5.425 6.975 0
TP_L4_00122.Mother TES_L4
TP_L4_00122.Visibility 0

TES_Pixel_L4.Copy TP_L4_00123
TP_L4_00123.Position -5.425 8.525 0
TP_L4_00123.Mother TES_L4
TP_L4_00123.Visibility 0

TES_Pixel_L4.Copy TP_L4_00124
TP_L4_00124.Position -5.425 10.075 0
TP_L4_00124.Mother TES_L4
TP_L4_00124.Visibility 0

TES_Pixel_L4.Copy TP_L4_00125
TP_L4_00125.Position -5.425 11.625 0
TP_L4_00125.Mother TES_L4
TP_L4_00125.Visibility 0

TES_Pixel_L4.Copy TP_L4_00126
TP_L4_00126.Position -5.425 13.175 0
TP_L4_00126.Mother TES_L4
TP_L4_00126.Visibility 0

TES_Pixel_L4.Copy TP_L4_00127
TP_L4_00127.Position -5.425 14.725 0
TP_L4_00127.Mother TES_L4
TP_L4_00127.Visibility 0

TES_Pixel_L4.Copy TP_L4_00128
TP_L4_00128.Position -3.875 -14.725 0
TP_L4_00128.Mother TES_L4
TP_L4_00128.Visibility 0

TES_Pixel_L4.Copy TP_L4_00129
TP_L4_00129.Position -3.875 -13.175 0
TP_L4_00129.Mother TES_L4
TP_L4_00129.Visibility 0

TES_Pixel_L4.Copy TP_L4_00130
TP_L4_00130.Position -3.875 -11.625 0
TP_L4_00130.Mother TES_L4
TP_L4_00130.Visibility 0

TES_Pixel_L4.Copy TP_L4_00131
TP_L4_00131.Position -3.875 -10.075 0
TP_L4_00131.Mother TES_L4
TP_L4_00131.Visibility 0

TES_Pixel_L4.Copy TP_L4_00132
TP_L4_00132.Position -3.875 -8.525 0
TP_L4_00132.Mother TES_L4
TP_L4_00132.Visibility 0

TES_Pixel_L4.Copy TP_L4_00133
TP_L4_00133.Position -3.875 -6.975 0
TP_L4_00133.Mother TES_L4
TP_L4_00133.Visibility 0

TES_Pixel_L4.Copy TP_L4_00134
TP_L4_00134.Position -3.875 -5.425 0
TP_L4_00134.Mother TES_L4
TP_L4_00134.Visibility 0

TES_Pixel_L4.Copy TP_L4_00135
TP_L4_00135.Position -3.875 -3.875 0
TP_L4_00135.Mother TES_L4
TP_L4_00135.Visibility 0

TES_Pixel_L4.Copy TP_L4_00136
TP_L4_00136.Position -3.875 -2.325 0
TP_L4_00136.Mother TES_L4
TP_L4_00136.Visibility 0

TES_Pixel_L4.Copy TP_L4_00137
TP_L4_00137.Position -3.875 -0.775 0
TP_L4_00137.Mother TES_L4
TP_L4_00137.Visibility 0

TES_Pixel_L4.Copy TP_L4_00138
TP_L4_00138.Position -3.875 0.775 0
TP_L4_00138.Mother TES_L4
TP_L4_00138.Visibility 0

TES_Pixel_L4.Copy TP_L4_00139
TP_L4_00139.Position -3.875 2.325 0
TP_L4_00139.Mother TES_L4
TP_L4_00139.Visibility 0

TES_Pixel_L4.Copy TP_L4_00140
TP_L4_00140.Position -3.875 3.875 0
TP_L4_00140.Mother TES_L4
TP_L4_00140.Visibility 0

TES_Pixel_L4.Copy TP_L4_00141
TP_L4_00141.Position -3.875 5.425 0
TP_L4_00141.Mother TES_L4
TP_L4_00141.Visibility 0

TES_Pixel_L4.Copy TP_L4_00142
TP_L4_00142.Position -3.875 6.975 0
TP_L4_00142.Mother TES_L4
TP_L4_00142.Visibility 0

TES_Pixel_L4.Copy TP_L4_00143
TP_L4_00143.Position -3.875 8.525 0
TP_L4_00143.Mother TES_L4
TP_L4_00143.Visibility 0

TES_Pixel_L4.Copy TP_L4_00144
TP_L4_00144.Position -3.875 10.075 0
TP_L4_00144.Mother TES_L4
TP_L4_00144.Visibility 0

TES_Pixel_L4.Copy TP_L4_00145
TP_L4_00145.Position -3.875 11.625 0
TP_L4_00145.Mother TES_L4
TP_L4_00145.Visibility 0

TES_Pixel_L4.Copy TP_L4_00146
TP_L4_00146.Position -3.875 13.175 0
TP_L4_00146.Mother TES_L4
TP_L4_00146.Visibility 0

TES_Pixel_L4.Copy TP_L4_00147
TP_L4_00147.Position -3.875 14.725 0
TP_L4_00147.Mother TES_L4
TP_L4_00147.Visibility 0

TES_Pixel_L4.Copy TP_L4_00148
TP_L4_00148.Position -2.325 -14.725 0
TP_L4_00148.Mother TES_L4
TP_L4_00148.Visibility 0

TES_Pixel_L4.Copy TP_L4_00149
TP_L4_00149.Position -2.325 -13.175 0
TP_L4_00149.Mother TES_L4
TP_L4_00149.Visibility 0

TES_Pixel_L4.Copy TP_L4_00150
TP_L4_00150.Position -2.325 -11.625 0
TP_L4_00150.Mother TES_L4
TP_L4_00150.Visibility 0

TES_Pixel_L4.Copy TP_L4_00151
TP_L4_00151.Position -2.325 -10.075 0
TP_L4_00151.Mother TES_L4
TP_L4_00151.Visibility 0

TES_Pixel_L4.Copy TP_L4_00152
TP_L4_00152.Position -2.325 -8.525 0
TP_L4_00152.Mother TES_L4
TP_L4_00152.Visibility 0

TES_Pixel_L4.Copy TP_L4_00153
TP_L4_00153.Position -2.325 -6.975 0
TP_L4_00153.Mother TES_L4
TP_L4_00153.Visibility 0

TES_Pixel_L4.Copy TP_L4_00154
TP_L4_00154.Position -2.325 -5.425 0
TP_L4_00154.Mother TES_L4
TP_L4_00154.Visibility 0

TES_Pixel_L4.Copy TP_L4_00155
TP_L4_00155.Position -2.325 -3.875 0
TP_L4_00155.Mother TES_L4
TP_L4_00155.Visibility 0

TES_Pixel_L4.Copy TP_L4_00156
TP_L4_00156.Position -2.325 -2.325 0
TP_L4_00156.Mother TES_L4
TP_L4_00156.Visibility 0

TES_Pixel_L4.Copy TP_L4_00157
TP_L4_00157.Position -2.325 -0.775 0
TP_L4_00157.Mother TES_L4
TP_L4_00157.Visibility 0

TES_Pixel_L4.Copy TP_L4_00158
TP_L4_00158.Position -2.325 0.775 0
TP_L4_00158.Mother TES_L4
TP_L4_00158.Visibility 0

TES_Pixel_L4.Copy TP_L4_00159
TP_L4_00159.Position -2.325 2.325 0
TP_L4_00159.Mother TES_L4
TP_L4_00159.Visibility 0

TES_Pixel_L4.Copy TP_L4_00160
TP_L4_00160.Position -2.325 3.875 0
TP_L4_00160.Mother TES_L4
TP_L4_00160.Visibility 0

TES_Pixel_L4.Copy TP_L4_00161
TP_L4_00161.Position -2.325 5.425 0
TP_L4_00161.Mother TES_L4
TP_L4_00161.Visibility 0

TES_Pixel_L4.Copy TP_L4_00162
TP_L4_00162.Position -2.325 6.975 0
TP_L4_00162.Mother TES_L4
TP_L4_00162.Visibility 0

TES_Pixel_L4.Copy TP_L4_00163
TP_L4_00163.Position -2.325 8.525 0
TP_L4_00163.Mother TES_L4
TP_L4_00163.Visibility 0

TES_Pixel_L4.Copy TP_L4_00164
TP_L4_00164.Position -2.325 10.075 0
TP_L4_00164.Mother TES_L4
TP_L4_00164.Visibility 0

TES_Pixel_L4.Copy TP_L4_00165
TP_L4_00165.Position -2.325 11.625 0
TP_L4_00165.Mother TES_L4
TP_L4_00165.Visibility 0

TES_Pixel_L4.Copy TP_L4_00166
TP_L4_00166.Position -2.325 13.175 0
TP_L4_00166.Mother TES_L4
TP_L4_00166.Visibility 0

TES_Pixel_L4.Copy TP_L4_00167
TP_L4_00167.Position -2.325 14.725 0
TP_L4_00167.Mother TES_L4
TP_L4_00167.Visibility 0

TES_Pixel_L4.Copy TP_L4_00168
TP_L4_00168.Position -0.775 -14.725 0
TP_L4_00168.Mother TES_L4
TP_L4_00168.Visibility 0

TES_Pixel_L4.Copy TP_L4_00169
TP_L4_00169.Position -0.775 -13.175 0
TP_L4_00169.Mother TES_L4
TP_L4_00169.Visibility 0

TES_Pixel_L4.Copy TP_L4_00170
TP_L4_00170.Position -0.775 -11.625 0
TP_L4_00170.Mother TES_L4
TP_L4_00170.Visibility 0

TES_Pixel_L4.Copy TP_L4_00171
TP_L4_00171.Position -0.775 -10.075 0
TP_L4_00171.Mother TES_L4
TP_L4_00171.Visibility 0

TES_Pixel_L4.Copy TP_L4_00172
TP_L4_00172.Position -0.775 -8.525 0
TP_L4_00172.Mother TES_L4
TP_L4_00172.Visibility 0

TES_Pixel_L4.Copy TP_L4_00173
TP_L4_00173.Position -0.775 -6.975 0
TP_L4_00173.Mother TES_L4
TP_L4_00173.Visibility 0

TES_Pixel_L4.Copy TP_L4_00174
TP_L4_00174.Position -0.775 -5.425 0
TP_L4_00174.Mother TES_L4
TP_L4_00174.Visibility 0

TES_Pixel_L4.Copy TP_L4_00175
TP_L4_00175.Position -0.775 -3.875 0
TP_L4_00175.Mother TES_L4
TP_L4_00175.Visibility 0

TES_Pixel_L4.Copy TP_L4_00176
TP_L4_00176.Position -0.775 -2.325 0
TP_L4_00176.Mother TES_L4
TP_L4_00176.Visibility 0

TES_Pixel_L4.Copy TP_L4_00177
TP_L4_00177.Position -0.775 -0.775 0
TP_L4_00177.Mother TES_L4
TP_L4_00177.Visibility 0

TES_Pixel_L4.Copy TP_L4_00178
TP_L4_00178.Position -0.775 0.775 0
TP_L4_00178.Mother TES_L4
TP_L4_00178.Visibility 0

TES_Pixel_L4.Copy TP_L4_00179
TP_L4_00179.Position -0.775 2.325 0
TP_L4_00179.Mother TES_L4
TP_L4_00179.Visibility 0

TES_Pixel_L4.Copy TP_L4_00180
TP_L4_00180.Position -0.775 3.875 0
TP_L4_00180.Mother TES_L4
TP_L4_00180.Visibility 0

TES_Pixel_L4.Copy TP_L4_00181
TP_L4_00181.Position -0.775 5.425 0
TP_L4_00181.Mother TES_L4
TP_L4_00181.Visibility 0

TES_Pixel_L4.Copy TP_L4_00182
TP_L4_00182.Position -0.775 6.975 0
TP_L4_00182.Mother TES_L4
TP_L4_00182.Visibility 0

TES_Pixel_L4.Copy TP_L4_00183
TP_L4_00183.Position -0.775 8.525 0
TP_L4_00183.Mother TES_L4
TP_L4_00183.Visibility 0

TES_Pixel_L4.Copy TP_L4_00184
TP_L4_00184.Position -0.775 10.075 0
TP_L4_00184.Mother TES_L4
TP_L4_00184.Visibility 0

TES_Pixel_L4.Copy TP_L4_00185
TP_L4_00185.Position -0.775 11.625 0
TP_L4_00185.Mother TES_L4
TP_L4_00185.Visibility 0

TES_Pixel_L4.Copy TP_L4_00186
TP_L4_00186.Position -0.775 13.175 0
TP_L4_00186.Mother TES_L4
TP_L4_00186.Visibility 0

TES_Pixel_L4.Copy TP_L4_00187
TP_L4_00187.Position -0.775 14.725 0
TP_L4_00187.Mother TES_L4
TP_L4_00187.Visibility 0

TES_Pixel_L4.Copy TP_L4_00188
TP_L4_00188.Position 0.775 -14.725 0
TP_L4_00188.Mother TES_L4
TP_L4_00188.Visibility 0

TES_Pixel_L4.Copy TP_L4_00189
TP_L4_00189.Position 0.775 -13.175 0
TP_L4_00189.Mother TES_L4
TP_L4_00189.Visibility 0

TES_Pixel_L4.Copy TP_L4_00190
TP_L4_00190.Position 0.775 -11.625 0
TP_L4_00190.Mother TES_L4
TP_L4_00190.Visibility 0

TES_Pixel_L4.Copy TP_L4_00191
TP_L4_00191.Position 0.775 -10.075 0
TP_L4_00191.Mother TES_L4
TP_L4_00191.Visibility 0

TES_Pixel_L4.Copy TP_L4_00192
TP_L4_00192.Position 0.775 -8.525 0
TP_L4_00192.Mother TES_L4
TP_L4_00192.Visibility 0

TES_Pixel_L4.Copy TP_L4_00193
TP_L4_00193.Position 0.775 -6.975 0
TP_L4_00193.Mother TES_L4
TP_L4_00193.Visibility 0

TES_Pixel_L4.Copy TP_L4_00194
TP_L4_00194.Position 0.775 -5.425 0
TP_L4_00194.Mother TES_L4
TP_L4_00194.Visibility 0

TES_Pixel_L4.Copy TP_L4_00195
TP_L4_00195.Position 0.775 -3.875 0
TP_L4_00195.Mother TES_L4
TP_L4_00195.Visibility 0

TES_Pixel_L4.Copy TP_L4_00196
TP_L4_00196.Position 0.775 -2.325 0
TP_L4_00196.Mother TES_L4
TP_L4_00196.Visibility 0

TES_Pixel_L4.Copy TP_L4_00197
TP_L4_00197.Position 0.775 -0.775 0
TP_L4_00197.Mother TES_L4
TP_L4_00197.Visibility 0

TES_Pixel_L4.Copy TP_L4_00198
TP_L4_00198.Position 0.775 0.775 0
TP_L4_00198.Mother TES_L4
TP_L4_00198.Visibility 0

TES_Pixel_L4.Copy TP_L4_00199
TP_L4_00199.Position 0.775 2.325 0
TP_L4_00199.Mother TES_L4
TP_L4_00199.Visibility 0

TES_Pixel_L4.Copy TP_L4_00200
TP_L4_00200.Position 0.775 3.875 0
TP_L4_00200.Mother TES_L4
TP_L4_00200.Visibility 0

TES_Pixel_L4.Copy TP_L4_00201
TP_L4_00201.Position 0.775 5.425 0
TP_L4_00201.Mother TES_L4
TP_L4_00201.Visibility 0

TES_Pixel_L4.Copy TP_L4_00202
TP_L4_00202.Position 0.775 6.975 0
TP_L4_00202.Mother TES_L4
TP_L4_00202.Visibility 0

TES_Pixel_L4.Copy TP_L4_00203
TP_L4_00203.Position 0.775 8.525 0
TP_L4_00203.Mother TES_L4
TP_L4_00203.Visibility 0

TES_Pixel_L4.Copy TP_L4_00204
TP_L4_00204.Position 0.775 10.075 0
TP_L4_00204.Mother TES_L4
TP_L4_00204.Visibility 0

TES_Pixel_L4.Copy TP_L4_00205
TP_L4_00205.Position 0.775 11.625 0
TP_L4_00205.Mother TES_L4
TP_L4_00205.Visibility 0

TES_Pixel_L4.Copy TP_L4_00206
TP_L4_00206.Position 0.775 13.175 0
TP_L4_00206.Mother TES_L4
TP_L4_00206.Visibility 0

TES_Pixel_L4.Copy TP_L4_00207
TP_L4_00207.Position 0.775 14.725 0
TP_L4_00207.Mother TES_L4
TP_L4_00207.Visibility 0

TES_Pixel_L4.Copy TP_L4_00208
TP_L4_00208.Position 2.325 -14.725 0
TP_L4_00208.Mother TES_L4
TP_L4_00208.Visibility 0

TES_Pixel_L4.Copy TP_L4_00209
TP_L4_00209.Position 2.325 -13.175 0
TP_L4_00209.Mother TES_L4
TP_L4_00209.Visibility 0

TES_Pixel_L4.Copy TP_L4_00210
TP_L4_00210.Position 2.325 -11.625 0
TP_L4_00210.Mother TES_L4
TP_L4_00210.Visibility 0

TES_Pixel_L4.Copy TP_L4_00211
TP_L4_00211.Position 2.325 -10.075 0
TP_L4_00211.Mother TES_L4
TP_L4_00211.Visibility 0

TES_Pixel_L4.Copy TP_L4_00212
TP_L4_00212.Position 2.325 -8.525 0
TP_L4_00212.Mother TES_L4
TP_L4_00212.Visibility 0

TES_Pixel_L4.Copy TP_L4_00213
TP_L4_00213.Position 2.325 -6.975 0
TP_L4_00213.Mother TES_L4
TP_L4_00213.Visibility 0

TES_Pixel_L4.Copy TP_L4_00214
TP_L4_00214.Position 2.325 -5.425 0
TP_L4_00214.Mother TES_L4
TP_L4_00214.Visibility 0

TES_Pixel_L4.Copy TP_L4_00215
TP_L4_00215.Position 2.325 -3.875 0
TP_L4_00215.Mother TES_L4
TP_L4_00215.Visibility 0

TES_Pixel_L4.Copy TP_L4_00216
TP_L4_00216.Position 2.325 -2.325 0
TP_L4_00216.Mother TES_L4
TP_L4_00216.Visibility 0

TES_Pixel_L4.Copy TP_L4_00217
TP_L4_00217.Position 2.325 -0.775 0
TP_L4_00217.Mother TES_L4
TP_L4_00217.Visibility 0

TES_Pixel_L4.Copy TP_L4_00218
TP_L4_00218.Position 2.325 0.775 0
TP_L4_00218.Mother TES_L4
TP_L4_00218.Visibility 0

TES_Pixel_L4.Copy TP_L4_00219
TP_L4_00219.Position 2.325 2.325 0
TP_L4_00219.Mother TES_L4
TP_L4_00219.Visibility 0

TES_Pixel_L4.Copy TP_L4_00220
TP_L4_00220.Position 2.325 3.875 0
TP_L4_00220.Mother TES_L4
TP_L4_00220.Visibility 0

TES_Pixel_L4.Copy TP_L4_00221
TP_L4_00221.Position 2.325 5.425 0
TP_L4_00221.Mother TES_L4
TP_L4_00221.Visibility 0

TES_Pixel_L4.Copy TP_L4_00222
TP_L4_00222.Position 2.325 6.975 0
TP_L4_00222.Mother TES_L4
TP_L4_00222.Visibility 0

TES_Pixel_L4.Copy TP_L4_00223
TP_L4_00223.Position 2.325 8.525 0
TP_L4_00223.Mother TES_L4
TP_L4_00223.Visibility 0

TES_Pixel_L4.Copy TP_L4_00224
TP_L4_00224.Position 2.325 10.075 0
TP_L4_00224.Mother TES_L4
TP_L4_00224.Visibility 0

TES_Pixel_L4.Copy TP_L4_00225
TP_L4_00225.Position 2.325 11.625 0
TP_L4_00225.Mother TES_L4
TP_L4_00225.Visibility 0

TES_Pixel_L4.Copy TP_L4_00226
TP_L4_00226.Position 2.325 13.175 0
TP_L4_00226.Mother TES_L4
TP_L4_00226.Visibility 0

TES_Pixel_L4.Copy TP_L4_00227
TP_L4_00227.Position 2.325 14.725 0
TP_L4_00227.Mother TES_L4
TP_L4_00227.Visibility 0

TES_Pixel_L4.Copy TP_L4_00228
TP_L4_00228.Position 3.875 -14.725 0
TP_L4_00228.Mother TES_L4
TP_L4_00228.Visibility 0

TES_Pixel_L4.Copy TP_L4_00229
TP_L4_00229.Position 3.875 -13.175 0
TP_L4_00229.Mother TES_L4
TP_L4_00229.Visibility 0

TES_Pixel_L4.Copy TP_L4_00230
TP_L4_00230.Position 3.875 -11.625 0
TP_L4_00230.Mother TES_L4
TP_L4_00230.Visibility 0

TES_Pixel_L4.Copy TP_L4_00231
TP_L4_00231.Position 3.875 -10.075 0
TP_L4_00231.Mother TES_L4
TP_L4_00231.Visibility 0

TES_Pixel_L4.Copy TP_L4_00232
TP_L4_00232.Position 3.875 -8.525 0
TP_L4_00232.Mother TES_L4
TP_L4_00232.Visibility 0

TES_Pixel_L4.Copy TP_L4_00233
TP_L4_00233.Position 3.875 -6.975 0
TP_L4_00233.Mother TES_L4
TP_L4_00233.Visibility 0

TES_Pixel_L4.Copy TP_L4_00234
TP_L4_00234.Position 3.875 -5.425 0
TP_L4_00234.Mother TES_L4
TP_L4_00234.Visibility 0

TES_Pixel_L4.Copy TP_L4_00235
TP_L4_00235.Position 3.875 -3.875 0
TP_L4_00235.Mother TES_L4
TP_L4_00235.Visibility 0

TES_Pixel_L4.Copy TP_L4_00236
TP_L4_00236.Position 3.875 -2.325 0
TP_L4_00236.Mother TES_L4
TP_L4_00236.Visibility 0

TES_Pixel_L4.Copy TP_L4_00237
TP_L4_00237.Position 3.875 -0.775 0
TP_L4_00237.Mother TES_L4
TP_L4_00237.Visibility 0

TES_Pixel_L4.Copy TP_L4_00238
TP_L4_00238.Position 3.875 0.775 0
TP_L4_00238.Mother TES_L4
TP_L4_00238.Visibility 0

TES_Pixel_L4.Copy TP_L4_00239
TP_L4_00239.Position 3.875 2.325 0
TP_L4_00239.Mother TES_L4
TP_L4_00239.Visibility 0

TES_Pixel_L4.Copy TP_L4_00240
TP_L4_00240.Position 3.875 3.875 0
TP_L4_00240.Mother TES_L4
TP_L4_00240.Visibility 0

TES_Pixel_L4.Copy TP_L4_00241
TP_L4_00241.Position 3.875 5.425 0
TP_L4_00241.Mother TES_L4
TP_L4_00241.Visibility 0

TES_Pixel_L4.Copy TP_L4_00242
TP_L4_00242.Position 3.875 6.975 0
TP_L4_00242.Mother TES_L4
TP_L4_00242.Visibility 0

TES_Pixel_L4.Copy TP_L4_00243
TP_L4_00243.Position 3.875 8.525 0
TP_L4_00243.Mother TES_L4
TP_L4_00243.Visibility 0

TES_Pixel_L4.Copy TP_L4_00244
TP_L4_00244.Position 3.875 10.075 0
TP_L4_00244.Mother TES_L4
TP_L4_00244.Visibility 0

TES_Pixel_L4.Copy TP_L4_00245
TP_L4_00245.Position 3.875 11.625 0
TP_L4_00245.Mother TES_L4
TP_L4_00245.Visibility 0

TES_Pixel_L4.Copy TP_L4_00246
TP_L4_00246.Position 3.875 13.175 0
TP_L4_00246.Mother TES_L4
TP_L4_00246.Visibility 0

TES_Pixel_L4.Copy TP_L4_00247
TP_L4_00247.Position 3.875 14.725 0
TP_L4_00247.Mother TES_L4
TP_L4_00247.Visibility 0

TES_Pixel_L4.Copy TP_L4_00248
TP_L4_00248.Position 5.425 -14.725 0
TP_L4_00248.Mother TES_L4
TP_L4_00248.Visibility 0

TES_Pixel_L4.Copy TP_L4_00249
TP_L4_00249.Position 5.425 -13.175 0
TP_L4_00249.Mother TES_L4
TP_L4_00249.Visibility 0

TES_Pixel_L4.Copy TP_L4_00250
TP_L4_00250.Position 5.425 -11.625 0
TP_L4_00250.Mother TES_L4
TP_L4_00250.Visibility 0

TES_Pixel_L4.Copy TP_L4_00251
TP_L4_00251.Position 5.425 -10.075 0
TP_L4_00251.Mother TES_L4
TP_L4_00251.Visibility 0

TES_Pixel_L4.Copy TP_L4_00252
TP_L4_00252.Position 5.425 -8.525 0
TP_L4_00252.Mother TES_L4
TP_L4_00252.Visibility 0

TES_Pixel_L4.Copy TP_L4_00253
TP_L4_00253.Position 5.425 -6.975 0
TP_L4_00253.Mother TES_L4
TP_L4_00253.Visibility 0

TES_Pixel_L4.Copy TP_L4_00254
TP_L4_00254.Position 5.425 -5.425 0
TP_L4_00254.Mother TES_L4
TP_L4_00254.Visibility 0

TES_Pixel_L4.Copy TP_L4_00255
TP_L4_00255.Position 5.425 -3.875 0
TP_L4_00255.Mother TES_L4
TP_L4_00255.Visibility 0

TES_Pixel_L4.Copy TP_L4_00256
TP_L4_00256.Position 5.425 -2.325 0
TP_L4_00256.Mother TES_L4
TP_L4_00256.Visibility 0

TES_Pixel_L4.Copy TP_L4_00257
TP_L4_00257.Position 5.425 -0.775 0
TP_L4_00257.Mother TES_L4
TP_L4_00257.Visibility 0

TES_Pixel_L4.Copy TP_L4_00258
TP_L4_00258.Position 5.425 0.775 0
TP_L4_00258.Mother TES_L4
TP_L4_00258.Visibility 0

TES_Pixel_L4.Copy TP_L4_00259
TP_L4_00259.Position 5.425 2.325 0
TP_L4_00259.Mother TES_L4
TP_L4_00259.Visibility 0

TES_Pixel_L4.Copy TP_L4_00260
TP_L4_00260.Position 5.425 3.875 0
TP_L4_00260.Mother TES_L4
TP_L4_00260.Visibility 0

TES_Pixel_L4.Copy TP_L4_00261
TP_L4_00261.Position 5.425 5.425 0
TP_L4_00261.Mother TES_L4
TP_L4_00261.Visibility 0

TES_Pixel_L4.Copy TP_L4_00262
TP_L4_00262.Position 5.425 6.975 0
TP_L4_00262.Mother TES_L4
TP_L4_00262.Visibility 0

TES_Pixel_L4.Copy TP_L4_00263
TP_L4_00263.Position 5.425 8.525 0
TP_L4_00263.Mother TES_L4
TP_L4_00263.Visibility 0

TES_Pixel_L4.Copy TP_L4_00264
TP_L4_00264.Position 5.425 10.075 0
TP_L4_00264.Mother TES_L4
TP_L4_00264.Visibility 0

TES_Pixel_L4.Copy TP_L4_00265
TP_L4_00265.Position 5.425 11.625 0
TP_L4_00265.Mother TES_L4
TP_L4_00265.Visibility 0

TES_Pixel_L4.Copy TP_L4_00266
TP_L4_00266.Position 5.425 13.175 0
TP_L4_00266.Mother TES_L4
TP_L4_00266.Visibility 0

TES_Pixel_L4.Copy TP_L4_00267
TP_L4_00267.Position 5.425 14.725 0
TP_L4_00267.Mother TES_L4
TP_L4_00267.Visibility 0

TES_Pixel_L4.Copy TP_L4_00268
TP_L4_00268.Position 6.975 -14.725 0
TP_L4_00268.Mother TES_L4
TP_L4_00268.Visibility 0

TES_Pixel_L4.Copy TP_L4_00269
TP_L4_00269.Position 6.975 -13.175 0
TP_L4_00269.Mother TES_L4
TP_L4_00269.Visibility 0

TES_Pixel_L4.Copy TP_L4_00270
TP_L4_00270.Position 6.975 -11.625 0
TP_L4_00270.Mother TES_L4
TP_L4_00270.Visibility 0

TES_Pixel_L4.Copy TP_L4_00271
TP_L4_00271.Position 6.975 -10.075 0
TP_L4_00271.Mother TES_L4
TP_L4_00271.Visibility 0

TES_Pixel_L4.Copy TP_L4_00272
TP_L4_00272.Position 6.975 -8.525 0
TP_L4_00272.Mother TES_L4
TP_L4_00272.Visibility 0

TES_Pixel_L4.Copy TP_L4_00273
TP_L4_00273.Position 6.975 -6.975 0
TP_L4_00273.Mother TES_L4
TP_L4_00273.Visibility 0

TES_Pixel_L4.Copy TP_L4_00274
TP_L4_00274.Position 6.975 -5.425 0
TP_L4_00274.Mother TES_L4
TP_L4_00274.Visibility 0

TES_Pixel_L4.Copy TP_L4_00275
TP_L4_00275.Position 6.975 -3.875 0
TP_L4_00275.Mother TES_L4
TP_L4_00275.Visibility 0

TES_Pixel_L4.Copy TP_L4_00276
TP_L4_00276.Position 6.975 -2.325 0
TP_L4_00276.Mother TES_L4
TP_L4_00276.Visibility 0

TES_Pixel_L4.Copy TP_L4_00277
TP_L4_00277.Position 6.975 -0.775 0
TP_L4_00277.Mother TES_L4
TP_L4_00277.Visibility 0

TES_Pixel_L4.Copy TP_L4_00278
TP_L4_00278.Position 6.975 0.775 0
TP_L4_00278.Mother TES_L4
TP_L4_00278.Visibility 0

TES_Pixel_L4.Copy TP_L4_00279
TP_L4_00279.Position 6.975 2.325 0
TP_L4_00279.Mother TES_L4
TP_L4_00279.Visibility 0

TES_Pixel_L4.Copy TP_L4_00280
TP_L4_00280.Position 6.975 3.875 0
TP_L4_00280.Mother TES_L4
TP_L4_00280.Visibility 0

TES_Pixel_L4.Copy TP_L4_00281
TP_L4_00281.Position 6.975 5.425 0
TP_L4_00281.Mother TES_L4
TP_L4_00281.Visibility 0

TES_Pixel_L4.Copy TP_L4_00282
TP_L4_00282.Position 6.975 6.975 0
TP_L4_00282.Mother TES_L4
TP_L4_00282.Visibility 0

TES_Pixel_L4.Copy TP_L4_00283
TP_L4_00283.Position 6.975 8.525 0
TP_L4_00283.Mother TES_L4
TP_L4_00283.Visibility 0

TES_Pixel_L4.Copy TP_L4_00284
TP_L4_00284.Position 6.975 10.075 0
TP_L4_00284.Mother TES_L4
TP_L4_00284.Visibility 0

TES_Pixel_L4.Copy TP_L4_00285
TP_L4_00285.Position 6.975 11.625 0
TP_L4_00285.Mother TES_L4
TP_L4_00285.Visibility 0

TES_Pixel_L4.Copy TP_L4_00286
TP_L4_00286.Position 6.975 13.175 0
TP_L4_00286.Mother TES_L4
TP_L4_00286.Visibility 0

TES_Pixel_L4.Copy TP_L4_00287
TP_L4_00287.Position 6.975 14.725 0
TP_L4_00287.Mother TES_L4
TP_L4_00287.Visibility 0

TES_Pixel_L4.Copy TP_L4_00288
TP_L4_00288.Position 8.525 -14.725 0
TP_L4_00288.Mother TES_L4
TP_L4_00288.Visibility 0

TES_Pixel_L4.Copy TP_L4_00289
TP_L4_00289.Position 8.525 -13.175 0
TP_L4_00289.Mother TES_L4
TP_L4_00289.Visibility 0

TES_Pixel_L4.Copy TP_L4_00290
TP_L4_00290.Position 8.525 -11.625 0
TP_L4_00290.Mother TES_L4
TP_L4_00290.Visibility 0

TES_Pixel_L4.Copy TP_L4_00291
TP_L4_00291.Position 8.525 -10.075 0
TP_L4_00291.Mother TES_L4
TP_L4_00291.Visibility 0

TES_Pixel_L4.Copy TP_L4_00292
TP_L4_00292.Position 8.525 -8.525 0
TP_L4_00292.Mother TES_L4
TP_L4_00292.Visibility 0

TES_Pixel_L4.Copy TP_L4_00293
TP_L4_00293.Position 8.525 -6.975 0
TP_L4_00293.Mother TES_L4
TP_L4_00293.Visibility 0

TES_Pixel_L4.Copy TP_L4_00294
TP_L4_00294.Position 8.525 -5.425 0
TP_L4_00294.Mother TES_L4
TP_L4_00294.Visibility 0

TES_Pixel_L4.Copy TP_L4_00295
TP_L4_00295.Position 8.525 -3.875 0
TP_L4_00295.Mother TES_L4
TP_L4_00295.Visibility 0

TES_Pixel_L4.Copy TP_L4_00296
TP_L4_00296.Position 8.525 -2.325 0
TP_L4_00296.Mother TES_L4
TP_L4_00296.Visibility 0

TES_Pixel_L4.Copy TP_L4_00297
TP_L4_00297.Position 8.525 -0.775 0
TP_L4_00297.Mother TES_L4
TP_L4_00297.Visibility 0

TES_Pixel_L4.Copy TP_L4_00298
TP_L4_00298.Position 8.525 0.775 0
TP_L4_00298.Mother TES_L4
TP_L4_00298.Visibility 0

TES_Pixel_L4.Copy TP_L4_00299
TP_L4_00299.Position 8.525 2.325 0
TP_L4_00299.Mother TES_L4
TP_L4_00299.Visibility 0

TES_Pixel_L4.Copy TP_L4_00300
TP_L4_00300.Position 8.525 3.875 0
TP_L4_00300.Mother TES_L4
TP_L4_00300.Visibility 0

TES_Pixel_L4.Copy TP_L4_00301
TP_L4_00301.Position 8.525 5.425 0
TP_L4_00301.Mother TES_L4
TP_L4_00301.Visibility 0

TES_Pixel_L4.Copy TP_L4_00302
TP_L4_00302.Position 8.525 6.975 0
TP_L4_00302.Mother TES_L4
TP_L4_00302.Visibility 0

TES_Pixel_L4.Copy TP_L4_00303
TP_L4_00303.Position 8.525 8.525 0
TP_L4_00303.Mother TES_L4
TP_L4_00303.Visibility 0

TES_Pixel_L4.Copy TP_L4_00304
TP_L4_00304.Position 8.525 10.075 0
TP_L4_00304.Mother TES_L4
TP_L4_00304.Visibility 0

TES_Pixel_L4.Copy TP_L4_00305
TP_L4_00305.Position 8.525 11.625 0
TP_L4_00305.Mother TES_L4
TP_L4_00305.Visibility 0

TES_Pixel_L4.Copy TP_L4_00306
TP_L4_00306.Position 8.525 13.175 0
TP_L4_00306.Mother TES_L4
TP_L4_00306.Visibility 0

TES_Pixel_L4.Copy TP_L4_00307
TP_L4_00307.Position 8.525 14.725 0
TP_L4_00307.Mother TES_L4
TP_L4_00307.Visibility 0

TES_Pixel_L4.Copy TP_L4_00308
TP_L4_00308.Position 10.075 -14.725 0
TP_L4_00308.Mother TES_L4
TP_L4_00308.Visibility 0

TES_Pixel_L4.Copy TP_L4_00309
TP_L4_00309.Position 10.075 -13.175 0
TP_L4_00309.Mother TES_L4
TP_L4_00309.Visibility 0

TES_Pixel_L4.Copy TP_L4_00310
TP_L4_00310.Position 10.075 -11.625 0
TP_L4_00310.Mother TES_L4
TP_L4_00310.Visibility 0

TES_Pixel_L4.Copy TP_L4_00311
TP_L4_00311.Position 10.075 -10.075 0
TP_L4_00311.Mother TES_L4
TP_L4_00311.Visibility 0

TES_Pixel_L4.Copy TP_L4_00312
TP_L4_00312.Position 10.075 -8.525 0
TP_L4_00312.Mother TES_L4
TP_L4_00312.Visibility 0

TES_Pixel_L4.Copy TP_L4_00313
TP_L4_00313.Position 10.075 -6.975 0
TP_L4_00313.Mother TES_L4
TP_L4_00313.Visibility 0

TES_Pixel_L4.Copy TP_L4_00314
TP_L4_00314.Position 10.075 -5.425 0
TP_L4_00314.Mother TES_L4
TP_L4_00314.Visibility 0

TES_Pixel_L4.Copy TP_L4_00315
TP_L4_00315.Position 10.075 -3.875 0
TP_L4_00315.Mother TES_L4
TP_L4_00315.Visibility 0

TES_Pixel_L4.Copy TP_L4_00316
TP_L4_00316.Position 10.075 -2.325 0
TP_L4_00316.Mother TES_L4
TP_L4_00316.Visibility 0

TES_Pixel_L4.Copy TP_L4_00317
TP_L4_00317.Position 10.075 -0.775 0
TP_L4_00317.Mother TES_L4
TP_L4_00317.Visibility 0

TES_Pixel_L4.Copy TP_L4_00318
TP_L4_00318.Position 10.075 0.775 0
TP_L4_00318.Mother TES_L4
TP_L4_00318.Visibility 0

TES_Pixel_L4.Copy TP_L4_00319
TP_L4_00319.Position 10.075 2.325 0
TP_L4_00319.Mother TES_L4
TP_L4_00319.Visibility 0

TES_Pixel_L4.Copy TP_L4_00320
TP_L4_00320.Position 10.075 3.875 0
TP_L4_00320.Mother TES_L4
TP_L4_00320.Visibility 0

TES_Pixel_L4.Copy TP_L4_00321
TP_L4_00321.Position 10.075 5.425 0
TP_L4_00321.Mother TES_L4
TP_L4_00321.Visibility 0

TES_Pixel_L4.Copy TP_L4_00322
TP_L4_00322.Position 10.075 6.975 0
TP_L4_00322.Mother TES_L4
TP_L4_00322.Visibility 0

TES_Pixel_L4.Copy TP_L4_00323
TP_L4_00323.Position 10.075 8.525 0
TP_L4_00323.Mother TES_L4
TP_L4_00323.Visibility 0

TES_Pixel_L4.Copy TP_L4_00324
TP_L4_00324.Position 10.075 10.075 0
TP_L4_00324.Mother TES_L4
TP_L4_00324.Visibility 0

TES_Pixel_L4.Copy TP_L4_00325
TP_L4_00325.Position 10.075 11.625 0
TP_L4_00325.Mother TES_L4
TP_L4_00325.Visibility 0

TES_Pixel_L4.Copy TP_L4_00326
TP_L4_00326.Position 10.075 13.175 0
TP_L4_00326.Mother TES_L4
TP_L4_00326.Visibility 0

TES_Pixel_L4.Copy TP_L4_00327
TP_L4_00327.Position 10.075 14.725 0
TP_L4_00327.Mother TES_L4
TP_L4_00327.Visibility 0

TES_Pixel_L4.Copy TP_L4_00328
TP_L4_00328.Position 11.625 -13.175 0
TP_L4_00328.Mother TES_L4
TP_L4_00328.Visibility 0

TES_Pixel_L4.Copy TP_L4_00329
TP_L4_00329.Position 11.625 -11.625 0
TP_L4_00329.Mother TES_L4
TP_L4_00329.Visibility 0

TES_Pixel_L4.Copy TP_L4_00330
TP_L4_00330.Position 11.625 -10.075 0
TP_L4_00330.Mother TES_L4
TP_L4_00330.Visibility 0

TES_Pixel_L4.Copy TP_L4_00331
TP_L4_00331.Position 11.625 -8.525 0
TP_L4_00331.Mother TES_L4
TP_L4_00331.Visibility 0

TES_Pixel_L4.Copy TP_L4_00332
TP_L4_00332.Position 11.625 -6.975 0
TP_L4_00332.Mother TES_L4
TP_L4_00332.Visibility 0

TES_Pixel_L4.Copy TP_L4_00333
TP_L4_00333.Position 11.625 -5.425 0
TP_L4_00333.Mother TES_L4
TP_L4_00333.Visibility 0

TES_Pixel_L4.Copy TP_L4_00334
TP_L4_00334.Position 11.625 -3.875 0
TP_L4_00334.Mother TES_L4
TP_L4_00334.Visibility 0

TES_Pixel_L4.Copy TP_L4_00335
TP_L4_00335.Position 11.625 -2.325 0
TP_L4_00335.Mother TES_L4
TP_L4_00335.Visibility 0

TES_Pixel_L4.Copy TP_L4_00336
TP_L4_00336.Position 11.625 -0.775 0
TP_L4_00336.Mother TES_L4
TP_L4_00336.Visibility 0

TES_Pixel_L4.Copy TP_L4_00337
TP_L4_00337.Position 11.625 0.775 0
TP_L4_00337.Mother TES_L4
TP_L4_00337.Visibility 0

TES_Pixel_L4.Copy TP_L4_00338
TP_L4_00338.Position 11.625 2.325 0
TP_L4_00338.Mother TES_L4
TP_L4_00338.Visibility 0

TES_Pixel_L4.Copy TP_L4_00339
TP_L4_00339.Position 11.625 3.875 0
TP_L4_00339.Mother TES_L4
TP_L4_00339.Visibility 0

TES_Pixel_L4.Copy TP_L4_00340
TP_L4_00340.Position 11.625 5.425 0
TP_L4_00340.Mother TES_L4
TP_L4_00340.Visibility 0

TES_Pixel_L4.Copy TP_L4_00341
TP_L4_00341.Position 11.625 6.975 0
TP_L4_00341.Mother TES_L4
TP_L4_00341.Visibility 0

TES_Pixel_L4.Copy TP_L4_00342
TP_L4_00342.Position 11.625 8.525 0
TP_L4_00342.Mother TES_L4
TP_L4_00342.Visibility 0

TES_Pixel_L4.Copy TP_L4_00343
TP_L4_00343.Position 11.625 10.075 0
TP_L4_00343.Mother TES_L4
TP_L4_00343.Visibility 0

TES_Pixel_L4.Copy TP_L4_00344
TP_L4_00344.Position 11.625 11.625 0
TP_L4_00344.Mother TES_L4
TP_L4_00344.Visibility 0

TES_Pixel_L4.Copy TP_L4_00345
TP_L4_00345.Position 11.625 13.175 0
TP_L4_00345.Mother TES_L4
TP_L4_00345.Visibility 0

TES_Pixel_L4.Copy TP_L4_00346
TP_L4_00346.Position 13.175 -11.625 0
TP_L4_00346.Mother TES_L4
TP_L4_00346.Visibility 0

TES_Pixel_L4.Copy TP_L4_00347
TP_L4_00347.Position 13.175 -10.075 0
TP_L4_00347.Mother TES_L4
TP_L4_00347.Visibility 0

TES_Pixel_L4.Copy TP_L4_00348
TP_L4_00348.Position 13.175 -8.525 0
TP_L4_00348.Mother TES_L4
TP_L4_00348.Visibility 0

TES_Pixel_L4.Copy TP_L4_00349
TP_L4_00349.Position 13.175 -6.975 0
TP_L4_00349.Mother TES_L4
TP_L4_00349.Visibility 0

TES_Pixel_L4.Copy TP_L4_00350
TP_L4_00350.Position 13.175 -5.425 0
TP_L4_00350.Mother TES_L4
TP_L4_00350.Visibility 0

TES_Pixel_L4.Copy TP_L4_00351
TP_L4_00351.Position 13.175 -3.875 0
TP_L4_00351.Mother TES_L4
TP_L4_00351.Visibility 0

TES_Pixel_L4.Copy TP_L4_00352
TP_L4_00352.Position 13.175 -2.325 0
TP_L4_00352.Mother TES_L4
TP_L4_00352.Visibility 0

TES_Pixel_L4.Copy TP_L4_00353
TP_L4_00353.Position 13.175 -0.775 0
TP_L4_00353.Mother TES_L4
TP_L4_00353.Visibility 0

TES_Pixel_L4.Copy TP_L4_00354
TP_L4_00354.Position 13.175 0.775 0
TP_L4_00354.Mother TES_L4
TP_L4_00354.Visibility 0

TES_Pixel_L4.Copy TP_L4_00355
TP_L4_00355.Position 13.175 2.325 0
TP_L4_00355.Mother TES_L4
TP_L4_00355.Visibility 0

TES_Pixel_L4.Copy TP_L4_00356
TP_L4_00356.Position 13.175 3.875 0
TP_L4_00356.Mother TES_L4
TP_L4_00356.Visibility 0

TES_Pixel_L4.Copy TP_L4_00357
TP_L4_00357.Position 13.175 5.425 0
TP_L4_00357.Mother TES_L4
TP_L4_00357.Visibility 0

TES_Pixel_L4.Copy TP_L4_00358
TP_L4_00358.Position 13.175 6.975 0
TP_L4_00358.Mother TES_L4
TP_L4_00358.Visibility 0

TES_Pixel_L4.Copy TP_L4_00359
TP_L4_00359.Position 13.175 8.525 0
TP_L4_00359.Mother TES_L4
TP_L4_00359.Visibility 0

TES_Pixel_L4.Copy TP_L4_00360
TP_L4_00360.Position 13.175 10.075 0
TP_L4_00360.Mother TES_L4
TP_L4_00360.Visibility 0

TES_Pixel_L4.Copy TP_L4_00361
TP_L4_00361.Position 13.175 11.625 0
TP_L4_00361.Mother TES_L4
TP_L4_00361.Visibility 0

TES_Pixel_L4.Copy TP_L4_00362
TP_L4_00362.Position 14.725 -10.075 0
TP_L4_00362.Mother TES_L4
TP_L4_00362.Visibility 0

TES_Pixel_L4.Copy TP_L4_00363
TP_L4_00363.Position 14.725 -8.525 0
TP_L4_00363.Mother TES_L4
TP_L4_00363.Visibility 0

TES_Pixel_L4.Copy TP_L4_00364
TP_L4_00364.Position 14.725 -6.975 0
TP_L4_00364.Mother TES_L4
TP_L4_00364.Visibility 0

TES_Pixel_L4.Copy TP_L4_00365
TP_L4_00365.Position 14.725 -5.425 0
TP_L4_00365.Mother TES_L4
TP_L4_00365.Visibility 0

TES_Pixel_L4.Copy TP_L4_00366
TP_L4_00366.Position 14.725 -3.875 0
TP_L4_00366.Mother TES_L4
TP_L4_00366.Visibility 0

TES_Pixel_L4.Copy TP_L4_00367
TP_L4_00367.Position 14.725 -2.325 0
TP_L4_00367.Mother TES_L4
TP_L4_00367.Visibility 0

TES_Pixel_L4.Copy TP_L4_00368
TP_L4_00368.Position 14.725 -0.775 0
TP_L4_00368.Mother TES_L4
TP_L4_00368.Visibility 0

TES_Pixel_L4.Copy TP_L4_00369
TP_L4_00369.Position 14.725 0.775 0
TP_L4_00369.Mother TES_L4
TP_L4_00369.Visibility 0

TES_Pixel_L4.Copy TP_L4_00370
TP_L4_00370.Position 14.725 2.325 0
TP_L4_00370.Mother TES_L4
TP_L4_00370.Visibility 0

TES_Pixel_L4.Copy TP_L4_00371
TP_L4_00371.Position 14.725 3.875 0
TP_L4_00371.Mother TES_L4
TP_L4_00371.Visibility 0

TES_Pixel_L4.Copy TP_L4_00372
TP_L4_00372.Position 14.725 5.425 0
TP_L4_00372.Mother TES_L4
TP_L4_00372.Visibility 0

TES_Pixel_L4.Copy TP_L4_00373
TP_L4_00373.Position 14.725 6.975 0
TP_L4_00373.Mother TES_L4
TP_L4_00373.Visibility 0

TES_Pixel_L4.Copy TP_L4_00374
TP_L4_00374.Position 14.725 8.525 0
TP_L4_00374.Mother TES_L4
TP_L4_00374.Visibility 0

TES_Pixel_L4.Copy TP_L4_00375
TP_L4_00375.Position 14.725 10.075 0
TP_L4_00375.Mother TES_L4
TP_L4_00375.Visibility 0

Substrate_L5.Position 0 0 70
Substrate_L5.Mother WorldVolume

TES_L5.Position 0 0 71.65
TES_L5.Mother WorldVolume
TES_L5.Visibility 0

TES_Pixel_L5.Copy TP_L5_00000
TP_L5_00000.Position -14.725 -10.075 0
TP_L5_00000.Mother TES_L5
TP_L5_00000.Visibility 0

TES_Pixel_L5.Copy TP_L5_00001
TP_L5_00001.Position -14.725 -8.525 0
TP_L5_00001.Mother TES_L5
TP_L5_00001.Visibility 0

TES_Pixel_L5.Copy TP_L5_00002
TP_L5_00002.Position -14.725 -6.975 0
TP_L5_00002.Mother TES_L5
TP_L5_00002.Visibility 0

TES_Pixel_L5.Copy TP_L5_00003
TP_L5_00003.Position -14.725 -5.425 0
TP_L5_00003.Mother TES_L5
TP_L5_00003.Visibility 0

TES_Pixel_L5.Copy TP_L5_00004
TP_L5_00004.Position -14.725 -3.875 0
TP_L5_00004.Mother TES_L5
TP_L5_00004.Visibility 0

TES_Pixel_L5.Copy TP_L5_00005
TP_L5_00005.Position -14.725 -2.325 0
TP_L5_00005.Mother TES_L5
TP_L5_00005.Visibility 0

TES_Pixel_L5.Copy TP_L5_00006
TP_L5_00006.Position -14.725 -0.775 0
TP_L5_00006.Mother TES_L5
TP_L5_00006.Visibility 0

TES_Pixel_L5.Copy TP_L5_00007
TP_L5_00007.Position -14.725 0.775 0
TP_L5_00007.Mother TES_L5
TP_L5_00007.Visibility 0

TES_Pixel_L5.Copy TP_L5_00008
TP_L5_00008.Position -14.725 2.325 0
TP_L5_00008.Mother TES_L5
TP_L5_00008.Visibility 0

TES_Pixel_L5.Copy TP_L5_00009
TP_L5_00009.Position -14.725 3.875 0
TP_L5_00009.Mother TES_L5
TP_L5_00009.Visibility 0

TES_Pixel_L5.Copy TP_L5_00010
TP_L5_00010.Position -14.725 5.425 0
TP_L5_00010.Mother TES_L5
TP_L5_00010.Visibility 0

TES_Pixel_L5.Copy TP_L5_00011
TP_L5_00011.Position -14.725 6.975 0
TP_L5_00011.Mother TES_L5
TP_L5_00011.Visibility 0

TES_Pixel_L5.Copy TP_L5_00012
TP_L5_00012.Position -14.725 8.525 0
TP_L5_00012.Mother TES_L5
TP_L5_00012.Visibility 0

TES_Pixel_L5.Copy TP_L5_00013
TP_L5_00013.Position -14.725 10.075 0
TP_L5_00013.Mother TES_L5
TP_L5_00013.Visibility 0

TES_Pixel_L5.Copy TP_L5_00014
TP_L5_00014.Position -13.175 -11.625 0
TP_L5_00014.Mother TES_L5
TP_L5_00014.Visibility 0

TES_Pixel_L5.Copy TP_L5_00015
TP_L5_00015.Position -13.175 -10.075 0
TP_L5_00015.Mother TES_L5
TP_L5_00015.Visibility 0

TES_Pixel_L5.Copy TP_L5_00016
TP_L5_00016.Position -13.175 -8.525 0
TP_L5_00016.Mother TES_L5
TP_L5_00016.Visibility 0

TES_Pixel_L5.Copy TP_L5_00017
TP_L5_00017.Position -13.175 -6.975 0
TP_L5_00017.Mother TES_L5
TP_L5_00017.Visibility 0

TES_Pixel_L5.Copy TP_L5_00018
TP_L5_00018.Position -13.175 -5.425 0
TP_L5_00018.Mother TES_L5
TP_L5_00018.Visibility 0

TES_Pixel_L5.Copy TP_L5_00019
TP_L5_00019.Position -13.175 -3.875 0
TP_L5_00019.Mother TES_L5
TP_L5_00019.Visibility 0

TES_Pixel_L5.Copy TP_L5_00020
TP_L5_00020.Position -13.175 -2.325 0
TP_L5_00020.Mother TES_L5
TP_L5_00020.Visibility 0

TES_Pixel_L5.Copy TP_L5_00021
TP_L5_00021.Position -13.175 -0.775 0
TP_L5_00021.Mother TES_L5
TP_L5_00021.Visibility 0

TES_Pixel_L5.Copy TP_L5_00022
TP_L5_00022.Position -13.175 0.775 0
TP_L5_00022.Mother TES_L5
TP_L5_00022.Visibility 0

TES_Pixel_L5.Copy TP_L5_00023
TP_L5_00023.Position -13.175 2.325 0
TP_L5_00023.Mother TES_L5
TP_L5_00023.Visibility 0

TES_Pixel_L5.Copy TP_L5_00024
TP_L5_00024.Position -13.175 3.875 0
TP_L5_00024.Mother TES_L5
TP_L5_00024.Visibility 0

TES_Pixel_L5.Copy TP_L5_00025
TP_L5_00025.Position -13.175 5.425 0
TP_L5_00025.Mother TES_L5
TP_L5_00025.Visibility 0

TES_Pixel_L5.Copy TP_L5_00026
TP_L5_00026.Position -13.175 6.975 0
TP_L5_00026.Mother TES_L5
TP_L5_00026.Visibility 0

TES_Pixel_L5.Copy TP_L5_00027
TP_L5_00027.Position -13.175 8.525 0
TP_L5_00027.Mother TES_L5
TP_L5_00027.Visibility 0

TES_Pixel_L5.Copy TP_L5_00028
TP_L5_00028.Position -13.175 10.075 0
TP_L5_00028.Mother TES_L5
TP_L5_00028.Visibility 0

TES_Pixel_L5.Copy TP_L5_00029
TP_L5_00029.Position -13.175 11.625 0
TP_L5_00029.Mother TES_L5
TP_L5_00029.Visibility 0

TES_Pixel_L5.Copy TP_L5_00030
TP_L5_00030.Position -11.625 -13.175 0
TP_L5_00030.Mother TES_L5
TP_L5_00030.Visibility 0

TES_Pixel_L5.Copy TP_L5_00031
TP_L5_00031.Position -11.625 -11.625 0
TP_L5_00031.Mother TES_L5
TP_L5_00031.Visibility 0

TES_Pixel_L5.Copy TP_L5_00032
TP_L5_00032.Position -11.625 -10.075 0
TP_L5_00032.Mother TES_L5
TP_L5_00032.Visibility 0

TES_Pixel_L5.Copy TP_L5_00033
TP_L5_00033.Position -11.625 -8.525 0
TP_L5_00033.Mother TES_L5
TP_L5_00033.Visibility 0

TES_Pixel_L5.Copy TP_L5_00034
TP_L5_00034.Position -11.625 -6.975 0
TP_L5_00034.Mother TES_L5
TP_L5_00034.Visibility 0

TES_Pixel_L5.Copy TP_L5_00035
TP_L5_00035.Position -11.625 -5.425 0
TP_L5_00035.Mother TES_L5
TP_L5_00035.Visibility 0

TES_Pixel_L5.Copy TP_L5_00036
TP_L5_00036.Position -11.625 -3.875 0
TP_L5_00036.Mother TES_L5
TP_L5_00036.Visibility 0

TES_Pixel_L5.Copy TP_L5_00037
TP_L5_00037.Position -11.625 -2.325 0
TP_L5_00037.Mother TES_L5
TP_L5_00037.Visibility 0

TES_Pixel_L5.Copy TP_L5_00038
TP_L5_00038.Position -11.625 -0.775 0
TP_L5_00038.Mother TES_L5
TP_L5_00038.Visibility 0

TES_Pixel_L5.Copy TP_L5_00039
TP_L5_00039.Position -11.625 0.775 0
TP_L5_00039.Mother TES_L5
TP_L5_00039.Visibility 0

TES_Pixel_L5.Copy TP_L5_00040
TP_L5_00040.Position -11.625 2.325 0
TP_L5_00040.Mother TES_L5
TP_L5_00040.Visibility 0

TES_Pixel_L5.Copy TP_L5_00041
TP_L5_00041.Position -11.625 3.875 0
TP_L5_00041.Mother TES_L5
TP_L5_00041.Visibility 0

TES_Pixel_L5.Copy TP_L5_00042
TP_L5_00042.Position -11.625 5.425 0
TP_L5_00042.Mother TES_L5
TP_L5_00042.Visibility 0

TES_Pixel_L5.Copy TP_L5_00043
TP_L5_00043.Position -11.625 6.975 0
TP_L5_00043.Mother TES_L5
TP_L5_00043.Visibility 0

TES_Pixel_L5.Copy TP_L5_00044
TP_L5_00044.Position -11.625 8.525 0
TP_L5_00044.Mother TES_L5
TP_L5_00044.Visibility 0

TES_Pixel_L5.Copy TP_L5_00045
TP_L5_00045.Position -11.625 10.075 0
TP_L5_00045.Mother TES_L5
TP_L5_00045.Visibility 0

TES_Pixel_L5.Copy TP_L5_00046
TP_L5_00046.Position -11.625 11.625 0
TP_L5_00046.Mother TES_L5
TP_L5_00046.Visibility 0

TES_Pixel_L5.Copy TP_L5_00047
TP_L5_00047.Position -11.625 13.175 0
TP_L5_00047.Mother TES_L5
TP_L5_00047.Visibility 0

TES_Pixel_L5.Copy TP_L5_00048
TP_L5_00048.Position -10.075 -14.725 0
TP_L5_00048.Mother TES_L5
TP_L5_00048.Visibility 0

TES_Pixel_L5.Copy TP_L5_00049
TP_L5_00049.Position -10.075 -13.175 0
TP_L5_00049.Mother TES_L5
TP_L5_00049.Visibility 0

TES_Pixel_L5.Copy TP_L5_00050
TP_L5_00050.Position -10.075 -11.625 0
TP_L5_00050.Mother TES_L5
TP_L5_00050.Visibility 0

TES_Pixel_L5.Copy TP_L5_00051
TP_L5_00051.Position -10.075 -10.075 0
TP_L5_00051.Mother TES_L5
TP_L5_00051.Visibility 0

TES_Pixel_L5.Copy TP_L5_00052
TP_L5_00052.Position -10.075 -8.525 0
TP_L5_00052.Mother TES_L5
TP_L5_00052.Visibility 0

TES_Pixel_L5.Copy TP_L5_00053
TP_L5_00053.Position -10.075 -6.975 0
TP_L5_00053.Mother TES_L5
TP_L5_00053.Visibility 0

TES_Pixel_L5.Copy TP_L5_00054
TP_L5_00054.Position -10.075 -5.425 0
TP_L5_00054.Mother TES_L5
TP_L5_00054.Visibility 0

TES_Pixel_L5.Copy TP_L5_00055
TP_L5_00055.Position -10.075 -3.875 0
TP_L5_00055.Mother TES_L5
TP_L5_00055.Visibility 0

TES_Pixel_L5.Copy TP_L5_00056
TP_L5_00056.Position -10.075 -2.325 0
TP_L5_00056.Mother TES_L5
TP_L5_00056.Visibility 0

TES_Pixel_L5.Copy TP_L5_00057
TP_L5_00057.Position -10.075 -0.775 0
TP_L5_00057.Mother TES_L5
TP_L5_00057.Visibility 0

TES_Pixel_L5.Copy TP_L5_00058
TP_L5_00058.Position -10.075 0.775 0
TP_L5_00058.Mother TES_L5
TP_L5_00058.Visibility 0

TES_Pixel_L5.Copy TP_L5_00059
TP_L5_00059.Position -10.075 2.325 0
TP_L5_00059.Mother TES_L5
TP_L5_00059.Visibility 0

TES_Pixel_L5.Copy TP_L5_00060
TP_L5_00060.Position -10.075 3.875 0
TP_L5_00060.Mother TES_L5
TP_L5_00060.Visibility 0

TES_Pixel_L5.Copy TP_L5_00061
TP_L5_00061.Position -10.075 5.425 0
TP_L5_00061.Mother TES_L5
TP_L5_00061.Visibility 0

TES_Pixel_L5.Copy TP_L5_00062
TP_L5_00062.Position -10.075 6.975 0
TP_L5_00062.Mother TES_L5
TP_L5_00062.Visibility 0

TES_Pixel_L5.Copy TP_L5_00063
TP_L5_00063.Position -10.075 8.525 0
TP_L5_00063.Mother TES_L5
TP_L5_00063.Visibility 0

TES_Pixel_L5.Copy TP_L5_00064
TP_L5_00064.Position -10.075 10.075 0
TP_L5_00064.Mother TES_L5
TP_L5_00064.Visibility 0

TES_Pixel_L5.Copy TP_L5_00065
TP_L5_00065.Position -10.075 11.625 0
TP_L5_00065.Mother TES_L5
TP_L5_00065.Visibility 0

TES_Pixel_L5.Copy TP_L5_00066
TP_L5_00066.Position -10.075 13.175 0
TP_L5_00066.Mother TES_L5
TP_L5_00066.Visibility 0

TES_Pixel_L5.Copy TP_L5_00067
TP_L5_00067.Position -10.075 14.725 0
TP_L5_00067.Mother TES_L5
TP_L5_00067.Visibility 0

TES_Pixel_L5.Copy TP_L5_00068
TP_L5_00068.Position -8.525 -14.725 0
TP_L5_00068.Mother TES_L5
TP_L5_00068.Visibility 0

TES_Pixel_L5.Copy TP_L5_00069
TP_L5_00069.Position -8.525 -13.175 0
TP_L5_00069.Mother TES_L5
TP_L5_00069.Visibility 0

TES_Pixel_L5.Copy TP_L5_00070
TP_L5_00070.Position -8.525 -11.625 0
TP_L5_00070.Mother TES_L5
TP_L5_00070.Visibility 0

TES_Pixel_L5.Copy TP_L5_00071
TP_L5_00071.Position -8.525 -10.075 0
TP_L5_00071.Mother TES_L5
TP_L5_00071.Visibility 0

TES_Pixel_L5.Copy TP_L5_00072
TP_L5_00072.Position -8.525 -8.525 0
TP_L5_00072.Mother TES_L5
TP_L5_00072.Visibility 0

TES_Pixel_L5.Copy TP_L5_00073
TP_L5_00073.Position -8.525 -6.975 0
TP_L5_00073.Mother TES_L5
TP_L5_00073.Visibility 0

TES_Pixel_L5.Copy TP_L5_00074
TP_L5_00074.Position -8.525 -5.425 0
TP_L5_00074.Mother TES_L5
TP_L5_00074.Visibility 0

TES_Pixel_L5.Copy TP_L5_00075
TP_L5_00075.Position -8.525 -3.875 0
TP_L5_00075.Mother TES_L5
TP_L5_00075.Visibility 0

TES_Pixel_L5.Copy TP_L5_00076
TP_L5_00076.Position -8.525 -2.325 0
TP_L5_00076.Mother TES_L5
TP_L5_00076.Visibility 0

TES_Pixel_L5.Copy TP_L5_00077
TP_L5_00077.Position -8.525 -0.775 0
TP_L5_00077.Mother TES_L5
TP_L5_00077.Visibility 0

TES_Pixel_L5.Copy TP_L5_00078
TP_L5_00078.Position -8.525 0.775 0
TP_L5_00078.Mother TES_L5
TP_L5_00078.Visibility 0

TES_Pixel_L5.Copy TP_L5_00079
TP_L5_00079.Position -8.525 2.325 0
TP_L5_00079.Mother TES_L5
TP_L5_00079.Visibility 0

TES_Pixel_L5.Copy TP_L5_00080
TP_L5_00080.Position -8.525 3.875 0
TP_L5_00080.Mother TES_L5
TP_L5_00080.Visibility 0

TES_Pixel_L5.Copy TP_L5_00081
TP_L5_00081.Position -8.525 5.425 0
TP_L5_00081.Mother TES_L5
TP_L5_00081.Visibility 0

TES_Pixel_L5.Copy TP_L5_00082
TP_L5_00082.Position -8.525 6.975 0
TP_L5_00082.Mother TES_L5
TP_L5_00082.Visibility 0

TES_Pixel_L5.Copy TP_L5_00083
TP_L5_00083.Position -8.525 8.525 0
TP_L5_00083.Mother TES_L5
TP_L5_00083.Visibility 0

TES_Pixel_L5.Copy TP_L5_00084
TP_L5_00084.Position -8.525 10.075 0
TP_L5_00084.Mother TES_L5
TP_L5_00084.Visibility 0

TES_Pixel_L5.Copy TP_L5_00085
TP_L5_00085.Position -8.525 11.625 0
TP_L5_00085.Mother TES_L5
TP_L5_00085.Visibility 0

TES_Pixel_L5.Copy TP_L5_00086
TP_L5_00086.Position -8.525 13.175 0
TP_L5_00086.Mother TES_L5
TP_L5_00086.Visibility 0

TES_Pixel_L5.Copy TP_L5_00087
TP_L5_00087.Position -8.525 14.725 0
TP_L5_00087.Mother TES_L5
TP_L5_00087.Visibility 0

TES_Pixel_L5.Copy TP_L5_00088
TP_L5_00088.Position -6.975 -14.725 0
TP_L5_00088.Mother TES_L5
TP_L5_00088.Visibility 0

TES_Pixel_L5.Copy TP_L5_00089
TP_L5_00089.Position -6.975 -13.175 0
TP_L5_00089.Mother TES_L5
TP_L5_00089.Visibility 0

TES_Pixel_L5.Copy TP_L5_00090
TP_L5_00090.Position -6.975 -11.625 0
TP_L5_00090.Mother TES_L5
TP_L5_00090.Visibility 0

TES_Pixel_L5.Copy TP_L5_00091
TP_L5_00091.Position -6.975 -10.075 0
TP_L5_00091.Mother TES_L5
TP_L5_00091.Visibility 0

TES_Pixel_L5.Copy TP_L5_00092
TP_L5_00092.Position -6.975 -8.525 0
TP_L5_00092.Mother TES_L5
TP_L5_00092.Visibility 0

TES_Pixel_L5.Copy TP_L5_00093
TP_L5_00093.Position -6.975 -6.975 0
TP_L5_00093.Mother TES_L5
TP_L5_00093.Visibility 0

TES_Pixel_L5.Copy TP_L5_00094
TP_L5_00094.Position -6.975 -5.425 0
TP_L5_00094.Mother TES_L5
TP_L5_00094.Visibility 0

TES_Pixel_L5.Copy TP_L5_00095
TP_L5_00095.Position -6.975 -3.875 0
TP_L5_00095.Mother TES_L5
TP_L5_00095.Visibility 0

TES_Pixel_L5.Copy TP_L5_00096
TP_L5_00096.Position -6.975 -2.325 0
TP_L5_00096.Mother TES_L5
TP_L5_00096.Visibility 0

TES_Pixel_L5.Copy TP_L5_00097
TP_L5_00097.Position -6.975 -0.775 0
TP_L5_00097.Mother TES_L5
TP_L5_00097.Visibility 0

TES_Pixel_L5.Copy TP_L5_00098
TP_L5_00098.Position -6.975 0.775 0
TP_L5_00098.Mother TES_L5
TP_L5_00098.Visibility 0

TES_Pixel_L5.Copy TP_L5_00099
TP_L5_00099.Position -6.975 2.325 0
TP_L5_00099.Mother TES_L5
TP_L5_00099.Visibility 0

TES_Pixel_L5.Copy TP_L5_00100
TP_L5_00100.Position -6.975 3.875 0
TP_L5_00100.Mother TES_L5
TP_L5_00100.Visibility 0

TES_Pixel_L5.Copy TP_L5_00101
TP_L5_00101.Position -6.975 5.425 0
TP_L5_00101.Mother TES_L5
TP_L5_00101.Visibility 0

TES_Pixel_L5.Copy TP_L5_00102
TP_L5_00102.Position -6.975 6.975 0
TP_L5_00102.Mother TES_L5
TP_L5_00102.Visibility 0

TES_Pixel_L5.Copy TP_L5_00103
TP_L5_00103.Position -6.975 8.525 0
TP_L5_00103.Mother TES_L5
TP_L5_00103.Visibility 0

TES_Pixel_L5.Copy TP_L5_00104
TP_L5_00104.Position -6.975 10.075 0
TP_L5_00104.Mother TES_L5
TP_L5_00104.Visibility 0

TES_Pixel_L5.Copy TP_L5_00105
TP_L5_00105.Position -6.975 11.625 0
TP_L5_00105.Mother TES_L5
TP_L5_00105.Visibility 0

TES_Pixel_L5.Copy TP_L5_00106
TP_L5_00106.Position -6.975 13.175 0
TP_L5_00106.Mother TES_L5
TP_L5_00106.Visibility 0

TES_Pixel_L5.Copy TP_L5_00107
TP_L5_00107.Position -6.975 14.725 0
TP_L5_00107.Mother TES_L5
TP_L5_00107.Visibility 0

TES_Pixel_L5.Copy TP_L5_00108
TP_L5_00108.Position -5.425 -14.725 0
TP_L5_00108.Mother TES_L5
TP_L5_00108.Visibility 0

TES_Pixel_L5.Copy TP_L5_00109
TP_L5_00109.Position -5.425 -13.175 0
TP_L5_00109.Mother TES_L5
TP_L5_00109.Visibility 0

TES_Pixel_L5.Copy TP_L5_00110
TP_L5_00110.Position -5.425 -11.625 0
TP_L5_00110.Mother TES_L5
TP_L5_00110.Visibility 0

TES_Pixel_L5.Copy TP_L5_00111
TP_L5_00111.Position -5.425 -10.075 0
TP_L5_00111.Mother TES_L5
TP_L5_00111.Visibility 0

TES_Pixel_L5.Copy TP_L5_00112
TP_L5_00112.Position -5.425 -8.525 0
TP_L5_00112.Mother TES_L5
TP_L5_00112.Visibility 0

TES_Pixel_L5.Copy TP_L5_00113
TP_L5_00113.Position -5.425 -6.975 0
TP_L5_00113.Mother TES_L5
TP_L5_00113.Visibility 0

TES_Pixel_L5.Copy TP_L5_00114
TP_L5_00114.Position -5.425 -5.425 0
TP_L5_00114.Mother TES_L5
TP_L5_00114.Visibility 0

TES_Pixel_L5.Copy TP_L5_00115
TP_L5_00115.Position -5.425 -3.875 0
TP_L5_00115.Mother TES_L5
TP_L5_00115.Visibility 0

TES_Pixel_L5.Copy TP_L5_00116
TP_L5_00116.Position -5.425 -2.325 0
TP_L5_00116.Mother TES_L5
TP_L5_00116.Visibility 0

TES_Pixel_L5.Copy TP_L5_00117
TP_L5_00117.Position -5.425 -0.775 0
TP_L5_00117.Mother TES_L5
TP_L5_00117.Visibility 0

TES_Pixel_L5.Copy TP_L5_00118
TP_L5_00118.Position -5.425 0.775 0
TP_L5_00118.Mother TES_L5
TP_L5_00118.Visibility 0

TES_Pixel_L5.Copy TP_L5_00119
TP_L5_00119.Position -5.425 2.325 0
TP_L5_00119.Mother TES_L5
TP_L5_00119.Visibility 0

TES_Pixel_L5.Copy TP_L5_00120
TP_L5_00120.Position -5.425 3.875 0
TP_L5_00120.Mother TES_L5
TP_L5_00120.Visibility 0

TES_Pixel_L5.Copy TP_L5_00121
TP_L5_00121.Position -5.425 5.425 0
TP_L5_00121.Mother TES_L5
TP_L5_00121.Visibility 0

TES_Pixel_L5.Copy TP_L5_00122
TP_L5_00122.Position -5.425 6.975 0
TP_L5_00122.Mother TES_L5
TP_L5_00122.Visibility 0

TES_Pixel_L5.Copy TP_L5_00123
TP_L5_00123.Position -5.425 8.525 0
TP_L5_00123.Mother TES_L5
TP_L5_00123.Visibility 0

TES_Pixel_L5.Copy TP_L5_00124
TP_L5_00124.Position -5.425 10.075 0
TP_L5_00124.Mother TES_L5
TP_L5_00124.Visibility 0

TES_Pixel_L5.Copy TP_L5_00125
TP_L5_00125.Position -5.425 11.625 0
TP_L5_00125.Mother TES_L5
TP_L5_00125.Visibility 0

TES_Pixel_L5.Copy TP_L5_00126
TP_L5_00126.Position -5.425 13.175 0
TP_L5_00126.Mother TES_L5
TP_L5_00126.Visibility 0

TES_Pixel_L5.Copy TP_L5_00127
TP_L5_00127.Position -5.425 14.725 0
TP_L5_00127.Mother TES_L5
TP_L5_00127.Visibility 0

TES_Pixel_L5.Copy TP_L5_00128
TP_L5_00128.Position -3.875 -14.725 0
TP_L5_00128.Mother TES_L5
TP_L5_00128.Visibility 0

TES_Pixel_L5.Copy TP_L5_00129
TP_L5_00129.Position -3.875 -13.175 0
TP_L5_00129.Mother TES_L5
TP_L5_00129.Visibility 0

TES_Pixel_L5.Copy TP_L5_00130
TP_L5_00130.Position -3.875 -11.625 0
TP_L5_00130.Mother TES_L5
TP_L5_00130.Visibility 0

TES_Pixel_L5.Copy TP_L5_00131
TP_L5_00131.Position -3.875 -10.075 0
TP_L5_00131.Mother TES_L5
TP_L5_00131.Visibility 0

TES_Pixel_L5.Copy TP_L5_00132
TP_L5_00132.Position -3.875 -8.525 0
TP_L5_00132.Mother TES_L5
TP_L5_00132.Visibility 0

TES_Pixel_L5.Copy TP_L5_00133
TP_L5_00133.Position -3.875 -6.975 0
TP_L5_00133.Mother TES_L5
TP_L5_00133.Visibility 0

TES_Pixel_L5.Copy TP_L5_00134
TP_L5_00134.Position -3.875 -5.425 0
TP_L5_00134.Mother TES_L5
TP_L5_00134.Visibility 0

TES_Pixel_L5.Copy TP_L5_00135
TP_L5_00135.Position -3.875 -3.875 0
TP_L5_00135.Mother TES_L5
TP_L5_00135.Visibility 0

TES_Pixel_L5.Copy TP_L5_00136
TP_L5_00136.Position -3.875 -2.325 0
TP_L5_00136.Mother TES_L5
TP_L5_00136.Visibility 0

TES_Pixel_L5.Copy TP_L5_00137
TP_L5_00137.Position -3.875 -0.775 0
TP_L5_00137.Mother TES_L5
TP_L5_00137.Visibility 0

TES_Pixel_L5.Copy TP_L5_00138
TP_L5_00138.Position -3.875 0.775 0
TP_L5_00138.Mother TES_L5
TP_L5_00138.Visibility 0

TES_Pixel_L5.Copy TP_L5_00139
TP_L5_00139.Position -3.875 2.325 0
TP_L5_00139.Mother TES_L5
TP_L5_00139.Visibility 0

TES_Pixel_L5.Copy TP_L5_00140
TP_L5_00140.Position -3.875 3.875 0
TP_L5_00140.Mother TES_L5
TP_L5_00140.Visibility 0

TES_Pixel_L5.Copy TP_L5_00141
TP_L5_00141.Position -3.875 5.425 0
TP_L5_00141.Mother TES_L5
TP_L5_00141.Visibility 0

TES_Pixel_L5.Copy TP_L5_00142
TP_L5_00142.Position -3.875 6.975 0
TP_L5_00142.Mother TES_L5
TP_L5_00142.Visibility 0

TES_Pixel_L5.Copy TP_L5_00143
TP_L5_00143.Position -3.875 8.525 0
TP_L5_00143.Mother TES_L5
TP_L5_00143.Visibility 0

TES_Pixel_L5.Copy TP_L5_00144
TP_L5_00144.Position -3.875 10.075 0
TP_L5_00144.Mother TES_L5
TP_L5_00144.Visibility 0

TES_Pixel_L5.Copy TP_L5_00145
TP_L5_00145.Position -3.875 11.625 0
TP_L5_00145.Mother TES_L5
TP_L5_00145.Visibility 0

TES_Pixel_L5.Copy TP_L5_00146
TP_L5_00146.Position -3.875 13.175 0
TP_L5_00146.Mother TES_L5
TP_L5_00146.Visibility 0

TES_Pixel_L5.Copy TP_L5_00147
TP_L5_00147.Position -3.875 14.725 0
TP_L5_00147.Mother TES_L5
TP_L5_00147.Visibility 0

TES_Pixel_L5.Copy TP_L5_00148
TP_L5_00148.Position -2.325 -14.725 0
TP_L5_00148.Mother TES_L5
TP_L5_00148.Visibility 0

TES_Pixel_L5.Copy TP_L5_00149
TP_L5_00149.Position -2.325 -13.175 0
TP_L5_00149.Mother TES_L5
TP_L5_00149.Visibility 0

TES_Pixel_L5.Copy TP_L5_00150
TP_L5_00150.Position -2.325 -11.625 0
TP_L5_00150.Mother TES_L5
TP_L5_00150.Visibility 0

TES_Pixel_L5.Copy TP_L5_00151
TP_L5_00151.Position -2.325 -10.075 0
TP_L5_00151.Mother TES_L5
TP_L5_00151.Visibility 0

TES_Pixel_L5.Copy TP_L5_00152
TP_L5_00152.Position -2.325 -8.525 0
TP_L5_00152.Mother TES_L5
TP_L5_00152.Visibility 0

TES_Pixel_L5.Copy TP_L5_00153
TP_L5_00153.Position -2.325 -6.975 0
TP_L5_00153.Mother TES_L5
TP_L5_00153.Visibility 0

TES_Pixel_L5.Copy TP_L5_00154
TP_L5_00154.Position -2.325 -5.425 0
TP_L5_00154.Mother TES_L5
TP_L5_00154.Visibility 0

TES_Pixel_L5.Copy TP_L5_00155
TP_L5_00155.Position -2.325 -3.875 0
TP_L5_00155.Mother TES_L5
TP_L5_00155.Visibility 0

TES_Pixel_L5.Copy TP_L5_00156
TP_L5_00156.Position -2.325 -2.325 0
TP_L5_00156.Mother TES_L5
TP_L5_00156.Visibility 0

TES_Pixel_L5.Copy TP_L5_00157
TP_L5_00157.Position -2.325 -0.775 0
TP_L5_00157.Mother TES_L5
TP_L5_00157.Visibility 0

TES_Pixel_L5.Copy TP_L5_00158
TP_L5_00158.Position -2.325 0.775 0
TP_L5_00158.Mother TES_L5
TP_L5_00158.Visibility 0

TES_Pixel_L5.Copy TP_L5_00159
TP_L5_00159.Position -2.325 2.325 0
TP_L5_00159.Mother TES_L5
TP_L5_00159.Visibility 0

TES_Pixel_L5.Copy TP_L5_00160
TP_L5_00160.Position -2.325 3.875 0
TP_L5_00160.Mother TES_L5
TP_L5_00160.Visibility 0

TES_Pixel_L5.Copy TP_L5_00161
TP_L5_00161.Position -2.325 5.425 0
TP_L5_00161.Mother TES_L5
TP_L5_00161.Visibility 0

TES_Pixel_L5.Copy TP_L5_00162
TP_L5_00162.Position -2.325 6.975 0
TP_L5_00162.Mother TES_L5
TP_L5_00162.Visibility 0

TES_Pixel_L5.Copy TP_L5_00163
TP_L5_00163.Position -2.325 8.525 0
TP_L5_00163.Mother TES_L5
TP_L5_00163.Visibility 0

TES_Pixel_L5.Copy TP_L5_00164
TP_L5_00164.Position -2.325 10.075 0
TP_L5_00164.Mother TES_L5
TP_L5_00164.Visibility 0

TES_Pixel_L5.Copy TP_L5_00165
TP_L5_00165.Position -2.325 11.625 0
TP_L5_00165.Mother TES_L5
TP_L5_00165.Visibility 0

TES_Pixel_L5.Copy TP_L5_00166
TP_L5_00166.Position -2.325 13.175 0
TP_L5_00166.Mother TES_L5
TP_L5_00166.Visibility 0

TES_Pixel_L5.Copy TP_L5_00167
TP_L5_00167.Position -2.325 14.725 0
TP_L5_00167.Mother TES_L5
TP_L5_00167.Visibility 0

TES_Pixel_L5.Copy TP_L5_00168
TP_L5_00168.Position -0.775 -14.725 0
TP_L5_00168.Mother TES_L5
TP_L5_00168.Visibility 0

TES_Pixel_L5.Copy TP_L5_00169
TP_L5_00169.Position -0.775 -13.175 0
TP_L5_00169.Mother TES_L5
TP_L5_00169.Visibility 0

TES_Pixel_L5.Copy TP_L5_00170
TP_L5_00170.Position -0.775 -11.625 0
TP_L5_00170.Mother TES_L5
TP_L5_00170.Visibility 0

TES_Pixel_L5.Copy TP_L5_00171
TP_L5_00171.Position -0.775 -10.075 0
TP_L5_00171.Mother TES_L5
TP_L5_00171.Visibility 0

TES_Pixel_L5.Copy TP_L5_00172
TP_L5_00172.Position -0.775 -8.525 0
TP_L5_00172.Mother TES_L5
TP_L5_00172.Visibility 0

TES_Pixel_L5.Copy TP_L5_00173
TP_L5_00173.Position -0.775 -6.975 0
TP_L5_00173.Mother TES_L5
TP_L5_00173.Visibility 0

TES_Pixel_L5.Copy TP_L5_00174
TP_L5_00174.Position -0.775 -5.425 0
TP_L5_00174.Mother TES_L5
TP_L5_00174.Visibility 0

TES_Pixel_L5.Copy TP_L5_00175
TP_L5_00175.Position -0.775 -3.875 0
TP_L5_00175.Mother TES_L5
TP_L5_00175.Visibility 0

TES_Pixel_L5.Copy TP_L5_00176
TP_L5_00176.Position -0.775 -2.325 0
TP_L5_00176.Mother TES_L5
TP_L5_00176.Visibility 0

TES_Pixel_L5.Copy TP_L5_00177
TP_L5_00177.Position -0.775 -0.775 0
TP_L5_00177.Mother TES_L5
TP_L5_00177.Visibility 0

TES_Pixel_L5.Copy TP_L5_00178
TP_L5_00178.Position -0.775 0.775 0
TP_L5_00178.Mother TES_L5
TP_L5_00178.Visibility 0

TES_Pixel_L5.Copy TP_L5_00179
TP_L5_00179.Position -0.775 2.325 0
TP_L5_00179.Mother TES_L5
TP_L5_00179.Visibility 0

TES_Pixel_L5.Copy TP_L5_00180
TP_L5_00180.Position -0.775 3.875 0
TP_L5_00180.Mother TES_L5
TP_L5_00180.Visibility 0

TES_Pixel_L5.Copy TP_L5_00181
TP_L5_00181.Position -0.775 5.425 0
TP_L5_00181.Mother TES_L5
TP_L5_00181.Visibility 0

TES_Pixel_L5.Copy TP_L5_00182
TP_L5_00182.Position -0.775 6.975 0
TP_L5_00182.Mother TES_L5
TP_L5_00182.Visibility 0

TES_Pixel_L5.Copy TP_L5_00183
TP_L5_00183.Position -0.775 8.525 0
TP_L5_00183.Mother TES_L5
TP_L5_00183.Visibility 0

TES_Pixel_L5.Copy TP_L5_00184
TP_L5_00184.Position -0.775 10.075 0
TP_L5_00184.Mother TES_L5
TP_L5_00184.Visibility 0

TES_Pixel_L5.Copy TP_L5_00185
TP_L5_00185.Position -0.775 11.625 0
TP_L5_00185.Mother TES_L5
TP_L5_00185.Visibility 0

TES_Pixel_L5.Copy TP_L5_00186
TP_L5_00186.Position -0.775 13.175 0
TP_L5_00186.Mother TES_L5
TP_L5_00186.Visibility 0

TES_Pixel_L5.Copy TP_L5_00187
TP_L5_00187.Position -0.775 14.725 0
TP_L5_00187.Mother TES_L5
TP_L5_00187.Visibility 0

TES_Pixel_L5.Copy TP_L5_00188
TP_L5_00188.Position 0.775 -14.725 0
TP_L5_00188.Mother TES_L5
TP_L5_00188.Visibility 0

TES_Pixel_L5.Copy TP_L5_00189
TP_L5_00189.Position 0.775 -13.175 0
TP_L5_00189.Mother TES_L5
TP_L5_00189.Visibility 0

TES_Pixel_L5.Copy TP_L5_00190
TP_L5_00190.Position 0.775 -11.625 0
TP_L5_00190.Mother TES_L5
TP_L5_00190.Visibility 0

TES_Pixel_L5.Copy TP_L5_00191
TP_L5_00191.Position 0.775 -10.075 0
TP_L5_00191.Mother TES_L5
TP_L5_00191.Visibility 0

TES_Pixel_L5.Copy TP_L5_00192
TP_L5_00192.Position 0.775 -8.525 0
TP_L5_00192.Mother TES_L5
TP_L5_00192.Visibility 0

TES_Pixel_L5.Copy TP_L5_00193
TP_L5_00193.Position 0.775 -6.975 0
TP_L5_00193.Mother TES_L5
TP_L5_00193.Visibility 0

TES_Pixel_L5.Copy TP_L5_00194
TP_L5_00194.Position 0.775 -5.425 0
TP_L5_00194.Mother TES_L5
TP_L5_00194.Visibility 0

TES_Pixel_L5.Copy TP_L5_00195
TP_L5_00195.Position 0.775 -3.875 0
TP_L5_00195.Mother TES_L5
TP_L5_00195.Visibility 0

TES_Pixel_L5.Copy TP_L5_00196
TP_L5_00196.Position 0.775 -2.325 0
TP_L5_00196.Mother TES_L5
TP_L5_00196.Visibility 0

TES_Pixel_L5.Copy TP_L5_00197
TP_L5_00197.Position 0.775 -0.775 0
TP_L5_00197.Mother TES_L5
TP_L5_00197.Visibility 0

TES_Pixel_L5.Copy TP_L5_00198
TP_L5_00198.Position 0.775 0.775 0
TP_L5_00198.Mother TES_L5
TP_L5_00198.Visibility 0

TES_Pixel_L5.Copy TP_L5_00199
TP_L5_00199.Position 0.775 2.325 0
TP_L5_00199.Mother TES_L5
TP_L5_00199.Visibility 0

TES_Pixel_L5.Copy TP_L5_00200
TP_L5_00200.Position 0.775 3.875 0
TP_L5_00200.Mother TES_L5
TP_L5_00200.Visibility 0

TES_Pixel_L5.Copy TP_L5_00201
TP_L5_00201.Position 0.775 5.425 0
TP_L5_00201.Mother TES_L5
TP_L5_00201.Visibility 0

TES_Pixel_L5.Copy TP_L5_00202
TP_L5_00202.Position 0.775 6.975 0
TP_L5_00202.Mother TES_L5
TP_L5_00202.Visibility 0

TES_Pixel_L5.Copy TP_L5_00203
TP_L5_00203.Position 0.775 8.525 0
TP_L5_00203.Mother TES_L5
TP_L5_00203.Visibility 0

TES_Pixel_L5.Copy TP_L5_00204
TP_L5_00204.Position 0.775 10.075 0
TP_L5_00204.Mother TES_L5
TP_L5_00204.Visibility 0

TES_Pixel_L5.Copy TP_L5_00205
TP_L5_00205.Position 0.775 11.625 0
TP_L5_00205.Mother TES_L5
TP_L5_00205.Visibility 0

TES_Pixel_L5.Copy TP_L5_00206
TP_L5_00206.Position 0.775 13.175 0
TP_L5_00206.Mother TES_L5
TP_L5_00206.Visibility 0

TES_Pixel_L5.Copy TP_L5_00207
TP_L5_00207.Position 0.775 14.725 0
TP_L5_00207.Mother TES_L5
TP_L5_00207.Visibility 0

TES_Pixel_L5.Copy TP_L5_00208
TP_L5_00208.Position 2.325 -14.725 0
TP_L5_00208.Mother TES_L5
TP_L5_00208.Visibility 0

TES_Pixel_L5.Copy TP_L5_00209
TP_L5_00209.Position 2.325 -13.175 0
TP_L5_00209.Mother TES_L5
TP_L5_00209.Visibility 0

TES_Pixel_L5.Copy TP_L5_00210
TP_L5_00210.Position 2.325 -11.625 0
TP_L5_00210.Mother TES_L5
TP_L5_00210.Visibility 0

TES_Pixel_L5.Copy TP_L5_00211
TP_L5_00211.Position 2.325 -10.075 0
TP_L5_00211.Mother TES_L5
TP_L5_00211.Visibility 0

TES_Pixel_L5.Copy TP_L5_00212
TP_L5_00212.Position 2.325 -8.525 0
TP_L5_00212.Mother TES_L5
TP_L5_00212.Visibility 0

TES_Pixel_L5.Copy TP_L5_00213
TP_L5_00213.Position 2.325 -6.975 0
TP_L5_00213.Mother TES_L5
TP_L5_00213.Visibility 0

TES_Pixel_L5.Copy TP_L5_00214
TP_L5_00214.Position 2.325 -5.425 0
TP_L5_00214.Mother TES_L5
TP_L5_00214.Visibility 0

TES_Pixel_L5.Copy TP_L5_00215
TP_L5_00215.Position 2.325 -3.875 0
TP_L5_00215.Mother TES_L5
TP_L5_00215.Visibility 0

TES_Pixel_L5.Copy TP_L5_00216
TP_L5_00216.Position 2.325 -2.325 0
TP_L5_00216.Mother TES_L5
TP_L5_00216.Visibility 0

TES_Pixel_L5.Copy TP_L5_00217
TP_L5_00217.Position 2.325 -0.775 0
TP_L5_00217.Mother TES_L5
TP_L5_00217.Visibility 0

TES_Pixel_L5.Copy TP_L5_00218
TP_L5_00218.Position 2.325 0.775 0
TP_L5_00218.Mother TES_L5
TP_L5_00218.Visibility 0

TES_Pixel_L5.Copy TP_L5_00219
TP_L5_00219.Position 2.325 2.325 0
TP_L5_00219.Mother TES_L5
TP_L5_00219.Visibility 0

TES_Pixel_L5.Copy TP_L5_00220
TP_L5_00220.Position 2.325 3.875 0
TP_L5_00220.Mother TES_L5
TP_L5_00220.Visibility 0

TES_Pixel_L5.Copy TP_L5_00221
TP_L5_00221.Position 2.325 5.425 0
TP_L5_00221.Mother TES_L5
TP_L5_00221.Visibility 0

TES_Pixel_L5.Copy TP_L5_00222
TP_L5_00222.Position 2.325 6.975 0
TP_L5_00222.Mother TES_L5
TP_L5_00222.Visibility 0

TES_Pixel_L5.Copy TP_L5_00223
TP_L5_00223.Position 2.325 8.525 0
TP_L5_00223.Mother TES_L5
TP_L5_00223.Visibility 0

TES_Pixel_L5.Copy TP_L5_00224
TP_L5_00224.Position 2.325 10.075 0
TP_L5_00224.Mother TES_L5
TP_L5_00224.Visibility 0

TES_Pixel_L5.Copy TP_L5_00225
TP_L5_00225.Position 2.325 11.625 0
TP_L5_00225.Mother TES_L5
TP_L5_00225.Visibility 0

TES_Pixel_L5.Copy TP_L5_00226
TP_L5_00226.Position 2.325 13.175 0
TP_L5_00226.Mother TES_L5
TP_L5_00226.Visibility 0

TES_Pixel_L5.Copy TP_L5_00227
TP_L5_00227.Position 2.325 14.725 0
TP_L5_00227.Mother TES_L5
TP_L5_00227.Visibility 0

TES_Pixel_L5.Copy TP_L5_00228
TP_L5_00228.Position 3.875 -14.725 0
TP_L5_00228.Mother TES_L5
TP_L5_00228.Visibility 0

TES_Pixel_L5.Copy TP_L5_00229
TP_L5_00229.Position 3.875 -13.175 0
TP_L5_00229.Mother TES_L5
TP_L5_00229.Visibility 0

TES_Pixel_L5.Copy TP_L5_00230
TP_L5_00230.Position 3.875 -11.625 0
TP_L5_00230.Mother TES_L5
TP_L5_00230.Visibility 0

TES_Pixel_L5.Copy TP_L5_00231
TP_L5_00231.Position 3.875 -10.075 0
TP_L5_00231.Mother TES_L5
TP_L5_00231.Visibility 0

TES_Pixel_L5.Copy TP_L5_00232
TP_L5_00232.Position 3.875 -8.525 0
TP_L5_00232.Mother TES_L5
TP_L5_00232.Visibility 0

TES_Pixel_L5.Copy TP_L5_00233
TP_L5_00233.Position 3.875 -6.975 0
TP_L5_00233.Mother TES_L5
TP_L5_00233.Visibility 0

TES_Pixel_L5.Copy TP_L5_00234
TP_L5_00234.Position 3.875 -5.425 0
TP_L5_00234.Mother TES_L5
TP_L5_00234.Visibility 0

TES_Pixel_L5.Copy TP_L5_00235
TP_L5_00235.Position 3.875 -3.875 0
TP_L5_00235.Mother TES_L5
TP_L5_00235.Visibility 0

TES_Pixel_L5.Copy TP_L5_00236
TP_L5_00236.Position 3.875 -2.325 0
TP_L5_00236.Mother TES_L5
TP_L5_00236.Visibility 0

TES_Pixel_L5.Copy TP_L5_00237
TP_L5_00237.Position 3.875 -0.775 0
TP_L5_00237.Mother TES_L5
TP_L5_00237.Visibility 0

TES_Pixel_L5.Copy TP_L5_00238
TP_L5_00238.Position 3.875 0.775 0
TP_L5_00238.Mother TES_L5
TP_L5_00238.Visibility 0

TES_Pixel_L5.Copy TP_L5_00239
TP_L5_00239.Position 3.875 2.325 0
TP_L5_00239.Mother TES_L5
TP_L5_00239.Visibility 0

TES_Pixel_L5.Copy TP_L5_00240
TP_L5_00240.Position 3.875 3.875 0
TP_L5_00240.Mother TES_L5
TP_L5_00240.Visibility 0

TES_Pixel_L5.Copy TP_L5_00241
TP_L5_00241.Position 3.875 5.425 0
TP_L5_00241.Mother TES_L5
TP_L5_00241.Visibility 0

TES_Pixel_L5.Copy TP_L5_00242
TP_L5_00242.Position 3.875 6.975 0
TP_L5_00242.Mother TES_L5
TP_L5_00242.Visibility 0

TES_Pixel_L5.Copy TP_L5_00243
TP_L5_00243.Position 3.875 8.525 0
TP_L5_00243.Mother TES_L5
TP_L5_00243.Visibility 0

TES_Pixel_L5.Copy TP_L5_00244
TP_L5_00244.Position 3.875 10.075 0
TP_L5_00244.Mother TES_L5
TP_L5_00244.Visibility 0

TES_Pixel_L5.Copy TP_L5_00245
TP_L5_00245.Position 3.875 11.625 0
TP_L5_00245.Mother TES_L5
TP_L5_00245.Visibility 0

TES_Pixel_L5.Copy TP_L5_00246
TP_L5_00246.Position 3.875 13.175 0
TP_L5_00246.Mother TES_L5
TP_L5_00246.Visibility 0

TES_Pixel_L5.Copy TP_L5_00247
TP_L5_00247.Position 3.875 14.725 0
TP_L5_00247.Mother TES_L5
TP_L5_00247.Visibility 0

TES_Pixel_L5.Copy TP_L5_00248
TP_L5_00248.Position 5.425 -14.725 0
TP_L5_00248.Mother TES_L5
TP_L5_00248.Visibility 0

TES_Pixel_L5.Copy TP_L5_00249
TP_L5_00249.Position 5.425 -13.175 0
TP_L5_00249.Mother TES_L5
TP_L5_00249.Visibility 0

TES_Pixel_L5.Copy TP_L5_00250
TP_L5_00250.Position 5.425 -11.625 0
TP_L5_00250.Mother TES_L5
TP_L5_00250.Visibility 0

TES_Pixel_L5.Copy TP_L5_00251
TP_L5_00251.Position 5.425 -10.075 0
TP_L5_00251.Mother TES_L5
TP_L5_00251.Visibility 0

TES_Pixel_L5.Copy TP_L5_00252
TP_L5_00252.Position 5.425 -8.525 0
TP_L5_00252.Mother TES_L5
TP_L5_00252.Visibility 0

TES_Pixel_L5.Copy TP_L5_00253
TP_L5_00253.Position 5.425 -6.975 0
TP_L5_00253.Mother TES_L5
TP_L5_00253.Visibility 0

TES_Pixel_L5.Copy TP_L5_00254
TP_L5_00254.Position 5.425 -5.425 0
TP_L5_00254.Mother TES_L5
TP_L5_00254.Visibility 0

TES_Pixel_L5.Copy TP_L5_00255
TP_L5_00255.Position 5.425 -3.875 0
TP_L5_00255.Mother TES_L5
TP_L5_00255.Visibility 0

TES_Pixel_L5.Copy TP_L5_00256
TP_L5_00256.Position 5.425 -2.325 0
TP_L5_00256.Mother TES_L5
TP_L5_00256.Visibility 0

TES_Pixel_L5.Copy TP_L5_00257
TP_L5_00257.Position 5.425 -0.775 0
TP_L5_00257.Mother TES_L5
TP_L5_00257.Visibility 0

TES_Pixel_L5.Copy TP_L5_00258
TP_L5_00258.Position 5.425 0.775 0
TP_L5_00258.Mother TES_L5
TP_L5_00258.Visibility 0

TES_Pixel_L5.Copy TP_L5_00259
TP_L5_00259.Position 5.425 2.325 0
TP_L5_00259.Mother TES_L5
TP_L5_00259.Visibility 0

TES_Pixel_L5.Copy TP_L5_00260
TP_L5_00260.Position 5.425 3.875 0
TP_L5_00260.Mother TES_L5
TP_L5_00260.Visibility 0

TES_Pixel_L5.Copy TP_L5_00261
TP_L5_00261.Position 5.425 5.425 0
TP_L5_00261.Mother TES_L5
TP_L5_00261.Visibility 0

TES_Pixel_L5.Copy TP_L5_00262
TP_L5_00262.Position 5.425 6.975 0
TP_L5_00262.Mother TES_L5
TP_L5_00262.Visibility 0

TES_Pixel_L5.Copy TP_L5_00263
TP_L5_00263.Position 5.425 8.525 0
TP_L5_00263.Mother TES_L5
TP_L5_00263.Visibility 0

TES_Pixel_L5.Copy TP_L5_00264
TP_L5_00264.Position 5.425 10.075 0
TP_L5_00264.Mother TES_L5
TP_L5_00264.Visibility 0

TES_Pixel_L5.Copy TP_L5_00265
TP_L5_00265.Position 5.425 11.625 0
TP_L5_00265.Mother TES_L5
TP_L5_00265.Visibility 0

TES_Pixel_L5.Copy TP_L5_00266
TP_L5_00266.Position 5.425 13.175 0
TP_L5_00266.Mother TES_L5
TP_L5_00266.Visibility 0

TES_Pixel_L5.Copy TP_L5_00267
TP_L5_00267.Position 5.425 14.725 0
TP_L5_00267.Mother TES_L5
TP_L5_00267.Visibility 0

TES_Pixel_L5.Copy TP_L5_00268
TP_L5_00268.Position 6.975 -14.725 0
TP_L5_00268.Mother TES_L5
TP_L5_00268.Visibility 0

TES_Pixel_L5.Copy TP_L5_00269
TP_L5_00269.Position 6.975 -13.175 0
TP_L5_00269.Mother TES_L5
TP_L5_00269.Visibility 0

TES_Pixel_L5.Copy TP_L5_00270
TP_L5_00270.Position 6.975 -11.625 0
TP_L5_00270.Mother TES_L5
TP_L5_00270.Visibility 0

TES_Pixel_L5.Copy TP_L5_00271
TP_L5_00271.Position 6.975 -10.075 0
TP_L5_00271.Mother TES_L5
TP_L5_00271.Visibility 0

TES_Pixel_L5.Copy TP_L5_00272
TP_L5_00272.Position 6.975 -8.525 0
TP_L5_00272.Mother TES_L5
TP_L5_00272.Visibility 0

TES_Pixel_L5.Copy TP_L5_00273
TP_L5_00273.Position 6.975 -6.975 0
TP_L5_00273.Mother TES_L5
TP_L5_00273.Visibility 0

TES_Pixel_L5.Copy TP_L5_00274
TP_L5_00274.Position 6.975 -5.425 0
TP_L5_00274.Mother TES_L5
TP_L5_00274.Visibility 0

TES_Pixel_L5.Copy TP_L5_00275
TP_L5_00275.Position 6.975 -3.875 0
TP_L5_00275.Mother TES_L5
TP_L5_00275.Visibility 0

TES_Pixel_L5.Copy TP_L5_00276
TP_L5_00276.Position 6.975 -2.325 0
TP_L5_00276.Mother TES_L5
TP_L5_00276.Visibility 0

TES_Pixel_L5.Copy TP_L5_00277
TP_L5_00277.Position 6.975 -0.775 0
TP_L5_00277.Mother TES_L5
TP_L5_00277.Visibility 0

TES_Pixel_L5.Copy TP_L5_00278
TP_L5_00278.Position 6.975 0.775 0
TP_L5_00278.Mother TES_L5
TP_L5_00278.Visibility 0

TES_Pixel_L5.Copy TP_L5_00279
TP_L5_00279.Position 6.975 2.325 0
TP_L5_00279.Mother TES_L5
TP_L5_00279.Visibility 0

TES_Pixel_L5.Copy TP_L5_00280
TP_L5_00280.Position 6.975 3.875 0
TP_L5_00280.Mother TES_L5
TP_L5_00280.Visibility 0

TES_Pixel_L5.Copy TP_L5_00281
TP_L5_00281.Position 6.975 5.425 0
TP_L5_00281.Mother TES_L5
TP_L5_00281.Visibility 0

TES_Pixel_L5.Copy TP_L5_00282
TP_L5_00282.Position 6.975 6.975 0
TP_L5_00282.Mother TES_L5
TP_L5_00282.Visibility 0

TES_Pixel_L5.Copy TP_L5_00283
TP_L5_00283.Position 6.975 8.525 0
TP_L5_00283.Mother TES_L5
TP_L5_00283.Visibility 0

TES_Pixel_L5.Copy TP_L5_00284
TP_L5_00284.Position 6.975 10.075 0
TP_L5_00284.Mother TES_L5
TP_L5_00284.Visibility 0

TES_Pixel_L5.Copy TP_L5_00285
TP_L5_00285.Position 6.975 11.625 0
TP_L5_00285.Mother TES_L5
TP_L5_00285.Visibility 0

TES_Pixel_L5.Copy TP_L5_00286
TP_L5_00286.Position 6.975 13.175 0
TP_L5_00286.Mother TES_L5
TP_L5_00286.Visibility 0

TES_Pixel_L5.Copy TP_L5_00287
TP_L5_00287.Position 6.975 14.725 0
TP_L5_00287.Mother TES_L5
TP_L5_00287.Visibility 0

TES_Pixel_L5.Copy TP_L5_00288
TP_L5_00288.Position 8.525 -14.725 0
TP_L5_00288.Mother TES_L5
TP_L5_00288.Visibility 0

TES_Pixel_L5.Copy TP_L5_00289
TP_L5_00289.Position 8.525 -13.175 0
TP_L5_00289.Mother TES_L5
TP_L5_00289.Visibility 0

TES_Pixel_L5.Copy TP_L5_00290
TP_L5_00290.Position 8.525 -11.625 0
TP_L5_00290.Mother TES_L5
TP_L5_00290.Visibility 0

TES_Pixel_L5.Copy TP_L5_00291
TP_L5_00291.Position 8.525 -10.075 0
TP_L5_00291.Mother TES_L5
TP_L5_00291.Visibility 0

TES_Pixel_L5.Copy TP_L5_00292
TP_L5_00292.Position 8.525 -8.525 0
TP_L5_00292.Mother TES_L5
TP_L5_00292.Visibility 0

TES_Pixel_L5.Copy TP_L5_00293
TP_L5_00293.Position 8.525 -6.975 0
TP_L5_00293.Mother TES_L5
TP_L5_00293.Visibility 0

TES_Pixel_L5.Copy TP_L5_00294
TP_L5_00294.Position 8.525 -5.425 0
TP_L5_00294.Mother TES_L5
TP_L5_00294.Visibility 0

TES_Pixel_L5.Copy TP_L5_00295
TP_L5_00295.Position 8.525 -3.875 0
TP_L5_00295.Mother TES_L5
TP_L5_00295.Visibility 0

TES_Pixel_L5.Copy TP_L5_00296
TP_L5_00296.Position 8.525 -2.325 0
TP_L5_00296.Mother TES_L5
TP_L5_00296.Visibility 0

TES_Pixel_L5.Copy TP_L5_00297
TP_L5_00297.Position 8.525 -0.775 0
TP_L5_00297.Mother TES_L5
TP_L5_00297.Visibility 0

TES_Pixel_L5.Copy TP_L5_00298
TP_L5_00298.Position 8.525 0.775 0
TP_L5_00298.Mother TES_L5
TP_L5_00298.Visibility 0

TES_Pixel_L5.Copy TP_L5_00299
TP_L5_00299.Position 8.525 2.325 0
TP_L5_00299.Mother TES_L5
TP_L5_00299.Visibility 0

TES_Pixel_L5.Copy TP_L5_00300
TP_L5_00300.Position 8.525 3.875 0
TP_L5_00300.Mother TES_L5
TP_L5_00300.Visibility 0

TES_Pixel_L5.Copy TP_L5_00301
TP_L5_00301.Position 8.525 5.425 0
TP_L5_00301.Mother TES_L5
TP_L5_00301.Visibility 0

TES_Pixel_L5.Copy TP_L5_00302
TP_L5_00302.Position 8.525 6.975 0
TP_L5_00302.Mother TES_L5
TP_L5_00302.Visibility 0

TES_Pixel_L5.Copy TP_L5_00303
TP_L5_00303.Position 8.525 8.525 0
TP_L5_00303.Mother TES_L5
TP_L5_00303.Visibility 0

TES_Pixel_L5.Copy TP_L5_00304
TP_L5_00304.Position 8.525 10.075 0
TP_L5_00304.Mother TES_L5
TP_L5_00304.Visibility 0

TES_Pixel_L5.Copy TP_L5_00305
TP_L5_00305.Position 8.525 11.625 0
TP_L5_00305.Mother TES_L5
TP_L5_00305.Visibility 0

TES_Pixel_L5.Copy TP_L5_00306
TP_L5_00306.Position 8.525 13.175 0
TP_L5_00306.Mother TES_L5
TP_L5_00306.Visibility 0

TES_Pixel_L5.Copy TP_L5_00307
TP_L5_00307.Position 8.525 14.725 0
TP_L5_00307.Mother TES_L5
TP_L5_00307.Visibility 0

TES_Pixel_L5.Copy TP_L5_00308
TP_L5_00308.Position 10.075 -14.725 0
TP_L5_00308.Mother TES_L5
TP_L5_00308.Visibility 0

TES_Pixel_L5.Copy TP_L5_00309
TP_L5_00309.Position 10.075 -13.175 0
TP_L5_00309.Mother TES_L5
TP_L5_00309.Visibility 0

TES_Pixel_L5.Copy TP_L5_00310
TP_L5_00310.Position 10.075 -11.625 0
TP_L5_00310.Mother TES_L5
TP_L5_00310.Visibility 0

TES_Pixel_L5.Copy TP_L5_00311
TP_L5_00311.Position 10.075 -10.075 0
TP_L5_00311.Mother TES_L5
TP_L5_00311.Visibility 0

TES_Pixel_L5.Copy TP_L5_00312
TP_L5_00312.Position 10.075 -8.525 0
TP_L5_00312.Mother TES_L5
TP_L5_00312.Visibility 0

TES_Pixel_L5.Copy TP_L5_00313
TP_L5_00313.Position 10.075 -6.975 0
TP_L5_00313.Mother TES_L5
TP_L5_00313.Visibility 0

TES_Pixel_L5.Copy TP_L5_00314
TP_L5_00314.Position 10.075 -5.425 0
TP_L5_00314.Mother TES_L5
TP_L5_00314.Visibility 0

TES_Pixel_L5.Copy TP_L5_00315
TP_L5_00315.Position 10.075 -3.875 0
TP_L5_00315.Mother TES_L5
TP_L5_00315.Visibility 0

TES_Pixel_L5.Copy TP_L5_00316
TP_L5_00316.Position 10.075 -2.325 0
TP_L5_00316.Mother TES_L5
TP_L5_00316.Visibility 0

TES_Pixel_L5.Copy TP_L5_00317
TP_L5_00317.Position 10.075 -0.775 0
TP_L5_00317.Mother TES_L5
TP_L5_00317.Visibility 0

TES_Pixel_L5.Copy TP_L5_00318
TP_L5_00318.Position 10.075 0.775 0
TP_L5_00318.Mother TES_L5
TP_L5_00318.Visibility 0

TES_Pixel_L5.Copy TP_L5_00319
TP_L5_00319.Position 10.075 2.325 0
TP_L5_00319.Mother TES_L5
TP_L5_00319.Visibility 0

TES_Pixel_L5.Copy TP_L5_00320
TP_L5_00320.Position 10.075 3.875 0
TP_L5_00320.Mother TES_L5
TP_L5_00320.Visibility 0

TES_Pixel_L5.Copy TP_L5_00321
TP_L5_00321.Position 10.075 5.425 0
TP_L5_00321.Mother TES_L5
TP_L5_00321.Visibility 0

TES_Pixel_L5.Copy TP_L5_00322
TP_L5_00322.Position 10.075 6.975 0
TP_L5_00322.Mother TES_L5
TP_L5_00322.Visibility 0

TES_Pixel_L5.Copy TP_L5_00323
TP_L5_00323.Position 10.075 8.525 0
TP_L5_00323.Mother TES_L5
TP_L5_00323.Visibility 0

TES_Pixel_L5.Copy TP_L5_00324
TP_L5_00324.Position 10.075 10.075 0
TP_L5_00324.Mother TES_L5
TP_L5_00324.Visibility 0

TES_Pixel_L5.Copy TP_L5_00325
TP_L5_00325.Position 10.075 11.625 0
TP_L5_00325.Mother TES_L5
TP_L5_00325.Visibility 0

TES_Pixel_L5.Copy TP_L5_00326
TP_L5_00326.Position 10.075 13.175 0
TP_L5_00326.Mother TES_L5
TP_L5_00326.Visibility 0

TES_Pixel_L5.Copy TP_L5_00327
TP_L5_00327.Position 10.075 14.725 0
TP_L5_00327.Mother TES_L5
TP_L5_00327.Visibility 0

TES_Pixel_L5.Copy TP_L5_00328
TP_L5_00328.Position 11.625 -13.175 0
TP_L5_00328.Mother TES_L5
TP_L5_00328.Visibility 0

TES_Pixel_L5.Copy TP_L5_00329
TP_L5_00329.Position 11.625 -11.625 0
TP_L5_00329.Mother TES_L5
TP_L5_00329.Visibility 0

TES_Pixel_L5.Copy TP_L5_00330
TP_L5_00330.Position 11.625 -10.075 0
TP_L5_00330.Mother TES_L5
TP_L5_00330.Visibility 0

TES_Pixel_L5.Copy TP_L5_00331
TP_L5_00331.Position 11.625 -8.525 0
TP_L5_00331.Mother TES_L5
TP_L5_00331.Visibility 0

TES_Pixel_L5.Copy TP_L5_00332
TP_L5_00332.Position 11.625 -6.975 0
TP_L5_00332.Mother TES_L5
TP_L5_00332.Visibility 0

TES_Pixel_L5.Copy TP_L5_00333
TP_L5_00333.Position 11.625 -5.425 0
TP_L5_00333.Mother TES_L5
TP_L5_00333.Visibility 0

TES_Pixel_L5.Copy TP_L5_00334
TP_L5_00334.Position 11.625 -3.875 0
TP_L5_00334.Mother TES_L5
TP_L5_00334.Visibility 0

TES_Pixel_L5.Copy TP_L5_00335
TP_L5_00335.Position 11.625 -2.325 0
TP_L5_00335.Mother TES_L5
TP_L5_00335.Visibility 0

TES_Pixel_L5.Copy TP_L5_00336
TP_L5_00336.Position 11.625 -0.775 0
TP_L5_00336.Mother TES_L5
TP_L5_00336.Visibility 0

TES_Pixel_L5.Copy TP_L5_00337
TP_L5_00337.Position 11.625 0.775 0
TP_L5_00337.Mother TES_L5
TP_L5_00337.Visibility 0

TES_Pixel_L5.Copy TP_L5_00338
TP_L5_00338.Position 11.625 2.325 0
TP_L5_00338.Mother TES_L5
TP_L5_00338.Visibility 0

TES_Pixel_L5.Copy TP_L5_00339
TP_L5_00339.Position 11.625 3.875 0
TP_L5_00339.Mother TES_L5
TP_L5_00339.Visibility 0

TES_Pixel_L5.Copy TP_L5_00340
TP_L5_00340.Position 11.625 5.425 0
TP_L5_00340.Mother TES_L5
TP_L5_00340.Visibility 0

TES_Pixel_L5.Copy TP_L5_00341
TP_L5_00341.Position 11.625 6.975 0
TP_L5_00341.Mother TES_L5
TP_L5_00341.Visibility 0

TES_Pixel_L5.Copy TP_L5_00342
TP_L5_00342.Position 11.625 8.525 0
TP_L5_00342.Mother TES_L5
TP_L5_00342.Visibility 0

TES_Pixel_L5.Copy TP_L5_00343
TP_L5_00343.Position 11.625 10.075 0
TP_L5_00343.Mother TES_L5
TP_L5_00343.Visibility 0

TES_Pixel_L5.Copy TP_L5_00344
TP_L5_00344.Position 11.625 11.625 0
TP_L5_00344.Mother TES_L5
TP_L5_00344.Visibility 0

TES_Pixel_L5.Copy TP_L5_00345
TP_L5_00345.Position 11.625 13.175 0
TP_L5_00345.Mother TES_L5
TP_L5_00345.Visibility 0

TES_Pixel_L5.Copy TP_L5_00346
TP_L5_00346.Position 13.175 -11.625 0
TP_L5_00346.Mother TES_L5
TP_L5_00346.Visibility 0

TES_Pixel_L5.Copy TP_L5_00347
TP_L5_00347.Position 13.175 -10.075 0
TP_L5_00347.Mother TES_L5
TP_L5_00347.Visibility 0

TES_Pixel_L5.Copy TP_L5_00348
TP_L5_00348.Position 13.175 -8.525 0
TP_L5_00348.Mother TES_L5
TP_L5_00348.Visibility 0

TES_Pixel_L5.Copy TP_L5_00349
TP_L5_00349.Position 13.175 -6.975 0
TP_L5_00349.Mother TES_L5
TP_L5_00349.Visibility 0

TES_Pixel_L5.Copy TP_L5_00350
TP_L5_00350.Position 13.175 -5.425 0
TP_L5_00350.Mother TES_L5
TP_L5_00350.Visibility 0

TES_Pixel_L5.Copy TP_L5_00351
TP_L5_00351.Position 13.175 -3.875 0
TP_L5_00351.Mother TES_L5
TP_L5_00351.Visibility 0

TES_Pixel_L5.Copy TP_L5_00352
TP_L5_00352.Position 13.175 -2.325 0
TP_L5_00352.Mother TES_L5
TP_L5_00352.Visibility 0

TES_Pixel_L5.Copy TP_L5_00353
TP_L5_00353.Position 13.175 -0.775 0
TP_L5_00353.Mother TES_L5
TP_L5_00353.Visibility 0

TES_Pixel_L5.Copy TP_L5_00354
TP_L5_00354.Position 13.175 0.775 0
TP_L5_00354.Mother TES_L5
TP_L5_00354.Visibility 0

TES_Pixel_L5.Copy TP_L5_00355
TP_L5_00355.Position 13.175 2.325 0
TP_L5_00355.Mother TES_L5
TP_L5_00355.Visibility 0

TES_Pixel_L5.Copy TP_L5_00356
TP_L5_00356.Position 13.175 3.875 0
TP_L5_00356.Mother TES_L5
TP_L5_00356.Visibility 0

TES_Pixel_L5.Copy TP_L5_00357
TP_L5_00357.Position 13.175 5.425 0
TP_L5_00357.Mother TES_L5
TP_L5_00357.Visibility 0

TES_Pixel_L5.Copy TP_L5_00358
TP_L5_00358.Position 13.175 6.975 0
TP_L5_00358.Mother TES_L5
TP_L5_00358.Visibility 0

TES_Pixel_L5.Copy TP_L5_00359
TP_L5_00359.Position 13.175 8.525 0
TP_L5_00359.Mother TES_L5
TP_L5_00359.Visibility 0

TES_Pixel_L5.Copy TP_L5_00360
TP_L5_00360.Position 13.175 10.075 0
TP_L5_00360.Mother TES_L5
TP_L5_00360.Visibility 0

TES_Pixel_L5.Copy TP_L5_00361
TP_L5_00361.Position 13.175 11.625 0
TP_L5_00361.Mother TES_L5
TP_L5_00361.Visibility 0

TES_Pixel_L5.Copy TP_L5_00362
TP_L5_00362.Position 14.725 -10.075 0
TP_L5_00362.Mother TES_L5
TP_L5_00362.Visibility 0

TES_Pixel_L5.Copy TP_L5_00363
TP_L5_00363.Position 14.725 -8.525 0
TP_L5_00363.Mother TES_L5
TP_L5_00363.Visibility 0

TES_Pixel_L5.Copy TP_L5_00364
TP_L5_00364.Position 14.725 -6.975 0
TP_L5_00364.Mother TES_L5
TP_L5_00364.Visibility 0

TES_Pixel_L5.Copy TP_L5_00365
TP_L5_00365.Position 14.725 -5.425 0
TP_L5_00365.Mother TES_L5
TP_L5_00365.Visibility 0

TES_Pixel_L5.Copy TP_L5_00366
TP_L5_00366.Position 14.725 -3.875 0
TP_L5_00366.Mother TES_L5
TP_L5_00366.Visibility 0

TES_Pixel_L5.Copy TP_L5_00367
TP_L5_00367.Position 14.725 -2.325 0
TP_L5_00367.Mother TES_L5
TP_L5_00367.Visibility 0

TES_Pixel_L5.Copy TP_L5_00368
TP_L5_00368.Position 14.725 -0.775 0
TP_L5_00368.Mother TES_L5
TP_L5_00368.Visibility 0

TES_Pixel_L5.Copy TP_L5_00369
TP_L5_00369.Position 14.725 0.775 0
TP_L5_00369.Mother TES_L5
TP_L5_00369.Visibility 0

TES_Pixel_L5.Copy TP_L5_00370
TP_L5_00370.Position 14.725 2.325 0
TP_L5_00370.Mother TES_L5
TP_L5_00370.Visibility 0

TES_Pixel_L5.Copy TP_L5_00371
TP_L5_00371.Position 14.725 3.875 0
TP_L5_00371.Mother TES_L5
TP_L5_00371.Visibility 0

TES_Pixel_L5.Copy TP_L5_00372
TP_L5_00372.Position 14.725 5.425 0
TP_L5_00372.Mother TES_L5
TP_L5_00372.Visibility 0

TES_Pixel_L5.Copy TP_L5_00373
TP_L5_00373.Position 14.725 6.975 0
TP_L5_00373.Mother TES_L5
TP_L5_00373.Visibility 0

TES_Pixel_L5.Copy TP_L5_00374
TP_L5_00374.Position 14.725 8.525 0
TP_L5_00374.Mother TES_L5
TP_L5_00374.Visibility 0

TES_Pixel_L5.Copy TP_L5_00375
TP_L5_00375.Position 14.725 10.075 0
TP_L5_00375.Mother TES_L5
TP_L5_00375.Visibility 0

TES_SampleBox_Cu.Position 0 0 0
TES_SampleBox_Cu.Mother WorldVolume

SampleBox_Al_Window.Position 0 0 85.5
SampleBox_Al_Window.Mother WorldVolume

Nb_SC_Detector_Can.Position 0 0 0
Nb_SC_Detector_Can.Mother WorldVolume

Win_Nb_SC_Detector_Can.Position 0 0 92.15
Win_Nb_SC_Detector_Can.Mother WorldVolume

Thermal_4K_Al_Shield.Position 0 0 0
Thermal_4K_Al_Shield.Mother WorldVolume

Thermal_50K_Al_Shield.Position 0 0 0
Thermal_50K_Al_Shield.Mother WorldVolume

Vacuum_Jacket_Al.Position 0 0 0
Vacuum_Jacket_Al.Mother WorldVolume

Win_4K_Al_Shield.Position 0 0 114.4
Win_4K_Al_Shield.Mother WorldVolume

Win_50K_Al_Shield.Position 0 0 122.4
Win_50K_Al_Shield.Mother WorldVolume

CeBr3_Active_Shield.Position 0 0 0
CeBr3_Active_Shield.Mother WorldVolume

Outer_Al_Mech_Shell.Position 0 0 0
Outer_Al_Mech_Shell.Mother WorldVolume

Win_Be_Cryostat.Position 0 0 128.425
Win_Be_Cryostat.Mother WorldVolume


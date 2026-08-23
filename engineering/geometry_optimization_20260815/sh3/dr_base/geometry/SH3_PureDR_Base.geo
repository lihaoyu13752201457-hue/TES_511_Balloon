// SH3 pure dilution-refrigerator base; chimney intentionally not assembled.
// Parent-frame 45 degree tilt is retained from pinned SG3B.
Include Materials_SH3_DR_Base.geo
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

// BEGIN PINNED_SG3B_COLD_PLATES_AND_INTERNAL_SUPPORTS
// Volume ColdPlate_MXC_50mK_SD_anchor; material=Copper
Volume ColdPlate_MXC_50mK_SD_anchor
ColdPlate_MXC_50mK_SD_anchor.Material Copper
ColdPlate_MXC_50mK_SD_anchor.Visibility 1
ColdPlate_MXC_50mK_SD_anchor.Shape PCON 0 360 2 -0.2 0 15 0.2 0 15

ColdPlate_MXC_50mK_SD_anchor.Position 0 0 0
ColdPlate_MXC_50mK_SD_anchor.Mother InstrumentFrame

// BEGIN SE3_HOLE_PATTERN_MXC_50mK
// 48 Vacuum daughters preserve the reviewed 4 mm-array excavated area with far fewer placements.
// Centres remain on the unshifted 6 mm grid; large-hole web/edge/keep-out margins are revalidated.
Volume SE3_HoleTemplate_MXC_50mK
SE3_HoleTemplate_MXC_50mK.Material Vacuum
SE3_HoleTemplate_MXC_50mK.Visibility 1
SE3_HoleTemplate_MXC_50mK.Shape PCON 0 360 2 -0.2 0 1.1629703349613 0.2 0 1.1629703349613

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00001
SE3_HOLE_MXC_50mK_00001.Position -13.2 -0.6 0
SE3_HOLE_MXC_50mK_00001.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00001.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00002
SE3_HOLE_MXC_50mK_00002.Position -12.6 -4.2 0
SE3_HOLE_MXC_50mK_00002.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00002.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00003
SE3_HOLE_MXC_50mK_00003.Position -12.6 4.8 0
SE3_HOLE_MXC_50mK_00003.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00003.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00004
SE3_HOLE_MXC_50mK_00004.Position -11.4 -7.2 0
SE3_HOLE_MXC_50mK_00004.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00004.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00005
SE3_HOLE_MXC_50mK_00005.Position -10.8 7.8 0
SE3_HOLE_MXC_50mK_00005.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00005.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00006
SE3_HOLE_MXC_50mK_00006.Position -10.2 -1.2 0
SE3_HOLE_MXC_50mK_00006.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00006.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00007
SE3_HOLE_MXC_50mK_00007.Position -9 -10.2 0
SE3_HOLE_MXC_50mK_00007.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00007.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00008
SE3_HOLE_MXC_50mK_00008.Position -9 -4.2 0
SE3_HOLE_MXC_50mK_00008.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00008.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00009
SE3_HOLE_MXC_50mK_00009.Position -9 2.4 0
SE3_HOLE_MXC_50mK_00009.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00009.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00010
SE3_HOLE_MXC_50mK_00010.Position -7.8 7.8 0
SE3_HOLE_MXC_50mK_00010.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00010.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00011
SE3_HOLE_MXC_50mK_00011.Position -7.8 10.8 0
SE3_HOLE_MXC_50mK_00011.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00011.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00012
SE3_HOLE_MXC_50mK_00012.Position -7.2 -7.2 0
SE3_HOLE_MXC_50mK_00012.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00012.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00013
SE3_HOLE_MXC_50mK_00013.Position -7.2 4.8 0
SE3_HOLE_MXC_50mK_00013.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00013.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00014
SE3_HOLE_MXC_50mK_00014.Position -6 -10.2 0
SE3_HOLE_MXC_50mK_00014.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00014.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00015
SE3_HOLE_MXC_50mK_00015.Position -5.4 0 0
SE3_HOLE_MXC_50mK_00015.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00015.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00016
SE3_HOLE_MXC_50mK_00016.Position -4.8 -12.6 0
SE3_HOLE_MXC_50mK_00016.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00016.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00017
SE3_HOLE_MXC_50mK_00017.Position -4.8 9 0
SE3_HOLE_MXC_50mK_00017.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00017.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00018
SE3_HOLE_MXC_50mK_00018.Position -4.8 12.6 0
SE3_HOLE_MXC_50mK_00018.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00018.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00019
SE3_HOLE_MXC_50mK_00019.Position -3.6 -8.4 0
SE3_HOLE_MXC_50mK_00019.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00019.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00020
SE3_HOLE_MXC_50mK_00020.Position -3 -4.2 0
SE3_HOLE_MXC_50mK_00020.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00020.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00021
SE3_HOLE_MXC_50mK_00021.Position -3 4.2 0
SE3_HOLE_MXC_50mK_00021.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00021.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00022
SE3_HOLE_MXC_50mK_00022.Position -2.4 -10.8 0
SE3_HOLE_MXC_50mK_00022.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00022.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00023
SE3_HOLE_MXC_50mK_00023.Position -1.8 8.4 0
SE3_HOLE_MXC_50mK_00023.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00023.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00024
SE3_HOLE_MXC_50mK_00024.Position -1.8 12 0
SE3_HOLE_MXC_50mK_00024.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00024.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00025
SE3_HOLE_MXC_50mK_00025.Position 0 -13.2 0
SE3_HOLE_MXC_50mK_00025.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00025.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00026
SE3_HOLE_MXC_50mK_00026.Position 0 -9.6 0
SE3_HOLE_MXC_50mK_00026.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00026.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00027
SE3_HOLE_MXC_50mK_00027.Position 1.2 13.2 0
SE3_HOLE_MXC_50mK_00027.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00027.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00028
SE3_HOLE_MXC_50mK_00028.Position 1.8 -4.8 0
SE3_HOLE_MXC_50mK_00028.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00028.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00029
SE3_HOLE_MXC_50mK_00029.Position 1.8 9.6 0
SE3_HOLE_MXC_50mK_00029.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00029.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00030
SE3_HOLE_MXC_50mK_00030.Position 3 -12.6 0
SE3_HOLE_MXC_50mK_00030.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00030.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00031
SE3_HOLE_MXC_50mK_00031.Position 3.6 -9.6 0
SE3_HOLE_MXC_50mK_00031.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00031.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00032
SE3_HOLE_MXC_50mK_00032.Position 4.2 7.2 0
SE3_HOLE_MXC_50mK_00032.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00032.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00033
SE3_HOLE_MXC_50mK_00033.Position 4.2 12 0
SE3_HOLE_MXC_50mK_00033.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00033.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00034
SE3_HOLE_MXC_50mK_00034.Position 6 -12 0
SE3_HOLE_MXC_50mK_00034.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00034.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00035
SE3_HOLE_MXC_50mK_00035.Position 6.6 -7.8 0
SE3_HOLE_MXC_50mK_00035.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00035.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00036
SE3_HOLE_MXC_50mK_00036.Position 7.2 11.4 0
SE3_HOLE_MXC_50mK_00036.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00036.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00037
SE3_HOLE_MXC_50mK_00037.Position 7.8 -4.2 0
SE3_HOLE_MXC_50mK_00037.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00037.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00038
SE3_HOLE_MXC_50mK_00038.Position 7.8 6 0
SE3_HOLE_MXC_50mK_00038.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00038.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00039
SE3_HOLE_MXC_50mK_00039.Position 8.4 2.4 0
SE3_HOLE_MXC_50mK_00039.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00039.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00040
SE3_HOLE_MXC_50mK_00040.Position 9 -10.2 0
SE3_HOLE_MXC_50mK_00040.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00040.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00041
SE3_HOLE_MXC_50mK_00041.Position 9.6 -7.2 0
SE3_HOLE_MXC_50mK_00041.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00041.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00042
SE3_HOLE_MXC_50mK_00042.Position 9.6 -1.2 0
SE3_HOLE_MXC_50mK_00042.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00042.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00043
SE3_HOLE_MXC_50mK_00043.Position 10.8 1.2 0
SE3_HOLE_MXC_50mK_00043.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00043.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00044
SE3_HOLE_MXC_50mK_00044.Position 10.8 4.8 0
SE3_HOLE_MXC_50mK_00044.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00044.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00045
SE3_HOLE_MXC_50mK_00045.Position 10.8 7.8 0
SE3_HOLE_MXC_50mK_00045.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00045.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00046
SE3_HOLE_MXC_50mK_00046.Position 12 -6 0
SE3_HOLE_MXC_50mK_00046.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00046.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00047
SE3_HOLE_MXC_50mK_00047.Position 13.2 -1.8 0
SE3_HOLE_MXC_50mK_00047.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00047.Visibility 1

SE3_HoleTemplate_MXC_50mK.Copy SE3_HOLE_MXC_50mK_00048
SE3_HOLE_MXC_50mK_00048.Position 13.2 3 0
SE3_HOLE_MXC_50mK_00048.Mother ColdPlate_MXC_50mK_SD_anchor
SE3_HOLE_MXC_50mK_00048.Visibility 1

// END SE3_HOLE_PATTERN_MXC_50mK

// Volume ColdPlate_CP_100mK_intercept; material=Copper
Volume ColdPlate_CP_100mK_intercept
ColdPlate_CP_100mK_intercept.Material Copper
ColdPlate_CP_100mK_intercept.Visibility 1
ColdPlate_CP_100mK_intercept.Shape PCON 0 360 2 -0.2 0 15 0.2 0 15

ColdPlate_CP_100mK_intercept.Position 0 0 5
ColdPlate_CP_100mK_intercept.Mother InstrumentFrame

// BEGIN SE3_HOLE_PATTERN_CP_100mK
// 48 Vacuum daughters preserve the reviewed 4 mm-array excavated area with far fewer placements.
// Centres remain on the unshifted 6 mm grid; large-hole web/edge/keep-out margins are revalidated.
Volume SE3_HoleTemplate_CP_100mK
SE3_HoleTemplate_CP_100mK.Material Vacuum
SE3_HoleTemplate_CP_100mK.Visibility 1
SE3_HoleTemplate_CP_100mK.Shape PCON 0 360 2 -0.2 0 1.20554275466834 0.2 0 1.20554275466834

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00001
SE3_HOLE_CP_100mK_00001.Position -13.2 -2.4 0
SE3_HOLE_CP_100mK_00001.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00001.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00002
SE3_HOLE_CP_100mK_00002.Position -13.2 2.4 0
SE3_HOLE_CP_100mK_00002.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00002.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00003
SE3_HOLE_CP_100mK_00003.Position -12 -5.4 0
SE3_HOLE_CP_100mK_00003.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00003.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00004
SE3_HOLE_CP_100mK_00004.Position -12 6 0
SE3_HOLE_CP_100mK_00004.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00004.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00005
SE3_HOLE_CP_100mK_00005.Position -10.8 0 0
SE3_HOLE_CP_100mK_00005.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00005.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00006
SE3_HOLE_CP_100mK_00006.Position -10.2 8.4 0
SE3_HOLE_CP_100mK_00006.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00006.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00007
SE3_HOLE_CP_100mK_00007.Position -9 -9.6 0
SE3_HOLE_CP_100mK_00007.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00007.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00008
SE3_HOLE_CP_100mK_00008.Position -8.4 -3 0
SE3_HOLE_CP_100mK_00008.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00008.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00009
SE3_HOLE_CP_100mK_00009.Position -8.4 3 0
SE3_HOLE_CP_100mK_00009.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00009.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00010
SE3_HOLE_CP_100mK_00010.Position -7.8 10.8 0
SE3_HOLE_CP_100mK_00010.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00010.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00011
SE3_HOLE_CP_100mK_00011.Position -7.2 -6.6 0
SE3_HOLE_CP_100mK_00011.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00011.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00012
SE3_HOLE_CP_100mK_00012.Position -6.6 0 0
SE3_HOLE_CP_100mK_00012.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00012.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00013
SE3_HOLE_CP_100mK_00013.Position -6.6 6.6 0
SE3_HOLE_CP_100mK_00013.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00013.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00014
SE3_HOLE_CP_100mK_00014.Position -6 -12 0
SE3_HOLE_CP_100mK_00014.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00014.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00015
SE3_HOLE_CP_100mK_00015.Position -4.8 10.2 0
SE3_HOLE_CP_100mK_00015.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00015.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00016
SE3_HOLE_CP_100mK_00016.Position -4.2 -4.2 0
SE3_HOLE_CP_100mK_00016.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00016.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00017
SE3_HOLE_CP_100mK_00017.Position -4.2 3 0
SE3_HOLE_CP_100mK_00017.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00017.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00018
SE3_HOLE_CP_100mK_00018.Position -3.6 -9.6 0
SE3_HOLE_CP_100mK_00018.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00018.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00019
SE3_HOLE_CP_100mK_00019.Position -3 -12.6 0
SE3_HOLE_CP_100mK_00019.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00019.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00020
SE3_HOLE_CP_100mK_00020.Position -3 -0.6 0
SE3_HOLE_CP_100mK_00020.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00020.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00021
SE3_HOLE_CP_100mK_00021.Position -3 13.2 0
SE3_HOLE_CP_100mK_00021.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00021.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00022
SE3_HOLE_CP_100mK_00022.Position -1.8 9 0
SE3_HOLE_CP_100mK_00022.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00022.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00023
SE3_HOLE_CP_100mK_00023.Position -0.6 -10.2 0
SE3_HOLE_CP_100mK_00023.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00023.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00024
SE3_HOLE_CP_100mK_00024.Position -0.6 -4.2 0
SE3_HOLE_CP_100mK_00024.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00024.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00025
SE3_HOLE_CP_100mK_00025.Position 0 -13.2 0
SE3_HOLE_CP_100mK_00025.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00025.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00026
SE3_HOLE_CP_100mK_00026.Position 0 12.6 0
SE3_HOLE_CP_100mK_00026.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00026.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00027
SE3_HOLE_CP_100mK_00027.Position 0.6 3.6 0
SE3_HOLE_CP_100mK_00027.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00027.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00028
SE3_HOLE_CP_100mK_00028.Position 1.2 -1.2 0
SE3_HOLE_CP_100mK_00028.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00028.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00029
SE3_HOLE_CP_100mK_00029.Position 1.8 9.6 0
SE3_HOLE_CP_100mK_00029.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00029.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00030
SE3_HOLE_CP_100mK_00030.Position 2.4 -5.4 0
SE3_HOLE_CP_100mK_00030.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00030.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00031
SE3_HOLE_CP_100mK_00031.Position 3 13.2 0
SE3_HOLE_CP_100mK_00031.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00031.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00032
SE3_HOLE_CP_100mK_00032.Position 3.6 -9.6 0
SE3_HOLE_CP_100mK_00032.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00032.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00033
SE3_HOLE_CP_100mK_00033.Position 4.2 6.6 0
SE3_HOLE_CP_100mK_00033.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00033.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00034
SE3_HOLE_CP_100mK_00034.Position 4.8 -12.6 0
SE3_HOLE_CP_100mK_00034.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00034.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00035
SE3_HOLE_CP_100mK_00035.Position 4.8 -1.8 0
SE3_HOLE_CP_100mK_00035.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00035.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00036
SE3_HOLE_CP_100mK_00036.Position 4.8 10.2 0
SE3_HOLE_CP_100mK_00036.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00036.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00037
SE3_HOLE_CP_100mK_00037.Position 6.6 -7.8 0
SE3_HOLE_CP_100mK_00037.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00037.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00038
SE3_HOLE_CP_100mK_00038.Position 7.2 7.8 0
SE3_HOLE_CP_100mK_00038.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00038.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00039
SE3_HOLE_CP_100mK_00039.Position 7.8 -4.8 0
SE3_HOLE_CP_100mK_00039.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00039.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00040
SE3_HOLE_CP_100mK_00040.Position 7.8 0.6 0
SE3_HOLE_CP_100mK_00040.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00040.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00041
SE3_HOLE_CP_100mK_00041.Position 7.8 4.8 0
SE3_HOLE_CP_100mK_00041.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00041.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00042
SE3_HOLE_CP_100mK_00042.Position 7.8 10.8 0
SE3_HOLE_CP_100mK_00042.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00042.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00043
SE3_HOLE_CP_100mK_00043.Position 8.4 -10.2 0
SE3_HOLE_CP_100mK_00043.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00043.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00044
SE3_HOLE_CP_100mK_00044.Position 10.8 -0.6 0
SE3_HOLE_CP_100mK_00044.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00044.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00045
SE3_HOLE_CP_100mK_00045.Position 11.4 -7.2 0
SE3_HOLE_CP_100mK_00045.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00045.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00046
SE3_HOLE_CP_100mK_00046.Position 11.4 7.2 0
SE3_HOLE_CP_100mK_00046.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00046.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00047
SE3_HOLE_CP_100mK_00047.Position 13.2 -3 0
SE3_HOLE_CP_100mK_00047.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00047.Visibility 1

SE3_HoleTemplate_CP_100mK.Copy SE3_HOLE_CP_100mK_00048
SE3_HOLE_CP_100mK_00048.Position 13.2 2.4 0
SE3_HOLE_CP_100mK_00048.Mother ColdPlate_CP_100mK_intercept
SE3_HOLE_CP_100mK_00048.Visibility 1

// END SE3_HOLE_PATTERN_CP_100mK

// Volume ColdPlate_Still_0p7K; material=Copper
Volume ColdPlate_Still_0p7K
ColdPlate_Still_0p7K.Material Copper
ColdPlate_Still_0p7K.Visibility 1
ColdPlate_Still_0p7K.Shape PCON 0 360 2 -0.2 0 15 0.2 0 15

ColdPlate_Still_0p7K.Position 0 0 11
ColdPlate_Still_0p7K.Mother InstrumentFrame

// BEGIN SE3_HOLE_PATTERN_Still_0p7K
// 48 Vacuum daughters preserve the reviewed 4 mm-array excavated area with far fewer placements.
// Centres remain on the unshifted 6 mm grid; large-hole web/edge/keep-out margins are revalidated.
Volume SE3_HoleTemplate_Still_0p7K
SE3_HoleTemplate_Still_0p7K.Material Vacuum
SE3_HoleTemplate_Still_0p7K.Visibility 1
SE3_HoleTemplate_Still_0p7K.Shape PCON 0 360 2 -0.2 0 1.14273064776146 0.2 0 1.14273064776146

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00001
SE3_HOLE_Still_0p7K_00001.Position -13.2 0.6 0
SE3_HOLE_Still_0p7K_00001.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00001.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00002
SE3_HOLE_Still_0p7K_00002.Position -12.6 -4.8 0
SE3_HOLE_Still_0p7K_00002.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00002.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00003
SE3_HOLE_Still_0p7K_00003.Position -12.6 3.6 0
SE3_HOLE_Still_0p7K_00003.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00003.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00004
SE3_HOLE_Still_0p7K_00004.Position -11.4 -1.8 0
SE3_HOLE_Still_0p7K_00004.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00004.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00005
SE3_HOLE_Still_0p7K_00005.Position -10.8 -7.8 0
SE3_HOLE_Still_0p7K_00005.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00005.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00006
SE3_HOLE_Still_0p7K_00006.Position -10.8 7.8 0
SE3_HOLE_Still_0p7K_00006.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00006.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00007
SE3_HOLE_Still_0p7K_00007.Position -10.2 0.6 0
SE3_HOLE_Still_0p7K_00007.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00007.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00008
SE3_HOLE_Still_0p7K_00008.Position -10.2 4.8 0
SE3_HOLE_Still_0p7K_00008.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00008.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00009
SE3_HOLE_Still_0p7K_00009.Position -9.6 -5.4 0
SE3_HOLE_Still_0p7K_00009.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00009.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00010
SE3_HOLE_Still_0p7K_00010.Position -9 10.2 0
SE3_HOLE_Still_0p7K_00010.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00010.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00011
SE3_HOLE_Still_0p7K_00011.Position -8.4 -2.4 0
SE3_HOLE_Still_0p7K_00011.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00011.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00012
SE3_HOLE_Still_0p7K_00012.Position -7.8 -10.8 0
SE3_HOLE_Still_0p7K_00012.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00012.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00013
SE3_HOLE_Still_0p7K_00013.Position -7.8 -7.8 0
SE3_HOLE_Still_0p7K_00013.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00013.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00014
SE3_HOLE_Still_0p7K_00014.Position -7.8 1.8 0
SE3_HOLE_Still_0p7K_00014.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00014.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00015
SE3_HOLE_Still_0p7K_00015.Position -6.6 9 0
SE3_HOLE_Still_0p7K_00015.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00015.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00016
SE3_HOLE_Still_0p7K_00016.Position -5.4 -9.6 0
SE3_HOLE_Still_0p7K_00016.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00016.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00017
SE3_HOLE_Still_0p7K_00017.Position -4.8 -12.6 0
SE3_HOLE_Still_0p7K_00017.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00017.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00018
SE3_HOLE_Still_0p7K_00018.Position -4.2 1.2 0
SE3_HOLE_Still_0p7K_00018.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00018.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00019
SE3_HOLE_Still_0p7K_00019.Position -4.2 10.8 0
SE3_HOLE_Still_0p7K_00019.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00019.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00020
SE3_HOLE_Still_0p7K_00020.Position -1.8 -11.4 0
SE3_HOLE_Still_0p7K_00020.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00020.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00021
SE3_HOLE_Still_0p7K_00021.Position -1.2 -4.2 0
SE3_HOLE_Still_0p7K_00021.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00021.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00022
SE3_HOLE_Still_0p7K_00022.Position 0 9.6 0
SE3_HOLE_Still_0p7K_00022.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00022.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00023
SE3_HOLE_Still_0p7K_00023.Position 0 13.2 0
SE3_HOLE_Still_0p7K_00023.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00023.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00024
SE3_HOLE_Still_0p7K_00024.Position 1.2 -13.2 0
SE3_HOLE_Still_0p7K_00024.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00024.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00025
SE3_HOLE_Still_0p7K_00025.Position 1.8 -6 0
SE3_HOLE_Still_0p7K_00025.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00025.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00026
SE3_HOLE_Still_0p7K_00026.Position 2.4 10.8 0
SE3_HOLE_Still_0p7K_00026.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00026.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00027
SE3_HOLE_Still_0p7K_00027.Position 3 7.2 0
SE3_HOLE_Still_0p7K_00027.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00027.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00028
SE3_HOLE_Still_0p7K_00028.Position 3.6 -10.8 0
SE3_HOLE_Still_0p7K_00028.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00028.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00029
SE3_HOLE_Still_0p7K_00029.Position 4.2 -1.2 0
SE3_HOLE_Still_0p7K_00029.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00029.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00030
SE3_HOLE_Still_0p7K_00030.Position 4.8 12.6 0
SE3_HOLE_Still_0p7K_00030.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00030.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00031
SE3_HOLE_Still_0p7K_00031.Position 5.4 -6.6 0
SE3_HOLE_Still_0p7K_00031.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00031.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00032
SE3_HOLE_Still_0p7K_00032.Position 6 9 0
SE3_HOLE_Still_0p7K_00032.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00032.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00033
SE3_HOLE_Still_0p7K_00033.Position 6.6 -11.4 0
SE3_HOLE_Still_0p7K_00033.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00033.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00034
SE3_HOLE_Still_0p7K_00034.Position 7.2 -0.6 0
SE3_HOLE_Still_0p7K_00034.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00034.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00035
SE3_HOLE_Still_0p7K_00035.Position 7.8 -8.4 0
SE3_HOLE_Still_0p7K_00035.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00035.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00036
SE3_HOLE_Still_0p7K_00036.Position 7.8 4.2 0
SE3_HOLE_Still_0p7K_00036.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00036.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00037
SE3_HOLE_Still_0p7K_00037.Position 8.4 -5.4 0
SE3_HOLE_Still_0p7K_00037.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00037.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00038
SE3_HOLE_Still_0p7K_00038.Position 8.4 7.2 0
SE3_HOLE_Still_0p7K_00038.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00038.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00039
SE3_HOLE_Still_0p7K_00039.Position 9 10.2 0
SE3_HOLE_Still_0p7K_00039.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00039.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00040
SE3_HOLE_Still_0p7K_00040.Position 9.6 -2.4 0
SE3_HOLE_Still_0p7K_00040.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00040.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00041
SE3_HOLE_Still_0p7K_00041.Position 9.6 1.2 0
SE3_HOLE_Still_0p7K_00041.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00041.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00042
SE3_HOLE_Still_0p7K_00042.Position 10.8 -7.8 0
SE3_HOLE_Still_0p7K_00042.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00042.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00043
SE3_HOLE_Still_0p7K_00043.Position 10.8 3.6 0
SE3_HOLE_Still_0p7K_00043.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00043.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00044
SE3_HOLE_Still_0p7K_00044.Position 12 -5.4 0
SE3_HOLE_Still_0p7K_00044.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00044.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00045
SE3_HOLE_Still_0p7K_00045.Position 12 -0.6 0
SE3_HOLE_Still_0p7K_00045.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00045.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00046
SE3_HOLE_Still_0p7K_00046.Position 12 6 0
SE3_HOLE_Still_0p7K_00046.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00046.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00047
SE3_HOLE_Still_0p7K_00047.Position 13.2 -3 0
SE3_HOLE_Still_0p7K_00047.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00047.Visibility 1

SE3_HoleTemplate_Still_0p7K.Copy SE3_HOLE_Still_0p7K_00048
SE3_HOLE_Still_0p7K_00048.Position 13.2 1.8 0
SE3_HOLE_Still_0p7K_00048.Mother ColdPlate_Still_0p7K
SE3_HOLE_Still_0p7K_00048.Visibility 1

// END SE3_HOLE_PATTERN_Still_0p7K

// Volume ColdPlate_4K; material=Copper
Volume ColdPlate_4K
ColdPlate_4K.Material Copper
ColdPlate_4K.Visibility 1
ColdPlate_4K.Shape PCON 0 360 2 -0.2 0 17.5 0.2 0 17.5

ColdPlate_4K.Position 0 0 20
ColdPlate_4K.Mother InstrumentFrame

// BEGIN SE3_HOLE_PATTERN_4K
// 48 Vacuum daughters preserve the reviewed 4 mm-array excavated area with far fewer placements.
// Centres remain on the unshifted 6 mm grid; large-hole web/edge/keep-out margins are revalidated.
Volume SE3_HoleTemplate_4K
SE3_HoleTemplate_4K.Material Vacuum
SE3_HoleTemplate_4K.Visibility 1
SE3_HoleTemplate_4K.Shape PCON 0 360 2 -0.2 0 1.26491106406735 0.2 0 1.26491106406735

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00001
SE3_HOLE_4K_00001.Position -15.6 -3.6 0
SE3_HOLE_4K_00001.Mother ColdPlate_4K
SE3_HOLE_4K_00001.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00002
SE3_HOLE_4K_00002.Position -15.6 3.6 0
SE3_HOLE_4K_00002.Mother ColdPlate_4K
SE3_HOLE_4K_00002.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00003
SE3_HOLE_4K_00003.Position -15 0 0
SE3_HOLE_4K_00003.Mother ColdPlate_4K
SE3_HOLE_4K_00003.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00004
SE3_HOLE_4K_00004.Position -14.4 6.6 0
SE3_HOLE_4K_00004.Mother ColdPlate_4K
SE3_HOLE_4K_00004.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00005
SE3_HOLE_4K_00005.Position -13.8 -7.8 0
SE3_HOLE_4K_00005.Mother ColdPlate_4K
SE3_HOLE_4K_00005.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00006
SE3_HOLE_4K_00006.Position -12 10.2 0
SE3_HOLE_4K_00006.Mother ColdPlate_4K
SE3_HOLE_4K_00006.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00007
SE3_HOLE_4K_00007.Position -11.4 -10.8 0
SE3_HOLE_4K_00007.Mother ColdPlate_4K
SE3_HOLE_4K_00007.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00008
SE3_HOLE_4K_00008.Position -11.4 -5.4 0
SE3_HOLE_4K_00008.Mother ColdPlate_4K
SE3_HOLE_4K_00008.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00009
SE3_HOLE_4K_00009.Position -11.4 -1.8 0
SE3_HOLE_4K_00009.Mother ColdPlate_4K
SE3_HOLE_4K_00009.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00010
SE3_HOLE_4K_00010.Position -11.4 2.4 0
SE3_HOLE_4K_00010.Mother ColdPlate_4K
SE3_HOLE_4K_00010.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00011
SE3_HOLE_4K_00011.Position -10.8 7.2 0
SE3_HOLE_4K_00011.Mother ColdPlate_4K
SE3_HOLE_4K_00011.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00012
SE3_HOLE_4K_00012.Position -9 -13.2 0
SE3_HOLE_4K_00012.Mother ColdPlate_4K
SE3_HOLE_4K_00012.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00013
SE3_HOLE_4K_00013.Position -9 12.6 0
SE3_HOLE_4K_00013.Mother ColdPlate_4K
SE3_HOLE_4K_00013.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00014
SE3_HOLE_4K_00014.Position -8.4 -9.6 0
SE3_HOLE_4K_00014.Mother ColdPlate_4K
SE3_HOLE_4K_00014.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00015
SE3_HOLE_4K_00015.Position -8.4 9.6 0
SE3_HOLE_4K_00015.Mother ColdPlate_4K
SE3_HOLE_4K_00015.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00016
SE3_HOLE_4K_00016.Position -6 -12 0
SE3_HOLE_4K_00016.Mother ColdPlate_4K
SE3_HOLE_4K_00016.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00017
SE3_HOLE_4K_00017.Position -5.4 -15 0
SE3_HOLE_4K_00017.Mother ColdPlate_4K
SE3_HOLE_4K_00017.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00018
SE3_HOLE_4K_00018.Position -5.4 11.4 0
SE3_HOLE_4K_00018.Mother ColdPlate_4K
SE3_HOLE_4K_00018.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00019
SE3_HOLE_4K_00019.Position -3.6 14.4 0
SE3_HOLE_4K_00019.Mother ColdPlate_4K
SE3_HOLE_4K_00019.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00020
SE3_HOLE_4K_00020.Position -3 -12.6 0
SE3_HOLE_4K_00020.Mother ColdPlate_4K
SE3_HOLE_4K_00020.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00021
SE3_HOLE_4K_00021.Position -1.8 -15.6 0
SE3_HOLE_4K_00021.Mother ColdPlate_4K
SE3_HOLE_4K_00021.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00022
SE3_HOLE_4K_00022.Position -0.6 13.2 0
SE3_HOLE_4K_00022.Mother ColdPlate_4K
SE3_HOLE_4K_00022.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00023
SE3_HOLE_4K_00023.Position 0 10.2 0
SE3_HOLE_4K_00023.Mother ColdPlate_4K
SE3_HOLE_4K_00023.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00024
SE3_HOLE_4K_00024.Position 0.6 -13.2 0
SE3_HOLE_4K_00024.Mother ColdPlate_4K
SE3_HOLE_4K_00024.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00025
SE3_HOLE_4K_00025.Position 1.8 15.6 0
SE3_HOLE_4K_00025.Mother ColdPlate_4K
SE3_HOLE_4K_00025.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00026
SE3_HOLE_4K_00026.Position 3 12.6 0
SE3_HOLE_4K_00026.Mother ColdPlate_4K
SE3_HOLE_4K_00026.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00027
SE3_HOLE_4K_00027.Position 3.6 -15.6 0
SE3_HOLE_4K_00027.Mother ColdPlate_4K
SE3_HOLE_4K_00027.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00028
SE3_HOLE_4K_00028.Position 4.2 -12 0
SE3_HOLE_4K_00028.Mother ColdPlate_4K
SE3_HOLE_4K_00028.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00029
SE3_HOLE_4K_00029.Position 5.4 15 0
SE3_HOLE_4K_00029.Mother ColdPlate_4K
SE3_HOLE_4K_00029.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00030
SE3_HOLE_4K_00030.Position 6 10.8 0
SE3_HOLE_4K_00030.Mother ColdPlate_4K
SE3_HOLE_4K_00030.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00031
SE3_HOLE_4K_00031.Position 7.2 -13.8 0
SE3_HOLE_4K_00031.Mother ColdPlate_4K
SE3_HOLE_4K_00031.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00032
SE3_HOLE_4K_00032.Position 7.8 -8.4 0
SE3_HOLE_4K_00032.Mother ColdPlate_4K
SE3_HOLE_4K_00032.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00033
SE3_HOLE_4K_00033.Position 8.4 -4.2 0
SE3_HOLE_4K_00033.Mother ColdPlate_4K
SE3_HOLE_4K_00033.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00034
SE3_HOLE_4K_00034.Position 8.4 3.6 0
SE3_HOLE_4K_00034.Mother ColdPlate_4K
SE3_HOLE_4K_00034.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00035
SE3_HOLE_4K_00035.Position 9 -0.6 0
SE3_HOLE_4K_00035.Mother ColdPlate_4K
SE3_HOLE_4K_00035.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00036
SE3_HOLE_4K_00036.Position 9 9 0
SE3_HOLE_4K_00036.Mother ColdPlate_4K
SE3_HOLE_4K_00036.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00037
SE3_HOLE_4K_00037.Position 9.6 12.6 0
SE3_HOLE_4K_00037.Mother ColdPlate_4K
SE3_HOLE_4K_00037.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00038
SE3_HOLE_4K_00038.Position 10.2 -12 0
SE3_HOLE_4K_00038.Mother ColdPlate_4K
SE3_HOLE_4K_00038.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00039
SE3_HOLE_4K_00039.Position 11.4 -6 0
SE3_HOLE_4K_00039.Mother ColdPlate_4K
SE3_HOLE_4K_00039.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00040
SE3_HOLE_4K_00040.Position 11.4 6 0
SE3_HOLE_4K_00040.Mother ColdPlate_4K
SE3_HOLE_4K_00040.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00041
SE3_HOLE_4K_00041.Position 12 -2.4 0
SE3_HOLE_4K_00041.Mother ColdPlate_4K
SE3_HOLE_4K_00041.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00042
SE3_HOLE_4K_00042.Position 12 1.8 0
SE3_HOLE_4K_00042.Mother ColdPlate_4K
SE3_HOLE_4K_00042.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00043
SE3_HOLE_4K_00043.Position 12.6 -9.6 0
SE3_HOLE_4K_00043.Mother ColdPlate_4K
SE3_HOLE_4K_00043.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00044
SE3_HOLE_4K_00044.Position 12.6 9.6 0
SE3_HOLE_4K_00044.Mother ColdPlate_4K
SE3_HOLE_4K_00044.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00045
SE3_HOLE_4K_00045.Position 14.4 6.6 0
SE3_HOLE_4K_00045.Mother ColdPlate_4K
SE3_HOLE_4K_00045.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00046
SE3_HOLE_4K_00046.Position 15 -5.4 0
SE3_HOLE_4K_00046.Mother ColdPlate_4K
SE3_HOLE_4K_00046.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00047
SE3_HOLE_4K_00047.Position 15.6 -0.6 0
SE3_HOLE_4K_00047.Mother ColdPlate_4K
SE3_HOLE_4K_00047.Visibility 1

SE3_HoleTemplate_4K.Copy SE3_HOLE_4K_00048
SE3_HOLE_4K_00048.Position 15.6 3.6 0
SE3_HOLE_4K_00048.Mother ColdPlate_4K
SE3_HOLE_4K_00048.Visibility 1

// END SE3_HOLE_PATTERN_4K

// Volume ColdPlate_60K; material=Aluminium
Volume ColdPlate_60K
ColdPlate_60K.Material Aluminium
ColdPlate_60K.Visibility 1
ColdPlate_60K.Shape PCON 0 360 2 -0.2 0 17.5 0.2 0 17.5

ColdPlate_60K.Position 0 0 29
ColdPlate_60K.Mother InstrumentFrame

// BEGIN SE3_HOLE_PATTERN_60K
// 48 Vacuum daughters preserve the reviewed 4 mm-array excavated area with far fewer placements.
// Centres remain on the unshifted 6 mm grid; large-hole web/edge/keep-out margins are revalidated.
Volume SE3_HoleTemplate_60K
SE3_HoleTemplate_60K.Material Vacuum
SE3_HoleTemplate_60K.Visibility 1
SE3_HoleTemplate_60K.Shape PCON 0 360 2 -0.2 0 1.29034879005639 0.2 0 1.29034879005639

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00001
SE3_HOLE_60K_00001.Position -15.6 -2.4 0
SE3_HOLE_60K_00001.Mother ColdPlate_60K
SE3_HOLE_60K_00001.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00002
SE3_HOLE_60K_00002.Position -15.6 1.8 0
SE3_HOLE_60K_00002.Mother ColdPlate_60K
SE3_HOLE_60K_00002.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00003
SE3_HOLE_60K_00003.Position -15 5.4 0
SE3_HOLE_60K_00003.Mother ColdPlate_60K
SE3_HOLE_60K_00003.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00004
SE3_HOLE_60K_00004.Position -14.4 -6 0
SE3_HOLE_60K_00004.Mother ColdPlate_60K
SE3_HOLE_60K_00004.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00005
SE3_HOLE_60K_00005.Position -13.2 9 0
SE3_HOLE_60K_00005.Mother ColdPlate_60K
SE3_HOLE_60K_00005.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00006
SE3_HOLE_60K_00006.Position -12.6 0 0
SE3_HOLE_60K_00006.Mother ColdPlate_60K
SE3_HOLE_60K_00006.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00007
SE3_HOLE_60K_00007.Position -12 -3.6 0
SE3_HOLE_60K_00007.Mother ColdPlate_60K
SE3_HOLE_60K_00007.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00008
SE3_HOLE_60K_00008.Position -12 3.6 0
SE3_HOLE_60K_00008.Mother ColdPlate_60K
SE3_HOLE_60K_00008.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00009
SE3_HOLE_60K_00009.Position -11.4 -10.8 0
SE3_HOLE_60K_00009.Mother ColdPlate_60K
SE3_HOLE_60K_00009.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00010
SE3_HOLE_60K_00010.Position -10.8 11.4 0
SE3_HOLE_60K_00010.Mother ColdPlate_60K
SE3_HOLE_60K_00010.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00011
SE3_HOLE_60K_00011.Position -10.2 8.4 0
SE3_HOLE_60K_00011.Mother ColdPlate_60K
SE3_HOLE_60K_00011.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00012
SE3_HOLE_60K_00012.Position -8.4 -12 0
SE3_HOLE_60K_00012.Mother ColdPlate_60K
SE3_HOLE_60K_00012.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00013
SE3_HOLE_60K_00013.Position -8.4 -4.2 0
SE3_HOLE_60K_00013.Mother ColdPlate_60K
SE3_HOLE_60K_00013.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00014
SE3_HOLE_60K_00014.Position -7.8 13.8 0
SE3_HOLE_60K_00014.Mother ColdPlate_60K
SE3_HOLE_60K_00014.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00015
SE3_HOLE_60K_00015.Position -6.6 -14.4 0
SE3_HOLE_60K_00015.Mother ColdPlate_60K
SE3_HOLE_60K_00015.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00016
SE3_HOLE_60K_00016.Position -4.8 12 0
SE3_HOLE_60K_00016.Mother ColdPlate_60K
SE3_HOLE_60K_00016.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00017
SE3_HOLE_60K_00017.Position -3.6 -8.4 0
SE3_HOLE_60K_00017.Mother ColdPlate_60K
SE3_HOLE_60K_00017.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00018
SE3_HOLE_60K_00018.Position -3 -14.4 0
SE3_HOLE_60K_00018.Mother ColdPlate_60K
SE3_HOLE_60K_00018.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00019
SE3_HOLE_60K_00019.Position -2.4 14.4 0
SE3_HOLE_60K_00019.Mother ColdPlate_60K
SE3_HOLE_60K_00019.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00020
SE3_HOLE_60K_00020.Position -1.2 7.8 0
SE3_HOLE_60K_00020.Mother ColdPlate_60K
SE3_HOLE_60K_00020.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00021
SE3_HOLE_60K_00021.Position -0.6 -7.8 0
SE3_HOLE_60K_00021.Mother ColdPlate_60K
SE3_HOLE_60K_00021.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00022
SE3_HOLE_60K_00022.Position 0 -15.6 0
SE3_HOLE_60K_00022.Mother ColdPlate_60K
SE3_HOLE_60K_00022.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00023
SE3_HOLE_60K_00023.Position 0.6 12 0
SE3_HOLE_60K_00023.Mother ColdPlate_60K
SE3_HOLE_60K_00023.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00024
SE3_HOLE_60K_00024.Position 3 -15 0
SE3_HOLE_60K_00024.Mother ColdPlate_60K
SE3_HOLE_60K_00024.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00025
SE3_HOLE_60K_00025.Position 3 15.6 0
SE3_HOLE_60K_00025.Mother ColdPlate_60K
SE3_HOLE_60K_00025.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00026
SE3_HOLE_60K_00026.Position 3.6 -8.4 0
SE3_HOLE_60K_00026.Mother ColdPlate_60K
SE3_HOLE_60K_00026.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00027
SE3_HOLE_60K_00027.Position 3.6 7.8 0
SE3_HOLE_60K_00027.Mother ColdPlate_60K
SE3_HOLE_60K_00027.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00028
SE3_HOLE_60K_00028.Position 4.2 12 0
SE3_HOLE_60K_00028.Mother ColdPlate_60K
SE3_HOLE_60K_00028.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00029
SE3_HOLE_60K_00029.Position 6 -14.4 0
SE3_HOLE_60K_00029.Mother ColdPlate_60K
SE3_HOLE_60K_00029.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00030
SE3_HOLE_60K_00030.Position 6.6 14.4 0
SE3_HOLE_60K_00030.Mother ColdPlate_60K
SE3_HOLE_60K_00030.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00031
SE3_HOLE_60K_00031.Position 7.2 10.8 0
SE3_HOLE_60K_00031.Mother ColdPlate_60K
SE3_HOLE_60K_00031.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00032
SE3_HOLE_60K_00032.Position 7.8 -10.2 0
SE3_HOLE_60K_00032.Mother ColdPlate_60K
SE3_HOLE_60K_00032.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00033
SE3_HOLE_60K_00033.Position 7.8 -0.6 0
SE3_HOLE_60K_00033.Mother ColdPlate_60K
SE3_HOLE_60K_00033.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00034
SE3_HOLE_60K_00034.Position 7.8 3.6 0
SE3_HOLE_60K_00034.Mother ColdPlate_60K
SE3_HOLE_60K_00034.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00035
SE3_HOLE_60K_00035.Position 8.4 -3.6 0
SE3_HOLE_60K_00035.Mother ColdPlate_60K
SE3_HOLE_60K_00035.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00036
SE3_HOLE_60K_00036.Position 9 -13.2 0
SE3_HOLE_60K_00036.Mother ColdPlate_60K
SE3_HOLE_60K_00036.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00037
SE3_HOLE_60K_00037.Position 10.2 -6.6 0
SE3_HOLE_60K_00037.Mother ColdPlate_60K
SE3_HOLE_60K_00037.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00038
SE3_HOLE_60K_00038.Position 10.2 7.8 0
SE3_HOLE_60K_00038.Mother ColdPlate_60K
SE3_HOLE_60K_00038.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00039
SE3_HOLE_60K_00039.Position 10.8 11.4 0
SE3_HOLE_60K_00039.Mother ColdPlate_60K
SE3_HOLE_60K_00039.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00040
SE3_HOLE_60K_00040.Position 11.4 -3 0
SE3_HOLE_60K_00040.Mother ColdPlate_60K
SE3_HOLE_60K_00040.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00041
SE3_HOLE_60K_00041.Position 12 -10.2 0
SE3_HOLE_60K_00041.Mother ColdPlate_60K
SE3_HOLE_60K_00041.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00042
SE3_HOLE_60K_00042.Position 12 0.6 0
SE3_HOLE_60K_00042.Mother ColdPlate_60K
SE3_HOLE_60K_00042.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00043
SE3_HOLE_60K_00043.Position 12 4.8 0
SE3_HOLE_60K_00043.Mother ColdPlate_60K
SE3_HOLE_60K_00043.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00044
SE3_HOLE_60K_00044.Position 13.2 9 0
SE3_HOLE_60K_00044.Mother ColdPlate_60K
SE3_HOLE_60K_00044.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00045
SE3_HOLE_60K_00045.Position 14.4 -6.6 0
SE3_HOLE_60K_00045.Mother ColdPlate_60K
SE3_HOLE_60K_00045.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00046
SE3_HOLE_60K_00046.Position 15 5.4 0
SE3_HOLE_60K_00046.Mother ColdPlate_60K
SE3_HOLE_60K_00046.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00047
SE3_HOLE_60K_00047.Position 15.6 -2.4 0
SE3_HOLE_60K_00047.Mother ColdPlate_60K
SE3_HOLE_60K_00047.Visibility 1

SE3_HoleTemplate_60K.Copy SE3_HOLE_60K_00048
SE3_HOLE_60K_00048.Position 15.6 2.4 0
SE3_HOLE_60K_00048.Mother ColdPlate_60K
SE3_HOLE_60K_00048.Visibility 1

// END SE3_HOLE_PATTERN_60K

// Volume Plate_300K_Top_Service_Lid; material=Aluminium
Volume Plate_300K_Top_Service_Lid
Plate_300K_Top_Service_Lid.Material Aluminium
Plate_300K_Top_Service_Lid.Visibility 1
Plate_300K_Top_Service_Lid.Shape PCON 0 360 2 -0.3 0 20 0.3 0 20

Plate_300K_Top_Service_Lid.Position 0 0 38
Plate_300K_Top_Service_Lid.Mother InstrumentFrame

// BEGIN XS400_GROUP1_INTER_COLD_PLATE_SUPPORT_RODS_PROXY
// Added 2026-06-30: XS400 group 1 inter-cold-plate support rods.
// Mass-preserving equivalent-cylinder proxy: z length follows this geometry's plate gaps;
// radius is back-calculated from each XS400 CAD rod volume. Small pads/brackets are omitted.
// Volume XS400_Group1_SupportRod_50mK_to_100mK_01; source=Part-004; family=50mK_to_100mK; volume_cm3=9.79869; mass_g=78.3895
Volume XS400_Group1_SupportRod_50mK_to_100mK_01
XS400_Group1_SupportRod_50mK_to_100mK_01.Material StainlessSteel
XS400_Group1_SupportRod_50mK_to_100mK_01.Visibility 1
XS400_Group1_SupportRod_50mK_to_100mK_01.Shape PCON 0 360 2 -2.18 0 0.845796179 2.18 0 0.845796179
XS400_Group1_SupportRod_50mK_to_100mK_01.Position 6.16701521 2.24460997 2.5
XS400_Group1_SupportRod_50mK_to_100mK_01.Mother InstrumentFrame

// Volume XS400_Group1_SupportRod_50mK_to_100mK_02; source=Part-005; family=50mK_to_100mK; volume_cm3=9.79869; mass_g=78.3895
Volume XS400_Group1_SupportRod_50mK_to_100mK_02
XS400_Group1_SupportRod_50mK_to_100mK_02.Material StainlessSteel
XS400_Group1_SupportRod_50mK_to_100mK_02.Visibility 1
XS400_Group1_SupportRod_50mK_to_100mK_02.Shape PCON 0 360 2 -2.18 0 0.845796179 2.18 0 0.845796179
XS400_Group1_SupportRod_50mK_to_100mK_02.Position -6.16701521 -2.24460997 2.5
XS400_Group1_SupportRod_50mK_to_100mK_02.Mother InstrumentFrame

// Volume XS400_Group1_SupportRod_50mK_to_100mK_03; source=Part-006; family=50mK_to_100mK; volume_cm3=9.79869; mass_g=78.3895
Volume XS400_Group1_SupportRod_50mK_to_100mK_03
XS400_Group1_SupportRod_50mK_to_100mK_03.Material StainlessSteel
XS400_Group1_SupportRod_50mK_to_100mK_03.Visibility 1
XS400_Group1_SupportRod_50mK_to_100mK_03.Shape PCON 0 360 2 -2.18 0 0.845796179 2.18 0 0.845796179
XS400_Group1_SupportRod_50mK_to_100mK_03.Position -1.13961835 -6.46309682 2.5
XS400_Group1_SupportRod_50mK_to_100mK_03.Mother InstrumentFrame

// Volume XS400_Group1_SupportRod_50mK_to_100mK_04; source=Part-11; family=50mK_to_100mK; volume_cm3=9.79869; mass_g=78.3895
Volume XS400_Group1_SupportRod_50mK_to_100mK_04
XS400_Group1_SupportRod_50mK_to_100mK_04.Material StainlessSteel
XS400_Group1_SupportRod_50mK_to_100mK_04.Visibility 1
XS400_Group1_SupportRod_50mK_to_100mK_04.Shape PCON 0 360 2 -2.18 0 0.845796179 2.18 0 0.845796179
XS400_Group1_SupportRod_50mK_to_100mK_04.Position 5.02739686 -4.21848685 2.5
XS400_Group1_SupportRod_50mK_to_100mK_04.Mother InstrumentFrame

// Volume XS400_Group1_SupportRod_100mK_to_Still_01; source=Part-001; family=100mK_to_Still; volume_cm3=11.2764; mass_g=90.2113
Volume XS400_Group1_SupportRod_100mK_to_Still_01
XS400_Group1_SupportRod_100mK_to_Still_01.Material StainlessSteel
XS400_Group1_SupportRod_100mK_to_Still_01.Visibility 1
XS400_Group1_SupportRod_100mK_to_Still_01.Shape PCON 0 360 2 -2.68 0 0.818329356 2.68 0 0.818329356
XS400_Group1_SupportRod_100mK_to_Still_01.Position 6.19112313 2.25338454 8
XS400_Group1_SupportRod_100mK_to_Still_01.Mother InstrumentFrame

// Volume XS400_Group1_SupportRod_100mK_to_Still_02; source=Part-002; family=100mK_to_Still; volume_cm3=11.2764; mass_g=90.2113
Volume XS400_Group1_SupportRod_100mK_to_Still_02
XS400_Group1_SupportRod_100mK_to_Still_02.Material StainlessSteel
XS400_Group1_SupportRod_100mK_to_Still_02.Visibility 1
XS400_Group1_SupportRod_100mK_to_Still_02.Shape PCON 0 360 2 -2.68 0 0.818329356 2.68 0 0.818329356
XS400_Group1_SupportRod_100mK_to_Still_02.Position -6.19112313 -2.25338454 8
XS400_Group1_SupportRod_100mK_to_Still_02.Mother InstrumentFrame

// Volume XS400_Group1_SupportRod_100mK_to_Still_03; source=Part-003; family=100mK_to_Still; volume_cm3=11.2764; mass_g=90.2113
Volume XS400_Group1_SupportRod_100mK_to_Still_03
XS400_Group1_SupportRod_100mK_to_Still_03.Material StainlessSteel
XS400_Group1_SupportRod_100mK_to_Still_03.Visibility 1
XS400_Group1_SupportRod_100mK_to_Still_03.Shape PCON 0 360 2 -2.68 0 0.818329356 2.68 0 0.818329356
XS400_Group1_SupportRod_100mK_to_Still_03.Position -1.14407331 -6.48836217 8
XS400_Group1_SupportRod_100mK_to_Still_03.Mother InstrumentFrame

// Volume XS400_Group1_SupportRod_100mK_to_Still_04; source=Part-10; family=100mK_to_Still; volume_cm3=11.2764; mass_g=90.2113
Volume XS400_Group1_SupportRod_100mK_to_Still_04
XS400_Group1_SupportRod_100mK_to_Still_04.Material StainlessSteel
XS400_Group1_SupportRod_100mK_to_Still_04.Visibility 1
XS400_Group1_SupportRod_100mK_to_Still_04.Shape PCON 0 360 2 -2.68 0 0.818329356 2.68 0 0.818329356
XS400_Group1_SupportRod_100mK_to_Still_04.Position 5.04704982 -4.23497764 8
XS400_Group1_SupportRod_100mK_to_Still_04.Mother InstrumentFrame

// Volume XS400_Group1_SupportRod_Still_to_4K_single_edge_01; source=Part-204 split 1/4; family=Still_to_4K_single_edge; volume_cm3=35.5376603; mass_g=284.301283
Volume XS400_Group1_SupportRod_Still_to_4K_single_edge_01
XS400_Group1_SupportRod_Still_to_4K_single_edge_01.Material StainlessSteel
XS400_Group1_SupportRod_Still_to_4K_single_edge_01.Visibility 1
XS400_Group1_SupportRod_Still_to_4K_single_edge_01.Shape PCON 0 360 2 -4.18 0 1.163232 4.18 0 1.163232
XS400_Group1_SupportRod_Still_to_4K_single_edge_01.Position 4.29855997 4.29855997 15.5
XS400_Group1_SupportRod_Still_to_4K_single_edge_01.Mother InstrumentFrame
// Volume XS400_Group1_SupportRod_Still_to_4K_single_edge_02; source=Part-204 split 2/4; family=Still_to_4K_single_edge; volume_cm3=35.5376603; mass_g=284.301283
Volume XS400_Group1_SupportRod_Still_to_4K_single_edge_02
XS400_Group1_SupportRod_Still_to_4K_single_edge_02.Material StainlessSteel
XS400_Group1_SupportRod_Still_to_4K_single_edge_02.Visibility 1
XS400_Group1_SupportRod_Still_to_4K_single_edge_02.Shape PCON 0 360 2 -4.18 0 1.163232 4.18 0 1.163232
XS400_Group1_SupportRod_Still_to_4K_single_edge_02.Position -4.29855997 4.29855997 15.5
XS400_Group1_SupportRod_Still_to_4K_single_edge_02.Mother InstrumentFrame

// Volume XS400_Group1_SupportRod_Still_to_4K_single_edge_03; source=Part-204 split 3/4; family=Still_to_4K_single_edge; volume_cm3=35.5376603; mass_g=284.301283
Volume XS400_Group1_SupportRod_Still_to_4K_single_edge_03
XS400_Group1_SupportRod_Still_to_4K_single_edge_03.Material StainlessSteel
XS400_Group1_SupportRod_Still_to_4K_single_edge_03.Visibility 1
XS400_Group1_SupportRod_Still_to_4K_single_edge_03.Shape PCON 0 360 2 -4.18 0 1.163232 4.18 0 1.163232
XS400_Group1_SupportRod_Still_to_4K_single_edge_03.Position -4.29855997 -4.29855997 15.5
XS400_Group1_SupportRod_Still_to_4K_single_edge_03.Mother InstrumentFrame

// Volume XS400_Group1_SupportRod_Still_to_4K_single_edge_04; source=Part-204 split 4/4; family=Still_to_4K_single_edge; volume_cm3=35.5376603; mass_g=284.301283
Volume XS400_Group1_SupportRod_Still_to_4K_single_edge_04
XS400_Group1_SupportRod_Still_to_4K_single_edge_04.Material StainlessSteel
XS400_Group1_SupportRod_Still_to_4K_single_edge_04.Visibility 1
XS400_Group1_SupportRod_Still_to_4K_single_edge_04.Shape PCON 0 360 2 -4.18 0 1.163232 4.18 0 1.163232
XS400_Group1_SupportRod_Still_to_4K_single_edge_04.Position 4.29855997 -4.29855997 15.5
XS400_Group1_SupportRod_Still_to_4K_single_edge_04.Mother InstrumentFrame

// Volume XS400_Group1_SupportRod_4K_to_60K_01; source=Part-173; family=4K_to_60K; volume_cm3=46.4547; mass_g=371.638
Volume XS400_Group1_SupportRod_4K_to_60K_01
XS400_Group1_SupportRod_4K_to_60K_01.Material StainlessSteel
XS400_Group1_SupportRod_4K_to_60K_01.Visibility 1
XS400_Group1_SupportRod_4K_to_60K_01.Shape PCON 0 360 2 -4.18 0 1.32995485 4.18 0 1.32995485
XS400_Group1_SupportRod_4K_to_60K_01.Position 6.13008476 6.13008476 24.5
XS400_Group1_SupportRod_4K_to_60K_01.Mother InstrumentFrame

// Volume XS400_Group1_SupportRod_4K_to_60K_02; source=Part-174; family=4K_to_60K; volume_cm3=46.4547; mass_g=371.638
Volume XS400_Group1_SupportRod_4K_to_60K_02
XS400_Group1_SupportRod_4K_to_60K_02.Material StainlessSteel
XS400_Group1_SupportRod_4K_to_60K_02.Visibility 1
XS400_Group1_SupportRod_4K_to_60K_02.Shape PCON 0 360 2 -4.18 0 1.32995485 4.18 0 1.32995485
XS400_Group1_SupportRod_4K_to_60K_02.Position -6.13008476 6.13008476 24.5
XS400_Group1_SupportRod_4K_to_60K_02.Mother InstrumentFrame

// Volume XS400_Group1_SupportRod_4K_to_60K_03; source=Part-175; family=4K_to_60K; volume_cm3=46.4547; mass_g=371.638
Volume XS400_Group1_SupportRod_4K_to_60K_03
XS400_Group1_SupportRod_4K_to_60K_03.Material StainlessSteel
XS400_Group1_SupportRod_4K_to_60K_03.Visibility 1
XS400_Group1_SupportRod_4K_to_60K_03.Shape PCON 0 360 2 -4.18 0 1.32995485 4.18 0 1.32995485
XS400_Group1_SupportRod_4K_to_60K_03.Position -6.13008476 -6.13008476 24.5
XS400_Group1_SupportRod_4K_to_60K_03.Mother InstrumentFrame

// Volume XS400_Group1_SupportRod_4K_to_60K_04; source=Part-63; family=4K_to_60K; volume_cm3=46.4547; mass_g=371.638
Volume XS400_Group1_SupportRod_4K_to_60K_04
XS400_Group1_SupportRod_4K_to_60K_04.Material StainlessSteel
XS400_Group1_SupportRod_4K_to_60K_04.Visibility 1
XS400_Group1_SupportRod_4K_to_60K_04.Shape PCON 0 360 2 -4.18 0 1.32995485 4.18 0 1.32995485
XS400_Group1_SupportRod_4K_to_60K_04.Position 6.13008476 -6.13008476 24.5
XS400_Group1_SupportRod_4K_to_60K_04.Mother InstrumentFrame

// Volume XS400_Group1_SupportRod_60K_to_300K_01; source=Part-170; family=60K_to_300K; volume_cm3=35.0319; mass_g=280.255
Volume XS400_Group1_SupportRod_60K_to_300K_01
XS400_Group1_SupportRod_60K_to_300K_01.Material StainlessSteel
XS400_Group1_SupportRod_60K_to_300K_01.Visibility 1
XS400_Group1_SupportRod_60K_to_300K_01.Shape PCON 0 360 2 -4.18 0 1.15492496 4.18 0 1.15492496
XS400_Group1_SupportRod_60K_to_300K_01.Position 7.3046183 7.3046183 33.5
XS400_Group1_SupportRod_60K_to_300K_01.Mother InstrumentFrame

// Volume XS400_Group1_SupportRod_60K_to_300K_02; source=Part-171; family=60K_to_300K; volume_cm3=35.0319; mass_g=280.255
Volume XS400_Group1_SupportRod_60K_to_300K_02
XS400_Group1_SupportRod_60K_to_300K_02.Material StainlessSteel
XS400_Group1_SupportRod_60K_to_300K_02.Visibility 1
XS400_Group1_SupportRod_60K_to_300K_02.Shape PCON 0 360 2 -4.18 0 1.15492496 4.18 0 1.15492496
XS400_Group1_SupportRod_60K_to_300K_02.Position -7.3046183 7.3046183 33.5
XS400_Group1_SupportRod_60K_to_300K_02.Mother InstrumentFrame

// Volume XS400_Group1_SupportRod_60K_to_300K_03; source=Part-172; family=60K_to_300K; volume_cm3=35.0319; mass_g=280.255
Volume XS400_Group1_SupportRod_60K_to_300K_03
XS400_Group1_SupportRod_60K_to_300K_03.Material StainlessSteel
XS400_Group1_SupportRod_60K_to_300K_03.Visibility 1
XS400_Group1_SupportRod_60K_to_300K_03.Shape PCON 0 360 2 -4.18 0 1.15492496 4.18 0 1.15492496
XS400_Group1_SupportRod_60K_to_300K_03.Position -7.3046183 -7.3046183 33.5
XS400_Group1_SupportRod_60K_to_300K_03.Mother InstrumentFrame

// Volume XS400_Group1_SupportRod_60K_to_300K_04; source=Part-62; family=60K_to_300K; volume_cm3=35.0319; mass_g=280.255
Volume XS400_Group1_SupportRod_60K_to_300K_04
XS400_Group1_SupportRod_60K_to_300K_04.Material StainlessSteel
XS400_Group1_SupportRod_60K_to_300K_04.Visibility 1
XS400_Group1_SupportRod_60K_to_300K_04.Shape PCON 0 360 2 -4.18 0 1.15492496 4.18 0 1.15492496
XS400_Group1_SupportRod_60K_to_300K_04.Position 7.3046183 -7.3046183 33.5
XS400_Group1_SupportRod_60K_to_300K_04.Mother InstrumentFrame

// END XS400_GROUP1_INTER_COLD_PLATE_SUPPORT_RODS_PROXY












// BEGIN XS400_GROUP2_TOP_SCALED_PROXY
// Added 2026-06-30: XS400 group 2 spring/retainer/contact-stack mass proxy.
// Coarse solid mass proxy: PCON and BRIK shapes preserve material volume and mass.
// Rule: split source groups by XS400 z relative to the 50K stage, scale by local
// project/reference cold-plate area ratio, and keep the XS400 groups' offset character.
// source_layout_axis_xy_mm=[135.0, 0.0]; xs400_split_z_mm=-637
// band=lower_4K_to_60K; ColdPlate_4K -> ColdPlate_60K; area_scale=(10.4/20)^2=0.2704; layout_max_radius_cm=7.95; z=20.4..28.6
// band=upper_60K_to_300K; ColdPlate_60K -> Plate_300K_Top_Service_Lid; area_scale=(11.9/24)^2=0.245850694; layout_max_radius_cm=8.75; z=29.45..37.45
// Volume XS400_Group2_Cu_Coarse_LowerOpenCollar_4K60K; kind=PCON_annular_sector; source=aggregate:lower copper flange/collar source parts; band=4K_to_60K; source_material=Copper_aggregate; scaled_volume_cm3=121.951; scaled_mass_g=1092.68
Volume XS400_Group2_Cu_Coarse_LowerOpenCollar_4K60K
XS400_Group2_Cu_Coarse_LowerOpenCollar_4K60K.Material Copper
XS400_Group2_Cu_Coarse_LowerOpenCollar_4K60K.Visibility 1
XS400_Group2_Cu_Coarse_LowerOpenCollar_4K60K.Shape PCON 230 260 2 -0.65 3.2 7.1822672 0.65 3.2 7.1822672
XS400_Group2_Cu_Coarse_LowerOpenCollar_4K60K.Position 0 0 21.1
XS400_Group2_Cu_Coarse_LowerOpenCollar_4K60K.Mother InstrumentFrame

// Volume XS400_Group2_Cu_Coarse_MainVerticalStack_4K60K; kind=PCON_cylinder; source=aggregate:Part-246/240/271/248; band=4K_to_60K; source_material=Copper_aggregate; scaled_volume_cm3=140.244; scaled_mass_g=1256.59
Volume XS400_Group2_Cu_Coarse_MainVerticalStack_4K60K
XS400_Group2_Cu_Coarse_MainVerticalStack_4K60K.Material Copper
XS400_Group2_Cu_Coarse_MainVerticalStack_4K60K.Visibility 1
XS400_Group2_Cu_Coarse_MainVerticalStack_4K60K.Shape PCON 0 360 2 -1.65 0 3.67798835 1.65 0 3.67798835
XS400_Group2_Cu_Coarse_MainVerticalStack_4K60K.Position 0 0 24.45
XS400_Group2_Cu_Coarse_MainVerticalStack_4K60K.Mother InstrumentFrame

// Volume XS400_Group2_Cu_Coarse_SideSleeve_4K60K; kind=PCON_cylinder; source=aggregate:Part-288/212/221; band=4K_to_60K; source_material=Copper_aggregate; scaled_volume_cm3=103.659; scaled_mass_g=928.782
Volume XS400_Group2_Cu_Coarse_SideSleeve_4K60K
XS400_Group2_Cu_Coarse_SideSleeve_4K60K.Material Copper
XS400_Group2_Cu_Coarse_SideSleeve_4K60K.Visibility 1
XS400_Group2_Cu_Coarse_SideSleeve_4K60K.Shape PCON 0 360 2 -1.65 0 3.16206572 1.65 0 3.16206572
XS400_Group2_Cu_Coarse_SideSleeve_4K60K.Position 0 -7.2 24.45
XS400_Group2_Cu_Coarse_SideSleeve_4K60K.Mother InstrumentFrame

// Volume XS400_Group2_Cu_Coarse_NorthContactBlock_4K60K; kind=BRIK_offset_block; source=aggregate:small lower-band Cu brackets; band=4K_to_60K; source_material=Copper_aggregate; scaled_volume_cm3=85.366; scaled_mass_g=764.879
Volume XS400_Group2_Cu_Coarse_NorthContactBlock_4K60K
XS400_Group2_Cu_Coarse_NorthContactBlock_4K60K.Material Copper
XS400_Group2_Cu_Coarse_NorthContactBlock_4K60K.Visibility 1
XS400_Group2_Cu_Coarse_NorthContactBlock_4K60K.Shape BRIK 2.5 2.58684717 1.65
XS400_Group2_Cu_Coarse_NorthContactBlock_4K60K.Position 0 7.2 24.45
XS400_Group2_Cu_Coarse_NorthContactBlock_4K60K.Mother InstrumentFrame

// Volume XS400_Group2_Cu_Coarse_TopOpenCollar_4K60K; kind=PCON_annular_sector; source=aggregate:upper copper flange/collar source parts; band=4K_to_60K; source_material=Copper_aggregate; scaled_volume_cm3=158.537; scaled_mass_g=1420.49
Volume XS400_Group2_Cu_Coarse_TopOpenCollar_4K60K
XS400_Group2_Cu_Coarse_TopOpenCollar_4K60K.Material Copper
XS400_Group2_Cu_Coarse_TopOpenCollar_4K60K.Visibility 1
XS400_Group2_Cu_Coarse_TopOpenCollar_4K60K.Shape PCON 230 260 2 -1.175 3.2 6.3224351 1.175 3.2 6.3224351
XS400_Group2_Cu_Coarse_TopOpenCollar_4K60K.Position 0 0 27.325
XS400_Group2_Cu_Coarse_TopOpenCollar_4K60K.Mother InstrumentFrame

// Volume XS400_Group2_SS_Coarse_SpringBoss_4K60K; kind=PCON_cylinder; source=aggregate:lower-band SS fasteners; band=4K_to_60K; source_material=StainlessSteel_aggregate; scaled_volume_cm3=10.6892; scaled_mass_g=85.5136
Volume XS400_Group2_SS_Coarse_SpringBoss_4K60K
XS400_Group2_SS_Coarse_SpringBoss_4K60K.Material StainlessSteel
XS400_Group2_SS_Coarse_SpringBoss_4K60K.Visibility 1
XS400_Group2_SS_Coarse_SpringBoss_4K60K.Shape PCON 0 360 2 -0.2 0 2.91653862 0.2 0 2.91653862
XS400_Group2_SS_Coarse_SpringBoss_4K60K.Position -6.8 0 26.35
XS400_Group2_SS_Coarse_SpringBoss_4K60K.Mother InstrumentFrame

// Volume XS400_Group2_Cu_Coarse_ServiceCan_60K300K; kind=PCON_cylinder; source=aggregate:Part-68/69/70; band=60K_to_300K; source_material=Copper_aggregate; scaled_volume_cm3=105.832; scaled_mass_g=948.253
Volume XS400_Group2_Cu_Coarse_ServiceCan_60K300K
XS400_Group2_Cu_Coarse_ServiceCan_60K300K.Material Copper
XS400_Group2_Cu_Coarse_ServiceCan_60K300K.Visibility 1
XS400_Group2_Cu_Coarse_ServiceCan_60K300K.Shape PCON 0 360 2 -1.225 0 3.70808796 1.225 0 3.70808796
XS400_Group2_Cu_Coarse_ServiceCan_60K300K.Position 3.4 -0.2 30.775
XS400_Group2_Cu_Coarse_ServiceCan_60K300K.Mother InstrumentFrame

// Volume XS400_Group2_SS_Coarse_SpringBlock_60K300K; kind=BRIK_offset_block; source=aggregate:upper-band SS springs and fasteners; band=60K_to_300K; source_material=StainlessSteel_aggregate; scaled_volume_cm3=37.281; scaled_mass_g=298.248
Volume XS400_Group2_SS_Coarse_SpringBlock_60K300K
XS400_Group2_SS_Coarse_SpringBlock_60K300K.Material StainlessSteel
XS400_Group2_SS_Coarse_SpringBlock_60K300K.Visibility 1
XS400_Group2_SS_Coarse_SpringBlock_60K300K.Shape BRIK 3 2.58896106 0.6
XS400_Group2_SS_Coarse_SpringBlock_60K300K.Position 0 6.5 30.2
XS400_Group2_SS_Coarse_SpringBlock_60K300K.Mother InstrumentFrame

// Volume XS400_Group2_Cu_Coarse_OffAxisContactBlock_60K300K; kind=BRIK_offset_block; source=aggregate:Part-312/313/314/315; band=60K_to_300K; source_material=Copper_aggregate; scaled_volume_cm3=232.83; scaled_mass_g=2086.16
Volume XS400_Group2_Cu_Coarse_OffAxisContactBlock_60K300K
XS400_Group2_Cu_Coarse_OffAxisContactBlock_60K300K.Material Copper
XS400_Group2_Cu_Coarse_OffAxisContactBlock_60K300K.Visibility 1
XS400_Group2_Cu_Coarse_OffAxisContactBlock_60K300K.Shape BRIK 3.8 3.06355091 2.5
XS400_Group2_Cu_Coarse_OffAxisContactBlock_60K300K.Position 0 -2.5 34.7
XS400_Group2_Cu_Coarse_OffAxisContactBlock_60K300K.Mother InstrumentFrame

// Volume XS400_Group2_Cu_Coarse_CurvedManifoldArc_60K300K; kind=PCON_annular_sector; source=aggregate:upper-band Cu service cylinders; band=60K_to_300K; source_material=Copper_aggregate; scaled_volume_cm3=84.6654; scaled_mass_g=758.602
Volume XS400_Group2_Cu_Coarse_CurvedManifoldArc_60K300K
XS400_Group2_Cu_Coarse_CurvedManifoldArc_60K300K.Material Copper
XS400_Group2_Cu_Coarse_CurvedManifoldArc_60K300K.Visibility 1
XS400_Group2_Cu_Coarse_CurvedManifoldArc_60K300K.Shape PCON 70 50 2 -1.8 4.8 8.77152621 1.8 4.8 8.77152621
XS400_Group2_Cu_Coarse_CurvedManifoldArc_60K300K.Position 0 0 35.85
XS400_Group2_Cu_Coarse_CurvedManifoldArc_60K300K.Mother InstrumentFrame

// END XS400_GROUP2_TOP_SCALED_PROXY










// BEGIN XS400_GROUP3_AUX_SERVICE_SCALED_PROXY
// Added 2026-06-30: XS400 group 3 auxiliary service-port/cold-trap mass proxy.
// Coarse solid mass proxy: PCON and BRIK shapes preserve material volume and mass.
// Rule: split source groups by XS400 z relative to the 50K stage, scale by local
// project/reference cold-plate area ratio, and keep the XS400 groups' offset character.
// source_layout_axis_xy_mm=[135.0, 0.0]; xs400_split_z_mm=-637
// band=lower_4K_to_60K; ColdPlate_4K -> ColdPlate_60K; area_scale=(10.4/20)^2=0.2704; layout_max_radius_cm=7.95; z=20.4..28.6
// band=upper_60K_to_300K; ColdPlate_60K -> Plate_300K_Top_Service_Lid; area_scale=(11.9/24)^2=0.245850694; layout_max_radius_cm=8.75; z=29.45..37.45
// Volume XS400_Group3_Cu_Coarse_LowerFlange_4K60K; kind=PCON_annular_sector; source=aggregate:Part-335/341; band=4K_to_60K; source_material=Copper_aggregate; scaled_volume_cm3=23.9154; scaled_mass_g=214.282
Volume XS400_Group3_Cu_Coarse_LowerFlange_4K60K
XS400_Group3_Cu_Coarse_LowerFlange_4K60K.Material Copper
XS400_Group3_Cu_Coarse_LowerFlange_4K60K.Visibility 1
XS400_Group3_Cu_Coarse_LowerFlange_4K60K.Shape PCON 0 360 2 -0.45 0.55 2.95987352 0.45 0.55 2.95987352
XS400_Group3_Cu_Coarse_LowerFlange_4K60K.Position -6.8 0 21
XS400_Group3_Cu_Coarse_LowerFlange_4K60K.Mother InstrumentFrame

// Volume XS400_Group3_SS_Coarse_SideSupportBlock_4K60K; kind=BRIK_offset_block; source=aggregate:Part-334/326/342; band=4K_to_60K; source_material=StainlessSteel_aggregate; scaled_volume_cm3=36.808; scaled_mass_g=294.464
Volume XS400_Group3_SS_Coarse_SideSupportBlock_4K60K
XS400_Group3_SS_Coarse_SideSupportBlock_4K60K.Material StainlessSteel
XS400_Group3_SS_Coarse_SideSupportBlock_4K60K.Visibility 1
XS400_Group3_SS_Coarse_SideSupportBlock_4K60K.Shape BRIK 3 3.06733565 0.5
XS400_Group3_SS_Coarse_SideSupportBlock_4K60K.Position -6.8 0 22.15
XS400_Group3_SS_Coarse_SideSupportBlock_4K60K.Mother InstrumentFrame

// Volume XS400_Group3_SS_Coarse_MainSteppedServiceCan_4K60K; kind=PCON_cylinder; source=aggregate:Part-337/336/339; band=4K_to_60K; source_material=StainlessSteel_aggregate; scaled_volume_cm3=74.7315; scaled_mass_g=597.852
Volume XS400_Group3_SS_Coarse_MainSteppedServiceCan_4K60K
XS400_Group3_SS_Coarse_MainSteppedServiceCan_4K60K.Material StainlessSteel
XS400_Group3_SS_Coarse_MainSteppedServiceCan_4K60K.Visibility 1
XS400_Group3_SS_Coarse_MainSteppedServiceCan_4K60K.Shape PCON 0 360 2 -1.65 0 2.68484859 1.65 0 2.68484859
XS400_Group3_SS_Coarse_MainSteppedServiceCan_4K60K.Position -6.8 0 24.45
XS400_Group3_SS_Coarse_MainSteppedServiceCan_4K60K.Mother InstrumentFrame

// Volume XS400_Group3_Cu_Coarse_DualThermalTabs_4K60K; kind=BRIK_offset_block; source=aggregate:Part-59/169/148/152; band=4K_to_60K; source_material=Copper_aggregate; scaled_volume_cm3=25.5098; scaled_mass_g=228.568
Volume XS400_Group3_Cu_Coarse_DualThermalTabs_4K60K
XS400_Group3_Cu_Coarse_DualThermalTabs_4K60K.Material Copper
XS400_Group3_Cu_Coarse_DualThermalTabs_4K60K.Visibility 1
XS400_Group3_Cu_Coarse_DualThermalTabs_4K60K.Shape BRIK 3 4.25163107 0.25
XS400_Group3_Cu_Coarse_DualThermalTabs_4K60K.Position -6.8 0 26.9
XS400_Group3_Cu_Coarse_DualThermalTabs_4K60K.Mother InstrumentFrame

// Volume XS400_Group3_Cu_Coarse_TopFlange_4K60K; kind=PCON_annular_sector; source=aggregate:Part-340/338; band=4K_to_60K; source_material=Copper_aggregate; scaled_volume_cm3=30.2929; scaled_mass_g=271.424
Volume XS400_Group3_Cu_Coarse_TopFlange_4K60K
XS400_Group3_Cu_Coarse_TopFlange_4K60K.Material Copper
XS400_Group3_Cu_Coarse_TopFlange_4K60K.Visibility 1
XS400_Group3_Cu_Coarse_TopFlange_4K60K.Shape PCON 0 360 2 -0.6 0.65 2.90825269 0.6 0.65 2.90825269
XS400_Group3_Cu_Coarse_TopFlange_4K60K.Position -6.8 0 27.85
XS400_Group3_Cu_Coarse_TopFlange_4K60K.Mother InstrumentFrame

// END XS400_GROUP3_AUX_SERVICE_SCALED_PROXY







// BEGIN XS400_GROUP4_TOP_PORT_FITTINGS_SCALED_PROXY
// Added 2026-06-30: XS400 group 4 upper small-cylinder/port-fitting mass proxy.
// Coarse solid mass proxy: PCON and BRIK shapes preserve material volume and mass.
// Rule: split source groups by XS400 z relative to the 50K stage, scale by local
// project/reference cold-plate area ratio, and keep the XS400 groups' offset character.
// source_layout_axis_xy_mm=[135.0, 0.0]; xs400_split_z_mm=-637
// band=lower_4K_to_60K; ColdPlate_4K -> ColdPlate_60K; area_scale=(10.4/20)^2=0.2704; layout_max_radius_cm=7.95; z=20.4..28.6
// band=upper_60K_to_300K; ColdPlate_60K -> Plate_300K_Top_Service_Lid; area_scale=(11.9/24)^2=0.245850694; layout_max_radius_cm=8.75; z=29.45..37.45
// Volume XS400_Group4_SS_Coarse_LowerServiceStub_4K60K; kind=PCON_cylinder; source=aggregate:Part-22/165; band=4K_to_60K; source_material=StainlessSteel_aggregate; scaled_volume_cm3=3.82497; scaled_mass_g=30.5998
Volume XS400_Group4_SS_Coarse_LowerServiceStub_4K60K
XS400_Group4_SS_Coarse_LowerServiceStub_4K60K.Material StainlessSteel
XS400_Group4_SS_Coarse_LowerServiceStub_4K60K.Visibility 1
XS400_Group4_SS_Coarse_LowerServiceStub_4K60K.Shape PCON 0 360 2 -0.4 0 1.23365608 0.4 0 1.23365608
XS400_Group4_SS_Coarse_LowerServiceStub_4K60K.Position 6.5 0 22.25
XS400_Group4_SS_Coarse_LowerServiceStub_4K60K.Mother InstrumentFrame

// Volume XS400_Group4_SS_Coarse_UpperServiceTubeBank_60K300K; kind=BRIK_offset_block; source=aggregate:upper small service cylinders; band=60K_to_300K; source_material=StainlessSteel_aggregate; scaled_volume_cm3=53.4383; scaled_mass_g=427.507
Volume XS400_Group4_SS_Coarse_UpperServiceTubeBank_60K300K
XS400_Group4_SS_Coarse_UpperServiceTubeBank_60K300K.Material StainlessSteel
XS400_Group4_SS_Coarse_UpperServiceTubeBank_60K300K.Visibility 1
XS400_Group4_SS_Coarse_UpperServiceTubeBank_60K300K.Shape BRIK 3 1.85549818 1.2
XS400_Group4_SS_Coarse_UpperServiceTubeBank_60K300K.Position 0 7 32.4
XS400_Group4_SS_Coarse_UpperServiceTubeBank_60K300K.Mother InstrumentFrame

// Volume XS400_Group4_SS_Coarse_PortFlange_A_60K300K; kind=PCON_cylinder; source=aggregate:Part-191; band=60K_to_300K; source_material=StainlessSteel_aggregate; scaled_volume_cm3=21.3309; scaled_mass_g=170.647
Volume XS400_Group4_SS_Coarse_PortFlange_A_60K300K
XS400_Group4_SS_Coarse_PortFlange_A_60K300K.Material StainlessSteel
XS400_Group4_SS_Coarse_PortFlange_A_60K300K.Visibility 1
XS400_Group4_SS_Coarse_PortFlange_A_60K300K.Shape PCON 0 360 2 -0.55 0 2.48446642 0.55 0 2.48446642
XS400_Group4_SS_Coarse_PortFlange_A_60K300K.Position 5.2 3.3 34.75
XS400_Group4_SS_Coarse_PortFlange_A_60K300K.Mother InstrumentFrame

// Volume XS400_Group4_SS_Coarse_PortFlange_B_60K300K; kind=PCON_cylinder; source=aggregate:Part-76; band=60K_to_300K; source_material=StainlessSteel_aggregate; scaled_volume_cm3=21.3309; scaled_mass_g=170.647
Volume XS400_Group4_SS_Coarse_PortFlange_B_60K300K
XS400_Group4_SS_Coarse_PortFlange_B_60K300K.Material StainlessSteel
XS400_Group4_SS_Coarse_PortFlange_B_60K300K.Visibility 1
XS400_Group4_SS_Coarse_PortFlange_B_60K300K.Shape PCON 0 360 2 -0.55 0 2.48446642 0.55 0 2.48446642
XS400_Group4_SS_Coarse_PortFlange_B_60K300K.Position 7.5 -2.8 36.05
XS400_Group4_SS_Coarse_PortFlange_B_60K300K.Mother InstrumentFrame

// END XS400_GROUP4_TOP_PORT_FITTINGS_SCALED_PROXY

// END PINNED_SG3B_COLD_PLATES_AND_INTERNAL_SUPPORTS

// BEGIN SH3_DRBASE_PORTED_THERMAL_SHELLS
// 50 mK aluminium can; original 3.796 cm square window replaced by one 1.50 cm circular cold-finger port.
Shape PCON SH3_DRBase_MXC50mK_FullSideShellShape
SH3_DRBase_MXC50mK_FullSideShellShape.Parameters 0 360 2 -9.700000 15.100000 15.300000 -0.300000 15.100000 15.300000
Shape TUBS SH3_DRBase_MXC50mK_ColdFingerPortCutShape
SH3_DRBase_MXC50mK_ColdFingerPortCutShape.Parameters 0 0.750000 0.300000 0 360
Orientation SH3_DRBase_MXC50mK_ColdFingerPortCutOrientation
SH3_DRBase_MXC50mK_ColdFingerPortCutOrientation.Position -15.200000 0 -5.200000
SH3_DRBase_MXC50mK_ColdFingerPortCutOrientation.Rotation 0 90 0
Shape Subtraction SH3_DRBase_MXC50mK_PortedSideShellShape
SH3_DRBase_MXC50mK_PortedSideShellShape.Parameters SH3_DRBase_MXC50mK_FullSideShellShape SH3_DRBase_MXC50mK_ColdFingerPortCutShape SH3_DRBase_MXC50mK_ColdFingerPortCutOrientation

Volume SH3_DRBase_MXC50mK_PortedSideShell
SH3_DRBase_MXC50mK_PortedSideShell.Material Aluminium
SH3_DRBase_MXC50mK_PortedSideShell.Visibility 1
SH3_DRBase_MXC50mK_PortedSideShell.Shape SH3_DRBase_MXC50mK_PortedSideShellShape
SH3_DRBase_MXC50mK_PortedSideShell.Position 0 0 0
SH3_DRBase_MXC50mK_PortedSideShell.Mother InstrumentFrame

Volume SH3_DRBase_MXC50mK_BottomCap
SH3_DRBase_MXC50mK_BottomCap.Material Aluminium
SH3_DRBase_MXC50mK_BottomCap.Visibility 1
SH3_DRBase_MXC50mK_BottomCap.Shape PCON 0 360 2 -9.900000 0 15.300000 -9.700000 0 15.300000
SH3_DRBase_MXC50mK_BottomCap.Position 0 0 0
SH3_DRBase_MXC50mK_BottomCap.Mother InstrumentFrame

// Still aluminium shield; original 3.796 cm square window replaced by one 1.50 cm circular cold-finger port.
Shape PCON SH3_DRBase_Still_FullSideShellShape
SH3_DRBase_Still_FullSideShellShape.Parameters 0 360 2 -10.400000 15.500000 15.800000 10.700000 15.500000 15.800000
Shape TUBS SH3_DRBase_Still_ColdFingerPortCutShape
SH3_DRBase_Still_ColdFingerPortCutShape.Parameters 0 0.750000 0.350000 0 360
Orientation SH3_DRBase_Still_ColdFingerPortCutOrientation
SH3_DRBase_Still_ColdFingerPortCutOrientation.Position -15.650000 0 -5.200000
SH3_DRBase_Still_ColdFingerPortCutOrientation.Rotation 0 90 0
Shape Subtraction SH3_DRBase_Still_PortedSideShellShape
SH3_DRBase_Still_PortedSideShellShape.Parameters SH3_DRBase_Still_FullSideShellShape SH3_DRBase_Still_ColdFingerPortCutShape SH3_DRBase_Still_ColdFingerPortCutOrientation

Volume SH3_DRBase_Still_PortedSideShell
SH3_DRBase_Still_PortedSideShell.Material Aluminium
SH3_DRBase_Still_PortedSideShell.Visibility 1
SH3_DRBase_Still_PortedSideShell.Shape SH3_DRBase_Still_PortedSideShellShape
SH3_DRBase_Still_PortedSideShell.Position 0 0 0
SH3_DRBase_Still_PortedSideShell.Mother InstrumentFrame

Volume SH3_DRBase_Still_BottomCap
SH3_DRBase_Still_BottomCap.Material Aluminium
SH3_DRBase_Still_BottomCap.Visibility 1
SH3_DRBase_Still_BottomCap.Shape PCON 0 360 2 -10.700000 0 15.800000 -10.400000 0 15.800000
SH3_DRBase_Still_BottomCap.Position 0 0 0
SH3_DRBase_Still_BottomCap.Mother InstrumentFrame

// 4 K aluminium shield; original 3.796 cm square window replaced by one 1.50 cm circular cold-finger port.
Shape PCON SH3_DRBase_4K_FullSideShellShape
SH3_DRBase_4K_FullSideShellShape.Parameters 0 360 2 -11.400000 17.700000 18.000000 19.700000 17.700000 18.000000
Shape TUBS SH3_DRBase_4K_ColdFingerPortCutShape
SH3_DRBase_4K_ColdFingerPortCutShape.Parameters 0 0.750000 0.350000 0 360
Orientation SH3_DRBase_4K_ColdFingerPortCutOrientation
SH3_DRBase_4K_ColdFingerPortCutOrientation.Position -17.850000 0 -5.200000
SH3_DRBase_4K_ColdFingerPortCutOrientation.Rotation 0 90 0
Shape Subtraction SH3_DRBase_4K_PortedSideShellShape
SH3_DRBase_4K_PortedSideShellShape.Parameters SH3_DRBase_4K_FullSideShellShape SH3_DRBase_4K_ColdFingerPortCutShape SH3_DRBase_4K_ColdFingerPortCutOrientation

Volume SH3_DRBase_4K_PortedSideShell
SH3_DRBase_4K_PortedSideShell.Material Aluminium
SH3_DRBase_4K_PortedSideShell.Visibility 1
SH3_DRBase_4K_PortedSideShell.Shape SH3_DRBase_4K_PortedSideShellShape
SH3_DRBase_4K_PortedSideShell.Position 0 0 0
SH3_DRBase_4K_PortedSideShell.Mother InstrumentFrame

Volume SH3_DRBase_4K_BottomCap
SH3_DRBase_4K_BottomCap.Material Aluminium
SH3_DRBase_4K_BottomCap.Visibility 1
SH3_DRBase_4K_BottomCap.Shape PCON 0 360 2 -11.700000 0 18.000000 -11.400000 0 18.000000
SH3_DRBase_4K_BottomCap.Position 0 0 0
SH3_DRBase_4K_BottomCap.Mother InstrumentFrame

// 60 K aluminium shield; original 3.796 cm square window replaced by one 1.50 cm circular cold-finger port.
Shape PCON SH3_DRBase_60K_FullSideShellShape
SH3_DRBase_60K_FullSideShellShape.Parameters 0 360 2 -12.400000 18.200000 18.500000 28.650000 18.200000 18.500000
Shape TUBS SH3_DRBase_60K_ColdFingerPortCutShape
SH3_DRBase_60K_ColdFingerPortCutShape.Parameters 0 0.750000 0.350000 0 360
Orientation SH3_DRBase_60K_ColdFingerPortCutOrientation
SH3_DRBase_60K_ColdFingerPortCutOrientation.Position -18.350000 0 -5.200000
SH3_DRBase_60K_ColdFingerPortCutOrientation.Rotation 0 90 0
Shape Subtraction SH3_DRBase_60K_PortedSideShellShape
SH3_DRBase_60K_PortedSideShellShape.Parameters SH3_DRBase_60K_FullSideShellShape SH3_DRBase_60K_ColdFingerPortCutShape SH3_DRBase_60K_ColdFingerPortCutOrientation

Volume SH3_DRBase_60K_PortedSideShell
SH3_DRBase_60K_PortedSideShell.Material Aluminium
SH3_DRBase_60K_PortedSideShell.Visibility 1
SH3_DRBase_60K_PortedSideShell.Shape SH3_DRBase_60K_PortedSideShellShape
SH3_DRBase_60K_PortedSideShell.Position 0 0 0
SH3_DRBase_60K_PortedSideShell.Mother InstrumentFrame

Volume SH3_DRBase_60K_BottomCap
SH3_DRBase_60K_BottomCap.Material Aluminium
SH3_DRBase_60K_BottomCap.Visibility 1
SH3_DRBase_60K_BottomCap.Shape PCON 0 360 2 -12.700000 0 18.500000 -12.400000 0 18.500000
SH3_DRBase_60K_BottomCap.Position 0 0 0
SH3_DRBase_60K_BottomCap.Mother InstrumentFrame

// 300 K aluminium vacuum jacket; original 3.796 cm square window replaced by one 1.50 cm circular cold-finger port.
Shape PCON SH3_DRBase_VacuumJacket_FullSideShellShape
SH3_DRBase_VacuumJacket_FullSideShellShape.Parameters 0 360 2 -13.600000 20.100000 20.600000 37.500000 20.100000 20.600000
Shape TUBS SH3_DRBase_VacuumJacket_ColdFingerPortCutShape
SH3_DRBase_VacuumJacket_ColdFingerPortCutShape.Parameters 0 0.750000 0.450000 0 360
Orientation SH3_DRBase_VacuumJacket_ColdFingerPortCutOrientation
SH3_DRBase_VacuumJacket_ColdFingerPortCutOrientation.Position -20.350000 0 -5.200000
SH3_DRBase_VacuumJacket_ColdFingerPortCutOrientation.Rotation 0 90 0
Shape Subtraction SH3_DRBase_VacuumJacket_PortedSideShellShape
SH3_DRBase_VacuumJacket_PortedSideShellShape.Parameters SH3_DRBase_VacuumJacket_FullSideShellShape SH3_DRBase_VacuumJacket_ColdFingerPortCutShape SH3_DRBase_VacuumJacket_ColdFingerPortCutOrientation

Volume SH3_DRBase_VacuumJacket_PortedSideShell
SH3_DRBase_VacuumJacket_PortedSideShell.Material Aluminium
SH3_DRBase_VacuumJacket_PortedSideShell.Visibility 1
SH3_DRBase_VacuumJacket_PortedSideShell.Shape SH3_DRBase_VacuumJacket_PortedSideShellShape
SH3_DRBase_VacuumJacket_PortedSideShell.Position 0 0 0
SH3_DRBase_VacuumJacket_PortedSideShell.Mother InstrumentFrame

Volume SH3_DRBase_VacuumJacket_BottomCap
SH3_DRBase_VacuumJacket_BottomCap.Material Aluminium
SH3_DRBase_VacuumJacket_BottomCap.Visibility 1
SH3_DRBase_VacuumJacket_BottomCap.Shape PCON 0 360 2 -14.100000 0 20.600000 -13.600000 0 20.600000
SH3_DRBase_VacuumJacket_BottomCap.Position 0 0 0
SH3_DRBase_VacuumJacket_BottomCap.Mother InstrumentFrame


// END SH3_DRBASE_PORTED_THERMAL_SHELLS

// BEGIN PINNED_SG3B_DR_CORE
// Volume DR_MixingChamber_Cu; material=Copper
Volume DR_MixingChamber_Cu
DR_MixingChamber_Cu.Material Copper
DR_MixingChamber_Cu.Visibility 1
DR_MixingChamber_Cu.Shape PCON 0 360 2 -0.9 0 2.2 0.9 0 2.2

DR_MixingChamber_Cu.Position 0 0 1.21
DR_MixingChamber_Cu.Mother InstrumentFrame

// Volume DR_MXC_Sinter_HEX_AgProxy; material=SilverSinterProxy
Volume DR_MXC_Sinter_HEX_AgProxy
DR_MXC_Sinter_HEX_AgProxy.Material SilverSinterProxy
DR_MXC_Sinter_HEX_AgProxy.Visibility 1
DR_MXC_Sinter_HEX_AgProxy.Shape PCON 0 360 2 -0.9 2.5 3.5 0.9 2.5 3.5

DR_MXC_Sinter_HEX_AgProxy.Position 0 0 1.3
DR_MXC_Sinter_HEX_AgProxy.Mother InstrumentFrame

// Volume DR_Continuous_HEX_CuNi_MXC_to_CP; material=CuNi
Volume DR_Continuous_HEX_CuNi_MXC_to_CP
DR_Continuous_HEX_CuNi_MXC_to_CP.Material CuNi
DR_Continuous_HEX_CuNi_MXC_to_CP.Visibility 1
DR_Continuous_HEX_CuNi_MXC_to_CP.Shape PCON 0 108 2 -2.1 5.2 5.5 2.1 5.2 5.5

DR_Continuous_HEX_CuNi_MXC_to_CP.Position 0 0 2.5
DR_Continuous_HEX_CuNi_MXC_to_CP.Mother InstrumentFrame

// Volume DR_Continuous_HEX_CuNi_CP_to_Still; material=CuNi
Volume DR_Continuous_HEX_CuNi_CP_to_Still
DR_Continuous_HEX_CuNi_CP_to_Still.Material CuNi
DR_Continuous_HEX_CuNi_CP_to_Still.Visibility 1
DR_Continuous_HEX_CuNi_CP_to_Still.Shape PCON 0 108 2 -2.1 5.2 5.5 2.1 5.2 5.5

DR_Continuous_HEX_CuNi_CP_to_Still.Position 0 0 7.5
DR_Continuous_HEX_CuNi_CP_to_Still.Mother InstrumentFrame

// Volume DR_Still_Pot_Cu; material=Copper
Volume DR_Still_Pot_Cu
DR_Still_Pot_Cu.Material Copper
DR_Still_Pot_Cu.Visibility 1
DR_Still_Pot_Cu.Shape PCON 0 360 2 -0.8 0 2.6 0.8 0 2.6

DR_Still_Pot_Cu.Position 0 0 9.8
DR_Still_Pot_Cu.Mother InstrumentFrame

// Volume DR_Still_Heater_SS_ring; material=StainlessSteel
Volume DR_Still_Heater_SS_ring
DR_Still_Heater_SS_ring.Material StainlessSteel
DR_Still_Heater_SS_ring.Visibility 1
DR_Still_Heater_SS_ring.Shape PCON 0 360 2 -0.15 2.7 2.9 0.15 2.7 2.9

DR_Still_Heater_SS_ring.Position 0 0 9.35
DR_Still_Heater_SS_ring.Mother InstrumentFrame

// Volume DR_4K_Condenser_Cu; material=Copper
Volume DR_4K_Condenser_Cu
DR_4K_Condenser_Cu.Material Copper
DR_4K_Condenser_Cu.Visibility 1
DR_4K_Condenser_Cu.Shape PCON 0 360 2 -0.6 0 1.8 0.6 0 1.8

DR_4K_Condenser_Cu.Position 0 0 19
DR_4K_Condenser_Cu.Mother InstrumentFrame

// Volume DR_60K_Charcoal_Trap; material=CharcoalProxy
Volume DR_60K_Charcoal_Trap
DR_60K_Charcoal_Trap.Material CharcoalProxy
DR_60K_Charcoal_Trap.Visibility 1
DR_60K_Charcoal_Trap.Shape PCON 0 360 2 -1.1 0 1.9 1.1 0 1.9

DR_60K_Charcoal_Trap.Position 0 0 27.4
DR_60K_Charcoal_Trap.Mother InstrumentFrame

// Volume DR_Capillary_CuNi_MXC_CP; material=CuNi
Volume DR_Capillary_CuNi_MXC_CP
DR_Capillary_CuNi_MXC_CP.Material CuNi
DR_Capillary_CuNi_MXC_CP.Visibility 1
DR_Capillary_CuNi_MXC_CP.Shape PCON 38.4 43.2 2 -2.1 6.2 6.32 2.1 6.2 6.32

DR_Capillary_CuNi_MXC_CP.Position 0 0 2.5
DR_Capillary_CuNi_MXC_CP.Mother InstrumentFrame

// Volume DR_Capillary_CuNi_CP_Still; material=CuNi
Volume DR_Capillary_CuNi_CP_Still
DR_Capillary_CuNi_CP_Still.Material CuNi
DR_Capillary_CuNi_CP_Still.Visibility 1
DR_Capillary_CuNi_CP_Still.Shape PCON 38.4 43.2 2 -2.1 6.2 6.32 2.1 6.2 6.32

DR_Capillary_CuNi_CP_Still.Position 0 0 7.5
DR_Capillary_CuNi_CP_Still.Mother InstrumentFrame

// Volume DR_Capillary_CuNi_Still_4K; material=CuNi
Volume DR_Capillary_CuNi_Still_4K
DR_Capillary_CuNi_Still_4K.Material CuNi
DR_Capillary_CuNi_Still_4K.Visibility 1
DR_Capillary_CuNi_Still_4K.Shape PCON 38.4 43.2 2 -4.1 9.2 9.32 4.1 9.2 9.32

DR_Capillary_CuNi_Still_4K.Position 0 0 15.5
DR_Capillary_CuNi_Still_4K.Mother InstrumentFrame

// Volume DR_Capillary_CuNi_4K_60K; material=CuNi
Volume DR_Capillary_CuNi_4K_60K
DR_Capillary_CuNi_4K_60K.Material CuNi
DR_Capillary_CuNi_4K_60K.Visibility 1
DR_Capillary_CuNi_4K_60K.Shape PCON 38.4 43.2 2 -4.05 10.7 10.82 4.05 10.7 10.82

DR_Capillary_CuNi_4K_60K.Position 0 0 24.45
DR_Capillary_CuNi_4K_60K.Mother InstrumentFrame

// Volume DR_Still_PumpLine_SS_to_300K_top; material=StainlessSteel
Volume DR_Still_PumpLine_SS_to_300K_top
DR_Still_PumpLine_SS_to_300K_top.Material StainlessSteel
DR_Still_PumpLine_SS_to_300K_top.Visibility 1
DR_Still_PumpLine_SS_to_300K_top.Shape BRIK 0.2 0.2 12.7

DR_Still_PumpLine_SS_to_300K_top.Position 21.4 0 24.7
DR_Still_PumpLine_SS_to_300K_top.Mother InstrumentFrame

// Volume PreCool_FlexLink_Cu_remote_interface; material=Copper
Volume PreCool_FlexLink_Cu_remote_interface
PreCool_FlexLink_Cu_remote_interface.Material Copper
PreCool_FlexLink_Cu_remote_interface.Visibility 1
PreCool_FlexLink_Cu_remote_interface.Shape BRIK 0.15 0.5 2.25

PreCool_FlexLink_Cu_remote_interface.Position -10.7 0 26.25
PreCool_FlexLink_Cu_remote_interface.Mother InstrumentFrame

// END PINNED_SG3B_DR_CORE

// BEGIN PINNED_SG3B_G10_SUPPORT_RINGS
// Volume G10_Support_Ring_MXC_CP; material=G10
Volume G10_Support_Ring_MXC_CP
G10_Support_Ring_MXC_CP.Material G10
G10_Support_Ring_MXC_CP.Visibility 1
G10_Support_Ring_MXC_CP.Shape PCON 210 90 2 -2.1 7.45 7.75 2.1 7.45 7.75

G10_Support_Ring_MXC_CP.Position 0 0 2.5
G10_Support_Ring_MXC_CP.Mother InstrumentFrame

// Volume G10_Support_Ring_CP_Still; material=G10
Volume G10_Support_Ring_CP_Still
G10_Support_Ring_CP_Still.Material G10
G10_Support_Ring_CP_Still.Visibility 1
G10_Support_Ring_CP_Still.Shape PCON 210 90 2 -2.1 8.05 8.35 2.1 8.05 8.35

G10_Support_Ring_CP_Still.Position 0 0 7.5
G10_Support_Ring_CP_Still.Mother InstrumentFrame

// Volume G10_Support_Ring_Still_4K; material=G10
Volume G10_Support_Ring_Still_4K
G10_Support_Ring_Still_4K.Material G10
G10_Support_Ring_Still_4K.Visibility 1
G10_Support_Ring_Still_4K.Shape PCON 210 90 2 -4.1 9.35 9.65 4.1 9.35 9.65

G10_Support_Ring_Still_4K.Position 0 0 15.5
G10_Support_Ring_Still_4K.Mother InstrumentFrame

// Volume G10_Support_Ring_4K_60K; material=G10
Volume G10_Support_Ring_4K_60K
G10_Support_Ring_4K_60K.Material G10
G10_Support_Ring_4K_60K.Visibility 1
G10_Support_Ring_4K_60K.Shape PCON 210 90 2 -4.05 10.85 11.15 4.05 10.85 11.15

G10_Support_Ring_4K_60K.Position 0 0 24.45
G10_Support_Ring_4K_60K.Mother InstrumentFrame

// Volume G10_Support_Ring_60K_Top; material=G10
Volume G10_Support_Ring_60K_Top
G10_Support_Ring_60K_Top.Material G10
G10_Support_Ring_60K_Top.Visibility 1
G10_Support_Ring_60K_Top.Shape PCON 210 90 2 -4 12.45 12.7 4 12.45 12.7

G10_Support_Ring_60K_Top.Position 0 0 33.4
G10_Support_Ring_60K_Top.Mother InstrumentFrame

// END PINNED_SG3B_G10_SUPPORT_RINGS

// BEGIN PINNED_SG3B_TOP_SERVICES_AND_OUTER_SUPPORT_CAGE
// BEGIN XS400_TOP_300K_FEEDTHROUGH_PIPE_PROXY
// Added 2026-07-01: XS400-inspired top feedthrough pipes on the 300K lid.
// Interpretation: stainless-steel gas tubes, pumping/fill tube, and small cable/gas conduits leaving the DR.
// These are not copied source solids; they are simple hollow PCON pipe proxies with base flanges and top sleeves.
// Volume XS400_Group4_SS_TopPipe_GasReturn_LargePort_A_BaseFlange_300KTop; source=XS400 top-tube morphology proxy; role=large stainless gas-return / service-port tube inspired by XS400 top flanges base flange; volume_cm3=17.1766578; mass_g=137.413263
Volume XS400_Group4_SS_TopPipe_GasReturn_LargePort_A_BaseFlange_300KTop
XS400_Group4_SS_TopPipe_GasReturn_LargePort_A_BaseFlange_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_GasReturn_LargePort_A_BaseFlange_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_GasReturn_LargePort_A_BaseFlange_300KTop.Shape PCON 0 360 2 -0.375 0 2.7 0.375 0 2.7
XS400_Group4_SS_TopPipe_GasReturn_LargePort_A_BaseFlange_300KTop.Position 5 3.2 38.695
XS400_Group4_SS_TopPipe_GasReturn_LargePort_A_BaseFlange_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_GasReturn_LargePort_A_HollowTube_300KTop; source=XS400 top-tube morphology proxy; role=large stainless gas-return / service-port tube inspired by XS400 top flanges hollow tube; volume_cm3=59.7153932; mass_g=477.723145
Volume XS400_Group4_SS_TopPipe_GasReturn_LargePort_A_HollowTube_300KTop
XS400_Group4_SS_TopPipe_GasReturn_LargePort_A_HollowTube_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_GasReturn_LargePort_A_HollowTube_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_GasReturn_LargePort_A_HollowTube_300KTop.Shape PCON 0 360 2 -3.2 0.8 1.9 3.2 0.8 1.9
XS400_Group4_SS_TopPipe_GasReturn_LargePort_A_HollowTube_300KTop.Position 5 3.2 42.27
XS400_Group4_SS_TopPipe_GasReturn_LargePort_A_HollowTube_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_GasReturn_LargePort_A_TopSleeve_300KTop; source=XS400 top-tube morphology proxy; role=large stainless gas-return / service-port tube inspired by XS400 top flanges top sleeve; volume_cm3=3.44953157; mass_g=27.5962525
Volume XS400_Group4_SS_TopPipe_GasReturn_LargePort_A_TopSleeve_300KTop
XS400_Group4_SS_TopPipe_GasReturn_LargePort_A_TopSleeve_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_GasReturn_LargePort_A_TopSleeve_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_GasReturn_LargePort_A_TopSleeve_300KTop.Shape PCON 0 360 2 -0.275 1.94 2.4 0.275 1.94 2.4
XS400_Group4_SS_TopPipe_GasReturn_LargePort_A_TopSleeve_300KTop.Position 5 3.2 45.195
XS400_Group4_SS_TopPipe_GasReturn_LargePort_A_TopSleeve_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_PumpFill_LargePort_B_BaseFlange_300KTop; source=XS400 top-tube morphology proxy; role=second offset stainless pumping/fill tube inspired by XS400 paired top ports base flange; volume_cm3=11.2771395; mass_g=90.2171162
Volume XS400_Group4_SS_TopPipe_PumpFill_LargePort_B_BaseFlange_300KTop
XS400_Group4_SS_TopPipe_PumpFill_LargePort_B_BaseFlange_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_PumpFill_LargePort_B_BaseFlange_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_PumpFill_LargePort_B_BaseFlange_300KTop.Shape PCON 0 360 2 -0.325 0 2.35 0.325 0 2.35
XS400_Group4_SS_TopPipe_PumpFill_LargePort_B_BaseFlange_300KTop.Position 7.4 -2.8 38.645
XS400_Group4_SS_TopPipe_PumpFill_LargePort_B_BaseFlange_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_PumpFill_LargePort_B_HollowTube_300KTop; source=XS400 top-tube morphology proxy; role=second offset stainless pumping/fill tube inspired by XS400 paired top ports hollow tube; volume_cm3=39.388409; mass_g=315.107272
Volume XS400_Group4_SS_TopPipe_PumpFill_LargePort_B_HollowTube_300KTop
XS400_Group4_SS_TopPipe_PumpFill_LargePort_B_HollowTube_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_PumpFill_LargePort_B_HollowTube_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_PumpFill_LargePort_B_HollowTube_300KTop.Shape PCON 0 360 2 -2.85 0.7 1.64 2.85 0.7 1.64
XS400_Group4_SS_TopPipe_PumpFill_LargePort_B_HollowTube_300KTop.Position 7.4 -2.8 41.82
XS400_Group4_SS_TopPipe_PumpFill_LargePort_B_HollowTube_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_PumpFill_LargePort_B_TopSleeve_300KTop; source=XS400 top-tube morphology proxy; role=second offset stainless pumping/fill tube inspired by XS400 paired top ports top sleeve; volume_cm3=2.49379625; mass_g=19.95037
Volume XS400_Group4_SS_TopPipe_PumpFill_LargePort_B_TopSleeve_300KTop
XS400_Group4_SS_TopPipe_PumpFill_LargePort_B_TopSleeve_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_PumpFill_LargePort_B_TopSleeve_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_PumpFill_LargePort_B_TopSleeve_300KTop.Shape PCON 0 360 2 -0.25 1.68 2.1 0.25 1.68 2.1
XS400_Group4_SS_TopPipe_PumpFill_LargePort_B_TopSleeve_300KTop.Position 7.4 -2.8 44.42
XS400_Group4_SS_TopPipe_PumpFill_LargePort_B_TopSleeve_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_VacuumService_MidPort_C_BaseFlange_300KTop; source=XS400 top-tube morphology proxy; role=medium stainless vacuum-service tube inspired by the XS400 small-cylinder cluster base flange; volume_cm3=4.7041423; mass_g=37.6331384
Volume XS400_Group4_SS_TopPipe_VacuumService_MidPort_C_BaseFlange_300KTop
XS400_Group4_SS_TopPipe_VacuumService_MidPort_C_BaseFlange_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_VacuumService_MidPort_C_BaseFlange_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_VacuumService_MidPort_C_BaseFlange_300KTop.Shape PCON 0 360 2 -0.275 0 1.65 0.275 0 1.65
XS400_Group4_SS_TopPipe_VacuumService_MidPort_C_BaseFlange_300KTop.Position -4.5 6.5 38.595
XS400_Group4_SS_TopPipe_VacuumService_MidPort_C_BaseFlange_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_VacuumService_MidPort_C_HollowTube_300KTop; source=XS400 top-tube morphology proxy; role=medium stainless vacuum-service tube inspired by the XS400 small-cylinder cluster hollow tube; volume_cm3=18.4574852; mass_g=147.659881
Volume XS400_Group4_SS_TopPipe_VacuumService_MidPort_C_HollowTube_300KTop
XS400_Group4_SS_TopPipe_VacuumService_MidPort_C_HollowTube_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_VacuumService_MidPort_C_HollowTube_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_VacuumService_MidPort_C_HollowTube_300KTop.Shape PCON 0 360 2 -2.4 0.56 1.24 2.4 0.56 1.24
XS400_Group4_SS_TopPipe_VacuumService_MidPort_C_HollowTube_300KTop.Position -4.5 6.5 41.27
XS400_Group4_SS_TopPipe_VacuumService_MidPort_C_HollowTube_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_VacuumService_MidPort_C_TopSleeve_300KTop; source=XS400 top-tube morphology proxy; role=medium stainless vacuum-service tube inspired by the XS400 small-cylinder cluster top sleeve; volume_cm3=1.48609899; mass_g=11.8887919
Volume XS400_Group4_SS_TopPipe_VacuumService_MidPort_C_TopSleeve_300KTop
XS400_Group4_SS_TopPipe_VacuumService_MidPort_C_TopSleeve_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_VacuumService_MidPort_C_TopSleeve_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_VacuumService_MidPort_C_TopSleeve_300KTop.Shape PCON 0 360 2 -0.225 1.28 1.64 0.225 1.28 1.64
XS400_Group4_SS_TopPipe_VacuumService_MidPort_C_TopSleeve_300KTop.Position -4.5 6.5 43.445
XS400_Group4_SS_TopPipe_VacuumService_MidPort_C_TopSleeve_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_01_BaseFlange_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank base flange; volume_cm3=0.570010571; mass_g=4.56008457
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_01_BaseFlange_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_01_BaseFlange_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_01_BaseFlange_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_01_BaseFlange_300KTop.Shape PCON 0 360 2 -0.175 0 0.72 0.175 0 0.72
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_01_BaseFlange_300KTop.Position -2.4 8.8 38.495
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_01_BaseFlange_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_01_HollowTube_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank hollow tube; volume_cm3=3.47435015; mass_g=27.7948012
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_01_HollowTube_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_01_HollowTube_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_01_HollowTube_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_01_HollowTube_300KTop.Shape PCON 0 360 2 -1.8 0.32 0.64 1.8 0.32 0.64
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_01_HollowTube_300KTop.Position -2.4 8.8 40.47
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_01_HollowTube_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_01_TopSleeve_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank top sleeve; volume_cm3=0.30576493; mass_g=2.44611944
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_01_TopSleeve_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_01_TopSleeve_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_01_TopSleeve_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_01_TopSleeve_300KTop.Shape PCON 0 360 2 -0.14 0.68 0.9 0.14 0.68 0.9
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_01_TopSleeve_300KTop.Position -2.4 8.8 42.13
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_01_TopSleeve_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_02_BaseFlange_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank base flange; volume_cm3=0.570010571; mass_g=4.56008457
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_02_BaseFlange_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_02_BaseFlange_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_02_BaseFlange_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_02_BaseFlange_300KTop.Shape PCON 0 360 2 -0.175 0 0.72 0.175 0 0.72
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_02_BaseFlange_300KTop.Position -0.2 8.9 38.495
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_02_BaseFlange_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_02_HollowTube_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank hollow tube; volume_cm3=3.47435015; mass_g=27.7948012
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_02_HollowTube_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_02_HollowTube_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_02_HollowTube_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_02_HollowTube_300KTop.Shape PCON 0 360 2 -1.8 0.32 0.64 1.8 0.32 0.64
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_02_HollowTube_300KTop.Position -0.2 8.9 40.47
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_02_HollowTube_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_02_TopSleeve_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank top sleeve; volume_cm3=0.30576493; mass_g=2.44611944
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_02_TopSleeve_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_02_TopSleeve_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_02_TopSleeve_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_02_TopSleeve_300KTop.Shape PCON 0 360 2 -0.14 0.68 0.9 0.14 0.68 0.9
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_02_TopSleeve_300KTop.Position -0.2 8.9 42.13
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_02_TopSleeve_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_03_BaseFlange_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank base flange; volume_cm3=0.570010571; mass_g=4.56008457
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_03_BaseFlange_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_03_BaseFlange_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_03_BaseFlange_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_03_BaseFlange_300KTop.Shape PCON 0 360 2 -0.175 0 0.72 0.175 0 0.72
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_03_BaseFlange_300KTop.Position 2 8.8 38.495
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_03_BaseFlange_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_03_HollowTube_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank hollow tube; volume_cm3=3.47435015; mass_g=27.7948012
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_03_HollowTube_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_03_HollowTube_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_03_HollowTube_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_03_HollowTube_300KTop.Shape PCON 0 360 2 -1.8 0.32 0.64 1.8 0.32 0.64
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_03_HollowTube_300KTop.Position 2 8.8 40.47
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_03_HollowTube_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_03_TopSleeve_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank top sleeve; volume_cm3=0.30576493; mass_g=2.44611944
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_03_TopSleeve_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_03_TopSleeve_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_03_TopSleeve_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_03_TopSleeve_300KTop.Shape PCON 0 360 2 -0.14 0.68 0.9 0.14 0.68 0.9
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_03_TopSleeve_300KTop.Position 2 8.8 42.13
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_03_TopSleeve_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_04_BaseFlange_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank base flange; volume_cm3=0.570010571; mass_g=4.56008457
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_04_BaseFlange_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_04_BaseFlange_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_04_BaseFlange_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_04_BaseFlange_300KTop.Shape PCON 0 360 2 -0.175 0 0.72 0.175 0 0.72
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_04_BaseFlange_300KTop.Position 4.2 8.6 38.495
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_04_BaseFlange_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_04_HollowTube_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank hollow tube; volume_cm3=3.47435015; mass_g=27.7948012
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_04_HollowTube_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_04_HollowTube_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_04_HollowTube_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_04_HollowTube_300KTop.Shape PCON 0 360 2 -1.8 0.32 0.64 1.8 0.32 0.64
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_04_HollowTube_300KTop.Position 4.2 8.6 40.47
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_04_HollowTube_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_04_TopSleeve_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank top sleeve; volume_cm3=0.30576493; mass_g=2.44611944
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_04_TopSleeve_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_04_TopSleeve_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_04_TopSleeve_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_04_TopSleeve_300KTop.Shape PCON 0 360 2 -0.14 0.68 0.9 0.14 0.68 0.9
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_04_TopSleeve_300KTop.Position 4.2 8.6 42.13
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_04_TopSleeve_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_05_BaseFlange_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank base flange; volume_cm3=0.570010571; mass_g=4.56008457
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_05_BaseFlange_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_05_BaseFlange_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_05_BaseFlange_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_05_BaseFlange_300KTop.Shape PCON 0 360 2 -0.175 0 0.72 0.175 0 0.72
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_05_BaseFlange_300KTop.Position 6.4 8.3 38.495
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_05_BaseFlange_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_05_HollowTube_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank hollow tube; volume_cm3=3.47435015; mass_g=27.7948012
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_05_HollowTube_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_05_HollowTube_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_05_HollowTube_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_05_HollowTube_300KTop.Shape PCON 0 360 2 -1.8 0.32 0.64 1.8 0.32 0.64
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_05_HollowTube_300KTop.Position 6.4 8.3 40.47
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_05_HollowTube_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_05_TopSleeve_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank top sleeve; volume_cm3=0.30576493; mass_g=2.44611944
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_05_TopSleeve_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_05_TopSleeve_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_05_TopSleeve_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_05_TopSleeve_300KTop.Shape PCON 0 360 2 -0.14 0.68 0.9 0.14 0.68 0.9
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_05_TopSleeve_300KTop.Position 6.4 8.3 42.13
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_05_TopSleeve_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_06_BaseFlange_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank base flange; volume_cm3=0.570010571; mass_g=4.56008457
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_06_BaseFlange_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_06_BaseFlange_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_06_BaseFlange_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_06_BaseFlange_300KTop.Shape PCON 0 360 2 -0.175 0 0.72 0.175 0 0.72
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_06_BaseFlange_300KTop.Position -1.3 10.9 38.495
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_06_BaseFlange_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_06_HollowTube_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank hollow tube; volume_cm3=3.47435015; mass_g=27.7948012
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_06_HollowTube_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_06_HollowTube_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_06_HollowTube_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_06_HollowTube_300KTop.Shape PCON 0 360 2 -1.8 0.32 0.64 1.8 0.32 0.64
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_06_HollowTube_300KTop.Position -1.3 10.9 40.47
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_06_HollowTube_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_06_TopSleeve_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank top sleeve; volume_cm3=0.30576493; mass_g=2.44611944
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_06_TopSleeve_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_06_TopSleeve_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_06_TopSleeve_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_06_TopSleeve_300KTop.Shape PCON 0 360 2 -0.14 0.68 0.9 0.14 0.68 0.9
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_06_TopSleeve_300KTop.Position -1.3 10.9 42.13
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_06_TopSleeve_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_07_BaseFlange_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank base flange; volume_cm3=0.570010571; mass_g=4.56008457
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_07_BaseFlange_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_07_BaseFlange_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_07_BaseFlange_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_07_BaseFlange_300KTop.Shape PCON 0 360 2 -0.175 0 0.72 0.175 0 0.72
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_07_BaseFlange_300KTop.Position 0.9 11.1 38.495
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_07_BaseFlange_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_07_HollowTube_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank hollow tube; volume_cm3=3.47435015; mass_g=27.7948012
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_07_HollowTube_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_07_HollowTube_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_07_HollowTube_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_07_HollowTube_300KTop.Shape PCON 0 360 2 -1.8 0.32 0.64 1.8 0.32 0.64
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_07_HollowTube_300KTop.Position 0.9 11.1 40.47
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_07_HollowTube_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_07_TopSleeve_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank top sleeve; volume_cm3=0.30576493; mass_g=2.44611944
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_07_TopSleeve_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_07_TopSleeve_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_07_TopSleeve_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_07_TopSleeve_300KTop.Shape PCON 0 360 2 -0.14 0.68 0.9 0.14 0.68 0.9
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_07_TopSleeve_300KTop.Position 0.9 11.1 42.13
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_07_TopSleeve_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_08_BaseFlange_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank base flange; volume_cm3=0.570010571; mass_g=4.56008457
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_08_BaseFlange_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_08_BaseFlange_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_08_BaseFlange_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_08_BaseFlange_300KTop.Shape PCON 0 360 2 -0.175 0 0.72 0.175 0 0.72
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_08_BaseFlange_300KTop.Position 3.1 10.9 38.495
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_08_BaseFlange_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_08_HollowTube_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank hollow tube; volume_cm3=3.47435015; mass_g=27.7948012
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_08_HollowTube_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_08_HollowTube_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_08_HollowTube_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_08_HollowTube_300KTop.Shape PCON 0 360 2 -1.8 0.32 0.64 1.8 0.32 0.64
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_08_HollowTube_300KTop.Position 3.1 10.9 40.47
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_08_HollowTube_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_08_TopSleeve_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank top sleeve; volume_cm3=0.30576493; mass_g=2.44611944
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_08_TopSleeve_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_08_TopSleeve_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_08_TopSleeve_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_08_TopSleeve_300KTop.Shape PCON 0 360 2 -0.14 0.68 0.9 0.14 0.68 0.9
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_08_TopSleeve_300KTop.Position 3.1 10.9 42.13
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_08_TopSleeve_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_09_BaseFlange_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank base flange; volume_cm3=0.570010571; mass_g=4.56008457
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_09_BaseFlange_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_09_BaseFlange_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_09_BaseFlange_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_09_BaseFlange_300KTop.Shape PCON 0 360 2 -0.175 0 0.72 0.175 0 0.72
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_09_BaseFlange_300KTop.Position 5.3 10.5 38.495
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_09_BaseFlange_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_09_HollowTube_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank hollow tube; volume_cm3=3.47435015; mass_g=27.7948012
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_09_HollowTube_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_09_HollowTube_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_09_HollowTube_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_09_HollowTube_300KTop.Shape PCON 0 360 2 -1.8 0.32 0.64 1.8 0.32 0.64
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_09_HollowTube_300KTop.Position 5.3 10.5 40.47
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_09_HollowTube_300KTop.Mother InstrumentFrame
// Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_09_TopSleeve_300KTop; source=XS400 top-tube morphology proxy; role=small stainless cable/gas conduit in an XS400-like top tube bank top sleeve; volume_cm3=0.30576493; mass_g=2.44611944
Volume XS400_Group4_SS_TopPipe_CableGas_MicroConduit_09_TopSleeve_300KTop
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_09_TopSleeve_300KTop.Material StainlessSteel
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_09_TopSleeve_300KTop.Visibility 1
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_09_TopSleeve_300KTop.Shape PCON 0 360 2 -0.14 0.68 0.9 0.14 0.68 0.9
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_09_TopSleeve_300KTop.Position 5.3 10.5 42.13
XS400_Group4_SS_TopPipe_CableGas_MicroConduit_09_TopSleeve_300KTop.Mother InstrumentFrame
// END XS400_TOP_300K_FEEDTHROUGH_PIPE_PROXY

// BEGIN NF2_NEARFIELD_OUTER_MECHANICAL_SUPPORT_PROXY
// Added 2026-07-01: imported from add_mass NF2 detector-nearfield mechanical support overlay.
// Adaptation: support cage is attached to InstrumentFrame with a -45 deg counter-rotation.
// Its exported/world-space axis stays vertical while the refrigerator axis remains the InstrumentFrame 45 deg axis.
// Support ring radial widths are scaled by 2.4 and G10 rod half-widths by 2.5.
// Source overlay: add_mass/TES_511_Balloon_nearfield_mass_proxy_v2/detector/overlays/SupportProxy_DetectorNearfieldMechanical_v2.geo
// Volume NF2_OuterSupport_Al_BaseMountAnnulus; source=NF2 nearfield mechanical overlay; role=external detector/gondola base mount annulus on the vertical support axis; volume_cm3=3240.61565; mass_g=8749.66227
Volume NF2_OuterSupport_Al_BaseMountAnnulus
NF2_OuterSupport_Al_BaseMountAnnulus.Material Aluminium
NF2_OuterSupport_Al_BaseMountAnnulus.Visibility 1
NF2_OuterSupport_Al_BaseMountAnnulus.Shape PCON 0 360 2 -0.5 35.7702529 48.0731837 0.5 35.7702529 48.0731837
NF2_OuterSupport_Al_BaseMountAnnulus.Position 19.7989899 0 -12.7279221
NF2_OuterSupport_Al_BaseMountAnnulus.Rotation 0 -45 0
NF2_OuterSupport_Al_BaseMountAnnulus.Mother InstrumentFrame
// Volume NF2_OuterSupport_Al_TopMountAnnulus; source=NF2 nearfield mechanical overlay; role=top support interface annulus on the vertical support axis; volume_cm3=1822.94055; mass_g=4921.93949
Volume NF2_OuterSupport_Al_TopMountAnnulus
NF2_OuterSupport_Al_TopMountAnnulus.Material Aluminium
NF2_OuterSupport_Al_TopMountAnnulus.Visibility 1
NF2_OuterSupport_Al_TopMountAnnulus.Shape PCON 0 360 2 -0.25 34.9765777 48.8250037 0.25 34.9765777 48.8250037
NF2_OuterSupport_Al_TopMountAnnulus.Position -24.7487373 0 31.8198052
NF2_OuterSupport_Al_TopMountAnnulus.Rotation 0 -45 0
NF2_OuterSupport_Al_TopMountAnnulus.Mother InstrumentFrame
// Volume NF2_OuterSupport_G10_Rod_01; source=NF2 nearfield mechanical overlay; role=low-Z external perimeter support cage rod at 30 deg; volume_cm3=384.375; mass_g=711.09375
Volume NF2_OuterSupport_G10_Rod_01
NF2_OuterSupport_G10_Rod_01.Material G10
NF2_OuterSupport_G10_Rod_01.Visibility 1
NF2_OuterSupport_G10_Rod_01.Shape BRIK 1.2551125 1.2551125 30.5
NF2_OuterSupport_G10_Rod_01.Position 23.2447686 21 35.2655838
NF2_OuterSupport_G10_Rod_01.Rotation 0 -45 0
NF2_OuterSupport_G10_Rod_01.Mother InstrumentFrame
// Volume NF2_OuterSupport_G10_Rod_02; source=NF2 nearfield mechanical overlay; role=low-Z external perimeter support cage rod at 90 deg; volume_cm3=384.375; mass_g=711.09375
Volume NF2_OuterSupport_G10_Rod_02
NF2_OuterSupport_G10_Rod_02.Material G10
NF2_OuterSupport_G10_Rod_02.Visibility 1
NF2_OuterSupport_G10_Rod_02.Shape BRIK 1.2551125 1.2551125 30.5
NF2_OuterSupport_G10_Rod_02.Position -2.47487373 42 9.54594155
NF2_OuterSupport_G10_Rod_02.Rotation 0 -45 0
NF2_OuterSupport_G10_Rod_02.Mother InstrumentFrame
// Volume NF2_OuterSupport_G10_Rod_03; source=NF2 nearfield mechanical overlay; role=low-Z external perimeter support cage rod at 150 deg; volume_cm3=384.375; mass_g=711.09375
Volume NF2_OuterSupport_G10_Rod_03
NF2_OuterSupport_G10_Rod_03.Material G10
NF2_OuterSupport_G10_Rod_03.Visibility 1
NF2_OuterSupport_G10_Rod_03.Shape BRIK 1.2551125 1.2551125 30.5
NF2_OuterSupport_G10_Rod_03.Position -28.194516 21 -16.1737008
NF2_OuterSupport_G10_Rod_03.Rotation 0 -45 0
NF2_OuterSupport_G10_Rod_03.Mother InstrumentFrame
// Volume NF2_OuterSupport_G10_Rod_04; source=NF2 nearfield mechanical overlay; role=low-Z external perimeter support cage rod at 210 deg; volume_cm3=384.375; mass_g=711.09375
Volume NF2_OuterSupport_G10_Rod_04
NF2_OuterSupport_G10_Rod_04.Material G10
NF2_OuterSupport_G10_Rod_04.Visibility 1
NF2_OuterSupport_G10_Rod_04.Shape BRIK 1.2551125 1.2551125 30.5
NF2_OuterSupport_G10_Rod_04.Position -28.194516 -21 -16.1737008
NF2_OuterSupport_G10_Rod_04.Rotation 0 -45 0
NF2_OuterSupport_G10_Rod_04.Mother InstrumentFrame
// Volume NF2_OuterSupport_G10_Rod_05; source=NF2 nearfield mechanical overlay; role=low-Z external perimeter support cage rod at 270 deg; volume_cm3=384.375; mass_g=711.09375
Volume NF2_OuterSupport_G10_Rod_05
NF2_OuterSupport_G10_Rod_05.Material G10
NF2_OuterSupport_G10_Rod_05.Visibility 1
NF2_OuterSupport_G10_Rod_05.Shape BRIK 1.2551125 1.2551125 30.5
NF2_OuterSupport_G10_Rod_05.Position -2.47487373 -42 9.54594155
NF2_OuterSupport_G10_Rod_05.Rotation 0 -45 0
NF2_OuterSupport_G10_Rod_05.Mother InstrumentFrame
// Volume NF2_OuterSupport_G10_Rod_06; source=NF2 nearfield mechanical overlay; role=low-Z external perimeter support cage rod at 330 deg; volume_cm3=384.375; mass_g=711.09375
Volume NF2_OuterSupport_G10_Rod_06
NF2_OuterSupport_G10_Rod_06.Material G10
NF2_OuterSupport_G10_Rod_06.Visibility 1
NF2_OuterSupport_G10_Rod_06.Shape BRIK 1.2551125 1.2551125 30.5
NF2_OuterSupport_G10_Rod_06.Position 23.2447686 -21 35.2655838
NF2_OuterSupport_G10_Rod_06.Rotation 0 -45 0
NF2_OuterSupport_G10_Rod_06.Mother InstrumentFrame
// Volume NF2_OuterSupport_SS_Hardpoint_B_01; source=NF2 nearfield mechanical overlay; role=bottom stainless mount hardpoint at 30 deg; volume_cm3=2; mass_g=16
Volume NF2_OuterSupport_SS_Hardpoint_B_01
NF2_OuterSupport_SS_Hardpoint_B_01.Material StainlessSteel
NF2_OuterSupport_SS_Hardpoint_B_01.Visibility 1
NF2_OuterSupport_SS_Hardpoint_B_01.Shape BRIK 1 1 0.25
NF2_OuterSupport_SS_Hardpoint_B_01.Position 44.9883021 21 13.5220503
NF2_OuterSupport_SS_Hardpoint_B_01.Rotation 0 -45 0
NF2_OuterSupport_SS_Hardpoint_B_01.Mother InstrumentFrame
// Volume NF2_OuterSupport_SS_Hardpoint_B_02; source=NF2 nearfield mechanical overlay; role=bottom stainless mount hardpoint at 90 deg; volume_cm3=2; mass_g=16
Volume NF2_OuterSupport_SS_Hardpoint_B_02
NF2_OuterSupport_SS_Hardpoint_B_02.Material StainlessSteel
NF2_OuterSupport_SS_Hardpoint_B_02.Visibility 1
NF2_OuterSupport_SS_Hardpoint_B_02.Shape BRIK 1 1 0.25
NF2_OuterSupport_SS_Hardpoint_B_02.Position 19.2686598 42 -12.197592
NF2_OuterSupport_SS_Hardpoint_B_02.Rotation 0 -45 0
NF2_OuterSupport_SS_Hardpoint_B_02.Mother InstrumentFrame
// Volume NF2_OuterSupport_SS_Hardpoint_B_03; source=NF2 nearfield mechanical overlay; role=bottom stainless mount hardpoint at 150 deg; volume_cm3=2; mass_g=16
Volume NF2_OuterSupport_SS_Hardpoint_B_03
NF2_OuterSupport_SS_Hardpoint_B_03.Material StainlessSteel
NF2_OuterSupport_SS_Hardpoint_B_03.Visibility 1
NF2_OuterSupport_SS_Hardpoint_B_03.Shape BRIK 1 1 0.25
NF2_OuterSupport_SS_Hardpoint_B_03.Position -6.45098251 21 -37.9172343
NF2_OuterSupport_SS_Hardpoint_B_03.Rotation 0 -45 0
NF2_OuterSupport_SS_Hardpoint_B_03.Mother InstrumentFrame
// Volume NF2_OuterSupport_SS_Hardpoint_B_04; source=NF2 nearfield mechanical overlay; role=bottom stainless mount hardpoint at 210 deg; volume_cm3=2; mass_g=16
Volume NF2_OuterSupport_SS_Hardpoint_B_04
NF2_OuterSupport_SS_Hardpoint_B_04.Material StainlessSteel
NF2_OuterSupport_SS_Hardpoint_B_04.Visibility 1
NF2_OuterSupport_SS_Hardpoint_B_04.Shape BRIK 1 1 0.25
NF2_OuterSupport_SS_Hardpoint_B_04.Position -6.45098251 -21 -37.9172343
NF2_OuterSupport_SS_Hardpoint_B_04.Rotation 0 -45 0
NF2_OuterSupport_SS_Hardpoint_B_04.Mother InstrumentFrame
// Volume NF2_OuterSupport_SS_Hardpoint_B_05; source=NF2 nearfield mechanical overlay; role=bottom stainless mount hardpoint at 270 deg; volume_cm3=2; mass_g=16
Volume NF2_OuterSupport_SS_Hardpoint_B_05
NF2_OuterSupport_SS_Hardpoint_B_05.Material StainlessSteel
NF2_OuterSupport_SS_Hardpoint_B_05.Visibility 1
NF2_OuterSupport_SS_Hardpoint_B_05.Shape BRIK 1 1 0.25
NF2_OuterSupport_SS_Hardpoint_B_05.Position 19.2686598 -42 -12.197592
NF2_OuterSupport_SS_Hardpoint_B_05.Rotation 0 -45 0
NF2_OuterSupport_SS_Hardpoint_B_05.Mother InstrumentFrame
// Volume NF2_OuterSupport_SS_Hardpoint_B_06; source=NF2 nearfield mechanical overlay; role=bottom stainless mount hardpoint at 330 deg; volume_cm3=2; mass_g=16
Volume NF2_OuterSupport_SS_Hardpoint_B_06
NF2_OuterSupport_SS_Hardpoint_B_06.Material StainlessSteel
NF2_OuterSupport_SS_Hardpoint_B_06.Visibility 1
NF2_OuterSupport_SS_Hardpoint_B_06.Shape BRIK 1 1 0.25
NF2_OuterSupport_SS_Hardpoint_B_06.Position 44.9883021 -21 13.5220503
NF2_OuterSupport_SS_Hardpoint_B_06.Rotation 0 -45 0
NF2_OuterSupport_SS_Hardpoint_B_06.Mother InstrumentFrame
// Volume NF2_OuterSupport_SS_Hardpoint_T_01; source=NF2 nearfield mechanical overlay; role=top stainless mount hardpoint at 30 deg; volume_cm3=2; mass_g=16
Volume NF2_OuterSupport_SS_Hardpoint_T_01
NF2_OuterSupport_SS_Hardpoint_T_01.Material StainlessSteel
NF2_OuterSupport_SS_Hardpoint_T_01.Visibility 1
NF2_OuterSupport_SS_Hardpoint_T_01.Shape BRIK 1 1 0.25
NF2_OuterSupport_SS_Hardpoint_T_01.Position 1.50123504 21 57.0091174
NF2_OuterSupport_SS_Hardpoint_T_01.Rotation 0 -45 0
NF2_OuterSupport_SS_Hardpoint_T_01.Mother InstrumentFrame
// Volume NF2_OuterSupport_SS_Hardpoint_T_02; source=NF2 nearfield mechanical overlay; role=top stainless mount hardpoint at 90 deg; volume_cm3=2; mass_g=16
Volume NF2_OuterSupport_SS_Hardpoint_T_02
NF2_OuterSupport_SS_Hardpoint_T_02.Material StainlessSteel
NF2_OuterSupport_SS_Hardpoint_T_02.Visibility 1
NF2_OuterSupport_SS_Hardpoint_T_02.Shape BRIK 1 1 0.25
NF2_OuterSupport_SS_Hardpoint_T_02.Position -24.2184073 42 31.2894751
NF2_OuterSupport_SS_Hardpoint_T_02.Rotation 0 -45 0
NF2_OuterSupport_SS_Hardpoint_T_02.Mother InstrumentFrame
// Volume NF2_OuterSupport_SS_Hardpoint_T_03; source=NF2 nearfield mechanical overlay; role=top stainless mount hardpoint at 150 deg; volume_cm3=2; mass_g=16
Volume NF2_OuterSupport_SS_Hardpoint_T_03
NF2_OuterSupport_SS_Hardpoint_T_03.Material StainlessSteel
NF2_OuterSupport_SS_Hardpoint_T_03.Visibility 1
NF2_OuterSupport_SS_Hardpoint_T_03.Shape BRIK 1 1 0.25
NF2_OuterSupport_SS_Hardpoint_T_03.Position -49.9380496 21 5.56983277
NF2_OuterSupport_SS_Hardpoint_T_03.Rotation 0 -45 0
NF2_OuterSupport_SS_Hardpoint_T_03.Mother InstrumentFrame
// Volume NF2_OuterSupport_SS_Hardpoint_T_04; source=NF2 nearfield mechanical overlay; role=top stainless mount hardpoint at 210 deg; volume_cm3=2; mass_g=16
Volume NF2_OuterSupport_SS_Hardpoint_T_04
NF2_OuterSupport_SS_Hardpoint_T_04.Material StainlessSteel
NF2_OuterSupport_SS_Hardpoint_T_04.Visibility 1
NF2_OuterSupport_SS_Hardpoint_T_04.Shape BRIK 1 1 0.25
NF2_OuterSupport_SS_Hardpoint_T_04.Position -49.9380496 -21 5.56983277
NF2_OuterSupport_SS_Hardpoint_T_04.Rotation 0 -45 0
NF2_OuterSupport_SS_Hardpoint_T_04.Mother InstrumentFrame
// Volume NF2_OuterSupport_SS_Hardpoint_T_05; source=NF2 nearfield mechanical overlay; role=top stainless mount hardpoint at 270 deg; volume_cm3=2; mass_g=16
Volume NF2_OuterSupport_SS_Hardpoint_T_05
NF2_OuterSupport_SS_Hardpoint_T_05.Material StainlessSteel
NF2_OuterSupport_SS_Hardpoint_T_05.Visibility 1
NF2_OuterSupport_SS_Hardpoint_T_05.Shape BRIK 1 1 0.25
NF2_OuterSupport_SS_Hardpoint_T_05.Position -24.2184073 -42 31.2894751
NF2_OuterSupport_SS_Hardpoint_T_05.Rotation 0 -45 0
NF2_OuterSupport_SS_Hardpoint_T_05.Mother InstrumentFrame
// Volume NF2_OuterSupport_SS_Hardpoint_T_06; source=NF2 nearfield mechanical overlay; role=top stainless mount hardpoint at 330 deg; volume_cm3=2; mass_g=16
Volume NF2_OuterSupport_SS_Hardpoint_T_06
NF2_OuterSupport_SS_Hardpoint_T_06.Material StainlessSteel
NF2_OuterSupport_SS_Hardpoint_T_06.Visibility 1
NF2_OuterSupport_SS_Hardpoint_T_06.Shape BRIK 1 1 0.25
NF2_OuterSupport_SS_Hardpoint_T_06.Position 1.50123504 -21 57.0091174
NF2_OuterSupport_SS_Hardpoint_T_06.Rotation 0 -45 0
NF2_OuterSupport_SS_Hardpoint_T_06.Mother InstrumentFrame
// END NF2_NEARFIELD_OUTER_MECHANICAL_SUPPORT_PROXY

// END PINNED_SG3B_TOP_SERVICES_AND_OUTER_SUPPORT_CAGE

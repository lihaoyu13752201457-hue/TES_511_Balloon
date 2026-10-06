// SH3 pure dilution-refrigerator base; chimney intentionally not assembled.
// Parent-frame 45 degree tilt is retained from pinned SG3B.
Include Materials_SH3_Assembly_OptV3.geo
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
SH3_DRBase_MXC50mK_ColdFingerPortCutOrientation.Position -15.200000 0 -2.800000
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
SH3_DRBase_Still_ColdFingerPortCutOrientation.Position -15.650000 0 -2.800000
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
SH3_DRBase_4K_ColdFingerPortCutOrientation.Position -17.850000 0 -2.800000
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
SH3_DRBase_60K_ColdFingerPortCutOrientation.Position -18.350000 0 -2.800000
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

// OptV3: one welded 300 K Al shell. The chimney branch is unioned into the
// curved DR side shell and bottom cap; the branch bore and DR cavity are then
// subtracted. This creates a continuous saddle joint, not a plane/nozzle contact.
Shape PCON SH3_OptV3_DRFullSideShellShape
SH3_OptV3_DRFullSideShellShape.Parameters 0 360 2 -13.600000 20.100000 20.600000 37.500000 20.100000 20.600000
Shape PCON SH3_OptV3_DRBottomCapShape
SH3_OptV3_DRBottomCapShape.Parameters 0 360 2 -14.100000 0 20.600000 -13.600000 0 20.600000
Orientation SH3_OptV3_IdentityOrientation
SH3_OptV3_IdentityOrientation.Position 0 0 0
Shape Union SH3_OptV3_DRSidePlusBottomShape
SH3_OptV3_DRSidePlusBottomShape.Parameters SH3_OptV3_DRFullSideShellShape SH3_OptV3_DRBottomCapShape SH3_OptV3_IdentityOrientation

Shape TUBS SH3_OptV3_ChimneyBranchOuterSolid
SH3_OptV3_ChimneyBranchOuterSolid.Parameters 0 11.050000 15.375000 0 360
Orientation SH3_OptV3_ChimneyBranchOuterOrientation
SH3_OptV3_ChimneyBranchOuterOrientation.Position -30.375000 0 -2.800000
SH3_OptV3_ChimneyBranchOuterOrientation.Rotation 0 90 0
Shape Union SH3_OptV3_DRPlusChimneyOuterUnionShape
SH3_OptV3_DRPlusChimneyOuterUnionShape.Parameters SH3_OptV3_DRSidePlusBottomShape SH3_OptV3_ChimneyBranchOuterSolid SH3_OptV3_ChimneyBranchOuterOrientation

Shape TUBS SH3_OptV3_ChimneyBranchInnerBore
SH3_OptV3_ChimneyBranchInnerBore.Parameters 0 10.750000 15.800000 0 360
Orientation SH3_OptV3_ChimneyBranchInnerBoreOrientation
SH3_OptV3_ChimneyBranchInnerBoreOrientation.Position -30.300000 0 -2.800000
SH3_OptV3_ChimneyBranchInnerBoreOrientation.Rotation 0 90 0
Shape Subtraction SH3_OptV3_WeldedShellWithOpenBranchShape
SH3_OptV3_WeldedShellWithOpenBranchShape.Parameters SH3_OptV3_DRPlusChimneyOuterUnionShape SH3_OptV3_ChimneyBranchInnerBore SH3_OptV3_ChimneyBranchInnerBoreOrientation

Shape PCON SH3_OptV3_DRMainVacuumCavityShape
SH3_OptV3_DRMainVacuumCavityShape.Parameters 0 360 2 -13.600000 0 20.100000 37.500000 0 20.100000
Shape Subtraction SH3_OptV3_WeldedSaddleOuterShellShape
SH3_OptV3_WeldedSaddleOuterShellShape.Parameters SH3_OptV3_WeldedShellWithOpenBranchShape SH3_OptV3_DRMainVacuumCavityShape SH3_OptV3_IdentityOrientation

Volume SH3_DRBase_VacuumJacket_PortedSideShell
SH3_DRBase_VacuumJacket_PortedSideShell.Material Aluminium
SH3_DRBase_VacuumJacket_PortedSideShell.Visibility 1
SH3_DRBase_VacuumJacket_PortedSideShell.Shape SH3_OptV3_WeldedSaddleOuterShellShape
SH3_DRBase_VacuumJacket_PortedSideShell.Position 0 0 0
SH3_DRBase_VacuumJacket_PortedSideShell.Mother InstrumentFrame


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
// OptV2: optical-axis clearance through the upper NF2 aluminium mount plate.
Shape PCON SH3_OptV2_NF2_TopMount_BaseShape
SH3_OptV2_NF2_TopMount_BaseShape.Parameters 0 360 2 -0.25 34.9765777 48.8250037 0.25 34.9765777 48.8250037
Shape TUBS SH3_OptV2_NF2_TopMount_OpticalCutShape
SH3_OptV2_NF2_TopMount_OpticalCutShape.Parameters 0 3.000000 5.000000 0 360
Orientation SH3_OptV2_NF2_TopMount_OpticalCutOrientation
SH3_OptV2_NF2_TopMount_OpticalCutOrientation.Position -48.959798 0 0
SH3_OptV2_NF2_TopMount_OpticalCutOrientation.Rotation 0 135 0
Shape Subtraction SH3_OptV2_NF2_TopMount_WithOpticalCutShape
SH3_OptV2_NF2_TopMount_WithOpticalCutShape.Parameters SH3_OptV2_NF2_TopMount_BaseShape SH3_OptV2_NF2_TopMount_OpticalCutShape SH3_OptV2_NF2_TopMount_OpticalCutOrientation

// Volume NF2_OuterSupport_Al_TopMountAnnulus; source=NF2 nearfield mechanical overlay; role=top support interface annulus on the vertical support axis; volume_cm3=1822.94055; mass_g=4921.93949
Volume NF2_OuterSupport_Al_TopMountAnnulus
NF2_OuterSupport_Al_TopMountAnnulus.Material Aluminium
NF2_OuterSupport_Al_TopMountAnnulus.Visibility 1
NF2_OuterSupport_Al_TopMountAnnulus.Shape SH3_OptV2_NF2_TopMount_WithOpticalCutShape
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

// BEGIN SH3_ASSEMBLY_OPT_V3
// Boolean-welded chimney/DR outer Al shell; no OptV2 frustum or nozzle.
// Geometry only; no structural, transport, timing, or sensitivity authority.
// BEGIN FLATTENED_SH3_CHIMNEY_OPT_V3
// SH3 standalone/mergeable TES chimney component
// Local frame contract: x'=optical axis, signal travels from negative x' to positive x'.
// This file deliberately does not define SH3_ChimneyFrame or any World volume.
// A wrapper must define SH3_ChimneyFrame and then include this file.
// Pinned SG3B top-level TES/support placements are recentered from z=-5.2 cm to local z=0.
// The five local shell layers are not DR cold plates/vessels and have no thermal-stage assignment.
// Active BGO: 40 mm side plus 40 mm optical-front and cold-port-rear annuli.
// Mechanical Al: 3 mm side/front only; the cold-finger rear face has no Al end cap.
// Physics status: geometry and scorer definitions only; no Bi/plastic/transport/timing authority.

// BEGIN PINNED_SG3B_TES_BLOCK
// Volume TES_Pixel_L0; material=Ta
Volume TES_Pixel_L0
TES_Pixel_L0.Material Ta
TES_Pixel_L0.Visibility 1
TES_Pixel_L0.Shape BRIK 0.15 0.075 0.075

// Volume TES_L0; material=Vacuum
Volume TES_L0
TES_L0.Material Vacuum
TES_L0.Visibility 0
TES_L0.Shape BRIK 0.15 1.8 1.8

TES_L0.Position -38.55 0 -2.8
TES_L0.Mother InstrumentFrame

TES_Pixel_L0.Copy TP_L0_00000
TP_L0_00000.Position 0 -1.705 0
TP_L0_00000.Mother TES_L0
TP_L0_00000.Visibility 0

TES_Pixel_L0.Copy TP_L0_00001
TP_L0_00001.Position 0 -1.55 -0.62
TP_L0_00001.Mother TES_L0
TP_L0_00001.Visibility 0

TES_Pixel_L0.Copy TP_L0_00002
TP_L0_00002.Position 0 -1.55 -0.465
TP_L0_00002.Mother TES_L0
TP_L0_00002.Visibility 0

TES_Pixel_L0.Copy TP_L0_00003
TP_L0_00003.Position 0 -1.55 -0.31
TP_L0_00003.Mother TES_L0
TP_L0_00003.Visibility 0

TES_Pixel_L0.Copy TP_L0_00004
TP_L0_00004.Position 0 -1.55 -0.155
TP_L0_00004.Mother TES_L0
TP_L0_00004.Visibility 0

TES_Pixel_L0.Copy TP_L0_00005
TP_L0_00005.Position 0 -1.55 0
TP_L0_00005.Mother TES_L0
TP_L0_00005.Visibility 0

TES_Pixel_L0.Copy TP_L0_00006
TP_L0_00006.Position 0 -1.55 0.155
TP_L0_00006.Mother TES_L0
TP_L0_00006.Visibility 0

TES_Pixel_L0.Copy TP_L0_00007
TP_L0_00007.Position 0 -1.55 0.31
TP_L0_00007.Mother TES_L0
TP_L0_00007.Visibility 0

TES_Pixel_L0.Copy TP_L0_00008
TP_L0_00008.Position 0 -1.55 0.465
TP_L0_00008.Mother TES_L0
TP_L0_00008.Visibility 0

TES_Pixel_L0.Copy TP_L0_00009
TP_L0_00009.Position 0 -1.55 0.62
TP_L0_00009.Mother TES_L0
TP_L0_00009.Visibility 0

TES_Pixel_L0.Copy TP_L0_00010
TP_L0_00010.Position 0 -1.395 -0.93
TP_L0_00010.Mother TES_L0
TP_L0_00010.Visibility 0

TES_Pixel_L0.Copy TP_L0_00011
TP_L0_00011.Position 0 -1.395 -0.775
TP_L0_00011.Mother TES_L0
TP_L0_00011.Visibility 0

TES_Pixel_L0.Copy TP_L0_00012
TP_L0_00012.Position 0 -1.395 -0.62
TP_L0_00012.Mother TES_L0
TP_L0_00012.Visibility 0

TES_Pixel_L0.Copy TP_L0_00013
TP_L0_00013.Position 0 -1.395 -0.465
TP_L0_00013.Mother TES_L0
TP_L0_00013.Visibility 0

TES_Pixel_L0.Copy TP_L0_00014
TP_L0_00014.Position 0 -1.395 -0.31
TP_L0_00014.Mother TES_L0
TP_L0_00014.Visibility 0

TES_Pixel_L0.Copy TP_L0_00015
TP_L0_00015.Position 0 -1.395 -0.155
TP_L0_00015.Mother TES_L0
TP_L0_00015.Visibility 0

TES_Pixel_L0.Copy TP_L0_00016
TP_L0_00016.Position 0 -1.395 0
TP_L0_00016.Mother TES_L0
TP_L0_00016.Visibility 0

TES_Pixel_L0.Copy TP_L0_00017
TP_L0_00017.Position 0 -1.395 0.155
TP_L0_00017.Mother TES_L0
TP_L0_00017.Visibility 0

TES_Pixel_L0.Copy TP_L0_00018
TP_L0_00018.Position 0 -1.395 0.31
TP_L0_00018.Mother TES_L0
TP_L0_00018.Visibility 0

TES_Pixel_L0.Copy TP_L0_00019
TP_L0_00019.Position 0 -1.395 0.465
TP_L0_00019.Mother TES_L0
TP_L0_00019.Visibility 0

TES_Pixel_L0.Copy TP_L0_00020
TP_L0_00020.Position 0 -1.395 0.62
TP_L0_00020.Mother TES_L0
TP_L0_00020.Visibility 0

TES_Pixel_L0.Copy TP_L0_00021
TP_L0_00021.Position 0 -1.395 0.775
TP_L0_00021.Mother TES_L0
TP_L0_00021.Visibility 0

TES_Pixel_L0.Copy TP_L0_00022
TP_L0_00022.Position 0 -1.395 0.93
TP_L0_00022.Mother TES_L0
TP_L0_00022.Visibility 0

TES_Pixel_L0.Copy TP_L0_00023
TP_L0_00023.Position 0 -1.24 -1.085
TP_L0_00023.Mother TES_L0
TP_L0_00023.Visibility 0

TES_Pixel_L0.Copy TP_L0_00024
TP_L0_00024.Position 0 -1.24 -0.93
TP_L0_00024.Mother TES_L0
TP_L0_00024.Visibility 0

TES_Pixel_L0.Copy TP_L0_00025
TP_L0_00025.Position 0 -1.24 -0.775
TP_L0_00025.Mother TES_L0
TP_L0_00025.Visibility 0

TES_Pixel_L0.Copy TP_L0_00026
TP_L0_00026.Position 0 -1.24 -0.62
TP_L0_00026.Mother TES_L0
TP_L0_00026.Visibility 0

TES_Pixel_L0.Copy TP_L0_00027
TP_L0_00027.Position 0 -1.24 -0.465
TP_L0_00027.Mother TES_L0
TP_L0_00027.Visibility 0

TES_Pixel_L0.Copy TP_L0_00028
TP_L0_00028.Position 0 -1.24 -0.31
TP_L0_00028.Mother TES_L0
TP_L0_00028.Visibility 0

TES_Pixel_L0.Copy TP_L0_00029
TP_L0_00029.Position 0 -1.24 -0.155
TP_L0_00029.Mother TES_L0
TP_L0_00029.Visibility 0

TES_Pixel_L0.Copy TP_L0_00030
TP_L0_00030.Position 0 -1.24 0
TP_L0_00030.Mother TES_L0
TP_L0_00030.Visibility 0

TES_Pixel_L0.Copy TP_L0_00031
TP_L0_00031.Position 0 -1.24 0.155
TP_L0_00031.Mother TES_L0
TP_L0_00031.Visibility 0

TES_Pixel_L0.Copy TP_L0_00032
TP_L0_00032.Position 0 -1.24 0.31
TP_L0_00032.Mother TES_L0
TP_L0_00032.Visibility 0

TES_Pixel_L0.Copy TP_L0_00033
TP_L0_00033.Position 0 -1.24 0.465
TP_L0_00033.Mother TES_L0
TP_L0_00033.Visibility 0

TES_Pixel_L0.Copy TP_L0_00034
TP_L0_00034.Position 0 -1.24 0.62
TP_L0_00034.Mother TES_L0
TP_L0_00034.Visibility 0

TES_Pixel_L0.Copy TP_L0_00035
TP_L0_00035.Position 0 -1.24 0.775
TP_L0_00035.Mother TES_L0
TP_L0_00035.Visibility 0

TES_Pixel_L0.Copy TP_L0_00036
TP_L0_00036.Position 0 -1.24 0.93
TP_L0_00036.Mother TES_L0
TP_L0_00036.Visibility 0

TES_Pixel_L0.Copy TP_L0_00037
TP_L0_00037.Position 0 -1.24 1.085
TP_L0_00037.Mother TES_L0
TP_L0_00037.Visibility 0

TES_Pixel_L0.Copy TP_L0_00038
TP_L0_00038.Position 0 -1.085 -1.24
TP_L0_00038.Mother TES_L0
TP_L0_00038.Visibility 0

TES_Pixel_L0.Copy TP_L0_00039
TP_L0_00039.Position 0 -1.085 -1.085
TP_L0_00039.Mother TES_L0
TP_L0_00039.Visibility 0

TES_Pixel_L0.Copy TP_L0_00040
TP_L0_00040.Position 0 -1.085 -0.93
TP_L0_00040.Mother TES_L0
TP_L0_00040.Visibility 0

TES_Pixel_L0.Copy TP_L0_00041
TP_L0_00041.Position 0 -1.085 -0.775
TP_L0_00041.Mother TES_L0
TP_L0_00041.Visibility 0

TES_Pixel_L0.Copy TP_L0_00042
TP_L0_00042.Position 0 -1.085 -0.62
TP_L0_00042.Mother TES_L0
TP_L0_00042.Visibility 0

TES_Pixel_L0.Copy TP_L0_00043
TP_L0_00043.Position 0 -1.085 -0.465
TP_L0_00043.Mother TES_L0
TP_L0_00043.Visibility 0

TES_Pixel_L0.Copy TP_L0_00044
TP_L0_00044.Position 0 -1.085 -0.31
TP_L0_00044.Mother TES_L0
TP_L0_00044.Visibility 0

TES_Pixel_L0.Copy TP_L0_00045
TP_L0_00045.Position 0 -1.085 -0.155
TP_L0_00045.Mother TES_L0
TP_L0_00045.Visibility 0

TES_Pixel_L0.Copy TP_L0_00046
TP_L0_00046.Position 0 -1.085 0
TP_L0_00046.Mother TES_L0
TP_L0_00046.Visibility 0

TES_Pixel_L0.Copy TP_L0_00047
TP_L0_00047.Position 0 -1.085 0.155
TP_L0_00047.Mother TES_L0
TP_L0_00047.Visibility 0

TES_Pixel_L0.Copy TP_L0_00048
TP_L0_00048.Position 0 -1.085 0.31
TP_L0_00048.Mother TES_L0
TP_L0_00048.Visibility 0

TES_Pixel_L0.Copy TP_L0_00049
TP_L0_00049.Position 0 -1.085 0.465
TP_L0_00049.Mother TES_L0
TP_L0_00049.Visibility 0

TES_Pixel_L0.Copy TP_L0_00050
TP_L0_00050.Position 0 -1.085 0.62
TP_L0_00050.Mother TES_L0
TP_L0_00050.Visibility 0

TES_Pixel_L0.Copy TP_L0_00051
TP_L0_00051.Position 0 -1.085 0.775
TP_L0_00051.Mother TES_L0
TP_L0_00051.Visibility 0

TES_Pixel_L0.Copy TP_L0_00052
TP_L0_00052.Position 0 -1.085 0.93
TP_L0_00052.Mother TES_L0
TP_L0_00052.Visibility 0

TES_Pixel_L0.Copy TP_L0_00053
TP_L0_00053.Position 0 -1.085 1.085
TP_L0_00053.Mother TES_L0
TP_L0_00053.Visibility 0

TES_Pixel_L0.Copy TP_L0_00054
TP_L0_00054.Position 0 -1.085 1.24
TP_L0_00054.Mother TES_L0
TP_L0_00054.Visibility 0

TES_Pixel_L0.Copy TP_L0_00055
TP_L0_00055.Position 0 -0.93 -1.395
TP_L0_00055.Mother TES_L0
TP_L0_00055.Visibility 0

TES_Pixel_L0.Copy TP_L0_00056
TP_L0_00056.Position 0 -0.93 -1.24
TP_L0_00056.Mother TES_L0
TP_L0_00056.Visibility 0

TES_Pixel_L0.Copy TP_L0_00057
TP_L0_00057.Position 0 -0.93 -1.085
TP_L0_00057.Mother TES_L0
TP_L0_00057.Visibility 0

TES_Pixel_L0.Copy TP_L0_00058
TP_L0_00058.Position 0 -0.93 -0.93
TP_L0_00058.Mother TES_L0
TP_L0_00058.Visibility 0

TES_Pixel_L0.Copy TP_L0_00059
TP_L0_00059.Position 0 -0.93 -0.775
TP_L0_00059.Mother TES_L0
TP_L0_00059.Visibility 0

TES_Pixel_L0.Copy TP_L0_00060
TP_L0_00060.Position 0 -0.93 -0.62
TP_L0_00060.Mother TES_L0
TP_L0_00060.Visibility 0

TES_Pixel_L0.Copy TP_L0_00061
TP_L0_00061.Position 0 -0.93 -0.465
TP_L0_00061.Mother TES_L0
TP_L0_00061.Visibility 0

TES_Pixel_L0.Copy TP_L0_00062
TP_L0_00062.Position 0 -0.93 -0.31
TP_L0_00062.Mother TES_L0
TP_L0_00062.Visibility 0

TES_Pixel_L0.Copy TP_L0_00063
TP_L0_00063.Position 0 -0.93 -0.155
TP_L0_00063.Mother TES_L0
TP_L0_00063.Visibility 0

TES_Pixel_L0.Copy TP_L0_00064
TP_L0_00064.Position 0 -0.93 0
TP_L0_00064.Mother TES_L0
TP_L0_00064.Visibility 0

TES_Pixel_L0.Copy TP_L0_00065
TP_L0_00065.Position 0 -0.93 0.155
TP_L0_00065.Mother TES_L0
TP_L0_00065.Visibility 0

TES_Pixel_L0.Copy TP_L0_00066
TP_L0_00066.Position 0 -0.93 0.31
TP_L0_00066.Mother TES_L0
TP_L0_00066.Visibility 0

TES_Pixel_L0.Copy TP_L0_00067
TP_L0_00067.Position 0 -0.93 0.465
TP_L0_00067.Mother TES_L0
TP_L0_00067.Visibility 0

TES_Pixel_L0.Copy TP_L0_00068
TP_L0_00068.Position 0 -0.93 0.62
TP_L0_00068.Mother TES_L0
TP_L0_00068.Visibility 0

TES_Pixel_L0.Copy TP_L0_00069
TP_L0_00069.Position 0 -0.93 0.775
TP_L0_00069.Mother TES_L0
TP_L0_00069.Visibility 0

TES_Pixel_L0.Copy TP_L0_00070
TP_L0_00070.Position 0 -0.93 0.93
TP_L0_00070.Mother TES_L0
TP_L0_00070.Visibility 0

TES_Pixel_L0.Copy TP_L0_00071
TP_L0_00071.Position 0 -0.93 1.085
TP_L0_00071.Mother TES_L0
TP_L0_00071.Visibility 0

TES_Pixel_L0.Copy TP_L0_00072
TP_L0_00072.Position 0 -0.93 1.24
TP_L0_00072.Mother TES_L0
TP_L0_00072.Visibility 0

TES_Pixel_L0.Copy TP_L0_00073
TP_L0_00073.Position 0 -0.93 1.395
TP_L0_00073.Mother TES_L0
TP_L0_00073.Visibility 0

TES_Pixel_L0.Copy TP_L0_00074
TP_L0_00074.Position 0 -0.775 -1.395
TP_L0_00074.Mother TES_L0
TP_L0_00074.Visibility 0

TES_Pixel_L0.Copy TP_L0_00075
TP_L0_00075.Position 0 -0.775 -1.24
TP_L0_00075.Mother TES_L0
TP_L0_00075.Visibility 0

TES_Pixel_L0.Copy TP_L0_00076
TP_L0_00076.Position 0 -0.775 -1.085
TP_L0_00076.Mother TES_L0
TP_L0_00076.Visibility 0

TES_Pixel_L0.Copy TP_L0_00077
TP_L0_00077.Position 0 -0.775 -0.93
TP_L0_00077.Mother TES_L0
TP_L0_00077.Visibility 0

TES_Pixel_L0.Copy TP_L0_00078
TP_L0_00078.Position 0 -0.775 -0.775
TP_L0_00078.Mother TES_L0
TP_L0_00078.Visibility 0

TES_Pixel_L0.Copy TP_L0_00079
TP_L0_00079.Position 0 -0.775 -0.62
TP_L0_00079.Mother TES_L0
TP_L0_00079.Visibility 0

TES_Pixel_L0.Copy TP_L0_00080
TP_L0_00080.Position 0 -0.775 -0.465
TP_L0_00080.Mother TES_L0
TP_L0_00080.Visibility 0

TES_Pixel_L0.Copy TP_L0_00081
TP_L0_00081.Position 0 -0.775 -0.31
TP_L0_00081.Mother TES_L0
TP_L0_00081.Visibility 0

TES_Pixel_L0.Copy TP_L0_00082
TP_L0_00082.Position 0 -0.775 -0.155
TP_L0_00082.Mother TES_L0
TP_L0_00082.Visibility 0

TES_Pixel_L0.Copy TP_L0_00083
TP_L0_00083.Position 0 -0.775 0
TP_L0_00083.Mother TES_L0
TP_L0_00083.Visibility 0

TES_Pixel_L0.Copy TP_L0_00084
TP_L0_00084.Position 0 -0.775 0.155
TP_L0_00084.Mother TES_L0
TP_L0_00084.Visibility 0

TES_Pixel_L0.Copy TP_L0_00085
TP_L0_00085.Position 0 -0.775 0.31
TP_L0_00085.Mother TES_L0
TP_L0_00085.Visibility 0

TES_Pixel_L0.Copy TP_L0_00086
TP_L0_00086.Position 0 -0.775 0.465
TP_L0_00086.Mother TES_L0
TP_L0_00086.Visibility 0

TES_Pixel_L0.Copy TP_L0_00087
TP_L0_00087.Position 0 -0.775 0.62
TP_L0_00087.Mother TES_L0
TP_L0_00087.Visibility 0

TES_Pixel_L0.Copy TP_L0_00088
TP_L0_00088.Position 0 -0.775 0.775
TP_L0_00088.Mother TES_L0
TP_L0_00088.Visibility 0

TES_Pixel_L0.Copy TP_L0_00089
TP_L0_00089.Position 0 -0.775 0.93
TP_L0_00089.Mother TES_L0
TP_L0_00089.Visibility 0

TES_Pixel_L0.Copy TP_L0_00090
TP_L0_00090.Position 0 -0.775 1.085
TP_L0_00090.Mother TES_L0
TP_L0_00090.Visibility 0

TES_Pixel_L0.Copy TP_L0_00091
TP_L0_00091.Position 0 -0.775 1.24
TP_L0_00091.Mother TES_L0
TP_L0_00091.Visibility 0

TES_Pixel_L0.Copy TP_L0_00092
TP_L0_00092.Position 0 -0.775 1.395
TP_L0_00092.Mother TES_L0
TP_L0_00092.Visibility 0

TES_Pixel_L0.Copy TP_L0_00093
TP_L0_00093.Position 0 -0.62 -1.55
TP_L0_00093.Mother TES_L0
TP_L0_00093.Visibility 0

TES_Pixel_L0.Copy TP_L0_00094
TP_L0_00094.Position 0 -0.62 -1.395
TP_L0_00094.Mother TES_L0
TP_L0_00094.Visibility 0

TES_Pixel_L0.Copy TP_L0_00095
TP_L0_00095.Position 0 -0.62 -1.24
TP_L0_00095.Mother TES_L0
TP_L0_00095.Visibility 0

TES_Pixel_L0.Copy TP_L0_00096
TP_L0_00096.Position 0 -0.62 -1.085
TP_L0_00096.Mother TES_L0
TP_L0_00096.Visibility 0

TES_Pixel_L0.Copy TP_L0_00097
TP_L0_00097.Position 0 -0.62 -0.93
TP_L0_00097.Mother TES_L0
TP_L0_00097.Visibility 0

TES_Pixel_L0.Copy TP_L0_00098
TP_L0_00098.Position 0 -0.62 -0.775
TP_L0_00098.Mother TES_L0
TP_L0_00098.Visibility 0

TES_Pixel_L0.Copy TP_L0_00099
TP_L0_00099.Position 0 -0.62 -0.62
TP_L0_00099.Mother TES_L0
TP_L0_00099.Visibility 0

TES_Pixel_L0.Copy TP_L0_00100
TP_L0_00100.Position 0 -0.62 -0.465
TP_L0_00100.Mother TES_L0
TP_L0_00100.Visibility 0

TES_Pixel_L0.Copy TP_L0_00101
TP_L0_00101.Position 0 -0.62 -0.31
TP_L0_00101.Mother TES_L0
TP_L0_00101.Visibility 0

TES_Pixel_L0.Copy TP_L0_00102
TP_L0_00102.Position 0 -0.62 -0.155
TP_L0_00102.Mother TES_L0
TP_L0_00102.Visibility 0

TES_Pixel_L0.Copy TP_L0_00103
TP_L0_00103.Position 0 -0.62 0
TP_L0_00103.Mother TES_L0
TP_L0_00103.Visibility 0

TES_Pixel_L0.Copy TP_L0_00104
TP_L0_00104.Position 0 -0.62 0.155
TP_L0_00104.Mother TES_L0
TP_L0_00104.Visibility 0

TES_Pixel_L0.Copy TP_L0_00105
TP_L0_00105.Position 0 -0.62 0.31
TP_L0_00105.Mother TES_L0
TP_L0_00105.Visibility 0

TES_Pixel_L0.Copy TP_L0_00106
TP_L0_00106.Position 0 -0.62 0.465
TP_L0_00106.Mother TES_L0
TP_L0_00106.Visibility 0

TES_Pixel_L0.Copy TP_L0_00107
TP_L0_00107.Position 0 -0.62 0.62
TP_L0_00107.Mother TES_L0
TP_L0_00107.Visibility 0

TES_Pixel_L0.Copy TP_L0_00108
TP_L0_00108.Position 0 -0.62 0.775
TP_L0_00108.Mother TES_L0
TP_L0_00108.Visibility 0

TES_Pixel_L0.Copy TP_L0_00109
TP_L0_00109.Position 0 -0.62 0.93
TP_L0_00109.Mother TES_L0
TP_L0_00109.Visibility 0

TES_Pixel_L0.Copy TP_L0_00110
TP_L0_00110.Position 0 -0.62 1.085
TP_L0_00110.Mother TES_L0
TP_L0_00110.Visibility 0

TES_Pixel_L0.Copy TP_L0_00111
TP_L0_00111.Position 0 -0.62 1.24
TP_L0_00111.Mother TES_L0
TP_L0_00111.Visibility 0

TES_Pixel_L0.Copy TP_L0_00112
TP_L0_00112.Position 0 -0.62 1.395
TP_L0_00112.Mother TES_L0
TP_L0_00112.Visibility 0

TES_Pixel_L0.Copy TP_L0_00113
TP_L0_00113.Position 0 -0.62 1.55
TP_L0_00113.Mother TES_L0
TP_L0_00113.Visibility 0

TES_Pixel_L0.Copy TP_L0_00114
TP_L0_00114.Position 0 -0.465 -1.55
TP_L0_00114.Mother TES_L0
TP_L0_00114.Visibility 0

TES_Pixel_L0.Copy TP_L0_00115
TP_L0_00115.Position 0 -0.465 -1.395
TP_L0_00115.Mother TES_L0
TP_L0_00115.Visibility 0

TES_Pixel_L0.Copy TP_L0_00116
TP_L0_00116.Position 0 -0.465 -1.24
TP_L0_00116.Mother TES_L0
TP_L0_00116.Visibility 0

TES_Pixel_L0.Copy TP_L0_00117
TP_L0_00117.Position 0 -0.465 -1.085
TP_L0_00117.Mother TES_L0
TP_L0_00117.Visibility 0

TES_Pixel_L0.Copy TP_L0_00118
TP_L0_00118.Position 0 -0.465 -0.93
TP_L0_00118.Mother TES_L0
TP_L0_00118.Visibility 0

TES_Pixel_L0.Copy TP_L0_00119
TP_L0_00119.Position 0 -0.465 -0.775
TP_L0_00119.Mother TES_L0
TP_L0_00119.Visibility 0

TES_Pixel_L0.Copy TP_L0_00120
TP_L0_00120.Position 0 -0.465 -0.62
TP_L0_00120.Mother TES_L0
TP_L0_00120.Visibility 0

TES_Pixel_L0.Copy TP_L0_00121
TP_L0_00121.Position 0 -0.465 -0.465
TP_L0_00121.Mother TES_L0
TP_L0_00121.Visibility 0

TES_Pixel_L0.Copy TP_L0_00122
TP_L0_00122.Position 0 -0.465 -0.31
TP_L0_00122.Mother TES_L0
TP_L0_00122.Visibility 0

TES_Pixel_L0.Copy TP_L0_00123
TP_L0_00123.Position 0 -0.465 -0.155
TP_L0_00123.Mother TES_L0
TP_L0_00123.Visibility 0

TES_Pixel_L0.Copy TP_L0_00124
TP_L0_00124.Position 0 -0.465 0
TP_L0_00124.Mother TES_L0
TP_L0_00124.Visibility 0

TES_Pixel_L0.Copy TP_L0_00125
TP_L0_00125.Position 0 -0.465 0.155
TP_L0_00125.Mother TES_L0
TP_L0_00125.Visibility 0

TES_Pixel_L0.Copy TP_L0_00126
TP_L0_00126.Position 0 -0.465 0.31
TP_L0_00126.Mother TES_L0
TP_L0_00126.Visibility 0

TES_Pixel_L0.Copy TP_L0_00127
TP_L0_00127.Position 0 -0.465 0.465
TP_L0_00127.Mother TES_L0
TP_L0_00127.Visibility 0

TES_Pixel_L0.Copy TP_L0_00128
TP_L0_00128.Position 0 -0.465 0.62
TP_L0_00128.Mother TES_L0
TP_L0_00128.Visibility 0

TES_Pixel_L0.Copy TP_L0_00129
TP_L0_00129.Position 0 -0.465 0.775
TP_L0_00129.Mother TES_L0
TP_L0_00129.Visibility 0

TES_Pixel_L0.Copy TP_L0_00130
TP_L0_00130.Position 0 -0.465 0.93
TP_L0_00130.Mother TES_L0
TP_L0_00130.Visibility 0

TES_Pixel_L0.Copy TP_L0_00131
TP_L0_00131.Position 0 -0.465 1.085
TP_L0_00131.Mother TES_L0
TP_L0_00131.Visibility 0

TES_Pixel_L0.Copy TP_L0_00132
TP_L0_00132.Position 0 -0.465 1.24
TP_L0_00132.Mother TES_L0
TP_L0_00132.Visibility 0

TES_Pixel_L0.Copy TP_L0_00133
TP_L0_00133.Position 0 -0.465 1.395
TP_L0_00133.Mother TES_L0
TP_L0_00133.Visibility 0

TES_Pixel_L0.Copy TP_L0_00134
TP_L0_00134.Position 0 -0.465 1.55
TP_L0_00134.Mother TES_L0
TP_L0_00134.Visibility 0

TES_Pixel_L0.Copy TP_L0_00135
TP_L0_00135.Position 0 -0.31 -1.55
TP_L0_00135.Mother TES_L0
TP_L0_00135.Visibility 0

TES_Pixel_L0.Copy TP_L0_00136
TP_L0_00136.Position 0 -0.31 -1.395
TP_L0_00136.Mother TES_L0
TP_L0_00136.Visibility 0

TES_Pixel_L0.Copy TP_L0_00137
TP_L0_00137.Position 0 -0.31 -1.24
TP_L0_00137.Mother TES_L0
TP_L0_00137.Visibility 0

TES_Pixel_L0.Copy TP_L0_00138
TP_L0_00138.Position 0 -0.31 -1.085
TP_L0_00138.Mother TES_L0
TP_L0_00138.Visibility 0

TES_Pixel_L0.Copy TP_L0_00139
TP_L0_00139.Position 0 -0.31 -0.93
TP_L0_00139.Mother TES_L0
TP_L0_00139.Visibility 0

TES_Pixel_L0.Copy TP_L0_00140
TP_L0_00140.Position 0 -0.31 -0.775
TP_L0_00140.Mother TES_L0
TP_L0_00140.Visibility 0

TES_Pixel_L0.Copy TP_L0_00141
TP_L0_00141.Position 0 -0.31 -0.62
TP_L0_00141.Mother TES_L0
TP_L0_00141.Visibility 0

TES_Pixel_L0.Copy TP_L0_00142
TP_L0_00142.Position 0 -0.31 -0.465
TP_L0_00142.Mother TES_L0
TP_L0_00142.Visibility 0

TES_Pixel_L0.Copy TP_L0_00143
TP_L0_00143.Position 0 -0.31 -0.31
TP_L0_00143.Mother TES_L0
TP_L0_00143.Visibility 0

TES_Pixel_L0.Copy TP_L0_00144
TP_L0_00144.Position 0 -0.31 -0.155
TP_L0_00144.Mother TES_L0
TP_L0_00144.Visibility 0

TES_Pixel_L0.Copy TP_L0_00145
TP_L0_00145.Position 0 -0.31 0
TP_L0_00145.Mother TES_L0
TP_L0_00145.Visibility 0

TES_Pixel_L0.Copy TP_L0_00146
TP_L0_00146.Position 0 -0.31 0.155
TP_L0_00146.Mother TES_L0
TP_L0_00146.Visibility 0

TES_Pixel_L0.Copy TP_L0_00147
TP_L0_00147.Position 0 -0.31 0.31
TP_L0_00147.Mother TES_L0
TP_L0_00147.Visibility 0

TES_Pixel_L0.Copy TP_L0_00148
TP_L0_00148.Position 0 -0.31 0.465
TP_L0_00148.Mother TES_L0
TP_L0_00148.Visibility 0

TES_Pixel_L0.Copy TP_L0_00149
TP_L0_00149.Position 0 -0.31 0.62
TP_L0_00149.Mother TES_L0
TP_L0_00149.Visibility 0

TES_Pixel_L0.Copy TP_L0_00150
TP_L0_00150.Position 0 -0.31 0.775
TP_L0_00150.Mother TES_L0
TP_L0_00150.Visibility 0

TES_Pixel_L0.Copy TP_L0_00151
TP_L0_00151.Position 0 -0.31 0.93
TP_L0_00151.Mother TES_L0
TP_L0_00151.Visibility 0

TES_Pixel_L0.Copy TP_L0_00152
TP_L0_00152.Position 0 -0.31 1.085
TP_L0_00152.Mother TES_L0
TP_L0_00152.Visibility 0

TES_Pixel_L0.Copy TP_L0_00153
TP_L0_00153.Position 0 -0.31 1.24
TP_L0_00153.Mother TES_L0
TP_L0_00153.Visibility 0

TES_Pixel_L0.Copy TP_L0_00154
TP_L0_00154.Position 0 -0.31 1.395
TP_L0_00154.Mother TES_L0
TP_L0_00154.Visibility 0

TES_Pixel_L0.Copy TP_L0_00155
TP_L0_00155.Position 0 -0.31 1.55
TP_L0_00155.Mother TES_L0
TP_L0_00155.Visibility 0

TES_Pixel_L0.Copy TP_L0_00156
TP_L0_00156.Position 0 -0.155 -1.55
TP_L0_00156.Mother TES_L0
TP_L0_00156.Visibility 0

TES_Pixel_L0.Copy TP_L0_00157
TP_L0_00157.Position 0 -0.155 -1.395
TP_L0_00157.Mother TES_L0
TP_L0_00157.Visibility 0

TES_Pixel_L0.Copy TP_L0_00158
TP_L0_00158.Position 0 -0.155 -1.24
TP_L0_00158.Mother TES_L0
TP_L0_00158.Visibility 0

TES_Pixel_L0.Copy TP_L0_00159
TP_L0_00159.Position 0 -0.155 -1.085
TP_L0_00159.Mother TES_L0
TP_L0_00159.Visibility 0

TES_Pixel_L0.Copy TP_L0_00160
TP_L0_00160.Position 0 -0.155 -0.93
TP_L0_00160.Mother TES_L0
TP_L0_00160.Visibility 0

TES_Pixel_L0.Copy TP_L0_00161
TP_L0_00161.Position 0 -0.155 -0.775
TP_L0_00161.Mother TES_L0
TP_L0_00161.Visibility 0

TES_Pixel_L0.Copy TP_L0_00162
TP_L0_00162.Position 0 -0.155 -0.62
TP_L0_00162.Mother TES_L0
TP_L0_00162.Visibility 0

TES_Pixel_L0.Copy TP_L0_00163
TP_L0_00163.Position 0 -0.155 -0.465
TP_L0_00163.Mother TES_L0
TP_L0_00163.Visibility 0

TES_Pixel_L0.Copy TP_L0_00164
TP_L0_00164.Position 0 -0.155 -0.31
TP_L0_00164.Mother TES_L0
TP_L0_00164.Visibility 0

TES_Pixel_L0.Copy TP_L0_00165
TP_L0_00165.Position 0 -0.155 -0.155
TP_L0_00165.Mother TES_L0
TP_L0_00165.Visibility 0

TES_Pixel_L0.Copy TP_L0_00166
TP_L0_00166.Position 0 -0.155 0
TP_L0_00166.Mother TES_L0
TP_L0_00166.Visibility 0

TES_Pixel_L0.Copy TP_L0_00167
TP_L0_00167.Position 0 -0.155 0.155
TP_L0_00167.Mother TES_L0
TP_L0_00167.Visibility 0

TES_Pixel_L0.Copy TP_L0_00168
TP_L0_00168.Position 0 -0.155 0.31
TP_L0_00168.Mother TES_L0
TP_L0_00168.Visibility 0

TES_Pixel_L0.Copy TP_L0_00169
TP_L0_00169.Position 0 -0.155 0.465
TP_L0_00169.Mother TES_L0
TP_L0_00169.Visibility 0

TES_Pixel_L0.Copy TP_L0_00170
TP_L0_00170.Position 0 -0.155 0.62
TP_L0_00170.Mother TES_L0
TP_L0_00170.Visibility 0

TES_Pixel_L0.Copy TP_L0_00171
TP_L0_00171.Position 0 -0.155 0.775
TP_L0_00171.Mother TES_L0
TP_L0_00171.Visibility 0

TES_Pixel_L0.Copy TP_L0_00172
TP_L0_00172.Position 0 -0.155 0.93
TP_L0_00172.Mother TES_L0
TP_L0_00172.Visibility 0

TES_Pixel_L0.Copy TP_L0_00173
TP_L0_00173.Position 0 -0.155 1.085
TP_L0_00173.Mother TES_L0
TP_L0_00173.Visibility 0

TES_Pixel_L0.Copy TP_L0_00174
TP_L0_00174.Position 0 -0.155 1.24
TP_L0_00174.Mother TES_L0
TP_L0_00174.Visibility 0

TES_Pixel_L0.Copy TP_L0_00175
TP_L0_00175.Position 0 -0.155 1.395
TP_L0_00175.Mother TES_L0
TP_L0_00175.Visibility 0

TES_Pixel_L0.Copy TP_L0_00176
TP_L0_00176.Position 0 -0.155 1.55
TP_L0_00176.Mother TES_L0
TP_L0_00176.Visibility 0

TES_Pixel_L0.Copy TP_L0_00177
TP_L0_00177.Position 0 0 -1.705
TP_L0_00177.Mother TES_L0
TP_L0_00177.Visibility 0

TES_Pixel_L0.Copy TP_L0_00178
TP_L0_00178.Position 0 0 -1.55
TP_L0_00178.Mother TES_L0
TP_L0_00178.Visibility 0

TES_Pixel_L0.Copy TP_L0_00179
TP_L0_00179.Position 0 0 -1.395
TP_L0_00179.Mother TES_L0
TP_L0_00179.Visibility 0

TES_Pixel_L0.Copy TP_L0_00180
TP_L0_00180.Position 0 0 -1.24
TP_L0_00180.Mother TES_L0
TP_L0_00180.Visibility 0

TES_Pixel_L0.Copy TP_L0_00181
TP_L0_00181.Position 0 0 -1.085
TP_L0_00181.Mother TES_L0
TP_L0_00181.Visibility 0

TES_Pixel_L0.Copy TP_L0_00182
TP_L0_00182.Position 0 0 -0.93
TP_L0_00182.Mother TES_L0
TP_L0_00182.Visibility 0

TES_Pixel_L0.Copy TP_L0_00183
TP_L0_00183.Position 0 0 -0.775
TP_L0_00183.Mother TES_L0
TP_L0_00183.Visibility 0

TES_Pixel_L0.Copy TP_L0_00184
TP_L0_00184.Position 0 0 -0.62
TP_L0_00184.Mother TES_L0
TP_L0_00184.Visibility 0

TES_Pixel_L0.Copy TP_L0_00185
TP_L0_00185.Position 0 0 -0.465
TP_L0_00185.Mother TES_L0
TP_L0_00185.Visibility 0

TES_Pixel_L0.Copy TP_L0_00186
TP_L0_00186.Position 0 0 -0.31
TP_L0_00186.Mother TES_L0
TP_L0_00186.Visibility 0

TES_Pixel_L0.Copy TP_L0_00187
TP_L0_00187.Position 0 0 -0.155
TP_L0_00187.Mother TES_L0
TP_L0_00187.Visibility 0

TES_Pixel_L0.Copy TP_L0_00188
TP_L0_00188.Position 0 0 0
TP_L0_00188.Mother TES_L0
TP_L0_00188.Visibility 0

TES_Pixel_L0.Copy TP_L0_00189
TP_L0_00189.Position 0 0 0.155
TP_L0_00189.Mother TES_L0
TP_L0_00189.Visibility 0

TES_Pixel_L0.Copy TP_L0_00190
TP_L0_00190.Position 0 0 0.31
TP_L0_00190.Mother TES_L0
TP_L0_00190.Visibility 0

TES_Pixel_L0.Copy TP_L0_00191
TP_L0_00191.Position 0 0 0.465
TP_L0_00191.Mother TES_L0
TP_L0_00191.Visibility 0

TES_Pixel_L0.Copy TP_L0_00192
TP_L0_00192.Position 0 0 0.62
TP_L0_00192.Mother TES_L0
TP_L0_00192.Visibility 0

TES_Pixel_L0.Copy TP_L0_00193
TP_L0_00193.Position 0 0 0.775
TP_L0_00193.Mother TES_L0
TP_L0_00193.Visibility 0

TES_Pixel_L0.Copy TP_L0_00194
TP_L0_00194.Position 0 0 0.93
TP_L0_00194.Mother TES_L0
TP_L0_00194.Visibility 0

TES_Pixel_L0.Copy TP_L0_00195
TP_L0_00195.Position 0 0 1.085
TP_L0_00195.Mother TES_L0
TP_L0_00195.Visibility 0

TES_Pixel_L0.Copy TP_L0_00196
TP_L0_00196.Position 0 0 1.24
TP_L0_00196.Mother TES_L0
TP_L0_00196.Visibility 0

TES_Pixel_L0.Copy TP_L0_00197
TP_L0_00197.Position 0 0 1.395
TP_L0_00197.Mother TES_L0
TP_L0_00197.Visibility 0

TES_Pixel_L0.Copy TP_L0_00198
TP_L0_00198.Position 0 0 1.55
TP_L0_00198.Mother TES_L0
TP_L0_00198.Visibility 0

TES_Pixel_L0.Copy TP_L0_00199
TP_L0_00199.Position 0 0 1.705
TP_L0_00199.Mother TES_L0
TP_L0_00199.Visibility 0

TES_Pixel_L0.Copy TP_L0_00200
TP_L0_00200.Position 0 0.155 -1.55
TP_L0_00200.Mother TES_L0
TP_L0_00200.Visibility 0

TES_Pixel_L0.Copy TP_L0_00201
TP_L0_00201.Position 0 0.155 -1.395
TP_L0_00201.Mother TES_L0
TP_L0_00201.Visibility 0

TES_Pixel_L0.Copy TP_L0_00202
TP_L0_00202.Position 0 0.155 -1.24
TP_L0_00202.Mother TES_L0
TP_L0_00202.Visibility 0

TES_Pixel_L0.Copy TP_L0_00203
TP_L0_00203.Position 0 0.155 -1.085
TP_L0_00203.Mother TES_L0
TP_L0_00203.Visibility 0

TES_Pixel_L0.Copy TP_L0_00204
TP_L0_00204.Position 0 0.155 -0.93
TP_L0_00204.Mother TES_L0
TP_L0_00204.Visibility 0

TES_Pixel_L0.Copy TP_L0_00205
TP_L0_00205.Position 0 0.155 -0.775
TP_L0_00205.Mother TES_L0
TP_L0_00205.Visibility 0

TES_Pixel_L0.Copy TP_L0_00206
TP_L0_00206.Position 0 0.155 -0.62
TP_L0_00206.Mother TES_L0
TP_L0_00206.Visibility 0

TES_Pixel_L0.Copy TP_L0_00207
TP_L0_00207.Position 0 0.155 -0.465
TP_L0_00207.Mother TES_L0
TP_L0_00207.Visibility 0

TES_Pixel_L0.Copy TP_L0_00208
TP_L0_00208.Position 0 0.155 -0.31
TP_L0_00208.Mother TES_L0
TP_L0_00208.Visibility 0

TES_Pixel_L0.Copy TP_L0_00209
TP_L0_00209.Position 0 0.155 -0.155
TP_L0_00209.Mother TES_L0
TP_L0_00209.Visibility 0

TES_Pixel_L0.Copy TP_L0_00210
TP_L0_00210.Position 0 0.155 0
TP_L0_00210.Mother TES_L0
TP_L0_00210.Visibility 0

TES_Pixel_L0.Copy TP_L0_00211
TP_L0_00211.Position 0 0.155 0.155
TP_L0_00211.Mother TES_L0
TP_L0_00211.Visibility 0

TES_Pixel_L0.Copy TP_L0_00212
TP_L0_00212.Position 0 0.155 0.31
TP_L0_00212.Mother TES_L0
TP_L0_00212.Visibility 0

TES_Pixel_L0.Copy TP_L0_00213
TP_L0_00213.Position 0 0.155 0.465
TP_L0_00213.Mother TES_L0
TP_L0_00213.Visibility 0

TES_Pixel_L0.Copy TP_L0_00214
TP_L0_00214.Position 0 0.155 0.62
TP_L0_00214.Mother TES_L0
TP_L0_00214.Visibility 0

TES_Pixel_L0.Copy TP_L0_00215
TP_L0_00215.Position 0 0.155 0.775
TP_L0_00215.Mother TES_L0
TP_L0_00215.Visibility 0

TES_Pixel_L0.Copy TP_L0_00216
TP_L0_00216.Position 0 0.155 0.93
TP_L0_00216.Mother TES_L0
TP_L0_00216.Visibility 0

TES_Pixel_L0.Copy TP_L0_00217
TP_L0_00217.Position 0 0.155 1.085
TP_L0_00217.Mother TES_L0
TP_L0_00217.Visibility 0

TES_Pixel_L0.Copy TP_L0_00218
TP_L0_00218.Position 0 0.155 1.24
TP_L0_00218.Mother TES_L0
TP_L0_00218.Visibility 0

TES_Pixel_L0.Copy TP_L0_00219
TP_L0_00219.Position 0 0.155 1.395
TP_L0_00219.Mother TES_L0
TP_L0_00219.Visibility 0

TES_Pixel_L0.Copy TP_L0_00220
TP_L0_00220.Position 0 0.155 1.55
TP_L0_00220.Mother TES_L0
TP_L0_00220.Visibility 0

TES_Pixel_L0.Copy TP_L0_00221
TP_L0_00221.Position 0 0.31 -1.55
TP_L0_00221.Mother TES_L0
TP_L0_00221.Visibility 0

TES_Pixel_L0.Copy TP_L0_00222
TP_L0_00222.Position 0 0.31 -1.395
TP_L0_00222.Mother TES_L0
TP_L0_00222.Visibility 0

TES_Pixel_L0.Copy TP_L0_00223
TP_L0_00223.Position 0 0.31 -1.24
TP_L0_00223.Mother TES_L0
TP_L0_00223.Visibility 0

TES_Pixel_L0.Copy TP_L0_00224
TP_L0_00224.Position 0 0.31 -1.085
TP_L0_00224.Mother TES_L0
TP_L0_00224.Visibility 0

TES_Pixel_L0.Copy TP_L0_00225
TP_L0_00225.Position 0 0.31 -0.93
TP_L0_00225.Mother TES_L0
TP_L0_00225.Visibility 0

TES_Pixel_L0.Copy TP_L0_00226
TP_L0_00226.Position 0 0.31 -0.775
TP_L0_00226.Mother TES_L0
TP_L0_00226.Visibility 0

TES_Pixel_L0.Copy TP_L0_00227
TP_L0_00227.Position 0 0.31 -0.62
TP_L0_00227.Mother TES_L0
TP_L0_00227.Visibility 0

TES_Pixel_L0.Copy TP_L0_00228
TP_L0_00228.Position 0 0.31 -0.465
TP_L0_00228.Mother TES_L0
TP_L0_00228.Visibility 0

TES_Pixel_L0.Copy TP_L0_00229
TP_L0_00229.Position 0 0.31 -0.31
TP_L0_00229.Mother TES_L0
TP_L0_00229.Visibility 0

TES_Pixel_L0.Copy TP_L0_00230
TP_L0_00230.Position 0 0.31 -0.155
TP_L0_00230.Mother TES_L0
TP_L0_00230.Visibility 0

TES_Pixel_L0.Copy TP_L0_00231
TP_L0_00231.Position 0 0.31 0
TP_L0_00231.Mother TES_L0
TP_L0_00231.Visibility 0

TES_Pixel_L0.Copy TP_L0_00232
TP_L0_00232.Position 0 0.31 0.155
TP_L0_00232.Mother TES_L0
TP_L0_00232.Visibility 0

TES_Pixel_L0.Copy TP_L0_00233
TP_L0_00233.Position 0 0.31 0.31
TP_L0_00233.Mother TES_L0
TP_L0_00233.Visibility 0

TES_Pixel_L0.Copy TP_L0_00234
TP_L0_00234.Position 0 0.31 0.465
TP_L0_00234.Mother TES_L0
TP_L0_00234.Visibility 0

TES_Pixel_L0.Copy TP_L0_00235
TP_L0_00235.Position 0 0.31 0.62
TP_L0_00235.Mother TES_L0
TP_L0_00235.Visibility 0

TES_Pixel_L0.Copy TP_L0_00236
TP_L0_00236.Position 0 0.31 0.775
TP_L0_00236.Mother TES_L0
TP_L0_00236.Visibility 0

TES_Pixel_L0.Copy TP_L0_00237
TP_L0_00237.Position 0 0.31 0.93
TP_L0_00237.Mother TES_L0
TP_L0_00237.Visibility 0

TES_Pixel_L0.Copy TP_L0_00238
TP_L0_00238.Position 0 0.31 1.085
TP_L0_00238.Mother TES_L0
TP_L0_00238.Visibility 0

TES_Pixel_L0.Copy TP_L0_00239
TP_L0_00239.Position 0 0.31 1.24
TP_L0_00239.Mother TES_L0
TP_L0_00239.Visibility 0

TES_Pixel_L0.Copy TP_L0_00240
TP_L0_00240.Position 0 0.31 1.395
TP_L0_00240.Mother TES_L0
TP_L0_00240.Visibility 0

TES_Pixel_L0.Copy TP_L0_00241
TP_L0_00241.Position 0 0.31 1.55
TP_L0_00241.Mother TES_L0
TP_L0_00241.Visibility 0

TES_Pixel_L0.Copy TP_L0_00242
TP_L0_00242.Position 0 0.465 -1.55
TP_L0_00242.Mother TES_L0
TP_L0_00242.Visibility 0

TES_Pixel_L0.Copy TP_L0_00243
TP_L0_00243.Position 0 0.465 -1.395
TP_L0_00243.Mother TES_L0
TP_L0_00243.Visibility 0

TES_Pixel_L0.Copy TP_L0_00244
TP_L0_00244.Position 0 0.465 -1.24
TP_L0_00244.Mother TES_L0
TP_L0_00244.Visibility 0

TES_Pixel_L0.Copy TP_L0_00245
TP_L0_00245.Position 0 0.465 -1.085
TP_L0_00245.Mother TES_L0
TP_L0_00245.Visibility 0

TES_Pixel_L0.Copy TP_L0_00246
TP_L0_00246.Position 0 0.465 -0.93
TP_L0_00246.Mother TES_L0
TP_L0_00246.Visibility 0

TES_Pixel_L0.Copy TP_L0_00247
TP_L0_00247.Position 0 0.465 -0.775
TP_L0_00247.Mother TES_L0
TP_L0_00247.Visibility 0

TES_Pixel_L0.Copy TP_L0_00248
TP_L0_00248.Position 0 0.465 -0.62
TP_L0_00248.Mother TES_L0
TP_L0_00248.Visibility 0

TES_Pixel_L0.Copy TP_L0_00249
TP_L0_00249.Position 0 0.465 -0.465
TP_L0_00249.Mother TES_L0
TP_L0_00249.Visibility 0

TES_Pixel_L0.Copy TP_L0_00250
TP_L0_00250.Position 0 0.465 -0.31
TP_L0_00250.Mother TES_L0
TP_L0_00250.Visibility 0

TES_Pixel_L0.Copy TP_L0_00251
TP_L0_00251.Position 0 0.465 -0.155
TP_L0_00251.Mother TES_L0
TP_L0_00251.Visibility 0

TES_Pixel_L0.Copy TP_L0_00252
TP_L0_00252.Position 0 0.465 0
TP_L0_00252.Mother TES_L0
TP_L0_00252.Visibility 0

TES_Pixel_L0.Copy TP_L0_00253
TP_L0_00253.Position 0 0.465 0.155
TP_L0_00253.Mother TES_L0
TP_L0_00253.Visibility 0

TES_Pixel_L0.Copy TP_L0_00254
TP_L0_00254.Position 0 0.465 0.31
TP_L0_00254.Mother TES_L0
TP_L0_00254.Visibility 0

TES_Pixel_L0.Copy TP_L0_00255
TP_L0_00255.Position 0 0.465 0.465
TP_L0_00255.Mother TES_L0
TP_L0_00255.Visibility 0

TES_Pixel_L0.Copy TP_L0_00256
TP_L0_00256.Position 0 0.465 0.62
TP_L0_00256.Mother TES_L0
TP_L0_00256.Visibility 0

TES_Pixel_L0.Copy TP_L0_00257
TP_L0_00257.Position 0 0.465 0.775
TP_L0_00257.Mother TES_L0
TP_L0_00257.Visibility 0

TES_Pixel_L0.Copy TP_L0_00258
TP_L0_00258.Position 0 0.465 0.93
TP_L0_00258.Mother TES_L0
TP_L0_00258.Visibility 0

TES_Pixel_L0.Copy TP_L0_00259
TP_L0_00259.Position 0 0.465 1.085
TP_L0_00259.Mother TES_L0
TP_L0_00259.Visibility 0

TES_Pixel_L0.Copy TP_L0_00260
TP_L0_00260.Position 0 0.465 1.24
TP_L0_00260.Mother TES_L0
TP_L0_00260.Visibility 0

TES_Pixel_L0.Copy TP_L0_00261
TP_L0_00261.Position 0 0.465 1.395
TP_L0_00261.Mother TES_L0
TP_L0_00261.Visibility 0

TES_Pixel_L0.Copy TP_L0_00262
TP_L0_00262.Position 0 0.465 1.55
TP_L0_00262.Mother TES_L0
TP_L0_00262.Visibility 0

TES_Pixel_L0.Copy TP_L0_00263
TP_L0_00263.Position 0 0.62 -1.55
TP_L0_00263.Mother TES_L0
TP_L0_00263.Visibility 0

TES_Pixel_L0.Copy TP_L0_00264
TP_L0_00264.Position 0 0.62 -1.395
TP_L0_00264.Mother TES_L0
TP_L0_00264.Visibility 0

TES_Pixel_L0.Copy TP_L0_00265
TP_L0_00265.Position 0 0.62 -1.24
TP_L0_00265.Mother TES_L0
TP_L0_00265.Visibility 0

TES_Pixel_L0.Copy TP_L0_00266
TP_L0_00266.Position 0 0.62 -1.085
TP_L0_00266.Mother TES_L0
TP_L0_00266.Visibility 0

TES_Pixel_L0.Copy TP_L0_00267
TP_L0_00267.Position 0 0.62 -0.93
TP_L0_00267.Mother TES_L0
TP_L0_00267.Visibility 0

TES_Pixel_L0.Copy TP_L0_00268
TP_L0_00268.Position 0 0.62 -0.775
TP_L0_00268.Mother TES_L0
TP_L0_00268.Visibility 0

TES_Pixel_L0.Copy TP_L0_00269
TP_L0_00269.Position 0 0.62 -0.62
TP_L0_00269.Mother TES_L0
TP_L0_00269.Visibility 0

TES_Pixel_L0.Copy TP_L0_00270
TP_L0_00270.Position 0 0.62 -0.465
TP_L0_00270.Mother TES_L0
TP_L0_00270.Visibility 0

TES_Pixel_L0.Copy TP_L0_00271
TP_L0_00271.Position 0 0.62 -0.31
TP_L0_00271.Mother TES_L0
TP_L0_00271.Visibility 0

TES_Pixel_L0.Copy TP_L0_00272
TP_L0_00272.Position 0 0.62 -0.155
TP_L0_00272.Mother TES_L0
TP_L0_00272.Visibility 0

TES_Pixel_L0.Copy TP_L0_00273
TP_L0_00273.Position 0 0.62 0
TP_L0_00273.Mother TES_L0
TP_L0_00273.Visibility 0

TES_Pixel_L0.Copy TP_L0_00274
TP_L0_00274.Position 0 0.62 0.155
TP_L0_00274.Mother TES_L0
TP_L0_00274.Visibility 0

TES_Pixel_L0.Copy TP_L0_00275
TP_L0_00275.Position 0 0.62 0.31
TP_L0_00275.Mother TES_L0
TP_L0_00275.Visibility 0

TES_Pixel_L0.Copy TP_L0_00276
TP_L0_00276.Position 0 0.62 0.465
TP_L0_00276.Mother TES_L0
TP_L0_00276.Visibility 0

TES_Pixel_L0.Copy TP_L0_00277
TP_L0_00277.Position 0 0.62 0.62
TP_L0_00277.Mother TES_L0
TP_L0_00277.Visibility 0

TES_Pixel_L0.Copy TP_L0_00278
TP_L0_00278.Position 0 0.62 0.775
TP_L0_00278.Mother TES_L0
TP_L0_00278.Visibility 0

TES_Pixel_L0.Copy TP_L0_00279
TP_L0_00279.Position 0 0.62 0.93
TP_L0_00279.Mother TES_L0
TP_L0_00279.Visibility 0

TES_Pixel_L0.Copy TP_L0_00280
TP_L0_00280.Position 0 0.62 1.085
TP_L0_00280.Mother TES_L0
TP_L0_00280.Visibility 0

TES_Pixel_L0.Copy TP_L0_00281
TP_L0_00281.Position 0 0.62 1.24
TP_L0_00281.Mother TES_L0
TP_L0_00281.Visibility 0

TES_Pixel_L0.Copy TP_L0_00282
TP_L0_00282.Position 0 0.62 1.395
TP_L0_00282.Mother TES_L0
TP_L0_00282.Visibility 0

TES_Pixel_L0.Copy TP_L0_00283
TP_L0_00283.Position 0 0.62 1.55
TP_L0_00283.Mother TES_L0
TP_L0_00283.Visibility 0

TES_Pixel_L0.Copy TP_L0_00284
TP_L0_00284.Position 0 0.775 -1.395
TP_L0_00284.Mother TES_L0
TP_L0_00284.Visibility 0

TES_Pixel_L0.Copy TP_L0_00285
TP_L0_00285.Position 0 0.775 -1.24
TP_L0_00285.Mother TES_L0
TP_L0_00285.Visibility 0

TES_Pixel_L0.Copy TP_L0_00286
TP_L0_00286.Position 0 0.775 -1.085
TP_L0_00286.Mother TES_L0
TP_L0_00286.Visibility 0

TES_Pixel_L0.Copy TP_L0_00287
TP_L0_00287.Position 0 0.775 -0.93
TP_L0_00287.Mother TES_L0
TP_L0_00287.Visibility 0

TES_Pixel_L0.Copy TP_L0_00288
TP_L0_00288.Position 0 0.775 -0.775
TP_L0_00288.Mother TES_L0
TP_L0_00288.Visibility 0

TES_Pixel_L0.Copy TP_L0_00289
TP_L0_00289.Position 0 0.775 -0.62
TP_L0_00289.Mother TES_L0
TP_L0_00289.Visibility 0

TES_Pixel_L0.Copy TP_L0_00290
TP_L0_00290.Position 0 0.775 -0.465
TP_L0_00290.Mother TES_L0
TP_L0_00290.Visibility 0

TES_Pixel_L0.Copy TP_L0_00291
TP_L0_00291.Position 0 0.775 -0.31
TP_L0_00291.Mother TES_L0
TP_L0_00291.Visibility 0

TES_Pixel_L0.Copy TP_L0_00292
TP_L0_00292.Position 0 0.775 -0.155
TP_L0_00292.Mother TES_L0
TP_L0_00292.Visibility 0

TES_Pixel_L0.Copy TP_L0_00293
TP_L0_00293.Position 0 0.775 0
TP_L0_00293.Mother TES_L0
TP_L0_00293.Visibility 0

TES_Pixel_L0.Copy TP_L0_00294
TP_L0_00294.Position 0 0.775 0.155
TP_L0_00294.Mother TES_L0
TP_L0_00294.Visibility 0

TES_Pixel_L0.Copy TP_L0_00295
TP_L0_00295.Position 0 0.775 0.31
TP_L0_00295.Mother TES_L0
TP_L0_00295.Visibility 0

TES_Pixel_L0.Copy TP_L0_00296
TP_L0_00296.Position 0 0.775 0.465
TP_L0_00296.Mother TES_L0
TP_L0_00296.Visibility 0

TES_Pixel_L0.Copy TP_L0_00297
TP_L0_00297.Position 0 0.775 0.62
TP_L0_00297.Mother TES_L0
TP_L0_00297.Visibility 0

TES_Pixel_L0.Copy TP_L0_00298
TP_L0_00298.Position 0 0.775 0.775
TP_L0_00298.Mother TES_L0
TP_L0_00298.Visibility 0

TES_Pixel_L0.Copy TP_L0_00299
TP_L0_00299.Position 0 0.775 0.93
TP_L0_00299.Mother TES_L0
TP_L0_00299.Visibility 0

TES_Pixel_L0.Copy TP_L0_00300
TP_L0_00300.Position 0 0.775 1.085
TP_L0_00300.Mother TES_L0
TP_L0_00300.Visibility 0

TES_Pixel_L0.Copy TP_L0_00301
TP_L0_00301.Position 0 0.775 1.24
TP_L0_00301.Mother TES_L0
TP_L0_00301.Visibility 0

TES_Pixel_L0.Copy TP_L0_00302
TP_L0_00302.Position 0 0.775 1.395
TP_L0_00302.Mother TES_L0
TP_L0_00302.Visibility 0

TES_Pixel_L0.Copy TP_L0_00303
TP_L0_00303.Position 0 0.93 -1.395
TP_L0_00303.Mother TES_L0
TP_L0_00303.Visibility 0

TES_Pixel_L0.Copy TP_L0_00304
TP_L0_00304.Position 0 0.93 -1.24
TP_L0_00304.Mother TES_L0
TP_L0_00304.Visibility 0

TES_Pixel_L0.Copy TP_L0_00305
TP_L0_00305.Position 0 0.93 -1.085
TP_L0_00305.Mother TES_L0
TP_L0_00305.Visibility 0

TES_Pixel_L0.Copy TP_L0_00306
TP_L0_00306.Position 0 0.93 -0.93
TP_L0_00306.Mother TES_L0
TP_L0_00306.Visibility 0

TES_Pixel_L0.Copy TP_L0_00307
TP_L0_00307.Position 0 0.93 -0.775
TP_L0_00307.Mother TES_L0
TP_L0_00307.Visibility 0

TES_Pixel_L0.Copy TP_L0_00308
TP_L0_00308.Position 0 0.93 -0.62
TP_L0_00308.Mother TES_L0
TP_L0_00308.Visibility 0

TES_Pixel_L0.Copy TP_L0_00309
TP_L0_00309.Position 0 0.93 -0.465
TP_L0_00309.Mother TES_L0
TP_L0_00309.Visibility 0

TES_Pixel_L0.Copy TP_L0_00310
TP_L0_00310.Position 0 0.93 -0.31
TP_L0_00310.Mother TES_L0
TP_L0_00310.Visibility 0

TES_Pixel_L0.Copy TP_L0_00311
TP_L0_00311.Position 0 0.93 -0.155
TP_L0_00311.Mother TES_L0
TP_L0_00311.Visibility 0

TES_Pixel_L0.Copy TP_L0_00312
TP_L0_00312.Position 0 0.93 0
TP_L0_00312.Mother TES_L0
TP_L0_00312.Visibility 0

TES_Pixel_L0.Copy TP_L0_00313
TP_L0_00313.Position 0 0.93 0.155
TP_L0_00313.Mother TES_L0
TP_L0_00313.Visibility 0

TES_Pixel_L0.Copy TP_L0_00314
TP_L0_00314.Position 0 0.93 0.31
TP_L0_00314.Mother TES_L0
TP_L0_00314.Visibility 0

TES_Pixel_L0.Copy TP_L0_00315
TP_L0_00315.Position 0 0.93 0.465
TP_L0_00315.Mother TES_L0
TP_L0_00315.Visibility 0

TES_Pixel_L0.Copy TP_L0_00316
TP_L0_00316.Position 0 0.93 0.62
TP_L0_00316.Mother TES_L0
TP_L0_00316.Visibility 0

TES_Pixel_L0.Copy TP_L0_00317
TP_L0_00317.Position 0 0.93 0.775
TP_L0_00317.Mother TES_L0
TP_L0_00317.Visibility 0

TES_Pixel_L0.Copy TP_L0_00318
TP_L0_00318.Position 0 0.93 0.93
TP_L0_00318.Mother TES_L0
TP_L0_00318.Visibility 0

TES_Pixel_L0.Copy TP_L0_00319
TP_L0_00319.Position 0 0.93 1.085
TP_L0_00319.Mother TES_L0
TP_L0_00319.Visibility 0

TES_Pixel_L0.Copy TP_L0_00320
TP_L0_00320.Position 0 0.93 1.24
TP_L0_00320.Mother TES_L0
TP_L0_00320.Visibility 0

TES_Pixel_L0.Copy TP_L0_00321
TP_L0_00321.Position 0 0.93 1.395
TP_L0_00321.Mother TES_L0
TP_L0_00321.Visibility 0

TES_Pixel_L0.Copy TP_L0_00322
TP_L0_00322.Position 0 1.085 -1.24
TP_L0_00322.Mother TES_L0
TP_L0_00322.Visibility 0

TES_Pixel_L0.Copy TP_L0_00323
TP_L0_00323.Position 0 1.085 -1.085
TP_L0_00323.Mother TES_L0
TP_L0_00323.Visibility 0

TES_Pixel_L0.Copy TP_L0_00324
TP_L0_00324.Position 0 1.085 -0.93
TP_L0_00324.Mother TES_L0
TP_L0_00324.Visibility 0

TES_Pixel_L0.Copy TP_L0_00325
TP_L0_00325.Position 0 1.085 -0.775
TP_L0_00325.Mother TES_L0
TP_L0_00325.Visibility 0

TES_Pixel_L0.Copy TP_L0_00326
TP_L0_00326.Position 0 1.085 -0.62
TP_L0_00326.Mother TES_L0
TP_L0_00326.Visibility 0

TES_Pixel_L0.Copy TP_L0_00327
TP_L0_00327.Position 0 1.085 -0.465
TP_L0_00327.Mother TES_L0
TP_L0_00327.Visibility 0

TES_Pixel_L0.Copy TP_L0_00328
TP_L0_00328.Position 0 1.085 -0.31
TP_L0_00328.Mother TES_L0
TP_L0_00328.Visibility 0

TES_Pixel_L0.Copy TP_L0_00329
TP_L0_00329.Position 0 1.085 -0.155
TP_L0_00329.Mother TES_L0
TP_L0_00329.Visibility 0

TES_Pixel_L0.Copy TP_L0_00330
TP_L0_00330.Position 0 1.085 0
TP_L0_00330.Mother TES_L0
TP_L0_00330.Visibility 0

TES_Pixel_L0.Copy TP_L0_00331
TP_L0_00331.Position 0 1.085 0.155
TP_L0_00331.Mother TES_L0
TP_L0_00331.Visibility 0

TES_Pixel_L0.Copy TP_L0_00332
TP_L0_00332.Position 0 1.085 0.31
TP_L0_00332.Mother TES_L0
TP_L0_00332.Visibility 0

TES_Pixel_L0.Copy TP_L0_00333
TP_L0_00333.Position 0 1.085 0.465
TP_L0_00333.Mother TES_L0
TP_L0_00333.Visibility 0

TES_Pixel_L0.Copy TP_L0_00334
TP_L0_00334.Position 0 1.085 0.62
TP_L0_00334.Mother TES_L0
TP_L0_00334.Visibility 0

TES_Pixel_L0.Copy TP_L0_00335
TP_L0_00335.Position 0 1.085 0.775
TP_L0_00335.Mother TES_L0
TP_L0_00335.Visibility 0

TES_Pixel_L0.Copy TP_L0_00336
TP_L0_00336.Position 0 1.085 0.93
TP_L0_00336.Mother TES_L0
TP_L0_00336.Visibility 0

TES_Pixel_L0.Copy TP_L0_00337
TP_L0_00337.Position 0 1.085 1.085
TP_L0_00337.Mother TES_L0
TP_L0_00337.Visibility 0

TES_Pixel_L0.Copy TP_L0_00338
TP_L0_00338.Position 0 1.085 1.24
TP_L0_00338.Mother TES_L0
TP_L0_00338.Visibility 0

TES_Pixel_L0.Copy TP_L0_00339
TP_L0_00339.Position 0 1.24 -1.085
TP_L0_00339.Mother TES_L0
TP_L0_00339.Visibility 0

TES_Pixel_L0.Copy TP_L0_00340
TP_L0_00340.Position 0 1.24 -0.93
TP_L0_00340.Mother TES_L0
TP_L0_00340.Visibility 0

TES_Pixel_L0.Copy TP_L0_00341
TP_L0_00341.Position 0 1.24 -0.775
TP_L0_00341.Mother TES_L0
TP_L0_00341.Visibility 0

TES_Pixel_L0.Copy TP_L0_00342
TP_L0_00342.Position 0 1.24 -0.62
TP_L0_00342.Mother TES_L0
TP_L0_00342.Visibility 0

TES_Pixel_L0.Copy TP_L0_00343
TP_L0_00343.Position 0 1.24 -0.465
TP_L0_00343.Mother TES_L0
TP_L0_00343.Visibility 0

TES_Pixel_L0.Copy TP_L0_00344
TP_L0_00344.Position 0 1.24 -0.31
TP_L0_00344.Mother TES_L0
TP_L0_00344.Visibility 0

TES_Pixel_L0.Copy TP_L0_00345
TP_L0_00345.Position 0 1.24 -0.155
TP_L0_00345.Mother TES_L0
TP_L0_00345.Visibility 0

TES_Pixel_L0.Copy TP_L0_00346
TP_L0_00346.Position 0 1.24 0
TP_L0_00346.Mother TES_L0
TP_L0_00346.Visibility 0

TES_Pixel_L0.Copy TP_L0_00347
TP_L0_00347.Position 0 1.24 0.155
TP_L0_00347.Mother TES_L0
TP_L0_00347.Visibility 0

TES_Pixel_L0.Copy TP_L0_00348
TP_L0_00348.Position 0 1.24 0.31
TP_L0_00348.Mother TES_L0
TP_L0_00348.Visibility 0

TES_Pixel_L0.Copy TP_L0_00349
TP_L0_00349.Position 0 1.24 0.465
TP_L0_00349.Mother TES_L0
TP_L0_00349.Visibility 0

TES_Pixel_L0.Copy TP_L0_00350
TP_L0_00350.Position 0 1.24 0.62
TP_L0_00350.Mother TES_L0
TP_L0_00350.Visibility 0

TES_Pixel_L0.Copy TP_L0_00351
TP_L0_00351.Position 0 1.24 0.775
TP_L0_00351.Mother TES_L0
TP_L0_00351.Visibility 0

TES_Pixel_L0.Copy TP_L0_00352
TP_L0_00352.Position 0 1.24 0.93
TP_L0_00352.Mother TES_L0
TP_L0_00352.Visibility 0

TES_Pixel_L0.Copy TP_L0_00353
TP_L0_00353.Position 0 1.24 1.085
TP_L0_00353.Mother TES_L0
TP_L0_00353.Visibility 0

TES_Pixel_L0.Copy TP_L0_00354
TP_L0_00354.Position 0 1.395 -0.93
TP_L0_00354.Mother TES_L0
TP_L0_00354.Visibility 0

TES_Pixel_L0.Copy TP_L0_00355
TP_L0_00355.Position 0 1.395 -0.775
TP_L0_00355.Mother TES_L0
TP_L0_00355.Visibility 0

TES_Pixel_L0.Copy TP_L0_00356
TP_L0_00356.Position 0 1.395 -0.62
TP_L0_00356.Mother TES_L0
TP_L0_00356.Visibility 0

TES_Pixel_L0.Copy TP_L0_00357
TP_L0_00357.Position 0 1.395 -0.465
TP_L0_00357.Mother TES_L0
TP_L0_00357.Visibility 0

TES_Pixel_L0.Copy TP_L0_00358
TP_L0_00358.Position 0 1.395 -0.31
TP_L0_00358.Mother TES_L0
TP_L0_00358.Visibility 0

TES_Pixel_L0.Copy TP_L0_00359
TP_L0_00359.Position 0 1.395 -0.155
TP_L0_00359.Mother TES_L0
TP_L0_00359.Visibility 0

TES_Pixel_L0.Copy TP_L0_00360
TP_L0_00360.Position 0 1.395 0
TP_L0_00360.Mother TES_L0
TP_L0_00360.Visibility 0

TES_Pixel_L0.Copy TP_L0_00361
TP_L0_00361.Position 0 1.395 0.155
TP_L0_00361.Mother TES_L0
TP_L0_00361.Visibility 0

TES_Pixel_L0.Copy TP_L0_00362
TP_L0_00362.Position 0 1.395 0.31
TP_L0_00362.Mother TES_L0
TP_L0_00362.Visibility 0

TES_Pixel_L0.Copy TP_L0_00363
TP_L0_00363.Position 0 1.395 0.465
TP_L0_00363.Mother TES_L0
TP_L0_00363.Visibility 0

TES_Pixel_L0.Copy TP_L0_00364
TP_L0_00364.Position 0 1.395 0.62
TP_L0_00364.Mother TES_L0
TP_L0_00364.Visibility 0

TES_Pixel_L0.Copy TP_L0_00365
TP_L0_00365.Position 0 1.395 0.775
TP_L0_00365.Mother TES_L0
TP_L0_00365.Visibility 0

TES_Pixel_L0.Copy TP_L0_00366
TP_L0_00366.Position 0 1.395 0.93
TP_L0_00366.Mother TES_L0
TP_L0_00366.Visibility 0

TES_Pixel_L0.Copy TP_L0_00367
TP_L0_00367.Position 0 1.55 -0.62
TP_L0_00367.Mother TES_L0
TP_L0_00367.Visibility 0

TES_Pixel_L0.Copy TP_L0_00368
TP_L0_00368.Position 0 1.55 -0.465
TP_L0_00368.Mother TES_L0
TP_L0_00368.Visibility 0

TES_Pixel_L0.Copy TP_L0_00369
TP_L0_00369.Position 0 1.55 -0.31
TP_L0_00369.Mother TES_L0
TP_L0_00369.Visibility 0

TES_Pixel_L0.Copy TP_L0_00370
TP_L0_00370.Position 0 1.55 -0.155
TP_L0_00370.Mother TES_L0
TP_L0_00370.Visibility 0

TES_Pixel_L0.Copy TP_L0_00371
TP_L0_00371.Position 0 1.55 0
TP_L0_00371.Mother TES_L0
TP_L0_00371.Visibility 0

TES_Pixel_L0.Copy TP_L0_00372
TP_L0_00372.Position 0 1.55 0.155
TP_L0_00372.Mother TES_L0
TP_L0_00372.Visibility 0

TES_Pixel_L0.Copy TP_L0_00373
TP_L0_00373.Position 0 1.55 0.31
TP_L0_00373.Mother TES_L0
TP_L0_00373.Visibility 0

TES_Pixel_L0.Copy TP_L0_00374
TP_L0_00374.Position 0 1.55 0.465
TP_L0_00374.Mother TES_L0
TP_L0_00374.Visibility 0

TES_Pixel_L0.Copy TP_L0_00375
TP_L0_00375.Position 0 1.55 0.62
TP_L0_00375.Mother TES_L0
TP_L0_00375.Visibility 0

// Volume TES_Pixel_L1; material=Ta
Volume TES_Pixel_L1
TES_Pixel_L1.Material Ta
TES_Pixel_L1.Visibility 1
TES_Pixel_L1.Shape BRIK 0.15 0.075 0.075

// Volume TES_L1; material=Vacuum
Volume TES_L1
TES_L1.Material Vacuum
TES_L1.Visibility 0
TES_L1.Shape BRIK 0.15 1.8 1.8

TES_L1.Position -37.35 0 -2.8
TES_L1.Mother InstrumentFrame

TES_Pixel_L1.Copy TP_L1_00000
TP_L1_00000.Position 0 -1.705 0
TP_L1_00000.Mother TES_L1
TP_L1_00000.Visibility 0

TES_Pixel_L1.Copy TP_L1_00001
TP_L1_00001.Position 0 -1.55 -0.62
TP_L1_00001.Mother TES_L1
TP_L1_00001.Visibility 0

TES_Pixel_L1.Copy TP_L1_00002
TP_L1_00002.Position 0 -1.55 -0.465
TP_L1_00002.Mother TES_L1
TP_L1_00002.Visibility 0

TES_Pixel_L1.Copy TP_L1_00003
TP_L1_00003.Position 0 -1.55 -0.31
TP_L1_00003.Mother TES_L1
TP_L1_00003.Visibility 0

TES_Pixel_L1.Copy TP_L1_00004
TP_L1_00004.Position 0 -1.55 -0.155
TP_L1_00004.Mother TES_L1
TP_L1_00004.Visibility 0

TES_Pixel_L1.Copy TP_L1_00005
TP_L1_00005.Position 0 -1.55 0
TP_L1_00005.Mother TES_L1
TP_L1_00005.Visibility 0

TES_Pixel_L1.Copy TP_L1_00006
TP_L1_00006.Position 0 -1.55 0.155
TP_L1_00006.Mother TES_L1
TP_L1_00006.Visibility 0

TES_Pixel_L1.Copy TP_L1_00007
TP_L1_00007.Position 0 -1.55 0.31
TP_L1_00007.Mother TES_L1
TP_L1_00007.Visibility 0

TES_Pixel_L1.Copy TP_L1_00008
TP_L1_00008.Position 0 -1.55 0.465
TP_L1_00008.Mother TES_L1
TP_L1_00008.Visibility 0

TES_Pixel_L1.Copy TP_L1_00009
TP_L1_00009.Position 0 -1.55 0.62
TP_L1_00009.Mother TES_L1
TP_L1_00009.Visibility 0

TES_Pixel_L1.Copy TP_L1_00010
TP_L1_00010.Position 0 -1.395 -0.93
TP_L1_00010.Mother TES_L1
TP_L1_00010.Visibility 0

TES_Pixel_L1.Copy TP_L1_00011
TP_L1_00011.Position 0 -1.395 -0.775
TP_L1_00011.Mother TES_L1
TP_L1_00011.Visibility 0

TES_Pixel_L1.Copy TP_L1_00012
TP_L1_00012.Position 0 -1.395 -0.62
TP_L1_00012.Mother TES_L1
TP_L1_00012.Visibility 0

TES_Pixel_L1.Copy TP_L1_00013
TP_L1_00013.Position 0 -1.395 -0.465
TP_L1_00013.Mother TES_L1
TP_L1_00013.Visibility 0

TES_Pixel_L1.Copy TP_L1_00014
TP_L1_00014.Position 0 -1.395 -0.31
TP_L1_00014.Mother TES_L1
TP_L1_00014.Visibility 0

TES_Pixel_L1.Copy TP_L1_00015
TP_L1_00015.Position 0 -1.395 -0.155
TP_L1_00015.Mother TES_L1
TP_L1_00015.Visibility 0

TES_Pixel_L1.Copy TP_L1_00016
TP_L1_00016.Position 0 -1.395 0
TP_L1_00016.Mother TES_L1
TP_L1_00016.Visibility 0

TES_Pixel_L1.Copy TP_L1_00017
TP_L1_00017.Position 0 -1.395 0.155
TP_L1_00017.Mother TES_L1
TP_L1_00017.Visibility 0

TES_Pixel_L1.Copy TP_L1_00018
TP_L1_00018.Position 0 -1.395 0.31
TP_L1_00018.Mother TES_L1
TP_L1_00018.Visibility 0

TES_Pixel_L1.Copy TP_L1_00019
TP_L1_00019.Position 0 -1.395 0.465
TP_L1_00019.Mother TES_L1
TP_L1_00019.Visibility 0

TES_Pixel_L1.Copy TP_L1_00020
TP_L1_00020.Position 0 -1.395 0.62
TP_L1_00020.Mother TES_L1
TP_L1_00020.Visibility 0

TES_Pixel_L1.Copy TP_L1_00021
TP_L1_00021.Position 0 -1.395 0.775
TP_L1_00021.Mother TES_L1
TP_L1_00021.Visibility 0

TES_Pixel_L1.Copy TP_L1_00022
TP_L1_00022.Position 0 -1.395 0.93
TP_L1_00022.Mother TES_L1
TP_L1_00022.Visibility 0

TES_Pixel_L1.Copy TP_L1_00023
TP_L1_00023.Position 0 -1.24 -1.085
TP_L1_00023.Mother TES_L1
TP_L1_00023.Visibility 0

TES_Pixel_L1.Copy TP_L1_00024
TP_L1_00024.Position 0 -1.24 -0.93
TP_L1_00024.Mother TES_L1
TP_L1_00024.Visibility 0

TES_Pixel_L1.Copy TP_L1_00025
TP_L1_00025.Position 0 -1.24 -0.775
TP_L1_00025.Mother TES_L1
TP_L1_00025.Visibility 0

TES_Pixel_L1.Copy TP_L1_00026
TP_L1_00026.Position 0 -1.24 -0.62
TP_L1_00026.Mother TES_L1
TP_L1_00026.Visibility 0

TES_Pixel_L1.Copy TP_L1_00027
TP_L1_00027.Position 0 -1.24 -0.465
TP_L1_00027.Mother TES_L1
TP_L1_00027.Visibility 0

TES_Pixel_L1.Copy TP_L1_00028
TP_L1_00028.Position 0 -1.24 -0.31
TP_L1_00028.Mother TES_L1
TP_L1_00028.Visibility 0

TES_Pixel_L1.Copy TP_L1_00029
TP_L1_00029.Position 0 -1.24 -0.155
TP_L1_00029.Mother TES_L1
TP_L1_00029.Visibility 0

TES_Pixel_L1.Copy TP_L1_00030
TP_L1_00030.Position 0 -1.24 0
TP_L1_00030.Mother TES_L1
TP_L1_00030.Visibility 0

TES_Pixel_L1.Copy TP_L1_00031
TP_L1_00031.Position 0 -1.24 0.155
TP_L1_00031.Mother TES_L1
TP_L1_00031.Visibility 0

TES_Pixel_L1.Copy TP_L1_00032
TP_L1_00032.Position 0 -1.24 0.31
TP_L1_00032.Mother TES_L1
TP_L1_00032.Visibility 0

TES_Pixel_L1.Copy TP_L1_00033
TP_L1_00033.Position 0 -1.24 0.465
TP_L1_00033.Mother TES_L1
TP_L1_00033.Visibility 0

TES_Pixel_L1.Copy TP_L1_00034
TP_L1_00034.Position 0 -1.24 0.62
TP_L1_00034.Mother TES_L1
TP_L1_00034.Visibility 0

TES_Pixel_L1.Copy TP_L1_00035
TP_L1_00035.Position 0 -1.24 0.775
TP_L1_00035.Mother TES_L1
TP_L1_00035.Visibility 0

TES_Pixel_L1.Copy TP_L1_00036
TP_L1_00036.Position 0 -1.24 0.93
TP_L1_00036.Mother TES_L1
TP_L1_00036.Visibility 0

TES_Pixel_L1.Copy TP_L1_00037
TP_L1_00037.Position 0 -1.24 1.085
TP_L1_00037.Mother TES_L1
TP_L1_00037.Visibility 0

TES_Pixel_L1.Copy TP_L1_00038
TP_L1_00038.Position 0 -1.085 -1.24
TP_L1_00038.Mother TES_L1
TP_L1_00038.Visibility 0

TES_Pixel_L1.Copy TP_L1_00039
TP_L1_00039.Position 0 -1.085 -1.085
TP_L1_00039.Mother TES_L1
TP_L1_00039.Visibility 0

TES_Pixel_L1.Copy TP_L1_00040
TP_L1_00040.Position 0 -1.085 -0.93
TP_L1_00040.Mother TES_L1
TP_L1_00040.Visibility 0

TES_Pixel_L1.Copy TP_L1_00041
TP_L1_00041.Position 0 -1.085 -0.775
TP_L1_00041.Mother TES_L1
TP_L1_00041.Visibility 0

TES_Pixel_L1.Copy TP_L1_00042
TP_L1_00042.Position 0 -1.085 -0.62
TP_L1_00042.Mother TES_L1
TP_L1_00042.Visibility 0

TES_Pixel_L1.Copy TP_L1_00043
TP_L1_00043.Position 0 -1.085 -0.465
TP_L1_00043.Mother TES_L1
TP_L1_00043.Visibility 0

TES_Pixel_L1.Copy TP_L1_00044
TP_L1_00044.Position 0 -1.085 -0.31
TP_L1_00044.Mother TES_L1
TP_L1_00044.Visibility 0

TES_Pixel_L1.Copy TP_L1_00045
TP_L1_00045.Position 0 -1.085 -0.155
TP_L1_00045.Mother TES_L1
TP_L1_00045.Visibility 0

TES_Pixel_L1.Copy TP_L1_00046
TP_L1_00046.Position 0 -1.085 0
TP_L1_00046.Mother TES_L1
TP_L1_00046.Visibility 0

TES_Pixel_L1.Copy TP_L1_00047
TP_L1_00047.Position 0 -1.085 0.155
TP_L1_00047.Mother TES_L1
TP_L1_00047.Visibility 0

TES_Pixel_L1.Copy TP_L1_00048
TP_L1_00048.Position 0 -1.085 0.31
TP_L1_00048.Mother TES_L1
TP_L1_00048.Visibility 0

TES_Pixel_L1.Copy TP_L1_00049
TP_L1_00049.Position 0 -1.085 0.465
TP_L1_00049.Mother TES_L1
TP_L1_00049.Visibility 0

TES_Pixel_L1.Copy TP_L1_00050
TP_L1_00050.Position 0 -1.085 0.62
TP_L1_00050.Mother TES_L1
TP_L1_00050.Visibility 0

TES_Pixel_L1.Copy TP_L1_00051
TP_L1_00051.Position 0 -1.085 0.775
TP_L1_00051.Mother TES_L1
TP_L1_00051.Visibility 0

TES_Pixel_L1.Copy TP_L1_00052
TP_L1_00052.Position 0 -1.085 0.93
TP_L1_00052.Mother TES_L1
TP_L1_00052.Visibility 0

TES_Pixel_L1.Copy TP_L1_00053
TP_L1_00053.Position 0 -1.085 1.085
TP_L1_00053.Mother TES_L1
TP_L1_00053.Visibility 0

TES_Pixel_L1.Copy TP_L1_00054
TP_L1_00054.Position 0 -1.085 1.24
TP_L1_00054.Mother TES_L1
TP_L1_00054.Visibility 0

TES_Pixel_L1.Copy TP_L1_00055
TP_L1_00055.Position 0 -0.93 -1.395
TP_L1_00055.Mother TES_L1
TP_L1_00055.Visibility 0

TES_Pixel_L1.Copy TP_L1_00056
TP_L1_00056.Position 0 -0.93 -1.24
TP_L1_00056.Mother TES_L1
TP_L1_00056.Visibility 0

TES_Pixel_L1.Copy TP_L1_00057
TP_L1_00057.Position 0 -0.93 -1.085
TP_L1_00057.Mother TES_L1
TP_L1_00057.Visibility 0

TES_Pixel_L1.Copy TP_L1_00058
TP_L1_00058.Position 0 -0.93 -0.93
TP_L1_00058.Mother TES_L1
TP_L1_00058.Visibility 0

TES_Pixel_L1.Copy TP_L1_00059
TP_L1_00059.Position 0 -0.93 -0.775
TP_L1_00059.Mother TES_L1
TP_L1_00059.Visibility 0

TES_Pixel_L1.Copy TP_L1_00060
TP_L1_00060.Position 0 -0.93 -0.62
TP_L1_00060.Mother TES_L1
TP_L1_00060.Visibility 0

TES_Pixel_L1.Copy TP_L1_00061
TP_L1_00061.Position 0 -0.93 -0.465
TP_L1_00061.Mother TES_L1
TP_L1_00061.Visibility 0

TES_Pixel_L1.Copy TP_L1_00062
TP_L1_00062.Position 0 -0.93 -0.31
TP_L1_00062.Mother TES_L1
TP_L1_00062.Visibility 0

TES_Pixel_L1.Copy TP_L1_00063
TP_L1_00063.Position 0 -0.93 -0.155
TP_L1_00063.Mother TES_L1
TP_L1_00063.Visibility 0

TES_Pixel_L1.Copy TP_L1_00064
TP_L1_00064.Position 0 -0.93 0
TP_L1_00064.Mother TES_L1
TP_L1_00064.Visibility 0

TES_Pixel_L1.Copy TP_L1_00065
TP_L1_00065.Position 0 -0.93 0.155
TP_L1_00065.Mother TES_L1
TP_L1_00065.Visibility 0

TES_Pixel_L1.Copy TP_L1_00066
TP_L1_00066.Position 0 -0.93 0.31
TP_L1_00066.Mother TES_L1
TP_L1_00066.Visibility 0

TES_Pixel_L1.Copy TP_L1_00067
TP_L1_00067.Position 0 -0.93 0.465
TP_L1_00067.Mother TES_L1
TP_L1_00067.Visibility 0

TES_Pixel_L1.Copy TP_L1_00068
TP_L1_00068.Position 0 -0.93 0.62
TP_L1_00068.Mother TES_L1
TP_L1_00068.Visibility 0

TES_Pixel_L1.Copy TP_L1_00069
TP_L1_00069.Position 0 -0.93 0.775
TP_L1_00069.Mother TES_L1
TP_L1_00069.Visibility 0

TES_Pixel_L1.Copy TP_L1_00070
TP_L1_00070.Position 0 -0.93 0.93
TP_L1_00070.Mother TES_L1
TP_L1_00070.Visibility 0

TES_Pixel_L1.Copy TP_L1_00071
TP_L1_00071.Position 0 -0.93 1.085
TP_L1_00071.Mother TES_L1
TP_L1_00071.Visibility 0

TES_Pixel_L1.Copy TP_L1_00072
TP_L1_00072.Position 0 -0.93 1.24
TP_L1_00072.Mother TES_L1
TP_L1_00072.Visibility 0

TES_Pixel_L1.Copy TP_L1_00073
TP_L1_00073.Position 0 -0.93 1.395
TP_L1_00073.Mother TES_L1
TP_L1_00073.Visibility 0

TES_Pixel_L1.Copy TP_L1_00074
TP_L1_00074.Position 0 -0.775 -1.395
TP_L1_00074.Mother TES_L1
TP_L1_00074.Visibility 0

TES_Pixel_L1.Copy TP_L1_00075
TP_L1_00075.Position 0 -0.775 -1.24
TP_L1_00075.Mother TES_L1
TP_L1_00075.Visibility 0

TES_Pixel_L1.Copy TP_L1_00076
TP_L1_00076.Position 0 -0.775 -1.085
TP_L1_00076.Mother TES_L1
TP_L1_00076.Visibility 0

TES_Pixel_L1.Copy TP_L1_00077
TP_L1_00077.Position 0 -0.775 -0.93
TP_L1_00077.Mother TES_L1
TP_L1_00077.Visibility 0

TES_Pixel_L1.Copy TP_L1_00078
TP_L1_00078.Position 0 -0.775 -0.775
TP_L1_00078.Mother TES_L1
TP_L1_00078.Visibility 0

TES_Pixel_L1.Copy TP_L1_00079
TP_L1_00079.Position 0 -0.775 -0.62
TP_L1_00079.Mother TES_L1
TP_L1_00079.Visibility 0

TES_Pixel_L1.Copy TP_L1_00080
TP_L1_00080.Position 0 -0.775 -0.465
TP_L1_00080.Mother TES_L1
TP_L1_00080.Visibility 0

TES_Pixel_L1.Copy TP_L1_00081
TP_L1_00081.Position 0 -0.775 -0.31
TP_L1_00081.Mother TES_L1
TP_L1_00081.Visibility 0

TES_Pixel_L1.Copy TP_L1_00082
TP_L1_00082.Position 0 -0.775 -0.155
TP_L1_00082.Mother TES_L1
TP_L1_00082.Visibility 0

TES_Pixel_L1.Copy TP_L1_00083
TP_L1_00083.Position 0 -0.775 0
TP_L1_00083.Mother TES_L1
TP_L1_00083.Visibility 0

TES_Pixel_L1.Copy TP_L1_00084
TP_L1_00084.Position 0 -0.775 0.155
TP_L1_00084.Mother TES_L1
TP_L1_00084.Visibility 0

TES_Pixel_L1.Copy TP_L1_00085
TP_L1_00085.Position 0 -0.775 0.31
TP_L1_00085.Mother TES_L1
TP_L1_00085.Visibility 0

TES_Pixel_L1.Copy TP_L1_00086
TP_L1_00086.Position 0 -0.775 0.465
TP_L1_00086.Mother TES_L1
TP_L1_00086.Visibility 0

TES_Pixel_L1.Copy TP_L1_00087
TP_L1_00087.Position 0 -0.775 0.62
TP_L1_00087.Mother TES_L1
TP_L1_00087.Visibility 0

TES_Pixel_L1.Copy TP_L1_00088
TP_L1_00088.Position 0 -0.775 0.775
TP_L1_00088.Mother TES_L1
TP_L1_00088.Visibility 0

TES_Pixel_L1.Copy TP_L1_00089
TP_L1_00089.Position 0 -0.775 0.93
TP_L1_00089.Mother TES_L1
TP_L1_00089.Visibility 0

TES_Pixel_L1.Copy TP_L1_00090
TP_L1_00090.Position 0 -0.775 1.085
TP_L1_00090.Mother TES_L1
TP_L1_00090.Visibility 0

TES_Pixel_L1.Copy TP_L1_00091
TP_L1_00091.Position 0 -0.775 1.24
TP_L1_00091.Mother TES_L1
TP_L1_00091.Visibility 0

TES_Pixel_L1.Copy TP_L1_00092
TP_L1_00092.Position 0 -0.775 1.395
TP_L1_00092.Mother TES_L1
TP_L1_00092.Visibility 0

TES_Pixel_L1.Copy TP_L1_00093
TP_L1_00093.Position 0 -0.62 -1.55
TP_L1_00093.Mother TES_L1
TP_L1_00093.Visibility 0

TES_Pixel_L1.Copy TP_L1_00094
TP_L1_00094.Position 0 -0.62 -1.395
TP_L1_00094.Mother TES_L1
TP_L1_00094.Visibility 0

TES_Pixel_L1.Copy TP_L1_00095
TP_L1_00095.Position 0 -0.62 -1.24
TP_L1_00095.Mother TES_L1
TP_L1_00095.Visibility 0

TES_Pixel_L1.Copy TP_L1_00096
TP_L1_00096.Position 0 -0.62 -1.085
TP_L1_00096.Mother TES_L1
TP_L1_00096.Visibility 0

TES_Pixel_L1.Copy TP_L1_00097
TP_L1_00097.Position 0 -0.62 -0.93
TP_L1_00097.Mother TES_L1
TP_L1_00097.Visibility 0

TES_Pixel_L1.Copy TP_L1_00098
TP_L1_00098.Position 0 -0.62 -0.775
TP_L1_00098.Mother TES_L1
TP_L1_00098.Visibility 0

TES_Pixel_L1.Copy TP_L1_00099
TP_L1_00099.Position 0 -0.62 -0.62
TP_L1_00099.Mother TES_L1
TP_L1_00099.Visibility 0

TES_Pixel_L1.Copy TP_L1_00100
TP_L1_00100.Position 0 -0.62 -0.465
TP_L1_00100.Mother TES_L1
TP_L1_00100.Visibility 0

TES_Pixel_L1.Copy TP_L1_00101
TP_L1_00101.Position 0 -0.62 -0.31
TP_L1_00101.Mother TES_L1
TP_L1_00101.Visibility 0

TES_Pixel_L1.Copy TP_L1_00102
TP_L1_00102.Position 0 -0.62 -0.155
TP_L1_00102.Mother TES_L1
TP_L1_00102.Visibility 0

TES_Pixel_L1.Copy TP_L1_00103
TP_L1_00103.Position 0 -0.62 0
TP_L1_00103.Mother TES_L1
TP_L1_00103.Visibility 0

TES_Pixel_L1.Copy TP_L1_00104
TP_L1_00104.Position 0 -0.62 0.155
TP_L1_00104.Mother TES_L1
TP_L1_00104.Visibility 0

TES_Pixel_L1.Copy TP_L1_00105
TP_L1_00105.Position 0 -0.62 0.31
TP_L1_00105.Mother TES_L1
TP_L1_00105.Visibility 0

TES_Pixel_L1.Copy TP_L1_00106
TP_L1_00106.Position 0 -0.62 0.465
TP_L1_00106.Mother TES_L1
TP_L1_00106.Visibility 0

TES_Pixel_L1.Copy TP_L1_00107
TP_L1_00107.Position 0 -0.62 0.62
TP_L1_00107.Mother TES_L1
TP_L1_00107.Visibility 0

TES_Pixel_L1.Copy TP_L1_00108
TP_L1_00108.Position 0 -0.62 0.775
TP_L1_00108.Mother TES_L1
TP_L1_00108.Visibility 0

TES_Pixel_L1.Copy TP_L1_00109
TP_L1_00109.Position 0 -0.62 0.93
TP_L1_00109.Mother TES_L1
TP_L1_00109.Visibility 0

TES_Pixel_L1.Copy TP_L1_00110
TP_L1_00110.Position 0 -0.62 1.085
TP_L1_00110.Mother TES_L1
TP_L1_00110.Visibility 0

TES_Pixel_L1.Copy TP_L1_00111
TP_L1_00111.Position 0 -0.62 1.24
TP_L1_00111.Mother TES_L1
TP_L1_00111.Visibility 0

TES_Pixel_L1.Copy TP_L1_00112
TP_L1_00112.Position 0 -0.62 1.395
TP_L1_00112.Mother TES_L1
TP_L1_00112.Visibility 0

TES_Pixel_L1.Copy TP_L1_00113
TP_L1_00113.Position 0 -0.62 1.55
TP_L1_00113.Mother TES_L1
TP_L1_00113.Visibility 0

TES_Pixel_L1.Copy TP_L1_00114
TP_L1_00114.Position 0 -0.465 -1.55
TP_L1_00114.Mother TES_L1
TP_L1_00114.Visibility 0

TES_Pixel_L1.Copy TP_L1_00115
TP_L1_00115.Position 0 -0.465 -1.395
TP_L1_00115.Mother TES_L1
TP_L1_00115.Visibility 0

TES_Pixel_L1.Copy TP_L1_00116
TP_L1_00116.Position 0 -0.465 -1.24
TP_L1_00116.Mother TES_L1
TP_L1_00116.Visibility 0

TES_Pixel_L1.Copy TP_L1_00117
TP_L1_00117.Position 0 -0.465 -1.085
TP_L1_00117.Mother TES_L1
TP_L1_00117.Visibility 0

TES_Pixel_L1.Copy TP_L1_00118
TP_L1_00118.Position 0 -0.465 -0.93
TP_L1_00118.Mother TES_L1
TP_L1_00118.Visibility 0

TES_Pixel_L1.Copy TP_L1_00119
TP_L1_00119.Position 0 -0.465 -0.775
TP_L1_00119.Mother TES_L1
TP_L1_00119.Visibility 0

TES_Pixel_L1.Copy TP_L1_00120
TP_L1_00120.Position 0 -0.465 -0.62
TP_L1_00120.Mother TES_L1
TP_L1_00120.Visibility 0

TES_Pixel_L1.Copy TP_L1_00121
TP_L1_00121.Position 0 -0.465 -0.465
TP_L1_00121.Mother TES_L1
TP_L1_00121.Visibility 0

TES_Pixel_L1.Copy TP_L1_00122
TP_L1_00122.Position 0 -0.465 -0.31
TP_L1_00122.Mother TES_L1
TP_L1_00122.Visibility 0

TES_Pixel_L1.Copy TP_L1_00123
TP_L1_00123.Position 0 -0.465 -0.155
TP_L1_00123.Mother TES_L1
TP_L1_00123.Visibility 0

TES_Pixel_L1.Copy TP_L1_00124
TP_L1_00124.Position 0 -0.465 0
TP_L1_00124.Mother TES_L1
TP_L1_00124.Visibility 0

TES_Pixel_L1.Copy TP_L1_00125
TP_L1_00125.Position 0 -0.465 0.155
TP_L1_00125.Mother TES_L1
TP_L1_00125.Visibility 0

TES_Pixel_L1.Copy TP_L1_00126
TP_L1_00126.Position 0 -0.465 0.31
TP_L1_00126.Mother TES_L1
TP_L1_00126.Visibility 0

TES_Pixel_L1.Copy TP_L1_00127
TP_L1_00127.Position 0 -0.465 0.465
TP_L1_00127.Mother TES_L1
TP_L1_00127.Visibility 0

TES_Pixel_L1.Copy TP_L1_00128
TP_L1_00128.Position 0 -0.465 0.62
TP_L1_00128.Mother TES_L1
TP_L1_00128.Visibility 0

TES_Pixel_L1.Copy TP_L1_00129
TP_L1_00129.Position 0 -0.465 0.775
TP_L1_00129.Mother TES_L1
TP_L1_00129.Visibility 0

TES_Pixel_L1.Copy TP_L1_00130
TP_L1_00130.Position 0 -0.465 0.93
TP_L1_00130.Mother TES_L1
TP_L1_00130.Visibility 0

TES_Pixel_L1.Copy TP_L1_00131
TP_L1_00131.Position 0 -0.465 1.085
TP_L1_00131.Mother TES_L1
TP_L1_00131.Visibility 0

TES_Pixel_L1.Copy TP_L1_00132
TP_L1_00132.Position 0 -0.465 1.24
TP_L1_00132.Mother TES_L1
TP_L1_00132.Visibility 0

TES_Pixel_L1.Copy TP_L1_00133
TP_L1_00133.Position 0 -0.465 1.395
TP_L1_00133.Mother TES_L1
TP_L1_00133.Visibility 0

TES_Pixel_L1.Copy TP_L1_00134
TP_L1_00134.Position 0 -0.465 1.55
TP_L1_00134.Mother TES_L1
TP_L1_00134.Visibility 0

TES_Pixel_L1.Copy TP_L1_00135
TP_L1_00135.Position 0 -0.31 -1.55
TP_L1_00135.Mother TES_L1
TP_L1_00135.Visibility 0

TES_Pixel_L1.Copy TP_L1_00136
TP_L1_00136.Position 0 -0.31 -1.395
TP_L1_00136.Mother TES_L1
TP_L1_00136.Visibility 0

TES_Pixel_L1.Copy TP_L1_00137
TP_L1_00137.Position 0 -0.31 -1.24
TP_L1_00137.Mother TES_L1
TP_L1_00137.Visibility 0

TES_Pixel_L1.Copy TP_L1_00138
TP_L1_00138.Position 0 -0.31 -1.085
TP_L1_00138.Mother TES_L1
TP_L1_00138.Visibility 0

TES_Pixel_L1.Copy TP_L1_00139
TP_L1_00139.Position 0 -0.31 -0.93
TP_L1_00139.Mother TES_L1
TP_L1_00139.Visibility 0

TES_Pixel_L1.Copy TP_L1_00140
TP_L1_00140.Position 0 -0.31 -0.775
TP_L1_00140.Mother TES_L1
TP_L1_00140.Visibility 0

TES_Pixel_L1.Copy TP_L1_00141
TP_L1_00141.Position 0 -0.31 -0.62
TP_L1_00141.Mother TES_L1
TP_L1_00141.Visibility 0

TES_Pixel_L1.Copy TP_L1_00142
TP_L1_00142.Position 0 -0.31 -0.465
TP_L1_00142.Mother TES_L1
TP_L1_00142.Visibility 0

TES_Pixel_L1.Copy TP_L1_00143
TP_L1_00143.Position 0 -0.31 -0.31
TP_L1_00143.Mother TES_L1
TP_L1_00143.Visibility 0

TES_Pixel_L1.Copy TP_L1_00144
TP_L1_00144.Position 0 -0.31 -0.155
TP_L1_00144.Mother TES_L1
TP_L1_00144.Visibility 0

TES_Pixel_L1.Copy TP_L1_00145
TP_L1_00145.Position 0 -0.31 0
TP_L1_00145.Mother TES_L1
TP_L1_00145.Visibility 0

TES_Pixel_L1.Copy TP_L1_00146
TP_L1_00146.Position 0 -0.31 0.155
TP_L1_00146.Mother TES_L1
TP_L1_00146.Visibility 0

TES_Pixel_L1.Copy TP_L1_00147
TP_L1_00147.Position 0 -0.31 0.31
TP_L1_00147.Mother TES_L1
TP_L1_00147.Visibility 0

TES_Pixel_L1.Copy TP_L1_00148
TP_L1_00148.Position 0 -0.31 0.465
TP_L1_00148.Mother TES_L1
TP_L1_00148.Visibility 0

TES_Pixel_L1.Copy TP_L1_00149
TP_L1_00149.Position 0 -0.31 0.62
TP_L1_00149.Mother TES_L1
TP_L1_00149.Visibility 0

TES_Pixel_L1.Copy TP_L1_00150
TP_L1_00150.Position 0 -0.31 0.775
TP_L1_00150.Mother TES_L1
TP_L1_00150.Visibility 0

TES_Pixel_L1.Copy TP_L1_00151
TP_L1_00151.Position 0 -0.31 0.93
TP_L1_00151.Mother TES_L1
TP_L1_00151.Visibility 0

TES_Pixel_L1.Copy TP_L1_00152
TP_L1_00152.Position 0 -0.31 1.085
TP_L1_00152.Mother TES_L1
TP_L1_00152.Visibility 0

TES_Pixel_L1.Copy TP_L1_00153
TP_L1_00153.Position 0 -0.31 1.24
TP_L1_00153.Mother TES_L1
TP_L1_00153.Visibility 0

TES_Pixel_L1.Copy TP_L1_00154
TP_L1_00154.Position 0 -0.31 1.395
TP_L1_00154.Mother TES_L1
TP_L1_00154.Visibility 0

TES_Pixel_L1.Copy TP_L1_00155
TP_L1_00155.Position 0 -0.31 1.55
TP_L1_00155.Mother TES_L1
TP_L1_00155.Visibility 0

TES_Pixel_L1.Copy TP_L1_00156
TP_L1_00156.Position 0 -0.155 -1.55
TP_L1_00156.Mother TES_L1
TP_L1_00156.Visibility 0

TES_Pixel_L1.Copy TP_L1_00157
TP_L1_00157.Position 0 -0.155 -1.395
TP_L1_00157.Mother TES_L1
TP_L1_00157.Visibility 0

TES_Pixel_L1.Copy TP_L1_00158
TP_L1_00158.Position 0 -0.155 -1.24
TP_L1_00158.Mother TES_L1
TP_L1_00158.Visibility 0

TES_Pixel_L1.Copy TP_L1_00159
TP_L1_00159.Position 0 -0.155 -1.085
TP_L1_00159.Mother TES_L1
TP_L1_00159.Visibility 0

TES_Pixel_L1.Copy TP_L1_00160
TP_L1_00160.Position 0 -0.155 -0.93
TP_L1_00160.Mother TES_L1
TP_L1_00160.Visibility 0

TES_Pixel_L1.Copy TP_L1_00161
TP_L1_00161.Position 0 -0.155 -0.775
TP_L1_00161.Mother TES_L1
TP_L1_00161.Visibility 0

TES_Pixel_L1.Copy TP_L1_00162
TP_L1_00162.Position 0 -0.155 -0.62
TP_L1_00162.Mother TES_L1
TP_L1_00162.Visibility 0

TES_Pixel_L1.Copy TP_L1_00163
TP_L1_00163.Position 0 -0.155 -0.465
TP_L1_00163.Mother TES_L1
TP_L1_00163.Visibility 0

TES_Pixel_L1.Copy TP_L1_00164
TP_L1_00164.Position 0 -0.155 -0.31
TP_L1_00164.Mother TES_L1
TP_L1_00164.Visibility 0

TES_Pixel_L1.Copy TP_L1_00165
TP_L1_00165.Position 0 -0.155 -0.155
TP_L1_00165.Mother TES_L1
TP_L1_00165.Visibility 0

TES_Pixel_L1.Copy TP_L1_00166
TP_L1_00166.Position 0 -0.155 0
TP_L1_00166.Mother TES_L1
TP_L1_00166.Visibility 0

TES_Pixel_L1.Copy TP_L1_00167
TP_L1_00167.Position 0 -0.155 0.155
TP_L1_00167.Mother TES_L1
TP_L1_00167.Visibility 0

TES_Pixel_L1.Copy TP_L1_00168
TP_L1_00168.Position 0 -0.155 0.31
TP_L1_00168.Mother TES_L1
TP_L1_00168.Visibility 0

TES_Pixel_L1.Copy TP_L1_00169
TP_L1_00169.Position 0 -0.155 0.465
TP_L1_00169.Mother TES_L1
TP_L1_00169.Visibility 0

TES_Pixel_L1.Copy TP_L1_00170
TP_L1_00170.Position 0 -0.155 0.62
TP_L1_00170.Mother TES_L1
TP_L1_00170.Visibility 0

TES_Pixel_L1.Copy TP_L1_00171
TP_L1_00171.Position 0 -0.155 0.775
TP_L1_00171.Mother TES_L1
TP_L1_00171.Visibility 0

TES_Pixel_L1.Copy TP_L1_00172
TP_L1_00172.Position 0 -0.155 0.93
TP_L1_00172.Mother TES_L1
TP_L1_00172.Visibility 0

TES_Pixel_L1.Copy TP_L1_00173
TP_L1_00173.Position 0 -0.155 1.085
TP_L1_00173.Mother TES_L1
TP_L1_00173.Visibility 0

TES_Pixel_L1.Copy TP_L1_00174
TP_L1_00174.Position 0 -0.155 1.24
TP_L1_00174.Mother TES_L1
TP_L1_00174.Visibility 0

TES_Pixel_L1.Copy TP_L1_00175
TP_L1_00175.Position 0 -0.155 1.395
TP_L1_00175.Mother TES_L1
TP_L1_00175.Visibility 0

TES_Pixel_L1.Copy TP_L1_00176
TP_L1_00176.Position 0 -0.155 1.55
TP_L1_00176.Mother TES_L1
TP_L1_00176.Visibility 0

TES_Pixel_L1.Copy TP_L1_00177
TP_L1_00177.Position 0 0 -1.705
TP_L1_00177.Mother TES_L1
TP_L1_00177.Visibility 0

TES_Pixel_L1.Copy TP_L1_00178
TP_L1_00178.Position 0 0 -1.55
TP_L1_00178.Mother TES_L1
TP_L1_00178.Visibility 0

TES_Pixel_L1.Copy TP_L1_00179
TP_L1_00179.Position 0 0 -1.395
TP_L1_00179.Mother TES_L1
TP_L1_00179.Visibility 0

TES_Pixel_L1.Copy TP_L1_00180
TP_L1_00180.Position 0 0 -1.24
TP_L1_00180.Mother TES_L1
TP_L1_00180.Visibility 0

TES_Pixel_L1.Copy TP_L1_00181
TP_L1_00181.Position 0 0 -1.085
TP_L1_00181.Mother TES_L1
TP_L1_00181.Visibility 0

TES_Pixel_L1.Copy TP_L1_00182
TP_L1_00182.Position 0 0 -0.93
TP_L1_00182.Mother TES_L1
TP_L1_00182.Visibility 0

TES_Pixel_L1.Copy TP_L1_00183
TP_L1_00183.Position 0 0 -0.775
TP_L1_00183.Mother TES_L1
TP_L1_00183.Visibility 0

TES_Pixel_L1.Copy TP_L1_00184
TP_L1_00184.Position 0 0 -0.62
TP_L1_00184.Mother TES_L1
TP_L1_00184.Visibility 0

TES_Pixel_L1.Copy TP_L1_00185
TP_L1_00185.Position 0 0 -0.465
TP_L1_00185.Mother TES_L1
TP_L1_00185.Visibility 0

TES_Pixel_L1.Copy TP_L1_00186
TP_L1_00186.Position 0 0 -0.31
TP_L1_00186.Mother TES_L1
TP_L1_00186.Visibility 0

TES_Pixel_L1.Copy TP_L1_00187
TP_L1_00187.Position 0 0 -0.155
TP_L1_00187.Mother TES_L1
TP_L1_00187.Visibility 0

TES_Pixel_L1.Copy TP_L1_00188
TP_L1_00188.Position 0 0 0
TP_L1_00188.Mother TES_L1
TP_L1_00188.Visibility 0

TES_Pixel_L1.Copy TP_L1_00189
TP_L1_00189.Position 0 0 0.155
TP_L1_00189.Mother TES_L1
TP_L1_00189.Visibility 0

TES_Pixel_L1.Copy TP_L1_00190
TP_L1_00190.Position 0 0 0.31
TP_L1_00190.Mother TES_L1
TP_L1_00190.Visibility 0

TES_Pixel_L1.Copy TP_L1_00191
TP_L1_00191.Position 0 0 0.465
TP_L1_00191.Mother TES_L1
TP_L1_00191.Visibility 0

TES_Pixel_L1.Copy TP_L1_00192
TP_L1_00192.Position 0 0 0.62
TP_L1_00192.Mother TES_L1
TP_L1_00192.Visibility 0

TES_Pixel_L1.Copy TP_L1_00193
TP_L1_00193.Position 0 0 0.775
TP_L1_00193.Mother TES_L1
TP_L1_00193.Visibility 0

TES_Pixel_L1.Copy TP_L1_00194
TP_L1_00194.Position 0 0 0.93
TP_L1_00194.Mother TES_L1
TP_L1_00194.Visibility 0

TES_Pixel_L1.Copy TP_L1_00195
TP_L1_00195.Position 0 0 1.085
TP_L1_00195.Mother TES_L1
TP_L1_00195.Visibility 0

TES_Pixel_L1.Copy TP_L1_00196
TP_L1_00196.Position 0 0 1.24
TP_L1_00196.Mother TES_L1
TP_L1_00196.Visibility 0

TES_Pixel_L1.Copy TP_L1_00197
TP_L1_00197.Position 0 0 1.395
TP_L1_00197.Mother TES_L1
TP_L1_00197.Visibility 0

TES_Pixel_L1.Copy TP_L1_00198
TP_L1_00198.Position 0 0 1.55
TP_L1_00198.Mother TES_L1
TP_L1_00198.Visibility 0

TES_Pixel_L1.Copy TP_L1_00199
TP_L1_00199.Position 0 0 1.705
TP_L1_00199.Mother TES_L1
TP_L1_00199.Visibility 0

TES_Pixel_L1.Copy TP_L1_00200
TP_L1_00200.Position 0 0.155 -1.55
TP_L1_00200.Mother TES_L1
TP_L1_00200.Visibility 0

TES_Pixel_L1.Copy TP_L1_00201
TP_L1_00201.Position 0 0.155 -1.395
TP_L1_00201.Mother TES_L1
TP_L1_00201.Visibility 0

TES_Pixel_L1.Copy TP_L1_00202
TP_L1_00202.Position 0 0.155 -1.24
TP_L1_00202.Mother TES_L1
TP_L1_00202.Visibility 0

TES_Pixel_L1.Copy TP_L1_00203
TP_L1_00203.Position 0 0.155 -1.085
TP_L1_00203.Mother TES_L1
TP_L1_00203.Visibility 0

TES_Pixel_L1.Copy TP_L1_00204
TP_L1_00204.Position 0 0.155 -0.93
TP_L1_00204.Mother TES_L1
TP_L1_00204.Visibility 0

TES_Pixel_L1.Copy TP_L1_00205
TP_L1_00205.Position 0 0.155 -0.775
TP_L1_00205.Mother TES_L1
TP_L1_00205.Visibility 0

TES_Pixel_L1.Copy TP_L1_00206
TP_L1_00206.Position 0 0.155 -0.62
TP_L1_00206.Mother TES_L1
TP_L1_00206.Visibility 0

TES_Pixel_L1.Copy TP_L1_00207
TP_L1_00207.Position 0 0.155 -0.465
TP_L1_00207.Mother TES_L1
TP_L1_00207.Visibility 0

TES_Pixel_L1.Copy TP_L1_00208
TP_L1_00208.Position 0 0.155 -0.31
TP_L1_00208.Mother TES_L1
TP_L1_00208.Visibility 0

TES_Pixel_L1.Copy TP_L1_00209
TP_L1_00209.Position 0 0.155 -0.155
TP_L1_00209.Mother TES_L1
TP_L1_00209.Visibility 0

TES_Pixel_L1.Copy TP_L1_00210
TP_L1_00210.Position 0 0.155 0
TP_L1_00210.Mother TES_L1
TP_L1_00210.Visibility 0

TES_Pixel_L1.Copy TP_L1_00211
TP_L1_00211.Position 0 0.155 0.155
TP_L1_00211.Mother TES_L1
TP_L1_00211.Visibility 0

TES_Pixel_L1.Copy TP_L1_00212
TP_L1_00212.Position 0 0.155 0.31
TP_L1_00212.Mother TES_L1
TP_L1_00212.Visibility 0

TES_Pixel_L1.Copy TP_L1_00213
TP_L1_00213.Position 0 0.155 0.465
TP_L1_00213.Mother TES_L1
TP_L1_00213.Visibility 0

TES_Pixel_L1.Copy TP_L1_00214
TP_L1_00214.Position 0 0.155 0.62
TP_L1_00214.Mother TES_L1
TP_L1_00214.Visibility 0

TES_Pixel_L1.Copy TP_L1_00215
TP_L1_00215.Position 0 0.155 0.775
TP_L1_00215.Mother TES_L1
TP_L1_00215.Visibility 0

TES_Pixel_L1.Copy TP_L1_00216
TP_L1_00216.Position 0 0.155 0.93
TP_L1_00216.Mother TES_L1
TP_L1_00216.Visibility 0

TES_Pixel_L1.Copy TP_L1_00217
TP_L1_00217.Position 0 0.155 1.085
TP_L1_00217.Mother TES_L1
TP_L1_00217.Visibility 0

TES_Pixel_L1.Copy TP_L1_00218
TP_L1_00218.Position 0 0.155 1.24
TP_L1_00218.Mother TES_L1
TP_L1_00218.Visibility 0

TES_Pixel_L1.Copy TP_L1_00219
TP_L1_00219.Position 0 0.155 1.395
TP_L1_00219.Mother TES_L1
TP_L1_00219.Visibility 0

TES_Pixel_L1.Copy TP_L1_00220
TP_L1_00220.Position 0 0.155 1.55
TP_L1_00220.Mother TES_L1
TP_L1_00220.Visibility 0

TES_Pixel_L1.Copy TP_L1_00221
TP_L1_00221.Position 0 0.31 -1.55
TP_L1_00221.Mother TES_L1
TP_L1_00221.Visibility 0

TES_Pixel_L1.Copy TP_L1_00222
TP_L1_00222.Position 0 0.31 -1.395
TP_L1_00222.Mother TES_L1
TP_L1_00222.Visibility 0

TES_Pixel_L1.Copy TP_L1_00223
TP_L1_00223.Position 0 0.31 -1.24
TP_L1_00223.Mother TES_L1
TP_L1_00223.Visibility 0

TES_Pixel_L1.Copy TP_L1_00224
TP_L1_00224.Position 0 0.31 -1.085
TP_L1_00224.Mother TES_L1
TP_L1_00224.Visibility 0

TES_Pixel_L1.Copy TP_L1_00225
TP_L1_00225.Position 0 0.31 -0.93
TP_L1_00225.Mother TES_L1
TP_L1_00225.Visibility 0

TES_Pixel_L1.Copy TP_L1_00226
TP_L1_00226.Position 0 0.31 -0.775
TP_L1_00226.Mother TES_L1
TP_L1_00226.Visibility 0

TES_Pixel_L1.Copy TP_L1_00227
TP_L1_00227.Position 0 0.31 -0.62
TP_L1_00227.Mother TES_L1
TP_L1_00227.Visibility 0

TES_Pixel_L1.Copy TP_L1_00228
TP_L1_00228.Position 0 0.31 -0.465
TP_L1_00228.Mother TES_L1
TP_L1_00228.Visibility 0

TES_Pixel_L1.Copy TP_L1_00229
TP_L1_00229.Position 0 0.31 -0.31
TP_L1_00229.Mother TES_L1
TP_L1_00229.Visibility 0

TES_Pixel_L1.Copy TP_L1_00230
TP_L1_00230.Position 0 0.31 -0.155
TP_L1_00230.Mother TES_L1
TP_L1_00230.Visibility 0

TES_Pixel_L1.Copy TP_L1_00231
TP_L1_00231.Position 0 0.31 0
TP_L1_00231.Mother TES_L1
TP_L1_00231.Visibility 0

TES_Pixel_L1.Copy TP_L1_00232
TP_L1_00232.Position 0 0.31 0.155
TP_L1_00232.Mother TES_L1
TP_L1_00232.Visibility 0

TES_Pixel_L1.Copy TP_L1_00233
TP_L1_00233.Position 0 0.31 0.31
TP_L1_00233.Mother TES_L1
TP_L1_00233.Visibility 0

TES_Pixel_L1.Copy TP_L1_00234
TP_L1_00234.Position 0 0.31 0.465
TP_L1_00234.Mother TES_L1
TP_L1_00234.Visibility 0

TES_Pixel_L1.Copy TP_L1_00235
TP_L1_00235.Position 0 0.31 0.62
TP_L1_00235.Mother TES_L1
TP_L1_00235.Visibility 0

TES_Pixel_L1.Copy TP_L1_00236
TP_L1_00236.Position 0 0.31 0.775
TP_L1_00236.Mother TES_L1
TP_L1_00236.Visibility 0

TES_Pixel_L1.Copy TP_L1_00237
TP_L1_00237.Position 0 0.31 0.93
TP_L1_00237.Mother TES_L1
TP_L1_00237.Visibility 0

TES_Pixel_L1.Copy TP_L1_00238
TP_L1_00238.Position 0 0.31 1.085
TP_L1_00238.Mother TES_L1
TP_L1_00238.Visibility 0

TES_Pixel_L1.Copy TP_L1_00239
TP_L1_00239.Position 0 0.31 1.24
TP_L1_00239.Mother TES_L1
TP_L1_00239.Visibility 0

TES_Pixel_L1.Copy TP_L1_00240
TP_L1_00240.Position 0 0.31 1.395
TP_L1_00240.Mother TES_L1
TP_L1_00240.Visibility 0

TES_Pixel_L1.Copy TP_L1_00241
TP_L1_00241.Position 0 0.31 1.55
TP_L1_00241.Mother TES_L1
TP_L1_00241.Visibility 0

TES_Pixel_L1.Copy TP_L1_00242
TP_L1_00242.Position 0 0.465 -1.55
TP_L1_00242.Mother TES_L1
TP_L1_00242.Visibility 0

TES_Pixel_L1.Copy TP_L1_00243
TP_L1_00243.Position 0 0.465 -1.395
TP_L1_00243.Mother TES_L1
TP_L1_00243.Visibility 0

TES_Pixel_L1.Copy TP_L1_00244
TP_L1_00244.Position 0 0.465 -1.24
TP_L1_00244.Mother TES_L1
TP_L1_00244.Visibility 0

TES_Pixel_L1.Copy TP_L1_00245
TP_L1_00245.Position 0 0.465 -1.085
TP_L1_00245.Mother TES_L1
TP_L1_00245.Visibility 0

TES_Pixel_L1.Copy TP_L1_00246
TP_L1_00246.Position 0 0.465 -0.93
TP_L1_00246.Mother TES_L1
TP_L1_00246.Visibility 0

TES_Pixel_L1.Copy TP_L1_00247
TP_L1_00247.Position 0 0.465 -0.775
TP_L1_00247.Mother TES_L1
TP_L1_00247.Visibility 0

TES_Pixel_L1.Copy TP_L1_00248
TP_L1_00248.Position 0 0.465 -0.62
TP_L1_00248.Mother TES_L1
TP_L1_00248.Visibility 0

TES_Pixel_L1.Copy TP_L1_00249
TP_L1_00249.Position 0 0.465 -0.465
TP_L1_00249.Mother TES_L1
TP_L1_00249.Visibility 0

TES_Pixel_L1.Copy TP_L1_00250
TP_L1_00250.Position 0 0.465 -0.31
TP_L1_00250.Mother TES_L1
TP_L1_00250.Visibility 0

TES_Pixel_L1.Copy TP_L1_00251
TP_L1_00251.Position 0 0.465 -0.155
TP_L1_00251.Mother TES_L1
TP_L1_00251.Visibility 0

TES_Pixel_L1.Copy TP_L1_00252
TP_L1_00252.Position 0 0.465 0
TP_L1_00252.Mother TES_L1
TP_L1_00252.Visibility 0

TES_Pixel_L1.Copy TP_L1_00253
TP_L1_00253.Position 0 0.465 0.155
TP_L1_00253.Mother TES_L1
TP_L1_00253.Visibility 0

TES_Pixel_L1.Copy TP_L1_00254
TP_L1_00254.Position 0 0.465 0.31
TP_L1_00254.Mother TES_L1
TP_L1_00254.Visibility 0

TES_Pixel_L1.Copy TP_L1_00255
TP_L1_00255.Position 0 0.465 0.465
TP_L1_00255.Mother TES_L1
TP_L1_00255.Visibility 0

TES_Pixel_L1.Copy TP_L1_00256
TP_L1_00256.Position 0 0.465 0.62
TP_L1_00256.Mother TES_L1
TP_L1_00256.Visibility 0

TES_Pixel_L1.Copy TP_L1_00257
TP_L1_00257.Position 0 0.465 0.775
TP_L1_00257.Mother TES_L1
TP_L1_00257.Visibility 0

TES_Pixel_L1.Copy TP_L1_00258
TP_L1_00258.Position 0 0.465 0.93
TP_L1_00258.Mother TES_L1
TP_L1_00258.Visibility 0

TES_Pixel_L1.Copy TP_L1_00259
TP_L1_00259.Position 0 0.465 1.085
TP_L1_00259.Mother TES_L1
TP_L1_00259.Visibility 0

TES_Pixel_L1.Copy TP_L1_00260
TP_L1_00260.Position 0 0.465 1.24
TP_L1_00260.Mother TES_L1
TP_L1_00260.Visibility 0

TES_Pixel_L1.Copy TP_L1_00261
TP_L1_00261.Position 0 0.465 1.395
TP_L1_00261.Mother TES_L1
TP_L1_00261.Visibility 0

TES_Pixel_L1.Copy TP_L1_00262
TP_L1_00262.Position 0 0.465 1.55
TP_L1_00262.Mother TES_L1
TP_L1_00262.Visibility 0

TES_Pixel_L1.Copy TP_L1_00263
TP_L1_00263.Position 0 0.62 -1.55
TP_L1_00263.Mother TES_L1
TP_L1_00263.Visibility 0

TES_Pixel_L1.Copy TP_L1_00264
TP_L1_00264.Position 0 0.62 -1.395
TP_L1_00264.Mother TES_L1
TP_L1_00264.Visibility 0

TES_Pixel_L1.Copy TP_L1_00265
TP_L1_00265.Position 0 0.62 -1.24
TP_L1_00265.Mother TES_L1
TP_L1_00265.Visibility 0

TES_Pixel_L1.Copy TP_L1_00266
TP_L1_00266.Position 0 0.62 -1.085
TP_L1_00266.Mother TES_L1
TP_L1_00266.Visibility 0

TES_Pixel_L1.Copy TP_L1_00267
TP_L1_00267.Position 0 0.62 -0.93
TP_L1_00267.Mother TES_L1
TP_L1_00267.Visibility 0

TES_Pixel_L1.Copy TP_L1_00268
TP_L1_00268.Position 0 0.62 -0.775
TP_L1_00268.Mother TES_L1
TP_L1_00268.Visibility 0

TES_Pixel_L1.Copy TP_L1_00269
TP_L1_00269.Position 0 0.62 -0.62
TP_L1_00269.Mother TES_L1
TP_L1_00269.Visibility 0

TES_Pixel_L1.Copy TP_L1_00270
TP_L1_00270.Position 0 0.62 -0.465
TP_L1_00270.Mother TES_L1
TP_L1_00270.Visibility 0

TES_Pixel_L1.Copy TP_L1_00271
TP_L1_00271.Position 0 0.62 -0.31
TP_L1_00271.Mother TES_L1
TP_L1_00271.Visibility 0

TES_Pixel_L1.Copy TP_L1_00272
TP_L1_00272.Position 0 0.62 -0.155
TP_L1_00272.Mother TES_L1
TP_L1_00272.Visibility 0

TES_Pixel_L1.Copy TP_L1_00273
TP_L1_00273.Position 0 0.62 0
TP_L1_00273.Mother TES_L1
TP_L1_00273.Visibility 0

TES_Pixel_L1.Copy TP_L1_00274
TP_L1_00274.Position 0 0.62 0.155
TP_L1_00274.Mother TES_L1
TP_L1_00274.Visibility 0

TES_Pixel_L1.Copy TP_L1_00275
TP_L1_00275.Position 0 0.62 0.31
TP_L1_00275.Mother TES_L1
TP_L1_00275.Visibility 0

TES_Pixel_L1.Copy TP_L1_00276
TP_L1_00276.Position 0 0.62 0.465
TP_L1_00276.Mother TES_L1
TP_L1_00276.Visibility 0

TES_Pixel_L1.Copy TP_L1_00277
TP_L1_00277.Position 0 0.62 0.62
TP_L1_00277.Mother TES_L1
TP_L1_00277.Visibility 0

TES_Pixel_L1.Copy TP_L1_00278
TP_L1_00278.Position 0 0.62 0.775
TP_L1_00278.Mother TES_L1
TP_L1_00278.Visibility 0

TES_Pixel_L1.Copy TP_L1_00279
TP_L1_00279.Position 0 0.62 0.93
TP_L1_00279.Mother TES_L1
TP_L1_00279.Visibility 0

TES_Pixel_L1.Copy TP_L1_00280
TP_L1_00280.Position 0 0.62 1.085
TP_L1_00280.Mother TES_L1
TP_L1_00280.Visibility 0

TES_Pixel_L1.Copy TP_L1_00281
TP_L1_00281.Position 0 0.62 1.24
TP_L1_00281.Mother TES_L1
TP_L1_00281.Visibility 0

TES_Pixel_L1.Copy TP_L1_00282
TP_L1_00282.Position 0 0.62 1.395
TP_L1_00282.Mother TES_L1
TP_L1_00282.Visibility 0

TES_Pixel_L1.Copy TP_L1_00283
TP_L1_00283.Position 0 0.62 1.55
TP_L1_00283.Mother TES_L1
TP_L1_00283.Visibility 0

TES_Pixel_L1.Copy TP_L1_00284
TP_L1_00284.Position 0 0.775 -1.395
TP_L1_00284.Mother TES_L1
TP_L1_00284.Visibility 0

TES_Pixel_L1.Copy TP_L1_00285
TP_L1_00285.Position 0 0.775 -1.24
TP_L1_00285.Mother TES_L1
TP_L1_00285.Visibility 0

TES_Pixel_L1.Copy TP_L1_00286
TP_L1_00286.Position 0 0.775 -1.085
TP_L1_00286.Mother TES_L1
TP_L1_00286.Visibility 0

TES_Pixel_L1.Copy TP_L1_00287
TP_L1_00287.Position 0 0.775 -0.93
TP_L1_00287.Mother TES_L1
TP_L1_00287.Visibility 0

TES_Pixel_L1.Copy TP_L1_00288
TP_L1_00288.Position 0 0.775 -0.775
TP_L1_00288.Mother TES_L1
TP_L1_00288.Visibility 0

TES_Pixel_L1.Copy TP_L1_00289
TP_L1_00289.Position 0 0.775 -0.62
TP_L1_00289.Mother TES_L1
TP_L1_00289.Visibility 0

TES_Pixel_L1.Copy TP_L1_00290
TP_L1_00290.Position 0 0.775 -0.465
TP_L1_00290.Mother TES_L1
TP_L1_00290.Visibility 0

TES_Pixel_L1.Copy TP_L1_00291
TP_L1_00291.Position 0 0.775 -0.31
TP_L1_00291.Mother TES_L1
TP_L1_00291.Visibility 0

TES_Pixel_L1.Copy TP_L1_00292
TP_L1_00292.Position 0 0.775 -0.155
TP_L1_00292.Mother TES_L1
TP_L1_00292.Visibility 0

TES_Pixel_L1.Copy TP_L1_00293
TP_L1_00293.Position 0 0.775 0
TP_L1_00293.Mother TES_L1
TP_L1_00293.Visibility 0

TES_Pixel_L1.Copy TP_L1_00294
TP_L1_00294.Position 0 0.775 0.155
TP_L1_00294.Mother TES_L1
TP_L1_00294.Visibility 0

TES_Pixel_L1.Copy TP_L1_00295
TP_L1_00295.Position 0 0.775 0.31
TP_L1_00295.Mother TES_L1
TP_L1_00295.Visibility 0

TES_Pixel_L1.Copy TP_L1_00296
TP_L1_00296.Position 0 0.775 0.465
TP_L1_00296.Mother TES_L1
TP_L1_00296.Visibility 0

TES_Pixel_L1.Copy TP_L1_00297
TP_L1_00297.Position 0 0.775 0.62
TP_L1_00297.Mother TES_L1
TP_L1_00297.Visibility 0

TES_Pixel_L1.Copy TP_L1_00298
TP_L1_00298.Position 0 0.775 0.775
TP_L1_00298.Mother TES_L1
TP_L1_00298.Visibility 0

TES_Pixel_L1.Copy TP_L1_00299
TP_L1_00299.Position 0 0.775 0.93
TP_L1_00299.Mother TES_L1
TP_L1_00299.Visibility 0

TES_Pixel_L1.Copy TP_L1_00300
TP_L1_00300.Position 0 0.775 1.085
TP_L1_00300.Mother TES_L1
TP_L1_00300.Visibility 0

TES_Pixel_L1.Copy TP_L1_00301
TP_L1_00301.Position 0 0.775 1.24
TP_L1_00301.Mother TES_L1
TP_L1_00301.Visibility 0

TES_Pixel_L1.Copy TP_L1_00302
TP_L1_00302.Position 0 0.775 1.395
TP_L1_00302.Mother TES_L1
TP_L1_00302.Visibility 0

TES_Pixel_L1.Copy TP_L1_00303
TP_L1_00303.Position 0 0.93 -1.395
TP_L1_00303.Mother TES_L1
TP_L1_00303.Visibility 0

TES_Pixel_L1.Copy TP_L1_00304
TP_L1_00304.Position 0 0.93 -1.24
TP_L1_00304.Mother TES_L1
TP_L1_00304.Visibility 0

TES_Pixel_L1.Copy TP_L1_00305
TP_L1_00305.Position 0 0.93 -1.085
TP_L1_00305.Mother TES_L1
TP_L1_00305.Visibility 0

TES_Pixel_L1.Copy TP_L1_00306
TP_L1_00306.Position 0 0.93 -0.93
TP_L1_00306.Mother TES_L1
TP_L1_00306.Visibility 0

TES_Pixel_L1.Copy TP_L1_00307
TP_L1_00307.Position 0 0.93 -0.775
TP_L1_00307.Mother TES_L1
TP_L1_00307.Visibility 0

TES_Pixel_L1.Copy TP_L1_00308
TP_L1_00308.Position 0 0.93 -0.62
TP_L1_00308.Mother TES_L1
TP_L1_00308.Visibility 0

TES_Pixel_L1.Copy TP_L1_00309
TP_L1_00309.Position 0 0.93 -0.465
TP_L1_00309.Mother TES_L1
TP_L1_00309.Visibility 0

TES_Pixel_L1.Copy TP_L1_00310
TP_L1_00310.Position 0 0.93 -0.31
TP_L1_00310.Mother TES_L1
TP_L1_00310.Visibility 0

TES_Pixel_L1.Copy TP_L1_00311
TP_L1_00311.Position 0 0.93 -0.155
TP_L1_00311.Mother TES_L1
TP_L1_00311.Visibility 0

TES_Pixel_L1.Copy TP_L1_00312
TP_L1_00312.Position 0 0.93 0
TP_L1_00312.Mother TES_L1
TP_L1_00312.Visibility 0

TES_Pixel_L1.Copy TP_L1_00313
TP_L1_00313.Position 0 0.93 0.155
TP_L1_00313.Mother TES_L1
TP_L1_00313.Visibility 0

TES_Pixel_L1.Copy TP_L1_00314
TP_L1_00314.Position 0 0.93 0.31
TP_L1_00314.Mother TES_L1
TP_L1_00314.Visibility 0

TES_Pixel_L1.Copy TP_L1_00315
TP_L1_00315.Position 0 0.93 0.465
TP_L1_00315.Mother TES_L1
TP_L1_00315.Visibility 0

TES_Pixel_L1.Copy TP_L1_00316
TP_L1_00316.Position 0 0.93 0.62
TP_L1_00316.Mother TES_L1
TP_L1_00316.Visibility 0

TES_Pixel_L1.Copy TP_L1_00317
TP_L1_00317.Position 0 0.93 0.775
TP_L1_00317.Mother TES_L1
TP_L1_00317.Visibility 0

TES_Pixel_L1.Copy TP_L1_00318
TP_L1_00318.Position 0 0.93 0.93
TP_L1_00318.Mother TES_L1
TP_L1_00318.Visibility 0

TES_Pixel_L1.Copy TP_L1_00319
TP_L1_00319.Position 0 0.93 1.085
TP_L1_00319.Mother TES_L1
TP_L1_00319.Visibility 0

TES_Pixel_L1.Copy TP_L1_00320
TP_L1_00320.Position 0 0.93 1.24
TP_L1_00320.Mother TES_L1
TP_L1_00320.Visibility 0

TES_Pixel_L1.Copy TP_L1_00321
TP_L1_00321.Position 0 0.93 1.395
TP_L1_00321.Mother TES_L1
TP_L1_00321.Visibility 0

TES_Pixel_L1.Copy TP_L1_00322
TP_L1_00322.Position 0 1.085 -1.24
TP_L1_00322.Mother TES_L1
TP_L1_00322.Visibility 0

TES_Pixel_L1.Copy TP_L1_00323
TP_L1_00323.Position 0 1.085 -1.085
TP_L1_00323.Mother TES_L1
TP_L1_00323.Visibility 0

TES_Pixel_L1.Copy TP_L1_00324
TP_L1_00324.Position 0 1.085 -0.93
TP_L1_00324.Mother TES_L1
TP_L1_00324.Visibility 0

TES_Pixel_L1.Copy TP_L1_00325
TP_L1_00325.Position 0 1.085 -0.775
TP_L1_00325.Mother TES_L1
TP_L1_00325.Visibility 0

TES_Pixel_L1.Copy TP_L1_00326
TP_L1_00326.Position 0 1.085 -0.62
TP_L1_00326.Mother TES_L1
TP_L1_00326.Visibility 0

TES_Pixel_L1.Copy TP_L1_00327
TP_L1_00327.Position 0 1.085 -0.465
TP_L1_00327.Mother TES_L1
TP_L1_00327.Visibility 0

TES_Pixel_L1.Copy TP_L1_00328
TP_L1_00328.Position 0 1.085 -0.31
TP_L1_00328.Mother TES_L1
TP_L1_00328.Visibility 0

TES_Pixel_L1.Copy TP_L1_00329
TP_L1_00329.Position 0 1.085 -0.155
TP_L1_00329.Mother TES_L1
TP_L1_00329.Visibility 0

TES_Pixel_L1.Copy TP_L1_00330
TP_L1_00330.Position 0 1.085 0
TP_L1_00330.Mother TES_L1
TP_L1_00330.Visibility 0

TES_Pixel_L1.Copy TP_L1_00331
TP_L1_00331.Position 0 1.085 0.155
TP_L1_00331.Mother TES_L1
TP_L1_00331.Visibility 0

TES_Pixel_L1.Copy TP_L1_00332
TP_L1_00332.Position 0 1.085 0.31
TP_L1_00332.Mother TES_L1
TP_L1_00332.Visibility 0

TES_Pixel_L1.Copy TP_L1_00333
TP_L1_00333.Position 0 1.085 0.465
TP_L1_00333.Mother TES_L1
TP_L1_00333.Visibility 0

TES_Pixel_L1.Copy TP_L1_00334
TP_L1_00334.Position 0 1.085 0.62
TP_L1_00334.Mother TES_L1
TP_L1_00334.Visibility 0

TES_Pixel_L1.Copy TP_L1_00335
TP_L1_00335.Position 0 1.085 0.775
TP_L1_00335.Mother TES_L1
TP_L1_00335.Visibility 0

TES_Pixel_L1.Copy TP_L1_00336
TP_L1_00336.Position 0 1.085 0.93
TP_L1_00336.Mother TES_L1
TP_L1_00336.Visibility 0

TES_Pixel_L1.Copy TP_L1_00337
TP_L1_00337.Position 0 1.085 1.085
TP_L1_00337.Mother TES_L1
TP_L1_00337.Visibility 0

TES_Pixel_L1.Copy TP_L1_00338
TP_L1_00338.Position 0 1.085 1.24
TP_L1_00338.Mother TES_L1
TP_L1_00338.Visibility 0

TES_Pixel_L1.Copy TP_L1_00339
TP_L1_00339.Position 0 1.24 -1.085
TP_L1_00339.Mother TES_L1
TP_L1_00339.Visibility 0

TES_Pixel_L1.Copy TP_L1_00340
TP_L1_00340.Position 0 1.24 -0.93
TP_L1_00340.Mother TES_L1
TP_L1_00340.Visibility 0

TES_Pixel_L1.Copy TP_L1_00341
TP_L1_00341.Position 0 1.24 -0.775
TP_L1_00341.Mother TES_L1
TP_L1_00341.Visibility 0

TES_Pixel_L1.Copy TP_L1_00342
TP_L1_00342.Position 0 1.24 -0.62
TP_L1_00342.Mother TES_L1
TP_L1_00342.Visibility 0

TES_Pixel_L1.Copy TP_L1_00343
TP_L1_00343.Position 0 1.24 -0.465
TP_L1_00343.Mother TES_L1
TP_L1_00343.Visibility 0

TES_Pixel_L1.Copy TP_L1_00344
TP_L1_00344.Position 0 1.24 -0.31
TP_L1_00344.Mother TES_L1
TP_L1_00344.Visibility 0

TES_Pixel_L1.Copy TP_L1_00345
TP_L1_00345.Position 0 1.24 -0.155
TP_L1_00345.Mother TES_L1
TP_L1_00345.Visibility 0

TES_Pixel_L1.Copy TP_L1_00346
TP_L1_00346.Position 0 1.24 0
TP_L1_00346.Mother TES_L1
TP_L1_00346.Visibility 0

TES_Pixel_L1.Copy TP_L1_00347
TP_L1_00347.Position 0 1.24 0.155
TP_L1_00347.Mother TES_L1
TP_L1_00347.Visibility 0

TES_Pixel_L1.Copy TP_L1_00348
TP_L1_00348.Position 0 1.24 0.31
TP_L1_00348.Mother TES_L1
TP_L1_00348.Visibility 0

TES_Pixel_L1.Copy TP_L1_00349
TP_L1_00349.Position 0 1.24 0.465
TP_L1_00349.Mother TES_L1
TP_L1_00349.Visibility 0

TES_Pixel_L1.Copy TP_L1_00350
TP_L1_00350.Position 0 1.24 0.62
TP_L1_00350.Mother TES_L1
TP_L1_00350.Visibility 0

TES_Pixel_L1.Copy TP_L1_00351
TP_L1_00351.Position 0 1.24 0.775
TP_L1_00351.Mother TES_L1
TP_L1_00351.Visibility 0

TES_Pixel_L1.Copy TP_L1_00352
TP_L1_00352.Position 0 1.24 0.93
TP_L1_00352.Mother TES_L1
TP_L1_00352.Visibility 0

TES_Pixel_L1.Copy TP_L1_00353
TP_L1_00353.Position 0 1.24 1.085
TP_L1_00353.Mother TES_L1
TP_L1_00353.Visibility 0

TES_Pixel_L1.Copy TP_L1_00354
TP_L1_00354.Position 0 1.395 -0.93
TP_L1_00354.Mother TES_L1
TP_L1_00354.Visibility 0

TES_Pixel_L1.Copy TP_L1_00355
TP_L1_00355.Position 0 1.395 -0.775
TP_L1_00355.Mother TES_L1
TP_L1_00355.Visibility 0

TES_Pixel_L1.Copy TP_L1_00356
TP_L1_00356.Position 0 1.395 -0.62
TP_L1_00356.Mother TES_L1
TP_L1_00356.Visibility 0

TES_Pixel_L1.Copy TP_L1_00357
TP_L1_00357.Position 0 1.395 -0.465
TP_L1_00357.Mother TES_L1
TP_L1_00357.Visibility 0

TES_Pixel_L1.Copy TP_L1_00358
TP_L1_00358.Position 0 1.395 -0.31
TP_L1_00358.Mother TES_L1
TP_L1_00358.Visibility 0

TES_Pixel_L1.Copy TP_L1_00359
TP_L1_00359.Position 0 1.395 -0.155
TP_L1_00359.Mother TES_L1
TP_L1_00359.Visibility 0

TES_Pixel_L1.Copy TP_L1_00360
TP_L1_00360.Position 0 1.395 0
TP_L1_00360.Mother TES_L1
TP_L1_00360.Visibility 0

TES_Pixel_L1.Copy TP_L1_00361
TP_L1_00361.Position 0 1.395 0.155
TP_L1_00361.Mother TES_L1
TP_L1_00361.Visibility 0

TES_Pixel_L1.Copy TP_L1_00362
TP_L1_00362.Position 0 1.395 0.31
TP_L1_00362.Mother TES_L1
TP_L1_00362.Visibility 0

TES_Pixel_L1.Copy TP_L1_00363
TP_L1_00363.Position 0 1.395 0.465
TP_L1_00363.Mother TES_L1
TP_L1_00363.Visibility 0

TES_Pixel_L1.Copy TP_L1_00364
TP_L1_00364.Position 0 1.395 0.62
TP_L1_00364.Mother TES_L1
TP_L1_00364.Visibility 0

TES_Pixel_L1.Copy TP_L1_00365
TP_L1_00365.Position 0 1.395 0.775
TP_L1_00365.Mother TES_L1
TP_L1_00365.Visibility 0

TES_Pixel_L1.Copy TP_L1_00366
TP_L1_00366.Position 0 1.395 0.93
TP_L1_00366.Mother TES_L1
TP_L1_00366.Visibility 0

TES_Pixel_L1.Copy TP_L1_00367
TP_L1_00367.Position 0 1.55 -0.62
TP_L1_00367.Mother TES_L1
TP_L1_00367.Visibility 0

TES_Pixel_L1.Copy TP_L1_00368
TP_L1_00368.Position 0 1.55 -0.465
TP_L1_00368.Mother TES_L1
TP_L1_00368.Visibility 0

TES_Pixel_L1.Copy TP_L1_00369
TP_L1_00369.Position 0 1.55 -0.31
TP_L1_00369.Mother TES_L1
TP_L1_00369.Visibility 0

TES_Pixel_L1.Copy TP_L1_00370
TP_L1_00370.Position 0 1.55 -0.155
TP_L1_00370.Mother TES_L1
TP_L1_00370.Visibility 0

TES_Pixel_L1.Copy TP_L1_00371
TP_L1_00371.Position 0 1.55 0
TP_L1_00371.Mother TES_L1
TP_L1_00371.Visibility 0

TES_Pixel_L1.Copy TP_L1_00372
TP_L1_00372.Position 0 1.55 0.155
TP_L1_00372.Mother TES_L1
TP_L1_00372.Visibility 0

TES_Pixel_L1.Copy TP_L1_00373
TP_L1_00373.Position 0 1.55 0.31
TP_L1_00373.Mother TES_L1
TP_L1_00373.Visibility 0

TES_Pixel_L1.Copy TP_L1_00374
TP_L1_00374.Position 0 1.55 0.465
TP_L1_00374.Mother TES_L1
TP_L1_00374.Visibility 0

TES_Pixel_L1.Copy TP_L1_00375
TP_L1_00375.Position 0 1.55 0.62
TP_L1_00375.Mother TES_L1
TP_L1_00375.Visibility 0

// Volume TES_Pixel_L2; material=Ta
Volume TES_Pixel_L2
TES_Pixel_L2.Material Ta
TES_Pixel_L2.Visibility 1
TES_Pixel_L2.Shape BRIK 0.15 0.075 0.075

// Volume TES_L2; material=Vacuum
Volume TES_L2
TES_L2.Material Vacuum
TES_L2.Visibility 0
TES_L2.Shape BRIK 0.15 1.8 1.8

TES_L2.Position -36.15 0 -2.8
TES_L2.Mother InstrumentFrame

TES_Pixel_L2.Copy TP_L2_00000
TP_L2_00000.Position 0 -1.705 0
TP_L2_00000.Mother TES_L2
TP_L2_00000.Visibility 0

TES_Pixel_L2.Copy TP_L2_00001
TP_L2_00001.Position 0 -1.55 -0.62
TP_L2_00001.Mother TES_L2
TP_L2_00001.Visibility 0

TES_Pixel_L2.Copy TP_L2_00002
TP_L2_00002.Position 0 -1.55 -0.465
TP_L2_00002.Mother TES_L2
TP_L2_00002.Visibility 0

TES_Pixel_L2.Copy TP_L2_00003
TP_L2_00003.Position 0 -1.55 -0.31
TP_L2_00003.Mother TES_L2
TP_L2_00003.Visibility 0

TES_Pixel_L2.Copy TP_L2_00004
TP_L2_00004.Position 0 -1.55 -0.155
TP_L2_00004.Mother TES_L2
TP_L2_00004.Visibility 0

TES_Pixel_L2.Copy TP_L2_00005
TP_L2_00005.Position 0 -1.55 0
TP_L2_00005.Mother TES_L2
TP_L2_00005.Visibility 0

TES_Pixel_L2.Copy TP_L2_00006
TP_L2_00006.Position 0 -1.55 0.155
TP_L2_00006.Mother TES_L2
TP_L2_00006.Visibility 0

TES_Pixel_L2.Copy TP_L2_00007
TP_L2_00007.Position 0 -1.55 0.31
TP_L2_00007.Mother TES_L2
TP_L2_00007.Visibility 0

TES_Pixel_L2.Copy TP_L2_00008
TP_L2_00008.Position 0 -1.55 0.465
TP_L2_00008.Mother TES_L2
TP_L2_00008.Visibility 0

TES_Pixel_L2.Copy TP_L2_00009
TP_L2_00009.Position 0 -1.55 0.62
TP_L2_00009.Mother TES_L2
TP_L2_00009.Visibility 0

TES_Pixel_L2.Copy TP_L2_00010
TP_L2_00010.Position 0 -1.395 -0.93
TP_L2_00010.Mother TES_L2
TP_L2_00010.Visibility 0

TES_Pixel_L2.Copy TP_L2_00011
TP_L2_00011.Position 0 -1.395 -0.775
TP_L2_00011.Mother TES_L2
TP_L2_00011.Visibility 0

TES_Pixel_L2.Copy TP_L2_00012
TP_L2_00012.Position 0 -1.395 -0.62
TP_L2_00012.Mother TES_L2
TP_L2_00012.Visibility 0

TES_Pixel_L2.Copy TP_L2_00013
TP_L2_00013.Position 0 -1.395 -0.465
TP_L2_00013.Mother TES_L2
TP_L2_00013.Visibility 0

TES_Pixel_L2.Copy TP_L2_00014
TP_L2_00014.Position 0 -1.395 -0.31
TP_L2_00014.Mother TES_L2
TP_L2_00014.Visibility 0

TES_Pixel_L2.Copy TP_L2_00015
TP_L2_00015.Position 0 -1.395 -0.155
TP_L2_00015.Mother TES_L2
TP_L2_00015.Visibility 0

TES_Pixel_L2.Copy TP_L2_00016
TP_L2_00016.Position 0 -1.395 0
TP_L2_00016.Mother TES_L2
TP_L2_00016.Visibility 0

TES_Pixel_L2.Copy TP_L2_00017
TP_L2_00017.Position 0 -1.395 0.155
TP_L2_00017.Mother TES_L2
TP_L2_00017.Visibility 0

TES_Pixel_L2.Copy TP_L2_00018
TP_L2_00018.Position 0 -1.395 0.31
TP_L2_00018.Mother TES_L2
TP_L2_00018.Visibility 0

TES_Pixel_L2.Copy TP_L2_00019
TP_L2_00019.Position 0 -1.395 0.465
TP_L2_00019.Mother TES_L2
TP_L2_00019.Visibility 0

TES_Pixel_L2.Copy TP_L2_00020
TP_L2_00020.Position 0 -1.395 0.62
TP_L2_00020.Mother TES_L2
TP_L2_00020.Visibility 0

TES_Pixel_L2.Copy TP_L2_00021
TP_L2_00021.Position 0 -1.395 0.775
TP_L2_00021.Mother TES_L2
TP_L2_00021.Visibility 0

TES_Pixel_L2.Copy TP_L2_00022
TP_L2_00022.Position 0 -1.395 0.93
TP_L2_00022.Mother TES_L2
TP_L2_00022.Visibility 0

TES_Pixel_L2.Copy TP_L2_00023
TP_L2_00023.Position 0 -1.24 -1.085
TP_L2_00023.Mother TES_L2
TP_L2_00023.Visibility 0

TES_Pixel_L2.Copy TP_L2_00024
TP_L2_00024.Position 0 -1.24 -0.93
TP_L2_00024.Mother TES_L2
TP_L2_00024.Visibility 0

TES_Pixel_L2.Copy TP_L2_00025
TP_L2_00025.Position 0 -1.24 -0.775
TP_L2_00025.Mother TES_L2
TP_L2_00025.Visibility 0

TES_Pixel_L2.Copy TP_L2_00026
TP_L2_00026.Position 0 -1.24 -0.62
TP_L2_00026.Mother TES_L2
TP_L2_00026.Visibility 0

TES_Pixel_L2.Copy TP_L2_00027
TP_L2_00027.Position 0 -1.24 -0.465
TP_L2_00027.Mother TES_L2
TP_L2_00027.Visibility 0

TES_Pixel_L2.Copy TP_L2_00028
TP_L2_00028.Position 0 -1.24 -0.31
TP_L2_00028.Mother TES_L2
TP_L2_00028.Visibility 0

TES_Pixel_L2.Copy TP_L2_00029
TP_L2_00029.Position 0 -1.24 -0.155
TP_L2_00029.Mother TES_L2
TP_L2_00029.Visibility 0

TES_Pixel_L2.Copy TP_L2_00030
TP_L2_00030.Position 0 -1.24 0
TP_L2_00030.Mother TES_L2
TP_L2_00030.Visibility 0

TES_Pixel_L2.Copy TP_L2_00031
TP_L2_00031.Position 0 -1.24 0.155
TP_L2_00031.Mother TES_L2
TP_L2_00031.Visibility 0

TES_Pixel_L2.Copy TP_L2_00032
TP_L2_00032.Position 0 -1.24 0.31
TP_L2_00032.Mother TES_L2
TP_L2_00032.Visibility 0

TES_Pixel_L2.Copy TP_L2_00033
TP_L2_00033.Position 0 -1.24 0.465
TP_L2_00033.Mother TES_L2
TP_L2_00033.Visibility 0

TES_Pixel_L2.Copy TP_L2_00034
TP_L2_00034.Position 0 -1.24 0.62
TP_L2_00034.Mother TES_L2
TP_L2_00034.Visibility 0

TES_Pixel_L2.Copy TP_L2_00035
TP_L2_00035.Position 0 -1.24 0.775
TP_L2_00035.Mother TES_L2
TP_L2_00035.Visibility 0

TES_Pixel_L2.Copy TP_L2_00036
TP_L2_00036.Position 0 -1.24 0.93
TP_L2_00036.Mother TES_L2
TP_L2_00036.Visibility 0

TES_Pixel_L2.Copy TP_L2_00037
TP_L2_00037.Position 0 -1.24 1.085
TP_L2_00037.Mother TES_L2
TP_L2_00037.Visibility 0

TES_Pixel_L2.Copy TP_L2_00038
TP_L2_00038.Position 0 -1.085 -1.24
TP_L2_00038.Mother TES_L2
TP_L2_00038.Visibility 0

TES_Pixel_L2.Copy TP_L2_00039
TP_L2_00039.Position 0 -1.085 -1.085
TP_L2_00039.Mother TES_L2
TP_L2_00039.Visibility 0

TES_Pixel_L2.Copy TP_L2_00040
TP_L2_00040.Position 0 -1.085 -0.93
TP_L2_00040.Mother TES_L2
TP_L2_00040.Visibility 0

TES_Pixel_L2.Copy TP_L2_00041
TP_L2_00041.Position 0 -1.085 -0.775
TP_L2_00041.Mother TES_L2
TP_L2_00041.Visibility 0

TES_Pixel_L2.Copy TP_L2_00042
TP_L2_00042.Position 0 -1.085 -0.62
TP_L2_00042.Mother TES_L2
TP_L2_00042.Visibility 0

TES_Pixel_L2.Copy TP_L2_00043
TP_L2_00043.Position 0 -1.085 -0.465
TP_L2_00043.Mother TES_L2
TP_L2_00043.Visibility 0

TES_Pixel_L2.Copy TP_L2_00044
TP_L2_00044.Position 0 -1.085 -0.31
TP_L2_00044.Mother TES_L2
TP_L2_00044.Visibility 0

TES_Pixel_L2.Copy TP_L2_00045
TP_L2_00045.Position 0 -1.085 -0.155
TP_L2_00045.Mother TES_L2
TP_L2_00045.Visibility 0

TES_Pixel_L2.Copy TP_L2_00046
TP_L2_00046.Position 0 -1.085 0
TP_L2_00046.Mother TES_L2
TP_L2_00046.Visibility 0

TES_Pixel_L2.Copy TP_L2_00047
TP_L2_00047.Position 0 -1.085 0.155
TP_L2_00047.Mother TES_L2
TP_L2_00047.Visibility 0

TES_Pixel_L2.Copy TP_L2_00048
TP_L2_00048.Position 0 -1.085 0.31
TP_L2_00048.Mother TES_L2
TP_L2_00048.Visibility 0

TES_Pixel_L2.Copy TP_L2_00049
TP_L2_00049.Position 0 -1.085 0.465
TP_L2_00049.Mother TES_L2
TP_L2_00049.Visibility 0

TES_Pixel_L2.Copy TP_L2_00050
TP_L2_00050.Position 0 -1.085 0.62
TP_L2_00050.Mother TES_L2
TP_L2_00050.Visibility 0

TES_Pixel_L2.Copy TP_L2_00051
TP_L2_00051.Position 0 -1.085 0.775
TP_L2_00051.Mother TES_L2
TP_L2_00051.Visibility 0

TES_Pixel_L2.Copy TP_L2_00052
TP_L2_00052.Position 0 -1.085 0.93
TP_L2_00052.Mother TES_L2
TP_L2_00052.Visibility 0

TES_Pixel_L2.Copy TP_L2_00053
TP_L2_00053.Position 0 -1.085 1.085
TP_L2_00053.Mother TES_L2
TP_L2_00053.Visibility 0

TES_Pixel_L2.Copy TP_L2_00054
TP_L2_00054.Position 0 -1.085 1.24
TP_L2_00054.Mother TES_L2
TP_L2_00054.Visibility 0

TES_Pixel_L2.Copy TP_L2_00055
TP_L2_00055.Position 0 -0.93 -1.395
TP_L2_00055.Mother TES_L2
TP_L2_00055.Visibility 0

TES_Pixel_L2.Copy TP_L2_00056
TP_L2_00056.Position 0 -0.93 -1.24
TP_L2_00056.Mother TES_L2
TP_L2_00056.Visibility 0

TES_Pixel_L2.Copy TP_L2_00057
TP_L2_00057.Position 0 -0.93 -1.085
TP_L2_00057.Mother TES_L2
TP_L2_00057.Visibility 0

TES_Pixel_L2.Copy TP_L2_00058
TP_L2_00058.Position 0 -0.93 -0.93
TP_L2_00058.Mother TES_L2
TP_L2_00058.Visibility 0

TES_Pixel_L2.Copy TP_L2_00059
TP_L2_00059.Position 0 -0.93 -0.775
TP_L2_00059.Mother TES_L2
TP_L2_00059.Visibility 0

TES_Pixel_L2.Copy TP_L2_00060
TP_L2_00060.Position 0 -0.93 -0.62
TP_L2_00060.Mother TES_L2
TP_L2_00060.Visibility 0

TES_Pixel_L2.Copy TP_L2_00061
TP_L2_00061.Position 0 -0.93 -0.465
TP_L2_00061.Mother TES_L2
TP_L2_00061.Visibility 0

TES_Pixel_L2.Copy TP_L2_00062
TP_L2_00062.Position 0 -0.93 -0.31
TP_L2_00062.Mother TES_L2
TP_L2_00062.Visibility 0

TES_Pixel_L2.Copy TP_L2_00063
TP_L2_00063.Position 0 -0.93 -0.155
TP_L2_00063.Mother TES_L2
TP_L2_00063.Visibility 0

TES_Pixel_L2.Copy TP_L2_00064
TP_L2_00064.Position 0 -0.93 0
TP_L2_00064.Mother TES_L2
TP_L2_00064.Visibility 0

TES_Pixel_L2.Copy TP_L2_00065
TP_L2_00065.Position 0 -0.93 0.155
TP_L2_00065.Mother TES_L2
TP_L2_00065.Visibility 0

TES_Pixel_L2.Copy TP_L2_00066
TP_L2_00066.Position 0 -0.93 0.31
TP_L2_00066.Mother TES_L2
TP_L2_00066.Visibility 0

TES_Pixel_L2.Copy TP_L2_00067
TP_L2_00067.Position 0 -0.93 0.465
TP_L2_00067.Mother TES_L2
TP_L2_00067.Visibility 0

TES_Pixel_L2.Copy TP_L2_00068
TP_L2_00068.Position 0 -0.93 0.62
TP_L2_00068.Mother TES_L2
TP_L2_00068.Visibility 0

TES_Pixel_L2.Copy TP_L2_00069
TP_L2_00069.Position 0 -0.93 0.775
TP_L2_00069.Mother TES_L2
TP_L2_00069.Visibility 0

TES_Pixel_L2.Copy TP_L2_00070
TP_L2_00070.Position 0 -0.93 0.93
TP_L2_00070.Mother TES_L2
TP_L2_00070.Visibility 0

TES_Pixel_L2.Copy TP_L2_00071
TP_L2_00071.Position 0 -0.93 1.085
TP_L2_00071.Mother TES_L2
TP_L2_00071.Visibility 0

TES_Pixel_L2.Copy TP_L2_00072
TP_L2_00072.Position 0 -0.93 1.24
TP_L2_00072.Mother TES_L2
TP_L2_00072.Visibility 0

TES_Pixel_L2.Copy TP_L2_00073
TP_L2_00073.Position 0 -0.93 1.395
TP_L2_00073.Mother TES_L2
TP_L2_00073.Visibility 0

TES_Pixel_L2.Copy TP_L2_00074
TP_L2_00074.Position 0 -0.775 -1.395
TP_L2_00074.Mother TES_L2
TP_L2_00074.Visibility 0

TES_Pixel_L2.Copy TP_L2_00075
TP_L2_00075.Position 0 -0.775 -1.24
TP_L2_00075.Mother TES_L2
TP_L2_00075.Visibility 0

TES_Pixel_L2.Copy TP_L2_00076
TP_L2_00076.Position 0 -0.775 -1.085
TP_L2_00076.Mother TES_L2
TP_L2_00076.Visibility 0

TES_Pixel_L2.Copy TP_L2_00077
TP_L2_00077.Position 0 -0.775 -0.93
TP_L2_00077.Mother TES_L2
TP_L2_00077.Visibility 0

TES_Pixel_L2.Copy TP_L2_00078
TP_L2_00078.Position 0 -0.775 -0.775
TP_L2_00078.Mother TES_L2
TP_L2_00078.Visibility 0

TES_Pixel_L2.Copy TP_L2_00079
TP_L2_00079.Position 0 -0.775 -0.62
TP_L2_00079.Mother TES_L2
TP_L2_00079.Visibility 0

TES_Pixel_L2.Copy TP_L2_00080
TP_L2_00080.Position 0 -0.775 -0.465
TP_L2_00080.Mother TES_L2
TP_L2_00080.Visibility 0

TES_Pixel_L2.Copy TP_L2_00081
TP_L2_00081.Position 0 -0.775 -0.31
TP_L2_00081.Mother TES_L2
TP_L2_00081.Visibility 0

TES_Pixel_L2.Copy TP_L2_00082
TP_L2_00082.Position 0 -0.775 -0.155
TP_L2_00082.Mother TES_L2
TP_L2_00082.Visibility 0

TES_Pixel_L2.Copy TP_L2_00083
TP_L2_00083.Position 0 -0.775 0
TP_L2_00083.Mother TES_L2
TP_L2_00083.Visibility 0

TES_Pixel_L2.Copy TP_L2_00084
TP_L2_00084.Position 0 -0.775 0.155
TP_L2_00084.Mother TES_L2
TP_L2_00084.Visibility 0

TES_Pixel_L2.Copy TP_L2_00085
TP_L2_00085.Position 0 -0.775 0.31
TP_L2_00085.Mother TES_L2
TP_L2_00085.Visibility 0

TES_Pixel_L2.Copy TP_L2_00086
TP_L2_00086.Position 0 -0.775 0.465
TP_L2_00086.Mother TES_L2
TP_L2_00086.Visibility 0

TES_Pixel_L2.Copy TP_L2_00087
TP_L2_00087.Position 0 -0.775 0.62
TP_L2_00087.Mother TES_L2
TP_L2_00087.Visibility 0

TES_Pixel_L2.Copy TP_L2_00088
TP_L2_00088.Position 0 -0.775 0.775
TP_L2_00088.Mother TES_L2
TP_L2_00088.Visibility 0

TES_Pixel_L2.Copy TP_L2_00089
TP_L2_00089.Position 0 -0.775 0.93
TP_L2_00089.Mother TES_L2
TP_L2_00089.Visibility 0

TES_Pixel_L2.Copy TP_L2_00090
TP_L2_00090.Position 0 -0.775 1.085
TP_L2_00090.Mother TES_L2
TP_L2_00090.Visibility 0

TES_Pixel_L2.Copy TP_L2_00091
TP_L2_00091.Position 0 -0.775 1.24
TP_L2_00091.Mother TES_L2
TP_L2_00091.Visibility 0

TES_Pixel_L2.Copy TP_L2_00092
TP_L2_00092.Position 0 -0.775 1.395
TP_L2_00092.Mother TES_L2
TP_L2_00092.Visibility 0

TES_Pixel_L2.Copy TP_L2_00093
TP_L2_00093.Position 0 -0.62 -1.55
TP_L2_00093.Mother TES_L2
TP_L2_00093.Visibility 0

TES_Pixel_L2.Copy TP_L2_00094
TP_L2_00094.Position 0 -0.62 -1.395
TP_L2_00094.Mother TES_L2
TP_L2_00094.Visibility 0

TES_Pixel_L2.Copy TP_L2_00095
TP_L2_00095.Position 0 -0.62 -1.24
TP_L2_00095.Mother TES_L2
TP_L2_00095.Visibility 0

TES_Pixel_L2.Copy TP_L2_00096
TP_L2_00096.Position 0 -0.62 -1.085
TP_L2_00096.Mother TES_L2
TP_L2_00096.Visibility 0

TES_Pixel_L2.Copy TP_L2_00097
TP_L2_00097.Position 0 -0.62 -0.93
TP_L2_00097.Mother TES_L2
TP_L2_00097.Visibility 0

TES_Pixel_L2.Copy TP_L2_00098
TP_L2_00098.Position 0 -0.62 -0.775
TP_L2_00098.Mother TES_L2
TP_L2_00098.Visibility 0

TES_Pixel_L2.Copy TP_L2_00099
TP_L2_00099.Position 0 -0.62 -0.62
TP_L2_00099.Mother TES_L2
TP_L2_00099.Visibility 0

TES_Pixel_L2.Copy TP_L2_00100
TP_L2_00100.Position 0 -0.62 -0.465
TP_L2_00100.Mother TES_L2
TP_L2_00100.Visibility 0

TES_Pixel_L2.Copy TP_L2_00101
TP_L2_00101.Position 0 -0.62 -0.31
TP_L2_00101.Mother TES_L2
TP_L2_00101.Visibility 0

TES_Pixel_L2.Copy TP_L2_00102
TP_L2_00102.Position 0 -0.62 -0.155
TP_L2_00102.Mother TES_L2
TP_L2_00102.Visibility 0

TES_Pixel_L2.Copy TP_L2_00103
TP_L2_00103.Position 0 -0.62 0
TP_L2_00103.Mother TES_L2
TP_L2_00103.Visibility 0

TES_Pixel_L2.Copy TP_L2_00104
TP_L2_00104.Position 0 -0.62 0.155
TP_L2_00104.Mother TES_L2
TP_L2_00104.Visibility 0

TES_Pixel_L2.Copy TP_L2_00105
TP_L2_00105.Position 0 -0.62 0.31
TP_L2_00105.Mother TES_L2
TP_L2_00105.Visibility 0

TES_Pixel_L2.Copy TP_L2_00106
TP_L2_00106.Position 0 -0.62 0.465
TP_L2_00106.Mother TES_L2
TP_L2_00106.Visibility 0

TES_Pixel_L2.Copy TP_L2_00107
TP_L2_00107.Position 0 -0.62 0.62
TP_L2_00107.Mother TES_L2
TP_L2_00107.Visibility 0

TES_Pixel_L2.Copy TP_L2_00108
TP_L2_00108.Position 0 -0.62 0.775
TP_L2_00108.Mother TES_L2
TP_L2_00108.Visibility 0

TES_Pixel_L2.Copy TP_L2_00109
TP_L2_00109.Position 0 -0.62 0.93
TP_L2_00109.Mother TES_L2
TP_L2_00109.Visibility 0

TES_Pixel_L2.Copy TP_L2_00110
TP_L2_00110.Position 0 -0.62 1.085
TP_L2_00110.Mother TES_L2
TP_L2_00110.Visibility 0

TES_Pixel_L2.Copy TP_L2_00111
TP_L2_00111.Position 0 -0.62 1.24
TP_L2_00111.Mother TES_L2
TP_L2_00111.Visibility 0

TES_Pixel_L2.Copy TP_L2_00112
TP_L2_00112.Position 0 -0.62 1.395
TP_L2_00112.Mother TES_L2
TP_L2_00112.Visibility 0

TES_Pixel_L2.Copy TP_L2_00113
TP_L2_00113.Position 0 -0.62 1.55
TP_L2_00113.Mother TES_L2
TP_L2_00113.Visibility 0

TES_Pixel_L2.Copy TP_L2_00114
TP_L2_00114.Position 0 -0.465 -1.55
TP_L2_00114.Mother TES_L2
TP_L2_00114.Visibility 0

TES_Pixel_L2.Copy TP_L2_00115
TP_L2_00115.Position 0 -0.465 -1.395
TP_L2_00115.Mother TES_L2
TP_L2_00115.Visibility 0

TES_Pixel_L2.Copy TP_L2_00116
TP_L2_00116.Position 0 -0.465 -1.24
TP_L2_00116.Mother TES_L2
TP_L2_00116.Visibility 0

TES_Pixel_L2.Copy TP_L2_00117
TP_L2_00117.Position 0 -0.465 -1.085
TP_L2_00117.Mother TES_L2
TP_L2_00117.Visibility 0

TES_Pixel_L2.Copy TP_L2_00118
TP_L2_00118.Position 0 -0.465 -0.93
TP_L2_00118.Mother TES_L2
TP_L2_00118.Visibility 0

TES_Pixel_L2.Copy TP_L2_00119
TP_L2_00119.Position 0 -0.465 -0.775
TP_L2_00119.Mother TES_L2
TP_L2_00119.Visibility 0

TES_Pixel_L2.Copy TP_L2_00120
TP_L2_00120.Position 0 -0.465 -0.62
TP_L2_00120.Mother TES_L2
TP_L2_00120.Visibility 0

TES_Pixel_L2.Copy TP_L2_00121
TP_L2_00121.Position 0 -0.465 -0.465
TP_L2_00121.Mother TES_L2
TP_L2_00121.Visibility 0

TES_Pixel_L2.Copy TP_L2_00122
TP_L2_00122.Position 0 -0.465 -0.31
TP_L2_00122.Mother TES_L2
TP_L2_00122.Visibility 0

TES_Pixel_L2.Copy TP_L2_00123
TP_L2_00123.Position 0 -0.465 -0.155
TP_L2_00123.Mother TES_L2
TP_L2_00123.Visibility 0

TES_Pixel_L2.Copy TP_L2_00124
TP_L2_00124.Position 0 -0.465 0
TP_L2_00124.Mother TES_L2
TP_L2_00124.Visibility 0

TES_Pixel_L2.Copy TP_L2_00125
TP_L2_00125.Position 0 -0.465 0.155
TP_L2_00125.Mother TES_L2
TP_L2_00125.Visibility 0

TES_Pixel_L2.Copy TP_L2_00126
TP_L2_00126.Position 0 -0.465 0.31
TP_L2_00126.Mother TES_L2
TP_L2_00126.Visibility 0

TES_Pixel_L2.Copy TP_L2_00127
TP_L2_00127.Position 0 -0.465 0.465
TP_L2_00127.Mother TES_L2
TP_L2_00127.Visibility 0

TES_Pixel_L2.Copy TP_L2_00128
TP_L2_00128.Position 0 -0.465 0.62
TP_L2_00128.Mother TES_L2
TP_L2_00128.Visibility 0

TES_Pixel_L2.Copy TP_L2_00129
TP_L2_00129.Position 0 -0.465 0.775
TP_L2_00129.Mother TES_L2
TP_L2_00129.Visibility 0

TES_Pixel_L2.Copy TP_L2_00130
TP_L2_00130.Position 0 -0.465 0.93
TP_L2_00130.Mother TES_L2
TP_L2_00130.Visibility 0

TES_Pixel_L2.Copy TP_L2_00131
TP_L2_00131.Position 0 -0.465 1.085
TP_L2_00131.Mother TES_L2
TP_L2_00131.Visibility 0

TES_Pixel_L2.Copy TP_L2_00132
TP_L2_00132.Position 0 -0.465 1.24
TP_L2_00132.Mother TES_L2
TP_L2_00132.Visibility 0

TES_Pixel_L2.Copy TP_L2_00133
TP_L2_00133.Position 0 -0.465 1.395
TP_L2_00133.Mother TES_L2
TP_L2_00133.Visibility 0

TES_Pixel_L2.Copy TP_L2_00134
TP_L2_00134.Position 0 -0.465 1.55
TP_L2_00134.Mother TES_L2
TP_L2_00134.Visibility 0

TES_Pixel_L2.Copy TP_L2_00135
TP_L2_00135.Position 0 -0.31 -1.55
TP_L2_00135.Mother TES_L2
TP_L2_00135.Visibility 0

TES_Pixel_L2.Copy TP_L2_00136
TP_L2_00136.Position 0 -0.31 -1.395
TP_L2_00136.Mother TES_L2
TP_L2_00136.Visibility 0

TES_Pixel_L2.Copy TP_L2_00137
TP_L2_00137.Position 0 -0.31 -1.24
TP_L2_00137.Mother TES_L2
TP_L2_00137.Visibility 0

TES_Pixel_L2.Copy TP_L2_00138
TP_L2_00138.Position 0 -0.31 -1.085
TP_L2_00138.Mother TES_L2
TP_L2_00138.Visibility 0

TES_Pixel_L2.Copy TP_L2_00139
TP_L2_00139.Position 0 -0.31 -0.93
TP_L2_00139.Mother TES_L2
TP_L2_00139.Visibility 0

TES_Pixel_L2.Copy TP_L2_00140
TP_L2_00140.Position 0 -0.31 -0.775
TP_L2_00140.Mother TES_L2
TP_L2_00140.Visibility 0

TES_Pixel_L2.Copy TP_L2_00141
TP_L2_00141.Position 0 -0.31 -0.62
TP_L2_00141.Mother TES_L2
TP_L2_00141.Visibility 0

TES_Pixel_L2.Copy TP_L2_00142
TP_L2_00142.Position 0 -0.31 -0.465
TP_L2_00142.Mother TES_L2
TP_L2_00142.Visibility 0

TES_Pixel_L2.Copy TP_L2_00143
TP_L2_00143.Position 0 -0.31 -0.31
TP_L2_00143.Mother TES_L2
TP_L2_00143.Visibility 0

TES_Pixel_L2.Copy TP_L2_00144
TP_L2_00144.Position 0 -0.31 -0.155
TP_L2_00144.Mother TES_L2
TP_L2_00144.Visibility 0

TES_Pixel_L2.Copy TP_L2_00145
TP_L2_00145.Position 0 -0.31 0
TP_L2_00145.Mother TES_L2
TP_L2_00145.Visibility 0

TES_Pixel_L2.Copy TP_L2_00146
TP_L2_00146.Position 0 -0.31 0.155
TP_L2_00146.Mother TES_L2
TP_L2_00146.Visibility 0

TES_Pixel_L2.Copy TP_L2_00147
TP_L2_00147.Position 0 -0.31 0.31
TP_L2_00147.Mother TES_L2
TP_L2_00147.Visibility 0

TES_Pixel_L2.Copy TP_L2_00148
TP_L2_00148.Position 0 -0.31 0.465
TP_L2_00148.Mother TES_L2
TP_L2_00148.Visibility 0

TES_Pixel_L2.Copy TP_L2_00149
TP_L2_00149.Position 0 -0.31 0.62
TP_L2_00149.Mother TES_L2
TP_L2_00149.Visibility 0

TES_Pixel_L2.Copy TP_L2_00150
TP_L2_00150.Position 0 -0.31 0.775
TP_L2_00150.Mother TES_L2
TP_L2_00150.Visibility 0

TES_Pixel_L2.Copy TP_L2_00151
TP_L2_00151.Position 0 -0.31 0.93
TP_L2_00151.Mother TES_L2
TP_L2_00151.Visibility 0

TES_Pixel_L2.Copy TP_L2_00152
TP_L2_00152.Position 0 -0.31 1.085
TP_L2_00152.Mother TES_L2
TP_L2_00152.Visibility 0

TES_Pixel_L2.Copy TP_L2_00153
TP_L2_00153.Position 0 -0.31 1.24
TP_L2_00153.Mother TES_L2
TP_L2_00153.Visibility 0

TES_Pixel_L2.Copy TP_L2_00154
TP_L2_00154.Position 0 -0.31 1.395
TP_L2_00154.Mother TES_L2
TP_L2_00154.Visibility 0

TES_Pixel_L2.Copy TP_L2_00155
TP_L2_00155.Position 0 -0.31 1.55
TP_L2_00155.Mother TES_L2
TP_L2_00155.Visibility 0

TES_Pixel_L2.Copy TP_L2_00156
TP_L2_00156.Position 0 -0.155 -1.55
TP_L2_00156.Mother TES_L2
TP_L2_00156.Visibility 0

TES_Pixel_L2.Copy TP_L2_00157
TP_L2_00157.Position 0 -0.155 -1.395
TP_L2_00157.Mother TES_L2
TP_L2_00157.Visibility 0

TES_Pixel_L2.Copy TP_L2_00158
TP_L2_00158.Position 0 -0.155 -1.24
TP_L2_00158.Mother TES_L2
TP_L2_00158.Visibility 0

TES_Pixel_L2.Copy TP_L2_00159
TP_L2_00159.Position 0 -0.155 -1.085
TP_L2_00159.Mother TES_L2
TP_L2_00159.Visibility 0

TES_Pixel_L2.Copy TP_L2_00160
TP_L2_00160.Position 0 -0.155 -0.93
TP_L2_00160.Mother TES_L2
TP_L2_00160.Visibility 0

TES_Pixel_L2.Copy TP_L2_00161
TP_L2_00161.Position 0 -0.155 -0.775
TP_L2_00161.Mother TES_L2
TP_L2_00161.Visibility 0

TES_Pixel_L2.Copy TP_L2_00162
TP_L2_00162.Position 0 -0.155 -0.62
TP_L2_00162.Mother TES_L2
TP_L2_00162.Visibility 0

TES_Pixel_L2.Copy TP_L2_00163
TP_L2_00163.Position 0 -0.155 -0.465
TP_L2_00163.Mother TES_L2
TP_L2_00163.Visibility 0

TES_Pixel_L2.Copy TP_L2_00164
TP_L2_00164.Position 0 -0.155 -0.31
TP_L2_00164.Mother TES_L2
TP_L2_00164.Visibility 0

TES_Pixel_L2.Copy TP_L2_00165
TP_L2_00165.Position 0 -0.155 -0.155
TP_L2_00165.Mother TES_L2
TP_L2_00165.Visibility 0

TES_Pixel_L2.Copy TP_L2_00166
TP_L2_00166.Position 0 -0.155 0
TP_L2_00166.Mother TES_L2
TP_L2_00166.Visibility 0

TES_Pixel_L2.Copy TP_L2_00167
TP_L2_00167.Position 0 -0.155 0.155
TP_L2_00167.Mother TES_L2
TP_L2_00167.Visibility 0

TES_Pixel_L2.Copy TP_L2_00168
TP_L2_00168.Position 0 -0.155 0.31
TP_L2_00168.Mother TES_L2
TP_L2_00168.Visibility 0

TES_Pixel_L2.Copy TP_L2_00169
TP_L2_00169.Position 0 -0.155 0.465
TP_L2_00169.Mother TES_L2
TP_L2_00169.Visibility 0

TES_Pixel_L2.Copy TP_L2_00170
TP_L2_00170.Position 0 -0.155 0.62
TP_L2_00170.Mother TES_L2
TP_L2_00170.Visibility 0

TES_Pixel_L2.Copy TP_L2_00171
TP_L2_00171.Position 0 -0.155 0.775
TP_L2_00171.Mother TES_L2
TP_L2_00171.Visibility 0

TES_Pixel_L2.Copy TP_L2_00172
TP_L2_00172.Position 0 -0.155 0.93
TP_L2_00172.Mother TES_L2
TP_L2_00172.Visibility 0

TES_Pixel_L2.Copy TP_L2_00173
TP_L2_00173.Position 0 -0.155 1.085
TP_L2_00173.Mother TES_L2
TP_L2_00173.Visibility 0

TES_Pixel_L2.Copy TP_L2_00174
TP_L2_00174.Position 0 -0.155 1.24
TP_L2_00174.Mother TES_L2
TP_L2_00174.Visibility 0

TES_Pixel_L2.Copy TP_L2_00175
TP_L2_00175.Position 0 -0.155 1.395
TP_L2_00175.Mother TES_L2
TP_L2_00175.Visibility 0

TES_Pixel_L2.Copy TP_L2_00176
TP_L2_00176.Position 0 -0.155 1.55
TP_L2_00176.Mother TES_L2
TP_L2_00176.Visibility 0

TES_Pixel_L2.Copy TP_L2_00177
TP_L2_00177.Position 0 0 -1.705
TP_L2_00177.Mother TES_L2
TP_L2_00177.Visibility 0

TES_Pixel_L2.Copy TP_L2_00178
TP_L2_00178.Position 0 0 -1.55
TP_L2_00178.Mother TES_L2
TP_L2_00178.Visibility 0

TES_Pixel_L2.Copy TP_L2_00179
TP_L2_00179.Position 0 0 -1.395
TP_L2_00179.Mother TES_L2
TP_L2_00179.Visibility 0

TES_Pixel_L2.Copy TP_L2_00180
TP_L2_00180.Position 0 0 -1.24
TP_L2_00180.Mother TES_L2
TP_L2_00180.Visibility 0

TES_Pixel_L2.Copy TP_L2_00181
TP_L2_00181.Position 0 0 -1.085
TP_L2_00181.Mother TES_L2
TP_L2_00181.Visibility 0

TES_Pixel_L2.Copy TP_L2_00182
TP_L2_00182.Position 0 0 -0.93
TP_L2_00182.Mother TES_L2
TP_L2_00182.Visibility 0

TES_Pixel_L2.Copy TP_L2_00183
TP_L2_00183.Position 0 0 -0.775
TP_L2_00183.Mother TES_L2
TP_L2_00183.Visibility 0

TES_Pixel_L2.Copy TP_L2_00184
TP_L2_00184.Position 0 0 -0.62
TP_L2_00184.Mother TES_L2
TP_L2_00184.Visibility 0

TES_Pixel_L2.Copy TP_L2_00185
TP_L2_00185.Position 0 0 -0.465
TP_L2_00185.Mother TES_L2
TP_L2_00185.Visibility 0

TES_Pixel_L2.Copy TP_L2_00186
TP_L2_00186.Position 0 0 -0.31
TP_L2_00186.Mother TES_L2
TP_L2_00186.Visibility 0

TES_Pixel_L2.Copy TP_L2_00187
TP_L2_00187.Position 0 0 -0.155
TP_L2_00187.Mother TES_L2
TP_L2_00187.Visibility 0

TES_Pixel_L2.Copy TP_L2_00188
TP_L2_00188.Position 0 0 0
TP_L2_00188.Mother TES_L2
TP_L2_00188.Visibility 0

TES_Pixel_L2.Copy TP_L2_00189
TP_L2_00189.Position 0 0 0.155
TP_L2_00189.Mother TES_L2
TP_L2_00189.Visibility 0

TES_Pixel_L2.Copy TP_L2_00190
TP_L2_00190.Position 0 0 0.31
TP_L2_00190.Mother TES_L2
TP_L2_00190.Visibility 0

TES_Pixel_L2.Copy TP_L2_00191
TP_L2_00191.Position 0 0 0.465
TP_L2_00191.Mother TES_L2
TP_L2_00191.Visibility 0

TES_Pixel_L2.Copy TP_L2_00192
TP_L2_00192.Position 0 0 0.62
TP_L2_00192.Mother TES_L2
TP_L2_00192.Visibility 0

TES_Pixel_L2.Copy TP_L2_00193
TP_L2_00193.Position 0 0 0.775
TP_L2_00193.Mother TES_L2
TP_L2_00193.Visibility 0

TES_Pixel_L2.Copy TP_L2_00194
TP_L2_00194.Position 0 0 0.93
TP_L2_00194.Mother TES_L2
TP_L2_00194.Visibility 0

TES_Pixel_L2.Copy TP_L2_00195
TP_L2_00195.Position 0 0 1.085
TP_L2_00195.Mother TES_L2
TP_L2_00195.Visibility 0

TES_Pixel_L2.Copy TP_L2_00196
TP_L2_00196.Position 0 0 1.24
TP_L2_00196.Mother TES_L2
TP_L2_00196.Visibility 0

TES_Pixel_L2.Copy TP_L2_00197
TP_L2_00197.Position 0 0 1.395
TP_L2_00197.Mother TES_L2
TP_L2_00197.Visibility 0

TES_Pixel_L2.Copy TP_L2_00198
TP_L2_00198.Position 0 0 1.55
TP_L2_00198.Mother TES_L2
TP_L2_00198.Visibility 0

TES_Pixel_L2.Copy TP_L2_00199
TP_L2_00199.Position 0 0 1.705
TP_L2_00199.Mother TES_L2
TP_L2_00199.Visibility 0

TES_Pixel_L2.Copy TP_L2_00200
TP_L2_00200.Position 0 0.155 -1.55
TP_L2_00200.Mother TES_L2
TP_L2_00200.Visibility 0

TES_Pixel_L2.Copy TP_L2_00201
TP_L2_00201.Position 0 0.155 -1.395
TP_L2_00201.Mother TES_L2
TP_L2_00201.Visibility 0

TES_Pixel_L2.Copy TP_L2_00202
TP_L2_00202.Position 0 0.155 -1.24
TP_L2_00202.Mother TES_L2
TP_L2_00202.Visibility 0

TES_Pixel_L2.Copy TP_L2_00203
TP_L2_00203.Position 0 0.155 -1.085
TP_L2_00203.Mother TES_L2
TP_L2_00203.Visibility 0

TES_Pixel_L2.Copy TP_L2_00204
TP_L2_00204.Position 0 0.155 -0.93
TP_L2_00204.Mother TES_L2
TP_L2_00204.Visibility 0

TES_Pixel_L2.Copy TP_L2_00205
TP_L2_00205.Position 0 0.155 -0.775
TP_L2_00205.Mother TES_L2
TP_L2_00205.Visibility 0

TES_Pixel_L2.Copy TP_L2_00206
TP_L2_00206.Position 0 0.155 -0.62
TP_L2_00206.Mother TES_L2
TP_L2_00206.Visibility 0

TES_Pixel_L2.Copy TP_L2_00207
TP_L2_00207.Position 0 0.155 -0.465
TP_L2_00207.Mother TES_L2
TP_L2_00207.Visibility 0

TES_Pixel_L2.Copy TP_L2_00208
TP_L2_00208.Position 0 0.155 -0.31
TP_L2_00208.Mother TES_L2
TP_L2_00208.Visibility 0

TES_Pixel_L2.Copy TP_L2_00209
TP_L2_00209.Position 0 0.155 -0.155
TP_L2_00209.Mother TES_L2
TP_L2_00209.Visibility 0

TES_Pixel_L2.Copy TP_L2_00210
TP_L2_00210.Position 0 0.155 0
TP_L2_00210.Mother TES_L2
TP_L2_00210.Visibility 0

TES_Pixel_L2.Copy TP_L2_00211
TP_L2_00211.Position 0 0.155 0.155
TP_L2_00211.Mother TES_L2
TP_L2_00211.Visibility 0

TES_Pixel_L2.Copy TP_L2_00212
TP_L2_00212.Position 0 0.155 0.31
TP_L2_00212.Mother TES_L2
TP_L2_00212.Visibility 0

TES_Pixel_L2.Copy TP_L2_00213
TP_L2_00213.Position 0 0.155 0.465
TP_L2_00213.Mother TES_L2
TP_L2_00213.Visibility 0

TES_Pixel_L2.Copy TP_L2_00214
TP_L2_00214.Position 0 0.155 0.62
TP_L2_00214.Mother TES_L2
TP_L2_00214.Visibility 0

TES_Pixel_L2.Copy TP_L2_00215
TP_L2_00215.Position 0 0.155 0.775
TP_L2_00215.Mother TES_L2
TP_L2_00215.Visibility 0

TES_Pixel_L2.Copy TP_L2_00216
TP_L2_00216.Position 0 0.155 0.93
TP_L2_00216.Mother TES_L2
TP_L2_00216.Visibility 0

TES_Pixel_L2.Copy TP_L2_00217
TP_L2_00217.Position 0 0.155 1.085
TP_L2_00217.Mother TES_L2
TP_L2_00217.Visibility 0

TES_Pixel_L2.Copy TP_L2_00218
TP_L2_00218.Position 0 0.155 1.24
TP_L2_00218.Mother TES_L2
TP_L2_00218.Visibility 0

TES_Pixel_L2.Copy TP_L2_00219
TP_L2_00219.Position 0 0.155 1.395
TP_L2_00219.Mother TES_L2
TP_L2_00219.Visibility 0

TES_Pixel_L2.Copy TP_L2_00220
TP_L2_00220.Position 0 0.155 1.55
TP_L2_00220.Mother TES_L2
TP_L2_00220.Visibility 0

TES_Pixel_L2.Copy TP_L2_00221
TP_L2_00221.Position 0 0.31 -1.55
TP_L2_00221.Mother TES_L2
TP_L2_00221.Visibility 0

TES_Pixel_L2.Copy TP_L2_00222
TP_L2_00222.Position 0 0.31 -1.395
TP_L2_00222.Mother TES_L2
TP_L2_00222.Visibility 0

TES_Pixel_L2.Copy TP_L2_00223
TP_L2_00223.Position 0 0.31 -1.24
TP_L2_00223.Mother TES_L2
TP_L2_00223.Visibility 0

TES_Pixel_L2.Copy TP_L2_00224
TP_L2_00224.Position 0 0.31 -1.085
TP_L2_00224.Mother TES_L2
TP_L2_00224.Visibility 0

TES_Pixel_L2.Copy TP_L2_00225
TP_L2_00225.Position 0 0.31 -0.93
TP_L2_00225.Mother TES_L2
TP_L2_00225.Visibility 0

TES_Pixel_L2.Copy TP_L2_00226
TP_L2_00226.Position 0 0.31 -0.775
TP_L2_00226.Mother TES_L2
TP_L2_00226.Visibility 0

TES_Pixel_L2.Copy TP_L2_00227
TP_L2_00227.Position 0 0.31 -0.62
TP_L2_00227.Mother TES_L2
TP_L2_00227.Visibility 0

TES_Pixel_L2.Copy TP_L2_00228
TP_L2_00228.Position 0 0.31 -0.465
TP_L2_00228.Mother TES_L2
TP_L2_00228.Visibility 0

TES_Pixel_L2.Copy TP_L2_00229
TP_L2_00229.Position 0 0.31 -0.31
TP_L2_00229.Mother TES_L2
TP_L2_00229.Visibility 0

TES_Pixel_L2.Copy TP_L2_00230
TP_L2_00230.Position 0 0.31 -0.155
TP_L2_00230.Mother TES_L2
TP_L2_00230.Visibility 0

TES_Pixel_L2.Copy TP_L2_00231
TP_L2_00231.Position 0 0.31 0
TP_L2_00231.Mother TES_L2
TP_L2_00231.Visibility 0

TES_Pixel_L2.Copy TP_L2_00232
TP_L2_00232.Position 0 0.31 0.155
TP_L2_00232.Mother TES_L2
TP_L2_00232.Visibility 0

TES_Pixel_L2.Copy TP_L2_00233
TP_L2_00233.Position 0 0.31 0.31
TP_L2_00233.Mother TES_L2
TP_L2_00233.Visibility 0

TES_Pixel_L2.Copy TP_L2_00234
TP_L2_00234.Position 0 0.31 0.465
TP_L2_00234.Mother TES_L2
TP_L2_00234.Visibility 0

TES_Pixel_L2.Copy TP_L2_00235
TP_L2_00235.Position 0 0.31 0.62
TP_L2_00235.Mother TES_L2
TP_L2_00235.Visibility 0

TES_Pixel_L2.Copy TP_L2_00236
TP_L2_00236.Position 0 0.31 0.775
TP_L2_00236.Mother TES_L2
TP_L2_00236.Visibility 0

TES_Pixel_L2.Copy TP_L2_00237
TP_L2_00237.Position 0 0.31 0.93
TP_L2_00237.Mother TES_L2
TP_L2_00237.Visibility 0

TES_Pixel_L2.Copy TP_L2_00238
TP_L2_00238.Position 0 0.31 1.085
TP_L2_00238.Mother TES_L2
TP_L2_00238.Visibility 0

TES_Pixel_L2.Copy TP_L2_00239
TP_L2_00239.Position 0 0.31 1.24
TP_L2_00239.Mother TES_L2
TP_L2_00239.Visibility 0

TES_Pixel_L2.Copy TP_L2_00240
TP_L2_00240.Position 0 0.31 1.395
TP_L2_00240.Mother TES_L2
TP_L2_00240.Visibility 0

TES_Pixel_L2.Copy TP_L2_00241
TP_L2_00241.Position 0 0.31 1.55
TP_L2_00241.Mother TES_L2
TP_L2_00241.Visibility 0

TES_Pixel_L2.Copy TP_L2_00242
TP_L2_00242.Position 0 0.465 -1.55
TP_L2_00242.Mother TES_L2
TP_L2_00242.Visibility 0

TES_Pixel_L2.Copy TP_L2_00243
TP_L2_00243.Position 0 0.465 -1.395
TP_L2_00243.Mother TES_L2
TP_L2_00243.Visibility 0

TES_Pixel_L2.Copy TP_L2_00244
TP_L2_00244.Position 0 0.465 -1.24
TP_L2_00244.Mother TES_L2
TP_L2_00244.Visibility 0

TES_Pixel_L2.Copy TP_L2_00245
TP_L2_00245.Position 0 0.465 -1.085
TP_L2_00245.Mother TES_L2
TP_L2_00245.Visibility 0

TES_Pixel_L2.Copy TP_L2_00246
TP_L2_00246.Position 0 0.465 -0.93
TP_L2_00246.Mother TES_L2
TP_L2_00246.Visibility 0

TES_Pixel_L2.Copy TP_L2_00247
TP_L2_00247.Position 0 0.465 -0.775
TP_L2_00247.Mother TES_L2
TP_L2_00247.Visibility 0

TES_Pixel_L2.Copy TP_L2_00248
TP_L2_00248.Position 0 0.465 -0.62
TP_L2_00248.Mother TES_L2
TP_L2_00248.Visibility 0

TES_Pixel_L2.Copy TP_L2_00249
TP_L2_00249.Position 0 0.465 -0.465
TP_L2_00249.Mother TES_L2
TP_L2_00249.Visibility 0

TES_Pixel_L2.Copy TP_L2_00250
TP_L2_00250.Position 0 0.465 -0.31
TP_L2_00250.Mother TES_L2
TP_L2_00250.Visibility 0

TES_Pixel_L2.Copy TP_L2_00251
TP_L2_00251.Position 0 0.465 -0.155
TP_L2_00251.Mother TES_L2
TP_L2_00251.Visibility 0

TES_Pixel_L2.Copy TP_L2_00252
TP_L2_00252.Position 0 0.465 0
TP_L2_00252.Mother TES_L2
TP_L2_00252.Visibility 0

TES_Pixel_L2.Copy TP_L2_00253
TP_L2_00253.Position 0 0.465 0.155
TP_L2_00253.Mother TES_L2
TP_L2_00253.Visibility 0

TES_Pixel_L2.Copy TP_L2_00254
TP_L2_00254.Position 0 0.465 0.31
TP_L2_00254.Mother TES_L2
TP_L2_00254.Visibility 0

TES_Pixel_L2.Copy TP_L2_00255
TP_L2_00255.Position 0 0.465 0.465
TP_L2_00255.Mother TES_L2
TP_L2_00255.Visibility 0

TES_Pixel_L2.Copy TP_L2_00256
TP_L2_00256.Position 0 0.465 0.62
TP_L2_00256.Mother TES_L2
TP_L2_00256.Visibility 0

TES_Pixel_L2.Copy TP_L2_00257
TP_L2_00257.Position 0 0.465 0.775
TP_L2_00257.Mother TES_L2
TP_L2_00257.Visibility 0

TES_Pixel_L2.Copy TP_L2_00258
TP_L2_00258.Position 0 0.465 0.93
TP_L2_00258.Mother TES_L2
TP_L2_00258.Visibility 0

TES_Pixel_L2.Copy TP_L2_00259
TP_L2_00259.Position 0 0.465 1.085
TP_L2_00259.Mother TES_L2
TP_L2_00259.Visibility 0

TES_Pixel_L2.Copy TP_L2_00260
TP_L2_00260.Position 0 0.465 1.24
TP_L2_00260.Mother TES_L2
TP_L2_00260.Visibility 0

TES_Pixel_L2.Copy TP_L2_00261
TP_L2_00261.Position 0 0.465 1.395
TP_L2_00261.Mother TES_L2
TP_L2_00261.Visibility 0

TES_Pixel_L2.Copy TP_L2_00262
TP_L2_00262.Position 0 0.465 1.55
TP_L2_00262.Mother TES_L2
TP_L2_00262.Visibility 0

TES_Pixel_L2.Copy TP_L2_00263
TP_L2_00263.Position 0 0.62 -1.55
TP_L2_00263.Mother TES_L2
TP_L2_00263.Visibility 0

TES_Pixel_L2.Copy TP_L2_00264
TP_L2_00264.Position 0 0.62 -1.395
TP_L2_00264.Mother TES_L2
TP_L2_00264.Visibility 0

TES_Pixel_L2.Copy TP_L2_00265
TP_L2_00265.Position 0 0.62 -1.24
TP_L2_00265.Mother TES_L2
TP_L2_00265.Visibility 0

TES_Pixel_L2.Copy TP_L2_00266
TP_L2_00266.Position 0 0.62 -1.085
TP_L2_00266.Mother TES_L2
TP_L2_00266.Visibility 0

TES_Pixel_L2.Copy TP_L2_00267
TP_L2_00267.Position 0 0.62 -0.93
TP_L2_00267.Mother TES_L2
TP_L2_00267.Visibility 0

TES_Pixel_L2.Copy TP_L2_00268
TP_L2_00268.Position 0 0.62 -0.775
TP_L2_00268.Mother TES_L2
TP_L2_00268.Visibility 0

TES_Pixel_L2.Copy TP_L2_00269
TP_L2_00269.Position 0 0.62 -0.62
TP_L2_00269.Mother TES_L2
TP_L2_00269.Visibility 0

TES_Pixel_L2.Copy TP_L2_00270
TP_L2_00270.Position 0 0.62 -0.465
TP_L2_00270.Mother TES_L2
TP_L2_00270.Visibility 0

TES_Pixel_L2.Copy TP_L2_00271
TP_L2_00271.Position 0 0.62 -0.31
TP_L2_00271.Mother TES_L2
TP_L2_00271.Visibility 0

TES_Pixel_L2.Copy TP_L2_00272
TP_L2_00272.Position 0 0.62 -0.155
TP_L2_00272.Mother TES_L2
TP_L2_00272.Visibility 0

TES_Pixel_L2.Copy TP_L2_00273
TP_L2_00273.Position 0 0.62 0
TP_L2_00273.Mother TES_L2
TP_L2_00273.Visibility 0

TES_Pixel_L2.Copy TP_L2_00274
TP_L2_00274.Position 0 0.62 0.155
TP_L2_00274.Mother TES_L2
TP_L2_00274.Visibility 0

TES_Pixel_L2.Copy TP_L2_00275
TP_L2_00275.Position 0 0.62 0.31
TP_L2_00275.Mother TES_L2
TP_L2_00275.Visibility 0

TES_Pixel_L2.Copy TP_L2_00276
TP_L2_00276.Position 0 0.62 0.465
TP_L2_00276.Mother TES_L2
TP_L2_00276.Visibility 0

TES_Pixel_L2.Copy TP_L2_00277
TP_L2_00277.Position 0 0.62 0.62
TP_L2_00277.Mother TES_L2
TP_L2_00277.Visibility 0

TES_Pixel_L2.Copy TP_L2_00278
TP_L2_00278.Position 0 0.62 0.775
TP_L2_00278.Mother TES_L2
TP_L2_00278.Visibility 0

TES_Pixel_L2.Copy TP_L2_00279
TP_L2_00279.Position 0 0.62 0.93
TP_L2_00279.Mother TES_L2
TP_L2_00279.Visibility 0

TES_Pixel_L2.Copy TP_L2_00280
TP_L2_00280.Position 0 0.62 1.085
TP_L2_00280.Mother TES_L2
TP_L2_00280.Visibility 0

TES_Pixel_L2.Copy TP_L2_00281
TP_L2_00281.Position 0 0.62 1.24
TP_L2_00281.Mother TES_L2
TP_L2_00281.Visibility 0

TES_Pixel_L2.Copy TP_L2_00282
TP_L2_00282.Position 0 0.62 1.395
TP_L2_00282.Mother TES_L2
TP_L2_00282.Visibility 0

TES_Pixel_L2.Copy TP_L2_00283
TP_L2_00283.Position 0 0.62 1.55
TP_L2_00283.Mother TES_L2
TP_L2_00283.Visibility 0

TES_Pixel_L2.Copy TP_L2_00284
TP_L2_00284.Position 0 0.775 -1.395
TP_L2_00284.Mother TES_L2
TP_L2_00284.Visibility 0

TES_Pixel_L2.Copy TP_L2_00285
TP_L2_00285.Position 0 0.775 -1.24
TP_L2_00285.Mother TES_L2
TP_L2_00285.Visibility 0

TES_Pixel_L2.Copy TP_L2_00286
TP_L2_00286.Position 0 0.775 -1.085
TP_L2_00286.Mother TES_L2
TP_L2_00286.Visibility 0

TES_Pixel_L2.Copy TP_L2_00287
TP_L2_00287.Position 0 0.775 -0.93
TP_L2_00287.Mother TES_L2
TP_L2_00287.Visibility 0

TES_Pixel_L2.Copy TP_L2_00288
TP_L2_00288.Position 0 0.775 -0.775
TP_L2_00288.Mother TES_L2
TP_L2_00288.Visibility 0

TES_Pixel_L2.Copy TP_L2_00289
TP_L2_00289.Position 0 0.775 -0.62
TP_L2_00289.Mother TES_L2
TP_L2_00289.Visibility 0

TES_Pixel_L2.Copy TP_L2_00290
TP_L2_00290.Position 0 0.775 -0.465
TP_L2_00290.Mother TES_L2
TP_L2_00290.Visibility 0

TES_Pixel_L2.Copy TP_L2_00291
TP_L2_00291.Position 0 0.775 -0.31
TP_L2_00291.Mother TES_L2
TP_L2_00291.Visibility 0

TES_Pixel_L2.Copy TP_L2_00292
TP_L2_00292.Position 0 0.775 -0.155
TP_L2_00292.Mother TES_L2
TP_L2_00292.Visibility 0

TES_Pixel_L2.Copy TP_L2_00293
TP_L2_00293.Position 0 0.775 0
TP_L2_00293.Mother TES_L2
TP_L2_00293.Visibility 0

TES_Pixel_L2.Copy TP_L2_00294
TP_L2_00294.Position 0 0.775 0.155
TP_L2_00294.Mother TES_L2
TP_L2_00294.Visibility 0

TES_Pixel_L2.Copy TP_L2_00295
TP_L2_00295.Position 0 0.775 0.31
TP_L2_00295.Mother TES_L2
TP_L2_00295.Visibility 0

TES_Pixel_L2.Copy TP_L2_00296
TP_L2_00296.Position 0 0.775 0.465
TP_L2_00296.Mother TES_L2
TP_L2_00296.Visibility 0

TES_Pixel_L2.Copy TP_L2_00297
TP_L2_00297.Position 0 0.775 0.62
TP_L2_00297.Mother TES_L2
TP_L2_00297.Visibility 0

TES_Pixel_L2.Copy TP_L2_00298
TP_L2_00298.Position 0 0.775 0.775
TP_L2_00298.Mother TES_L2
TP_L2_00298.Visibility 0

TES_Pixel_L2.Copy TP_L2_00299
TP_L2_00299.Position 0 0.775 0.93
TP_L2_00299.Mother TES_L2
TP_L2_00299.Visibility 0

TES_Pixel_L2.Copy TP_L2_00300
TP_L2_00300.Position 0 0.775 1.085
TP_L2_00300.Mother TES_L2
TP_L2_00300.Visibility 0

TES_Pixel_L2.Copy TP_L2_00301
TP_L2_00301.Position 0 0.775 1.24
TP_L2_00301.Mother TES_L2
TP_L2_00301.Visibility 0

TES_Pixel_L2.Copy TP_L2_00302
TP_L2_00302.Position 0 0.775 1.395
TP_L2_00302.Mother TES_L2
TP_L2_00302.Visibility 0

TES_Pixel_L2.Copy TP_L2_00303
TP_L2_00303.Position 0 0.93 -1.395
TP_L2_00303.Mother TES_L2
TP_L2_00303.Visibility 0

TES_Pixel_L2.Copy TP_L2_00304
TP_L2_00304.Position 0 0.93 -1.24
TP_L2_00304.Mother TES_L2
TP_L2_00304.Visibility 0

TES_Pixel_L2.Copy TP_L2_00305
TP_L2_00305.Position 0 0.93 -1.085
TP_L2_00305.Mother TES_L2
TP_L2_00305.Visibility 0

TES_Pixel_L2.Copy TP_L2_00306
TP_L2_00306.Position 0 0.93 -0.93
TP_L2_00306.Mother TES_L2
TP_L2_00306.Visibility 0

TES_Pixel_L2.Copy TP_L2_00307
TP_L2_00307.Position 0 0.93 -0.775
TP_L2_00307.Mother TES_L2
TP_L2_00307.Visibility 0

TES_Pixel_L2.Copy TP_L2_00308
TP_L2_00308.Position 0 0.93 -0.62
TP_L2_00308.Mother TES_L2
TP_L2_00308.Visibility 0

TES_Pixel_L2.Copy TP_L2_00309
TP_L2_00309.Position 0 0.93 -0.465
TP_L2_00309.Mother TES_L2
TP_L2_00309.Visibility 0

TES_Pixel_L2.Copy TP_L2_00310
TP_L2_00310.Position 0 0.93 -0.31
TP_L2_00310.Mother TES_L2
TP_L2_00310.Visibility 0

TES_Pixel_L2.Copy TP_L2_00311
TP_L2_00311.Position 0 0.93 -0.155
TP_L2_00311.Mother TES_L2
TP_L2_00311.Visibility 0

TES_Pixel_L2.Copy TP_L2_00312
TP_L2_00312.Position 0 0.93 0
TP_L2_00312.Mother TES_L2
TP_L2_00312.Visibility 0

TES_Pixel_L2.Copy TP_L2_00313
TP_L2_00313.Position 0 0.93 0.155
TP_L2_00313.Mother TES_L2
TP_L2_00313.Visibility 0

TES_Pixel_L2.Copy TP_L2_00314
TP_L2_00314.Position 0 0.93 0.31
TP_L2_00314.Mother TES_L2
TP_L2_00314.Visibility 0

TES_Pixel_L2.Copy TP_L2_00315
TP_L2_00315.Position 0 0.93 0.465
TP_L2_00315.Mother TES_L2
TP_L2_00315.Visibility 0

TES_Pixel_L2.Copy TP_L2_00316
TP_L2_00316.Position 0 0.93 0.62
TP_L2_00316.Mother TES_L2
TP_L2_00316.Visibility 0

TES_Pixel_L2.Copy TP_L2_00317
TP_L2_00317.Position 0 0.93 0.775
TP_L2_00317.Mother TES_L2
TP_L2_00317.Visibility 0

TES_Pixel_L2.Copy TP_L2_00318
TP_L2_00318.Position 0 0.93 0.93
TP_L2_00318.Mother TES_L2
TP_L2_00318.Visibility 0

TES_Pixel_L2.Copy TP_L2_00319
TP_L2_00319.Position 0 0.93 1.085
TP_L2_00319.Mother TES_L2
TP_L2_00319.Visibility 0

TES_Pixel_L2.Copy TP_L2_00320
TP_L2_00320.Position 0 0.93 1.24
TP_L2_00320.Mother TES_L2
TP_L2_00320.Visibility 0

TES_Pixel_L2.Copy TP_L2_00321
TP_L2_00321.Position 0 0.93 1.395
TP_L2_00321.Mother TES_L2
TP_L2_00321.Visibility 0

TES_Pixel_L2.Copy TP_L2_00322
TP_L2_00322.Position 0 1.085 -1.24
TP_L2_00322.Mother TES_L2
TP_L2_00322.Visibility 0

TES_Pixel_L2.Copy TP_L2_00323
TP_L2_00323.Position 0 1.085 -1.085
TP_L2_00323.Mother TES_L2
TP_L2_00323.Visibility 0

TES_Pixel_L2.Copy TP_L2_00324
TP_L2_00324.Position 0 1.085 -0.93
TP_L2_00324.Mother TES_L2
TP_L2_00324.Visibility 0

TES_Pixel_L2.Copy TP_L2_00325
TP_L2_00325.Position 0 1.085 -0.775
TP_L2_00325.Mother TES_L2
TP_L2_00325.Visibility 0

TES_Pixel_L2.Copy TP_L2_00326
TP_L2_00326.Position 0 1.085 -0.62
TP_L2_00326.Mother TES_L2
TP_L2_00326.Visibility 0

TES_Pixel_L2.Copy TP_L2_00327
TP_L2_00327.Position 0 1.085 -0.465
TP_L2_00327.Mother TES_L2
TP_L2_00327.Visibility 0

TES_Pixel_L2.Copy TP_L2_00328
TP_L2_00328.Position 0 1.085 -0.31
TP_L2_00328.Mother TES_L2
TP_L2_00328.Visibility 0

TES_Pixel_L2.Copy TP_L2_00329
TP_L2_00329.Position 0 1.085 -0.155
TP_L2_00329.Mother TES_L2
TP_L2_00329.Visibility 0

TES_Pixel_L2.Copy TP_L2_00330
TP_L2_00330.Position 0 1.085 0
TP_L2_00330.Mother TES_L2
TP_L2_00330.Visibility 0

TES_Pixel_L2.Copy TP_L2_00331
TP_L2_00331.Position 0 1.085 0.155
TP_L2_00331.Mother TES_L2
TP_L2_00331.Visibility 0

TES_Pixel_L2.Copy TP_L2_00332
TP_L2_00332.Position 0 1.085 0.31
TP_L2_00332.Mother TES_L2
TP_L2_00332.Visibility 0

TES_Pixel_L2.Copy TP_L2_00333
TP_L2_00333.Position 0 1.085 0.465
TP_L2_00333.Mother TES_L2
TP_L2_00333.Visibility 0

TES_Pixel_L2.Copy TP_L2_00334
TP_L2_00334.Position 0 1.085 0.62
TP_L2_00334.Mother TES_L2
TP_L2_00334.Visibility 0

TES_Pixel_L2.Copy TP_L2_00335
TP_L2_00335.Position 0 1.085 0.775
TP_L2_00335.Mother TES_L2
TP_L2_00335.Visibility 0

TES_Pixel_L2.Copy TP_L2_00336
TP_L2_00336.Position 0 1.085 0.93
TP_L2_00336.Mother TES_L2
TP_L2_00336.Visibility 0

TES_Pixel_L2.Copy TP_L2_00337
TP_L2_00337.Position 0 1.085 1.085
TP_L2_00337.Mother TES_L2
TP_L2_00337.Visibility 0

TES_Pixel_L2.Copy TP_L2_00338
TP_L2_00338.Position 0 1.085 1.24
TP_L2_00338.Mother TES_L2
TP_L2_00338.Visibility 0

TES_Pixel_L2.Copy TP_L2_00339
TP_L2_00339.Position 0 1.24 -1.085
TP_L2_00339.Mother TES_L2
TP_L2_00339.Visibility 0

TES_Pixel_L2.Copy TP_L2_00340
TP_L2_00340.Position 0 1.24 -0.93
TP_L2_00340.Mother TES_L2
TP_L2_00340.Visibility 0

TES_Pixel_L2.Copy TP_L2_00341
TP_L2_00341.Position 0 1.24 -0.775
TP_L2_00341.Mother TES_L2
TP_L2_00341.Visibility 0

TES_Pixel_L2.Copy TP_L2_00342
TP_L2_00342.Position 0 1.24 -0.62
TP_L2_00342.Mother TES_L2
TP_L2_00342.Visibility 0

TES_Pixel_L2.Copy TP_L2_00343
TP_L2_00343.Position 0 1.24 -0.465
TP_L2_00343.Mother TES_L2
TP_L2_00343.Visibility 0

TES_Pixel_L2.Copy TP_L2_00344
TP_L2_00344.Position 0 1.24 -0.31
TP_L2_00344.Mother TES_L2
TP_L2_00344.Visibility 0

TES_Pixel_L2.Copy TP_L2_00345
TP_L2_00345.Position 0 1.24 -0.155
TP_L2_00345.Mother TES_L2
TP_L2_00345.Visibility 0

TES_Pixel_L2.Copy TP_L2_00346
TP_L2_00346.Position 0 1.24 0
TP_L2_00346.Mother TES_L2
TP_L2_00346.Visibility 0

TES_Pixel_L2.Copy TP_L2_00347
TP_L2_00347.Position 0 1.24 0.155
TP_L2_00347.Mother TES_L2
TP_L2_00347.Visibility 0

TES_Pixel_L2.Copy TP_L2_00348
TP_L2_00348.Position 0 1.24 0.31
TP_L2_00348.Mother TES_L2
TP_L2_00348.Visibility 0

TES_Pixel_L2.Copy TP_L2_00349
TP_L2_00349.Position 0 1.24 0.465
TP_L2_00349.Mother TES_L2
TP_L2_00349.Visibility 0

TES_Pixel_L2.Copy TP_L2_00350
TP_L2_00350.Position 0 1.24 0.62
TP_L2_00350.Mother TES_L2
TP_L2_00350.Visibility 0

TES_Pixel_L2.Copy TP_L2_00351
TP_L2_00351.Position 0 1.24 0.775
TP_L2_00351.Mother TES_L2
TP_L2_00351.Visibility 0

TES_Pixel_L2.Copy TP_L2_00352
TP_L2_00352.Position 0 1.24 0.93
TP_L2_00352.Mother TES_L2
TP_L2_00352.Visibility 0

TES_Pixel_L2.Copy TP_L2_00353
TP_L2_00353.Position 0 1.24 1.085
TP_L2_00353.Mother TES_L2
TP_L2_00353.Visibility 0

TES_Pixel_L2.Copy TP_L2_00354
TP_L2_00354.Position 0 1.395 -0.93
TP_L2_00354.Mother TES_L2
TP_L2_00354.Visibility 0

TES_Pixel_L2.Copy TP_L2_00355
TP_L2_00355.Position 0 1.395 -0.775
TP_L2_00355.Mother TES_L2
TP_L2_00355.Visibility 0

TES_Pixel_L2.Copy TP_L2_00356
TP_L2_00356.Position 0 1.395 -0.62
TP_L2_00356.Mother TES_L2
TP_L2_00356.Visibility 0

TES_Pixel_L2.Copy TP_L2_00357
TP_L2_00357.Position 0 1.395 -0.465
TP_L2_00357.Mother TES_L2
TP_L2_00357.Visibility 0

TES_Pixel_L2.Copy TP_L2_00358
TP_L2_00358.Position 0 1.395 -0.31
TP_L2_00358.Mother TES_L2
TP_L2_00358.Visibility 0

TES_Pixel_L2.Copy TP_L2_00359
TP_L2_00359.Position 0 1.395 -0.155
TP_L2_00359.Mother TES_L2
TP_L2_00359.Visibility 0

TES_Pixel_L2.Copy TP_L2_00360
TP_L2_00360.Position 0 1.395 0
TP_L2_00360.Mother TES_L2
TP_L2_00360.Visibility 0

TES_Pixel_L2.Copy TP_L2_00361
TP_L2_00361.Position 0 1.395 0.155
TP_L2_00361.Mother TES_L2
TP_L2_00361.Visibility 0

TES_Pixel_L2.Copy TP_L2_00362
TP_L2_00362.Position 0 1.395 0.31
TP_L2_00362.Mother TES_L2
TP_L2_00362.Visibility 0

TES_Pixel_L2.Copy TP_L2_00363
TP_L2_00363.Position 0 1.395 0.465
TP_L2_00363.Mother TES_L2
TP_L2_00363.Visibility 0

TES_Pixel_L2.Copy TP_L2_00364
TP_L2_00364.Position 0 1.395 0.62
TP_L2_00364.Mother TES_L2
TP_L2_00364.Visibility 0

TES_Pixel_L2.Copy TP_L2_00365
TP_L2_00365.Position 0 1.395 0.775
TP_L2_00365.Mother TES_L2
TP_L2_00365.Visibility 0

TES_Pixel_L2.Copy TP_L2_00366
TP_L2_00366.Position 0 1.395 0.93
TP_L2_00366.Mother TES_L2
TP_L2_00366.Visibility 0

TES_Pixel_L2.Copy TP_L2_00367
TP_L2_00367.Position 0 1.55 -0.62
TP_L2_00367.Mother TES_L2
TP_L2_00367.Visibility 0

TES_Pixel_L2.Copy TP_L2_00368
TP_L2_00368.Position 0 1.55 -0.465
TP_L2_00368.Mother TES_L2
TP_L2_00368.Visibility 0

TES_Pixel_L2.Copy TP_L2_00369
TP_L2_00369.Position 0 1.55 -0.31
TP_L2_00369.Mother TES_L2
TP_L2_00369.Visibility 0

TES_Pixel_L2.Copy TP_L2_00370
TP_L2_00370.Position 0 1.55 -0.155
TP_L2_00370.Mother TES_L2
TP_L2_00370.Visibility 0

TES_Pixel_L2.Copy TP_L2_00371
TP_L2_00371.Position 0 1.55 0
TP_L2_00371.Mother TES_L2
TP_L2_00371.Visibility 0

TES_Pixel_L2.Copy TP_L2_00372
TP_L2_00372.Position 0 1.55 0.155
TP_L2_00372.Mother TES_L2
TP_L2_00372.Visibility 0

TES_Pixel_L2.Copy TP_L2_00373
TP_L2_00373.Position 0 1.55 0.31
TP_L2_00373.Mother TES_L2
TP_L2_00373.Visibility 0

TES_Pixel_L2.Copy TP_L2_00374
TP_L2_00374.Position 0 1.55 0.465
TP_L2_00374.Mother TES_L2
TP_L2_00374.Visibility 0

TES_Pixel_L2.Copy TP_L2_00375
TP_L2_00375.Position 0 1.55 0.62
TP_L2_00375.Mother TES_L2
TP_L2_00375.Visibility 0

// Volume TES_Pixel_L3; material=Ta
Volume TES_Pixel_L3
TES_Pixel_L3.Material Ta
TES_Pixel_L3.Visibility 1
TES_Pixel_L3.Shape BRIK 0.15 0.075 0.075

// Volume TES_L3; material=Vacuum
Volume TES_L3
TES_L3.Material Vacuum
TES_L3.Visibility 0
TES_L3.Shape BRIK 0.15 1.8 1.8

TES_L3.Position -34.95 0 -2.8
TES_L3.Mother InstrumentFrame

TES_Pixel_L3.Copy TP_L3_00000
TP_L3_00000.Position 0 -1.705 0
TP_L3_00000.Mother TES_L3
TP_L3_00000.Visibility 0

TES_Pixel_L3.Copy TP_L3_00001
TP_L3_00001.Position 0 -1.55 -0.62
TP_L3_00001.Mother TES_L3
TP_L3_00001.Visibility 0

TES_Pixel_L3.Copy TP_L3_00002
TP_L3_00002.Position 0 -1.55 -0.465
TP_L3_00002.Mother TES_L3
TP_L3_00002.Visibility 0

TES_Pixel_L3.Copy TP_L3_00003
TP_L3_00003.Position 0 -1.55 -0.31
TP_L3_00003.Mother TES_L3
TP_L3_00003.Visibility 0

TES_Pixel_L3.Copy TP_L3_00004
TP_L3_00004.Position 0 -1.55 -0.155
TP_L3_00004.Mother TES_L3
TP_L3_00004.Visibility 0

TES_Pixel_L3.Copy TP_L3_00005
TP_L3_00005.Position 0 -1.55 0
TP_L3_00005.Mother TES_L3
TP_L3_00005.Visibility 0

TES_Pixel_L3.Copy TP_L3_00006
TP_L3_00006.Position 0 -1.55 0.155
TP_L3_00006.Mother TES_L3
TP_L3_00006.Visibility 0

TES_Pixel_L3.Copy TP_L3_00007
TP_L3_00007.Position 0 -1.55 0.31
TP_L3_00007.Mother TES_L3
TP_L3_00007.Visibility 0

TES_Pixel_L3.Copy TP_L3_00008
TP_L3_00008.Position 0 -1.55 0.465
TP_L3_00008.Mother TES_L3
TP_L3_00008.Visibility 0

TES_Pixel_L3.Copy TP_L3_00009
TP_L3_00009.Position 0 -1.55 0.62
TP_L3_00009.Mother TES_L3
TP_L3_00009.Visibility 0

TES_Pixel_L3.Copy TP_L3_00010
TP_L3_00010.Position 0 -1.395 -0.93
TP_L3_00010.Mother TES_L3
TP_L3_00010.Visibility 0

TES_Pixel_L3.Copy TP_L3_00011
TP_L3_00011.Position 0 -1.395 -0.775
TP_L3_00011.Mother TES_L3
TP_L3_00011.Visibility 0

TES_Pixel_L3.Copy TP_L3_00012
TP_L3_00012.Position 0 -1.395 -0.62
TP_L3_00012.Mother TES_L3
TP_L3_00012.Visibility 0

TES_Pixel_L3.Copy TP_L3_00013
TP_L3_00013.Position 0 -1.395 -0.465
TP_L3_00013.Mother TES_L3
TP_L3_00013.Visibility 0

TES_Pixel_L3.Copy TP_L3_00014
TP_L3_00014.Position 0 -1.395 -0.31
TP_L3_00014.Mother TES_L3
TP_L3_00014.Visibility 0

TES_Pixel_L3.Copy TP_L3_00015
TP_L3_00015.Position 0 -1.395 -0.155
TP_L3_00015.Mother TES_L3
TP_L3_00015.Visibility 0

TES_Pixel_L3.Copy TP_L3_00016
TP_L3_00016.Position 0 -1.395 0
TP_L3_00016.Mother TES_L3
TP_L3_00016.Visibility 0

TES_Pixel_L3.Copy TP_L3_00017
TP_L3_00017.Position 0 -1.395 0.155
TP_L3_00017.Mother TES_L3
TP_L3_00017.Visibility 0

TES_Pixel_L3.Copy TP_L3_00018
TP_L3_00018.Position 0 -1.395 0.31
TP_L3_00018.Mother TES_L3
TP_L3_00018.Visibility 0

TES_Pixel_L3.Copy TP_L3_00019
TP_L3_00019.Position 0 -1.395 0.465
TP_L3_00019.Mother TES_L3
TP_L3_00019.Visibility 0

TES_Pixel_L3.Copy TP_L3_00020
TP_L3_00020.Position 0 -1.395 0.62
TP_L3_00020.Mother TES_L3
TP_L3_00020.Visibility 0

TES_Pixel_L3.Copy TP_L3_00021
TP_L3_00021.Position 0 -1.395 0.775
TP_L3_00021.Mother TES_L3
TP_L3_00021.Visibility 0

TES_Pixel_L3.Copy TP_L3_00022
TP_L3_00022.Position 0 -1.395 0.93
TP_L3_00022.Mother TES_L3
TP_L3_00022.Visibility 0

TES_Pixel_L3.Copy TP_L3_00023
TP_L3_00023.Position 0 -1.24 -1.085
TP_L3_00023.Mother TES_L3
TP_L3_00023.Visibility 0

TES_Pixel_L3.Copy TP_L3_00024
TP_L3_00024.Position 0 -1.24 -0.93
TP_L3_00024.Mother TES_L3
TP_L3_00024.Visibility 0

TES_Pixel_L3.Copy TP_L3_00025
TP_L3_00025.Position 0 -1.24 -0.775
TP_L3_00025.Mother TES_L3
TP_L3_00025.Visibility 0

TES_Pixel_L3.Copy TP_L3_00026
TP_L3_00026.Position 0 -1.24 -0.62
TP_L3_00026.Mother TES_L3
TP_L3_00026.Visibility 0

TES_Pixel_L3.Copy TP_L3_00027
TP_L3_00027.Position 0 -1.24 -0.465
TP_L3_00027.Mother TES_L3
TP_L3_00027.Visibility 0

TES_Pixel_L3.Copy TP_L3_00028
TP_L3_00028.Position 0 -1.24 -0.31
TP_L3_00028.Mother TES_L3
TP_L3_00028.Visibility 0

TES_Pixel_L3.Copy TP_L3_00029
TP_L3_00029.Position 0 -1.24 -0.155
TP_L3_00029.Mother TES_L3
TP_L3_00029.Visibility 0

TES_Pixel_L3.Copy TP_L3_00030
TP_L3_00030.Position 0 -1.24 0
TP_L3_00030.Mother TES_L3
TP_L3_00030.Visibility 0

TES_Pixel_L3.Copy TP_L3_00031
TP_L3_00031.Position 0 -1.24 0.155
TP_L3_00031.Mother TES_L3
TP_L3_00031.Visibility 0

TES_Pixel_L3.Copy TP_L3_00032
TP_L3_00032.Position 0 -1.24 0.31
TP_L3_00032.Mother TES_L3
TP_L3_00032.Visibility 0

TES_Pixel_L3.Copy TP_L3_00033
TP_L3_00033.Position 0 -1.24 0.465
TP_L3_00033.Mother TES_L3
TP_L3_00033.Visibility 0

TES_Pixel_L3.Copy TP_L3_00034
TP_L3_00034.Position 0 -1.24 0.62
TP_L3_00034.Mother TES_L3
TP_L3_00034.Visibility 0

TES_Pixel_L3.Copy TP_L3_00035
TP_L3_00035.Position 0 -1.24 0.775
TP_L3_00035.Mother TES_L3
TP_L3_00035.Visibility 0

TES_Pixel_L3.Copy TP_L3_00036
TP_L3_00036.Position 0 -1.24 0.93
TP_L3_00036.Mother TES_L3
TP_L3_00036.Visibility 0

TES_Pixel_L3.Copy TP_L3_00037
TP_L3_00037.Position 0 -1.24 1.085
TP_L3_00037.Mother TES_L3
TP_L3_00037.Visibility 0

TES_Pixel_L3.Copy TP_L3_00038
TP_L3_00038.Position 0 -1.085 -1.24
TP_L3_00038.Mother TES_L3
TP_L3_00038.Visibility 0

TES_Pixel_L3.Copy TP_L3_00039
TP_L3_00039.Position 0 -1.085 -1.085
TP_L3_00039.Mother TES_L3
TP_L3_00039.Visibility 0

TES_Pixel_L3.Copy TP_L3_00040
TP_L3_00040.Position 0 -1.085 -0.93
TP_L3_00040.Mother TES_L3
TP_L3_00040.Visibility 0

TES_Pixel_L3.Copy TP_L3_00041
TP_L3_00041.Position 0 -1.085 -0.775
TP_L3_00041.Mother TES_L3
TP_L3_00041.Visibility 0

TES_Pixel_L3.Copy TP_L3_00042
TP_L3_00042.Position 0 -1.085 -0.62
TP_L3_00042.Mother TES_L3
TP_L3_00042.Visibility 0

TES_Pixel_L3.Copy TP_L3_00043
TP_L3_00043.Position 0 -1.085 -0.465
TP_L3_00043.Mother TES_L3
TP_L3_00043.Visibility 0

TES_Pixel_L3.Copy TP_L3_00044
TP_L3_00044.Position 0 -1.085 -0.31
TP_L3_00044.Mother TES_L3
TP_L3_00044.Visibility 0

TES_Pixel_L3.Copy TP_L3_00045
TP_L3_00045.Position 0 -1.085 -0.155
TP_L3_00045.Mother TES_L3
TP_L3_00045.Visibility 0

TES_Pixel_L3.Copy TP_L3_00046
TP_L3_00046.Position 0 -1.085 0
TP_L3_00046.Mother TES_L3
TP_L3_00046.Visibility 0

TES_Pixel_L3.Copy TP_L3_00047
TP_L3_00047.Position 0 -1.085 0.155
TP_L3_00047.Mother TES_L3
TP_L3_00047.Visibility 0

TES_Pixel_L3.Copy TP_L3_00048
TP_L3_00048.Position 0 -1.085 0.31
TP_L3_00048.Mother TES_L3
TP_L3_00048.Visibility 0

TES_Pixel_L3.Copy TP_L3_00049
TP_L3_00049.Position 0 -1.085 0.465
TP_L3_00049.Mother TES_L3
TP_L3_00049.Visibility 0

TES_Pixel_L3.Copy TP_L3_00050
TP_L3_00050.Position 0 -1.085 0.62
TP_L3_00050.Mother TES_L3
TP_L3_00050.Visibility 0

TES_Pixel_L3.Copy TP_L3_00051
TP_L3_00051.Position 0 -1.085 0.775
TP_L3_00051.Mother TES_L3
TP_L3_00051.Visibility 0

TES_Pixel_L3.Copy TP_L3_00052
TP_L3_00052.Position 0 -1.085 0.93
TP_L3_00052.Mother TES_L3
TP_L3_00052.Visibility 0

TES_Pixel_L3.Copy TP_L3_00053
TP_L3_00053.Position 0 -1.085 1.085
TP_L3_00053.Mother TES_L3
TP_L3_00053.Visibility 0

TES_Pixel_L3.Copy TP_L3_00054
TP_L3_00054.Position 0 -1.085 1.24
TP_L3_00054.Mother TES_L3
TP_L3_00054.Visibility 0

TES_Pixel_L3.Copy TP_L3_00055
TP_L3_00055.Position 0 -0.93 -1.395
TP_L3_00055.Mother TES_L3
TP_L3_00055.Visibility 0

TES_Pixel_L3.Copy TP_L3_00056
TP_L3_00056.Position 0 -0.93 -1.24
TP_L3_00056.Mother TES_L3
TP_L3_00056.Visibility 0

TES_Pixel_L3.Copy TP_L3_00057
TP_L3_00057.Position 0 -0.93 -1.085
TP_L3_00057.Mother TES_L3
TP_L3_00057.Visibility 0

TES_Pixel_L3.Copy TP_L3_00058
TP_L3_00058.Position 0 -0.93 -0.93
TP_L3_00058.Mother TES_L3
TP_L3_00058.Visibility 0

TES_Pixel_L3.Copy TP_L3_00059
TP_L3_00059.Position 0 -0.93 -0.775
TP_L3_00059.Mother TES_L3
TP_L3_00059.Visibility 0

TES_Pixel_L3.Copy TP_L3_00060
TP_L3_00060.Position 0 -0.93 -0.62
TP_L3_00060.Mother TES_L3
TP_L3_00060.Visibility 0

TES_Pixel_L3.Copy TP_L3_00061
TP_L3_00061.Position 0 -0.93 -0.465
TP_L3_00061.Mother TES_L3
TP_L3_00061.Visibility 0

TES_Pixel_L3.Copy TP_L3_00062
TP_L3_00062.Position 0 -0.93 -0.31
TP_L3_00062.Mother TES_L3
TP_L3_00062.Visibility 0

TES_Pixel_L3.Copy TP_L3_00063
TP_L3_00063.Position 0 -0.93 -0.155
TP_L3_00063.Mother TES_L3
TP_L3_00063.Visibility 0

TES_Pixel_L3.Copy TP_L3_00064
TP_L3_00064.Position 0 -0.93 0
TP_L3_00064.Mother TES_L3
TP_L3_00064.Visibility 0

TES_Pixel_L3.Copy TP_L3_00065
TP_L3_00065.Position 0 -0.93 0.155
TP_L3_00065.Mother TES_L3
TP_L3_00065.Visibility 0

TES_Pixel_L3.Copy TP_L3_00066
TP_L3_00066.Position 0 -0.93 0.31
TP_L3_00066.Mother TES_L3
TP_L3_00066.Visibility 0

TES_Pixel_L3.Copy TP_L3_00067
TP_L3_00067.Position 0 -0.93 0.465
TP_L3_00067.Mother TES_L3
TP_L3_00067.Visibility 0

TES_Pixel_L3.Copy TP_L3_00068
TP_L3_00068.Position 0 -0.93 0.62
TP_L3_00068.Mother TES_L3
TP_L3_00068.Visibility 0

TES_Pixel_L3.Copy TP_L3_00069
TP_L3_00069.Position 0 -0.93 0.775
TP_L3_00069.Mother TES_L3
TP_L3_00069.Visibility 0

TES_Pixel_L3.Copy TP_L3_00070
TP_L3_00070.Position 0 -0.93 0.93
TP_L3_00070.Mother TES_L3
TP_L3_00070.Visibility 0

TES_Pixel_L3.Copy TP_L3_00071
TP_L3_00071.Position 0 -0.93 1.085
TP_L3_00071.Mother TES_L3
TP_L3_00071.Visibility 0

TES_Pixel_L3.Copy TP_L3_00072
TP_L3_00072.Position 0 -0.93 1.24
TP_L3_00072.Mother TES_L3
TP_L3_00072.Visibility 0

TES_Pixel_L3.Copy TP_L3_00073
TP_L3_00073.Position 0 -0.93 1.395
TP_L3_00073.Mother TES_L3
TP_L3_00073.Visibility 0

TES_Pixel_L3.Copy TP_L3_00074
TP_L3_00074.Position 0 -0.775 -1.395
TP_L3_00074.Mother TES_L3
TP_L3_00074.Visibility 0

TES_Pixel_L3.Copy TP_L3_00075
TP_L3_00075.Position 0 -0.775 -1.24
TP_L3_00075.Mother TES_L3
TP_L3_00075.Visibility 0

TES_Pixel_L3.Copy TP_L3_00076
TP_L3_00076.Position 0 -0.775 -1.085
TP_L3_00076.Mother TES_L3
TP_L3_00076.Visibility 0

TES_Pixel_L3.Copy TP_L3_00077
TP_L3_00077.Position 0 -0.775 -0.93
TP_L3_00077.Mother TES_L3
TP_L3_00077.Visibility 0

TES_Pixel_L3.Copy TP_L3_00078
TP_L3_00078.Position 0 -0.775 -0.775
TP_L3_00078.Mother TES_L3
TP_L3_00078.Visibility 0

TES_Pixel_L3.Copy TP_L3_00079
TP_L3_00079.Position 0 -0.775 -0.62
TP_L3_00079.Mother TES_L3
TP_L3_00079.Visibility 0

TES_Pixel_L3.Copy TP_L3_00080
TP_L3_00080.Position 0 -0.775 -0.465
TP_L3_00080.Mother TES_L3
TP_L3_00080.Visibility 0

TES_Pixel_L3.Copy TP_L3_00081
TP_L3_00081.Position 0 -0.775 -0.31
TP_L3_00081.Mother TES_L3
TP_L3_00081.Visibility 0

TES_Pixel_L3.Copy TP_L3_00082
TP_L3_00082.Position 0 -0.775 -0.155
TP_L3_00082.Mother TES_L3
TP_L3_00082.Visibility 0

TES_Pixel_L3.Copy TP_L3_00083
TP_L3_00083.Position 0 -0.775 0
TP_L3_00083.Mother TES_L3
TP_L3_00083.Visibility 0

TES_Pixel_L3.Copy TP_L3_00084
TP_L3_00084.Position 0 -0.775 0.155
TP_L3_00084.Mother TES_L3
TP_L3_00084.Visibility 0

TES_Pixel_L3.Copy TP_L3_00085
TP_L3_00085.Position 0 -0.775 0.31
TP_L3_00085.Mother TES_L3
TP_L3_00085.Visibility 0

TES_Pixel_L3.Copy TP_L3_00086
TP_L3_00086.Position 0 -0.775 0.465
TP_L3_00086.Mother TES_L3
TP_L3_00086.Visibility 0

TES_Pixel_L3.Copy TP_L3_00087
TP_L3_00087.Position 0 -0.775 0.62
TP_L3_00087.Mother TES_L3
TP_L3_00087.Visibility 0

TES_Pixel_L3.Copy TP_L3_00088
TP_L3_00088.Position 0 -0.775 0.775
TP_L3_00088.Mother TES_L3
TP_L3_00088.Visibility 0

TES_Pixel_L3.Copy TP_L3_00089
TP_L3_00089.Position 0 -0.775 0.93
TP_L3_00089.Mother TES_L3
TP_L3_00089.Visibility 0

TES_Pixel_L3.Copy TP_L3_00090
TP_L3_00090.Position 0 -0.775 1.085
TP_L3_00090.Mother TES_L3
TP_L3_00090.Visibility 0

TES_Pixel_L3.Copy TP_L3_00091
TP_L3_00091.Position 0 -0.775 1.24
TP_L3_00091.Mother TES_L3
TP_L3_00091.Visibility 0

TES_Pixel_L3.Copy TP_L3_00092
TP_L3_00092.Position 0 -0.775 1.395
TP_L3_00092.Mother TES_L3
TP_L3_00092.Visibility 0

TES_Pixel_L3.Copy TP_L3_00093
TP_L3_00093.Position 0 -0.62 -1.55
TP_L3_00093.Mother TES_L3
TP_L3_00093.Visibility 0

TES_Pixel_L3.Copy TP_L3_00094
TP_L3_00094.Position 0 -0.62 -1.395
TP_L3_00094.Mother TES_L3
TP_L3_00094.Visibility 0

TES_Pixel_L3.Copy TP_L3_00095
TP_L3_00095.Position 0 -0.62 -1.24
TP_L3_00095.Mother TES_L3
TP_L3_00095.Visibility 0

TES_Pixel_L3.Copy TP_L3_00096
TP_L3_00096.Position 0 -0.62 -1.085
TP_L3_00096.Mother TES_L3
TP_L3_00096.Visibility 0

TES_Pixel_L3.Copy TP_L3_00097
TP_L3_00097.Position 0 -0.62 -0.93
TP_L3_00097.Mother TES_L3
TP_L3_00097.Visibility 0

TES_Pixel_L3.Copy TP_L3_00098
TP_L3_00098.Position 0 -0.62 -0.775
TP_L3_00098.Mother TES_L3
TP_L3_00098.Visibility 0

TES_Pixel_L3.Copy TP_L3_00099
TP_L3_00099.Position 0 -0.62 -0.62
TP_L3_00099.Mother TES_L3
TP_L3_00099.Visibility 0

TES_Pixel_L3.Copy TP_L3_00100
TP_L3_00100.Position 0 -0.62 -0.465
TP_L3_00100.Mother TES_L3
TP_L3_00100.Visibility 0

TES_Pixel_L3.Copy TP_L3_00101
TP_L3_00101.Position 0 -0.62 -0.31
TP_L3_00101.Mother TES_L3
TP_L3_00101.Visibility 0

TES_Pixel_L3.Copy TP_L3_00102
TP_L3_00102.Position 0 -0.62 -0.155
TP_L3_00102.Mother TES_L3
TP_L3_00102.Visibility 0

TES_Pixel_L3.Copy TP_L3_00103
TP_L3_00103.Position 0 -0.62 0
TP_L3_00103.Mother TES_L3
TP_L3_00103.Visibility 0

TES_Pixel_L3.Copy TP_L3_00104
TP_L3_00104.Position 0 -0.62 0.155
TP_L3_00104.Mother TES_L3
TP_L3_00104.Visibility 0

TES_Pixel_L3.Copy TP_L3_00105
TP_L3_00105.Position 0 -0.62 0.31
TP_L3_00105.Mother TES_L3
TP_L3_00105.Visibility 0

TES_Pixel_L3.Copy TP_L3_00106
TP_L3_00106.Position 0 -0.62 0.465
TP_L3_00106.Mother TES_L3
TP_L3_00106.Visibility 0

TES_Pixel_L3.Copy TP_L3_00107
TP_L3_00107.Position 0 -0.62 0.62
TP_L3_00107.Mother TES_L3
TP_L3_00107.Visibility 0

TES_Pixel_L3.Copy TP_L3_00108
TP_L3_00108.Position 0 -0.62 0.775
TP_L3_00108.Mother TES_L3
TP_L3_00108.Visibility 0

TES_Pixel_L3.Copy TP_L3_00109
TP_L3_00109.Position 0 -0.62 0.93
TP_L3_00109.Mother TES_L3
TP_L3_00109.Visibility 0

TES_Pixel_L3.Copy TP_L3_00110
TP_L3_00110.Position 0 -0.62 1.085
TP_L3_00110.Mother TES_L3
TP_L3_00110.Visibility 0

TES_Pixel_L3.Copy TP_L3_00111
TP_L3_00111.Position 0 -0.62 1.24
TP_L3_00111.Mother TES_L3
TP_L3_00111.Visibility 0

TES_Pixel_L3.Copy TP_L3_00112
TP_L3_00112.Position 0 -0.62 1.395
TP_L3_00112.Mother TES_L3
TP_L3_00112.Visibility 0

TES_Pixel_L3.Copy TP_L3_00113
TP_L3_00113.Position 0 -0.62 1.55
TP_L3_00113.Mother TES_L3
TP_L3_00113.Visibility 0

TES_Pixel_L3.Copy TP_L3_00114
TP_L3_00114.Position 0 -0.465 -1.55
TP_L3_00114.Mother TES_L3
TP_L3_00114.Visibility 0

TES_Pixel_L3.Copy TP_L3_00115
TP_L3_00115.Position 0 -0.465 -1.395
TP_L3_00115.Mother TES_L3
TP_L3_00115.Visibility 0

TES_Pixel_L3.Copy TP_L3_00116
TP_L3_00116.Position 0 -0.465 -1.24
TP_L3_00116.Mother TES_L3
TP_L3_00116.Visibility 0

TES_Pixel_L3.Copy TP_L3_00117
TP_L3_00117.Position 0 -0.465 -1.085
TP_L3_00117.Mother TES_L3
TP_L3_00117.Visibility 0

TES_Pixel_L3.Copy TP_L3_00118
TP_L3_00118.Position 0 -0.465 -0.93
TP_L3_00118.Mother TES_L3
TP_L3_00118.Visibility 0

TES_Pixel_L3.Copy TP_L3_00119
TP_L3_00119.Position 0 -0.465 -0.775
TP_L3_00119.Mother TES_L3
TP_L3_00119.Visibility 0

TES_Pixel_L3.Copy TP_L3_00120
TP_L3_00120.Position 0 -0.465 -0.62
TP_L3_00120.Mother TES_L3
TP_L3_00120.Visibility 0

TES_Pixel_L3.Copy TP_L3_00121
TP_L3_00121.Position 0 -0.465 -0.465
TP_L3_00121.Mother TES_L3
TP_L3_00121.Visibility 0

TES_Pixel_L3.Copy TP_L3_00122
TP_L3_00122.Position 0 -0.465 -0.31
TP_L3_00122.Mother TES_L3
TP_L3_00122.Visibility 0

TES_Pixel_L3.Copy TP_L3_00123
TP_L3_00123.Position 0 -0.465 -0.155
TP_L3_00123.Mother TES_L3
TP_L3_00123.Visibility 0

TES_Pixel_L3.Copy TP_L3_00124
TP_L3_00124.Position 0 -0.465 0
TP_L3_00124.Mother TES_L3
TP_L3_00124.Visibility 0

TES_Pixel_L3.Copy TP_L3_00125
TP_L3_00125.Position 0 -0.465 0.155
TP_L3_00125.Mother TES_L3
TP_L3_00125.Visibility 0

TES_Pixel_L3.Copy TP_L3_00126
TP_L3_00126.Position 0 -0.465 0.31
TP_L3_00126.Mother TES_L3
TP_L3_00126.Visibility 0

TES_Pixel_L3.Copy TP_L3_00127
TP_L3_00127.Position 0 -0.465 0.465
TP_L3_00127.Mother TES_L3
TP_L3_00127.Visibility 0

TES_Pixel_L3.Copy TP_L3_00128
TP_L3_00128.Position 0 -0.465 0.62
TP_L3_00128.Mother TES_L3
TP_L3_00128.Visibility 0

TES_Pixel_L3.Copy TP_L3_00129
TP_L3_00129.Position 0 -0.465 0.775
TP_L3_00129.Mother TES_L3
TP_L3_00129.Visibility 0

TES_Pixel_L3.Copy TP_L3_00130
TP_L3_00130.Position 0 -0.465 0.93
TP_L3_00130.Mother TES_L3
TP_L3_00130.Visibility 0

TES_Pixel_L3.Copy TP_L3_00131
TP_L3_00131.Position 0 -0.465 1.085
TP_L3_00131.Mother TES_L3
TP_L3_00131.Visibility 0

TES_Pixel_L3.Copy TP_L3_00132
TP_L3_00132.Position 0 -0.465 1.24
TP_L3_00132.Mother TES_L3
TP_L3_00132.Visibility 0

TES_Pixel_L3.Copy TP_L3_00133
TP_L3_00133.Position 0 -0.465 1.395
TP_L3_00133.Mother TES_L3
TP_L3_00133.Visibility 0

TES_Pixel_L3.Copy TP_L3_00134
TP_L3_00134.Position 0 -0.465 1.55
TP_L3_00134.Mother TES_L3
TP_L3_00134.Visibility 0

TES_Pixel_L3.Copy TP_L3_00135
TP_L3_00135.Position 0 -0.31 -1.55
TP_L3_00135.Mother TES_L3
TP_L3_00135.Visibility 0

TES_Pixel_L3.Copy TP_L3_00136
TP_L3_00136.Position 0 -0.31 -1.395
TP_L3_00136.Mother TES_L3
TP_L3_00136.Visibility 0

TES_Pixel_L3.Copy TP_L3_00137
TP_L3_00137.Position 0 -0.31 -1.24
TP_L3_00137.Mother TES_L3
TP_L3_00137.Visibility 0

TES_Pixel_L3.Copy TP_L3_00138
TP_L3_00138.Position 0 -0.31 -1.085
TP_L3_00138.Mother TES_L3
TP_L3_00138.Visibility 0

TES_Pixel_L3.Copy TP_L3_00139
TP_L3_00139.Position 0 -0.31 -0.93
TP_L3_00139.Mother TES_L3
TP_L3_00139.Visibility 0

TES_Pixel_L3.Copy TP_L3_00140
TP_L3_00140.Position 0 -0.31 -0.775
TP_L3_00140.Mother TES_L3
TP_L3_00140.Visibility 0

TES_Pixel_L3.Copy TP_L3_00141
TP_L3_00141.Position 0 -0.31 -0.62
TP_L3_00141.Mother TES_L3
TP_L3_00141.Visibility 0

TES_Pixel_L3.Copy TP_L3_00142
TP_L3_00142.Position 0 -0.31 -0.465
TP_L3_00142.Mother TES_L3
TP_L3_00142.Visibility 0

TES_Pixel_L3.Copy TP_L3_00143
TP_L3_00143.Position 0 -0.31 -0.31
TP_L3_00143.Mother TES_L3
TP_L3_00143.Visibility 0

TES_Pixel_L3.Copy TP_L3_00144
TP_L3_00144.Position 0 -0.31 -0.155
TP_L3_00144.Mother TES_L3
TP_L3_00144.Visibility 0

TES_Pixel_L3.Copy TP_L3_00145
TP_L3_00145.Position 0 -0.31 0
TP_L3_00145.Mother TES_L3
TP_L3_00145.Visibility 0

TES_Pixel_L3.Copy TP_L3_00146
TP_L3_00146.Position 0 -0.31 0.155
TP_L3_00146.Mother TES_L3
TP_L3_00146.Visibility 0

TES_Pixel_L3.Copy TP_L3_00147
TP_L3_00147.Position 0 -0.31 0.31
TP_L3_00147.Mother TES_L3
TP_L3_00147.Visibility 0

TES_Pixel_L3.Copy TP_L3_00148
TP_L3_00148.Position 0 -0.31 0.465
TP_L3_00148.Mother TES_L3
TP_L3_00148.Visibility 0

TES_Pixel_L3.Copy TP_L3_00149
TP_L3_00149.Position 0 -0.31 0.62
TP_L3_00149.Mother TES_L3
TP_L3_00149.Visibility 0

TES_Pixel_L3.Copy TP_L3_00150
TP_L3_00150.Position 0 -0.31 0.775
TP_L3_00150.Mother TES_L3
TP_L3_00150.Visibility 0

TES_Pixel_L3.Copy TP_L3_00151
TP_L3_00151.Position 0 -0.31 0.93
TP_L3_00151.Mother TES_L3
TP_L3_00151.Visibility 0

TES_Pixel_L3.Copy TP_L3_00152
TP_L3_00152.Position 0 -0.31 1.085
TP_L3_00152.Mother TES_L3
TP_L3_00152.Visibility 0

TES_Pixel_L3.Copy TP_L3_00153
TP_L3_00153.Position 0 -0.31 1.24
TP_L3_00153.Mother TES_L3
TP_L3_00153.Visibility 0

TES_Pixel_L3.Copy TP_L3_00154
TP_L3_00154.Position 0 -0.31 1.395
TP_L3_00154.Mother TES_L3
TP_L3_00154.Visibility 0

TES_Pixel_L3.Copy TP_L3_00155
TP_L3_00155.Position 0 -0.31 1.55
TP_L3_00155.Mother TES_L3
TP_L3_00155.Visibility 0

TES_Pixel_L3.Copy TP_L3_00156
TP_L3_00156.Position 0 -0.155 -1.55
TP_L3_00156.Mother TES_L3
TP_L3_00156.Visibility 0

TES_Pixel_L3.Copy TP_L3_00157
TP_L3_00157.Position 0 -0.155 -1.395
TP_L3_00157.Mother TES_L3
TP_L3_00157.Visibility 0

TES_Pixel_L3.Copy TP_L3_00158
TP_L3_00158.Position 0 -0.155 -1.24
TP_L3_00158.Mother TES_L3
TP_L3_00158.Visibility 0

TES_Pixel_L3.Copy TP_L3_00159
TP_L3_00159.Position 0 -0.155 -1.085
TP_L3_00159.Mother TES_L3
TP_L3_00159.Visibility 0

TES_Pixel_L3.Copy TP_L3_00160
TP_L3_00160.Position 0 -0.155 -0.93
TP_L3_00160.Mother TES_L3
TP_L3_00160.Visibility 0

TES_Pixel_L3.Copy TP_L3_00161
TP_L3_00161.Position 0 -0.155 -0.775
TP_L3_00161.Mother TES_L3
TP_L3_00161.Visibility 0

TES_Pixel_L3.Copy TP_L3_00162
TP_L3_00162.Position 0 -0.155 -0.62
TP_L3_00162.Mother TES_L3
TP_L3_00162.Visibility 0

TES_Pixel_L3.Copy TP_L3_00163
TP_L3_00163.Position 0 -0.155 -0.465
TP_L3_00163.Mother TES_L3
TP_L3_00163.Visibility 0

TES_Pixel_L3.Copy TP_L3_00164
TP_L3_00164.Position 0 -0.155 -0.31
TP_L3_00164.Mother TES_L3
TP_L3_00164.Visibility 0

TES_Pixel_L3.Copy TP_L3_00165
TP_L3_00165.Position 0 -0.155 -0.155
TP_L3_00165.Mother TES_L3
TP_L3_00165.Visibility 0

TES_Pixel_L3.Copy TP_L3_00166
TP_L3_00166.Position 0 -0.155 0
TP_L3_00166.Mother TES_L3
TP_L3_00166.Visibility 0

TES_Pixel_L3.Copy TP_L3_00167
TP_L3_00167.Position 0 -0.155 0.155
TP_L3_00167.Mother TES_L3
TP_L3_00167.Visibility 0

TES_Pixel_L3.Copy TP_L3_00168
TP_L3_00168.Position 0 -0.155 0.31
TP_L3_00168.Mother TES_L3
TP_L3_00168.Visibility 0

TES_Pixel_L3.Copy TP_L3_00169
TP_L3_00169.Position 0 -0.155 0.465
TP_L3_00169.Mother TES_L3
TP_L3_00169.Visibility 0

TES_Pixel_L3.Copy TP_L3_00170
TP_L3_00170.Position 0 -0.155 0.62
TP_L3_00170.Mother TES_L3
TP_L3_00170.Visibility 0

TES_Pixel_L3.Copy TP_L3_00171
TP_L3_00171.Position 0 -0.155 0.775
TP_L3_00171.Mother TES_L3
TP_L3_00171.Visibility 0

TES_Pixel_L3.Copy TP_L3_00172
TP_L3_00172.Position 0 -0.155 0.93
TP_L3_00172.Mother TES_L3
TP_L3_00172.Visibility 0

TES_Pixel_L3.Copy TP_L3_00173
TP_L3_00173.Position 0 -0.155 1.085
TP_L3_00173.Mother TES_L3
TP_L3_00173.Visibility 0

TES_Pixel_L3.Copy TP_L3_00174
TP_L3_00174.Position 0 -0.155 1.24
TP_L3_00174.Mother TES_L3
TP_L3_00174.Visibility 0

TES_Pixel_L3.Copy TP_L3_00175
TP_L3_00175.Position 0 -0.155 1.395
TP_L3_00175.Mother TES_L3
TP_L3_00175.Visibility 0

TES_Pixel_L3.Copy TP_L3_00176
TP_L3_00176.Position 0 -0.155 1.55
TP_L3_00176.Mother TES_L3
TP_L3_00176.Visibility 0

TES_Pixel_L3.Copy TP_L3_00177
TP_L3_00177.Position 0 0 -1.705
TP_L3_00177.Mother TES_L3
TP_L3_00177.Visibility 0

TES_Pixel_L3.Copy TP_L3_00178
TP_L3_00178.Position 0 0 -1.55
TP_L3_00178.Mother TES_L3
TP_L3_00178.Visibility 0

TES_Pixel_L3.Copy TP_L3_00179
TP_L3_00179.Position 0 0 -1.395
TP_L3_00179.Mother TES_L3
TP_L3_00179.Visibility 0

TES_Pixel_L3.Copy TP_L3_00180
TP_L3_00180.Position 0 0 -1.24
TP_L3_00180.Mother TES_L3
TP_L3_00180.Visibility 0

TES_Pixel_L3.Copy TP_L3_00181
TP_L3_00181.Position 0 0 -1.085
TP_L3_00181.Mother TES_L3
TP_L3_00181.Visibility 0

TES_Pixel_L3.Copy TP_L3_00182
TP_L3_00182.Position 0 0 -0.93
TP_L3_00182.Mother TES_L3
TP_L3_00182.Visibility 0

TES_Pixel_L3.Copy TP_L3_00183
TP_L3_00183.Position 0 0 -0.775
TP_L3_00183.Mother TES_L3
TP_L3_00183.Visibility 0

TES_Pixel_L3.Copy TP_L3_00184
TP_L3_00184.Position 0 0 -0.62
TP_L3_00184.Mother TES_L3
TP_L3_00184.Visibility 0

TES_Pixel_L3.Copy TP_L3_00185
TP_L3_00185.Position 0 0 -0.465
TP_L3_00185.Mother TES_L3
TP_L3_00185.Visibility 0

TES_Pixel_L3.Copy TP_L3_00186
TP_L3_00186.Position 0 0 -0.31
TP_L3_00186.Mother TES_L3
TP_L3_00186.Visibility 0

TES_Pixel_L3.Copy TP_L3_00187
TP_L3_00187.Position 0 0 -0.155
TP_L3_00187.Mother TES_L3
TP_L3_00187.Visibility 0

TES_Pixel_L3.Copy TP_L3_00188
TP_L3_00188.Position 0 0 0
TP_L3_00188.Mother TES_L3
TP_L3_00188.Visibility 0

TES_Pixel_L3.Copy TP_L3_00189
TP_L3_00189.Position 0 0 0.155
TP_L3_00189.Mother TES_L3
TP_L3_00189.Visibility 0

TES_Pixel_L3.Copy TP_L3_00190
TP_L3_00190.Position 0 0 0.31
TP_L3_00190.Mother TES_L3
TP_L3_00190.Visibility 0

TES_Pixel_L3.Copy TP_L3_00191
TP_L3_00191.Position 0 0 0.465
TP_L3_00191.Mother TES_L3
TP_L3_00191.Visibility 0

TES_Pixel_L3.Copy TP_L3_00192
TP_L3_00192.Position 0 0 0.62
TP_L3_00192.Mother TES_L3
TP_L3_00192.Visibility 0

TES_Pixel_L3.Copy TP_L3_00193
TP_L3_00193.Position 0 0 0.775
TP_L3_00193.Mother TES_L3
TP_L3_00193.Visibility 0

TES_Pixel_L3.Copy TP_L3_00194
TP_L3_00194.Position 0 0 0.93
TP_L3_00194.Mother TES_L3
TP_L3_00194.Visibility 0

TES_Pixel_L3.Copy TP_L3_00195
TP_L3_00195.Position 0 0 1.085
TP_L3_00195.Mother TES_L3
TP_L3_00195.Visibility 0

TES_Pixel_L3.Copy TP_L3_00196
TP_L3_00196.Position 0 0 1.24
TP_L3_00196.Mother TES_L3
TP_L3_00196.Visibility 0

TES_Pixel_L3.Copy TP_L3_00197
TP_L3_00197.Position 0 0 1.395
TP_L3_00197.Mother TES_L3
TP_L3_00197.Visibility 0

TES_Pixel_L3.Copy TP_L3_00198
TP_L3_00198.Position 0 0 1.55
TP_L3_00198.Mother TES_L3
TP_L3_00198.Visibility 0

TES_Pixel_L3.Copy TP_L3_00199
TP_L3_00199.Position 0 0 1.705
TP_L3_00199.Mother TES_L3
TP_L3_00199.Visibility 0

TES_Pixel_L3.Copy TP_L3_00200
TP_L3_00200.Position 0 0.155 -1.55
TP_L3_00200.Mother TES_L3
TP_L3_00200.Visibility 0

TES_Pixel_L3.Copy TP_L3_00201
TP_L3_00201.Position 0 0.155 -1.395
TP_L3_00201.Mother TES_L3
TP_L3_00201.Visibility 0

TES_Pixel_L3.Copy TP_L3_00202
TP_L3_00202.Position 0 0.155 -1.24
TP_L3_00202.Mother TES_L3
TP_L3_00202.Visibility 0

TES_Pixel_L3.Copy TP_L3_00203
TP_L3_00203.Position 0 0.155 -1.085
TP_L3_00203.Mother TES_L3
TP_L3_00203.Visibility 0

TES_Pixel_L3.Copy TP_L3_00204
TP_L3_00204.Position 0 0.155 -0.93
TP_L3_00204.Mother TES_L3
TP_L3_00204.Visibility 0

TES_Pixel_L3.Copy TP_L3_00205
TP_L3_00205.Position 0 0.155 -0.775
TP_L3_00205.Mother TES_L3
TP_L3_00205.Visibility 0

TES_Pixel_L3.Copy TP_L3_00206
TP_L3_00206.Position 0 0.155 -0.62
TP_L3_00206.Mother TES_L3
TP_L3_00206.Visibility 0

TES_Pixel_L3.Copy TP_L3_00207
TP_L3_00207.Position 0 0.155 -0.465
TP_L3_00207.Mother TES_L3
TP_L3_00207.Visibility 0

TES_Pixel_L3.Copy TP_L3_00208
TP_L3_00208.Position 0 0.155 -0.31
TP_L3_00208.Mother TES_L3
TP_L3_00208.Visibility 0

TES_Pixel_L3.Copy TP_L3_00209
TP_L3_00209.Position 0 0.155 -0.155
TP_L3_00209.Mother TES_L3
TP_L3_00209.Visibility 0

TES_Pixel_L3.Copy TP_L3_00210
TP_L3_00210.Position 0 0.155 0
TP_L3_00210.Mother TES_L3
TP_L3_00210.Visibility 0

TES_Pixel_L3.Copy TP_L3_00211
TP_L3_00211.Position 0 0.155 0.155
TP_L3_00211.Mother TES_L3
TP_L3_00211.Visibility 0

TES_Pixel_L3.Copy TP_L3_00212
TP_L3_00212.Position 0 0.155 0.31
TP_L3_00212.Mother TES_L3
TP_L3_00212.Visibility 0

TES_Pixel_L3.Copy TP_L3_00213
TP_L3_00213.Position 0 0.155 0.465
TP_L3_00213.Mother TES_L3
TP_L3_00213.Visibility 0

TES_Pixel_L3.Copy TP_L3_00214
TP_L3_00214.Position 0 0.155 0.62
TP_L3_00214.Mother TES_L3
TP_L3_00214.Visibility 0

TES_Pixel_L3.Copy TP_L3_00215
TP_L3_00215.Position 0 0.155 0.775
TP_L3_00215.Mother TES_L3
TP_L3_00215.Visibility 0

TES_Pixel_L3.Copy TP_L3_00216
TP_L3_00216.Position 0 0.155 0.93
TP_L3_00216.Mother TES_L3
TP_L3_00216.Visibility 0

TES_Pixel_L3.Copy TP_L3_00217
TP_L3_00217.Position 0 0.155 1.085
TP_L3_00217.Mother TES_L3
TP_L3_00217.Visibility 0

TES_Pixel_L3.Copy TP_L3_00218
TP_L3_00218.Position 0 0.155 1.24
TP_L3_00218.Mother TES_L3
TP_L3_00218.Visibility 0

TES_Pixel_L3.Copy TP_L3_00219
TP_L3_00219.Position 0 0.155 1.395
TP_L3_00219.Mother TES_L3
TP_L3_00219.Visibility 0

TES_Pixel_L3.Copy TP_L3_00220
TP_L3_00220.Position 0 0.155 1.55
TP_L3_00220.Mother TES_L3
TP_L3_00220.Visibility 0

TES_Pixel_L3.Copy TP_L3_00221
TP_L3_00221.Position 0 0.31 -1.55
TP_L3_00221.Mother TES_L3
TP_L3_00221.Visibility 0

TES_Pixel_L3.Copy TP_L3_00222
TP_L3_00222.Position 0 0.31 -1.395
TP_L3_00222.Mother TES_L3
TP_L3_00222.Visibility 0

TES_Pixel_L3.Copy TP_L3_00223
TP_L3_00223.Position 0 0.31 -1.24
TP_L3_00223.Mother TES_L3
TP_L3_00223.Visibility 0

TES_Pixel_L3.Copy TP_L3_00224
TP_L3_00224.Position 0 0.31 -1.085
TP_L3_00224.Mother TES_L3
TP_L3_00224.Visibility 0

TES_Pixel_L3.Copy TP_L3_00225
TP_L3_00225.Position 0 0.31 -0.93
TP_L3_00225.Mother TES_L3
TP_L3_00225.Visibility 0

TES_Pixel_L3.Copy TP_L3_00226
TP_L3_00226.Position 0 0.31 -0.775
TP_L3_00226.Mother TES_L3
TP_L3_00226.Visibility 0

TES_Pixel_L3.Copy TP_L3_00227
TP_L3_00227.Position 0 0.31 -0.62
TP_L3_00227.Mother TES_L3
TP_L3_00227.Visibility 0

TES_Pixel_L3.Copy TP_L3_00228
TP_L3_00228.Position 0 0.31 -0.465
TP_L3_00228.Mother TES_L3
TP_L3_00228.Visibility 0

TES_Pixel_L3.Copy TP_L3_00229
TP_L3_00229.Position 0 0.31 -0.31
TP_L3_00229.Mother TES_L3
TP_L3_00229.Visibility 0

TES_Pixel_L3.Copy TP_L3_00230
TP_L3_00230.Position 0 0.31 -0.155
TP_L3_00230.Mother TES_L3
TP_L3_00230.Visibility 0

TES_Pixel_L3.Copy TP_L3_00231
TP_L3_00231.Position 0 0.31 0
TP_L3_00231.Mother TES_L3
TP_L3_00231.Visibility 0

TES_Pixel_L3.Copy TP_L3_00232
TP_L3_00232.Position 0 0.31 0.155
TP_L3_00232.Mother TES_L3
TP_L3_00232.Visibility 0

TES_Pixel_L3.Copy TP_L3_00233
TP_L3_00233.Position 0 0.31 0.31
TP_L3_00233.Mother TES_L3
TP_L3_00233.Visibility 0

TES_Pixel_L3.Copy TP_L3_00234
TP_L3_00234.Position 0 0.31 0.465
TP_L3_00234.Mother TES_L3
TP_L3_00234.Visibility 0

TES_Pixel_L3.Copy TP_L3_00235
TP_L3_00235.Position 0 0.31 0.62
TP_L3_00235.Mother TES_L3
TP_L3_00235.Visibility 0

TES_Pixel_L3.Copy TP_L3_00236
TP_L3_00236.Position 0 0.31 0.775
TP_L3_00236.Mother TES_L3
TP_L3_00236.Visibility 0

TES_Pixel_L3.Copy TP_L3_00237
TP_L3_00237.Position 0 0.31 0.93
TP_L3_00237.Mother TES_L3
TP_L3_00237.Visibility 0

TES_Pixel_L3.Copy TP_L3_00238
TP_L3_00238.Position 0 0.31 1.085
TP_L3_00238.Mother TES_L3
TP_L3_00238.Visibility 0

TES_Pixel_L3.Copy TP_L3_00239
TP_L3_00239.Position 0 0.31 1.24
TP_L3_00239.Mother TES_L3
TP_L3_00239.Visibility 0

TES_Pixel_L3.Copy TP_L3_00240
TP_L3_00240.Position 0 0.31 1.395
TP_L3_00240.Mother TES_L3
TP_L3_00240.Visibility 0

TES_Pixel_L3.Copy TP_L3_00241
TP_L3_00241.Position 0 0.31 1.55
TP_L3_00241.Mother TES_L3
TP_L3_00241.Visibility 0

TES_Pixel_L3.Copy TP_L3_00242
TP_L3_00242.Position 0 0.465 -1.55
TP_L3_00242.Mother TES_L3
TP_L3_00242.Visibility 0

TES_Pixel_L3.Copy TP_L3_00243
TP_L3_00243.Position 0 0.465 -1.395
TP_L3_00243.Mother TES_L3
TP_L3_00243.Visibility 0

TES_Pixel_L3.Copy TP_L3_00244
TP_L3_00244.Position 0 0.465 -1.24
TP_L3_00244.Mother TES_L3
TP_L3_00244.Visibility 0

TES_Pixel_L3.Copy TP_L3_00245
TP_L3_00245.Position 0 0.465 -1.085
TP_L3_00245.Mother TES_L3
TP_L3_00245.Visibility 0

TES_Pixel_L3.Copy TP_L3_00246
TP_L3_00246.Position 0 0.465 -0.93
TP_L3_00246.Mother TES_L3
TP_L3_00246.Visibility 0

TES_Pixel_L3.Copy TP_L3_00247
TP_L3_00247.Position 0 0.465 -0.775
TP_L3_00247.Mother TES_L3
TP_L3_00247.Visibility 0

TES_Pixel_L3.Copy TP_L3_00248
TP_L3_00248.Position 0 0.465 -0.62
TP_L3_00248.Mother TES_L3
TP_L3_00248.Visibility 0

TES_Pixel_L3.Copy TP_L3_00249
TP_L3_00249.Position 0 0.465 -0.465
TP_L3_00249.Mother TES_L3
TP_L3_00249.Visibility 0

TES_Pixel_L3.Copy TP_L3_00250
TP_L3_00250.Position 0 0.465 -0.31
TP_L3_00250.Mother TES_L3
TP_L3_00250.Visibility 0

TES_Pixel_L3.Copy TP_L3_00251
TP_L3_00251.Position 0 0.465 -0.155
TP_L3_00251.Mother TES_L3
TP_L3_00251.Visibility 0

TES_Pixel_L3.Copy TP_L3_00252
TP_L3_00252.Position 0 0.465 0
TP_L3_00252.Mother TES_L3
TP_L3_00252.Visibility 0

TES_Pixel_L3.Copy TP_L3_00253
TP_L3_00253.Position 0 0.465 0.155
TP_L3_00253.Mother TES_L3
TP_L3_00253.Visibility 0

TES_Pixel_L3.Copy TP_L3_00254
TP_L3_00254.Position 0 0.465 0.31
TP_L3_00254.Mother TES_L3
TP_L3_00254.Visibility 0

TES_Pixel_L3.Copy TP_L3_00255
TP_L3_00255.Position 0 0.465 0.465
TP_L3_00255.Mother TES_L3
TP_L3_00255.Visibility 0

TES_Pixel_L3.Copy TP_L3_00256
TP_L3_00256.Position 0 0.465 0.62
TP_L3_00256.Mother TES_L3
TP_L3_00256.Visibility 0

TES_Pixel_L3.Copy TP_L3_00257
TP_L3_00257.Position 0 0.465 0.775
TP_L3_00257.Mother TES_L3
TP_L3_00257.Visibility 0

TES_Pixel_L3.Copy TP_L3_00258
TP_L3_00258.Position 0 0.465 0.93
TP_L3_00258.Mother TES_L3
TP_L3_00258.Visibility 0

TES_Pixel_L3.Copy TP_L3_00259
TP_L3_00259.Position 0 0.465 1.085
TP_L3_00259.Mother TES_L3
TP_L3_00259.Visibility 0

TES_Pixel_L3.Copy TP_L3_00260
TP_L3_00260.Position 0 0.465 1.24
TP_L3_00260.Mother TES_L3
TP_L3_00260.Visibility 0

TES_Pixel_L3.Copy TP_L3_00261
TP_L3_00261.Position 0 0.465 1.395
TP_L3_00261.Mother TES_L3
TP_L3_00261.Visibility 0

TES_Pixel_L3.Copy TP_L3_00262
TP_L3_00262.Position 0 0.465 1.55
TP_L3_00262.Mother TES_L3
TP_L3_00262.Visibility 0

TES_Pixel_L3.Copy TP_L3_00263
TP_L3_00263.Position 0 0.62 -1.55
TP_L3_00263.Mother TES_L3
TP_L3_00263.Visibility 0

TES_Pixel_L3.Copy TP_L3_00264
TP_L3_00264.Position 0 0.62 -1.395
TP_L3_00264.Mother TES_L3
TP_L3_00264.Visibility 0

TES_Pixel_L3.Copy TP_L3_00265
TP_L3_00265.Position 0 0.62 -1.24
TP_L3_00265.Mother TES_L3
TP_L3_00265.Visibility 0

TES_Pixel_L3.Copy TP_L3_00266
TP_L3_00266.Position 0 0.62 -1.085
TP_L3_00266.Mother TES_L3
TP_L3_00266.Visibility 0

TES_Pixel_L3.Copy TP_L3_00267
TP_L3_00267.Position 0 0.62 -0.93
TP_L3_00267.Mother TES_L3
TP_L3_00267.Visibility 0

TES_Pixel_L3.Copy TP_L3_00268
TP_L3_00268.Position 0 0.62 -0.775
TP_L3_00268.Mother TES_L3
TP_L3_00268.Visibility 0

TES_Pixel_L3.Copy TP_L3_00269
TP_L3_00269.Position 0 0.62 -0.62
TP_L3_00269.Mother TES_L3
TP_L3_00269.Visibility 0

TES_Pixel_L3.Copy TP_L3_00270
TP_L3_00270.Position 0 0.62 -0.465
TP_L3_00270.Mother TES_L3
TP_L3_00270.Visibility 0

TES_Pixel_L3.Copy TP_L3_00271
TP_L3_00271.Position 0 0.62 -0.31
TP_L3_00271.Mother TES_L3
TP_L3_00271.Visibility 0

TES_Pixel_L3.Copy TP_L3_00272
TP_L3_00272.Position 0 0.62 -0.155
TP_L3_00272.Mother TES_L3
TP_L3_00272.Visibility 0

TES_Pixel_L3.Copy TP_L3_00273
TP_L3_00273.Position 0 0.62 0
TP_L3_00273.Mother TES_L3
TP_L3_00273.Visibility 0

TES_Pixel_L3.Copy TP_L3_00274
TP_L3_00274.Position 0 0.62 0.155
TP_L3_00274.Mother TES_L3
TP_L3_00274.Visibility 0

TES_Pixel_L3.Copy TP_L3_00275
TP_L3_00275.Position 0 0.62 0.31
TP_L3_00275.Mother TES_L3
TP_L3_00275.Visibility 0

TES_Pixel_L3.Copy TP_L3_00276
TP_L3_00276.Position 0 0.62 0.465
TP_L3_00276.Mother TES_L3
TP_L3_00276.Visibility 0

TES_Pixel_L3.Copy TP_L3_00277
TP_L3_00277.Position 0 0.62 0.62
TP_L3_00277.Mother TES_L3
TP_L3_00277.Visibility 0

TES_Pixel_L3.Copy TP_L3_00278
TP_L3_00278.Position 0 0.62 0.775
TP_L3_00278.Mother TES_L3
TP_L3_00278.Visibility 0

TES_Pixel_L3.Copy TP_L3_00279
TP_L3_00279.Position 0 0.62 0.93
TP_L3_00279.Mother TES_L3
TP_L3_00279.Visibility 0

TES_Pixel_L3.Copy TP_L3_00280
TP_L3_00280.Position 0 0.62 1.085
TP_L3_00280.Mother TES_L3
TP_L3_00280.Visibility 0

TES_Pixel_L3.Copy TP_L3_00281
TP_L3_00281.Position 0 0.62 1.24
TP_L3_00281.Mother TES_L3
TP_L3_00281.Visibility 0

TES_Pixel_L3.Copy TP_L3_00282
TP_L3_00282.Position 0 0.62 1.395
TP_L3_00282.Mother TES_L3
TP_L3_00282.Visibility 0

TES_Pixel_L3.Copy TP_L3_00283
TP_L3_00283.Position 0 0.62 1.55
TP_L3_00283.Mother TES_L3
TP_L3_00283.Visibility 0

TES_Pixel_L3.Copy TP_L3_00284
TP_L3_00284.Position 0 0.775 -1.395
TP_L3_00284.Mother TES_L3
TP_L3_00284.Visibility 0

TES_Pixel_L3.Copy TP_L3_00285
TP_L3_00285.Position 0 0.775 -1.24
TP_L3_00285.Mother TES_L3
TP_L3_00285.Visibility 0

TES_Pixel_L3.Copy TP_L3_00286
TP_L3_00286.Position 0 0.775 -1.085
TP_L3_00286.Mother TES_L3
TP_L3_00286.Visibility 0

TES_Pixel_L3.Copy TP_L3_00287
TP_L3_00287.Position 0 0.775 -0.93
TP_L3_00287.Mother TES_L3
TP_L3_00287.Visibility 0

TES_Pixel_L3.Copy TP_L3_00288
TP_L3_00288.Position 0 0.775 -0.775
TP_L3_00288.Mother TES_L3
TP_L3_00288.Visibility 0

TES_Pixel_L3.Copy TP_L3_00289
TP_L3_00289.Position 0 0.775 -0.62
TP_L3_00289.Mother TES_L3
TP_L3_00289.Visibility 0

TES_Pixel_L3.Copy TP_L3_00290
TP_L3_00290.Position 0 0.775 -0.465
TP_L3_00290.Mother TES_L3
TP_L3_00290.Visibility 0

TES_Pixel_L3.Copy TP_L3_00291
TP_L3_00291.Position 0 0.775 -0.31
TP_L3_00291.Mother TES_L3
TP_L3_00291.Visibility 0

TES_Pixel_L3.Copy TP_L3_00292
TP_L3_00292.Position 0 0.775 -0.155
TP_L3_00292.Mother TES_L3
TP_L3_00292.Visibility 0

TES_Pixel_L3.Copy TP_L3_00293
TP_L3_00293.Position 0 0.775 0
TP_L3_00293.Mother TES_L3
TP_L3_00293.Visibility 0

TES_Pixel_L3.Copy TP_L3_00294
TP_L3_00294.Position 0 0.775 0.155
TP_L3_00294.Mother TES_L3
TP_L3_00294.Visibility 0

TES_Pixel_L3.Copy TP_L3_00295
TP_L3_00295.Position 0 0.775 0.31
TP_L3_00295.Mother TES_L3
TP_L3_00295.Visibility 0

TES_Pixel_L3.Copy TP_L3_00296
TP_L3_00296.Position 0 0.775 0.465
TP_L3_00296.Mother TES_L3
TP_L3_00296.Visibility 0

TES_Pixel_L3.Copy TP_L3_00297
TP_L3_00297.Position 0 0.775 0.62
TP_L3_00297.Mother TES_L3
TP_L3_00297.Visibility 0

TES_Pixel_L3.Copy TP_L3_00298
TP_L3_00298.Position 0 0.775 0.775
TP_L3_00298.Mother TES_L3
TP_L3_00298.Visibility 0

TES_Pixel_L3.Copy TP_L3_00299
TP_L3_00299.Position 0 0.775 0.93
TP_L3_00299.Mother TES_L3
TP_L3_00299.Visibility 0

TES_Pixel_L3.Copy TP_L3_00300
TP_L3_00300.Position 0 0.775 1.085
TP_L3_00300.Mother TES_L3
TP_L3_00300.Visibility 0

TES_Pixel_L3.Copy TP_L3_00301
TP_L3_00301.Position 0 0.775 1.24
TP_L3_00301.Mother TES_L3
TP_L3_00301.Visibility 0

TES_Pixel_L3.Copy TP_L3_00302
TP_L3_00302.Position 0 0.775 1.395
TP_L3_00302.Mother TES_L3
TP_L3_00302.Visibility 0

TES_Pixel_L3.Copy TP_L3_00303
TP_L3_00303.Position 0 0.93 -1.395
TP_L3_00303.Mother TES_L3
TP_L3_00303.Visibility 0

TES_Pixel_L3.Copy TP_L3_00304
TP_L3_00304.Position 0 0.93 -1.24
TP_L3_00304.Mother TES_L3
TP_L3_00304.Visibility 0

TES_Pixel_L3.Copy TP_L3_00305
TP_L3_00305.Position 0 0.93 -1.085
TP_L3_00305.Mother TES_L3
TP_L3_00305.Visibility 0

TES_Pixel_L3.Copy TP_L3_00306
TP_L3_00306.Position 0 0.93 -0.93
TP_L3_00306.Mother TES_L3
TP_L3_00306.Visibility 0

TES_Pixel_L3.Copy TP_L3_00307
TP_L3_00307.Position 0 0.93 -0.775
TP_L3_00307.Mother TES_L3
TP_L3_00307.Visibility 0

TES_Pixel_L3.Copy TP_L3_00308
TP_L3_00308.Position 0 0.93 -0.62
TP_L3_00308.Mother TES_L3
TP_L3_00308.Visibility 0

TES_Pixel_L3.Copy TP_L3_00309
TP_L3_00309.Position 0 0.93 -0.465
TP_L3_00309.Mother TES_L3
TP_L3_00309.Visibility 0

TES_Pixel_L3.Copy TP_L3_00310
TP_L3_00310.Position 0 0.93 -0.31
TP_L3_00310.Mother TES_L3
TP_L3_00310.Visibility 0

TES_Pixel_L3.Copy TP_L3_00311
TP_L3_00311.Position 0 0.93 -0.155
TP_L3_00311.Mother TES_L3
TP_L3_00311.Visibility 0

TES_Pixel_L3.Copy TP_L3_00312
TP_L3_00312.Position 0 0.93 0
TP_L3_00312.Mother TES_L3
TP_L3_00312.Visibility 0

TES_Pixel_L3.Copy TP_L3_00313
TP_L3_00313.Position 0 0.93 0.155
TP_L3_00313.Mother TES_L3
TP_L3_00313.Visibility 0

TES_Pixel_L3.Copy TP_L3_00314
TP_L3_00314.Position 0 0.93 0.31
TP_L3_00314.Mother TES_L3
TP_L3_00314.Visibility 0

TES_Pixel_L3.Copy TP_L3_00315
TP_L3_00315.Position 0 0.93 0.465
TP_L3_00315.Mother TES_L3
TP_L3_00315.Visibility 0

TES_Pixel_L3.Copy TP_L3_00316
TP_L3_00316.Position 0 0.93 0.62
TP_L3_00316.Mother TES_L3
TP_L3_00316.Visibility 0

TES_Pixel_L3.Copy TP_L3_00317
TP_L3_00317.Position 0 0.93 0.775
TP_L3_00317.Mother TES_L3
TP_L3_00317.Visibility 0

TES_Pixel_L3.Copy TP_L3_00318
TP_L3_00318.Position 0 0.93 0.93
TP_L3_00318.Mother TES_L3
TP_L3_00318.Visibility 0

TES_Pixel_L3.Copy TP_L3_00319
TP_L3_00319.Position 0 0.93 1.085
TP_L3_00319.Mother TES_L3
TP_L3_00319.Visibility 0

TES_Pixel_L3.Copy TP_L3_00320
TP_L3_00320.Position 0 0.93 1.24
TP_L3_00320.Mother TES_L3
TP_L3_00320.Visibility 0

TES_Pixel_L3.Copy TP_L3_00321
TP_L3_00321.Position 0 0.93 1.395
TP_L3_00321.Mother TES_L3
TP_L3_00321.Visibility 0

TES_Pixel_L3.Copy TP_L3_00322
TP_L3_00322.Position 0 1.085 -1.24
TP_L3_00322.Mother TES_L3
TP_L3_00322.Visibility 0

TES_Pixel_L3.Copy TP_L3_00323
TP_L3_00323.Position 0 1.085 -1.085
TP_L3_00323.Mother TES_L3
TP_L3_00323.Visibility 0

TES_Pixel_L3.Copy TP_L3_00324
TP_L3_00324.Position 0 1.085 -0.93
TP_L3_00324.Mother TES_L3
TP_L3_00324.Visibility 0

TES_Pixel_L3.Copy TP_L3_00325
TP_L3_00325.Position 0 1.085 -0.775
TP_L3_00325.Mother TES_L3
TP_L3_00325.Visibility 0

TES_Pixel_L3.Copy TP_L3_00326
TP_L3_00326.Position 0 1.085 -0.62
TP_L3_00326.Mother TES_L3
TP_L3_00326.Visibility 0

TES_Pixel_L3.Copy TP_L3_00327
TP_L3_00327.Position 0 1.085 -0.465
TP_L3_00327.Mother TES_L3
TP_L3_00327.Visibility 0

TES_Pixel_L3.Copy TP_L3_00328
TP_L3_00328.Position 0 1.085 -0.31
TP_L3_00328.Mother TES_L3
TP_L3_00328.Visibility 0

TES_Pixel_L3.Copy TP_L3_00329
TP_L3_00329.Position 0 1.085 -0.155
TP_L3_00329.Mother TES_L3
TP_L3_00329.Visibility 0

TES_Pixel_L3.Copy TP_L3_00330
TP_L3_00330.Position 0 1.085 0
TP_L3_00330.Mother TES_L3
TP_L3_00330.Visibility 0

TES_Pixel_L3.Copy TP_L3_00331
TP_L3_00331.Position 0 1.085 0.155
TP_L3_00331.Mother TES_L3
TP_L3_00331.Visibility 0

TES_Pixel_L3.Copy TP_L3_00332
TP_L3_00332.Position 0 1.085 0.31
TP_L3_00332.Mother TES_L3
TP_L3_00332.Visibility 0

TES_Pixel_L3.Copy TP_L3_00333
TP_L3_00333.Position 0 1.085 0.465
TP_L3_00333.Mother TES_L3
TP_L3_00333.Visibility 0

TES_Pixel_L3.Copy TP_L3_00334
TP_L3_00334.Position 0 1.085 0.62
TP_L3_00334.Mother TES_L3
TP_L3_00334.Visibility 0

TES_Pixel_L3.Copy TP_L3_00335
TP_L3_00335.Position 0 1.085 0.775
TP_L3_00335.Mother TES_L3
TP_L3_00335.Visibility 0

TES_Pixel_L3.Copy TP_L3_00336
TP_L3_00336.Position 0 1.085 0.93
TP_L3_00336.Mother TES_L3
TP_L3_00336.Visibility 0

TES_Pixel_L3.Copy TP_L3_00337
TP_L3_00337.Position 0 1.085 1.085
TP_L3_00337.Mother TES_L3
TP_L3_00337.Visibility 0

TES_Pixel_L3.Copy TP_L3_00338
TP_L3_00338.Position 0 1.085 1.24
TP_L3_00338.Mother TES_L3
TP_L3_00338.Visibility 0

TES_Pixel_L3.Copy TP_L3_00339
TP_L3_00339.Position 0 1.24 -1.085
TP_L3_00339.Mother TES_L3
TP_L3_00339.Visibility 0

TES_Pixel_L3.Copy TP_L3_00340
TP_L3_00340.Position 0 1.24 -0.93
TP_L3_00340.Mother TES_L3
TP_L3_00340.Visibility 0

TES_Pixel_L3.Copy TP_L3_00341
TP_L3_00341.Position 0 1.24 -0.775
TP_L3_00341.Mother TES_L3
TP_L3_00341.Visibility 0

TES_Pixel_L3.Copy TP_L3_00342
TP_L3_00342.Position 0 1.24 -0.62
TP_L3_00342.Mother TES_L3
TP_L3_00342.Visibility 0

TES_Pixel_L3.Copy TP_L3_00343
TP_L3_00343.Position 0 1.24 -0.465
TP_L3_00343.Mother TES_L3
TP_L3_00343.Visibility 0

TES_Pixel_L3.Copy TP_L3_00344
TP_L3_00344.Position 0 1.24 -0.31
TP_L3_00344.Mother TES_L3
TP_L3_00344.Visibility 0

TES_Pixel_L3.Copy TP_L3_00345
TP_L3_00345.Position 0 1.24 -0.155
TP_L3_00345.Mother TES_L3
TP_L3_00345.Visibility 0

TES_Pixel_L3.Copy TP_L3_00346
TP_L3_00346.Position 0 1.24 0
TP_L3_00346.Mother TES_L3
TP_L3_00346.Visibility 0

TES_Pixel_L3.Copy TP_L3_00347
TP_L3_00347.Position 0 1.24 0.155
TP_L3_00347.Mother TES_L3
TP_L3_00347.Visibility 0

TES_Pixel_L3.Copy TP_L3_00348
TP_L3_00348.Position 0 1.24 0.31
TP_L3_00348.Mother TES_L3
TP_L3_00348.Visibility 0

TES_Pixel_L3.Copy TP_L3_00349
TP_L3_00349.Position 0 1.24 0.465
TP_L3_00349.Mother TES_L3
TP_L3_00349.Visibility 0

TES_Pixel_L3.Copy TP_L3_00350
TP_L3_00350.Position 0 1.24 0.62
TP_L3_00350.Mother TES_L3
TP_L3_00350.Visibility 0

TES_Pixel_L3.Copy TP_L3_00351
TP_L3_00351.Position 0 1.24 0.775
TP_L3_00351.Mother TES_L3
TP_L3_00351.Visibility 0

TES_Pixel_L3.Copy TP_L3_00352
TP_L3_00352.Position 0 1.24 0.93
TP_L3_00352.Mother TES_L3
TP_L3_00352.Visibility 0

TES_Pixel_L3.Copy TP_L3_00353
TP_L3_00353.Position 0 1.24 1.085
TP_L3_00353.Mother TES_L3
TP_L3_00353.Visibility 0

TES_Pixel_L3.Copy TP_L3_00354
TP_L3_00354.Position 0 1.395 -0.93
TP_L3_00354.Mother TES_L3
TP_L3_00354.Visibility 0

TES_Pixel_L3.Copy TP_L3_00355
TP_L3_00355.Position 0 1.395 -0.775
TP_L3_00355.Mother TES_L3
TP_L3_00355.Visibility 0

TES_Pixel_L3.Copy TP_L3_00356
TP_L3_00356.Position 0 1.395 -0.62
TP_L3_00356.Mother TES_L3
TP_L3_00356.Visibility 0

TES_Pixel_L3.Copy TP_L3_00357
TP_L3_00357.Position 0 1.395 -0.465
TP_L3_00357.Mother TES_L3
TP_L3_00357.Visibility 0

TES_Pixel_L3.Copy TP_L3_00358
TP_L3_00358.Position 0 1.395 -0.31
TP_L3_00358.Mother TES_L3
TP_L3_00358.Visibility 0

TES_Pixel_L3.Copy TP_L3_00359
TP_L3_00359.Position 0 1.395 -0.155
TP_L3_00359.Mother TES_L3
TP_L3_00359.Visibility 0

TES_Pixel_L3.Copy TP_L3_00360
TP_L3_00360.Position 0 1.395 0
TP_L3_00360.Mother TES_L3
TP_L3_00360.Visibility 0

TES_Pixel_L3.Copy TP_L3_00361
TP_L3_00361.Position 0 1.395 0.155
TP_L3_00361.Mother TES_L3
TP_L3_00361.Visibility 0

TES_Pixel_L3.Copy TP_L3_00362
TP_L3_00362.Position 0 1.395 0.31
TP_L3_00362.Mother TES_L3
TP_L3_00362.Visibility 0

TES_Pixel_L3.Copy TP_L3_00363
TP_L3_00363.Position 0 1.395 0.465
TP_L3_00363.Mother TES_L3
TP_L3_00363.Visibility 0

TES_Pixel_L3.Copy TP_L3_00364
TP_L3_00364.Position 0 1.395 0.62
TP_L3_00364.Mother TES_L3
TP_L3_00364.Visibility 0

TES_Pixel_L3.Copy TP_L3_00365
TP_L3_00365.Position 0 1.395 0.775
TP_L3_00365.Mother TES_L3
TP_L3_00365.Visibility 0

TES_Pixel_L3.Copy TP_L3_00366
TP_L3_00366.Position 0 1.395 0.93
TP_L3_00366.Mother TES_L3
TP_L3_00366.Visibility 0

TES_Pixel_L3.Copy TP_L3_00367
TP_L3_00367.Position 0 1.55 -0.62
TP_L3_00367.Mother TES_L3
TP_L3_00367.Visibility 0

TES_Pixel_L3.Copy TP_L3_00368
TP_L3_00368.Position 0 1.55 -0.465
TP_L3_00368.Mother TES_L3
TP_L3_00368.Visibility 0

TES_Pixel_L3.Copy TP_L3_00369
TP_L3_00369.Position 0 1.55 -0.31
TP_L3_00369.Mother TES_L3
TP_L3_00369.Visibility 0

TES_Pixel_L3.Copy TP_L3_00370
TP_L3_00370.Position 0 1.55 -0.155
TP_L3_00370.Mother TES_L3
TP_L3_00370.Visibility 0

TES_Pixel_L3.Copy TP_L3_00371
TP_L3_00371.Position 0 1.55 0
TP_L3_00371.Mother TES_L3
TP_L3_00371.Visibility 0

TES_Pixel_L3.Copy TP_L3_00372
TP_L3_00372.Position 0 1.55 0.155
TP_L3_00372.Mother TES_L3
TP_L3_00372.Visibility 0

TES_Pixel_L3.Copy TP_L3_00373
TP_L3_00373.Position 0 1.55 0.31
TP_L3_00373.Mother TES_L3
TP_L3_00373.Visibility 0

TES_Pixel_L3.Copy TP_L3_00374
TP_L3_00374.Position 0 1.55 0.465
TP_L3_00374.Mother TES_L3
TP_L3_00374.Visibility 0

TES_Pixel_L3.Copy TP_L3_00375
TP_L3_00375.Position 0 1.55 0.62
TP_L3_00375.Mother TES_L3
TP_L3_00375.Visibility 0

// Volume TES_Pixel_L4; material=Ta
Volume TES_Pixel_L4
TES_Pixel_L4.Material Ta
TES_Pixel_L4.Visibility 1
TES_Pixel_L4.Shape BRIK 0.15 0.075 0.075

// Volume TES_L4; material=Vacuum
Volume TES_L4
TES_L4.Material Vacuum
TES_L4.Visibility 0
TES_L4.Shape BRIK 0.15 1.8 1.8

TES_L4.Position -33.75 0 -2.8
TES_L4.Mother InstrumentFrame

TES_Pixel_L4.Copy TP_L4_00000
TP_L4_00000.Position 0 -1.705 0
TP_L4_00000.Mother TES_L4
TP_L4_00000.Visibility 0

TES_Pixel_L4.Copy TP_L4_00001
TP_L4_00001.Position 0 -1.55 -0.62
TP_L4_00001.Mother TES_L4
TP_L4_00001.Visibility 0

TES_Pixel_L4.Copy TP_L4_00002
TP_L4_00002.Position 0 -1.55 -0.465
TP_L4_00002.Mother TES_L4
TP_L4_00002.Visibility 0

TES_Pixel_L4.Copy TP_L4_00003
TP_L4_00003.Position 0 -1.55 -0.31
TP_L4_00003.Mother TES_L4
TP_L4_00003.Visibility 0

TES_Pixel_L4.Copy TP_L4_00004
TP_L4_00004.Position 0 -1.55 -0.155
TP_L4_00004.Mother TES_L4
TP_L4_00004.Visibility 0

TES_Pixel_L4.Copy TP_L4_00005
TP_L4_00005.Position 0 -1.55 0
TP_L4_00005.Mother TES_L4
TP_L4_00005.Visibility 0

TES_Pixel_L4.Copy TP_L4_00006
TP_L4_00006.Position 0 -1.55 0.155
TP_L4_00006.Mother TES_L4
TP_L4_00006.Visibility 0

TES_Pixel_L4.Copy TP_L4_00007
TP_L4_00007.Position 0 -1.55 0.31
TP_L4_00007.Mother TES_L4
TP_L4_00007.Visibility 0

TES_Pixel_L4.Copy TP_L4_00008
TP_L4_00008.Position 0 -1.55 0.465
TP_L4_00008.Mother TES_L4
TP_L4_00008.Visibility 0

TES_Pixel_L4.Copy TP_L4_00009
TP_L4_00009.Position 0 -1.55 0.62
TP_L4_00009.Mother TES_L4
TP_L4_00009.Visibility 0

TES_Pixel_L4.Copy TP_L4_00010
TP_L4_00010.Position 0 -1.395 -0.93
TP_L4_00010.Mother TES_L4
TP_L4_00010.Visibility 0

TES_Pixel_L4.Copy TP_L4_00011
TP_L4_00011.Position 0 -1.395 -0.775
TP_L4_00011.Mother TES_L4
TP_L4_00011.Visibility 0

TES_Pixel_L4.Copy TP_L4_00012
TP_L4_00012.Position 0 -1.395 -0.62
TP_L4_00012.Mother TES_L4
TP_L4_00012.Visibility 0

TES_Pixel_L4.Copy TP_L4_00013
TP_L4_00013.Position 0 -1.395 -0.465
TP_L4_00013.Mother TES_L4
TP_L4_00013.Visibility 0

TES_Pixel_L4.Copy TP_L4_00014
TP_L4_00014.Position 0 -1.395 -0.31
TP_L4_00014.Mother TES_L4
TP_L4_00014.Visibility 0

TES_Pixel_L4.Copy TP_L4_00015
TP_L4_00015.Position 0 -1.395 -0.155
TP_L4_00015.Mother TES_L4
TP_L4_00015.Visibility 0

TES_Pixel_L4.Copy TP_L4_00016
TP_L4_00016.Position 0 -1.395 0
TP_L4_00016.Mother TES_L4
TP_L4_00016.Visibility 0

TES_Pixel_L4.Copy TP_L4_00017
TP_L4_00017.Position 0 -1.395 0.155
TP_L4_00017.Mother TES_L4
TP_L4_00017.Visibility 0

TES_Pixel_L4.Copy TP_L4_00018
TP_L4_00018.Position 0 -1.395 0.31
TP_L4_00018.Mother TES_L4
TP_L4_00018.Visibility 0

TES_Pixel_L4.Copy TP_L4_00019
TP_L4_00019.Position 0 -1.395 0.465
TP_L4_00019.Mother TES_L4
TP_L4_00019.Visibility 0

TES_Pixel_L4.Copy TP_L4_00020
TP_L4_00020.Position 0 -1.395 0.62
TP_L4_00020.Mother TES_L4
TP_L4_00020.Visibility 0

TES_Pixel_L4.Copy TP_L4_00021
TP_L4_00021.Position 0 -1.395 0.775
TP_L4_00021.Mother TES_L4
TP_L4_00021.Visibility 0

TES_Pixel_L4.Copy TP_L4_00022
TP_L4_00022.Position 0 -1.395 0.93
TP_L4_00022.Mother TES_L4
TP_L4_00022.Visibility 0

TES_Pixel_L4.Copy TP_L4_00023
TP_L4_00023.Position 0 -1.24 -1.085
TP_L4_00023.Mother TES_L4
TP_L4_00023.Visibility 0

TES_Pixel_L4.Copy TP_L4_00024
TP_L4_00024.Position 0 -1.24 -0.93
TP_L4_00024.Mother TES_L4
TP_L4_00024.Visibility 0

TES_Pixel_L4.Copy TP_L4_00025
TP_L4_00025.Position 0 -1.24 -0.775
TP_L4_00025.Mother TES_L4
TP_L4_00025.Visibility 0

TES_Pixel_L4.Copy TP_L4_00026
TP_L4_00026.Position 0 -1.24 -0.62
TP_L4_00026.Mother TES_L4
TP_L4_00026.Visibility 0

TES_Pixel_L4.Copy TP_L4_00027
TP_L4_00027.Position 0 -1.24 -0.465
TP_L4_00027.Mother TES_L4
TP_L4_00027.Visibility 0

TES_Pixel_L4.Copy TP_L4_00028
TP_L4_00028.Position 0 -1.24 -0.31
TP_L4_00028.Mother TES_L4
TP_L4_00028.Visibility 0

TES_Pixel_L4.Copy TP_L4_00029
TP_L4_00029.Position 0 -1.24 -0.155
TP_L4_00029.Mother TES_L4
TP_L4_00029.Visibility 0

TES_Pixel_L4.Copy TP_L4_00030
TP_L4_00030.Position 0 -1.24 0
TP_L4_00030.Mother TES_L4
TP_L4_00030.Visibility 0

TES_Pixel_L4.Copy TP_L4_00031
TP_L4_00031.Position 0 -1.24 0.155
TP_L4_00031.Mother TES_L4
TP_L4_00031.Visibility 0

TES_Pixel_L4.Copy TP_L4_00032
TP_L4_00032.Position 0 -1.24 0.31
TP_L4_00032.Mother TES_L4
TP_L4_00032.Visibility 0

TES_Pixel_L4.Copy TP_L4_00033
TP_L4_00033.Position 0 -1.24 0.465
TP_L4_00033.Mother TES_L4
TP_L4_00033.Visibility 0

TES_Pixel_L4.Copy TP_L4_00034
TP_L4_00034.Position 0 -1.24 0.62
TP_L4_00034.Mother TES_L4
TP_L4_00034.Visibility 0

TES_Pixel_L4.Copy TP_L4_00035
TP_L4_00035.Position 0 -1.24 0.775
TP_L4_00035.Mother TES_L4
TP_L4_00035.Visibility 0

TES_Pixel_L4.Copy TP_L4_00036
TP_L4_00036.Position 0 -1.24 0.93
TP_L4_00036.Mother TES_L4
TP_L4_00036.Visibility 0

TES_Pixel_L4.Copy TP_L4_00037
TP_L4_00037.Position 0 -1.24 1.085
TP_L4_00037.Mother TES_L4
TP_L4_00037.Visibility 0

TES_Pixel_L4.Copy TP_L4_00038
TP_L4_00038.Position 0 -1.085 -1.24
TP_L4_00038.Mother TES_L4
TP_L4_00038.Visibility 0

TES_Pixel_L4.Copy TP_L4_00039
TP_L4_00039.Position 0 -1.085 -1.085
TP_L4_00039.Mother TES_L4
TP_L4_00039.Visibility 0

TES_Pixel_L4.Copy TP_L4_00040
TP_L4_00040.Position 0 -1.085 -0.93
TP_L4_00040.Mother TES_L4
TP_L4_00040.Visibility 0

TES_Pixel_L4.Copy TP_L4_00041
TP_L4_00041.Position 0 -1.085 -0.775
TP_L4_00041.Mother TES_L4
TP_L4_00041.Visibility 0

TES_Pixel_L4.Copy TP_L4_00042
TP_L4_00042.Position 0 -1.085 -0.62
TP_L4_00042.Mother TES_L4
TP_L4_00042.Visibility 0

TES_Pixel_L4.Copy TP_L4_00043
TP_L4_00043.Position 0 -1.085 -0.465
TP_L4_00043.Mother TES_L4
TP_L4_00043.Visibility 0

TES_Pixel_L4.Copy TP_L4_00044
TP_L4_00044.Position 0 -1.085 -0.31
TP_L4_00044.Mother TES_L4
TP_L4_00044.Visibility 0

TES_Pixel_L4.Copy TP_L4_00045
TP_L4_00045.Position 0 -1.085 -0.155
TP_L4_00045.Mother TES_L4
TP_L4_00045.Visibility 0

TES_Pixel_L4.Copy TP_L4_00046
TP_L4_00046.Position 0 -1.085 0
TP_L4_00046.Mother TES_L4
TP_L4_00046.Visibility 0

TES_Pixel_L4.Copy TP_L4_00047
TP_L4_00047.Position 0 -1.085 0.155
TP_L4_00047.Mother TES_L4
TP_L4_00047.Visibility 0

TES_Pixel_L4.Copy TP_L4_00048
TP_L4_00048.Position 0 -1.085 0.31
TP_L4_00048.Mother TES_L4
TP_L4_00048.Visibility 0

TES_Pixel_L4.Copy TP_L4_00049
TP_L4_00049.Position 0 -1.085 0.465
TP_L4_00049.Mother TES_L4
TP_L4_00049.Visibility 0

TES_Pixel_L4.Copy TP_L4_00050
TP_L4_00050.Position 0 -1.085 0.62
TP_L4_00050.Mother TES_L4
TP_L4_00050.Visibility 0

TES_Pixel_L4.Copy TP_L4_00051
TP_L4_00051.Position 0 -1.085 0.775
TP_L4_00051.Mother TES_L4
TP_L4_00051.Visibility 0

TES_Pixel_L4.Copy TP_L4_00052
TP_L4_00052.Position 0 -1.085 0.93
TP_L4_00052.Mother TES_L4
TP_L4_00052.Visibility 0

TES_Pixel_L4.Copy TP_L4_00053
TP_L4_00053.Position 0 -1.085 1.085
TP_L4_00053.Mother TES_L4
TP_L4_00053.Visibility 0

TES_Pixel_L4.Copy TP_L4_00054
TP_L4_00054.Position 0 -1.085 1.24
TP_L4_00054.Mother TES_L4
TP_L4_00054.Visibility 0

TES_Pixel_L4.Copy TP_L4_00055
TP_L4_00055.Position 0 -0.93 -1.395
TP_L4_00055.Mother TES_L4
TP_L4_00055.Visibility 0

TES_Pixel_L4.Copy TP_L4_00056
TP_L4_00056.Position 0 -0.93 -1.24
TP_L4_00056.Mother TES_L4
TP_L4_00056.Visibility 0

TES_Pixel_L4.Copy TP_L4_00057
TP_L4_00057.Position 0 -0.93 -1.085
TP_L4_00057.Mother TES_L4
TP_L4_00057.Visibility 0

TES_Pixel_L4.Copy TP_L4_00058
TP_L4_00058.Position 0 -0.93 -0.93
TP_L4_00058.Mother TES_L4
TP_L4_00058.Visibility 0

TES_Pixel_L4.Copy TP_L4_00059
TP_L4_00059.Position 0 -0.93 -0.775
TP_L4_00059.Mother TES_L4
TP_L4_00059.Visibility 0

TES_Pixel_L4.Copy TP_L4_00060
TP_L4_00060.Position 0 -0.93 -0.62
TP_L4_00060.Mother TES_L4
TP_L4_00060.Visibility 0

TES_Pixel_L4.Copy TP_L4_00061
TP_L4_00061.Position 0 -0.93 -0.465
TP_L4_00061.Mother TES_L4
TP_L4_00061.Visibility 0

TES_Pixel_L4.Copy TP_L4_00062
TP_L4_00062.Position 0 -0.93 -0.31
TP_L4_00062.Mother TES_L4
TP_L4_00062.Visibility 0

TES_Pixel_L4.Copy TP_L4_00063
TP_L4_00063.Position 0 -0.93 -0.155
TP_L4_00063.Mother TES_L4
TP_L4_00063.Visibility 0

TES_Pixel_L4.Copy TP_L4_00064
TP_L4_00064.Position 0 -0.93 0
TP_L4_00064.Mother TES_L4
TP_L4_00064.Visibility 0

TES_Pixel_L4.Copy TP_L4_00065
TP_L4_00065.Position 0 -0.93 0.155
TP_L4_00065.Mother TES_L4
TP_L4_00065.Visibility 0

TES_Pixel_L4.Copy TP_L4_00066
TP_L4_00066.Position 0 -0.93 0.31
TP_L4_00066.Mother TES_L4
TP_L4_00066.Visibility 0

TES_Pixel_L4.Copy TP_L4_00067
TP_L4_00067.Position 0 -0.93 0.465
TP_L4_00067.Mother TES_L4
TP_L4_00067.Visibility 0

TES_Pixel_L4.Copy TP_L4_00068
TP_L4_00068.Position 0 -0.93 0.62
TP_L4_00068.Mother TES_L4
TP_L4_00068.Visibility 0

TES_Pixel_L4.Copy TP_L4_00069
TP_L4_00069.Position 0 -0.93 0.775
TP_L4_00069.Mother TES_L4
TP_L4_00069.Visibility 0

TES_Pixel_L4.Copy TP_L4_00070
TP_L4_00070.Position 0 -0.93 0.93
TP_L4_00070.Mother TES_L4
TP_L4_00070.Visibility 0

TES_Pixel_L4.Copy TP_L4_00071
TP_L4_00071.Position 0 -0.93 1.085
TP_L4_00071.Mother TES_L4
TP_L4_00071.Visibility 0

TES_Pixel_L4.Copy TP_L4_00072
TP_L4_00072.Position 0 -0.93 1.24
TP_L4_00072.Mother TES_L4
TP_L4_00072.Visibility 0

TES_Pixel_L4.Copy TP_L4_00073
TP_L4_00073.Position 0 -0.93 1.395
TP_L4_00073.Mother TES_L4
TP_L4_00073.Visibility 0

TES_Pixel_L4.Copy TP_L4_00074
TP_L4_00074.Position 0 -0.775 -1.395
TP_L4_00074.Mother TES_L4
TP_L4_00074.Visibility 0

TES_Pixel_L4.Copy TP_L4_00075
TP_L4_00075.Position 0 -0.775 -1.24
TP_L4_00075.Mother TES_L4
TP_L4_00075.Visibility 0

TES_Pixel_L4.Copy TP_L4_00076
TP_L4_00076.Position 0 -0.775 -1.085
TP_L4_00076.Mother TES_L4
TP_L4_00076.Visibility 0

TES_Pixel_L4.Copy TP_L4_00077
TP_L4_00077.Position 0 -0.775 -0.93
TP_L4_00077.Mother TES_L4
TP_L4_00077.Visibility 0

TES_Pixel_L4.Copy TP_L4_00078
TP_L4_00078.Position 0 -0.775 -0.775
TP_L4_00078.Mother TES_L4
TP_L4_00078.Visibility 0

TES_Pixel_L4.Copy TP_L4_00079
TP_L4_00079.Position 0 -0.775 -0.62
TP_L4_00079.Mother TES_L4
TP_L4_00079.Visibility 0

TES_Pixel_L4.Copy TP_L4_00080
TP_L4_00080.Position 0 -0.775 -0.465
TP_L4_00080.Mother TES_L4
TP_L4_00080.Visibility 0

TES_Pixel_L4.Copy TP_L4_00081
TP_L4_00081.Position 0 -0.775 -0.31
TP_L4_00081.Mother TES_L4
TP_L4_00081.Visibility 0

TES_Pixel_L4.Copy TP_L4_00082
TP_L4_00082.Position 0 -0.775 -0.155
TP_L4_00082.Mother TES_L4
TP_L4_00082.Visibility 0

TES_Pixel_L4.Copy TP_L4_00083
TP_L4_00083.Position 0 -0.775 0
TP_L4_00083.Mother TES_L4
TP_L4_00083.Visibility 0

TES_Pixel_L4.Copy TP_L4_00084
TP_L4_00084.Position 0 -0.775 0.155
TP_L4_00084.Mother TES_L4
TP_L4_00084.Visibility 0

TES_Pixel_L4.Copy TP_L4_00085
TP_L4_00085.Position 0 -0.775 0.31
TP_L4_00085.Mother TES_L4
TP_L4_00085.Visibility 0

TES_Pixel_L4.Copy TP_L4_00086
TP_L4_00086.Position 0 -0.775 0.465
TP_L4_00086.Mother TES_L4
TP_L4_00086.Visibility 0

TES_Pixel_L4.Copy TP_L4_00087
TP_L4_00087.Position 0 -0.775 0.62
TP_L4_00087.Mother TES_L4
TP_L4_00087.Visibility 0

TES_Pixel_L4.Copy TP_L4_00088
TP_L4_00088.Position 0 -0.775 0.775
TP_L4_00088.Mother TES_L4
TP_L4_00088.Visibility 0

TES_Pixel_L4.Copy TP_L4_00089
TP_L4_00089.Position 0 -0.775 0.93
TP_L4_00089.Mother TES_L4
TP_L4_00089.Visibility 0

TES_Pixel_L4.Copy TP_L4_00090
TP_L4_00090.Position 0 -0.775 1.085
TP_L4_00090.Mother TES_L4
TP_L4_00090.Visibility 0

TES_Pixel_L4.Copy TP_L4_00091
TP_L4_00091.Position 0 -0.775 1.24
TP_L4_00091.Mother TES_L4
TP_L4_00091.Visibility 0

TES_Pixel_L4.Copy TP_L4_00092
TP_L4_00092.Position 0 -0.775 1.395
TP_L4_00092.Mother TES_L4
TP_L4_00092.Visibility 0

TES_Pixel_L4.Copy TP_L4_00093
TP_L4_00093.Position 0 -0.62 -1.55
TP_L4_00093.Mother TES_L4
TP_L4_00093.Visibility 0

TES_Pixel_L4.Copy TP_L4_00094
TP_L4_00094.Position 0 -0.62 -1.395
TP_L4_00094.Mother TES_L4
TP_L4_00094.Visibility 0

TES_Pixel_L4.Copy TP_L4_00095
TP_L4_00095.Position 0 -0.62 -1.24
TP_L4_00095.Mother TES_L4
TP_L4_00095.Visibility 0

TES_Pixel_L4.Copy TP_L4_00096
TP_L4_00096.Position 0 -0.62 -1.085
TP_L4_00096.Mother TES_L4
TP_L4_00096.Visibility 0

TES_Pixel_L4.Copy TP_L4_00097
TP_L4_00097.Position 0 -0.62 -0.93
TP_L4_00097.Mother TES_L4
TP_L4_00097.Visibility 0

TES_Pixel_L4.Copy TP_L4_00098
TP_L4_00098.Position 0 -0.62 -0.775
TP_L4_00098.Mother TES_L4
TP_L4_00098.Visibility 0

TES_Pixel_L4.Copy TP_L4_00099
TP_L4_00099.Position 0 -0.62 -0.62
TP_L4_00099.Mother TES_L4
TP_L4_00099.Visibility 0

TES_Pixel_L4.Copy TP_L4_00100
TP_L4_00100.Position 0 -0.62 -0.465
TP_L4_00100.Mother TES_L4
TP_L4_00100.Visibility 0

TES_Pixel_L4.Copy TP_L4_00101
TP_L4_00101.Position 0 -0.62 -0.31
TP_L4_00101.Mother TES_L4
TP_L4_00101.Visibility 0

TES_Pixel_L4.Copy TP_L4_00102
TP_L4_00102.Position 0 -0.62 -0.155
TP_L4_00102.Mother TES_L4
TP_L4_00102.Visibility 0

TES_Pixel_L4.Copy TP_L4_00103
TP_L4_00103.Position 0 -0.62 0
TP_L4_00103.Mother TES_L4
TP_L4_00103.Visibility 0

TES_Pixel_L4.Copy TP_L4_00104
TP_L4_00104.Position 0 -0.62 0.155
TP_L4_00104.Mother TES_L4
TP_L4_00104.Visibility 0

TES_Pixel_L4.Copy TP_L4_00105
TP_L4_00105.Position 0 -0.62 0.31
TP_L4_00105.Mother TES_L4
TP_L4_00105.Visibility 0

TES_Pixel_L4.Copy TP_L4_00106
TP_L4_00106.Position 0 -0.62 0.465
TP_L4_00106.Mother TES_L4
TP_L4_00106.Visibility 0

TES_Pixel_L4.Copy TP_L4_00107
TP_L4_00107.Position 0 -0.62 0.62
TP_L4_00107.Mother TES_L4
TP_L4_00107.Visibility 0

TES_Pixel_L4.Copy TP_L4_00108
TP_L4_00108.Position 0 -0.62 0.775
TP_L4_00108.Mother TES_L4
TP_L4_00108.Visibility 0

TES_Pixel_L4.Copy TP_L4_00109
TP_L4_00109.Position 0 -0.62 0.93
TP_L4_00109.Mother TES_L4
TP_L4_00109.Visibility 0

TES_Pixel_L4.Copy TP_L4_00110
TP_L4_00110.Position 0 -0.62 1.085
TP_L4_00110.Mother TES_L4
TP_L4_00110.Visibility 0

TES_Pixel_L4.Copy TP_L4_00111
TP_L4_00111.Position 0 -0.62 1.24
TP_L4_00111.Mother TES_L4
TP_L4_00111.Visibility 0

TES_Pixel_L4.Copy TP_L4_00112
TP_L4_00112.Position 0 -0.62 1.395
TP_L4_00112.Mother TES_L4
TP_L4_00112.Visibility 0

TES_Pixel_L4.Copy TP_L4_00113
TP_L4_00113.Position 0 -0.62 1.55
TP_L4_00113.Mother TES_L4
TP_L4_00113.Visibility 0

TES_Pixel_L4.Copy TP_L4_00114
TP_L4_00114.Position 0 -0.465 -1.55
TP_L4_00114.Mother TES_L4
TP_L4_00114.Visibility 0

TES_Pixel_L4.Copy TP_L4_00115
TP_L4_00115.Position 0 -0.465 -1.395
TP_L4_00115.Mother TES_L4
TP_L4_00115.Visibility 0

TES_Pixel_L4.Copy TP_L4_00116
TP_L4_00116.Position 0 -0.465 -1.24
TP_L4_00116.Mother TES_L4
TP_L4_00116.Visibility 0

TES_Pixel_L4.Copy TP_L4_00117
TP_L4_00117.Position 0 -0.465 -1.085
TP_L4_00117.Mother TES_L4
TP_L4_00117.Visibility 0

TES_Pixel_L4.Copy TP_L4_00118
TP_L4_00118.Position 0 -0.465 -0.93
TP_L4_00118.Mother TES_L4
TP_L4_00118.Visibility 0

TES_Pixel_L4.Copy TP_L4_00119
TP_L4_00119.Position 0 -0.465 -0.775
TP_L4_00119.Mother TES_L4
TP_L4_00119.Visibility 0

TES_Pixel_L4.Copy TP_L4_00120
TP_L4_00120.Position 0 -0.465 -0.62
TP_L4_00120.Mother TES_L4
TP_L4_00120.Visibility 0

TES_Pixel_L4.Copy TP_L4_00121
TP_L4_00121.Position 0 -0.465 -0.465
TP_L4_00121.Mother TES_L4
TP_L4_00121.Visibility 0

TES_Pixel_L4.Copy TP_L4_00122
TP_L4_00122.Position 0 -0.465 -0.31
TP_L4_00122.Mother TES_L4
TP_L4_00122.Visibility 0

TES_Pixel_L4.Copy TP_L4_00123
TP_L4_00123.Position 0 -0.465 -0.155
TP_L4_00123.Mother TES_L4
TP_L4_00123.Visibility 0

TES_Pixel_L4.Copy TP_L4_00124
TP_L4_00124.Position 0 -0.465 0
TP_L4_00124.Mother TES_L4
TP_L4_00124.Visibility 0

TES_Pixel_L4.Copy TP_L4_00125
TP_L4_00125.Position 0 -0.465 0.155
TP_L4_00125.Mother TES_L4
TP_L4_00125.Visibility 0

TES_Pixel_L4.Copy TP_L4_00126
TP_L4_00126.Position 0 -0.465 0.31
TP_L4_00126.Mother TES_L4
TP_L4_00126.Visibility 0

TES_Pixel_L4.Copy TP_L4_00127
TP_L4_00127.Position 0 -0.465 0.465
TP_L4_00127.Mother TES_L4
TP_L4_00127.Visibility 0

TES_Pixel_L4.Copy TP_L4_00128
TP_L4_00128.Position 0 -0.465 0.62
TP_L4_00128.Mother TES_L4
TP_L4_00128.Visibility 0

TES_Pixel_L4.Copy TP_L4_00129
TP_L4_00129.Position 0 -0.465 0.775
TP_L4_00129.Mother TES_L4
TP_L4_00129.Visibility 0

TES_Pixel_L4.Copy TP_L4_00130
TP_L4_00130.Position 0 -0.465 0.93
TP_L4_00130.Mother TES_L4
TP_L4_00130.Visibility 0

TES_Pixel_L4.Copy TP_L4_00131
TP_L4_00131.Position 0 -0.465 1.085
TP_L4_00131.Mother TES_L4
TP_L4_00131.Visibility 0

TES_Pixel_L4.Copy TP_L4_00132
TP_L4_00132.Position 0 -0.465 1.24
TP_L4_00132.Mother TES_L4
TP_L4_00132.Visibility 0

TES_Pixel_L4.Copy TP_L4_00133
TP_L4_00133.Position 0 -0.465 1.395
TP_L4_00133.Mother TES_L4
TP_L4_00133.Visibility 0

TES_Pixel_L4.Copy TP_L4_00134
TP_L4_00134.Position 0 -0.465 1.55
TP_L4_00134.Mother TES_L4
TP_L4_00134.Visibility 0

TES_Pixel_L4.Copy TP_L4_00135
TP_L4_00135.Position 0 -0.31 -1.55
TP_L4_00135.Mother TES_L4
TP_L4_00135.Visibility 0

TES_Pixel_L4.Copy TP_L4_00136
TP_L4_00136.Position 0 -0.31 -1.395
TP_L4_00136.Mother TES_L4
TP_L4_00136.Visibility 0

TES_Pixel_L4.Copy TP_L4_00137
TP_L4_00137.Position 0 -0.31 -1.24
TP_L4_00137.Mother TES_L4
TP_L4_00137.Visibility 0

TES_Pixel_L4.Copy TP_L4_00138
TP_L4_00138.Position 0 -0.31 -1.085
TP_L4_00138.Mother TES_L4
TP_L4_00138.Visibility 0

TES_Pixel_L4.Copy TP_L4_00139
TP_L4_00139.Position 0 -0.31 -0.93
TP_L4_00139.Mother TES_L4
TP_L4_00139.Visibility 0

TES_Pixel_L4.Copy TP_L4_00140
TP_L4_00140.Position 0 -0.31 -0.775
TP_L4_00140.Mother TES_L4
TP_L4_00140.Visibility 0

TES_Pixel_L4.Copy TP_L4_00141
TP_L4_00141.Position 0 -0.31 -0.62
TP_L4_00141.Mother TES_L4
TP_L4_00141.Visibility 0

TES_Pixel_L4.Copy TP_L4_00142
TP_L4_00142.Position 0 -0.31 -0.465
TP_L4_00142.Mother TES_L4
TP_L4_00142.Visibility 0

TES_Pixel_L4.Copy TP_L4_00143
TP_L4_00143.Position 0 -0.31 -0.31
TP_L4_00143.Mother TES_L4
TP_L4_00143.Visibility 0

TES_Pixel_L4.Copy TP_L4_00144
TP_L4_00144.Position 0 -0.31 -0.155
TP_L4_00144.Mother TES_L4
TP_L4_00144.Visibility 0

TES_Pixel_L4.Copy TP_L4_00145
TP_L4_00145.Position 0 -0.31 0
TP_L4_00145.Mother TES_L4
TP_L4_00145.Visibility 0

TES_Pixel_L4.Copy TP_L4_00146
TP_L4_00146.Position 0 -0.31 0.155
TP_L4_00146.Mother TES_L4
TP_L4_00146.Visibility 0

TES_Pixel_L4.Copy TP_L4_00147
TP_L4_00147.Position 0 -0.31 0.31
TP_L4_00147.Mother TES_L4
TP_L4_00147.Visibility 0

TES_Pixel_L4.Copy TP_L4_00148
TP_L4_00148.Position 0 -0.31 0.465
TP_L4_00148.Mother TES_L4
TP_L4_00148.Visibility 0

TES_Pixel_L4.Copy TP_L4_00149
TP_L4_00149.Position 0 -0.31 0.62
TP_L4_00149.Mother TES_L4
TP_L4_00149.Visibility 0

TES_Pixel_L4.Copy TP_L4_00150
TP_L4_00150.Position 0 -0.31 0.775
TP_L4_00150.Mother TES_L4
TP_L4_00150.Visibility 0

TES_Pixel_L4.Copy TP_L4_00151
TP_L4_00151.Position 0 -0.31 0.93
TP_L4_00151.Mother TES_L4
TP_L4_00151.Visibility 0

TES_Pixel_L4.Copy TP_L4_00152
TP_L4_00152.Position 0 -0.31 1.085
TP_L4_00152.Mother TES_L4
TP_L4_00152.Visibility 0

TES_Pixel_L4.Copy TP_L4_00153
TP_L4_00153.Position 0 -0.31 1.24
TP_L4_00153.Mother TES_L4
TP_L4_00153.Visibility 0

TES_Pixel_L4.Copy TP_L4_00154
TP_L4_00154.Position 0 -0.31 1.395
TP_L4_00154.Mother TES_L4
TP_L4_00154.Visibility 0

TES_Pixel_L4.Copy TP_L4_00155
TP_L4_00155.Position 0 -0.31 1.55
TP_L4_00155.Mother TES_L4
TP_L4_00155.Visibility 0

TES_Pixel_L4.Copy TP_L4_00156
TP_L4_00156.Position 0 -0.155 -1.55
TP_L4_00156.Mother TES_L4
TP_L4_00156.Visibility 0

TES_Pixel_L4.Copy TP_L4_00157
TP_L4_00157.Position 0 -0.155 -1.395
TP_L4_00157.Mother TES_L4
TP_L4_00157.Visibility 0

TES_Pixel_L4.Copy TP_L4_00158
TP_L4_00158.Position 0 -0.155 -1.24
TP_L4_00158.Mother TES_L4
TP_L4_00158.Visibility 0

TES_Pixel_L4.Copy TP_L4_00159
TP_L4_00159.Position 0 -0.155 -1.085
TP_L4_00159.Mother TES_L4
TP_L4_00159.Visibility 0

TES_Pixel_L4.Copy TP_L4_00160
TP_L4_00160.Position 0 -0.155 -0.93
TP_L4_00160.Mother TES_L4
TP_L4_00160.Visibility 0

TES_Pixel_L4.Copy TP_L4_00161
TP_L4_00161.Position 0 -0.155 -0.775
TP_L4_00161.Mother TES_L4
TP_L4_00161.Visibility 0

TES_Pixel_L4.Copy TP_L4_00162
TP_L4_00162.Position 0 -0.155 -0.62
TP_L4_00162.Mother TES_L4
TP_L4_00162.Visibility 0

TES_Pixel_L4.Copy TP_L4_00163
TP_L4_00163.Position 0 -0.155 -0.465
TP_L4_00163.Mother TES_L4
TP_L4_00163.Visibility 0

TES_Pixel_L4.Copy TP_L4_00164
TP_L4_00164.Position 0 -0.155 -0.31
TP_L4_00164.Mother TES_L4
TP_L4_00164.Visibility 0

TES_Pixel_L4.Copy TP_L4_00165
TP_L4_00165.Position 0 -0.155 -0.155
TP_L4_00165.Mother TES_L4
TP_L4_00165.Visibility 0

TES_Pixel_L4.Copy TP_L4_00166
TP_L4_00166.Position 0 -0.155 0
TP_L4_00166.Mother TES_L4
TP_L4_00166.Visibility 0

TES_Pixel_L4.Copy TP_L4_00167
TP_L4_00167.Position 0 -0.155 0.155
TP_L4_00167.Mother TES_L4
TP_L4_00167.Visibility 0

TES_Pixel_L4.Copy TP_L4_00168
TP_L4_00168.Position 0 -0.155 0.31
TP_L4_00168.Mother TES_L4
TP_L4_00168.Visibility 0

TES_Pixel_L4.Copy TP_L4_00169
TP_L4_00169.Position 0 -0.155 0.465
TP_L4_00169.Mother TES_L4
TP_L4_00169.Visibility 0

TES_Pixel_L4.Copy TP_L4_00170
TP_L4_00170.Position 0 -0.155 0.62
TP_L4_00170.Mother TES_L4
TP_L4_00170.Visibility 0

TES_Pixel_L4.Copy TP_L4_00171
TP_L4_00171.Position 0 -0.155 0.775
TP_L4_00171.Mother TES_L4
TP_L4_00171.Visibility 0

TES_Pixel_L4.Copy TP_L4_00172
TP_L4_00172.Position 0 -0.155 0.93
TP_L4_00172.Mother TES_L4
TP_L4_00172.Visibility 0

TES_Pixel_L4.Copy TP_L4_00173
TP_L4_00173.Position 0 -0.155 1.085
TP_L4_00173.Mother TES_L4
TP_L4_00173.Visibility 0

TES_Pixel_L4.Copy TP_L4_00174
TP_L4_00174.Position 0 -0.155 1.24
TP_L4_00174.Mother TES_L4
TP_L4_00174.Visibility 0

TES_Pixel_L4.Copy TP_L4_00175
TP_L4_00175.Position 0 -0.155 1.395
TP_L4_00175.Mother TES_L4
TP_L4_00175.Visibility 0

TES_Pixel_L4.Copy TP_L4_00176
TP_L4_00176.Position 0 -0.155 1.55
TP_L4_00176.Mother TES_L4
TP_L4_00176.Visibility 0

TES_Pixel_L4.Copy TP_L4_00177
TP_L4_00177.Position 0 0 -1.705
TP_L4_00177.Mother TES_L4
TP_L4_00177.Visibility 0

TES_Pixel_L4.Copy TP_L4_00178
TP_L4_00178.Position 0 0 -1.55
TP_L4_00178.Mother TES_L4
TP_L4_00178.Visibility 0

TES_Pixel_L4.Copy TP_L4_00179
TP_L4_00179.Position 0 0 -1.395
TP_L4_00179.Mother TES_L4
TP_L4_00179.Visibility 0

TES_Pixel_L4.Copy TP_L4_00180
TP_L4_00180.Position 0 0 -1.24
TP_L4_00180.Mother TES_L4
TP_L4_00180.Visibility 0

TES_Pixel_L4.Copy TP_L4_00181
TP_L4_00181.Position 0 0 -1.085
TP_L4_00181.Mother TES_L4
TP_L4_00181.Visibility 0

TES_Pixel_L4.Copy TP_L4_00182
TP_L4_00182.Position 0 0 -0.93
TP_L4_00182.Mother TES_L4
TP_L4_00182.Visibility 0

TES_Pixel_L4.Copy TP_L4_00183
TP_L4_00183.Position 0 0 -0.775
TP_L4_00183.Mother TES_L4
TP_L4_00183.Visibility 0

TES_Pixel_L4.Copy TP_L4_00184
TP_L4_00184.Position 0 0 -0.62
TP_L4_00184.Mother TES_L4
TP_L4_00184.Visibility 0

TES_Pixel_L4.Copy TP_L4_00185
TP_L4_00185.Position 0 0 -0.465
TP_L4_00185.Mother TES_L4
TP_L4_00185.Visibility 0

TES_Pixel_L4.Copy TP_L4_00186
TP_L4_00186.Position 0 0 -0.31
TP_L4_00186.Mother TES_L4
TP_L4_00186.Visibility 0

TES_Pixel_L4.Copy TP_L4_00187
TP_L4_00187.Position 0 0 -0.155
TP_L4_00187.Mother TES_L4
TP_L4_00187.Visibility 0

TES_Pixel_L4.Copy TP_L4_00188
TP_L4_00188.Position 0 0 0
TP_L4_00188.Mother TES_L4
TP_L4_00188.Visibility 0

TES_Pixel_L4.Copy TP_L4_00189
TP_L4_00189.Position 0 0 0.155
TP_L4_00189.Mother TES_L4
TP_L4_00189.Visibility 0

TES_Pixel_L4.Copy TP_L4_00190
TP_L4_00190.Position 0 0 0.31
TP_L4_00190.Mother TES_L4
TP_L4_00190.Visibility 0

TES_Pixel_L4.Copy TP_L4_00191
TP_L4_00191.Position 0 0 0.465
TP_L4_00191.Mother TES_L4
TP_L4_00191.Visibility 0

TES_Pixel_L4.Copy TP_L4_00192
TP_L4_00192.Position 0 0 0.62
TP_L4_00192.Mother TES_L4
TP_L4_00192.Visibility 0

TES_Pixel_L4.Copy TP_L4_00193
TP_L4_00193.Position 0 0 0.775
TP_L4_00193.Mother TES_L4
TP_L4_00193.Visibility 0

TES_Pixel_L4.Copy TP_L4_00194
TP_L4_00194.Position 0 0 0.93
TP_L4_00194.Mother TES_L4
TP_L4_00194.Visibility 0

TES_Pixel_L4.Copy TP_L4_00195
TP_L4_00195.Position 0 0 1.085
TP_L4_00195.Mother TES_L4
TP_L4_00195.Visibility 0

TES_Pixel_L4.Copy TP_L4_00196
TP_L4_00196.Position 0 0 1.24
TP_L4_00196.Mother TES_L4
TP_L4_00196.Visibility 0

TES_Pixel_L4.Copy TP_L4_00197
TP_L4_00197.Position 0 0 1.395
TP_L4_00197.Mother TES_L4
TP_L4_00197.Visibility 0

TES_Pixel_L4.Copy TP_L4_00198
TP_L4_00198.Position 0 0 1.55
TP_L4_00198.Mother TES_L4
TP_L4_00198.Visibility 0

TES_Pixel_L4.Copy TP_L4_00199
TP_L4_00199.Position 0 0 1.705
TP_L4_00199.Mother TES_L4
TP_L4_00199.Visibility 0

TES_Pixel_L4.Copy TP_L4_00200
TP_L4_00200.Position 0 0.155 -1.55
TP_L4_00200.Mother TES_L4
TP_L4_00200.Visibility 0

TES_Pixel_L4.Copy TP_L4_00201
TP_L4_00201.Position 0 0.155 -1.395
TP_L4_00201.Mother TES_L4
TP_L4_00201.Visibility 0

TES_Pixel_L4.Copy TP_L4_00202
TP_L4_00202.Position 0 0.155 -1.24
TP_L4_00202.Mother TES_L4
TP_L4_00202.Visibility 0

TES_Pixel_L4.Copy TP_L4_00203
TP_L4_00203.Position 0 0.155 -1.085
TP_L4_00203.Mother TES_L4
TP_L4_00203.Visibility 0

TES_Pixel_L4.Copy TP_L4_00204
TP_L4_00204.Position 0 0.155 -0.93
TP_L4_00204.Mother TES_L4
TP_L4_00204.Visibility 0

TES_Pixel_L4.Copy TP_L4_00205
TP_L4_00205.Position 0 0.155 -0.775
TP_L4_00205.Mother TES_L4
TP_L4_00205.Visibility 0

TES_Pixel_L4.Copy TP_L4_00206
TP_L4_00206.Position 0 0.155 -0.62
TP_L4_00206.Mother TES_L4
TP_L4_00206.Visibility 0

TES_Pixel_L4.Copy TP_L4_00207
TP_L4_00207.Position 0 0.155 -0.465
TP_L4_00207.Mother TES_L4
TP_L4_00207.Visibility 0

TES_Pixel_L4.Copy TP_L4_00208
TP_L4_00208.Position 0 0.155 -0.31
TP_L4_00208.Mother TES_L4
TP_L4_00208.Visibility 0

TES_Pixel_L4.Copy TP_L4_00209
TP_L4_00209.Position 0 0.155 -0.155
TP_L4_00209.Mother TES_L4
TP_L4_00209.Visibility 0

TES_Pixel_L4.Copy TP_L4_00210
TP_L4_00210.Position 0 0.155 0
TP_L4_00210.Mother TES_L4
TP_L4_00210.Visibility 0

TES_Pixel_L4.Copy TP_L4_00211
TP_L4_00211.Position 0 0.155 0.155
TP_L4_00211.Mother TES_L4
TP_L4_00211.Visibility 0

TES_Pixel_L4.Copy TP_L4_00212
TP_L4_00212.Position 0 0.155 0.31
TP_L4_00212.Mother TES_L4
TP_L4_00212.Visibility 0

TES_Pixel_L4.Copy TP_L4_00213
TP_L4_00213.Position 0 0.155 0.465
TP_L4_00213.Mother TES_L4
TP_L4_00213.Visibility 0

TES_Pixel_L4.Copy TP_L4_00214
TP_L4_00214.Position 0 0.155 0.62
TP_L4_00214.Mother TES_L4
TP_L4_00214.Visibility 0

TES_Pixel_L4.Copy TP_L4_00215
TP_L4_00215.Position 0 0.155 0.775
TP_L4_00215.Mother TES_L4
TP_L4_00215.Visibility 0

TES_Pixel_L4.Copy TP_L4_00216
TP_L4_00216.Position 0 0.155 0.93
TP_L4_00216.Mother TES_L4
TP_L4_00216.Visibility 0

TES_Pixel_L4.Copy TP_L4_00217
TP_L4_00217.Position 0 0.155 1.085
TP_L4_00217.Mother TES_L4
TP_L4_00217.Visibility 0

TES_Pixel_L4.Copy TP_L4_00218
TP_L4_00218.Position 0 0.155 1.24
TP_L4_00218.Mother TES_L4
TP_L4_00218.Visibility 0

TES_Pixel_L4.Copy TP_L4_00219
TP_L4_00219.Position 0 0.155 1.395
TP_L4_00219.Mother TES_L4
TP_L4_00219.Visibility 0

TES_Pixel_L4.Copy TP_L4_00220
TP_L4_00220.Position 0 0.155 1.55
TP_L4_00220.Mother TES_L4
TP_L4_00220.Visibility 0

TES_Pixel_L4.Copy TP_L4_00221
TP_L4_00221.Position 0 0.31 -1.55
TP_L4_00221.Mother TES_L4
TP_L4_00221.Visibility 0

TES_Pixel_L4.Copy TP_L4_00222
TP_L4_00222.Position 0 0.31 -1.395
TP_L4_00222.Mother TES_L4
TP_L4_00222.Visibility 0

TES_Pixel_L4.Copy TP_L4_00223
TP_L4_00223.Position 0 0.31 -1.24
TP_L4_00223.Mother TES_L4
TP_L4_00223.Visibility 0

TES_Pixel_L4.Copy TP_L4_00224
TP_L4_00224.Position 0 0.31 -1.085
TP_L4_00224.Mother TES_L4
TP_L4_00224.Visibility 0

TES_Pixel_L4.Copy TP_L4_00225
TP_L4_00225.Position 0 0.31 -0.93
TP_L4_00225.Mother TES_L4
TP_L4_00225.Visibility 0

TES_Pixel_L4.Copy TP_L4_00226
TP_L4_00226.Position 0 0.31 -0.775
TP_L4_00226.Mother TES_L4
TP_L4_00226.Visibility 0

TES_Pixel_L4.Copy TP_L4_00227
TP_L4_00227.Position 0 0.31 -0.62
TP_L4_00227.Mother TES_L4
TP_L4_00227.Visibility 0

TES_Pixel_L4.Copy TP_L4_00228
TP_L4_00228.Position 0 0.31 -0.465
TP_L4_00228.Mother TES_L4
TP_L4_00228.Visibility 0

TES_Pixel_L4.Copy TP_L4_00229
TP_L4_00229.Position 0 0.31 -0.31
TP_L4_00229.Mother TES_L4
TP_L4_00229.Visibility 0

TES_Pixel_L4.Copy TP_L4_00230
TP_L4_00230.Position 0 0.31 -0.155
TP_L4_00230.Mother TES_L4
TP_L4_00230.Visibility 0

TES_Pixel_L4.Copy TP_L4_00231
TP_L4_00231.Position 0 0.31 0
TP_L4_00231.Mother TES_L4
TP_L4_00231.Visibility 0

TES_Pixel_L4.Copy TP_L4_00232
TP_L4_00232.Position 0 0.31 0.155
TP_L4_00232.Mother TES_L4
TP_L4_00232.Visibility 0

TES_Pixel_L4.Copy TP_L4_00233
TP_L4_00233.Position 0 0.31 0.31
TP_L4_00233.Mother TES_L4
TP_L4_00233.Visibility 0

TES_Pixel_L4.Copy TP_L4_00234
TP_L4_00234.Position 0 0.31 0.465
TP_L4_00234.Mother TES_L4
TP_L4_00234.Visibility 0

TES_Pixel_L4.Copy TP_L4_00235
TP_L4_00235.Position 0 0.31 0.62
TP_L4_00235.Mother TES_L4
TP_L4_00235.Visibility 0

TES_Pixel_L4.Copy TP_L4_00236
TP_L4_00236.Position 0 0.31 0.775
TP_L4_00236.Mother TES_L4
TP_L4_00236.Visibility 0

TES_Pixel_L4.Copy TP_L4_00237
TP_L4_00237.Position 0 0.31 0.93
TP_L4_00237.Mother TES_L4
TP_L4_00237.Visibility 0

TES_Pixel_L4.Copy TP_L4_00238
TP_L4_00238.Position 0 0.31 1.085
TP_L4_00238.Mother TES_L4
TP_L4_00238.Visibility 0

TES_Pixel_L4.Copy TP_L4_00239
TP_L4_00239.Position 0 0.31 1.24
TP_L4_00239.Mother TES_L4
TP_L4_00239.Visibility 0

TES_Pixel_L4.Copy TP_L4_00240
TP_L4_00240.Position 0 0.31 1.395
TP_L4_00240.Mother TES_L4
TP_L4_00240.Visibility 0

TES_Pixel_L4.Copy TP_L4_00241
TP_L4_00241.Position 0 0.31 1.55
TP_L4_00241.Mother TES_L4
TP_L4_00241.Visibility 0

TES_Pixel_L4.Copy TP_L4_00242
TP_L4_00242.Position 0 0.465 -1.55
TP_L4_00242.Mother TES_L4
TP_L4_00242.Visibility 0

TES_Pixel_L4.Copy TP_L4_00243
TP_L4_00243.Position 0 0.465 -1.395
TP_L4_00243.Mother TES_L4
TP_L4_00243.Visibility 0

TES_Pixel_L4.Copy TP_L4_00244
TP_L4_00244.Position 0 0.465 -1.24
TP_L4_00244.Mother TES_L4
TP_L4_00244.Visibility 0

TES_Pixel_L4.Copy TP_L4_00245
TP_L4_00245.Position 0 0.465 -1.085
TP_L4_00245.Mother TES_L4
TP_L4_00245.Visibility 0

TES_Pixel_L4.Copy TP_L4_00246
TP_L4_00246.Position 0 0.465 -0.93
TP_L4_00246.Mother TES_L4
TP_L4_00246.Visibility 0

TES_Pixel_L4.Copy TP_L4_00247
TP_L4_00247.Position 0 0.465 -0.775
TP_L4_00247.Mother TES_L4
TP_L4_00247.Visibility 0

TES_Pixel_L4.Copy TP_L4_00248
TP_L4_00248.Position 0 0.465 -0.62
TP_L4_00248.Mother TES_L4
TP_L4_00248.Visibility 0

TES_Pixel_L4.Copy TP_L4_00249
TP_L4_00249.Position 0 0.465 -0.465
TP_L4_00249.Mother TES_L4
TP_L4_00249.Visibility 0

TES_Pixel_L4.Copy TP_L4_00250
TP_L4_00250.Position 0 0.465 -0.31
TP_L4_00250.Mother TES_L4
TP_L4_00250.Visibility 0

TES_Pixel_L4.Copy TP_L4_00251
TP_L4_00251.Position 0 0.465 -0.155
TP_L4_00251.Mother TES_L4
TP_L4_00251.Visibility 0

TES_Pixel_L4.Copy TP_L4_00252
TP_L4_00252.Position 0 0.465 0
TP_L4_00252.Mother TES_L4
TP_L4_00252.Visibility 0

TES_Pixel_L4.Copy TP_L4_00253
TP_L4_00253.Position 0 0.465 0.155
TP_L4_00253.Mother TES_L4
TP_L4_00253.Visibility 0

TES_Pixel_L4.Copy TP_L4_00254
TP_L4_00254.Position 0 0.465 0.31
TP_L4_00254.Mother TES_L4
TP_L4_00254.Visibility 0

TES_Pixel_L4.Copy TP_L4_00255
TP_L4_00255.Position 0 0.465 0.465
TP_L4_00255.Mother TES_L4
TP_L4_00255.Visibility 0

TES_Pixel_L4.Copy TP_L4_00256
TP_L4_00256.Position 0 0.465 0.62
TP_L4_00256.Mother TES_L4
TP_L4_00256.Visibility 0

TES_Pixel_L4.Copy TP_L4_00257
TP_L4_00257.Position 0 0.465 0.775
TP_L4_00257.Mother TES_L4
TP_L4_00257.Visibility 0

TES_Pixel_L4.Copy TP_L4_00258
TP_L4_00258.Position 0 0.465 0.93
TP_L4_00258.Mother TES_L4
TP_L4_00258.Visibility 0

TES_Pixel_L4.Copy TP_L4_00259
TP_L4_00259.Position 0 0.465 1.085
TP_L4_00259.Mother TES_L4
TP_L4_00259.Visibility 0

TES_Pixel_L4.Copy TP_L4_00260
TP_L4_00260.Position 0 0.465 1.24
TP_L4_00260.Mother TES_L4
TP_L4_00260.Visibility 0

TES_Pixel_L4.Copy TP_L4_00261
TP_L4_00261.Position 0 0.465 1.395
TP_L4_00261.Mother TES_L4
TP_L4_00261.Visibility 0

TES_Pixel_L4.Copy TP_L4_00262
TP_L4_00262.Position 0 0.465 1.55
TP_L4_00262.Mother TES_L4
TP_L4_00262.Visibility 0

TES_Pixel_L4.Copy TP_L4_00263
TP_L4_00263.Position 0 0.62 -1.55
TP_L4_00263.Mother TES_L4
TP_L4_00263.Visibility 0

TES_Pixel_L4.Copy TP_L4_00264
TP_L4_00264.Position 0 0.62 -1.395
TP_L4_00264.Mother TES_L4
TP_L4_00264.Visibility 0

TES_Pixel_L4.Copy TP_L4_00265
TP_L4_00265.Position 0 0.62 -1.24
TP_L4_00265.Mother TES_L4
TP_L4_00265.Visibility 0

TES_Pixel_L4.Copy TP_L4_00266
TP_L4_00266.Position 0 0.62 -1.085
TP_L4_00266.Mother TES_L4
TP_L4_00266.Visibility 0

TES_Pixel_L4.Copy TP_L4_00267
TP_L4_00267.Position 0 0.62 -0.93
TP_L4_00267.Mother TES_L4
TP_L4_00267.Visibility 0

TES_Pixel_L4.Copy TP_L4_00268
TP_L4_00268.Position 0 0.62 -0.775
TP_L4_00268.Mother TES_L4
TP_L4_00268.Visibility 0

TES_Pixel_L4.Copy TP_L4_00269
TP_L4_00269.Position 0 0.62 -0.62
TP_L4_00269.Mother TES_L4
TP_L4_00269.Visibility 0

TES_Pixel_L4.Copy TP_L4_00270
TP_L4_00270.Position 0 0.62 -0.465
TP_L4_00270.Mother TES_L4
TP_L4_00270.Visibility 0

TES_Pixel_L4.Copy TP_L4_00271
TP_L4_00271.Position 0 0.62 -0.31
TP_L4_00271.Mother TES_L4
TP_L4_00271.Visibility 0

TES_Pixel_L4.Copy TP_L4_00272
TP_L4_00272.Position 0 0.62 -0.155
TP_L4_00272.Mother TES_L4
TP_L4_00272.Visibility 0

TES_Pixel_L4.Copy TP_L4_00273
TP_L4_00273.Position 0 0.62 0
TP_L4_00273.Mother TES_L4
TP_L4_00273.Visibility 0

TES_Pixel_L4.Copy TP_L4_00274
TP_L4_00274.Position 0 0.62 0.155
TP_L4_00274.Mother TES_L4
TP_L4_00274.Visibility 0

TES_Pixel_L4.Copy TP_L4_00275
TP_L4_00275.Position 0 0.62 0.31
TP_L4_00275.Mother TES_L4
TP_L4_00275.Visibility 0

TES_Pixel_L4.Copy TP_L4_00276
TP_L4_00276.Position 0 0.62 0.465
TP_L4_00276.Mother TES_L4
TP_L4_00276.Visibility 0

TES_Pixel_L4.Copy TP_L4_00277
TP_L4_00277.Position 0 0.62 0.62
TP_L4_00277.Mother TES_L4
TP_L4_00277.Visibility 0

TES_Pixel_L4.Copy TP_L4_00278
TP_L4_00278.Position 0 0.62 0.775
TP_L4_00278.Mother TES_L4
TP_L4_00278.Visibility 0

TES_Pixel_L4.Copy TP_L4_00279
TP_L4_00279.Position 0 0.62 0.93
TP_L4_00279.Mother TES_L4
TP_L4_00279.Visibility 0

TES_Pixel_L4.Copy TP_L4_00280
TP_L4_00280.Position 0 0.62 1.085
TP_L4_00280.Mother TES_L4
TP_L4_00280.Visibility 0

TES_Pixel_L4.Copy TP_L4_00281
TP_L4_00281.Position 0 0.62 1.24
TP_L4_00281.Mother TES_L4
TP_L4_00281.Visibility 0

TES_Pixel_L4.Copy TP_L4_00282
TP_L4_00282.Position 0 0.62 1.395
TP_L4_00282.Mother TES_L4
TP_L4_00282.Visibility 0

TES_Pixel_L4.Copy TP_L4_00283
TP_L4_00283.Position 0 0.62 1.55
TP_L4_00283.Mother TES_L4
TP_L4_00283.Visibility 0

TES_Pixel_L4.Copy TP_L4_00284
TP_L4_00284.Position 0 0.775 -1.395
TP_L4_00284.Mother TES_L4
TP_L4_00284.Visibility 0

TES_Pixel_L4.Copy TP_L4_00285
TP_L4_00285.Position 0 0.775 -1.24
TP_L4_00285.Mother TES_L4
TP_L4_00285.Visibility 0

TES_Pixel_L4.Copy TP_L4_00286
TP_L4_00286.Position 0 0.775 -1.085
TP_L4_00286.Mother TES_L4
TP_L4_00286.Visibility 0

TES_Pixel_L4.Copy TP_L4_00287
TP_L4_00287.Position 0 0.775 -0.93
TP_L4_00287.Mother TES_L4
TP_L4_00287.Visibility 0

TES_Pixel_L4.Copy TP_L4_00288
TP_L4_00288.Position 0 0.775 -0.775
TP_L4_00288.Mother TES_L4
TP_L4_00288.Visibility 0

TES_Pixel_L4.Copy TP_L4_00289
TP_L4_00289.Position 0 0.775 -0.62
TP_L4_00289.Mother TES_L4
TP_L4_00289.Visibility 0

TES_Pixel_L4.Copy TP_L4_00290
TP_L4_00290.Position 0 0.775 -0.465
TP_L4_00290.Mother TES_L4
TP_L4_00290.Visibility 0

TES_Pixel_L4.Copy TP_L4_00291
TP_L4_00291.Position 0 0.775 -0.31
TP_L4_00291.Mother TES_L4
TP_L4_00291.Visibility 0

TES_Pixel_L4.Copy TP_L4_00292
TP_L4_00292.Position 0 0.775 -0.155
TP_L4_00292.Mother TES_L4
TP_L4_00292.Visibility 0

TES_Pixel_L4.Copy TP_L4_00293
TP_L4_00293.Position 0 0.775 0
TP_L4_00293.Mother TES_L4
TP_L4_00293.Visibility 0

TES_Pixel_L4.Copy TP_L4_00294
TP_L4_00294.Position 0 0.775 0.155
TP_L4_00294.Mother TES_L4
TP_L4_00294.Visibility 0

TES_Pixel_L4.Copy TP_L4_00295
TP_L4_00295.Position 0 0.775 0.31
TP_L4_00295.Mother TES_L4
TP_L4_00295.Visibility 0

TES_Pixel_L4.Copy TP_L4_00296
TP_L4_00296.Position 0 0.775 0.465
TP_L4_00296.Mother TES_L4
TP_L4_00296.Visibility 0

TES_Pixel_L4.Copy TP_L4_00297
TP_L4_00297.Position 0 0.775 0.62
TP_L4_00297.Mother TES_L4
TP_L4_00297.Visibility 0

TES_Pixel_L4.Copy TP_L4_00298
TP_L4_00298.Position 0 0.775 0.775
TP_L4_00298.Mother TES_L4
TP_L4_00298.Visibility 0

TES_Pixel_L4.Copy TP_L4_00299
TP_L4_00299.Position 0 0.775 0.93
TP_L4_00299.Mother TES_L4
TP_L4_00299.Visibility 0

TES_Pixel_L4.Copy TP_L4_00300
TP_L4_00300.Position 0 0.775 1.085
TP_L4_00300.Mother TES_L4
TP_L4_00300.Visibility 0

TES_Pixel_L4.Copy TP_L4_00301
TP_L4_00301.Position 0 0.775 1.24
TP_L4_00301.Mother TES_L4
TP_L4_00301.Visibility 0

TES_Pixel_L4.Copy TP_L4_00302
TP_L4_00302.Position 0 0.775 1.395
TP_L4_00302.Mother TES_L4
TP_L4_00302.Visibility 0

TES_Pixel_L4.Copy TP_L4_00303
TP_L4_00303.Position 0 0.93 -1.395
TP_L4_00303.Mother TES_L4
TP_L4_00303.Visibility 0

TES_Pixel_L4.Copy TP_L4_00304
TP_L4_00304.Position 0 0.93 -1.24
TP_L4_00304.Mother TES_L4
TP_L4_00304.Visibility 0

TES_Pixel_L4.Copy TP_L4_00305
TP_L4_00305.Position 0 0.93 -1.085
TP_L4_00305.Mother TES_L4
TP_L4_00305.Visibility 0

TES_Pixel_L4.Copy TP_L4_00306
TP_L4_00306.Position 0 0.93 -0.93
TP_L4_00306.Mother TES_L4
TP_L4_00306.Visibility 0

TES_Pixel_L4.Copy TP_L4_00307
TP_L4_00307.Position 0 0.93 -0.775
TP_L4_00307.Mother TES_L4
TP_L4_00307.Visibility 0

TES_Pixel_L4.Copy TP_L4_00308
TP_L4_00308.Position 0 0.93 -0.62
TP_L4_00308.Mother TES_L4
TP_L4_00308.Visibility 0

TES_Pixel_L4.Copy TP_L4_00309
TP_L4_00309.Position 0 0.93 -0.465
TP_L4_00309.Mother TES_L4
TP_L4_00309.Visibility 0

TES_Pixel_L4.Copy TP_L4_00310
TP_L4_00310.Position 0 0.93 -0.31
TP_L4_00310.Mother TES_L4
TP_L4_00310.Visibility 0

TES_Pixel_L4.Copy TP_L4_00311
TP_L4_00311.Position 0 0.93 -0.155
TP_L4_00311.Mother TES_L4
TP_L4_00311.Visibility 0

TES_Pixel_L4.Copy TP_L4_00312
TP_L4_00312.Position 0 0.93 0
TP_L4_00312.Mother TES_L4
TP_L4_00312.Visibility 0

TES_Pixel_L4.Copy TP_L4_00313
TP_L4_00313.Position 0 0.93 0.155
TP_L4_00313.Mother TES_L4
TP_L4_00313.Visibility 0

TES_Pixel_L4.Copy TP_L4_00314
TP_L4_00314.Position 0 0.93 0.31
TP_L4_00314.Mother TES_L4
TP_L4_00314.Visibility 0

TES_Pixel_L4.Copy TP_L4_00315
TP_L4_00315.Position 0 0.93 0.465
TP_L4_00315.Mother TES_L4
TP_L4_00315.Visibility 0

TES_Pixel_L4.Copy TP_L4_00316
TP_L4_00316.Position 0 0.93 0.62
TP_L4_00316.Mother TES_L4
TP_L4_00316.Visibility 0

TES_Pixel_L4.Copy TP_L4_00317
TP_L4_00317.Position 0 0.93 0.775
TP_L4_00317.Mother TES_L4
TP_L4_00317.Visibility 0

TES_Pixel_L4.Copy TP_L4_00318
TP_L4_00318.Position 0 0.93 0.93
TP_L4_00318.Mother TES_L4
TP_L4_00318.Visibility 0

TES_Pixel_L4.Copy TP_L4_00319
TP_L4_00319.Position 0 0.93 1.085
TP_L4_00319.Mother TES_L4
TP_L4_00319.Visibility 0

TES_Pixel_L4.Copy TP_L4_00320
TP_L4_00320.Position 0 0.93 1.24
TP_L4_00320.Mother TES_L4
TP_L4_00320.Visibility 0

TES_Pixel_L4.Copy TP_L4_00321
TP_L4_00321.Position 0 0.93 1.395
TP_L4_00321.Mother TES_L4
TP_L4_00321.Visibility 0

TES_Pixel_L4.Copy TP_L4_00322
TP_L4_00322.Position 0 1.085 -1.24
TP_L4_00322.Mother TES_L4
TP_L4_00322.Visibility 0

TES_Pixel_L4.Copy TP_L4_00323
TP_L4_00323.Position 0 1.085 -1.085
TP_L4_00323.Mother TES_L4
TP_L4_00323.Visibility 0

TES_Pixel_L4.Copy TP_L4_00324
TP_L4_00324.Position 0 1.085 -0.93
TP_L4_00324.Mother TES_L4
TP_L4_00324.Visibility 0

TES_Pixel_L4.Copy TP_L4_00325
TP_L4_00325.Position 0 1.085 -0.775
TP_L4_00325.Mother TES_L4
TP_L4_00325.Visibility 0

TES_Pixel_L4.Copy TP_L4_00326
TP_L4_00326.Position 0 1.085 -0.62
TP_L4_00326.Mother TES_L4
TP_L4_00326.Visibility 0

TES_Pixel_L4.Copy TP_L4_00327
TP_L4_00327.Position 0 1.085 -0.465
TP_L4_00327.Mother TES_L4
TP_L4_00327.Visibility 0

TES_Pixel_L4.Copy TP_L4_00328
TP_L4_00328.Position 0 1.085 -0.31
TP_L4_00328.Mother TES_L4
TP_L4_00328.Visibility 0

TES_Pixel_L4.Copy TP_L4_00329
TP_L4_00329.Position 0 1.085 -0.155
TP_L4_00329.Mother TES_L4
TP_L4_00329.Visibility 0

TES_Pixel_L4.Copy TP_L4_00330
TP_L4_00330.Position 0 1.085 0
TP_L4_00330.Mother TES_L4
TP_L4_00330.Visibility 0

TES_Pixel_L4.Copy TP_L4_00331
TP_L4_00331.Position 0 1.085 0.155
TP_L4_00331.Mother TES_L4
TP_L4_00331.Visibility 0

TES_Pixel_L4.Copy TP_L4_00332
TP_L4_00332.Position 0 1.085 0.31
TP_L4_00332.Mother TES_L4
TP_L4_00332.Visibility 0

TES_Pixel_L4.Copy TP_L4_00333
TP_L4_00333.Position 0 1.085 0.465
TP_L4_00333.Mother TES_L4
TP_L4_00333.Visibility 0

TES_Pixel_L4.Copy TP_L4_00334
TP_L4_00334.Position 0 1.085 0.62
TP_L4_00334.Mother TES_L4
TP_L4_00334.Visibility 0

TES_Pixel_L4.Copy TP_L4_00335
TP_L4_00335.Position 0 1.085 0.775
TP_L4_00335.Mother TES_L4
TP_L4_00335.Visibility 0

TES_Pixel_L4.Copy TP_L4_00336
TP_L4_00336.Position 0 1.085 0.93
TP_L4_00336.Mother TES_L4
TP_L4_00336.Visibility 0

TES_Pixel_L4.Copy TP_L4_00337
TP_L4_00337.Position 0 1.085 1.085
TP_L4_00337.Mother TES_L4
TP_L4_00337.Visibility 0

TES_Pixel_L4.Copy TP_L4_00338
TP_L4_00338.Position 0 1.085 1.24
TP_L4_00338.Mother TES_L4
TP_L4_00338.Visibility 0

TES_Pixel_L4.Copy TP_L4_00339
TP_L4_00339.Position 0 1.24 -1.085
TP_L4_00339.Mother TES_L4
TP_L4_00339.Visibility 0

TES_Pixel_L4.Copy TP_L4_00340
TP_L4_00340.Position 0 1.24 -0.93
TP_L4_00340.Mother TES_L4
TP_L4_00340.Visibility 0

TES_Pixel_L4.Copy TP_L4_00341
TP_L4_00341.Position 0 1.24 -0.775
TP_L4_00341.Mother TES_L4
TP_L4_00341.Visibility 0

TES_Pixel_L4.Copy TP_L4_00342
TP_L4_00342.Position 0 1.24 -0.62
TP_L4_00342.Mother TES_L4
TP_L4_00342.Visibility 0

TES_Pixel_L4.Copy TP_L4_00343
TP_L4_00343.Position 0 1.24 -0.465
TP_L4_00343.Mother TES_L4
TP_L4_00343.Visibility 0

TES_Pixel_L4.Copy TP_L4_00344
TP_L4_00344.Position 0 1.24 -0.31
TP_L4_00344.Mother TES_L4
TP_L4_00344.Visibility 0

TES_Pixel_L4.Copy TP_L4_00345
TP_L4_00345.Position 0 1.24 -0.155
TP_L4_00345.Mother TES_L4
TP_L4_00345.Visibility 0

TES_Pixel_L4.Copy TP_L4_00346
TP_L4_00346.Position 0 1.24 0
TP_L4_00346.Mother TES_L4
TP_L4_00346.Visibility 0

TES_Pixel_L4.Copy TP_L4_00347
TP_L4_00347.Position 0 1.24 0.155
TP_L4_00347.Mother TES_L4
TP_L4_00347.Visibility 0

TES_Pixel_L4.Copy TP_L4_00348
TP_L4_00348.Position 0 1.24 0.31
TP_L4_00348.Mother TES_L4
TP_L4_00348.Visibility 0

TES_Pixel_L4.Copy TP_L4_00349
TP_L4_00349.Position 0 1.24 0.465
TP_L4_00349.Mother TES_L4
TP_L4_00349.Visibility 0

TES_Pixel_L4.Copy TP_L4_00350
TP_L4_00350.Position 0 1.24 0.62
TP_L4_00350.Mother TES_L4
TP_L4_00350.Visibility 0

TES_Pixel_L4.Copy TP_L4_00351
TP_L4_00351.Position 0 1.24 0.775
TP_L4_00351.Mother TES_L4
TP_L4_00351.Visibility 0

TES_Pixel_L4.Copy TP_L4_00352
TP_L4_00352.Position 0 1.24 0.93
TP_L4_00352.Mother TES_L4
TP_L4_00352.Visibility 0

TES_Pixel_L4.Copy TP_L4_00353
TP_L4_00353.Position 0 1.24 1.085
TP_L4_00353.Mother TES_L4
TP_L4_00353.Visibility 0

TES_Pixel_L4.Copy TP_L4_00354
TP_L4_00354.Position 0 1.395 -0.93
TP_L4_00354.Mother TES_L4
TP_L4_00354.Visibility 0

TES_Pixel_L4.Copy TP_L4_00355
TP_L4_00355.Position 0 1.395 -0.775
TP_L4_00355.Mother TES_L4
TP_L4_00355.Visibility 0

TES_Pixel_L4.Copy TP_L4_00356
TP_L4_00356.Position 0 1.395 -0.62
TP_L4_00356.Mother TES_L4
TP_L4_00356.Visibility 0

TES_Pixel_L4.Copy TP_L4_00357
TP_L4_00357.Position 0 1.395 -0.465
TP_L4_00357.Mother TES_L4
TP_L4_00357.Visibility 0

TES_Pixel_L4.Copy TP_L4_00358
TP_L4_00358.Position 0 1.395 -0.31
TP_L4_00358.Mother TES_L4
TP_L4_00358.Visibility 0

TES_Pixel_L4.Copy TP_L4_00359
TP_L4_00359.Position 0 1.395 -0.155
TP_L4_00359.Mother TES_L4
TP_L4_00359.Visibility 0

TES_Pixel_L4.Copy TP_L4_00360
TP_L4_00360.Position 0 1.395 0
TP_L4_00360.Mother TES_L4
TP_L4_00360.Visibility 0

TES_Pixel_L4.Copy TP_L4_00361
TP_L4_00361.Position 0 1.395 0.155
TP_L4_00361.Mother TES_L4
TP_L4_00361.Visibility 0

TES_Pixel_L4.Copy TP_L4_00362
TP_L4_00362.Position 0 1.395 0.31
TP_L4_00362.Mother TES_L4
TP_L4_00362.Visibility 0

TES_Pixel_L4.Copy TP_L4_00363
TP_L4_00363.Position 0 1.395 0.465
TP_L4_00363.Mother TES_L4
TP_L4_00363.Visibility 0

TES_Pixel_L4.Copy TP_L4_00364
TP_L4_00364.Position 0 1.395 0.62
TP_L4_00364.Mother TES_L4
TP_L4_00364.Visibility 0

TES_Pixel_L4.Copy TP_L4_00365
TP_L4_00365.Position 0 1.395 0.775
TP_L4_00365.Mother TES_L4
TP_L4_00365.Visibility 0

TES_Pixel_L4.Copy TP_L4_00366
TP_L4_00366.Position 0 1.395 0.93
TP_L4_00366.Mother TES_L4
TP_L4_00366.Visibility 0

TES_Pixel_L4.Copy TP_L4_00367
TP_L4_00367.Position 0 1.55 -0.62
TP_L4_00367.Mother TES_L4
TP_L4_00367.Visibility 0

TES_Pixel_L4.Copy TP_L4_00368
TP_L4_00368.Position 0 1.55 -0.465
TP_L4_00368.Mother TES_L4
TP_L4_00368.Visibility 0

TES_Pixel_L4.Copy TP_L4_00369
TP_L4_00369.Position 0 1.55 -0.31
TP_L4_00369.Mother TES_L4
TP_L4_00369.Visibility 0

TES_Pixel_L4.Copy TP_L4_00370
TP_L4_00370.Position 0 1.55 -0.155
TP_L4_00370.Mother TES_L4
TP_L4_00370.Visibility 0

TES_Pixel_L4.Copy TP_L4_00371
TP_L4_00371.Position 0 1.55 0
TP_L4_00371.Mother TES_L4
TP_L4_00371.Visibility 0

TES_Pixel_L4.Copy TP_L4_00372
TP_L4_00372.Position 0 1.55 0.155
TP_L4_00372.Mother TES_L4
TP_L4_00372.Visibility 0

TES_Pixel_L4.Copy TP_L4_00373
TP_L4_00373.Position 0 1.55 0.31
TP_L4_00373.Mother TES_L4
TP_L4_00373.Visibility 0

TES_Pixel_L4.Copy TP_L4_00374
TP_L4_00374.Position 0 1.55 0.465
TP_L4_00374.Mother TES_L4
TP_L4_00374.Visibility 0

TES_Pixel_L4.Copy TP_L4_00375
TP_L4_00375.Position 0 1.55 0.62
TP_L4_00375.Mother TES_L4
TP_L4_00375.Visibility 0

// Volume TES_Pixel_L5; material=Ta
Volume TES_Pixel_L5
TES_Pixel_L5.Material Ta
TES_Pixel_L5.Visibility 1
TES_Pixel_L5.Shape BRIK 0.15 0.075 0.075

// Volume TES_L5; material=Vacuum
Volume TES_L5
TES_L5.Material Vacuum
TES_L5.Visibility 0
TES_L5.Shape BRIK 0.15 1.8 1.8

TES_L5.Position -32.55 0 -2.8
TES_L5.Mother InstrumentFrame

TES_Pixel_L5.Copy TP_L5_00000
TP_L5_00000.Position 0 -1.705 0
TP_L5_00000.Mother TES_L5
TP_L5_00000.Visibility 0

TES_Pixel_L5.Copy TP_L5_00001
TP_L5_00001.Position 0 -1.55 -0.62
TP_L5_00001.Mother TES_L5
TP_L5_00001.Visibility 0

TES_Pixel_L5.Copy TP_L5_00002
TP_L5_00002.Position 0 -1.55 -0.465
TP_L5_00002.Mother TES_L5
TP_L5_00002.Visibility 0

TES_Pixel_L5.Copy TP_L5_00003
TP_L5_00003.Position 0 -1.55 -0.31
TP_L5_00003.Mother TES_L5
TP_L5_00003.Visibility 0

TES_Pixel_L5.Copy TP_L5_00004
TP_L5_00004.Position 0 -1.55 -0.155
TP_L5_00004.Mother TES_L5
TP_L5_00004.Visibility 0

TES_Pixel_L5.Copy TP_L5_00005
TP_L5_00005.Position 0 -1.55 0
TP_L5_00005.Mother TES_L5
TP_L5_00005.Visibility 0

TES_Pixel_L5.Copy TP_L5_00006
TP_L5_00006.Position 0 -1.55 0.155
TP_L5_00006.Mother TES_L5
TP_L5_00006.Visibility 0

TES_Pixel_L5.Copy TP_L5_00007
TP_L5_00007.Position 0 -1.55 0.31
TP_L5_00007.Mother TES_L5
TP_L5_00007.Visibility 0

TES_Pixel_L5.Copy TP_L5_00008
TP_L5_00008.Position 0 -1.55 0.465
TP_L5_00008.Mother TES_L5
TP_L5_00008.Visibility 0

TES_Pixel_L5.Copy TP_L5_00009
TP_L5_00009.Position 0 -1.55 0.62
TP_L5_00009.Mother TES_L5
TP_L5_00009.Visibility 0

TES_Pixel_L5.Copy TP_L5_00010
TP_L5_00010.Position 0 -1.395 -0.93
TP_L5_00010.Mother TES_L5
TP_L5_00010.Visibility 0

TES_Pixel_L5.Copy TP_L5_00011
TP_L5_00011.Position 0 -1.395 -0.775
TP_L5_00011.Mother TES_L5
TP_L5_00011.Visibility 0

TES_Pixel_L5.Copy TP_L5_00012
TP_L5_00012.Position 0 -1.395 -0.62
TP_L5_00012.Mother TES_L5
TP_L5_00012.Visibility 0

TES_Pixel_L5.Copy TP_L5_00013
TP_L5_00013.Position 0 -1.395 -0.465
TP_L5_00013.Mother TES_L5
TP_L5_00013.Visibility 0

TES_Pixel_L5.Copy TP_L5_00014
TP_L5_00014.Position 0 -1.395 -0.31
TP_L5_00014.Mother TES_L5
TP_L5_00014.Visibility 0

TES_Pixel_L5.Copy TP_L5_00015
TP_L5_00015.Position 0 -1.395 -0.155
TP_L5_00015.Mother TES_L5
TP_L5_00015.Visibility 0

TES_Pixel_L5.Copy TP_L5_00016
TP_L5_00016.Position 0 -1.395 0
TP_L5_00016.Mother TES_L5
TP_L5_00016.Visibility 0

TES_Pixel_L5.Copy TP_L5_00017
TP_L5_00017.Position 0 -1.395 0.155
TP_L5_00017.Mother TES_L5
TP_L5_00017.Visibility 0

TES_Pixel_L5.Copy TP_L5_00018
TP_L5_00018.Position 0 -1.395 0.31
TP_L5_00018.Mother TES_L5
TP_L5_00018.Visibility 0

TES_Pixel_L5.Copy TP_L5_00019
TP_L5_00019.Position 0 -1.395 0.465
TP_L5_00019.Mother TES_L5
TP_L5_00019.Visibility 0

TES_Pixel_L5.Copy TP_L5_00020
TP_L5_00020.Position 0 -1.395 0.62
TP_L5_00020.Mother TES_L5
TP_L5_00020.Visibility 0

TES_Pixel_L5.Copy TP_L5_00021
TP_L5_00021.Position 0 -1.395 0.775
TP_L5_00021.Mother TES_L5
TP_L5_00021.Visibility 0

TES_Pixel_L5.Copy TP_L5_00022
TP_L5_00022.Position 0 -1.395 0.93
TP_L5_00022.Mother TES_L5
TP_L5_00022.Visibility 0

TES_Pixel_L5.Copy TP_L5_00023
TP_L5_00023.Position 0 -1.24 -1.085
TP_L5_00023.Mother TES_L5
TP_L5_00023.Visibility 0

TES_Pixel_L5.Copy TP_L5_00024
TP_L5_00024.Position 0 -1.24 -0.93
TP_L5_00024.Mother TES_L5
TP_L5_00024.Visibility 0

TES_Pixel_L5.Copy TP_L5_00025
TP_L5_00025.Position 0 -1.24 -0.775
TP_L5_00025.Mother TES_L5
TP_L5_00025.Visibility 0

TES_Pixel_L5.Copy TP_L5_00026
TP_L5_00026.Position 0 -1.24 -0.62
TP_L5_00026.Mother TES_L5
TP_L5_00026.Visibility 0

TES_Pixel_L5.Copy TP_L5_00027
TP_L5_00027.Position 0 -1.24 -0.465
TP_L5_00027.Mother TES_L5
TP_L5_00027.Visibility 0

TES_Pixel_L5.Copy TP_L5_00028
TP_L5_00028.Position 0 -1.24 -0.31
TP_L5_00028.Mother TES_L5
TP_L5_00028.Visibility 0

TES_Pixel_L5.Copy TP_L5_00029
TP_L5_00029.Position 0 -1.24 -0.155
TP_L5_00029.Mother TES_L5
TP_L5_00029.Visibility 0

TES_Pixel_L5.Copy TP_L5_00030
TP_L5_00030.Position 0 -1.24 0
TP_L5_00030.Mother TES_L5
TP_L5_00030.Visibility 0

TES_Pixel_L5.Copy TP_L5_00031
TP_L5_00031.Position 0 -1.24 0.155
TP_L5_00031.Mother TES_L5
TP_L5_00031.Visibility 0

TES_Pixel_L5.Copy TP_L5_00032
TP_L5_00032.Position 0 -1.24 0.31
TP_L5_00032.Mother TES_L5
TP_L5_00032.Visibility 0

TES_Pixel_L5.Copy TP_L5_00033
TP_L5_00033.Position 0 -1.24 0.465
TP_L5_00033.Mother TES_L5
TP_L5_00033.Visibility 0

TES_Pixel_L5.Copy TP_L5_00034
TP_L5_00034.Position 0 -1.24 0.62
TP_L5_00034.Mother TES_L5
TP_L5_00034.Visibility 0

TES_Pixel_L5.Copy TP_L5_00035
TP_L5_00035.Position 0 -1.24 0.775
TP_L5_00035.Mother TES_L5
TP_L5_00035.Visibility 0

TES_Pixel_L5.Copy TP_L5_00036
TP_L5_00036.Position 0 -1.24 0.93
TP_L5_00036.Mother TES_L5
TP_L5_00036.Visibility 0

TES_Pixel_L5.Copy TP_L5_00037
TP_L5_00037.Position 0 -1.24 1.085
TP_L5_00037.Mother TES_L5
TP_L5_00037.Visibility 0

TES_Pixel_L5.Copy TP_L5_00038
TP_L5_00038.Position 0 -1.085 -1.24
TP_L5_00038.Mother TES_L5
TP_L5_00038.Visibility 0

TES_Pixel_L5.Copy TP_L5_00039
TP_L5_00039.Position 0 -1.085 -1.085
TP_L5_00039.Mother TES_L5
TP_L5_00039.Visibility 0

TES_Pixel_L5.Copy TP_L5_00040
TP_L5_00040.Position 0 -1.085 -0.93
TP_L5_00040.Mother TES_L5
TP_L5_00040.Visibility 0

TES_Pixel_L5.Copy TP_L5_00041
TP_L5_00041.Position 0 -1.085 -0.775
TP_L5_00041.Mother TES_L5
TP_L5_00041.Visibility 0

TES_Pixel_L5.Copy TP_L5_00042
TP_L5_00042.Position 0 -1.085 -0.62
TP_L5_00042.Mother TES_L5
TP_L5_00042.Visibility 0

TES_Pixel_L5.Copy TP_L5_00043
TP_L5_00043.Position 0 -1.085 -0.465
TP_L5_00043.Mother TES_L5
TP_L5_00043.Visibility 0

TES_Pixel_L5.Copy TP_L5_00044
TP_L5_00044.Position 0 -1.085 -0.31
TP_L5_00044.Mother TES_L5
TP_L5_00044.Visibility 0

TES_Pixel_L5.Copy TP_L5_00045
TP_L5_00045.Position 0 -1.085 -0.155
TP_L5_00045.Mother TES_L5
TP_L5_00045.Visibility 0

TES_Pixel_L5.Copy TP_L5_00046
TP_L5_00046.Position 0 -1.085 0
TP_L5_00046.Mother TES_L5
TP_L5_00046.Visibility 0

TES_Pixel_L5.Copy TP_L5_00047
TP_L5_00047.Position 0 -1.085 0.155
TP_L5_00047.Mother TES_L5
TP_L5_00047.Visibility 0

TES_Pixel_L5.Copy TP_L5_00048
TP_L5_00048.Position 0 -1.085 0.31
TP_L5_00048.Mother TES_L5
TP_L5_00048.Visibility 0

TES_Pixel_L5.Copy TP_L5_00049
TP_L5_00049.Position 0 -1.085 0.465
TP_L5_00049.Mother TES_L5
TP_L5_00049.Visibility 0

TES_Pixel_L5.Copy TP_L5_00050
TP_L5_00050.Position 0 -1.085 0.62
TP_L5_00050.Mother TES_L5
TP_L5_00050.Visibility 0

TES_Pixel_L5.Copy TP_L5_00051
TP_L5_00051.Position 0 -1.085 0.775
TP_L5_00051.Mother TES_L5
TP_L5_00051.Visibility 0

TES_Pixel_L5.Copy TP_L5_00052
TP_L5_00052.Position 0 -1.085 0.93
TP_L5_00052.Mother TES_L5
TP_L5_00052.Visibility 0

TES_Pixel_L5.Copy TP_L5_00053
TP_L5_00053.Position 0 -1.085 1.085
TP_L5_00053.Mother TES_L5
TP_L5_00053.Visibility 0

TES_Pixel_L5.Copy TP_L5_00054
TP_L5_00054.Position 0 -1.085 1.24
TP_L5_00054.Mother TES_L5
TP_L5_00054.Visibility 0

TES_Pixel_L5.Copy TP_L5_00055
TP_L5_00055.Position 0 -0.93 -1.395
TP_L5_00055.Mother TES_L5
TP_L5_00055.Visibility 0

TES_Pixel_L5.Copy TP_L5_00056
TP_L5_00056.Position 0 -0.93 -1.24
TP_L5_00056.Mother TES_L5
TP_L5_00056.Visibility 0

TES_Pixel_L5.Copy TP_L5_00057
TP_L5_00057.Position 0 -0.93 -1.085
TP_L5_00057.Mother TES_L5
TP_L5_00057.Visibility 0

TES_Pixel_L5.Copy TP_L5_00058
TP_L5_00058.Position 0 -0.93 -0.93
TP_L5_00058.Mother TES_L5
TP_L5_00058.Visibility 0

TES_Pixel_L5.Copy TP_L5_00059
TP_L5_00059.Position 0 -0.93 -0.775
TP_L5_00059.Mother TES_L5
TP_L5_00059.Visibility 0

TES_Pixel_L5.Copy TP_L5_00060
TP_L5_00060.Position 0 -0.93 -0.62
TP_L5_00060.Mother TES_L5
TP_L5_00060.Visibility 0

TES_Pixel_L5.Copy TP_L5_00061
TP_L5_00061.Position 0 -0.93 -0.465
TP_L5_00061.Mother TES_L5
TP_L5_00061.Visibility 0

TES_Pixel_L5.Copy TP_L5_00062
TP_L5_00062.Position 0 -0.93 -0.31
TP_L5_00062.Mother TES_L5
TP_L5_00062.Visibility 0

TES_Pixel_L5.Copy TP_L5_00063
TP_L5_00063.Position 0 -0.93 -0.155
TP_L5_00063.Mother TES_L5
TP_L5_00063.Visibility 0

TES_Pixel_L5.Copy TP_L5_00064
TP_L5_00064.Position 0 -0.93 0
TP_L5_00064.Mother TES_L5
TP_L5_00064.Visibility 0

TES_Pixel_L5.Copy TP_L5_00065
TP_L5_00065.Position 0 -0.93 0.155
TP_L5_00065.Mother TES_L5
TP_L5_00065.Visibility 0

TES_Pixel_L5.Copy TP_L5_00066
TP_L5_00066.Position 0 -0.93 0.31
TP_L5_00066.Mother TES_L5
TP_L5_00066.Visibility 0

TES_Pixel_L5.Copy TP_L5_00067
TP_L5_00067.Position 0 -0.93 0.465
TP_L5_00067.Mother TES_L5
TP_L5_00067.Visibility 0

TES_Pixel_L5.Copy TP_L5_00068
TP_L5_00068.Position 0 -0.93 0.62
TP_L5_00068.Mother TES_L5
TP_L5_00068.Visibility 0

TES_Pixel_L5.Copy TP_L5_00069
TP_L5_00069.Position 0 -0.93 0.775
TP_L5_00069.Mother TES_L5
TP_L5_00069.Visibility 0

TES_Pixel_L5.Copy TP_L5_00070
TP_L5_00070.Position 0 -0.93 0.93
TP_L5_00070.Mother TES_L5
TP_L5_00070.Visibility 0

TES_Pixel_L5.Copy TP_L5_00071
TP_L5_00071.Position 0 -0.93 1.085
TP_L5_00071.Mother TES_L5
TP_L5_00071.Visibility 0

TES_Pixel_L5.Copy TP_L5_00072
TP_L5_00072.Position 0 -0.93 1.24
TP_L5_00072.Mother TES_L5
TP_L5_00072.Visibility 0

TES_Pixel_L5.Copy TP_L5_00073
TP_L5_00073.Position 0 -0.93 1.395
TP_L5_00073.Mother TES_L5
TP_L5_00073.Visibility 0

TES_Pixel_L5.Copy TP_L5_00074
TP_L5_00074.Position 0 -0.775 -1.395
TP_L5_00074.Mother TES_L5
TP_L5_00074.Visibility 0

TES_Pixel_L5.Copy TP_L5_00075
TP_L5_00075.Position 0 -0.775 -1.24
TP_L5_00075.Mother TES_L5
TP_L5_00075.Visibility 0

TES_Pixel_L5.Copy TP_L5_00076
TP_L5_00076.Position 0 -0.775 -1.085
TP_L5_00076.Mother TES_L5
TP_L5_00076.Visibility 0

TES_Pixel_L5.Copy TP_L5_00077
TP_L5_00077.Position 0 -0.775 -0.93
TP_L5_00077.Mother TES_L5
TP_L5_00077.Visibility 0

TES_Pixel_L5.Copy TP_L5_00078
TP_L5_00078.Position 0 -0.775 -0.775
TP_L5_00078.Mother TES_L5
TP_L5_00078.Visibility 0

TES_Pixel_L5.Copy TP_L5_00079
TP_L5_00079.Position 0 -0.775 -0.62
TP_L5_00079.Mother TES_L5
TP_L5_00079.Visibility 0

TES_Pixel_L5.Copy TP_L5_00080
TP_L5_00080.Position 0 -0.775 -0.465
TP_L5_00080.Mother TES_L5
TP_L5_00080.Visibility 0

TES_Pixel_L5.Copy TP_L5_00081
TP_L5_00081.Position 0 -0.775 -0.31
TP_L5_00081.Mother TES_L5
TP_L5_00081.Visibility 0

TES_Pixel_L5.Copy TP_L5_00082
TP_L5_00082.Position 0 -0.775 -0.155
TP_L5_00082.Mother TES_L5
TP_L5_00082.Visibility 0

TES_Pixel_L5.Copy TP_L5_00083
TP_L5_00083.Position 0 -0.775 0
TP_L5_00083.Mother TES_L5
TP_L5_00083.Visibility 0

TES_Pixel_L5.Copy TP_L5_00084
TP_L5_00084.Position 0 -0.775 0.155
TP_L5_00084.Mother TES_L5
TP_L5_00084.Visibility 0

TES_Pixel_L5.Copy TP_L5_00085
TP_L5_00085.Position 0 -0.775 0.31
TP_L5_00085.Mother TES_L5
TP_L5_00085.Visibility 0

TES_Pixel_L5.Copy TP_L5_00086
TP_L5_00086.Position 0 -0.775 0.465
TP_L5_00086.Mother TES_L5
TP_L5_00086.Visibility 0

TES_Pixel_L5.Copy TP_L5_00087
TP_L5_00087.Position 0 -0.775 0.62
TP_L5_00087.Mother TES_L5
TP_L5_00087.Visibility 0

TES_Pixel_L5.Copy TP_L5_00088
TP_L5_00088.Position 0 -0.775 0.775
TP_L5_00088.Mother TES_L5
TP_L5_00088.Visibility 0

TES_Pixel_L5.Copy TP_L5_00089
TP_L5_00089.Position 0 -0.775 0.93
TP_L5_00089.Mother TES_L5
TP_L5_00089.Visibility 0

TES_Pixel_L5.Copy TP_L5_00090
TP_L5_00090.Position 0 -0.775 1.085
TP_L5_00090.Mother TES_L5
TP_L5_00090.Visibility 0

TES_Pixel_L5.Copy TP_L5_00091
TP_L5_00091.Position 0 -0.775 1.24
TP_L5_00091.Mother TES_L5
TP_L5_00091.Visibility 0

TES_Pixel_L5.Copy TP_L5_00092
TP_L5_00092.Position 0 -0.775 1.395
TP_L5_00092.Mother TES_L5
TP_L5_00092.Visibility 0

TES_Pixel_L5.Copy TP_L5_00093
TP_L5_00093.Position 0 -0.62 -1.55
TP_L5_00093.Mother TES_L5
TP_L5_00093.Visibility 0

TES_Pixel_L5.Copy TP_L5_00094
TP_L5_00094.Position 0 -0.62 -1.395
TP_L5_00094.Mother TES_L5
TP_L5_00094.Visibility 0

TES_Pixel_L5.Copy TP_L5_00095
TP_L5_00095.Position 0 -0.62 -1.24
TP_L5_00095.Mother TES_L5
TP_L5_00095.Visibility 0

TES_Pixel_L5.Copy TP_L5_00096
TP_L5_00096.Position 0 -0.62 -1.085
TP_L5_00096.Mother TES_L5
TP_L5_00096.Visibility 0

TES_Pixel_L5.Copy TP_L5_00097
TP_L5_00097.Position 0 -0.62 -0.93
TP_L5_00097.Mother TES_L5
TP_L5_00097.Visibility 0

TES_Pixel_L5.Copy TP_L5_00098
TP_L5_00098.Position 0 -0.62 -0.775
TP_L5_00098.Mother TES_L5
TP_L5_00098.Visibility 0

TES_Pixel_L5.Copy TP_L5_00099
TP_L5_00099.Position 0 -0.62 -0.62
TP_L5_00099.Mother TES_L5
TP_L5_00099.Visibility 0

TES_Pixel_L5.Copy TP_L5_00100
TP_L5_00100.Position 0 -0.62 -0.465
TP_L5_00100.Mother TES_L5
TP_L5_00100.Visibility 0

TES_Pixel_L5.Copy TP_L5_00101
TP_L5_00101.Position 0 -0.62 -0.31
TP_L5_00101.Mother TES_L5
TP_L5_00101.Visibility 0

TES_Pixel_L5.Copy TP_L5_00102
TP_L5_00102.Position 0 -0.62 -0.155
TP_L5_00102.Mother TES_L5
TP_L5_00102.Visibility 0

TES_Pixel_L5.Copy TP_L5_00103
TP_L5_00103.Position 0 -0.62 0
TP_L5_00103.Mother TES_L5
TP_L5_00103.Visibility 0

TES_Pixel_L5.Copy TP_L5_00104
TP_L5_00104.Position 0 -0.62 0.155
TP_L5_00104.Mother TES_L5
TP_L5_00104.Visibility 0

TES_Pixel_L5.Copy TP_L5_00105
TP_L5_00105.Position 0 -0.62 0.31
TP_L5_00105.Mother TES_L5
TP_L5_00105.Visibility 0

TES_Pixel_L5.Copy TP_L5_00106
TP_L5_00106.Position 0 -0.62 0.465
TP_L5_00106.Mother TES_L5
TP_L5_00106.Visibility 0

TES_Pixel_L5.Copy TP_L5_00107
TP_L5_00107.Position 0 -0.62 0.62
TP_L5_00107.Mother TES_L5
TP_L5_00107.Visibility 0

TES_Pixel_L5.Copy TP_L5_00108
TP_L5_00108.Position 0 -0.62 0.775
TP_L5_00108.Mother TES_L5
TP_L5_00108.Visibility 0

TES_Pixel_L5.Copy TP_L5_00109
TP_L5_00109.Position 0 -0.62 0.93
TP_L5_00109.Mother TES_L5
TP_L5_00109.Visibility 0

TES_Pixel_L5.Copy TP_L5_00110
TP_L5_00110.Position 0 -0.62 1.085
TP_L5_00110.Mother TES_L5
TP_L5_00110.Visibility 0

TES_Pixel_L5.Copy TP_L5_00111
TP_L5_00111.Position 0 -0.62 1.24
TP_L5_00111.Mother TES_L5
TP_L5_00111.Visibility 0

TES_Pixel_L5.Copy TP_L5_00112
TP_L5_00112.Position 0 -0.62 1.395
TP_L5_00112.Mother TES_L5
TP_L5_00112.Visibility 0

TES_Pixel_L5.Copy TP_L5_00113
TP_L5_00113.Position 0 -0.62 1.55
TP_L5_00113.Mother TES_L5
TP_L5_00113.Visibility 0

TES_Pixel_L5.Copy TP_L5_00114
TP_L5_00114.Position 0 -0.465 -1.55
TP_L5_00114.Mother TES_L5
TP_L5_00114.Visibility 0

TES_Pixel_L5.Copy TP_L5_00115
TP_L5_00115.Position 0 -0.465 -1.395
TP_L5_00115.Mother TES_L5
TP_L5_00115.Visibility 0

TES_Pixel_L5.Copy TP_L5_00116
TP_L5_00116.Position 0 -0.465 -1.24
TP_L5_00116.Mother TES_L5
TP_L5_00116.Visibility 0

TES_Pixel_L5.Copy TP_L5_00117
TP_L5_00117.Position 0 -0.465 -1.085
TP_L5_00117.Mother TES_L5
TP_L5_00117.Visibility 0

TES_Pixel_L5.Copy TP_L5_00118
TP_L5_00118.Position 0 -0.465 -0.93
TP_L5_00118.Mother TES_L5
TP_L5_00118.Visibility 0

TES_Pixel_L5.Copy TP_L5_00119
TP_L5_00119.Position 0 -0.465 -0.775
TP_L5_00119.Mother TES_L5
TP_L5_00119.Visibility 0

TES_Pixel_L5.Copy TP_L5_00120
TP_L5_00120.Position 0 -0.465 -0.62
TP_L5_00120.Mother TES_L5
TP_L5_00120.Visibility 0

TES_Pixel_L5.Copy TP_L5_00121
TP_L5_00121.Position 0 -0.465 -0.465
TP_L5_00121.Mother TES_L5
TP_L5_00121.Visibility 0

TES_Pixel_L5.Copy TP_L5_00122
TP_L5_00122.Position 0 -0.465 -0.31
TP_L5_00122.Mother TES_L5
TP_L5_00122.Visibility 0

TES_Pixel_L5.Copy TP_L5_00123
TP_L5_00123.Position 0 -0.465 -0.155
TP_L5_00123.Mother TES_L5
TP_L5_00123.Visibility 0

TES_Pixel_L5.Copy TP_L5_00124
TP_L5_00124.Position 0 -0.465 0
TP_L5_00124.Mother TES_L5
TP_L5_00124.Visibility 0

TES_Pixel_L5.Copy TP_L5_00125
TP_L5_00125.Position 0 -0.465 0.155
TP_L5_00125.Mother TES_L5
TP_L5_00125.Visibility 0

TES_Pixel_L5.Copy TP_L5_00126
TP_L5_00126.Position 0 -0.465 0.31
TP_L5_00126.Mother TES_L5
TP_L5_00126.Visibility 0

TES_Pixel_L5.Copy TP_L5_00127
TP_L5_00127.Position 0 -0.465 0.465
TP_L5_00127.Mother TES_L5
TP_L5_00127.Visibility 0

TES_Pixel_L5.Copy TP_L5_00128
TP_L5_00128.Position 0 -0.465 0.62
TP_L5_00128.Mother TES_L5
TP_L5_00128.Visibility 0

TES_Pixel_L5.Copy TP_L5_00129
TP_L5_00129.Position 0 -0.465 0.775
TP_L5_00129.Mother TES_L5
TP_L5_00129.Visibility 0

TES_Pixel_L5.Copy TP_L5_00130
TP_L5_00130.Position 0 -0.465 0.93
TP_L5_00130.Mother TES_L5
TP_L5_00130.Visibility 0

TES_Pixel_L5.Copy TP_L5_00131
TP_L5_00131.Position 0 -0.465 1.085
TP_L5_00131.Mother TES_L5
TP_L5_00131.Visibility 0

TES_Pixel_L5.Copy TP_L5_00132
TP_L5_00132.Position 0 -0.465 1.24
TP_L5_00132.Mother TES_L5
TP_L5_00132.Visibility 0

TES_Pixel_L5.Copy TP_L5_00133
TP_L5_00133.Position 0 -0.465 1.395
TP_L5_00133.Mother TES_L5
TP_L5_00133.Visibility 0

TES_Pixel_L5.Copy TP_L5_00134
TP_L5_00134.Position 0 -0.465 1.55
TP_L5_00134.Mother TES_L5
TP_L5_00134.Visibility 0

TES_Pixel_L5.Copy TP_L5_00135
TP_L5_00135.Position 0 -0.31 -1.55
TP_L5_00135.Mother TES_L5
TP_L5_00135.Visibility 0

TES_Pixel_L5.Copy TP_L5_00136
TP_L5_00136.Position 0 -0.31 -1.395
TP_L5_00136.Mother TES_L5
TP_L5_00136.Visibility 0

TES_Pixel_L5.Copy TP_L5_00137
TP_L5_00137.Position 0 -0.31 -1.24
TP_L5_00137.Mother TES_L5
TP_L5_00137.Visibility 0

TES_Pixel_L5.Copy TP_L5_00138
TP_L5_00138.Position 0 -0.31 -1.085
TP_L5_00138.Mother TES_L5
TP_L5_00138.Visibility 0

TES_Pixel_L5.Copy TP_L5_00139
TP_L5_00139.Position 0 -0.31 -0.93
TP_L5_00139.Mother TES_L5
TP_L5_00139.Visibility 0

TES_Pixel_L5.Copy TP_L5_00140
TP_L5_00140.Position 0 -0.31 -0.775
TP_L5_00140.Mother TES_L5
TP_L5_00140.Visibility 0

TES_Pixel_L5.Copy TP_L5_00141
TP_L5_00141.Position 0 -0.31 -0.62
TP_L5_00141.Mother TES_L5
TP_L5_00141.Visibility 0

TES_Pixel_L5.Copy TP_L5_00142
TP_L5_00142.Position 0 -0.31 -0.465
TP_L5_00142.Mother TES_L5
TP_L5_00142.Visibility 0

TES_Pixel_L5.Copy TP_L5_00143
TP_L5_00143.Position 0 -0.31 -0.31
TP_L5_00143.Mother TES_L5
TP_L5_00143.Visibility 0

TES_Pixel_L5.Copy TP_L5_00144
TP_L5_00144.Position 0 -0.31 -0.155
TP_L5_00144.Mother TES_L5
TP_L5_00144.Visibility 0

TES_Pixel_L5.Copy TP_L5_00145
TP_L5_00145.Position 0 -0.31 0
TP_L5_00145.Mother TES_L5
TP_L5_00145.Visibility 0

TES_Pixel_L5.Copy TP_L5_00146
TP_L5_00146.Position 0 -0.31 0.155
TP_L5_00146.Mother TES_L5
TP_L5_00146.Visibility 0

TES_Pixel_L5.Copy TP_L5_00147
TP_L5_00147.Position 0 -0.31 0.31
TP_L5_00147.Mother TES_L5
TP_L5_00147.Visibility 0

TES_Pixel_L5.Copy TP_L5_00148
TP_L5_00148.Position 0 -0.31 0.465
TP_L5_00148.Mother TES_L5
TP_L5_00148.Visibility 0

TES_Pixel_L5.Copy TP_L5_00149
TP_L5_00149.Position 0 -0.31 0.62
TP_L5_00149.Mother TES_L5
TP_L5_00149.Visibility 0

TES_Pixel_L5.Copy TP_L5_00150
TP_L5_00150.Position 0 -0.31 0.775
TP_L5_00150.Mother TES_L5
TP_L5_00150.Visibility 0

TES_Pixel_L5.Copy TP_L5_00151
TP_L5_00151.Position 0 -0.31 0.93
TP_L5_00151.Mother TES_L5
TP_L5_00151.Visibility 0

TES_Pixel_L5.Copy TP_L5_00152
TP_L5_00152.Position 0 -0.31 1.085
TP_L5_00152.Mother TES_L5
TP_L5_00152.Visibility 0

TES_Pixel_L5.Copy TP_L5_00153
TP_L5_00153.Position 0 -0.31 1.24
TP_L5_00153.Mother TES_L5
TP_L5_00153.Visibility 0

TES_Pixel_L5.Copy TP_L5_00154
TP_L5_00154.Position 0 -0.31 1.395
TP_L5_00154.Mother TES_L5
TP_L5_00154.Visibility 0

TES_Pixel_L5.Copy TP_L5_00155
TP_L5_00155.Position 0 -0.31 1.55
TP_L5_00155.Mother TES_L5
TP_L5_00155.Visibility 0

TES_Pixel_L5.Copy TP_L5_00156
TP_L5_00156.Position 0 -0.155 -1.55
TP_L5_00156.Mother TES_L5
TP_L5_00156.Visibility 0

TES_Pixel_L5.Copy TP_L5_00157
TP_L5_00157.Position 0 -0.155 -1.395
TP_L5_00157.Mother TES_L5
TP_L5_00157.Visibility 0

TES_Pixel_L5.Copy TP_L5_00158
TP_L5_00158.Position 0 -0.155 -1.24
TP_L5_00158.Mother TES_L5
TP_L5_00158.Visibility 0

TES_Pixel_L5.Copy TP_L5_00159
TP_L5_00159.Position 0 -0.155 -1.085
TP_L5_00159.Mother TES_L5
TP_L5_00159.Visibility 0

TES_Pixel_L5.Copy TP_L5_00160
TP_L5_00160.Position 0 -0.155 -0.93
TP_L5_00160.Mother TES_L5
TP_L5_00160.Visibility 0

TES_Pixel_L5.Copy TP_L5_00161
TP_L5_00161.Position 0 -0.155 -0.775
TP_L5_00161.Mother TES_L5
TP_L5_00161.Visibility 0

TES_Pixel_L5.Copy TP_L5_00162
TP_L5_00162.Position 0 -0.155 -0.62
TP_L5_00162.Mother TES_L5
TP_L5_00162.Visibility 0

TES_Pixel_L5.Copy TP_L5_00163
TP_L5_00163.Position 0 -0.155 -0.465
TP_L5_00163.Mother TES_L5
TP_L5_00163.Visibility 0

TES_Pixel_L5.Copy TP_L5_00164
TP_L5_00164.Position 0 -0.155 -0.31
TP_L5_00164.Mother TES_L5
TP_L5_00164.Visibility 0

TES_Pixel_L5.Copy TP_L5_00165
TP_L5_00165.Position 0 -0.155 -0.155
TP_L5_00165.Mother TES_L5
TP_L5_00165.Visibility 0

TES_Pixel_L5.Copy TP_L5_00166
TP_L5_00166.Position 0 -0.155 0
TP_L5_00166.Mother TES_L5
TP_L5_00166.Visibility 0

TES_Pixel_L5.Copy TP_L5_00167
TP_L5_00167.Position 0 -0.155 0.155
TP_L5_00167.Mother TES_L5
TP_L5_00167.Visibility 0

TES_Pixel_L5.Copy TP_L5_00168
TP_L5_00168.Position 0 -0.155 0.31
TP_L5_00168.Mother TES_L5
TP_L5_00168.Visibility 0

TES_Pixel_L5.Copy TP_L5_00169
TP_L5_00169.Position 0 -0.155 0.465
TP_L5_00169.Mother TES_L5
TP_L5_00169.Visibility 0

TES_Pixel_L5.Copy TP_L5_00170
TP_L5_00170.Position 0 -0.155 0.62
TP_L5_00170.Mother TES_L5
TP_L5_00170.Visibility 0

TES_Pixel_L5.Copy TP_L5_00171
TP_L5_00171.Position 0 -0.155 0.775
TP_L5_00171.Mother TES_L5
TP_L5_00171.Visibility 0

TES_Pixel_L5.Copy TP_L5_00172
TP_L5_00172.Position 0 -0.155 0.93
TP_L5_00172.Mother TES_L5
TP_L5_00172.Visibility 0

TES_Pixel_L5.Copy TP_L5_00173
TP_L5_00173.Position 0 -0.155 1.085
TP_L5_00173.Mother TES_L5
TP_L5_00173.Visibility 0

TES_Pixel_L5.Copy TP_L5_00174
TP_L5_00174.Position 0 -0.155 1.24
TP_L5_00174.Mother TES_L5
TP_L5_00174.Visibility 0

TES_Pixel_L5.Copy TP_L5_00175
TP_L5_00175.Position 0 -0.155 1.395
TP_L5_00175.Mother TES_L5
TP_L5_00175.Visibility 0

TES_Pixel_L5.Copy TP_L5_00176
TP_L5_00176.Position 0 -0.155 1.55
TP_L5_00176.Mother TES_L5
TP_L5_00176.Visibility 0

TES_Pixel_L5.Copy TP_L5_00177
TP_L5_00177.Position 0 0 -1.705
TP_L5_00177.Mother TES_L5
TP_L5_00177.Visibility 0

TES_Pixel_L5.Copy TP_L5_00178
TP_L5_00178.Position 0 0 -1.55
TP_L5_00178.Mother TES_L5
TP_L5_00178.Visibility 0

TES_Pixel_L5.Copy TP_L5_00179
TP_L5_00179.Position 0 0 -1.395
TP_L5_00179.Mother TES_L5
TP_L5_00179.Visibility 0

TES_Pixel_L5.Copy TP_L5_00180
TP_L5_00180.Position 0 0 -1.24
TP_L5_00180.Mother TES_L5
TP_L5_00180.Visibility 0

TES_Pixel_L5.Copy TP_L5_00181
TP_L5_00181.Position 0 0 -1.085
TP_L5_00181.Mother TES_L5
TP_L5_00181.Visibility 0

TES_Pixel_L5.Copy TP_L5_00182
TP_L5_00182.Position 0 0 -0.93
TP_L5_00182.Mother TES_L5
TP_L5_00182.Visibility 0

TES_Pixel_L5.Copy TP_L5_00183
TP_L5_00183.Position 0 0 -0.775
TP_L5_00183.Mother TES_L5
TP_L5_00183.Visibility 0

TES_Pixel_L5.Copy TP_L5_00184
TP_L5_00184.Position 0 0 -0.62
TP_L5_00184.Mother TES_L5
TP_L5_00184.Visibility 0

TES_Pixel_L5.Copy TP_L5_00185
TP_L5_00185.Position 0 0 -0.465
TP_L5_00185.Mother TES_L5
TP_L5_00185.Visibility 0

TES_Pixel_L5.Copy TP_L5_00186
TP_L5_00186.Position 0 0 -0.31
TP_L5_00186.Mother TES_L5
TP_L5_00186.Visibility 0

TES_Pixel_L5.Copy TP_L5_00187
TP_L5_00187.Position 0 0 -0.155
TP_L5_00187.Mother TES_L5
TP_L5_00187.Visibility 0

TES_Pixel_L5.Copy TP_L5_00188
TP_L5_00188.Position 0 0 0
TP_L5_00188.Mother TES_L5
TP_L5_00188.Visibility 0

TES_Pixel_L5.Copy TP_L5_00189
TP_L5_00189.Position 0 0 0.155
TP_L5_00189.Mother TES_L5
TP_L5_00189.Visibility 0

TES_Pixel_L5.Copy TP_L5_00190
TP_L5_00190.Position 0 0 0.31
TP_L5_00190.Mother TES_L5
TP_L5_00190.Visibility 0

TES_Pixel_L5.Copy TP_L5_00191
TP_L5_00191.Position 0 0 0.465
TP_L5_00191.Mother TES_L5
TP_L5_00191.Visibility 0

TES_Pixel_L5.Copy TP_L5_00192
TP_L5_00192.Position 0 0 0.62
TP_L5_00192.Mother TES_L5
TP_L5_00192.Visibility 0

TES_Pixel_L5.Copy TP_L5_00193
TP_L5_00193.Position 0 0 0.775
TP_L5_00193.Mother TES_L5
TP_L5_00193.Visibility 0

TES_Pixel_L5.Copy TP_L5_00194
TP_L5_00194.Position 0 0 0.93
TP_L5_00194.Mother TES_L5
TP_L5_00194.Visibility 0

TES_Pixel_L5.Copy TP_L5_00195
TP_L5_00195.Position 0 0 1.085
TP_L5_00195.Mother TES_L5
TP_L5_00195.Visibility 0

TES_Pixel_L5.Copy TP_L5_00196
TP_L5_00196.Position 0 0 1.24
TP_L5_00196.Mother TES_L5
TP_L5_00196.Visibility 0

TES_Pixel_L5.Copy TP_L5_00197
TP_L5_00197.Position 0 0 1.395
TP_L5_00197.Mother TES_L5
TP_L5_00197.Visibility 0

TES_Pixel_L5.Copy TP_L5_00198
TP_L5_00198.Position 0 0 1.55
TP_L5_00198.Mother TES_L5
TP_L5_00198.Visibility 0

TES_Pixel_L5.Copy TP_L5_00199
TP_L5_00199.Position 0 0 1.705
TP_L5_00199.Mother TES_L5
TP_L5_00199.Visibility 0

TES_Pixel_L5.Copy TP_L5_00200
TP_L5_00200.Position 0 0.155 -1.55
TP_L5_00200.Mother TES_L5
TP_L5_00200.Visibility 0

TES_Pixel_L5.Copy TP_L5_00201
TP_L5_00201.Position 0 0.155 -1.395
TP_L5_00201.Mother TES_L5
TP_L5_00201.Visibility 0

TES_Pixel_L5.Copy TP_L5_00202
TP_L5_00202.Position 0 0.155 -1.24
TP_L5_00202.Mother TES_L5
TP_L5_00202.Visibility 0

TES_Pixel_L5.Copy TP_L5_00203
TP_L5_00203.Position 0 0.155 -1.085
TP_L5_00203.Mother TES_L5
TP_L5_00203.Visibility 0

TES_Pixel_L5.Copy TP_L5_00204
TP_L5_00204.Position 0 0.155 -0.93
TP_L5_00204.Mother TES_L5
TP_L5_00204.Visibility 0

TES_Pixel_L5.Copy TP_L5_00205
TP_L5_00205.Position 0 0.155 -0.775
TP_L5_00205.Mother TES_L5
TP_L5_00205.Visibility 0

TES_Pixel_L5.Copy TP_L5_00206
TP_L5_00206.Position 0 0.155 -0.62
TP_L5_00206.Mother TES_L5
TP_L5_00206.Visibility 0

TES_Pixel_L5.Copy TP_L5_00207
TP_L5_00207.Position 0 0.155 -0.465
TP_L5_00207.Mother TES_L5
TP_L5_00207.Visibility 0

TES_Pixel_L5.Copy TP_L5_00208
TP_L5_00208.Position 0 0.155 -0.31
TP_L5_00208.Mother TES_L5
TP_L5_00208.Visibility 0

TES_Pixel_L5.Copy TP_L5_00209
TP_L5_00209.Position 0 0.155 -0.155
TP_L5_00209.Mother TES_L5
TP_L5_00209.Visibility 0

TES_Pixel_L5.Copy TP_L5_00210
TP_L5_00210.Position 0 0.155 0
TP_L5_00210.Mother TES_L5
TP_L5_00210.Visibility 0

TES_Pixel_L5.Copy TP_L5_00211
TP_L5_00211.Position 0 0.155 0.155
TP_L5_00211.Mother TES_L5
TP_L5_00211.Visibility 0

TES_Pixel_L5.Copy TP_L5_00212
TP_L5_00212.Position 0 0.155 0.31
TP_L5_00212.Mother TES_L5
TP_L5_00212.Visibility 0

TES_Pixel_L5.Copy TP_L5_00213
TP_L5_00213.Position 0 0.155 0.465
TP_L5_00213.Mother TES_L5
TP_L5_00213.Visibility 0

TES_Pixel_L5.Copy TP_L5_00214
TP_L5_00214.Position 0 0.155 0.62
TP_L5_00214.Mother TES_L5
TP_L5_00214.Visibility 0

TES_Pixel_L5.Copy TP_L5_00215
TP_L5_00215.Position 0 0.155 0.775
TP_L5_00215.Mother TES_L5
TP_L5_00215.Visibility 0

TES_Pixel_L5.Copy TP_L5_00216
TP_L5_00216.Position 0 0.155 0.93
TP_L5_00216.Mother TES_L5
TP_L5_00216.Visibility 0

TES_Pixel_L5.Copy TP_L5_00217
TP_L5_00217.Position 0 0.155 1.085
TP_L5_00217.Mother TES_L5
TP_L5_00217.Visibility 0

TES_Pixel_L5.Copy TP_L5_00218
TP_L5_00218.Position 0 0.155 1.24
TP_L5_00218.Mother TES_L5
TP_L5_00218.Visibility 0

TES_Pixel_L5.Copy TP_L5_00219
TP_L5_00219.Position 0 0.155 1.395
TP_L5_00219.Mother TES_L5
TP_L5_00219.Visibility 0

TES_Pixel_L5.Copy TP_L5_00220
TP_L5_00220.Position 0 0.155 1.55
TP_L5_00220.Mother TES_L5
TP_L5_00220.Visibility 0

TES_Pixel_L5.Copy TP_L5_00221
TP_L5_00221.Position 0 0.31 -1.55
TP_L5_00221.Mother TES_L5
TP_L5_00221.Visibility 0

TES_Pixel_L5.Copy TP_L5_00222
TP_L5_00222.Position 0 0.31 -1.395
TP_L5_00222.Mother TES_L5
TP_L5_00222.Visibility 0

TES_Pixel_L5.Copy TP_L5_00223
TP_L5_00223.Position 0 0.31 -1.24
TP_L5_00223.Mother TES_L5
TP_L5_00223.Visibility 0

TES_Pixel_L5.Copy TP_L5_00224
TP_L5_00224.Position 0 0.31 -1.085
TP_L5_00224.Mother TES_L5
TP_L5_00224.Visibility 0

TES_Pixel_L5.Copy TP_L5_00225
TP_L5_00225.Position 0 0.31 -0.93
TP_L5_00225.Mother TES_L5
TP_L5_00225.Visibility 0

TES_Pixel_L5.Copy TP_L5_00226
TP_L5_00226.Position 0 0.31 -0.775
TP_L5_00226.Mother TES_L5
TP_L5_00226.Visibility 0

TES_Pixel_L5.Copy TP_L5_00227
TP_L5_00227.Position 0 0.31 -0.62
TP_L5_00227.Mother TES_L5
TP_L5_00227.Visibility 0

TES_Pixel_L5.Copy TP_L5_00228
TP_L5_00228.Position 0 0.31 -0.465
TP_L5_00228.Mother TES_L5
TP_L5_00228.Visibility 0

TES_Pixel_L5.Copy TP_L5_00229
TP_L5_00229.Position 0 0.31 -0.31
TP_L5_00229.Mother TES_L5
TP_L5_00229.Visibility 0

TES_Pixel_L5.Copy TP_L5_00230
TP_L5_00230.Position 0 0.31 -0.155
TP_L5_00230.Mother TES_L5
TP_L5_00230.Visibility 0

TES_Pixel_L5.Copy TP_L5_00231
TP_L5_00231.Position 0 0.31 0
TP_L5_00231.Mother TES_L5
TP_L5_00231.Visibility 0

TES_Pixel_L5.Copy TP_L5_00232
TP_L5_00232.Position 0 0.31 0.155
TP_L5_00232.Mother TES_L5
TP_L5_00232.Visibility 0

TES_Pixel_L5.Copy TP_L5_00233
TP_L5_00233.Position 0 0.31 0.31
TP_L5_00233.Mother TES_L5
TP_L5_00233.Visibility 0

TES_Pixel_L5.Copy TP_L5_00234
TP_L5_00234.Position 0 0.31 0.465
TP_L5_00234.Mother TES_L5
TP_L5_00234.Visibility 0

TES_Pixel_L5.Copy TP_L5_00235
TP_L5_00235.Position 0 0.31 0.62
TP_L5_00235.Mother TES_L5
TP_L5_00235.Visibility 0

TES_Pixel_L5.Copy TP_L5_00236
TP_L5_00236.Position 0 0.31 0.775
TP_L5_00236.Mother TES_L5
TP_L5_00236.Visibility 0

TES_Pixel_L5.Copy TP_L5_00237
TP_L5_00237.Position 0 0.31 0.93
TP_L5_00237.Mother TES_L5
TP_L5_00237.Visibility 0

TES_Pixel_L5.Copy TP_L5_00238
TP_L5_00238.Position 0 0.31 1.085
TP_L5_00238.Mother TES_L5
TP_L5_00238.Visibility 0

TES_Pixel_L5.Copy TP_L5_00239
TP_L5_00239.Position 0 0.31 1.24
TP_L5_00239.Mother TES_L5
TP_L5_00239.Visibility 0

TES_Pixel_L5.Copy TP_L5_00240
TP_L5_00240.Position 0 0.31 1.395
TP_L5_00240.Mother TES_L5
TP_L5_00240.Visibility 0

TES_Pixel_L5.Copy TP_L5_00241
TP_L5_00241.Position 0 0.31 1.55
TP_L5_00241.Mother TES_L5
TP_L5_00241.Visibility 0

TES_Pixel_L5.Copy TP_L5_00242
TP_L5_00242.Position 0 0.465 -1.55
TP_L5_00242.Mother TES_L5
TP_L5_00242.Visibility 0

TES_Pixel_L5.Copy TP_L5_00243
TP_L5_00243.Position 0 0.465 -1.395
TP_L5_00243.Mother TES_L5
TP_L5_00243.Visibility 0

TES_Pixel_L5.Copy TP_L5_00244
TP_L5_00244.Position 0 0.465 -1.24
TP_L5_00244.Mother TES_L5
TP_L5_00244.Visibility 0

TES_Pixel_L5.Copy TP_L5_00245
TP_L5_00245.Position 0 0.465 -1.085
TP_L5_00245.Mother TES_L5
TP_L5_00245.Visibility 0

TES_Pixel_L5.Copy TP_L5_00246
TP_L5_00246.Position 0 0.465 -0.93
TP_L5_00246.Mother TES_L5
TP_L5_00246.Visibility 0

TES_Pixel_L5.Copy TP_L5_00247
TP_L5_00247.Position 0 0.465 -0.775
TP_L5_00247.Mother TES_L5
TP_L5_00247.Visibility 0

TES_Pixel_L5.Copy TP_L5_00248
TP_L5_00248.Position 0 0.465 -0.62
TP_L5_00248.Mother TES_L5
TP_L5_00248.Visibility 0

TES_Pixel_L5.Copy TP_L5_00249
TP_L5_00249.Position 0 0.465 -0.465
TP_L5_00249.Mother TES_L5
TP_L5_00249.Visibility 0

TES_Pixel_L5.Copy TP_L5_00250
TP_L5_00250.Position 0 0.465 -0.31
TP_L5_00250.Mother TES_L5
TP_L5_00250.Visibility 0

TES_Pixel_L5.Copy TP_L5_00251
TP_L5_00251.Position 0 0.465 -0.155
TP_L5_00251.Mother TES_L5
TP_L5_00251.Visibility 0

TES_Pixel_L5.Copy TP_L5_00252
TP_L5_00252.Position 0 0.465 0
TP_L5_00252.Mother TES_L5
TP_L5_00252.Visibility 0

TES_Pixel_L5.Copy TP_L5_00253
TP_L5_00253.Position 0 0.465 0.155
TP_L5_00253.Mother TES_L5
TP_L5_00253.Visibility 0

TES_Pixel_L5.Copy TP_L5_00254
TP_L5_00254.Position 0 0.465 0.31
TP_L5_00254.Mother TES_L5
TP_L5_00254.Visibility 0

TES_Pixel_L5.Copy TP_L5_00255
TP_L5_00255.Position 0 0.465 0.465
TP_L5_00255.Mother TES_L5
TP_L5_00255.Visibility 0

TES_Pixel_L5.Copy TP_L5_00256
TP_L5_00256.Position 0 0.465 0.62
TP_L5_00256.Mother TES_L5
TP_L5_00256.Visibility 0

TES_Pixel_L5.Copy TP_L5_00257
TP_L5_00257.Position 0 0.465 0.775
TP_L5_00257.Mother TES_L5
TP_L5_00257.Visibility 0

TES_Pixel_L5.Copy TP_L5_00258
TP_L5_00258.Position 0 0.465 0.93
TP_L5_00258.Mother TES_L5
TP_L5_00258.Visibility 0

TES_Pixel_L5.Copy TP_L5_00259
TP_L5_00259.Position 0 0.465 1.085
TP_L5_00259.Mother TES_L5
TP_L5_00259.Visibility 0

TES_Pixel_L5.Copy TP_L5_00260
TP_L5_00260.Position 0 0.465 1.24
TP_L5_00260.Mother TES_L5
TP_L5_00260.Visibility 0

TES_Pixel_L5.Copy TP_L5_00261
TP_L5_00261.Position 0 0.465 1.395
TP_L5_00261.Mother TES_L5
TP_L5_00261.Visibility 0

TES_Pixel_L5.Copy TP_L5_00262
TP_L5_00262.Position 0 0.465 1.55
TP_L5_00262.Mother TES_L5
TP_L5_00262.Visibility 0

TES_Pixel_L5.Copy TP_L5_00263
TP_L5_00263.Position 0 0.62 -1.55
TP_L5_00263.Mother TES_L5
TP_L5_00263.Visibility 0

TES_Pixel_L5.Copy TP_L5_00264
TP_L5_00264.Position 0 0.62 -1.395
TP_L5_00264.Mother TES_L5
TP_L5_00264.Visibility 0

TES_Pixel_L5.Copy TP_L5_00265
TP_L5_00265.Position 0 0.62 -1.24
TP_L5_00265.Mother TES_L5
TP_L5_00265.Visibility 0

TES_Pixel_L5.Copy TP_L5_00266
TP_L5_00266.Position 0 0.62 -1.085
TP_L5_00266.Mother TES_L5
TP_L5_00266.Visibility 0

TES_Pixel_L5.Copy TP_L5_00267
TP_L5_00267.Position 0 0.62 -0.93
TP_L5_00267.Mother TES_L5
TP_L5_00267.Visibility 0

TES_Pixel_L5.Copy TP_L5_00268
TP_L5_00268.Position 0 0.62 -0.775
TP_L5_00268.Mother TES_L5
TP_L5_00268.Visibility 0

TES_Pixel_L5.Copy TP_L5_00269
TP_L5_00269.Position 0 0.62 -0.62
TP_L5_00269.Mother TES_L5
TP_L5_00269.Visibility 0

TES_Pixel_L5.Copy TP_L5_00270
TP_L5_00270.Position 0 0.62 -0.465
TP_L5_00270.Mother TES_L5
TP_L5_00270.Visibility 0

TES_Pixel_L5.Copy TP_L5_00271
TP_L5_00271.Position 0 0.62 -0.31
TP_L5_00271.Mother TES_L5
TP_L5_00271.Visibility 0

TES_Pixel_L5.Copy TP_L5_00272
TP_L5_00272.Position 0 0.62 -0.155
TP_L5_00272.Mother TES_L5
TP_L5_00272.Visibility 0

TES_Pixel_L5.Copy TP_L5_00273
TP_L5_00273.Position 0 0.62 0
TP_L5_00273.Mother TES_L5
TP_L5_00273.Visibility 0

TES_Pixel_L5.Copy TP_L5_00274
TP_L5_00274.Position 0 0.62 0.155
TP_L5_00274.Mother TES_L5
TP_L5_00274.Visibility 0

TES_Pixel_L5.Copy TP_L5_00275
TP_L5_00275.Position 0 0.62 0.31
TP_L5_00275.Mother TES_L5
TP_L5_00275.Visibility 0

TES_Pixel_L5.Copy TP_L5_00276
TP_L5_00276.Position 0 0.62 0.465
TP_L5_00276.Mother TES_L5
TP_L5_00276.Visibility 0

TES_Pixel_L5.Copy TP_L5_00277
TP_L5_00277.Position 0 0.62 0.62
TP_L5_00277.Mother TES_L5
TP_L5_00277.Visibility 0

TES_Pixel_L5.Copy TP_L5_00278
TP_L5_00278.Position 0 0.62 0.775
TP_L5_00278.Mother TES_L5
TP_L5_00278.Visibility 0

TES_Pixel_L5.Copy TP_L5_00279
TP_L5_00279.Position 0 0.62 0.93
TP_L5_00279.Mother TES_L5
TP_L5_00279.Visibility 0

TES_Pixel_L5.Copy TP_L5_00280
TP_L5_00280.Position 0 0.62 1.085
TP_L5_00280.Mother TES_L5
TP_L5_00280.Visibility 0

TES_Pixel_L5.Copy TP_L5_00281
TP_L5_00281.Position 0 0.62 1.24
TP_L5_00281.Mother TES_L5
TP_L5_00281.Visibility 0

TES_Pixel_L5.Copy TP_L5_00282
TP_L5_00282.Position 0 0.62 1.395
TP_L5_00282.Mother TES_L5
TP_L5_00282.Visibility 0

TES_Pixel_L5.Copy TP_L5_00283
TP_L5_00283.Position 0 0.62 1.55
TP_L5_00283.Mother TES_L5
TP_L5_00283.Visibility 0

TES_Pixel_L5.Copy TP_L5_00284
TP_L5_00284.Position 0 0.775 -1.395
TP_L5_00284.Mother TES_L5
TP_L5_00284.Visibility 0

TES_Pixel_L5.Copy TP_L5_00285
TP_L5_00285.Position 0 0.775 -1.24
TP_L5_00285.Mother TES_L5
TP_L5_00285.Visibility 0

TES_Pixel_L5.Copy TP_L5_00286
TP_L5_00286.Position 0 0.775 -1.085
TP_L5_00286.Mother TES_L5
TP_L5_00286.Visibility 0

TES_Pixel_L5.Copy TP_L5_00287
TP_L5_00287.Position 0 0.775 -0.93
TP_L5_00287.Mother TES_L5
TP_L5_00287.Visibility 0

TES_Pixel_L5.Copy TP_L5_00288
TP_L5_00288.Position 0 0.775 -0.775
TP_L5_00288.Mother TES_L5
TP_L5_00288.Visibility 0

TES_Pixel_L5.Copy TP_L5_00289
TP_L5_00289.Position 0 0.775 -0.62
TP_L5_00289.Mother TES_L5
TP_L5_00289.Visibility 0

TES_Pixel_L5.Copy TP_L5_00290
TP_L5_00290.Position 0 0.775 -0.465
TP_L5_00290.Mother TES_L5
TP_L5_00290.Visibility 0

TES_Pixel_L5.Copy TP_L5_00291
TP_L5_00291.Position 0 0.775 -0.31
TP_L5_00291.Mother TES_L5
TP_L5_00291.Visibility 0

TES_Pixel_L5.Copy TP_L5_00292
TP_L5_00292.Position 0 0.775 -0.155
TP_L5_00292.Mother TES_L5
TP_L5_00292.Visibility 0

TES_Pixel_L5.Copy TP_L5_00293
TP_L5_00293.Position 0 0.775 0
TP_L5_00293.Mother TES_L5
TP_L5_00293.Visibility 0

TES_Pixel_L5.Copy TP_L5_00294
TP_L5_00294.Position 0 0.775 0.155
TP_L5_00294.Mother TES_L5
TP_L5_00294.Visibility 0

TES_Pixel_L5.Copy TP_L5_00295
TP_L5_00295.Position 0 0.775 0.31
TP_L5_00295.Mother TES_L5
TP_L5_00295.Visibility 0

TES_Pixel_L5.Copy TP_L5_00296
TP_L5_00296.Position 0 0.775 0.465
TP_L5_00296.Mother TES_L5
TP_L5_00296.Visibility 0

TES_Pixel_L5.Copy TP_L5_00297
TP_L5_00297.Position 0 0.775 0.62
TP_L5_00297.Mother TES_L5
TP_L5_00297.Visibility 0

TES_Pixel_L5.Copy TP_L5_00298
TP_L5_00298.Position 0 0.775 0.775
TP_L5_00298.Mother TES_L5
TP_L5_00298.Visibility 0

TES_Pixel_L5.Copy TP_L5_00299
TP_L5_00299.Position 0 0.775 0.93
TP_L5_00299.Mother TES_L5
TP_L5_00299.Visibility 0

TES_Pixel_L5.Copy TP_L5_00300
TP_L5_00300.Position 0 0.775 1.085
TP_L5_00300.Mother TES_L5
TP_L5_00300.Visibility 0

TES_Pixel_L5.Copy TP_L5_00301
TP_L5_00301.Position 0 0.775 1.24
TP_L5_00301.Mother TES_L5
TP_L5_00301.Visibility 0

TES_Pixel_L5.Copy TP_L5_00302
TP_L5_00302.Position 0 0.775 1.395
TP_L5_00302.Mother TES_L5
TP_L5_00302.Visibility 0

TES_Pixel_L5.Copy TP_L5_00303
TP_L5_00303.Position 0 0.93 -1.395
TP_L5_00303.Mother TES_L5
TP_L5_00303.Visibility 0

TES_Pixel_L5.Copy TP_L5_00304
TP_L5_00304.Position 0 0.93 -1.24
TP_L5_00304.Mother TES_L5
TP_L5_00304.Visibility 0

TES_Pixel_L5.Copy TP_L5_00305
TP_L5_00305.Position 0 0.93 -1.085
TP_L5_00305.Mother TES_L5
TP_L5_00305.Visibility 0

TES_Pixel_L5.Copy TP_L5_00306
TP_L5_00306.Position 0 0.93 -0.93
TP_L5_00306.Mother TES_L5
TP_L5_00306.Visibility 0

TES_Pixel_L5.Copy TP_L5_00307
TP_L5_00307.Position 0 0.93 -0.775
TP_L5_00307.Mother TES_L5
TP_L5_00307.Visibility 0

TES_Pixel_L5.Copy TP_L5_00308
TP_L5_00308.Position 0 0.93 -0.62
TP_L5_00308.Mother TES_L5
TP_L5_00308.Visibility 0

TES_Pixel_L5.Copy TP_L5_00309
TP_L5_00309.Position 0 0.93 -0.465
TP_L5_00309.Mother TES_L5
TP_L5_00309.Visibility 0

TES_Pixel_L5.Copy TP_L5_00310
TP_L5_00310.Position 0 0.93 -0.31
TP_L5_00310.Mother TES_L5
TP_L5_00310.Visibility 0

TES_Pixel_L5.Copy TP_L5_00311
TP_L5_00311.Position 0 0.93 -0.155
TP_L5_00311.Mother TES_L5
TP_L5_00311.Visibility 0

TES_Pixel_L5.Copy TP_L5_00312
TP_L5_00312.Position 0 0.93 0
TP_L5_00312.Mother TES_L5
TP_L5_00312.Visibility 0

TES_Pixel_L5.Copy TP_L5_00313
TP_L5_00313.Position 0 0.93 0.155
TP_L5_00313.Mother TES_L5
TP_L5_00313.Visibility 0

TES_Pixel_L5.Copy TP_L5_00314
TP_L5_00314.Position 0 0.93 0.31
TP_L5_00314.Mother TES_L5
TP_L5_00314.Visibility 0

TES_Pixel_L5.Copy TP_L5_00315
TP_L5_00315.Position 0 0.93 0.465
TP_L5_00315.Mother TES_L5
TP_L5_00315.Visibility 0

TES_Pixel_L5.Copy TP_L5_00316
TP_L5_00316.Position 0 0.93 0.62
TP_L5_00316.Mother TES_L5
TP_L5_00316.Visibility 0

TES_Pixel_L5.Copy TP_L5_00317
TP_L5_00317.Position 0 0.93 0.775
TP_L5_00317.Mother TES_L5
TP_L5_00317.Visibility 0

TES_Pixel_L5.Copy TP_L5_00318
TP_L5_00318.Position 0 0.93 0.93
TP_L5_00318.Mother TES_L5
TP_L5_00318.Visibility 0

TES_Pixel_L5.Copy TP_L5_00319
TP_L5_00319.Position 0 0.93 1.085
TP_L5_00319.Mother TES_L5
TP_L5_00319.Visibility 0

TES_Pixel_L5.Copy TP_L5_00320
TP_L5_00320.Position 0 0.93 1.24
TP_L5_00320.Mother TES_L5
TP_L5_00320.Visibility 0

TES_Pixel_L5.Copy TP_L5_00321
TP_L5_00321.Position 0 0.93 1.395
TP_L5_00321.Mother TES_L5
TP_L5_00321.Visibility 0

TES_Pixel_L5.Copy TP_L5_00322
TP_L5_00322.Position 0 1.085 -1.24
TP_L5_00322.Mother TES_L5
TP_L5_00322.Visibility 0

TES_Pixel_L5.Copy TP_L5_00323
TP_L5_00323.Position 0 1.085 -1.085
TP_L5_00323.Mother TES_L5
TP_L5_00323.Visibility 0

TES_Pixel_L5.Copy TP_L5_00324
TP_L5_00324.Position 0 1.085 -0.93
TP_L5_00324.Mother TES_L5
TP_L5_00324.Visibility 0

TES_Pixel_L5.Copy TP_L5_00325
TP_L5_00325.Position 0 1.085 -0.775
TP_L5_00325.Mother TES_L5
TP_L5_00325.Visibility 0

TES_Pixel_L5.Copy TP_L5_00326
TP_L5_00326.Position 0 1.085 -0.62
TP_L5_00326.Mother TES_L5
TP_L5_00326.Visibility 0

TES_Pixel_L5.Copy TP_L5_00327
TP_L5_00327.Position 0 1.085 -0.465
TP_L5_00327.Mother TES_L5
TP_L5_00327.Visibility 0

TES_Pixel_L5.Copy TP_L5_00328
TP_L5_00328.Position 0 1.085 -0.31
TP_L5_00328.Mother TES_L5
TP_L5_00328.Visibility 0

TES_Pixel_L5.Copy TP_L5_00329
TP_L5_00329.Position 0 1.085 -0.155
TP_L5_00329.Mother TES_L5
TP_L5_00329.Visibility 0

TES_Pixel_L5.Copy TP_L5_00330
TP_L5_00330.Position 0 1.085 0
TP_L5_00330.Mother TES_L5
TP_L5_00330.Visibility 0

TES_Pixel_L5.Copy TP_L5_00331
TP_L5_00331.Position 0 1.085 0.155
TP_L5_00331.Mother TES_L5
TP_L5_00331.Visibility 0

TES_Pixel_L5.Copy TP_L5_00332
TP_L5_00332.Position 0 1.085 0.31
TP_L5_00332.Mother TES_L5
TP_L5_00332.Visibility 0

TES_Pixel_L5.Copy TP_L5_00333
TP_L5_00333.Position 0 1.085 0.465
TP_L5_00333.Mother TES_L5
TP_L5_00333.Visibility 0

TES_Pixel_L5.Copy TP_L5_00334
TP_L5_00334.Position 0 1.085 0.62
TP_L5_00334.Mother TES_L5
TP_L5_00334.Visibility 0

TES_Pixel_L5.Copy TP_L5_00335
TP_L5_00335.Position 0 1.085 0.775
TP_L5_00335.Mother TES_L5
TP_L5_00335.Visibility 0

TES_Pixel_L5.Copy TP_L5_00336
TP_L5_00336.Position 0 1.085 0.93
TP_L5_00336.Mother TES_L5
TP_L5_00336.Visibility 0

TES_Pixel_L5.Copy TP_L5_00337
TP_L5_00337.Position 0 1.085 1.085
TP_L5_00337.Mother TES_L5
TP_L5_00337.Visibility 0

TES_Pixel_L5.Copy TP_L5_00338
TP_L5_00338.Position 0 1.085 1.24
TP_L5_00338.Mother TES_L5
TP_L5_00338.Visibility 0

TES_Pixel_L5.Copy TP_L5_00339
TP_L5_00339.Position 0 1.24 -1.085
TP_L5_00339.Mother TES_L5
TP_L5_00339.Visibility 0

TES_Pixel_L5.Copy TP_L5_00340
TP_L5_00340.Position 0 1.24 -0.93
TP_L5_00340.Mother TES_L5
TP_L5_00340.Visibility 0

TES_Pixel_L5.Copy TP_L5_00341
TP_L5_00341.Position 0 1.24 -0.775
TP_L5_00341.Mother TES_L5
TP_L5_00341.Visibility 0

TES_Pixel_L5.Copy TP_L5_00342
TP_L5_00342.Position 0 1.24 -0.62
TP_L5_00342.Mother TES_L5
TP_L5_00342.Visibility 0

TES_Pixel_L5.Copy TP_L5_00343
TP_L5_00343.Position 0 1.24 -0.465
TP_L5_00343.Mother TES_L5
TP_L5_00343.Visibility 0

TES_Pixel_L5.Copy TP_L5_00344
TP_L5_00344.Position 0 1.24 -0.31
TP_L5_00344.Mother TES_L5
TP_L5_00344.Visibility 0

TES_Pixel_L5.Copy TP_L5_00345
TP_L5_00345.Position 0 1.24 -0.155
TP_L5_00345.Mother TES_L5
TP_L5_00345.Visibility 0

TES_Pixel_L5.Copy TP_L5_00346
TP_L5_00346.Position 0 1.24 0
TP_L5_00346.Mother TES_L5
TP_L5_00346.Visibility 0

TES_Pixel_L5.Copy TP_L5_00347
TP_L5_00347.Position 0 1.24 0.155
TP_L5_00347.Mother TES_L5
TP_L5_00347.Visibility 0

TES_Pixel_L5.Copy TP_L5_00348
TP_L5_00348.Position 0 1.24 0.31
TP_L5_00348.Mother TES_L5
TP_L5_00348.Visibility 0

TES_Pixel_L5.Copy TP_L5_00349
TP_L5_00349.Position 0 1.24 0.465
TP_L5_00349.Mother TES_L5
TP_L5_00349.Visibility 0

TES_Pixel_L5.Copy TP_L5_00350
TP_L5_00350.Position 0 1.24 0.62
TP_L5_00350.Mother TES_L5
TP_L5_00350.Visibility 0

TES_Pixel_L5.Copy TP_L5_00351
TP_L5_00351.Position 0 1.24 0.775
TP_L5_00351.Mother TES_L5
TP_L5_00351.Visibility 0

TES_Pixel_L5.Copy TP_L5_00352
TP_L5_00352.Position 0 1.24 0.93
TP_L5_00352.Mother TES_L5
TP_L5_00352.Visibility 0

TES_Pixel_L5.Copy TP_L5_00353
TP_L5_00353.Position 0 1.24 1.085
TP_L5_00353.Mother TES_L5
TP_L5_00353.Visibility 0

TES_Pixel_L5.Copy TP_L5_00354
TP_L5_00354.Position 0 1.395 -0.93
TP_L5_00354.Mother TES_L5
TP_L5_00354.Visibility 0

TES_Pixel_L5.Copy TP_L5_00355
TP_L5_00355.Position 0 1.395 -0.775
TP_L5_00355.Mother TES_L5
TP_L5_00355.Visibility 0

TES_Pixel_L5.Copy TP_L5_00356
TP_L5_00356.Position 0 1.395 -0.62
TP_L5_00356.Mother TES_L5
TP_L5_00356.Visibility 0

TES_Pixel_L5.Copy TP_L5_00357
TP_L5_00357.Position 0 1.395 -0.465
TP_L5_00357.Mother TES_L5
TP_L5_00357.Visibility 0

TES_Pixel_L5.Copy TP_L5_00358
TP_L5_00358.Position 0 1.395 -0.31
TP_L5_00358.Mother TES_L5
TP_L5_00358.Visibility 0

TES_Pixel_L5.Copy TP_L5_00359
TP_L5_00359.Position 0 1.395 -0.155
TP_L5_00359.Mother TES_L5
TP_L5_00359.Visibility 0

TES_Pixel_L5.Copy TP_L5_00360
TP_L5_00360.Position 0 1.395 0
TP_L5_00360.Mother TES_L5
TP_L5_00360.Visibility 0

TES_Pixel_L5.Copy TP_L5_00361
TP_L5_00361.Position 0 1.395 0.155
TP_L5_00361.Mother TES_L5
TP_L5_00361.Visibility 0

TES_Pixel_L5.Copy TP_L5_00362
TP_L5_00362.Position 0 1.395 0.31
TP_L5_00362.Mother TES_L5
TP_L5_00362.Visibility 0

TES_Pixel_L5.Copy TP_L5_00363
TP_L5_00363.Position 0 1.395 0.465
TP_L5_00363.Mother TES_L5
TP_L5_00363.Visibility 0

TES_Pixel_L5.Copy TP_L5_00364
TP_L5_00364.Position 0 1.395 0.62
TP_L5_00364.Mother TES_L5
TP_L5_00364.Visibility 0

TES_Pixel_L5.Copy TP_L5_00365
TP_L5_00365.Position 0 1.395 0.775
TP_L5_00365.Mother TES_L5
TP_L5_00365.Visibility 0

TES_Pixel_L5.Copy TP_L5_00366
TP_L5_00366.Position 0 1.395 0.93
TP_L5_00366.Mother TES_L5
TP_L5_00366.Visibility 0

TES_Pixel_L5.Copy TP_L5_00367
TP_L5_00367.Position 0 1.55 -0.62
TP_L5_00367.Mother TES_L5
TP_L5_00367.Visibility 0

TES_Pixel_L5.Copy TP_L5_00368
TP_L5_00368.Position 0 1.55 -0.465
TP_L5_00368.Mother TES_L5
TP_L5_00368.Visibility 0

TES_Pixel_L5.Copy TP_L5_00369
TP_L5_00369.Position 0 1.55 -0.31
TP_L5_00369.Mother TES_L5
TP_L5_00369.Visibility 0

TES_Pixel_L5.Copy TP_L5_00370
TP_L5_00370.Position 0 1.55 -0.155
TP_L5_00370.Mother TES_L5
TP_L5_00370.Visibility 0

TES_Pixel_L5.Copy TP_L5_00371
TP_L5_00371.Position 0 1.55 0
TP_L5_00371.Mother TES_L5
TP_L5_00371.Visibility 0

TES_Pixel_L5.Copy TP_L5_00372
TP_L5_00372.Position 0 1.55 0.155
TP_L5_00372.Mother TES_L5
TP_L5_00372.Visibility 0

TES_Pixel_L5.Copy TP_L5_00373
TP_L5_00373.Position 0 1.55 0.31
TP_L5_00373.Mother TES_L5
TP_L5_00373.Visibility 0

TES_Pixel_L5.Copy TP_L5_00374
TP_L5_00374.Position 0 1.55 0.465
TP_L5_00374.Mother TES_L5
TP_L5_00374.Visibility 0

TES_Pixel_L5.Copy TP_L5_00375
TP_L5_00375.Position 0 1.55 0.62
TP_L5_00375.Mother TES_L5
TP_L5_00375.Visibility 0
// END PINNED_SG3B_TES_BLOCK

// BEGIN PINNED_SG3B_SUBSTRATE_AND_COPPER_SUPPORT_BLOCK
// Volume Si_Substrate_Stack_side_entry_L0; material=Silicon
Volume Si_Substrate_Stack_side_entry_L0
Si_Substrate_Stack_side_entry_L0.Material Silicon
Si_Substrate_Stack_side_entry_L0.Visibility 1
Si_Substrate_Stack_side_entry_L0.Shape BRIK 0.015 1.8 1.8

Si_Substrate_Stack_side_entry_L0.Position -38.37 0 -2.8
Si_Substrate_Stack_side_entry_L0.Mother InstrumentFrame

// Volume Si_Substrate_Stack_side_entry_L1; material=Silicon
Volume Si_Substrate_Stack_side_entry_L1
Si_Substrate_Stack_side_entry_L1.Material Silicon
Si_Substrate_Stack_side_entry_L1.Visibility 1
Si_Substrate_Stack_side_entry_L1.Shape BRIK 0.015 1.8 1.8

Si_Substrate_Stack_side_entry_L1.Position -37.17 0 -2.8
Si_Substrate_Stack_side_entry_L1.Mother InstrumentFrame

// Volume Si_Substrate_Stack_side_entry_L2; material=Silicon
Volume Si_Substrate_Stack_side_entry_L2
Si_Substrate_Stack_side_entry_L2.Material Silicon
Si_Substrate_Stack_side_entry_L2.Visibility 1
Si_Substrate_Stack_side_entry_L2.Shape BRIK 0.015 1.8 1.8

Si_Substrate_Stack_side_entry_L2.Position -35.97 0 -2.8
Si_Substrate_Stack_side_entry_L2.Mother InstrumentFrame

// Volume Si_Substrate_Stack_side_entry_L3; material=Silicon
Volume Si_Substrate_Stack_side_entry_L3
Si_Substrate_Stack_side_entry_L3.Material Silicon
Si_Substrate_Stack_side_entry_L3.Visibility 1
Si_Substrate_Stack_side_entry_L3.Shape BRIK 0.015 1.8 1.8

Si_Substrate_Stack_side_entry_L3.Position -34.77 0 -2.8
Si_Substrate_Stack_side_entry_L3.Mother InstrumentFrame

// Volume Si_Substrate_Stack_side_entry_L4; material=Silicon
Volume Si_Substrate_Stack_side_entry_L4
Si_Substrate_Stack_side_entry_L4.Material Silicon
Si_Substrate_Stack_side_entry_L4.Visibility 1
Si_Substrate_Stack_side_entry_L4.Shape BRIK 0.015 1.8 1.8

Si_Substrate_Stack_side_entry_L4.Position -33.57 0 -2.8
Si_Substrate_Stack_side_entry_L4.Mother InstrumentFrame

// Volume Si_Substrate_Stack_side_entry_L5; material=Silicon
Volume Si_Substrate_Stack_side_entry_L5
Si_Substrate_Stack_side_entry_L5.Material Silicon
Si_Substrate_Stack_side_entry_L5.Visibility 1
Si_Substrate_Stack_side_entry_L5.Shape BRIK 0.015 1.8 1.8

Si_Substrate_Stack_side_entry_L5.Position -32.37 0 -2.8
Si_Substrate_Stack_side_entry_L5.Mother InstrumentFrame

// Volume Cu_SubstrateSupport_OpenRing_L1_ZP_panel; material=Copper
Volume Cu_SubstrateSupport_OpenRing_L1_ZP_panel
Cu_SubstrateSupport_OpenRing_L1_ZP_panel.Material Copper
Cu_SubstrateSupport_OpenRing_L1_ZP_panel.Visibility 1
Cu_SubstrateSupport_OpenRing_L1_ZP_panel.Shape BRIK 0.15 1.73 0.175

Cu_SubstrateSupport_OpenRing_L1_ZP_panel.Position -38.2 0 -0.775
Cu_SubstrateSupport_OpenRing_L1_ZP_panel.Mother InstrumentFrame

// Volume Cu_SubstrateSupport_OpenRing_L1_ZM_panel; material=Copper
Volume Cu_SubstrateSupport_OpenRing_L1_ZM_panel
Cu_SubstrateSupport_OpenRing_L1_ZM_panel.Material Copper
Cu_SubstrateSupport_OpenRing_L1_ZM_panel.Visibility 1
Cu_SubstrateSupport_OpenRing_L1_ZM_panel.Shape BRIK 0.15 1.73 0.175

Cu_SubstrateSupport_OpenRing_L1_ZM_panel.Position -38.2 0 -4.825
Cu_SubstrateSupport_OpenRing_L1_ZM_panel.Mother InstrumentFrame

// Volume Cu_SubstrateSupport_OpenRing_L1_YP_panel; material=Copper
Volume Cu_SubstrateSupport_OpenRing_L1_YP_panel
Cu_SubstrateSupport_OpenRing_L1_YP_panel.Material Copper
Cu_SubstrateSupport_OpenRing_L1_YP_panel.Visibility 1
Cu_SubstrateSupport_OpenRing_L1_YP_panel.Shape BRIK 0.15 0.175 1.73

Cu_SubstrateSupport_OpenRing_L1_YP_panel.Position -38.2 2.025 -2.8
Cu_SubstrateSupport_OpenRing_L1_YP_panel.Mother InstrumentFrame

// Volume Cu_SubstrateSupport_OpenRing_L1_YM_panel; material=Copper
Volume Cu_SubstrateSupport_OpenRing_L1_YM_panel
Cu_SubstrateSupport_OpenRing_L1_YM_panel.Material Copper
Cu_SubstrateSupport_OpenRing_L1_YM_panel.Visibility 1
Cu_SubstrateSupport_OpenRing_L1_YM_panel.Shape BRIK 0.15 0.175 1.73

Cu_SubstrateSupport_OpenRing_L1_YM_panel.Position -38.2 -2.025 -2.8
Cu_SubstrateSupport_OpenRing_L1_YM_panel.Mother InstrumentFrame

// Volume Cu_SubstrateSupport_OpenRing_L2_ZP_panel; material=Copper
Volume Cu_SubstrateSupport_OpenRing_L2_ZP_panel
Cu_SubstrateSupport_OpenRing_L2_ZP_panel.Material Copper
Cu_SubstrateSupport_OpenRing_L2_ZP_panel.Visibility 1
Cu_SubstrateSupport_OpenRing_L2_ZP_panel.Shape BRIK 0.15 1.73 0.175

Cu_SubstrateSupport_OpenRing_L2_ZP_panel.Position -37 0 -0.775
Cu_SubstrateSupport_OpenRing_L2_ZP_panel.Mother InstrumentFrame

// Volume Cu_SubstrateSupport_OpenRing_L2_ZM_panel; material=Copper
Volume Cu_SubstrateSupport_OpenRing_L2_ZM_panel
Cu_SubstrateSupport_OpenRing_L2_ZM_panel.Material Copper
Cu_SubstrateSupport_OpenRing_L2_ZM_panel.Visibility 1
Cu_SubstrateSupport_OpenRing_L2_ZM_panel.Shape BRIK 0.15 1.73 0.175

Cu_SubstrateSupport_OpenRing_L2_ZM_panel.Position -37 0 -4.825
Cu_SubstrateSupport_OpenRing_L2_ZM_panel.Mother InstrumentFrame

// Volume Cu_SubstrateSupport_OpenRing_L2_YP_panel; material=Copper
Volume Cu_SubstrateSupport_OpenRing_L2_YP_panel
Cu_SubstrateSupport_OpenRing_L2_YP_panel.Material Copper
Cu_SubstrateSupport_OpenRing_L2_YP_panel.Visibility 1
Cu_SubstrateSupport_OpenRing_L2_YP_panel.Shape BRIK 0.15 0.175 1.73

Cu_SubstrateSupport_OpenRing_L2_YP_panel.Position -37 2.025 -2.8
Cu_SubstrateSupport_OpenRing_L2_YP_panel.Mother InstrumentFrame

// Volume Cu_SubstrateSupport_OpenRing_L2_YM_panel; material=Copper
Volume Cu_SubstrateSupport_OpenRing_L2_YM_panel
Cu_SubstrateSupport_OpenRing_L2_YM_panel.Material Copper
Cu_SubstrateSupport_OpenRing_L2_YM_panel.Visibility 1
Cu_SubstrateSupport_OpenRing_L2_YM_panel.Shape BRIK 0.15 0.175 1.73

Cu_SubstrateSupport_OpenRing_L2_YM_panel.Position -37 -2.025 -2.8
Cu_SubstrateSupport_OpenRing_L2_YM_panel.Mother InstrumentFrame

// Volume Cu_SubstrateSupport_OpenRing_L3_ZP_panel; material=Copper
Volume Cu_SubstrateSupport_OpenRing_L3_ZP_panel
Cu_SubstrateSupport_OpenRing_L3_ZP_panel.Material Copper
Cu_SubstrateSupport_OpenRing_L3_ZP_panel.Visibility 1
Cu_SubstrateSupport_OpenRing_L3_ZP_panel.Shape BRIK 0.15 1.73 0.175

Cu_SubstrateSupport_OpenRing_L3_ZP_panel.Position -35.8 0 -0.775
Cu_SubstrateSupport_OpenRing_L3_ZP_panel.Mother InstrumentFrame

// Volume Cu_SubstrateSupport_OpenRing_L3_ZM_panel; material=Copper
Volume Cu_SubstrateSupport_OpenRing_L3_ZM_panel
Cu_SubstrateSupport_OpenRing_L3_ZM_panel.Material Copper
Cu_SubstrateSupport_OpenRing_L3_ZM_panel.Visibility 1
Cu_SubstrateSupport_OpenRing_L3_ZM_panel.Shape BRIK 0.15 1.73 0.175

Cu_SubstrateSupport_OpenRing_L3_ZM_panel.Position -35.8 0 -4.825
Cu_SubstrateSupport_OpenRing_L3_ZM_panel.Mother InstrumentFrame

// Volume Cu_SubstrateSupport_OpenRing_L3_YP_panel; material=Copper
Volume Cu_SubstrateSupport_OpenRing_L3_YP_panel
Cu_SubstrateSupport_OpenRing_L3_YP_panel.Material Copper
Cu_SubstrateSupport_OpenRing_L3_YP_panel.Visibility 1
Cu_SubstrateSupport_OpenRing_L3_YP_panel.Shape BRIK 0.15 0.175 1.73

Cu_SubstrateSupport_OpenRing_L3_YP_panel.Position -35.8 2.025 -2.8
Cu_SubstrateSupport_OpenRing_L3_YP_panel.Mother InstrumentFrame

// Volume Cu_SubstrateSupport_OpenRing_L3_YM_panel; material=Copper
Volume Cu_SubstrateSupport_OpenRing_L3_YM_panel
Cu_SubstrateSupport_OpenRing_L3_YM_panel.Material Copper
Cu_SubstrateSupport_OpenRing_L3_YM_panel.Visibility 1
Cu_SubstrateSupport_OpenRing_L3_YM_panel.Shape BRIK 0.15 0.175 1.73

Cu_SubstrateSupport_OpenRing_L3_YM_panel.Position -35.8 -2.025 -2.8
Cu_SubstrateSupport_OpenRing_L3_YM_panel.Mother InstrumentFrame

// Volume Cu_SubstrateSupport_OpenRing_L4_ZP_panel; material=Copper
Volume Cu_SubstrateSupport_OpenRing_L4_ZP_panel
Cu_SubstrateSupport_OpenRing_L4_ZP_panel.Material Copper
Cu_SubstrateSupport_OpenRing_L4_ZP_panel.Visibility 1
Cu_SubstrateSupport_OpenRing_L4_ZP_panel.Shape BRIK 0.15 1.73 0.175

Cu_SubstrateSupport_OpenRing_L4_ZP_panel.Position -34.6 0 -0.775
Cu_SubstrateSupport_OpenRing_L4_ZP_panel.Mother InstrumentFrame

// Volume Cu_SubstrateSupport_OpenRing_L4_ZM_panel; material=Copper
Volume Cu_SubstrateSupport_OpenRing_L4_ZM_panel
Cu_SubstrateSupport_OpenRing_L4_ZM_panel.Material Copper
Cu_SubstrateSupport_OpenRing_L4_ZM_panel.Visibility 1
Cu_SubstrateSupport_OpenRing_L4_ZM_panel.Shape BRIK 0.15 1.73 0.175

Cu_SubstrateSupport_OpenRing_L4_ZM_panel.Position -34.6 0 -4.825
Cu_SubstrateSupport_OpenRing_L4_ZM_panel.Mother InstrumentFrame

// Volume Cu_SubstrateSupport_OpenRing_L4_YP_panel; material=Copper
Volume Cu_SubstrateSupport_OpenRing_L4_YP_panel
Cu_SubstrateSupport_OpenRing_L4_YP_panel.Material Copper
Cu_SubstrateSupport_OpenRing_L4_YP_panel.Visibility 1
Cu_SubstrateSupport_OpenRing_L4_YP_panel.Shape BRIK 0.15 0.175 1.73

Cu_SubstrateSupport_OpenRing_L4_YP_panel.Position -34.6 2.025 -2.8
Cu_SubstrateSupport_OpenRing_L4_YP_panel.Mother InstrumentFrame

// Volume Cu_SubstrateSupport_OpenRing_L4_YM_panel; material=Copper
Volume Cu_SubstrateSupport_OpenRing_L4_YM_panel
Cu_SubstrateSupport_OpenRing_L4_YM_panel.Material Copper
Cu_SubstrateSupport_OpenRing_L4_YM_panel.Visibility 1
Cu_SubstrateSupport_OpenRing_L4_YM_panel.Shape BRIK 0.15 0.175 1.73

Cu_SubstrateSupport_OpenRing_L4_YM_panel.Position -34.6 -2.025 -2.8
Cu_SubstrateSupport_OpenRing_L4_YM_panel.Mother InstrumentFrame

// Volume Cu_SubstrateSupport_OpenRing_L5_ZP_panel; material=Copper
Volume Cu_SubstrateSupport_OpenRing_L5_ZP_panel
Cu_SubstrateSupport_OpenRing_L5_ZP_panel.Material Copper
Cu_SubstrateSupport_OpenRing_L5_ZP_panel.Visibility 1
Cu_SubstrateSupport_OpenRing_L5_ZP_panel.Shape BRIK 0.15 1.73 0.175

Cu_SubstrateSupport_OpenRing_L5_ZP_panel.Position -33.4 0 -0.775
Cu_SubstrateSupport_OpenRing_L5_ZP_panel.Mother InstrumentFrame

// Volume Cu_SubstrateSupport_OpenRing_L5_ZM_panel; material=Copper
Volume Cu_SubstrateSupport_OpenRing_L5_ZM_panel
Cu_SubstrateSupport_OpenRing_L5_ZM_panel.Material Copper
Cu_SubstrateSupport_OpenRing_L5_ZM_panel.Visibility 1
Cu_SubstrateSupport_OpenRing_L5_ZM_panel.Shape BRIK 0.15 1.73 0.175

Cu_SubstrateSupport_OpenRing_L5_ZM_panel.Position -33.4 0 -4.825
Cu_SubstrateSupport_OpenRing_L5_ZM_panel.Mother InstrumentFrame

// Volume Cu_SubstrateSupport_OpenRing_L5_YP_panel; material=Copper
Volume Cu_SubstrateSupport_OpenRing_L5_YP_panel
Cu_SubstrateSupport_OpenRing_L5_YP_panel.Material Copper
Cu_SubstrateSupport_OpenRing_L5_YP_panel.Visibility 1
Cu_SubstrateSupport_OpenRing_L5_YP_panel.Shape BRIK 0.15 0.175 1.73

Cu_SubstrateSupport_OpenRing_L5_YP_panel.Position -33.4 2.025 -2.8
Cu_SubstrateSupport_OpenRing_L5_YP_panel.Mother InstrumentFrame

// Volume Cu_SubstrateSupport_OpenRing_L5_YM_panel; material=Copper
Volume Cu_SubstrateSupport_OpenRing_L5_YM_panel
Cu_SubstrateSupport_OpenRing_L5_YM_panel.Material Copper
Cu_SubstrateSupport_OpenRing_L5_YM_panel.Visibility 1
Cu_SubstrateSupport_OpenRing_L5_YM_panel.Shape BRIK 0.15 0.175 1.73

Cu_SubstrateSupport_OpenRing_L5_YM_panel.Position -33.4 -2.025 -2.8
Cu_SubstrateSupport_OpenRing_L5_YM_panel.Mother InstrumentFrame

// BEGIN SG3_CU_L0_HEATSINK_RING
// Replaces the SF3 solid L0 Cu plate.  The annulus overlaps the nominal
// 1.8 cm TES substrate projection by 1.0 cm and protrudes beyond it by 1.0 cm.
// The four inherited edge rods at y,z = +/-1.95 cm terminate inside this band.
Shape BRIK SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm_OuterShape
SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm_OuterShape.Parameters 0.175 2.8 2.8
Shape BRIK SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm_CenterCutShape
SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm_CenterCutShape.Parameters 0.1751 0.8 0.8
Orientation SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm_CenterCutOrientation
SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm_CenterCutOrientation.Position 0 0 0
Shape Subtraction SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm_Shape
SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm_Shape.Parameters SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm_OuterShape SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm_CenterCutShape SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm_CenterCutOrientation
Volume SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm
SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm.Material Copper
SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm.Visibility 1
SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm.Shape SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm_Shape
SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm.Position -32.13 0 -2.8
SG3_Cu_SubstrateSupport_L0_HeatSinkRing_10mm.Mother InstrumentFrame
// END SG3_CU_L0_HEATSINK_RING

// Volume Cu_SubstrateSupport_EdgeRod_1; material=Copper
Volume Cu_SubstrateSupport_EdgeRod_1
Cu_SubstrateSupport_EdgeRod_1.Material Copper
Cu_SubstrateSupport_EdgeRod_1.Visibility 1
Cu_SubstrateSupport_EdgeRod_1.Shape BRIK 2.9425 0.0707106781 0.0707106781

Cu_SubstrateSupport_EdgeRod_1.Position -35.2575 1.95 -0.85
Cu_SubstrateSupport_EdgeRod_1.Mother InstrumentFrame

// Volume Cu_SubstrateSupport_EdgeRod_2; material=Copper
Volume Cu_SubstrateSupport_EdgeRod_2
Cu_SubstrateSupport_EdgeRod_2.Material Copper
Cu_SubstrateSupport_EdgeRod_2.Visibility 1
Cu_SubstrateSupport_EdgeRod_2.Shape BRIK 2.9425 0.0707106781 0.0707106781

Cu_SubstrateSupport_EdgeRod_2.Position -35.2575 -1.95 -0.85
Cu_SubstrateSupport_EdgeRod_2.Mother InstrumentFrame

// Volume Cu_SubstrateSupport_EdgeRod_3; material=Copper
Volume Cu_SubstrateSupport_EdgeRod_3
Cu_SubstrateSupport_EdgeRod_3.Material Copper
Cu_SubstrateSupport_EdgeRod_3.Visibility 1
Cu_SubstrateSupport_EdgeRod_3.Shape BRIK 2.9425 0.0707106781 0.0707106781

Cu_SubstrateSupport_EdgeRod_3.Position -35.2575 1.95 -4.75
Cu_SubstrateSupport_EdgeRod_3.Mother InstrumentFrame

// Volume Cu_SubstrateSupport_EdgeRod_4; material=Copper
Volume Cu_SubstrateSupport_EdgeRod_4
Cu_SubstrateSupport_EdgeRod_4.Material Copper
Cu_SubstrateSupport_EdgeRod_4.Visibility 1
Cu_SubstrateSupport_EdgeRod_4.Shape BRIK 2.9425 0.0707106781 0.0707106781

Cu_SubstrateSupport_EdgeRod_4.Position -35.2575 -1.95 -4.75
Cu_SubstrateSupport_EdgeRod_4.Mother InstrumentFrame
// END PINNED_SG3B_SUBSTRATE_AND_COPPER_SUPPORT_BLOCK

// SH3 local TES cold plate completion; this is not the MXC plate.
Volume SH3_TES_BottomColdPlate_CentralHub
SH3_TES_BottomColdPlate_CentralHub.Material Copper
SH3_TES_BottomColdPlate_CentralHub.Visibility 1
SH3_TES_BottomColdPlate_CentralHub.Shape TUBS 0.000000 0.160000 0.175000 0 360
SH3_TES_BottomColdPlate_CentralHub.Position -32.13 0 -2.8
SH3_TES_BottomColdPlate_CentralHub.Rotation 0 90 0
SH3_TES_BottomColdPlate_CentralHub.Mother InstrumentFrame

Volume SH3_TES_BottomColdPlate_Spoke_YP
SH3_TES_BottomColdPlate_Spoke_YP.Material Copper
SH3_TES_BottomColdPlate_Spoke_YP.Visibility 1
SH3_TES_BottomColdPlate_Spoke_YP.Shape BRIK 0.175000 0.320000 0.080000
SH3_TES_BottomColdPlate_Spoke_YP.Position -32.13 0.48 -2.8
SH3_TES_BottomColdPlate_Spoke_YP.Mother InstrumentFrame

Volume SH3_TES_BottomColdPlate_Spoke_YM
SH3_TES_BottomColdPlate_Spoke_YM.Material Copper
SH3_TES_BottomColdPlate_Spoke_YM.Visibility 1
SH3_TES_BottomColdPlate_Spoke_YM.Shape BRIK 0.175000 0.320000 0.080000
SH3_TES_BottomColdPlate_Spoke_YM.Position -32.13 -0.48 -2.8
SH3_TES_BottomColdPlate_Spoke_YM.Mother InstrumentFrame

Volume SH3_TES_BottomColdPlate_Spoke_ZP
SH3_TES_BottomColdPlate_Spoke_ZP.Material Copper
SH3_TES_BottomColdPlate_Spoke_ZP.Visibility 1
SH3_TES_BottomColdPlate_Spoke_ZP.Shape BRIK 0.175000 0.080000 0.320000
SH3_TES_BottomColdPlate_Spoke_ZP.Position -32.13 0 -2.32
SH3_TES_BottomColdPlate_Spoke_ZP.Mother InstrumentFrame

Volume SH3_TES_BottomColdPlate_Spoke_ZM
SH3_TES_BottomColdPlate_Spoke_ZM.Material Copper
SH3_TES_BottomColdPlate_Spoke_ZM.Visibility 1
SH3_TES_BottomColdPlate_Spoke_ZM.Shape BRIK 0.175000 0.080000 0.320000
SH3_TES_BottomColdPlate_Spoke_ZM.Position -32.13 0 -3.28
SH3_TES_BottomColdPlate_Spoke_ZM.Mother InstrumentFrame

Volume SH3_TES_ColdFinger_InterfaceStub
SH3_TES_ColdFinger_InterfaceStub.Material Copper
SH3_TES_ColdFinger_InterfaceStub.Visibility 1
SH3_TES_ColdFinger_InterfaceStub.Shape TUBS 0.000000 0.160000 1.602500 0 360
SH3_TES_ColdFinger_InterfaceStub.Position -30.3525 0 -2.8
SH3_TES_ColdFinger_InterfaceStub.Rotation 0 90 0
SH3_TES_ColdFinger_InterfaceStub.Mother InstrumentFrame
// The stub terminates at the SH3 merge plane; the main-DR cold finger is not included.

// BEGIN SH3_NESTED_CHIMNEY_SHELLS
// local inner aluminium liner; thermal-stage ownership deliberately unset
Volume SH3_Layer01_SideShell
SH3_Layer01_SideShell.Material Aluminium
SH3_Layer01_SideShell.Visibility 1
SH3_Layer01_SideShell.Shape TUBS 4.000000 4.200000 3.950000 0 360
SH3_Layer01_SideShell.Position -35.35 0 -2.8
SH3_Layer01_SideShell.Rotation 0 90 0
SH3_Layer01_SideShell.Mother InstrumentFrame
Volume SH3_Layer01_FrontAnnulus
SH3_Layer01_FrontAnnulus.Material Aluminium
SH3_Layer01_FrontAnnulus.Visibility 1
SH3_Layer01_FrontAnnulus.Shape TUBS 2.700000 4.200000 0.100000 0 360
SH3_Layer01_FrontAnnulus.Position -39.4 0 -2.8
SH3_Layer01_FrontAnnulus.Rotation 0 90 0
SH3_Layer01_FrontAnnulus.Mother InstrumentFrame
Volume SH3_Layer01_RearColdPortAnnulus
SH3_Layer01_RearColdPortAnnulus.Material Aluminium
SH3_Layer01_RearColdPortAnnulus.Visibility 1
SH3_Layer01_RearColdPortAnnulus.Shape TUBS 0.750000 4.200000 0.100000 0 360
SH3_Layer01_RearColdPortAnnulus.Position -31.3 0 -2.8
SH3_Layer01_RearColdPortAnnulus.Rotation 0 90 0
SH3_Layer01_RearColdPortAnnulus.Mother InstrumentFrame
Volume SH3_Layer01_OpticalWindow
SH3_Layer01_OpticalWindow.Material Aluminium
SH3_Layer01_OpticalWindow.Visibility 1
SH3_Layer01_OpticalWindow.Shape TUBS 0.000000 2.700000 0.001250 0 360
SH3_Layer01_OpticalWindow.Position -39.4 0 -2.8
SH3_Layer01_OpticalWindow.Rotation 0 90 0
SH3_Layer01_OpticalWindow.Mother InstrumentFrame

// local aluminium shell layer 02; thermal-stage ownership deliberately unset
Volume SH3_Layer02_SideShell
SH3_Layer02_SideShell.Material Aluminium
SH3_Layer02_SideShell.Visibility 1
SH3_Layer02_SideShell.Shape TUBS 4.450000 4.750000 4.350000 0 360
SH3_Layer02_SideShell.Position -35.3 0 -2.8
SH3_Layer02_SideShell.Rotation 0 90 0
SH3_Layer02_SideShell.Mother InstrumentFrame
Volume SH3_Layer02_FrontAnnulus
SH3_Layer02_FrontAnnulus.Material Aluminium
SH3_Layer02_FrontAnnulus.Visibility 1
SH3_Layer02_FrontAnnulus.Shape TUBS 2.700000 4.750000 0.150000 0 360
SH3_Layer02_FrontAnnulus.Position -39.8 0 -2.8
SH3_Layer02_FrontAnnulus.Rotation 0 90 0
SH3_Layer02_FrontAnnulus.Mother InstrumentFrame
Volume SH3_Layer02_RearColdPortAnnulus
SH3_Layer02_RearColdPortAnnulus.Material Aluminium
SH3_Layer02_RearColdPortAnnulus.Visibility 1
SH3_Layer02_RearColdPortAnnulus.Shape TUBS 0.750000 4.750000 0.150000 0 360
SH3_Layer02_RearColdPortAnnulus.Position -30.8 0 -2.8
SH3_Layer02_RearColdPortAnnulus.Rotation 0 90 0
SH3_Layer02_RearColdPortAnnulus.Mother InstrumentFrame
Volume SH3_Layer02_OpticalWindow
SH3_Layer02_OpticalWindow.Material Aluminium
SH3_Layer02_OpticalWindow.Visibility 1
SH3_Layer02_OpticalWindow.Shape TUBS 0.000000 2.700000 0.001250 0 360
SH3_Layer02_OpticalWindow.Position -39.8 0 -2.8
SH3_Layer02_OpticalWindow.Rotation 0 90 0
SH3_Layer02_OpticalWindow.Mother InstrumentFrame

// local aluminium shell layer 03; thermal-stage ownership deliberately unset
Volume SH3_Layer03_SideShell
SH3_Layer03_SideShell.Material Aluminium
SH3_Layer03_SideShell.Visibility 1
SH3_Layer03_SideShell.Shape TUBS 5.000000 5.300000 4.900000 0 360
SH3_Layer03_SideShell.Position -35.3 0 -2.8
SH3_Layer03_SideShell.Rotation 0 90 0
SH3_Layer03_SideShell.Mother InstrumentFrame
Volume SH3_Layer03_FrontAnnulus
SH3_Layer03_FrontAnnulus.Material Aluminium
SH3_Layer03_FrontAnnulus.Visibility 1
SH3_Layer03_FrontAnnulus.Shape TUBS 2.700000 5.300000 0.150000 0 360
SH3_Layer03_FrontAnnulus.Position -40.35 0 -2.8
SH3_Layer03_FrontAnnulus.Rotation 0 90 0
SH3_Layer03_FrontAnnulus.Mother InstrumentFrame
Volume SH3_Layer03_RearColdPortAnnulus
SH3_Layer03_RearColdPortAnnulus.Material Aluminium
SH3_Layer03_RearColdPortAnnulus.Visibility 1
SH3_Layer03_RearColdPortAnnulus.Shape TUBS 0.750000 5.300000 0.150000 0 360
SH3_Layer03_RearColdPortAnnulus.Position -30.25 0 -2.8
SH3_Layer03_RearColdPortAnnulus.Rotation 0 90 0
SH3_Layer03_RearColdPortAnnulus.Mother InstrumentFrame
Volume SH3_Layer03_OpticalWindow
SH3_Layer03_OpticalWindow.Material Aluminium
SH3_Layer03_OpticalWindow.Visibility 1
SH3_Layer03_OpticalWindow.Shape TUBS 0.000000 2.700000 0.001250 0 360
SH3_Layer03_OpticalWindow.Position -40.35 0 -2.8
SH3_Layer03_OpticalWindow.Rotation 0 90 0
SH3_Layer03_OpticalWindow.Mother InstrumentFrame

// local aluminium shell layer 04; thermal-stage ownership deliberately unset
Volume SH3_Layer04_SideShell
SH3_Layer04_SideShell.Material Aluminium
SH3_Layer04_SideShell.Visibility 1
SH3_Layer04_SideShell.Shape TUBS 5.550000 5.850000 5.450000 0 360
SH3_Layer04_SideShell.Position -35.3 0 -2.8
SH3_Layer04_SideShell.Rotation 0 90 0
SH3_Layer04_SideShell.Mother InstrumentFrame
Volume SH3_Layer04_FrontAnnulus
SH3_Layer04_FrontAnnulus.Material Aluminium
SH3_Layer04_FrontAnnulus.Visibility 1
SH3_Layer04_FrontAnnulus.Shape TUBS 2.700000 5.850000 0.150000 0 360
SH3_Layer04_FrontAnnulus.Position -40.9 0 -2.8
SH3_Layer04_FrontAnnulus.Rotation 0 90 0
SH3_Layer04_FrontAnnulus.Mother InstrumentFrame
Volume SH3_Layer04_RearColdPortAnnulus
SH3_Layer04_RearColdPortAnnulus.Material Aluminium
SH3_Layer04_RearColdPortAnnulus.Visibility 1
SH3_Layer04_RearColdPortAnnulus.Shape TUBS 0.750000 5.850000 0.150000 0 360
SH3_Layer04_RearColdPortAnnulus.Position -29.7 0 -2.8
SH3_Layer04_RearColdPortAnnulus.Rotation 0 90 0
SH3_Layer04_RearColdPortAnnulus.Mother InstrumentFrame
Volume SH3_Layer04_OpticalWindow
SH3_Layer04_OpticalWindow.Material Aluminium
SH3_Layer04_OpticalWindow.Visibility 1
SH3_Layer04_OpticalWindow.Shape TUBS 0.000000 2.700000 0.001250 0 360
SH3_Layer04_OpticalWindow.Position -40.9 0 -2.8
SH3_Layer04_OpticalWindow.Rotation 0 90 0
SH3_Layer04_OpticalWindow.Mother InstrumentFrame

// local outer mechanical jacket; thermal-stage ownership deliberately unset
Volume SH3_Layer05_SideShell
SH3_Layer05_SideShell.Material Aluminium
SH3_Layer05_SideShell.Visibility 1
SH3_Layer05_SideShell.Shape TUBS 6.100000 6.600000 5.900000 0 360
SH3_Layer05_SideShell.Position -35.2 0 -2.8
SH3_Layer05_SideShell.Rotation 0 90 0
SH3_Layer05_SideShell.Mother InstrumentFrame
Volume SH3_Layer05_FrontAnnulus
SH3_Layer05_FrontAnnulus.Material Aluminium
SH3_Layer05_FrontAnnulus.Visibility 1
SH3_Layer05_FrontAnnulus.Shape TUBS 2.700000 6.600000 0.250000 0 360
SH3_Layer05_FrontAnnulus.Position -41.35 0 -2.8
SH3_Layer05_FrontAnnulus.Rotation 0 90 0
SH3_Layer05_FrontAnnulus.Mother InstrumentFrame
Volume SH3_Layer05_RearColdPortAnnulus
SH3_Layer05_RearColdPortAnnulus.Material Aluminium
SH3_Layer05_RearColdPortAnnulus.Visibility 1
SH3_Layer05_RearColdPortAnnulus.Shape TUBS 0.750000 6.600000 0.250000 0 360
SH3_Layer05_RearColdPortAnnulus.Position -29.05 0 -2.8
SH3_Layer05_RearColdPortAnnulus.Rotation 0 90 0
SH3_Layer05_RearColdPortAnnulus.Mother InstrumentFrame
Volume SH3_Layer05_OpticalWindow
SH3_Layer05_OpticalWindow.Material Be
SH3_Layer05_OpticalWindow.Visibility 1
SH3_Layer05_OpticalWindow.Shape TUBS 0.000000 2.700000 0.007500 0 360
SH3_Layer05_OpticalWindow.Position -41.35 0 -2.8
SH3_Layer05_OpticalWindow.Rotation 0 90 0
SH3_Layer05_OpticalWindow.Mother InstrumentFrame

// Outer IR/optical filter immediately ahead of the structural Be window.
Volume SH3_Outer_Al_OpticalFilter
SH3_Outer_Al_OpticalFilter.Material Aluminium
SH3_Outer_Al_OpticalFilter.Visibility 1
SH3_Outer_Al_OpticalFilter.Shape TUBS 0.000000 2.700000 0.001500 0 360
SH3_Outer_Al_OpticalFilter.Position -42.15 0 -2.8
SH3_Outer_Al_OpticalFilter.Rotation 0 90 0
SH3_Outer_Al_OpticalFilter.Mother InstrumentFrame
// END SH3_NESTED_CHIMNEY_SHELLS

// BEGIN SH3_ACTIVE_BGO40_AND_MECHANICAL_AL3
// 40 mm is the retained SG3 side-shield baseline; no >40 mm benefit is asserted.
Volume SH3_BGO40_SideShield
SH3_BGO40_SideShield.Material BGO
SH3_BGO40_SideShield.Visibility 1
SH3_BGO40_SideShield.Shape TUBS 6.700000 10.700000 6.500000 0 360
SH3_BGO40_SideShield.Position -35.2 0 -2.8
SH3_BGO40_SideShield.Rotation 0 90 0
SH3_BGO40_SideShield.Mother InstrumentFrame
// OptV2: square BGO-front recess for a simple W frame.
Shape TUBS SH3_OptV2_BGOFront_FullCylinderShape
SH3_OptV2_BGOFront_FullCylinderShape.Parameters 0 10.700000 2.000000 0 360
Shape BRIK SH3_OptV2_BGOFront_SquareRecessCutShape
SH3_OptV2_BGOFront_SquareRecessCutShape.Parameters 3.000000 3.000000 2.100000
Orientation SH3_OptV2_BGOFront_SquareRecessCutOrientation
SH3_OptV2_BGOFront_SquareRecessCutOrientation.Position 0 0 0
Shape Subtraction SH3_OptV2_BGOFront_SquareRecessShape
SH3_OptV2_BGOFront_SquareRecessShape.Parameters SH3_OptV2_BGOFront_FullCylinderShape SH3_OptV2_BGOFront_SquareRecessCutShape SH3_OptV2_BGOFront_SquareRecessCutOrientation

Volume SH3_BGO40_FrontOpticalAnnulus
SH3_BGO40_FrontOpticalAnnulus.Material BGO
SH3_BGO40_FrontOpticalAnnulus.Visibility 1
SH3_BGO40_FrontOpticalAnnulus.Shape SH3_OptV2_BGOFront_SquareRecessShape
SH3_BGO40_FrontOpticalAnnulus.Position -43.7 0 -2.8
SH3_BGO40_FrontOpticalAnnulus.Rotation 0 90 0
SH3_BGO40_FrontOpticalAnnulus.Mother InstrumentFrame
Volume SH3_BGO40_RearColdPortAnnulus
SH3_BGO40_RearColdPortAnnulus.Material BGO
SH3_BGO40_RearColdPortAnnulus.Visibility 1
SH3_BGO40_RearColdPortAnnulus.Shape TUBS 0.750000 10.700000 2.000000 0 360
SH3_BGO40_RearColdPortAnnulus.Position -26.7 0 -2.8
SH3_BGO40_RearColdPortAnnulus.Rotation 0 90 0
SH3_BGO40_RearColdPortAnnulus.Mother InstrumentFrame
Volume SH3_BGO_MechanicalAl_FrontOpticalAnnulus_3mm
SH3_BGO_MechanicalAl_FrontOpticalAnnulus_3mm.Material Aluminium
SH3_BGO_MechanicalAl_FrontOpticalAnnulus_3mm.Visibility 1
SH3_BGO_MechanicalAl_FrontOpticalAnnulus_3mm.Shape TUBS 2.700000 11.050000 0.150000 0 360
SH3_BGO_MechanicalAl_FrontOpticalAnnulus_3mm.Position -45.9 0 -2.8
SH3_BGO_MechanicalAl_FrontOpticalAnnulus_3mm.Rotation 0 90 0
SH3_BGO_MechanicalAl_FrontOpticalAnnulus_3mm.Mother InstrumentFrame
// Deliberately no mechanical-Al rear end cap on the cold-finger face.
// END SH3_ACTIVE_BGO40_AND_MECHANICAL_AL3
// END FLATTENED_SH3_CHIMNEY_OPT_V3

// BEGIN SH3_OPTV2_SIMPLE_W_SQUARE_FRAME
// Four passive W bars only; no multihole/grid collimator. Inner square contains the r=2.70 cm optical circle.
Volume SH3_OptV2_W_Frame_Top
SH3_OptV2_W_Frame_Top.Material W
SH3_OptV2_W_Frame_Top.Visibility 1
SH3_OptV2_W_Frame_Top.Shape BRIK 1.000000 3.000000 0.150000
SH3_OptV2_W_Frame_Top.Position -44.700000 0.000000 0.050000
SH3_OptV2_W_Frame_Top.Mother InstrumentFrame
Volume SH3_OptV2_W_Frame_Bottom
SH3_OptV2_W_Frame_Bottom.Material W
SH3_OptV2_W_Frame_Bottom.Visibility 1
SH3_OptV2_W_Frame_Bottom.Shape BRIK 1.000000 3.000000 0.150000
SH3_OptV2_W_Frame_Bottom.Position -44.700000 0.000000 -5.650000
SH3_OptV2_W_Frame_Bottom.Mother InstrumentFrame
Volume SH3_OptV2_W_Frame_PosY
SH3_OptV2_W_Frame_PosY.Material W
SH3_OptV2_W_Frame_PosY.Visibility 1
SH3_OptV2_W_Frame_PosY.Shape BRIK 1.000000 0.150000 2.700000
SH3_OptV2_W_Frame_PosY.Position -44.700000 2.850000 -2.800000
SH3_OptV2_W_Frame_PosY.Mother InstrumentFrame
Volume SH3_OptV2_W_Frame_NegY
SH3_OptV2_W_Frame_NegY.Material W
SH3_OptV2_W_Frame_NegY.Visibility 1
SH3_OptV2_W_Frame_NegY.Shape BRIK 1.000000 0.150000 2.700000
SH3_OptV2_W_Frame_NegY.Position -44.700000 -2.850000 -2.800000
SH3_OptV2_W_Frame_NegY.Mother InstrumentFrame
// END SH3_OPTV2_SIMPLE_W_SQUARE_FRAME
// BEGIN SH3_OPTV2_BENT_COLD_FINGER_TO_MXC
Volume SH3_OptV2_Cu_ColdFinger_PortRun
SH3_OptV2_Cu_ColdFinger_PortRun.Material Copper
SH3_OptV2_Cu_ColdFinger_PortRun.Visibility 1
SH3_OptV2_Cu_ColdFinger_PortRun.Shape BRIK 6.945000 0.160000 0.160000
SH3_OptV2_Cu_ColdFinger_PortRun.Position -21.805000 0.000000 -2.800000
SH3_OptV2_Cu_ColdFinger_PortRun.Mother InstrumentFrame
Volume SH3_OptV2_Cu_ColdFinger_InsideMXC_Dogleg
SH3_OptV2_Cu_ColdFinger_InsideMXC_Dogleg.Material Copper
SH3_OptV2_Cu_ColdFinger_InsideMXC_Dogleg.Visibility 1
SH3_OptV2_Cu_ColdFinger_InsideMXC_Dogleg.Shape BRIK 0.160000 0.550000 0.160000
SH3_OptV2_Cu_ColdFinger_InsideMXC_Dogleg.Position -14.700000 0.550000 -2.800000
SH3_OptV2_Cu_ColdFinger_InsideMXC_Dogleg.Mother InstrumentFrame
Volume SH3_OptV2_Cu_ColdFinger_InternalRun
SH3_OptV2_Cu_ColdFinger_InternalRun.Material Copper
SH3_OptV2_Cu_ColdFinger_InternalRun.Visibility 1
SH3_OptV2_Cu_ColdFinger_InternalRun.Shape BRIK 10.215000 0.160000 0.160000
SH3_OptV2_Cu_ColdFinger_InternalRun.Position -4.325000 1.100000 -2.800000
SH3_OptV2_Cu_ColdFinger_InternalRun.Mother InstrumentFrame
Volume SH3_OptV2_Cu_ColdFinger_MXCStem
SH3_OptV2_Cu_ColdFinger_MXCStem.Material Copper
SH3_OptV2_Cu_ColdFinger_MXCStem.Visibility 1
SH3_OptV2_Cu_ColdFinger_MXCStem.Shape BRIK 0.160000 0.160000 1.045000
SH3_OptV2_Cu_ColdFinger_MXCStem.Position 6.050000 1.100000 -1.595000
SH3_OptV2_Cu_ColdFinger_MXCStem.Mother InstrumentFrame
Volume SH3_OptV2_Cu_MXC_ContactPad
SH3_OptV2_Cu_MXC_ContactPad.Material Copper
SH3_OptV2_Cu_MXC_ContactPad.Visibility 1
SH3_OptV2_Cu_MXC_ContactPad.Shape PCON 0 360 2 -0.175000 0 0.350000 0.175000 0 0.350000
SH3_OptV2_Cu_MXC_ContactPad.Position 6.050000 1.100000 -0.375000
SH3_OptV2_Cu_MXC_ContactPad.Mother InstrumentFrame
// Pad upper face touches the retained MXC copper plate underside at z'=-0.20 cm.
// END SH3_OPTV2_BENT_COLD_FINGER_TO_MXC
// END SH3_ASSEMBLY_OPT_V3

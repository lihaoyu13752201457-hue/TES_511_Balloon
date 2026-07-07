// f10m multiband UNIFIED: six-ring optical TILES + support, ONE frame.
// Optical axis = +x, lens plane at x=0 (project OF convention).
// SINGLE shared Ge tile template (all tiles identical) -> one MC detector.

Volume MB_Tile
MB_Tile.Material GeProxy
MB_Tile.Visibility 1
MB_Tile.Shape BRIK 0.510940 0.110000 0.110000

// ring 0: E=451.0 keV, r=8.416019 cm, 229 tiles
MB_Tile.Copy MB_Tile_r0_000
MB_Tile_r0_000.Position 0.000000 8.416019 0.000000
MB_Tile_r0_000.Rotation 0.000000 0 0
MB_Tile_r0_000.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_001
MB_Tile_r0_001.Position 0.000000 8.412851 0.230885
MB_Tile_r0_001.Rotation 1.572052 0 0
MB_Tile_r0_001.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_002
MB_Tile_r0_002.Position 0.000000 8.403350 0.461597
MB_Tile_r0_002.Rotation 3.144105 0 0
MB_Tile_r0_002.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_003
MB_Tile_r0_003.Position 0.000000 8.387524 0.691961
MB_Tile_r0_003.Rotation 4.716157 0 0
MB_Tile_r0_003.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_004
MB_Tile_r0_004.Position 0.000000 8.365384 0.921805
MB_Tile_r0_004.Rotation 6.288210 0 0
MB_Tile_r0_004.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_005
MB_Tile_r0_005.Position 0.000000 8.336946 1.150954
MB_Tile_r0_005.Rotation 7.860262 0 0
MB_Tile_r0_005.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_006
MB_Tile_r0_006.Position 0.000000 8.302233 1.379237
MB_Tile_r0_006.Rotation 9.432314 0 0
MB_Tile_r0_006.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_007
MB_Tile_r0_007.Position 0.000000 8.261270 1.606482
MB_Tile_r0_007.Rotation 11.004367 0 0
MB_Tile_r0_007.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_008
MB_Tile_r0_008.Position 0.000000 8.214089 1.832517
MB_Tile_r0_008.Rotation 12.576419 0 0
MB_Tile_r0_008.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_009
MB_Tile_r0_009.Position 0.000000 8.160724 2.057173
MB_Tile_r0_009.Rotation 14.148472 0 0
MB_Tile_r0_009.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_010
MB_Tile_r0_010.Position 0.000000 8.101215 2.280281
MB_Tile_r0_010.Rotation 15.720524 0 0
MB_Tile_r0_010.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_011
MB_Tile_r0_011.Position 0.000000 8.035609 2.501671
MB_Tile_r0_011.Rotation 17.292576 0 0
MB_Tile_r0_011.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_012
MB_Tile_r0_012.Position 0.000000 7.963953 2.721179
MB_Tile_r0_012.Rotation 18.864629 0 0
MB_Tile_r0_012.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_013
MB_Tile_r0_013.Position 0.000000 7.886303 2.938638
MB_Tile_r0_013.Rotation 20.436681 0 0
MB_Tile_r0_013.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_014
MB_Tile_r0_014.Position 0.000000 7.802716 3.153886
MB_Tile_r0_014.Rotation 22.008734 0 0
MB_Tile_r0_014.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_015
MB_Tile_r0_015.Position 0.000000 7.713255 3.366759
MB_Tile_r0_015.Rotation 23.580786 0 0
MB_Tile_r0_015.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_016
MB_Tile_r0_016.Position 0.000000 7.617988 3.577097
MB_Tile_r0_016.Rotation 25.152838 0 0
MB_Tile_r0_016.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_017
MB_Tile_r0_017.Position 0.000000 7.516987 3.784743
MB_Tile_r0_017.Rotation 26.724891 0 0
MB_Tile_r0_017.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_018
MB_Tile_r0_018.Position 0.000000 7.410327 3.989540
MB_Tile_r0_018.Rotation 28.296943 0 0
MB_Tile_r0_018.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_019
MB_Tile_r0_019.Position 0.000000 7.298088 4.191334
MB_Tile_r0_019.Rotation 29.868996 0 0
MB_Tile_r0_019.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_020
MB_Tile_r0_020.Position 0.000000 7.180356 4.389972
MB_Tile_r0_020.Rotation 31.441048 0 0
MB_Tile_r0_020.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_021
MB_Tile_r0_021.Position 0.000000 7.057219 4.585306
MB_Tile_r0_021.Rotation 33.013100 0 0
MB_Tile_r0_021.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_022
MB_Tile_r0_022.Position 0.000000 6.928769 4.777188
MB_Tile_r0_022.Rotation 34.585153 0 0
MB_Tile_r0_022.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_023
MB_Tile_r0_023.Position 0.000000 6.795104 4.965474
MB_Tile_r0_023.Rotation 36.157205 0 0
MB_Tile_r0_023.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_024
MB_Tile_r0_024.Position 0.000000 6.656323 5.150023
MB_Tile_r0_024.Rotation 37.729258 0 0
MB_Tile_r0_024.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_025
MB_Tile_r0_025.Position 0.000000 6.512532 5.330694
MB_Tile_r0_025.Rotation 39.301310 0 0
MB_Tile_r0_025.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_026
MB_Tile_r0_026.Position 0.000000 6.363838 5.507353
MB_Tile_r0_026.Rotation 40.873362 0 0
MB_Tile_r0_026.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_027
MB_Tile_r0_027.Position 0.000000 6.210354 5.679866
MB_Tile_r0_027.Rotation 42.445415 0 0
MB_Tile_r0_027.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_028
MB_Tile_r0_028.Position 0.000000 6.052195 5.848103
MB_Tile_r0_028.Rotation 44.017467 0 0
MB_Tile_r0_028.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_029
MB_Tile_r0_029.Position 0.000000 5.889480 6.011938
MB_Tile_r0_029.Rotation 45.589520 0 0
MB_Tile_r0_029.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_030
MB_Tile_r0_030.Position 0.000000 5.722331 6.171248
MB_Tile_r0_030.Rotation 47.161572 0 0
MB_Tile_r0_030.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_031
MB_Tile_r0_031.Position 0.000000 5.550875 6.325912
MB_Tile_r0_031.Rotation 48.733624 0 0
MB_Tile_r0_031.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_032
MB_Tile_r0_032.Position 0.000000 5.375240 6.475814
MB_Tile_r0_032.Rotation 50.305677 0 0
MB_Tile_r0_032.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_033
MB_Tile_r0_033.Position 0.000000 5.195559 6.620841
MB_Tile_r0_033.Rotation 51.877729 0 0
MB_Tile_r0_033.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_034
MB_Tile_r0_034.Position 0.000000 5.011967 6.760884
MB_Tile_r0_034.Rotation 53.449782 0 0
MB_Tile_r0_034.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_035
MB_Tile_r0_035.Position 0.000000 4.824603 6.895838
MB_Tile_r0_035.Rotation 55.021834 0 0
MB_Tile_r0_035.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_036
MB_Tile_r0_036.Position 0.000000 4.633606 7.025601
MB_Tile_r0_036.Rotation 56.593886 0 0
MB_Tile_r0_036.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_037
MB_Tile_r0_037.Position 0.000000 4.439121 7.150075
MB_Tile_r0_037.Rotation 58.165939 0 0
MB_Tile_r0_037.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_038
MB_Tile_r0_038.Position 0.000000 4.241295 7.269167
MB_Tile_r0_038.Rotation 59.737991 0 0
MB_Tile_r0_038.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_039
MB_Tile_r0_039.Position 0.000000 4.040276 7.382787
MB_Tile_r0_039.Rotation 61.310044 0 0
MB_Tile_r0_039.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_040
MB_Tile_r0_040.Position 0.000000 3.836215 7.490849
MB_Tile_r0_040.Rotation 62.882096 0 0
MB_Tile_r0_040.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_041
MB_Tile_r0_041.Position 0.000000 3.629267 7.593273
MB_Tile_r0_041.Rotation 64.454148 0 0
MB_Tile_r0_041.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_042
MB_Tile_r0_042.Position 0.000000 3.419587 7.689980
MB_Tile_r0_042.Rotation 66.026201 0 0
MB_Tile_r0_042.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_043
MB_Tile_r0_043.Position 0.000000 3.207333 7.780899
MB_Tile_r0_043.Rotation 67.598253 0 0
MB_Tile_r0_043.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_044
MB_Tile_r0_044.Position 0.000000 2.992664 7.865960
MB_Tile_r0_044.Rotation 69.170306 0 0
MB_Tile_r0_044.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_045
MB_Tile_r0_045.Position 0.000000 2.775742 7.945101
MB_Tile_r0_045.Rotation 70.742358 0 0
MB_Tile_r0_045.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_046
MB_Tile_r0_046.Position 0.000000 2.556731 8.018260
MB_Tile_r0_046.Rotation 72.314410 0 0
MB_Tile_r0_046.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_047
MB_Tile_r0_047.Position 0.000000 2.335796 8.085384
MB_Tile_r0_047.Rotation 73.886463 0 0
MB_Tile_r0_047.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_048
MB_Tile_r0_048.Position 0.000000 2.113102 8.146421
MB_Tile_r0_048.Rotation 75.458515 0 0
MB_Tile_r0_048.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_049
MB_Tile_r0_049.Position 0.000000 1.888817 8.201326
MB_Tile_r0_049.Rotation 77.030568 0 0
MB_Tile_r0_049.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_050
MB_Tile_r0_050.Position 0.000000 1.663111 8.250057
MB_Tile_r0_050.Rotation 78.602620 0 0
MB_Tile_r0_050.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_051
MB_Tile_r0_051.Position 0.000000 1.436152 8.292577
MB_Tile_r0_051.Rotation 80.174672 0 0
MB_Tile_r0_051.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_052
MB_Tile_r0_052.Position 0.000000 1.208113 8.328856
MB_Tile_r0_052.Rotation 81.746725 0 0
MB_Tile_r0_052.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_053
MB_Tile_r0_053.Position 0.000000 0.979164 8.358864
MB_Tile_r0_053.Rotation 83.318777 0 0
MB_Tile_r0_053.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_054
MB_Tile_r0_054.Position 0.000000 0.749478 8.382580
MB_Tile_r0_054.Rotation 84.890830 0 0
MB_Tile_r0_054.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_055
MB_Tile_r0_055.Position 0.000000 0.519228 8.399987
MB_Tile_r0_055.Rotation 86.462882 0 0
MB_Tile_r0_055.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_056
MB_Tile_r0_056.Position 0.000000 0.288586 8.411069
MB_Tile_r0_056.Rotation 88.034934 0 0
MB_Tile_r0_056.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_057
MB_Tile_r0_057.Position 0.000000 0.057728 8.415821
MB_Tile_r0_057.Rotation 89.606987 0 0
MB_Tile_r0_057.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_058
MB_Tile_r0_058.Position 0.000000 -0.173174 8.414237
MB_Tile_r0_058.Rotation 91.179039 0 0
MB_Tile_r0_058.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_059
MB_Tile_r0_059.Position 0.000000 -0.403945 8.406319
MB_Tile_r0_059.Rotation 92.751092 0 0
MB_Tile_r0_059.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_060
MB_Tile_r0_060.Position 0.000000 -0.634412 8.392073
MB_Tile_r0_060.Rotation 94.323144 0 0
MB_Tile_r0_060.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_061
MB_Tile_r0_061.Position 0.000000 -0.864402 8.371510
MB_Tile_r0_061.Rotation 95.895197 0 0
MB_Tile_r0_061.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_062
MB_Tile_r0_062.Position 0.000000 -1.093741 8.344645
MB_Tile_r0_062.Rotation 97.467249 0 0
MB_Tile_r0_062.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_063
MB_Tile_r0_063.Position 0.000000 -1.322257 8.311499
MB_Tile_r0_063.Rotation 99.039301 0 0
MB_Tile_r0_063.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_064
MB_Tile_r0_064.Position 0.000000 -1.549777 8.272095
MB_Tile_r0_064.Rotation 100.611354 0 0
MB_Tile_r0_064.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_065
MB_Tile_r0_065.Position 0.000000 -1.776131 8.226465
MB_Tile_r0_065.Rotation 102.183406 0 0
MB_Tile_r0_065.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_066
MB_Tile_r0_066.Position 0.000000 -2.001148 8.174642
MB_Tile_r0_066.Rotation 103.755459 0 0
MB_Tile_r0_066.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_067
MB_Tile_r0_067.Position 0.000000 -2.224658 8.116666
MB_Tile_r0_067.Rotation 105.327511 0 0
MB_Tile_r0_067.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_068
MB_Tile_r0_068.Position 0.000000 -2.446494 8.052580
MB_Tile_r0_068.Rotation 106.899563 0 0
MB_Tile_r0_068.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_069
MB_Tile_r0_069.Position 0.000000 -2.666488 7.982432
MB_Tile_r0_069.Rotation 108.471616 0 0
MB_Tile_r0_069.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_070
MB_Tile_r0_070.Position 0.000000 -2.884475 7.906275
MB_Tile_r0_070.Rotation 110.043668 0 0
MB_Tile_r0_070.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_071
MB_Tile_r0_071.Position 0.000000 -3.100290 7.824166
MB_Tile_r0_071.Rotation 111.615721 0 0
MB_Tile_r0_071.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_072
MB_Tile_r0_072.Position 0.000000 -3.313772 7.736168
MB_Tile_r0_072.Rotation 113.187773 0 0
MB_Tile_r0_072.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_073
MB_Tile_r0_073.Position 0.000000 -3.524759 7.642346
MB_Tile_r0_073.Rotation 114.759825 0 0
MB_Tile_r0_073.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_074
MB_Tile_r0_074.Position 0.000000 -3.733093 7.542771
MB_Tile_r0_074.Rotation 116.331878 0 0
MB_Tile_r0_074.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_075
MB_Tile_r0_075.Position 0.000000 -3.938616 7.437518
MB_Tile_r0_075.Rotation 117.903930 0 0
MB_Tile_r0_075.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_076
MB_Tile_r0_076.Position 0.000000 -4.141175 7.326666
MB_Tile_r0_076.Rotation 119.475983 0 0
MB_Tile_r0_076.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_077
MB_Tile_r0_077.Position 0.000000 -4.340616 7.210300
MB_Tile_r0_077.Rotation 121.048035 0 0
MB_Tile_r0_077.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_078
MB_Tile_r0_078.Position 0.000000 -4.536790 7.088505
MB_Tile_r0_078.Rotation 122.620087 0 0
MB_Tile_r0_078.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_079
MB_Tile_r0_079.Position 0.000000 -4.729549 6.961374
MB_Tile_r0_079.Rotation 124.192140 0 0
MB_Tile_r0_079.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_080
MB_Tile_r0_080.Position 0.000000 -4.918748 6.829004
MB_Tile_r0_080.Rotation 125.764192 0 0
MB_Tile_r0_080.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_081
MB_Tile_r0_081.Position 0.000000 -5.104244 6.691492
MB_Tile_r0_081.Rotation 127.336245 0 0
MB_Tile_r0_081.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_082
MB_Tile_r0_082.Position 0.000000 -5.285897 6.548944
MB_Tile_r0_082.Rotation 128.908297 0 0
MB_Tile_r0_082.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_083
MB_Tile_r0_083.Position 0.000000 -5.463572 6.401465
MB_Tile_r0_083.Rotation 130.480349 0 0
MB_Tile_r0_083.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_084
MB_Tile_r0_084.Position 0.000000 -5.637133 6.249168
MB_Tile_r0_084.Rotation 132.052402 0 0
MB_Tile_r0_084.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_085
MB_Tile_r0_085.Position 0.000000 -5.806452 6.092166
MB_Tile_r0_085.Rotation 133.624454 0 0
MB_Tile_r0_085.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_086
MB_Tile_r0_086.Position 0.000000 -5.971399 5.930579
MB_Tile_r0_086.Rotation 135.196507 0 0
MB_Tile_r0_086.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_087
MB_Tile_r0_087.Position 0.000000 -6.131851 5.764527
MB_Tile_r0_087.Rotation 136.768559 0 0
MB_Tile_r0_087.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_088
MB_Tile_r0_088.Position 0.000000 -6.287688 5.594136
MB_Tile_r0_088.Rotation 138.340611 0 0
MB_Tile_r0_088.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_089
MB_Tile_r0_089.Position 0.000000 -6.438791 5.419534
MB_Tile_r0_089.Rotation 139.912664 0 0
MB_Tile_r0_089.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_090
MB_Tile_r0_090.Position 0.000000 -6.585047 5.240852
MB_Tile_r0_090.Rotation 141.484716 0 0
MB_Tile_r0_090.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_091
MB_Tile_r0_091.Position 0.000000 -6.726346 5.058225
MB_Tile_r0_091.Rotation 143.056769 0 0
MB_Tile_r0_091.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_092
MB_Tile_r0_092.Position 0.000000 -6.862582 4.871790
MB_Tile_r0_092.Rotation 144.628821 0 0
MB_Tile_r0_092.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_093
MB_Tile_r0_093.Position 0.000000 -6.993652 4.681688
MB_Tile_r0_093.Rotation 146.200873 0 0
MB_Tile_r0_093.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_094
MB_Tile_r0_094.Position 0.000000 -7.119458 4.488061
MB_Tile_r0_094.Rotation 147.772926 0 0
MB_Tile_r0_094.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_095
MB_Tile_r0_095.Position 0.000000 -7.239904 4.291057
MB_Tile_r0_095.Rotation 149.344978 0 0
MB_Tile_r0_095.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_096
MB_Tile_r0_096.Position 0.000000 -7.354900 4.090822
MB_Tile_r0_096.Rotation 150.917031 0 0
MB_Tile_r0_096.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_097
MB_Tile_r0_097.Position 0.000000 -7.464359 3.887507
MB_Tile_r0_097.Rotation 152.489083 0 0
MB_Tile_r0_097.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_098
MB_Tile_r0_098.Position 0.000000 -7.568200 3.681266
MB_Tile_r0_098.Rotation 154.061135 0 0
MB_Tile_r0_098.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_099
MB_Tile_r0_099.Position 0.000000 -7.666343 3.472255
MB_Tile_r0_099.Rotation 155.633188 0 0
MB_Tile_r0_099.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_100
MB_Tile_r0_100.Position 0.000000 -7.758716 3.260629
MB_Tile_r0_100.Rotation 157.205240 0 0
MB_Tile_r0_100.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_101
MB_Tile_r0_101.Position 0.000000 -7.845248 3.046549
MB_Tile_r0_101.Rotation 158.777293 0 0
MB_Tile_r0_101.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_102
MB_Tile_r0_102.Position 0.000000 -7.925874 2.830175
MB_Tile_r0_102.Rotation 160.349345 0 0
MB_Tile_r0_102.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_103
MB_Tile_r0_103.Position 0.000000 -8.000534 2.611671
MB_Tile_r0_103.Rotation 161.921397 0 0
MB_Tile_r0_103.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_104
MB_Tile_r0_104.Position 0.000000 -8.069172 2.391201
MB_Tile_r0_104.Rotation 163.493450 0 0
MB_Tile_r0_104.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_105
MB_Tile_r0_105.Position 0.000000 -8.131735 2.168931
MB_Tile_r0_105.Rotation 165.065502 0 0
MB_Tile_r0_105.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_106
MB_Tile_r0_106.Position 0.000000 -8.188177 1.945028
MB_Tile_r0_106.Rotation 166.637555 0 0
MB_Tile_r0_106.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_107
MB_Tile_r0_107.Position 0.000000 -8.238455 1.719661
MB_Tile_r0_107.Rotation 168.209607 0 0
MB_Tile_r0_107.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_108
MB_Tile_r0_108.Position 0.000000 -8.282531 1.493000
MB_Tile_r0_108.Rotation 169.781659 0 0
MB_Tile_r0_108.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_109
MB_Tile_r0_109.Position 0.000000 -8.320373 1.265215
MB_Tile_r0_109.Rotation 171.353712 0 0
MB_Tile_r0_109.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_110
MB_Tile_r0_110.Position 0.000000 -8.351951 1.036477
MB_Tile_r0_110.Rotation 172.925764 0 0
MB_Tile_r0_110.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_111
MB_Tile_r0_111.Position 0.000000 -8.377242 0.806959
MB_Tile_r0_111.Rotation 174.497817 0 0
MB_Tile_r0_111.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_112
MB_Tile_r0_112.Position 0.000000 -8.396227 0.576833
MB_Tile_r0_112.Rotation 176.069869 0 0
MB_Tile_r0_112.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_113
MB_Tile_r0_113.Position 0.000000 -8.408892 0.346274
MB_Tile_r0_113.Rotation 177.641921 0 0
MB_Tile_r0_113.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_114
MB_Tile_r0_114.Position 0.000000 -8.415227 0.115454
MB_Tile_r0_114.Rotation 179.213974 0 0
MB_Tile_r0_114.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_115
MB_Tile_r0_115.Position 0.000000 -8.415227 -0.115454
MB_Tile_r0_115.Rotation 180.786026 0 0
MB_Tile_r0_115.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_116
MB_Tile_r0_116.Position 0.000000 -8.408892 -0.346274
MB_Tile_r0_116.Rotation 182.358079 0 0
MB_Tile_r0_116.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_117
MB_Tile_r0_117.Position 0.000000 -8.396227 -0.576833
MB_Tile_r0_117.Rotation 183.930131 0 0
MB_Tile_r0_117.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_118
MB_Tile_r0_118.Position 0.000000 -8.377242 -0.806959
MB_Tile_r0_118.Rotation 185.502183 0 0
MB_Tile_r0_118.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_119
MB_Tile_r0_119.Position 0.000000 -8.351951 -1.036477
MB_Tile_r0_119.Rotation 187.074236 0 0
MB_Tile_r0_119.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_120
MB_Tile_r0_120.Position 0.000000 -8.320373 -1.265215
MB_Tile_r0_120.Rotation 188.646288 0 0
MB_Tile_r0_120.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_121
MB_Tile_r0_121.Position 0.000000 -8.282531 -1.493000
MB_Tile_r0_121.Rotation 190.218341 0 0
MB_Tile_r0_121.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_122
MB_Tile_r0_122.Position 0.000000 -8.238455 -1.719661
MB_Tile_r0_122.Rotation 191.790393 0 0
MB_Tile_r0_122.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_123
MB_Tile_r0_123.Position 0.000000 -8.188177 -1.945028
MB_Tile_r0_123.Rotation 193.362445 0 0
MB_Tile_r0_123.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_124
MB_Tile_r0_124.Position 0.000000 -8.131735 -2.168931
MB_Tile_r0_124.Rotation 194.934498 0 0
MB_Tile_r0_124.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_125
MB_Tile_r0_125.Position 0.000000 -8.069172 -2.391201
MB_Tile_r0_125.Rotation 196.506550 0 0
MB_Tile_r0_125.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_126
MB_Tile_r0_126.Position 0.000000 -8.000534 -2.611671
MB_Tile_r0_126.Rotation 198.078603 0 0
MB_Tile_r0_126.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_127
MB_Tile_r0_127.Position 0.000000 -7.925874 -2.830175
MB_Tile_r0_127.Rotation 199.650655 0 0
MB_Tile_r0_127.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_128
MB_Tile_r0_128.Position 0.000000 -7.845248 -3.046549
MB_Tile_r0_128.Rotation 201.222707 0 0
MB_Tile_r0_128.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_129
MB_Tile_r0_129.Position 0.000000 -7.758716 -3.260629
MB_Tile_r0_129.Rotation 202.794760 0 0
MB_Tile_r0_129.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_130
MB_Tile_r0_130.Position 0.000000 -7.666343 -3.472255
MB_Tile_r0_130.Rotation 204.366812 0 0
MB_Tile_r0_130.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_131
MB_Tile_r0_131.Position 0.000000 -7.568200 -3.681266
MB_Tile_r0_131.Rotation 205.938865 0 0
MB_Tile_r0_131.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_132
MB_Tile_r0_132.Position 0.000000 -7.464359 -3.887507
MB_Tile_r0_132.Rotation 207.510917 0 0
MB_Tile_r0_132.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_133
MB_Tile_r0_133.Position 0.000000 -7.354900 -4.090822
MB_Tile_r0_133.Rotation 209.082969 0 0
MB_Tile_r0_133.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_134
MB_Tile_r0_134.Position 0.000000 -7.239904 -4.291057
MB_Tile_r0_134.Rotation 210.655022 0 0
MB_Tile_r0_134.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_135
MB_Tile_r0_135.Position 0.000000 -7.119458 -4.488061
MB_Tile_r0_135.Rotation 212.227074 0 0
MB_Tile_r0_135.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_136
MB_Tile_r0_136.Position 0.000000 -6.993652 -4.681688
MB_Tile_r0_136.Rotation 213.799127 0 0
MB_Tile_r0_136.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_137
MB_Tile_r0_137.Position 0.000000 -6.862582 -4.871790
MB_Tile_r0_137.Rotation 215.371179 0 0
MB_Tile_r0_137.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_138
MB_Tile_r0_138.Position 0.000000 -6.726346 -5.058225
MB_Tile_r0_138.Rotation 216.943231 0 0
MB_Tile_r0_138.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_139
MB_Tile_r0_139.Position 0.000000 -6.585047 -5.240852
MB_Tile_r0_139.Rotation 218.515284 0 0
MB_Tile_r0_139.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_140
MB_Tile_r0_140.Position 0.000000 -6.438791 -5.419534
MB_Tile_r0_140.Rotation 220.087336 0 0
MB_Tile_r0_140.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_141
MB_Tile_r0_141.Position 0.000000 -6.287688 -5.594136
MB_Tile_r0_141.Rotation 221.659389 0 0
MB_Tile_r0_141.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_142
MB_Tile_r0_142.Position 0.000000 -6.131851 -5.764527
MB_Tile_r0_142.Rotation 223.231441 0 0
MB_Tile_r0_142.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_143
MB_Tile_r0_143.Position 0.000000 -5.971399 -5.930579
MB_Tile_r0_143.Rotation 224.803493 0 0
MB_Tile_r0_143.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_144
MB_Tile_r0_144.Position 0.000000 -5.806452 -6.092166
MB_Tile_r0_144.Rotation 226.375546 0 0
MB_Tile_r0_144.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_145
MB_Tile_r0_145.Position 0.000000 -5.637133 -6.249168
MB_Tile_r0_145.Rotation 227.947598 0 0
MB_Tile_r0_145.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_146
MB_Tile_r0_146.Position 0.000000 -5.463572 -6.401465
MB_Tile_r0_146.Rotation 229.519651 0 0
MB_Tile_r0_146.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_147
MB_Tile_r0_147.Position 0.000000 -5.285897 -6.548944
MB_Tile_r0_147.Rotation 231.091703 0 0
MB_Tile_r0_147.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_148
MB_Tile_r0_148.Position 0.000000 -5.104244 -6.691492
MB_Tile_r0_148.Rotation 232.663755 0 0
MB_Tile_r0_148.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_149
MB_Tile_r0_149.Position 0.000000 -4.918748 -6.829004
MB_Tile_r0_149.Rotation 234.235808 0 0
MB_Tile_r0_149.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_150
MB_Tile_r0_150.Position 0.000000 -4.729549 -6.961374
MB_Tile_r0_150.Rotation 235.807860 0 0
MB_Tile_r0_150.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_151
MB_Tile_r0_151.Position 0.000000 -4.536790 -7.088505
MB_Tile_r0_151.Rotation 237.379913 0 0
MB_Tile_r0_151.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_152
MB_Tile_r0_152.Position 0.000000 -4.340616 -7.210300
MB_Tile_r0_152.Rotation 238.951965 0 0
MB_Tile_r0_152.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_153
MB_Tile_r0_153.Position 0.000000 -4.141175 -7.326666
MB_Tile_r0_153.Rotation 240.524017 0 0
MB_Tile_r0_153.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_154
MB_Tile_r0_154.Position 0.000000 -3.938616 -7.437518
MB_Tile_r0_154.Rotation 242.096070 0 0
MB_Tile_r0_154.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_155
MB_Tile_r0_155.Position 0.000000 -3.733093 -7.542771
MB_Tile_r0_155.Rotation 243.668122 0 0
MB_Tile_r0_155.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_156
MB_Tile_r0_156.Position 0.000000 -3.524759 -7.642346
MB_Tile_r0_156.Rotation 245.240175 0 0
MB_Tile_r0_156.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_157
MB_Tile_r0_157.Position 0.000000 -3.313772 -7.736168
MB_Tile_r0_157.Rotation 246.812227 0 0
MB_Tile_r0_157.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_158
MB_Tile_r0_158.Position 0.000000 -3.100290 -7.824166
MB_Tile_r0_158.Rotation 248.384279 0 0
MB_Tile_r0_158.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_159
MB_Tile_r0_159.Position 0.000000 -2.884475 -7.906275
MB_Tile_r0_159.Rotation 249.956332 0 0
MB_Tile_r0_159.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_160
MB_Tile_r0_160.Position 0.000000 -2.666488 -7.982432
MB_Tile_r0_160.Rotation 251.528384 0 0
MB_Tile_r0_160.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_161
MB_Tile_r0_161.Position 0.000000 -2.446494 -8.052580
MB_Tile_r0_161.Rotation 253.100437 0 0
MB_Tile_r0_161.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_162
MB_Tile_r0_162.Position 0.000000 -2.224658 -8.116666
MB_Tile_r0_162.Rotation 254.672489 0 0
MB_Tile_r0_162.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_163
MB_Tile_r0_163.Position 0.000000 -2.001148 -8.174642
MB_Tile_r0_163.Rotation 256.244541 0 0
MB_Tile_r0_163.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_164
MB_Tile_r0_164.Position 0.000000 -1.776131 -8.226465
MB_Tile_r0_164.Rotation 257.816594 0 0
MB_Tile_r0_164.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_165
MB_Tile_r0_165.Position 0.000000 -1.549777 -8.272095
MB_Tile_r0_165.Rotation 259.388646 0 0
MB_Tile_r0_165.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_166
MB_Tile_r0_166.Position 0.000000 -1.322257 -8.311499
MB_Tile_r0_166.Rotation 260.960699 0 0
MB_Tile_r0_166.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_167
MB_Tile_r0_167.Position 0.000000 -1.093741 -8.344645
MB_Tile_r0_167.Rotation 262.532751 0 0
MB_Tile_r0_167.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_168
MB_Tile_r0_168.Position 0.000000 -0.864402 -8.371510
MB_Tile_r0_168.Rotation 264.104803 0 0
MB_Tile_r0_168.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_169
MB_Tile_r0_169.Position 0.000000 -0.634412 -8.392073
MB_Tile_r0_169.Rotation 265.676856 0 0
MB_Tile_r0_169.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_170
MB_Tile_r0_170.Position 0.000000 -0.403945 -8.406319
MB_Tile_r0_170.Rotation 267.248908 0 0
MB_Tile_r0_170.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_171
MB_Tile_r0_171.Position 0.000000 -0.173174 -8.414237
MB_Tile_r0_171.Rotation 268.820961 0 0
MB_Tile_r0_171.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_172
MB_Tile_r0_172.Position 0.000000 0.057728 -8.415821
MB_Tile_r0_172.Rotation 270.393013 0 0
MB_Tile_r0_172.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_173
MB_Tile_r0_173.Position 0.000000 0.288586 -8.411069
MB_Tile_r0_173.Rotation 271.965066 0 0
MB_Tile_r0_173.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_174
MB_Tile_r0_174.Position 0.000000 0.519228 -8.399987
MB_Tile_r0_174.Rotation 273.537118 0 0
MB_Tile_r0_174.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_175
MB_Tile_r0_175.Position 0.000000 0.749478 -8.382580
MB_Tile_r0_175.Rotation 275.109170 0 0
MB_Tile_r0_175.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_176
MB_Tile_r0_176.Position 0.000000 0.979164 -8.358864
MB_Tile_r0_176.Rotation 276.681223 0 0
MB_Tile_r0_176.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_177
MB_Tile_r0_177.Position 0.000000 1.208113 -8.328856
MB_Tile_r0_177.Rotation 278.253275 0 0
MB_Tile_r0_177.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_178
MB_Tile_r0_178.Position 0.000000 1.436152 -8.292577
MB_Tile_r0_178.Rotation 279.825328 0 0
MB_Tile_r0_178.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_179
MB_Tile_r0_179.Position 0.000000 1.663111 -8.250057
MB_Tile_r0_179.Rotation 281.397380 0 0
MB_Tile_r0_179.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_180
MB_Tile_r0_180.Position 0.000000 1.888817 -8.201326
MB_Tile_r0_180.Rotation 282.969432 0 0
MB_Tile_r0_180.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_181
MB_Tile_r0_181.Position 0.000000 2.113102 -8.146421
MB_Tile_r0_181.Rotation 284.541485 0 0
MB_Tile_r0_181.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_182
MB_Tile_r0_182.Position 0.000000 2.335796 -8.085384
MB_Tile_r0_182.Rotation 286.113537 0 0
MB_Tile_r0_182.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_183
MB_Tile_r0_183.Position 0.000000 2.556731 -8.018260
MB_Tile_r0_183.Rotation 287.685590 0 0
MB_Tile_r0_183.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_184
MB_Tile_r0_184.Position 0.000000 2.775742 -7.945101
MB_Tile_r0_184.Rotation 289.257642 0 0
MB_Tile_r0_184.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_185
MB_Tile_r0_185.Position 0.000000 2.992664 -7.865960
MB_Tile_r0_185.Rotation 290.829694 0 0
MB_Tile_r0_185.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_186
MB_Tile_r0_186.Position 0.000000 3.207333 -7.780899
MB_Tile_r0_186.Rotation 292.401747 0 0
MB_Tile_r0_186.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_187
MB_Tile_r0_187.Position 0.000000 3.419587 -7.689980
MB_Tile_r0_187.Rotation 293.973799 0 0
MB_Tile_r0_187.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_188
MB_Tile_r0_188.Position 0.000000 3.629267 -7.593273
MB_Tile_r0_188.Rotation 295.545852 0 0
MB_Tile_r0_188.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_189
MB_Tile_r0_189.Position 0.000000 3.836215 -7.490849
MB_Tile_r0_189.Rotation 297.117904 0 0
MB_Tile_r0_189.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_190
MB_Tile_r0_190.Position 0.000000 4.040276 -7.382787
MB_Tile_r0_190.Rotation 298.689956 0 0
MB_Tile_r0_190.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_191
MB_Tile_r0_191.Position 0.000000 4.241295 -7.269167
MB_Tile_r0_191.Rotation 300.262009 0 0
MB_Tile_r0_191.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_192
MB_Tile_r0_192.Position 0.000000 4.439121 -7.150075
MB_Tile_r0_192.Rotation 301.834061 0 0
MB_Tile_r0_192.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_193
MB_Tile_r0_193.Position 0.000000 4.633606 -7.025601
MB_Tile_r0_193.Rotation 303.406114 0 0
MB_Tile_r0_193.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_194
MB_Tile_r0_194.Position 0.000000 4.824603 -6.895838
MB_Tile_r0_194.Rotation 304.978166 0 0
MB_Tile_r0_194.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_195
MB_Tile_r0_195.Position 0.000000 5.011967 -6.760884
MB_Tile_r0_195.Rotation 306.550218 0 0
MB_Tile_r0_195.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_196
MB_Tile_r0_196.Position 0.000000 5.195559 -6.620841
MB_Tile_r0_196.Rotation 308.122271 0 0
MB_Tile_r0_196.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_197
MB_Tile_r0_197.Position 0.000000 5.375240 -6.475814
MB_Tile_r0_197.Rotation 309.694323 0 0
MB_Tile_r0_197.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_198
MB_Tile_r0_198.Position 0.000000 5.550875 -6.325912
MB_Tile_r0_198.Rotation 311.266376 0 0
MB_Tile_r0_198.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_199
MB_Tile_r0_199.Position 0.000000 5.722331 -6.171248
MB_Tile_r0_199.Rotation 312.838428 0 0
MB_Tile_r0_199.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_200
MB_Tile_r0_200.Position 0.000000 5.889480 -6.011938
MB_Tile_r0_200.Rotation 314.410480 0 0
MB_Tile_r0_200.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_201
MB_Tile_r0_201.Position 0.000000 6.052195 -5.848103
MB_Tile_r0_201.Rotation 315.982533 0 0
MB_Tile_r0_201.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_202
MB_Tile_r0_202.Position 0.000000 6.210354 -5.679866
MB_Tile_r0_202.Rotation 317.554585 0 0
MB_Tile_r0_202.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_203
MB_Tile_r0_203.Position 0.000000 6.363838 -5.507353
MB_Tile_r0_203.Rotation 319.126638 0 0
MB_Tile_r0_203.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_204
MB_Tile_r0_204.Position 0.000000 6.512532 -5.330694
MB_Tile_r0_204.Rotation 320.698690 0 0
MB_Tile_r0_204.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_205
MB_Tile_r0_205.Position 0.000000 6.656323 -5.150023
MB_Tile_r0_205.Rotation 322.270742 0 0
MB_Tile_r0_205.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_206
MB_Tile_r0_206.Position 0.000000 6.795104 -4.965474
MB_Tile_r0_206.Rotation 323.842795 0 0
MB_Tile_r0_206.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_207
MB_Tile_r0_207.Position 0.000000 6.928769 -4.777188
MB_Tile_r0_207.Rotation 325.414847 0 0
MB_Tile_r0_207.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_208
MB_Tile_r0_208.Position 0.000000 7.057219 -4.585306
MB_Tile_r0_208.Rotation 326.986900 0 0
MB_Tile_r0_208.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_209
MB_Tile_r0_209.Position 0.000000 7.180356 -4.389972
MB_Tile_r0_209.Rotation 328.558952 0 0
MB_Tile_r0_209.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_210
MB_Tile_r0_210.Position 0.000000 7.298088 -4.191334
MB_Tile_r0_210.Rotation 330.131004 0 0
MB_Tile_r0_210.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_211
MB_Tile_r0_211.Position 0.000000 7.410327 -3.989540
MB_Tile_r0_211.Rotation 331.703057 0 0
MB_Tile_r0_211.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_212
MB_Tile_r0_212.Position 0.000000 7.516987 -3.784743
MB_Tile_r0_212.Rotation 333.275109 0 0
MB_Tile_r0_212.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_213
MB_Tile_r0_213.Position 0.000000 7.617988 -3.577097
MB_Tile_r0_213.Rotation 334.847162 0 0
MB_Tile_r0_213.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_214
MB_Tile_r0_214.Position 0.000000 7.713255 -3.366759
MB_Tile_r0_214.Rotation 336.419214 0 0
MB_Tile_r0_214.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_215
MB_Tile_r0_215.Position 0.000000 7.802716 -3.153886
MB_Tile_r0_215.Rotation 337.991266 0 0
MB_Tile_r0_215.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_216
MB_Tile_r0_216.Position 0.000000 7.886303 -2.938638
MB_Tile_r0_216.Rotation 339.563319 0 0
MB_Tile_r0_216.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_217
MB_Tile_r0_217.Position 0.000000 7.963953 -2.721179
MB_Tile_r0_217.Rotation 341.135371 0 0
MB_Tile_r0_217.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_218
MB_Tile_r0_218.Position 0.000000 8.035609 -2.501671
MB_Tile_r0_218.Rotation 342.707424 0 0
MB_Tile_r0_218.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_219
MB_Tile_r0_219.Position 0.000000 8.101215 -2.280281
MB_Tile_r0_219.Rotation 344.279476 0 0
MB_Tile_r0_219.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_220
MB_Tile_r0_220.Position 0.000000 8.160724 -2.057173
MB_Tile_r0_220.Rotation 345.851528 0 0
MB_Tile_r0_220.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_221
MB_Tile_r0_221.Position 0.000000 8.214089 -1.832517
MB_Tile_r0_221.Rotation 347.423581 0 0
MB_Tile_r0_221.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_222
MB_Tile_r0_222.Position 0.000000 8.261270 -1.606482
MB_Tile_r0_222.Rotation 348.995633 0 0
MB_Tile_r0_222.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_223
MB_Tile_r0_223.Position 0.000000 8.302233 -1.379237
MB_Tile_r0_223.Rotation 350.567686 0 0
MB_Tile_r0_223.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_224
MB_Tile_r0_224.Position 0.000000 8.336946 -1.150954
MB_Tile_r0_224.Rotation 352.139738 0 0
MB_Tile_r0_224.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_225
MB_Tile_r0_225.Position 0.000000 8.365384 -0.921805
MB_Tile_r0_225.Rotation 353.711790 0 0
MB_Tile_r0_225.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_226
MB_Tile_r0_226.Position 0.000000 8.387524 -0.691961
MB_Tile_r0_226.Rotation 355.283843 0 0
MB_Tile_r0_226.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_227
MB_Tile_r0_227.Position 0.000000 8.403350 -0.461597
MB_Tile_r0_227.Rotation 356.855895 0 0
MB_Tile_r0_227.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r0_228
MB_Tile_r0_228.Position 0.000000 8.412851 -0.230885
MB_Tile_r0_228.Rotation 358.427948 0 0
MB_Tile_r0_228.Mother InstrumentFrame

// ring 1: E=471.0 keV, r=8.058633 cm, 220 tiles
MB_Tile.Copy MB_Tile_r1_000
MB_Tile_r1_000.Position 0.000000 8.058633 0.000000
MB_Tile_r1_000.Rotation 0.000000 0 0
MB_Tile_r1_000.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_001
MB_Tile_r1_001.Position 0.000000 8.055346 0.230123
MB_Tile_r1_001.Rotation 1.636364 0 0
MB_Tile_r1_001.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_002
MB_Tile_r1_002.Position 0.000000 8.045490 0.460058
MB_Tile_r1_002.Rotation 3.272727 0 0
MB_Tile_r1_002.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_003
MB_Tile_r1_003.Position 0.000000 8.029072 0.689618
MB_Tile_r1_003.Rotation 4.909091 0 0
MB_Tile_r1_003.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_004
MB_Tile_r1_004.Position 0.000000 8.006104 0.918615
MB_Tile_r1_004.Rotation 6.545455 0 0
MB_Tile_r1_004.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_005
MB_Tile_r1_005.Position 0.000000 7.976608 1.146863
MB_Tile_r1_005.Rotation 8.181818 0 0
MB_Tile_r1_005.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_006
MB_Tile_r1_006.Position 0.000000 7.940605 1.374176
MB_Tile_r1_006.Rotation 9.818182 0 0
MB_Tile_r1_006.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_007
MB_Tile_r1_007.Position 0.000000 7.898125 1.600368
MB_Tile_r1_007.Rotation 11.454545 0 0
MB_Tile_r1_007.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_008
MB_Tile_r1_008.Position 0.000000 7.849204 1.825254
MB_Tile_r1_008.Rotation 13.090909 0 0
MB_Tile_r1_008.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_009
MB_Tile_r1_009.Position 0.000000 7.793881 2.048652
MB_Tile_r1_009.Rotation 14.727273 0 0
MB_Tile_r1_009.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_010
MB_Tile_r1_010.Position 0.000000 7.732202 2.270379
MB_Tile_r1_010.Rotation 16.363636 0 0
MB_Tile_r1_010.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_011
MB_Tile_r1_011.Position 0.000000 7.664215 2.490254
MB_Tile_r1_011.Rotation 18.000000 0 0
MB_Tile_r1_011.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_012
MB_Tile_r1_012.Position 0.000000 7.589978 2.708099
MB_Tile_r1_012.Rotation 19.636364 0 0
MB_Tile_r1_012.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_013
MB_Tile_r1_013.Position 0.000000 7.509550 2.923734
MB_Tile_r1_013.Rotation 21.272727 0 0
MB_Tile_r1_013.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_014
MB_Tile_r1_014.Position 0.000000 7.422997 3.136985
MB_Tile_r1_014.Rotation 22.909091 0 0
MB_Tile_r1_014.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_015
MB_Tile_r1_015.Position 0.000000 7.330390 3.347677
MB_Tile_r1_015.Rotation 24.545455 0 0
MB_Tile_r1_015.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_016
MB_Tile_r1_016.Position 0.000000 7.231804 3.555639
MB_Tile_r1_016.Rotation 26.181818 0 0
MB_Tile_r1_016.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_017
MB_Tile_r1_017.Position 0.000000 7.127320 3.760701
MB_Tile_r1_017.Rotation 27.818182 0 0
MB_Tile_r1_017.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_018
MB_Tile_r1_018.Position 0.000000 7.017023 3.962695
MB_Tile_r1_018.Rotation 29.454545 0 0
MB_Tile_r1_018.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_019
MB_Tile_r1_019.Position 0.000000 6.901002 4.161458
MB_Tile_r1_019.Rotation 31.090909 0 0
MB_Tile_r1_019.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_020
MB_Tile_r1_020.Position 0.000000 6.779353 4.356826
MB_Tile_r1_020.Rotation 32.727273 0 0
MB_Tile_r1_020.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_021
MB_Tile_r1_021.Position 0.000000 6.652175 4.548641
MB_Tile_r1_021.Rotation 34.363636 0 0
MB_Tile_r1_021.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_022
MB_Tile_r1_022.Position 0.000000 6.519571 4.736746
MB_Tile_r1_022.Rotation 36.000000 0 0
MB_Tile_r1_022.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_023
MB_Tile_r1_023.Position 0.000000 6.381649 4.920987
MB_Tile_r1_023.Rotation 37.636364 0 0
MB_Tile_r1_023.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_024
MB_Tile_r1_024.Position 0.000000 6.238523 5.101215
MB_Tile_r1_024.Rotation 39.272727 0 0
MB_Tile_r1_024.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_025
MB_Tile_r1_025.Position 0.000000 6.090308 5.277282
MB_Tile_r1_025.Rotation 40.909091 0 0
MB_Tile_r1_025.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_026
MB_Tile_r1_026.Position 0.000000 5.937126 5.449045
MB_Tile_r1_026.Rotation 42.545455 0 0
MB_Tile_r1_026.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_027
MB_Tile_r1_027.Position 0.000000 5.779102 5.616364
MB_Tile_r1_027.Rotation 44.181818 0 0
MB_Tile_r1_027.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_028
MB_Tile_r1_028.Position 0.000000 5.616364 5.779102
MB_Tile_r1_028.Rotation 45.818182 0 0
MB_Tile_r1_028.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_029
MB_Tile_r1_029.Position 0.000000 5.449045 5.937126
MB_Tile_r1_029.Rotation 47.454545 0 0
MB_Tile_r1_029.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_030
MB_Tile_r1_030.Position 0.000000 5.277282 6.090308
MB_Tile_r1_030.Rotation 49.090909 0 0
MB_Tile_r1_030.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_031
MB_Tile_r1_031.Position 0.000000 5.101215 6.238523
MB_Tile_r1_031.Rotation 50.727273 0 0
MB_Tile_r1_031.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_032
MB_Tile_r1_032.Position 0.000000 4.920987 6.381649
MB_Tile_r1_032.Rotation 52.363636 0 0
MB_Tile_r1_032.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_033
MB_Tile_r1_033.Position 0.000000 4.736746 6.519571
MB_Tile_r1_033.Rotation 54.000000 0 0
MB_Tile_r1_033.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_034
MB_Tile_r1_034.Position 0.000000 4.548641 6.652175
MB_Tile_r1_034.Rotation 55.636364 0 0
MB_Tile_r1_034.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_035
MB_Tile_r1_035.Position 0.000000 4.356826 6.779353
MB_Tile_r1_035.Rotation 57.272727 0 0
MB_Tile_r1_035.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_036
MB_Tile_r1_036.Position 0.000000 4.161458 6.901002
MB_Tile_r1_036.Rotation 58.909091 0 0
MB_Tile_r1_036.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_037
MB_Tile_r1_037.Position 0.000000 3.962695 7.017023
MB_Tile_r1_037.Rotation 60.545455 0 0
MB_Tile_r1_037.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_038
MB_Tile_r1_038.Position 0.000000 3.760701 7.127320
MB_Tile_r1_038.Rotation 62.181818 0 0
MB_Tile_r1_038.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_039
MB_Tile_r1_039.Position 0.000000 3.555639 7.231804
MB_Tile_r1_039.Rotation 63.818182 0 0
MB_Tile_r1_039.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_040
MB_Tile_r1_040.Position 0.000000 3.347677 7.330390
MB_Tile_r1_040.Rotation 65.454545 0 0
MB_Tile_r1_040.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_041
MB_Tile_r1_041.Position 0.000000 3.136985 7.422997
MB_Tile_r1_041.Rotation 67.090909 0 0
MB_Tile_r1_041.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_042
MB_Tile_r1_042.Position 0.000000 2.923734 7.509550
MB_Tile_r1_042.Rotation 68.727273 0 0
MB_Tile_r1_042.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_043
MB_Tile_r1_043.Position 0.000000 2.708099 7.589978
MB_Tile_r1_043.Rotation 70.363636 0 0
MB_Tile_r1_043.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_044
MB_Tile_r1_044.Position 0.000000 2.490254 7.664215
MB_Tile_r1_044.Rotation 72.000000 0 0
MB_Tile_r1_044.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_045
MB_Tile_r1_045.Position 0.000000 2.270379 7.732202
MB_Tile_r1_045.Rotation 73.636364 0 0
MB_Tile_r1_045.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_046
MB_Tile_r1_046.Position 0.000000 2.048652 7.793881
MB_Tile_r1_046.Rotation 75.272727 0 0
MB_Tile_r1_046.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_047
MB_Tile_r1_047.Position 0.000000 1.825254 7.849204
MB_Tile_r1_047.Rotation 76.909091 0 0
MB_Tile_r1_047.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_048
MB_Tile_r1_048.Position 0.000000 1.600368 7.898125
MB_Tile_r1_048.Rotation 78.545455 0 0
MB_Tile_r1_048.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_049
MB_Tile_r1_049.Position 0.000000 1.374176 7.940605
MB_Tile_r1_049.Rotation 80.181818 0 0
MB_Tile_r1_049.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_050
MB_Tile_r1_050.Position 0.000000 1.146863 7.976608
MB_Tile_r1_050.Rotation 81.818182 0 0
MB_Tile_r1_050.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_051
MB_Tile_r1_051.Position 0.000000 0.918615 8.006104
MB_Tile_r1_051.Rotation 83.454545 0 0
MB_Tile_r1_051.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_052
MB_Tile_r1_052.Position 0.000000 0.689618 8.029072
MB_Tile_r1_052.Rotation 85.090909 0 0
MB_Tile_r1_052.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_053
MB_Tile_r1_053.Position 0.000000 0.460058 8.045490
MB_Tile_r1_053.Rotation 86.727273 0 0
MB_Tile_r1_053.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_054
MB_Tile_r1_054.Position 0.000000 0.230123 8.055346
MB_Tile_r1_054.Rotation 88.363636 0 0
MB_Tile_r1_054.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_055
MB_Tile_r1_055.Position 0.000000 0.000000 8.058633
MB_Tile_r1_055.Rotation 90.000000 0 0
MB_Tile_r1_055.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_056
MB_Tile_r1_056.Position 0.000000 -0.230123 8.055346
MB_Tile_r1_056.Rotation 91.636364 0 0
MB_Tile_r1_056.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_057
MB_Tile_r1_057.Position 0.000000 -0.460058 8.045490
MB_Tile_r1_057.Rotation 93.272727 0 0
MB_Tile_r1_057.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_058
MB_Tile_r1_058.Position 0.000000 -0.689618 8.029072
MB_Tile_r1_058.Rotation 94.909091 0 0
MB_Tile_r1_058.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_059
MB_Tile_r1_059.Position 0.000000 -0.918615 8.006104
MB_Tile_r1_059.Rotation 96.545455 0 0
MB_Tile_r1_059.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_060
MB_Tile_r1_060.Position 0.000000 -1.146863 7.976608
MB_Tile_r1_060.Rotation 98.181818 0 0
MB_Tile_r1_060.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_061
MB_Tile_r1_061.Position 0.000000 -1.374176 7.940605
MB_Tile_r1_061.Rotation 99.818182 0 0
MB_Tile_r1_061.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_062
MB_Tile_r1_062.Position 0.000000 -1.600368 7.898125
MB_Tile_r1_062.Rotation 101.454545 0 0
MB_Tile_r1_062.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_063
MB_Tile_r1_063.Position 0.000000 -1.825254 7.849204
MB_Tile_r1_063.Rotation 103.090909 0 0
MB_Tile_r1_063.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_064
MB_Tile_r1_064.Position 0.000000 -2.048652 7.793881
MB_Tile_r1_064.Rotation 104.727273 0 0
MB_Tile_r1_064.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_065
MB_Tile_r1_065.Position 0.000000 -2.270379 7.732202
MB_Tile_r1_065.Rotation 106.363636 0 0
MB_Tile_r1_065.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_066
MB_Tile_r1_066.Position 0.000000 -2.490254 7.664215
MB_Tile_r1_066.Rotation 108.000000 0 0
MB_Tile_r1_066.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_067
MB_Tile_r1_067.Position 0.000000 -2.708099 7.589978
MB_Tile_r1_067.Rotation 109.636364 0 0
MB_Tile_r1_067.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_068
MB_Tile_r1_068.Position 0.000000 -2.923734 7.509550
MB_Tile_r1_068.Rotation 111.272727 0 0
MB_Tile_r1_068.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_069
MB_Tile_r1_069.Position 0.000000 -3.136985 7.422997
MB_Tile_r1_069.Rotation 112.909091 0 0
MB_Tile_r1_069.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_070
MB_Tile_r1_070.Position 0.000000 -3.347677 7.330390
MB_Tile_r1_070.Rotation 114.545455 0 0
MB_Tile_r1_070.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_071
MB_Tile_r1_071.Position 0.000000 -3.555639 7.231804
MB_Tile_r1_071.Rotation 116.181818 0 0
MB_Tile_r1_071.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_072
MB_Tile_r1_072.Position 0.000000 -3.760701 7.127320
MB_Tile_r1_072.Rotation 117.818182 0 0
MB_Tile_r1_072.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_073
MB_Tile_r1_073.Position 0.000000 -3.962695 7.017023
MB_Tile_r1_073.Rotation 119.454545 0 0
MB_Tile_r1_073.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_074
MB_Tile_r1_074.Position 0.000000 -4.161458 6.901002
MB_Tile_r1_074.Rotation 121.090909 0 0
MB_Tile_r1_074.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_075
MB_Tile_r1_075.Position 0.000000 -4.356826 6.779353
MB_Tile_r1_075.Rotation 122.727273 0 0
MB_Tile_r1_075.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_076
MB_Tile_r1_076.Position 0.000000 -4.548641 6.652175
MB_Tile_r1_076.Rotation 124.363636 0 0
MB_Tile_r1_076.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_077
MB_Tile_r1_077.Position 0.000000 -4.736746 6.519571
MB_Tile_r1_077.Rotation 126.000000 0 0
MB_Tile_r1_077.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_078
MB_Tile_r1_078.Position 0.000000 -4.920987 6.381649
MB_Tile_r1_078.Rotation 127.636364 0 0
MB_Tile_r1_078.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_079
MB_Tile_r1_079.Position 0.000000 -5.101215 6.238523
MB_Tile_r1_079.Rotation 129.272727 0 0
MB_Tile_r1_079.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_080
MB_Tile_r1_080.Position 0.000000 -5.277282 6.090308
MB_Tile_r1_080.Rotation 130.909091 0 0
MB_Tile_r1_080.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_081
MB_Tile_r1_081.Position 0.000000 -5.449045 5.937126
MB_Tile_r1_081.Rotation 132.545455 0 0
MB_Tile_r1_081.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_082
MB_Tile_r1_082.Position 0.000000 -5.616364 5.779102
MB_Tile_r1_082.Rotation 134.181818 0 0
MB_Tile_r1_082.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_083
MB_Tile_r1_083.Position 0.000000 -5.779102 5.616364
MB_Tile_r1_083.Rotation 135.818182 0 0
MB_Tile_r1_083.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_084
MB_Tile_r1_084.Position 0.000000 -5.937126 5.449045
MB_Tile_r1_084.Rotation 137.454545 0 0
MB_Tile_r1_084.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_085
MB_Tile_r1_085.Position 0.000000 -6.090308 5.277282
MB_Tile_r1_085.Rotation 139.090909 0 0
MB_Tile_r1_085.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_086
MB_Tile_r1_086.Position 0.000000 -6.238523 5.101215
MB_Tile_r1_086.Rotation 140.727273 0 0
MB_Tile_r1_086.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_087
MB_Tile_r1_087.Position 0.000000 -6.381649 4.920987
MB_Tile_r1_087.Rotation 142.363636 0 0
MB_Tile_r1_087.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_088
MB_Tile_r1_088.Position 0.000000 -6.519571 4.736746
MB_Tile_r1_088.Rotation 144.000000 0 0
MB_Tile_r1_088.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_089
MB_Tile_r1_089.Position 0.000000 -6.652175 4.548641
MB_Tile_r1_089.Rotation 145.636364 0 0
MB_Tile_r1_089.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_090
MB_Tile_r1_090.Position 0.000000 -6.779353 4.356826
MB_Tile_r1_090.Rotation 147.272727 0 0
MB_Tile_r1_090.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_091
MB_Tile_r1_091.Position 0.000000 -6.901002 4.161458
MB_Tile_r1_091.Rotation 148.909091 0 0
MB_Tile_r1_091.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_092
MB_Tile_r1_092.Position 0.000000 -7.017023 3.962695
MB_Tile_r1_092.Rotation 150.545455 0 0
MB_Tile_r1_092.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_093
MB_Tile_r1_093.Position 0.000000 -7.127320 3.760701
MB_Tile_r1_093.Rotation 152.181818 0 0
MB_Tile_r1_093.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_094
MB_Tile_r1_094.Position 0.000000 -7.231804 3.555639
MB_Tile_r1_094.Rotation 153.818182 0 0
MB_Tile_r1_094.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_095
MB_Tile_r1_095.Position 0.000000 -7.330390 3.347677
MB_Tile_r1_095.Rotation 155.454545 0 0
MB_Tile_r1_095.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_096
MB_Tile_r1_096.Position 0.000000 -7.422997 3.136985
MB_Tile_r1_096.Rotation 157.090909 0 0
MB_Tile_r1_096.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_097
MB_Tile_r1_097.Position 0.000000 -7.509550 2.923734
MB_Tile_r1_097.Rotation 158.727273 0 0
MB_Tile_r1_097.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_098
MB_Tile_r1_098.Position 0.000000 -7.589978 2.708099
MB_Tile_r1_098.Rotation 160.363636 0 0
MB_Tile_r1_098.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_099
MB_Tile_r1_099.Position 0.000000 -7.664215 2.490254
MB_Tile_r1_099.Rotation 162.000000 0 0
MB_Tile_r1_099.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_100
MB_Tile_r1_100.Position 0.000000 -7.732202 2.270379
MB_Tile_r1_100.Rotation 163.636364 0 0
MB_Tile_r1_100.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_101
MB_Tile_r1_101.Position 0.000000 -7.793881 2.048652
MB_Tile_r1_101.Rotation 165.272727 0 0
MB_Tile_r1_101.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_102
MB_Tile_r1_102.Position 0.000000 -7.849204 1.825254
MB_Tile_r1_102.Rotation 166.909091 0 0
MB_Tile_r1_102.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_103
MB_Tile_r1_103.Position 0.000000 -7.898125 1.600368
MB_Tile_r1_103.Rotation 168.545455 0 0
MB_Tile_r1_103.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_104
MB_Tile_r1_104.Position 0.000000 -7.940605 1.374176
MB_Tile_r1_104.Rotation 170.181818 0 0
MB_Tile_r1_104.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_105
MB_Tile_r1_105.Position 0.000000 -7.976608 1.146863
MB_Tile_r1_105.Rotation 171.818182 0 0
MB_Tile_r1_105.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_106
MB_Tile_r1_106.Position 0.000000 -8.006104 0.918615
MB_Tile_r1_106.Rotation 173.454545 0 0
MB_Tile_r1_106.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_107
MB_Tile_r1_107.Position 0.000000 -8.029072 0.689618
MB_Tile_r1_107.Rotation 175.090909 0 0
MB_Tile_r1_107.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_108
MB_Tile_r1_108.Position 0.000000 -8.045490 0.460058
MB_Tile_r1_108.Rotation 176.727273 0 0
MB_Tile_r1_108.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_109
MB_Tile_r1_109.Position 0.000000 -8.055346 0.230123
MB_Tile_r1_109.Rotation 178.363636 0 0
MB_Tile_r1_109.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_110
MB_Tile_r1_110.Position 0.000000 -8.058633 0.000000
MB_Tile_r1_110.Rotation 180.000000 0 0
MB_Tile_r1_110.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_111
MB_Tile_r1_111.Position 0.000000 -8.055346 -0.230123
MB_Tile_r1_111.Rotation 181.636364 0 0
MB_Tile_r1_111.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_112
MB_Tile_r1_112.Position 0.000000 -8.045490 -0.460058
MB_Tile_r1_112.Rotation 183.272727 0 0
MB_Tile_r1_112.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_113
MB_Tile_r1_113.Position 0.000000 -8.029072 -0.689618
MB_Tile_r1_113.Rotation 184.909091 0 0
MB_Tile_r1_113.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_114
MB_Tile_r1_114.Position 0.000000 -8.006104 -0.918615
MB_Tile_r1_114.Rotation 186.545455 0 0
MB_Tile_r1_114.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_115
MB_Tile_r1_115.Position 0.000000 -7.976608 -1.146863
MB_Tile_r1_115.Rotation 188.181818 0 0
MB_Tile_r1_115.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_116
MB_Tile_r1_116.Position 0.000000 -7.940605 -1.374176
MB_Tile_r1_116.Rotation 189.818182 0 0
MB_Tile_r1_116.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_117
MB_Tile_r1_117.Position 0.000000 -7.898125 -1.600368
MB_Tile_r1_117.Rotation 191.454545 0 0
MB_Tile_r1_117.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_118
MB_Tile_r1_118.Position 0.000000 -7.849204 -1.825254
MB_Tile_r1_118.Rotation 193.090909 0 0
MB_Tile_r1_118.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_119
MB_Tile_r1_119.Position 0.000000 -7.793881 -2.048652
MB_Tile_r1_119.Rotation 194.727273 0 0
MB_Tile_r1_119.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_120
MB_Tile_r1_120.Position 0.000000 -7.732202 -2.270379
MB_Tile_r1_120.Rotation 196.363636 0 0
MB_Tile_r1_120.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_121
MB_Tile_r1_121.Position 0.000000 -7.664215 -2.490254
MB_Tile_r1_121.Rotation 198.000000 0 0
MB_Tile_r1_121.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_122
MB_Tile_r1_122.Position 0.000000 -7.589978 -2.708099
MB_Tile_r1_122.Rotation 199.636364 0 0
MB_Tile_r1_122.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_123
MB_Tile_r1_123.Position 0.000000 -7.509550 -2.923734
MB_Tile_r1_123.Rotation 201.272727 0 0
MB_Tile_r1_123.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_124
MB_Tile_r1_124.Position 0.000000 -7.422997 -3.136985
MB_Tile_r1_124.Rotation 202.909091 0 0
MB_Tile_r1_124.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_125
MB_Tile_r1_125.Position 0.000000 -7.330390 -3.347677
MB_Tile_r1_125.Rotation 204.545455 0 0
MB_Tile_r1_125.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_126
MB_Tile_r1_126.Position 0.000000 -7.231804 -3.555639
MB_Tile_r1_126.Rotation 206.181818 0 0
MB_Tile_r1_126.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_127
MB_Tile_r1_127.Position 0.000000 -7.127320 -3.760701
MB_Tile_r1_127.Rotation 207.818182 0 0
MB_Tile_r1_127.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_128
MB_Tile_r1_128.Position 0.000000 -7.017023 -3.962695
MB_Tile_r1_128.Rotation 209.454545 0 0
MB_Tile_r1_128.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_129
MB_Tile_r1_129.Position 0.000000 -6.901002 -4.161458
MB_Tile_r1_129.Rotation 211.090909 0 0
MB_Tile_r1_129.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_130
MB_Tile_r1_130.Position 0.000000 -6.779353 -4.356826
MB_Tile_r1_130.Rotation 212.727273 0 0
MB_Tile_r1_130.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_131
MB_Tile_r1_131.Position 0.000000 -6.652175 -4.548641
MB_Tile_r1_131.Rotation 214.363636 0 0
MB_Tile_r1_131.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_132
MB_Tile_r1_132.Position 0.000000 -6.519571 -4.736746
MB_Tile_r1_132.Rotation 216.000000 0 0
MB_Tile_r1_132.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_133
MB_Tile_r1_133.Position 0.000000 -6.381649 -4.920987
MB_Tile_r1_133.Rotation 217.636364 0 0
MB_Tile_r1_133.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_134
MB_Tile_r1_134.Position 0.000000 -6.238523 -5.101215
MB_Tile_r1_134.Rotation 219.272727 0 0
MB_Tile_r1_134.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_135
MB_Tile_r1_135.Position 0.000000 -6.090308 -5.277282
MB_Tile_r1_135.Rotation 220.909091 0 0
MB_Tile_r1_135.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_136
MB_Tile_r1_136.Position 0.000000 -5.937126 -5.449045
MB_Tile_r1_136.Rotation 222.545455 0 0
MB_Tile_r1_136.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_137
MB_Tile_r1_137.Position 0.000000 -5.779102 -5.616364
MB_Tile_r1_137.Rotation 224.181818 0 0
MB_Tile_r1_137.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_138
MB_Tile_r1_138.Position 0.000000 -5.616364 -5.779102
MB_Tile_r1_138.Rotation 225.818182 0 0
MB_Tile_r1_138.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_139
MB_Tile_r1_139.Position 0.000000 -5.449045 -5.937126
MB_Tile_r1_139.Rotation 227.454545 0 0
MB_Tile_r1_139.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_140
MB_Tile_r1_140.Position 0.000000 -5.277282 -6.090308
MB_Tile_r1_140.Rotation 229.090909 0 0
MB_Tile_r1_140.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_141
MB_Tile_r1_141.Position 0.000000 -5.101215 -6.238523
MB_Tile_r1_141.Rotation 230.727273 0 0
MB_Tile_r1_141.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_142
MB_Tile_r1_142.Position 0.000000 -4.920987 -6.381649
MB_Tile_r1_142.Rotation 232.363636 0 0
MB_Tile_r1_142.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_143
MB_Tile_r1_143.Position 0.000000 -4.736746 -6.519571
MB_Tile_r1_143.Rotation 234.000000 0 0
MB_Tile_r1_143.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_144
MB_Tile_r1_144.Position 0.000000 -4.548641 -6.652175
MB_Tile_r1_144.Rotation 235.636364 0 0
MB_Tile_r1_144.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_145
MB_Tile_r1_145.Position 0.000000 -4.356826 -6.779353
MB_Tile_r1_145.Rotation 237.272727 0 0
MB_Tile_r1_145.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_146
MB_Tile_r1_146.Position 0.000000 -4.161458 -6.901002
MB_Tile_r1_146.Rotation 238.909091 0 0
MB_Tile_r1_146.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_147
MB_Tile_r1_147.Position 0.000000 -3.962695 -7.017023
MB_Tile_r1_147.Rotation 240.545455 0 0
MB_Tile_r1_147.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_148
MB_Tile_r1_148.Position 0.000000 -3.760701 -7.127320
MB_Tile_r1_148.Rotation 242.181818 0 0
MB_Tile_r1_148.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_149
MB_Tile_r1_149.Position 0.000000 -3.555639 -7.231804
MB_Tile_r1_149.Rotation 243.818182 0 0
MB_Tile_r1_149.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_150
MB_Tile_r1_150.Position 0.000000 -3.347677 -7.330390
MB_Tile_r1_150.Rotation 245.454545 0 0
MB_Tile_r1_150.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_151
MB_Tile_r1_151.Position 0.000000 -3.136985 -7.422997
MB_Tile_r1_151.Rotation 247.090909 0 0
MB_Tile_r1_151.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_152
MB_Tile_r1_152.Position 0.000000 -2.923734 -7.509550
MB_Tile_r1_152.Rotation 248.727273 0 0
MB_Tile_r1_152.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_153
MB_Tile_r1_153.Position 0.000000 -2.708099 -7.589978
MB_Tile_r1_153.Rotation 250.363636 0 0
MB_Tile_r1_153.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_154
MB_Tile_r1_154.Position 0.000000 -2.490254 -7.664215
MB_Tile_r1_154.Rotation 252.000000 0 0
MB_Tile_r1_154.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_155
MB_Tile_r1_155.Position 0.000000 -2.270379 -7.732202
MB_Tile_r1_155.Rotation 253.636364 0 0
MB_Tile_r1_155.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_156
MB_Tile_r1_156.Position 0.000000 -2.048652 -7.793881
MB_Tile_r1_156.Rotation 255.272727 0 0
MB_Tile_r1_156.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_157
MB_Tile_r1_157.Position 0.000000 -1.825254 -7.849204
MB_Tile_r1_157.Rotation 256.909091 0 0
MB_Tile_r1_157.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_158
MB_Tile_r1_158.Position 0.000000 -1.600368 -7.898125
MB_Tile_r1_158.Rotation 258.545455 0 0
MB_Tile_r1_158.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_159
MB_Tile_r1_159.Position 0.000000 -1.374176 -7.940605
MB_Tile_r1_159.Rotation 260.181818 0 0
MB_Tile_r1_159.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_160
MB_Tile_r1_160.Position 0.000000 -1.146863 -7.976608
MB_Tile_r1_160.Rotation 261.818182 0 0
MB_Tile_r1_160.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_161
MB_Tile_r1_161.Position 0.000000 -0.918615 -8.006104
MB_Tile_r1_161.Rotation 263.454545 0 0
MB_Tile_r1_161.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_162
MB_Tile_r1_162.Position 0.000000 -0.689618 -8.029072
MB_Tile_r1_162.Rotation 265.090909 0 0
MB_Tile_r1_162.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_163
MB_Tile_r1_163.Position 0.000000 -0.460058 -8.045490
MB_Tile_r1_163.Rotation 266.727273 0 0
MB_Tile_r1_163.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_164
MB_Tile_r1_164.Position 0.000000 -0.230123 -8.055346
MB_Tile_r1_164.Rotation 268.363636 0 0
MB_Tile_r1_164.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_165
MB_Tile_r1_165.Position 0.000000 -0.000000 -8.058633
MB_Tile_r1_165.Rotation 270.000000 0 0
MB_Tile_r1_165.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_166
MB_Tile_r1_166.Position 0.000000 0.230123 -8.055346
MB_Tile_r1_166.Rotation 271.636364 0 0
MB_Tile_r1_166.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_167
MB_Tile_r1_167.Position 0.000000 0.460058 -8.045490
MB_Tile_r1_167.Rotation 273.272727 0 0
MB_Tile_r1_167.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_168
MB_Tile_r1_168.Position 0.000000 0.689618 -8.029072
MB_Tile_r1_168.Rotation 274.909091 0 0
MB_Tile_r1_168.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_169
MB_Tile_r1_169.Position 0.000000 0.918615 -8.006104
MB_Tile_r1_169.Rotation 276.545455 0 0
MB_Tile_r1_169.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_170
MB_Tile_r1_170.Position 0.000000 1.146863 -7.976608
MB_Tile_r1_170.Rotation 278.181818 0 0
MB_Tile_r1_170.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_171
MB_Tile_r1_171.Position 0.000000 1.374176 -7.940605
MB_Tile_r1_171.Rotation 279.818182 0 0
MB_Tile_r1_171.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_172
MB_Tile_r1_172.Position 0.000000 1.600368 -7.898125
MB_Tile_r1_172.Rotation 281.454545 0 0
MB_Tile_r1_172.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_173
MB_Tile_r1_173.Position 0.000000 1.825254 -7.849204
MB_Tile_r1_173.Rotation 283.090909 0 0
MB_Tile_r1_173.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_174
MB_Tile_r1_174.Position 0.000000 2.048652 -7.793881
MB_Tile_r1_174.Rotation 284.727273 0 0
MB_Tile_r1_174.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_175
MB_Tile_r1_175.Position 0.000000 2.270379 -7.732202
MB_Tile_r1_175.Rotation 286.363636 0 0
MB_Tile_r1_175.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_176
MB_Tile_r1_176.Position 0.000000 2.490254 -7.664215
MB_Tile_r1_176.Rotation 288.000000 0 0
MB_Tile_r1_176.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_177
MB_Tile_r1_177.Position 0.000000 2.708099 -7.589978
MB_Tile_r1_177.Rotation 289.636364 0 0
MB_Tile_r1_177.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_178
MB_Tile_r1_178.Position 0.000000 2.923734 -7.509550
MB_Tile_r1_178.Rotation 291.272727 0 0
MB_Tile_r1_178.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_179
MB_Tile_r1_179.Position 0.000000 3.136985 -7.422997
MB_Tile_r1_179.Rotation 292.909091 0 0
MB_Tile_r1_179.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_180
MB_Tile_r1_180.Position 0.000000 3.347677 -7.330390
MB_Tile_r1_180.Rotation 294.545455 0 0
MB_Tile_r1_180.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_181
MB_Tile_r1_181.Position 0.000000 3.555639 -7.231804
MB_Tile_r1_181.Rotation 296.181818 0 0
MB_Tile_r1_181.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_182
MB_Tile_r1_182.Position 0.000000 3.760701 -7.127320
MB_Tile_r1_182.Rotation 297.818182 0 0
MB_Tile_r1_182.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_183
MB_Tile_r1_183.Position 0.000000 3.962695 -7.017023
MB_Tile_r1_183.Rotation 299.454545 0 0
MB_Tile_r1_183.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_184
MB_Tile_r1_184.Position 0.000000 4.161458 -6.901002
MB_Tile_r1_184.Rotation 301.090909 0 0
MB_Tile_r1_184.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_185
MB_Tile_r1_185.Position 0.000000 4.356826 -6.779353
MB_Tile_r1_185.Rotation 302.727273 0 0
MB_Tile_r1_185.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_186
MB_Tile_r1_186.Position 0.000000 4.548641 -6.652175
MB_Tile_r1_186.Rotation 304.363636 0 0
MB_Tile_r1_186.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_187
MB_Tile_r1_187.Position 0.000000 4.736746 -6.519571
MB_Tile_r1_187.Rotation 306.000000 0 0
MB_Tile_r1_187.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_188
MB_Tile_r1_188.Position 0.000000 4.920987 -6.381649
MB_Tile_r1_188.Rotation 307.636364 0 0
MB_Tile_r1_188.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_189
MB_Tile_r1_189.Position 0.000000 5.101215 -6.238523
MB_Tile_r1_189.Rotation 309.272727 0 0
MB_Tile_r1_189.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_190
MB_Tile_r1_190.Position 0.000000 5.277282 -6.090308
MB_Tile_r1_190.Rotation 310.909091 0 0
MB_Tile_r1_190.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_191
MB_Tile_r1_191.Position 0.000000 5.449045 -5.937126
MB_Tile_r1_191.Rotation 312.545455 0 0
MB_Tile_r1_191.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_192
MB_Tile_r1_192.Position 0.000000 5.616364 -5.779102
MB_Tile_r1_192.Rotation 314.181818 0 0
MB_Tile_r1_192.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_193
MB_Tile_r1_193.Position 0.000000 5.779102 -5.616364
MB_Tile_r1_193.Rotation 315.818182 0 0
MB_Tile_r1_193.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_194
MB_Tile_r1_194.Position 0.000000 5.937126 -5.449045
MB_Tile_r1_194.Rotation 317.454545 0 0
MB_Tile_r1_194.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_195
MB_Tile_r1_195.Position 0.000000 6.090308 -5.277282
MB_Tile_r1_195.Rotation 319.090909 0 0
MB_Tile_r1_195.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_196
MB_Tile_r1_196.Position 0.000000 6.238523 -5.101215
MB_Tile_r1_196.Rotation 320.727273 0 0
MB_Tile_r1_196.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_197
MB_Tile_r1_197.Position 0.000000 6.381649 -4.920987
MB_Tile_r1_197.Rotation 322.363636 0 0
MB_Tile_r1_197.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_198
MB_Tile_r1_198.Position 0.000000 6.519571 -4.736746
MB_Tile_r1_198.Rotation 324.000000 0 0
MB_Tile_r1_198.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_199
MB_Tile_r1_199.Position 0.000000 6.652175 -4.548641
MB_Tile_r1_199.Rotation 325.636364 0 0
MB_Tile_r1_199.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_200
MB_Tile_r1_200.Position 0.000000 6.779353 -4.356826
MB_Tile_r1_200.Rotation 327.272727 0 0
MB_Tile_r1_200.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_201
MB_Tile_r1_201.Position 0.000000 6.901002 -4.161458
MB_Tile_r1_201.Rotation 328.909091 0 0
MB_Tile_r1_201.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_202
MB_Tile_r1_202.Position 0.000000 7.017023 -3.962695
MB_Tile_r1_202.Rotation 330.545455 0 0
MB_Tile_r1_202.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_203
MB_Tile_r1_203.Position 0.000000 7.127320 -3.760701
MB_Tile_r1_203.Rotation 332.181818 0 0
MB_Tile_r1_203.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_204
MB_Tile_r1_204.Position 0.000000 7.231804 -3.555639
MB_Tile_r1_204.Rotation 333.818182 0 0
MB_Tile_r1_204.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_205
MB_Tile_r1_205.Position 0.000000 7.330390 -3.347677
MB_Tile_r1_205.Rotation 335.454545 0 0
MB_Tile_r1_205.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_206
MB_Tile_r1_206.Position 0.000000 7.422997 -3.136985
MB_Tile_r1_206.Rotation 337.090909 0 0
MB_Tile_r1_206.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_207
MB_Tile_r1_207.Position 0.000000 7.509550 -2.923734
MB_Tile_r1_207.Rotation 338.727273 0 0
MB_Tile_r1_207.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_208
MB_Tile_r1_208.Position 0.000000 7.589978 -2.708099
MB_Tile_r1_208.Rotation 340.363636 0 0
MB_Tile_r1_208.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_209
MB_Tile_r1_209.Position 0.000000 7.664215 -2.490254
MB_Tile_r1_209.Rotation 342.000000 0 0
MB_Tile_r1_209.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_210
MB_Tile_r1_210.Position 0.000000 7.732202 -2.270379
MB_Tile_r1_210.Rotation 343.636364 0 0
MB_Tile_r1_210.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_211
MB_Tile_r1_211.Position 0.000000 7.793881 -2.048652
MB_Tile_r1_211.Rotation 345.272727 0 0
MB_Tile_r1_211.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_212
MB_Tile_r1_212.Position 0.000000 7.849204 -1.825254
MB_Tile_r1_212.Rotation 346.909091 0 0
MB_Tile_r1_212.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_213
MB_Tile_r1_213.Position 0.000000 7.898125 -1.600368
MB_Tile_r1_213.Rotation 348.545455 0 0
MB_Tile_r1_213.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_214
MB_Tile_r1_214.Position 0.000000 7.940605 -1.374176
MB_Tile_r1_214.Rotation 350.181818 0 0
MB_Tile_r1_214.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_215
MB_Tile_r1_215.Position 0.000000 7.976608 -1.146863
MB_Tile_r1_215.Rotation 351.818182 0 0
MB_Tile_r1_215.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_216
MB_Tile_r1_216.Position 0.000000 8.006104 -0.918615
MB_Tile_r1_216.Rotation 353.454545 0 0
MB_Tile_r1_216.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_217
MB_Tile_r1_217.Position 0.000000 8.029072 -0.689618
MB_Tile_r1_217.Rotation 355.090909 0 0
MB_Tile_r1_217.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_218
MB_Tile_r1_218.Position 0.000000 8.045490 -0.460058
MB_Tile_r1_218.Rotation 356.727273 0 0
MB_Tile_r1_218.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r1_219
MB_Tile_r1_219.Position 0.000000 8.055346 -0.230123
MB_Tile_r1_219.Rotation 358.363636 0 0
MB_Tile_r1_219.Mother InstrumentFrame

// ring 2: E=491.0 keV, r=7.730364 cm, 211 tiles
MB_Tile.Copy MB_Tile_r2_000
MB_Tile_r2_000.Position 0.000000 7.730364 0.000000
MB_Tile_r2_000.Rotation 0.000000 0 0
MB_Tile_r2_000.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_001
MB_Tile_r2_001.Position 0.000000 7.726937 0.230162
MB_Tile_r2_001.Rotation 1.706161 0 0
MB_Tile_r2_001.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_002
MB_Tile_r2_002.Position 0.000000 7.716658 0.460119
MB_Tile_r2_002.Rotation 3.412322 0 0
MB_Tile_r2_002.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_003
MB_Tile_r2_003.Position 0.000000 7.699538 0.689669
MB_Tile_r2_003.Rotation 5.118483 0 0
MB_Tile_r2_003.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_004
MB_Tile_r2_004.Position 0.000000 7.675590 0.918607
MB_Tile_r2_004.Rotation 6.824645 0 0
MB_Tile_r2_004.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_005
MB_Tile_r2_005.Position 0.000000 7.644837 1.146731
MB_Tile_r2_005.Rotation 8.530806 0 0
MB_Tile_r2_005.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_006
MB_Tile_r2_006.Position 0.000000 7.607305 1.373838
MB_Tile_r2_006.Rotation 10.236967 0 0
MB_Tile_r2_006.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_007
MB_Tile_r2_007.Position 0.000000 7.563029 1.599727
MB_Tile_r2_007.Rotation 11.943128 0 0
MB_Tile_r2_007.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_008
MB_Tile_r2_008.Position 0.000000 7.512046 1.824197
MB_Tile_r2_008.Rotation 13.649289 0 0
MB_Tile_r2_008.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_009
MB_Tile_r2_009.Position 0.000000 7.454402 2.047050
MB_Tile_r2_009.Rotation 15.355450 0 0
MB_Tile_r2_009.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_010
MB_Tile_r2_010.Position 0.000000 7.390149 2.268088
MB_Tile_r2_010.Rotation 17.061611 0 0
MB_Tile_r2_010.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_011
MB_Tile_r2_011.Position 0.000000 7.319343 2.487115
MB_Tile_r2_011.Rotation 18.767773 0 0
MB_Tile_r2_011.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_012
MB_Tile_r2_012.Position 0.000000 7.242048 2.703936
MB_Tile_r2_012.Rotation 20.473934 0 0
MB_Tile_r2_012.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_013
MB_Tile_r2_013.Position 0.000000 7.158331 2.918360
MB_Tile_r2_013.Rotation 22.180095 0 0
MB_Tile_r2_013.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_014
MB_Tile_r2_014.Position 0.000000 7.068267 3.130196
MB_Tile_r2_014.Rotation 23.886256 0 0
MB_Tile_r2_014.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_015
MB_Tile_r2_015.Position 0.000000 6.971936 3.339257
MB_Tile_r2_015.Rotation 25.592417 0 0
MB_Tile_r2_015.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_016
MB_Tile_r2_016.Position 0.000000 6.869423 3.545357
MB_Tile_r2_016.Rotation 27.298578 0 0
MB_Tile_r2_016.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_017
MB_Tile_r2_017.Position 0.000000 6.760819 3.748314
MB_Tile_r2_017.Rotation 29.004739 0 0
MB_Tile_r2_017.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_018
MB_Tile_r2_018.Position 0.000000 6.646220 3.947947
MB_Tile_r2_018.Rotation 30.710900 0 0
MB_Tile_r2_018.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_019
MB_Tile_r2_019.Position 0.000000 6.525728 4.144080
MB_Tile_r2_019.Rotation 32.417062 0 0
MB_Tile_r2_019.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_020
MB_Tile_r2_020.Position 0.000000 6.399451 4.336538
MB_Tile_r2_020.Rotation 34.123223 0 0
MB_Tile_r2_020.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_021
MB_Tile_r2_021.Position 0.000000 6.267499 4.525151
MB_Tile_r2_021.Rotation 35.829384 0 0
MB_Tile_r2_021.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_022
MB_Tile_r2_022.Position 0.000000 6.129989 4.709751
MB_Tile_r2_022.Rotation 37.535545 0 0
MB_Tile_r2_022.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_023
MB_Tile_r2_023.Position 0.000000 5.987045 4.890176
MB_Tile_r2_023.Rotation 39.241706 0 0
MB_Tile_r2_023.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_024
MB_Tile_r2_024.Position 0.000000 5.838792 5.066264
MB_Tile_r2_024.Rotation 40.947867 0 0
MB_Tile_r2_024.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_025
MB_Tile_r2_025.Position 0.000000 5.685362 5.237861
MB_Tile_r2_025.Rotation 42.654028 0 0
MB_Tile_r2_025.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_026
MB_Tile_r2_026.Position 0.000000 5.526891 5.404813
MB_Tile_r2_026.Rotation 44.360190 0 0
MB_Tile_r2_026.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_027
MB_Tile_r2_027.Position 0.000000 5.363519 5.566973
MB_Tile_r2_027.Rotation 46.066351 0 0
MB_Tile_r2_027.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_028
MB_Tile_r2_028.Position 0.000000 5.195391 5.724197
MB_Tile_r2_028.Rotation 47.772512 0 0
MB_Tile_r2_028.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_029
MB_Tile_r2_029.Position 0.000000 5.022657 5.876346
MB_Tile_r2_029.Rotation 49.478673 0 0
MB_Tile_r2_029.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_030
MB_Tile_r2_030.Position 0.000000 4.845470 6.023284
MB_Tile_r2_030.Rotation 51.184834 0 0
MB_Tile_r2_030.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_031
MB_Tile_r2_031.Position 0.000000 4.663986 6.164881
MB_Tile_r2_031.Rotation 52.890995 0 0
MB_Tile_r2_031.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_032
MB_Tile_r2_032.Position 0.000000 4.478367 6.301012
MB_Tile_r2_032.Rotation 54.597156 0 0
MB_Tile_r2_032.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_033
MB_Tile_r2_033.Position 0.000000 4.288777 6.431556
MB_Tile_r2_033.Rotation 56.303318 0 0
MB_Tile_r2_033.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_034
MB_Tile_r2_034.Position 0.000000 4.095384 6.556398
MB_Tile_r2_034.Rotation 58.009479 0 0
MB_Tile_r2_034.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_035
MB_Tile_r2_035.Position 0.000000 3.898360 6.675426
MB_Tile_r2_035.Rotation 59.715640 0 0
MB_Tile_r2_035.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_036
MB_Tile_r2_036.Position 0.000000 3.697879 6.788535
MB_Tile_r2_036.Rotation 61.421801 0 0
MB_Tile_r2_036.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_037
MB_Tile_r2_037.Position 0.000000 3.494120 6.895625
MB_Tile_r2_037.Rotation 63.127962 0 0
MB_Tile_r2_037.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_038
MB_Tile_r2_038.Position 0.000000 3.287263 6.996601
MB_Tile_r2_038.Rotation 64.834123 0 0
MB_Tile_r2_038.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_039
MB_Tile_r2_039.Position 0.000000 3.077490 7.091374
MB_Tile_r2_039.Rotation 66.540284 0 0
MB_Tile_r2_039.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_040
MB_Tile_r2_040.Position 0.000000 2.864989 7.179858
MB_Tile_r2_040.Rotation 68.246445 0 0
MB_Tile_r2_040.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_041
MB_Tile_r2_041.Position 0.000000 2.649948 7.261976
MB_Tile_r2_041.Rotation 69.952607 0 0
MB_Tile_r2_041.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_042
MB_Tile_r2_042.Position 0.000000 2.432557 7.337656
MB_Tile_r2_042.Rotation 71.658768 0 0
MB_Tile_r2_042.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_043
MB_Tile_r2_043.Position 0.000000 2.213009 7.406829
MB_Tile_r2_043.Rotation 73.364929 0 0
MB_Tile_r2_043.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_044
MB_Tile_r2_044.Position 0.000000 1.991499 7.469435
MB_Tile_r2_044.Rotation 75.071090 0 0
MB_Tile_r2_044.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_045
MB_Tile_r2_045.Position 0.000000 1.768223 7.525418
MB_Tile_r2_045.Rotation 76.777251 0 0
MB_Tile_r2_045.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_046
MB_Tile_r2_046.Position 0.000000 1.543380 7.574728
MB_Tile_r2_046.Rotation 78.483412 0 0
MB_Tile_r2_046.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_047
MB_Tile_r2_047.Position 0.000000 1.317168 7.617322
MB_Tile_r2_047.Rotation 80.189573 0 0
MB_Tile_r2_047.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_048
MB_Tile_r2_048.Position 0.000000 1.089788 7.653162
MB_Tile_r2_048.Rotation 81.895735 0 0
MB_Tile_r2_048.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_049
MB_Tile_r2_049.Position 0.000000 0.861441 7.682216
MB_Tile_r2_049.Rotation 83.601896 0 0
MB_Tile_r2_049.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_050
MB_Tile_r2_050.Position 0.000000 0.632331 7.704459
MB_Tile_r2_050.Rotation 85.308057 0 0
MB_Tile_r2_050.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_051
MB_Tile_r2_051.Position 0.000000 0.402660 7.719870
MB_Tile_r2_051.Rotation 87.014218 0 0
MB_Tile_r2_051.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_052
MB_Tile_r2_052.Position 0.000000 0.172632 7.728436
MB_Tile_r2_052.Rotation 88.720379 0 0
MB_Tile_r2_052.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_053
MB_Tile_r2_053.Position 0.000000 -0.057548 7.730150
MB_Tile_r2_053.Rotation 90.426540 0 0
MB_Tile_r2_053.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_054
MB_Tile_r2_054.Position 0.000000 -0.287678 7.725009
MB_Tile_r2_054.Rotation 92.132701 0 0
MB_Tile_r2_054.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_055
MB_Tile_r2_055.Position 0.000000 -0.517553 7.713019
MB_Tile_r2_055.Rotation 93.838863 0 0
MB_Tile_r2_055.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_056
MB_Tile_r2_056.Position 0.000000 -0.746969 7.694190
MB_Tile_r2_056.Rotation 95.545024 0 0
MB_Tile_r2_056.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_057
MB_Tile_r2_057.Position 0.000000 -0.975723 7.668539
MB_Tile_r2_057.Rotation 97.251185 0 0
MB_Tile_r2_057.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_058
MB_Tile_r2_058.Position 0.000000 -1.203611 7.636088
MB_Tile_r2_058.Rotation 98.957346 0 0
MB_Tile_r2_058.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_059
MB_Tile_r2_059.Position 0.000000 -1.430432 7.596867
MB_Tile_r2_059.Rotation 100.663507 0 0
MB_Tile_r2_059.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_060
MB_Tile_r2_060.Position 0.000000 -1.655985 7.550910
MB_Tile_r2_060.Rotation 102.369668 0 0
MB_Tile_r2_060.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_061
MB_Tile_r2_061.Position 0.000000 -1.880070 7.498257
MB_Tile_r2_061.Rotation 104.075829 0 0
MB_Tile_r2_061.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_062
MB_Tile_r2_062.Position 0.000000 -2.102487 7.438956
MB_Tile_r2_062.Rotation 105.781991 0 0
MB_Tile_r2_062.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_063
MB_Tile_r2_063.Position 0.000000 -2.323041 7.373060
MB_Tile_r2_063.Rotation 107.488152 0 0
MB_Tile_r2_063.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_064
MB_Tile_r2_064.Position 0.000000 -2.541534 7.300625
MB_Tile_r2_064.Rotation 109.194313 0 0
MB_Tile_r2_064.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_065
MB_Tile_r2_065.Position 0.000000 -2.757774 7.221718
MB_Tile_r2_065.Rotation 110.900474 0 0
MB_Tile_r2_065.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_066
MB_Tile_r2_066.Position 0.000000 -2.971569 7.136407
MB_Tile_r2_066.Rotation 112.606635 0 0
MB_Tile_r2_066.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_067
MB_Tile_r2_067.Position 0.000000 -3.182729 7.044768
MB_Tile_r2_067.Rotation 114.312796 0 0
MB_Tile_r2_067.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_068
MB_Tile_r2_068.Position 0.000000 -3.391067 6.946883
MB_Tile_r2_068.Rotation 116.018957 0 0
MB_Tile_r2_068.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_069
MB_Tile_r2_069.Position 0.000000 -3.596398 6.842839
MB_Tile_r2_069.Rotation 117.725118 0 0
MB_Tile_r2_069.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_070
MB_Tile_r2_070.Position 0.000000 -3.798541 6.732727
MB_Tile_r2_070.Rotation 119.431280 0 0
MB_Tile_r2_070.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_071
MB_Tile_r2_071.Position 0.000000 -3.997315 6.616645
MB_Tile_r2_071.Rotation 121.137441 0 0
MB_Tile_r2_071.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_072
MB_Tile_r2_072.Position 0.000000 -4.192545 6.494697
MB_Tile_r2_072.Rotation 122.843602 0 0
MB_Tile_r2_072.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_073
MB_Tile_r2_073.Position 0.000000 -4.384058 6.366990
MB_Tile_r2_073.Rotation 124.549763 0 0
MB_Tile_r2_073.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_074
MB_Tile_r2_074.Position 0.000000 -4.571683 6.233638
MB_Tile_r2_074.Rotation 126.255924 0 0
MB_Tile_r2_074.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_075
MB_Tile_r2_075.Position 0.000000 -4.755255 6.094758
MB_Tile_r2_075.Rotation 127.962085 0 0
MB_Tile_r2_075.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_076
MB_Tile_r2_076.Position 0.000000 -4.934611 5.950474
MB_Tile_r2_076.Rotation 129.668246 0 0
MB_Tile_r2_076.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_077
MB_Tile_r2_077.Position 0.000000 -5.109591 5.800914
MB_Tile_r2_077.Rotation 131.374408 0 0
MB_Tile_r2_077.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_078
MB_Tile_r2_078.Position 0.000000 -5.280040 5.646211
MB_Tile_r2_078.Rotation 133.080569 0 0
MB_Tile_r2_078.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_079
MB_Tile_r2_079.Position 0.000000 -5.445808 5.486501
MB_Tile_r2_079.Rotation 134.786730 0 0
MB_Tile_r2_079.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_080
MB_Tile_r2_080.Position 0.000000 -5.606748 5.321927
MB_Tile_r2_080.Rotation 136.492891 0 0
MB_Tile_r2_080.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_081
MB_Tile_r2_081.Position 0.000000 -5.762716 5.152634
MB_Tile_r2_081.Rotation 138.199052 0 0
MB_Tile_r2_081.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_082
MB_Tile_r2_082.Position 0.000000 -5.913574 4.978772
MB_Tile_r2_082.Rotation 139.905213 0 0
MB_Tile_r2_082.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_083
MB_Tile_r2_083.Position 0.000000 -6.059189 4.800496
MB_Tile_r2_083.Rotation 141.611374 0 0
MB_Tile_r2_083.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_084
MB_Tile_r2_084.Position 0.000000 -6.199431 4.617963
MB_Tile_r2_084.Rotation 143.317536 0 0
MB_Tile_r2_084.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_085
MB_Tile_r2_085.Position 0.000000 -6.334177 4.431335
MB_Tile_r2_085.Rotation 145.023697 0 0
MB_Tile_r2_085.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_086
MB_Tile_r2_086.Position 0.000000 -6.463306 4.240779
MB_Tile_r2_086.Rotation 146.729858 0 0
MB_Tile_r2_086.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_087
MB_Tile_r2_087.Position 0.000000 -6.586704 4.046462
MB_Tile_r2_087.Rotation 148.436019 0 0
MB_Tile_r2_087.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_088
MB_Tile_r2_088.Position 0.000000 -6.704262 3.848557
MB_Tile_r2_088.Rotation 150.142180 0 0
MB_Tile_r2_088.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_089
MB_Tile_r2_089.Position 0.000000 -6.815876 3.647240
MB_Tile_r2_089.Rotation 151.848341 0 0
MB_Tile_r2_089.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_090
MB_Tile_r2_090.Position 0.000000 -6.921446 3.442689
MB_Tile_r2_090.Rotation 153.554502 0 0
MB_Tile_r2_090.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_091
MB_Tile_r2_091.Position 0.000000 -7.020879 3.235085
MB_Tile_r2_091.Rotation 155.260664 0 0
MB_Tile_r2_091.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_092
MB_Tile_r2_092.Position 0.000000 -7.114087 3.024614
MB_Tile_r2_092.Rotation 156.966825 0 0
MB_Tile_r2_092.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_093
MB_Tile_r2_093.Position 0.000000 -7.200987 2.811460
MB_Tile_r2_093.Rotation 158.672986 0 0
MB_Tile_r2_093.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_094
MB_Tile_r2_094.Position 0.000000 -7.281503 2.595813
MB_Tile_r2_094.Rotation 160.379147 0 0
MB_Tile_r2_094.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_095
MB_Tile_r2_095.Position 0.000000 -7.355562 2.377865
MB_Tile_r2_095.Rotation 162.085308 0 0
MB_Tile_r2_095.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_096
MB_Tile_r2_096.Position 0.000000 -7.423098 2.157808
MB_Tile_r2_096.Rotation 163.791469 0 0
MB_Tile_r2_096.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_097
MB_Tile_r2_097.Position 0.000000 -7.484054 1.935838
MB_Tile_r2_097.Rotation 165.497630 0 0
MB_Tile_r2_097.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_098
MB_Tile_r2_098.Position 0.000000 -7.538373 1.712152
MB_Tile_r2_098.Rotation 167.203791 0 0
MB_Tile_r2_098.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_099
MB_Tile_r2_099.Position 0.000000 -7.586008 1.486947
MB_Tile_r2_099.Rotation 168.909953 0 0
MB_Tile_r2_099.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_100
MB_Tile_r2_100.Position 0.000000 -7.626917 1.260424
MB_Tile_r2_100.Rotation 170.616114 0 0
MB_Tile_r2_100.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_101
MB_Tile_r2_101.Position 0.000000 -7.661063 1.032784
MB_Tile_r2_101.Rotation 172.322275 0 0
MB_Tile_r2_101.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_102
MB_Tile_r2_102.Position 0.000000 -7.688416 0.804227
MB_Tile_r2_102.Rotation 174.028436 0 0
MB_Tile_r2_102.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_103
MB_Tile_r2_103.Position 0.000000 -7.708953 0.574958
MB_Tile_r2_103.Rotation 175.734597 0 0
MB_Tile_r2_103.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_104
MB_Tile_r2_104.Position 0.000000 -7.722654 0.345179
MB_Tile_r2_104.Rotation 177.440758 0 0
MB_Tile_r2_104.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_105
MB_Tile_r2_105.Position 0.000000 -7.729507 0.115094
MB_Tile_r2_105.Rotation 179.146919 0 0
MB_Tile_r2_105.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_106
MB_Tile_r2_106.Position 0.000000 -7.729507 -0.115094
MB_Tile_r2_106.Rotation 180.853081 0 0
MB_Tile_r2_106.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_107
MB_Tile_r2_107.Position 0.000000 -7.722654 -0.345179
MB_Tile_r2_107.Rotation 182.559242 0 0
MB_Tile_r2_107.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_108
MB_Tile_r2_108.Position 0.000000 -7.708953 -0.574958
MB_Tile_r2_108.Rotation 184.265403 0 0
MB_Tile_r2_108.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_109
MB_Tile_r2_109.Position 0.000000 -7.688416 -0.804227
MB_Tile_r2_109.Rotation 185.971564 0 0
MB_Tile_r2_109.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_110
MB_Tile_r2_110.Position 0.000000 -7.661063 -1.032784
MB_Tile_r2_110.Rotation 187.677725 0 0
MB_Tile_r2_110.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_111
MB_Tile_r2_111.Position 0.000000 -7.626917 -1.260424
MB_Tile_r2_111.Rotation 189.383886 0 0
MB_Tile_r2_111.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_112
MB_Tile_r2_112.Position 0.000000 -7.586008 -1.486947
MB_Tile_r2_112.Rotation 191.090047 0 0
MB_Tile_r2_112.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_113
MB_Tile_r2_113.Position 0.000000 -7.538373 -1.712152
MB_Tile_r2_113.Rotation 192.796209 0 0
MB_Tile_r2_113.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_114
MB_Tile_r2_114.Position 0.000000 -7.484054 -1.935838
MB_Tile_r2_114.Rotation 194.502370 0 0
MB_Tile_r2_114.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_115
MB_Tile_r2_115.Position 0.000000 -7.423098 -2.157808
MB_Tile_r2_115.Rotation 196.208531 0 0
MB_Tile_r2_115.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_116
MB_Tile_r2_116.Position 0.000000 -7.355562 -2.377865
MB_Tile_r2_116.Rotation 197.914692 0 0
MB_Tile_r2_116.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_117
MB_Tile_r2_117.Position 0.000000 -7.281503 -2.595813
MB_Tile_r2_117.Rotation 199.620853 0 0
MB_Tile_r2_117.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_118
MB_Tile_r2_118.Position 0.000000 -7.200987 -2.811460
MB_Tile_r2_118.Rotation 201.327014 0 0
MB_Tile_r2_118.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_119
MB_Tile_r2_119.Position 0.000000 -7.114087 -3.024614
MB_Tile_r2_119.Rotation 203.033175 0 0
MB_Tile_r2_119.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_120
MB_Tile_r2_120.Position 0.000000 -7.020879 -3.235085
MB_Tile_r2_120.Rotation 204.739336 0 0
MB_Tile_r2_120.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_121
MB_Tile_r2_121.Position 0.000000 -6.921446 -3.442689
MB_Tile_r2_121.Rotation 206.445498 0 0
MB_Tile_r2_121.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_122
MB_Tile_r2_122.Position 0.000000 -6.815876 -3.647240
MB_Tile_r2_122.Rotation 208.151659 0 0
MB_Tile_r2_122.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_123
MB_Tile_r2_123.Position 0.000000 -6.704262 -3.848557
MB_Tile_r2_123.Rotation 209.857820 0 0
MB_Tile_r2_123.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_124
MB_Tile_r2_124.Position 0.000000 -6.586704 -4.046462
MB_Tile_r2_124.Rotation 211.563981 0 0
MB_Tile_r2_124.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_125
MB_Tile_r2_125.Position 0.000000 -6.463306 -4.240779
MB_Tile_r2_125.Rotation 213.270142 0 0
MB_Tile_r2_125.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_126
MB_Tile_r2_126.Position 0.000000 -6.334177 -4.431335
MB_Tile_r2_126.Rotation 214.976303 0 0
MB_Tile_r2_126.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_127
MB_Tile_r2_127.Position 0.000000 -6.199431 -4.617963
MB_Tile_r2_127.Rotation 216.682464 0 0
MB_Tile_r2_127.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_128
MB_Tile_r2_128.Position 0.000000 -6.059189 -4.800496
MB_Tile_r2_128.Rotation 218.388626 0 0
MB_Tile_r2_128.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_129
MB_Tile_r2_129.Position 0.000000 -5.913574 -4.978772
MB_Tile_r2_129.Rotation 220.094787 0 0
MB_Tile_r2_129.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_130
MB_Tile_r2_130.Position 0.000000 -5.762716 -5.152634
MB_Tile_r2_130.Rotation 221.800948 0 0
MB_Tile_r2_130.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_131
MB_Tile_r2_131.Position 0.000000 -5.606748 -5.321927
MB_Tile_r2_131.Rotation 223.507109 0 0
MB_Tile_r2_131.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_132
MB_Tile_r2_132.Position 0.000000 -5.445808 -5.486501
MB_Tile_r2_132.Rotation 225.213270 0 0
MB_Tile_r2_132.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_133
MB_Tile_r2_133.Position 0.000000 -5.280040 -5.646211
MB_Tile_r2_133.Rotation 226.919431 0 0
MB_Tile_r2_133.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_134
MB_Tile_r2_134.Position 0.000000 -5.109591 -5.800914
MB_Tile_r2_134.Rotation 228.625592 0 0
MB_Tile_r2_134.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_135
MB_Tile_r2_135.Position 0.000000 -4.934611 -5.950474
MB_Tile_r2_135.Rotation 230.331754 0 0
MB_Tile_r2_135.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_136
MB_Tile_r2_136.Position 0.000000 -4.755255 -6.094758
MB_Tile_r2_136.Rotation 232.037915 0 0
MB_Tile_r2_136.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_137
MB_Tile_r2_137.Position 0.000000 -4.571683 -6.233638
MB_Tile_r2_137.Rotation 233.744076 0 0
MB_Tile_r2_137.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_138
MB_Tile_r2_138.Position 0.000000 -4.384058 -6.366990
MB_Tile_r2_138.Rotation 235.450237 0 0
MB_Tile_r2_138.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_139
MB_Tile_r2_139.Position 0.000000 -4.192545 -6.494697
MB_Tile_r2_139.Rotation 237.156398 0 0
MB_Tile_r2_139.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_140
MB_Tile_r2_140.Position 0.000000 -3.997315 -6.616645
MB_Tile_r2_140.Rotation 238.862559 0 0
MB_Tile_r2_140.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_141
MB_Tile_r2_141.Position 0.000000 -3.798541 -6.732727
MB_Tile_r2_141.Rotation 240.568720 0 0
MB_Tile_r2_141.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_142
MB_Tile_r2_142.Position 0.000000 -3.596398 -6.842839
MB_Tile_r2_142.Rotation 242.274882 0 0
MB_Tile_r2_142.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_143
MB_Tile_r2_143.Position 0.000000 -3.391067 -6.946883
MB_Tile_r2_143.Rotation 243.981043 0 0
MB_Tile_r2_143.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_144
MB_Tile_r2_144.Position 0.000000 -3.182729 -7.044768
MB_Tile_r2_144.Rotation 245.687204 0 0
MB_Tile_r2_144.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_145
MB_Tile_r2_145.Position 0.000000 -2.971569 -7.136407
MB_Tile_r2_145.Rotation 247.393365 0 0
MB_Tile_r2_145.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_146
MB_Tile_r2_146.Position 0.000000 -2.757774 -7.221718
MB_Tile_r2_146.Rotation 249.099526 0 0
MB_Tile_r2_146.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_147
MB_Tile_r2_147.Position 0.000000 -2.541534 -7.300625
MB_Tile_r2_147.Rotation 250.805687 0 0
MB_Tile_r2_147.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_148
MB_Tile_r2_148.Position 0.000000 -2.323041 -7.373060
MB_Tile_r2_148.Rotation 252.511848 0 0
MB_Tile_r2_148.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_149
MB_Tile_r2_149.Position 0.000000 -2.102487 -7.438956
MB_Tile_r2_149.Rotation 254.218009 0 0
MB_Tile_r2_149.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_150
MB_Tile_r2_150.Position 0.000000 -1.880070 -7.498257
MB_Tile_r2_150.Rotation 255.924171 0 0
MB_Tile_r2_150.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_151
MB_Tile_r2_151.Position 0.000000 -1.655985 -7.550910
MB_Tile_r2_151.Rotation 257.630332 0 0
MB_Tile_r2_151.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_152
MB_Tile_r2_152.Position 0.000000 -1.430432 -7.596867
MB_Tile_r2_152.Rotation 259.336493 0 0
MB_Tile_r2_152.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_153
MB_Tile_r2_153.Position 0.000000 -1.203611 -7.636088
MB_Tile_r2_153.Rotation 261.042654 0 0
MB_Tile_r2_153.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_154
MB_Tile_r2_154.Position 0.000000 -0.975723 -7.668539
MB_Tile_r2_154.Rotation 262.748815 0 0
MB_Tile_r2_154.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_155
MB_Tile_r2_155.Position 0.000000 -0.746969 -7.694190
MB_Tile_r2_155.Rotation 264.454976 0 0
MB_Tile_r2_155.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_156
MB_Tile_r2_156.Position 0.000000 -0.517553 -7.713019
MB_Tile_r2_156.Rotation 266.161137 0 0
MB_Tile_r2_156.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_157
MB_Tile_r2_157.Position 0.000000 -0.287678 -7.725009
MB_Tile_r2_157.Rotation 267.867299 0 0
MB_Tile_r2_157.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_158
MB_Tile_r2_158.Position 0.000000 -0.057548 -7.730150
MB_Tile_r2_158.Rotation 269.573460 0 0
MB_Tile_r2_158.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_159
MB_Tile_r2_159.Position 0.000000 0.172632 -7.728436
MB_Tile_r2_159.Rotation 271.279621 0 0
MB_Tile_r2_159.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_160
MB_Tile_r2_160.Position 0.000000 0.402660 -7.719870
MB_Tile_r2_160.Rotation 272.985782 0 0
MB_Tile_r2_160.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_161
MB_Tile_r2_161.Position 0.000000 0.632331 -7.704459
MB_Tile_r2_161.Rotation 274.691943 0 0
MB_Tile_r2_161.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_162
MB_Tile_r2_162.Position 0.000000 0.861441 -7.682216
MB_Tile_r2_162.Rotation 276.398104 0 0
MB_Tile_r2_162.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_163
MB_Tile_r2_163.Position 0.000000 1.089788 -7.653162
MB_Tile_r2_163.Rotation 278.104265 0 0
MB_Tile_r2_163.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_164
MB_Tile_r2_164.Position 0.000000 1.317168 -7.617322
MB_Tile_r2_164.Rotation 279.810427 0 0
MB_Tile_r2_164.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_165
MB_Tile_r2_165.Position 0.000000 1.543380 -7.574728
MB_Tile_r2_165.Rotation 281.516588 0 0
MB_Tile_r2_165.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_166
MB_Tile_r2_166.Position 0.000000 1.768223 -7.525418
MB_Tile_r2_166.Rotation 283.222749 0 0
MB_Tile_r2_166.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_167
MB_Tile_r2_167.Position 0.000000 1.991499 -7.469435
MB_Tile_r2_167.Rotation 284.928910 0 0
MB_Tile_r2_167.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_168
MB_Tile_r2_168.Position 0.000000 2.213009 -7.406829
MB_Tile_r2_168.Rotation 286.635071 0 0
MB_Tile_r2_168.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_169
MB_Tile_r2_169.Position 0.000000 2.432557 -7.337656
MB_Tile_r2_169.Rotation 288.341232 0 0
MB_Tile_r2_169.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_170
MB_Tile_r2_170.Position 0.000000 2.649948 -7.261976
MB_Tile_r2_170.Rotation 290.047393 0 0
MB_Tile_r2_170.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_171
MB_Tile_r2_171.Position 0.000000 2.864989 -7.179858
MB_Tile_r2_171.Rotation 291.753555 0 0
MB_Tile_r2_171.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_172
MB_Tile_r2_172.Position 0.000000 3.077490 -7.091374
MB_Tile_r2_172.Rotation 293.459716 0 0
MB_Tile_r2_172.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_173
MB_Tile_r2_173.Position 0.000000 3.287263 -6.996601
MB_Tile_r2_173.Rotation 295.165877 0 0
MB_Tile_r2_173.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_174
MB_Tile_r2_174.Position 0.000000 3.494120 -6.895625
MB_Tile_r2_174.Rotation 296.872038 0 0
MB_Tile_r2_174.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_175
MB_Tile_r2_175.Position 0.000000 3.697879 -6.788535
MB_Tile_r2_175.Rotation 298.578199 0 0
MB_Tile_r2_175.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_176
MB_Tile_r2_176.Position 0.000000 3.898360 -6.675426
MB_Tile_r2_176.Rotation 300.284360 0 0
MB_Tile_r2_176.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_177
MB_Tile_r2_177.Position 0.000000 4.095384 -6.556398
MB_Tile_r2_177.Rotation 301.990521 0 0
MB_Tile_r2_177.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_178
MB_Tile_r2_178.Position 0.000000 4.288777 -6.431556
MB_Tile_r2_178.Rotation 303.696682 0 0
MB_Tile_r2_178.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_179
MB_Tile_r2_179.Position 0.000000 4.478367 -6.301012
MB_Tile_r2_179.Rotation 305.402844 0 0
MB_Tile_r2_179.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_180
MB_Tile_r2_180.Position 0.000000 4.663986 -6.164881
MB_Tile_r2_180.Rotation 307.109005 0 0
MB_Tile_r2_180.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_181
MB_Tile_r2_181.Position 0.000000 4.845470 -6.023284
MB_Tile_r2_181.Rotation 308.815166 0 0
MB_Tile_r2_181.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_182
MB_Tile_r2_182.Position 0.000000 5.022657 -5.876346
MB_Tile_r2_182.Rotation 310.521327 0 0
MB_Tile_r2_182.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_183
MB_Tile_r2_183.Position 0.000000 5.195391 -5.724197
MB_Tile_r2_183.Rotation 312.227488 0 0
MB_Tile_r2_183.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_184
MB_Tile_r2_184.Position 0.000000 5.363519 -5.566973
MB_Tile_r2_184.Rotation 313.933649 0 0
MB_Tile_r2_184.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_185
MB_Tile_r2_185.Position 0.000000 5.526891 -5.404813
MB_Tile_r2_185.Rotation 315.639810 0 0
MB_Tile_r2_185.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_186
MB_Tile_r2_186.Position 0.000000 5.685362 -5.237861
MB_Tile_r2_186.Rotation 317.345972 0 0
MB_Tile_r2_186.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_187
MB_Tile_r2_187.Position 0.000000 5.838792 -5.066264
MB_Tile_r2_187.Rotation 319.052133 0 0
MB_Tile_r2_187.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_188
MB_Tile_r2_188.Position 0.000000 5.987045 -4.890176
MB_Tile_r2_188.Rotation 320.758294 0 0
MB_Tile_r2_188.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_189
MB_Tile_r2_189.Position 0.000000 6.129989 -4.709751
MB_Tile_r2_189.Rotation 322.464455 0 0
MB_Tile_r2_189.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_190
MB_Tile_r2_190.Position 0.000000 6.267499 -4.525151
MB_Tile_r2_190.Rotation 324.170616 0 0
MB_Tile_r2_190.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_191
MB_Tile_r2_191.Position 0.000000 6.399451 -4.336538
MB_Tile_r2_191.Rotation 325.876777 0 0
MB_Tile_r2_191.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_192
MB_Tile_r2_192.Position 0.000000 6.525728 -4.144080
MB_Tile_r2_192.Rotation 327.582938 0 0
MB_Tile_r2_192.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_193
MB_Tile_r2_193.Position 0.000000 6.646220 -3.947947
MB_Tile_r2_193.Rotation 329.289100 0 0
MB_Tile_r2_193.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_194
MB_Tile_r2_194.Position 0.000000 6.760819 -3.748314
MB_Tile_r2_194.Rotation 330.995261 0 0
MB_Tile_r2_194.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_195
MB_Tile_r2_195.Position 0.000000 6.869423 -3.545357
MB_Tile_r2_195.Rotation 332.701422 0 0
MB_Tile_r2_195.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_196
MB_Tile_r2_196.Position 0.000000 6.971936 -3.339257
MB_Tile_r2_196.Rotation 334.407583 0 0
MB_Tile_r2_196.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_197
MB_Tile_r2_197.Position 0.000000 7.068267 -3.130196
MB_Tile_r2_197.Rotation 336.113744 0 0
MB_Tile_r2_197.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_198
MB_Tile_r2_198.Position 0.000000 7.158331 -2.918360
MB_Tile_r2_198.Rotation 337.819905 0 0
MB_Tile_r2_198.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_199
MB_Tile_r2_199.Position 0.000000 7.242048 -2.703936
MB_Tile_r2_199.Rotation 339.526066 0 0
MB_Tile_r2_199.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_200
MB_Tile_r2_200.Position 0.000000 7.319343 -2.487115
MB_Tile_r2_200.Rotation 341.232227 0 0
MB_Tile_r2_200.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_201
MB_Tile_r2_201.Position 0.000000 7.390149 -2.268088
MB_Tile_r2_201.Rotation 342.938389 0 0
MB_Tile_r2_201.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_202
MB_Tile_r2_202.Position 0.000000 7.454402 -2.047050
MB_Tile_r2_202.Rotation 344.644550 0 0
MB_Tile_r2_202.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_203
MB_Tile_r2_203.Position 0.000000 7.512046 -1.824197
MB_Tile_r2_203.Rotation 346.350711 0 0
MB_Tile_r2_203.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_204
MB_Tile_r2_204.Position 0.000000 7.563029 -1.599727
MB_Tile_r2_204.Rotation 348.056872 0 0
MB_Tile_r2_204.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_205
MB_Tile_r2_205.Position 0.000000 7.607305 -1.373838
MB_Tile_r2_205.Rotation 349.763033 0 0
MB_Tile_r2_205.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_206
MB_Tile_r2_206.Position 0.000000 7.644837 -1.146731
MB_Tile_r2_206.Rotation 351.469194 0 0
MB_Tile_r2_206.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_207
MB_Tile_r2_207.Position 0.000000 7.675590 -0.918607
MB_Tile_r2_207.Rotation 353.175355 0 0
MB_Tile_r2_207.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_208
MB_Tile_r2_208.Position 0.000000 7.699538 -0.689669
MB_Tile_r2_208.Rotation 354.881517 0 0
MB_Tile_r2_208.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_209
MB_Tile_r2_209.Position 0.000000 7.716658 -0.460119
MB_Tile_r2_209.Rotation 356.587678 0 0
MB_Tile_r2_209.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r2_210
MB_Tile_r2_210.Position 0.000000 7.726937 -0.230162
MB_Tile_r2_210.Rotation 358.293839 0 0
MB_Tile_r2_210.Mother InstrumentFrame

// ring 3: E=511.0 keV, r=7.427793 cm, 202 tiles
MB_Tile.Copy MB_Tile_r3_000
MB_Tile_r3_000.Position 0.000000 7.427793 0.000000
MB_Tile_r3_000.Rotation 0.000000 0 0
MB_Tile_r3_000.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_001
MB_Tile_r3_001.Position 0.000000 7.424200 0.231003
MB_Tile_r3_001.Rotation 1.782178 0 0
MB_Tile_r3_001.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_002
MB_Tile_r3_002.Position 0.000000 7.413425 0.461783
MB_Tile_r3_002.Rotation 3.564356 0 0
MB_Tile_r3_002.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_003
MB_Tile_r3_003.Position 0.000000 7.395477 0.692116
MB_Tile_r3_003.Rotation 5.346535 0 0
MB_Tile_r3_003.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_004
MB_Tile_r3_004.Position 0.000000 7.370375 0.921780
MB_Tile_r3_004.Rotation 7.128713 0 0
MB_Tile_r3_004.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_005
MB_Tile_r3_005.Position 0.000000 7.338143 1.150552
MB_Tile_r3_005.Rotation 8.910891 0 0
MB_Tile_r3_005.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_006
MB_Tile_r3_006.Position 0.000000 7.298811 1.378210
MB_Tile_r3_006.Rotation 10.693069 0 0
MB_Tile_r3_006.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_007
MB_Tile_r3_007.Position 0.000000 7.252418 1.604536
MB_Tile_r3_007.Rotation 12.475248 0 0
MB_Tile_r3_007.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_008
MB_Tile_r3_008.Position 0.000000 7.199009 1.829309
MB_Tile_r3_008.Rotation 14.257426 0 0
MB_Tile_r3_008.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_009
MB_Tile_r3_009.Position 0.000000 7.138636 2.052312
MB_Tile_r3_009.Rotation 16.039604 0 0
MB_Tile_r3_009.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_010
MB_Tile_r3_010.Position 0.000000 7.071356 2.273330
MB_Tile_r3_010.Rotation 17.821782 0 0
MB_Tile_r3_010.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_011
MB_Tile_r3_011.Position 0.000000 6.997235 2.492148
MB_Tile_r3_011.Rotation 19.603960 0 0
MB_Tile_r3_011.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_012
MB_Tile_r3_012.Position 0.000000 6.916345 2.708556
MB_Tile_r3_012.Rotation 21.386139 0 0
MB_Tile_r3_012.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_013
MB_Tile_r3_013.Position 0.000000 6.828764 2.922343
MB_Tile_r3_013.Rotation 23.168317 0 0
MB_Tile_r3_013.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_014
MB_Tile_r3_014.Position 0.000000 6.734576 3.133303
MB_Tile_r3_014.Rotation 24.950495 0 0
MB_Tile_r3_014.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_015
MB_Tile_r3_015.Position 0.000000 6.633873 3.341232
MB_Tile_r3_015.Rotation 26.732673 0 0
MB_Tile_r3_015.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_016
MB_Tile_r3_016.Position 0.000000 6.526753 3.545928
MB_Tile_r3_016.Rotation 28.514851 0 0
MB_Tile_r3_016.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_017
MB_Tile_r3_017.Position 0.000000 6.413318 3.747194
MB_Tile_r3_017.Rotation 30.297030 0 0
MB_Tile_r3_017.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_018
MB_Tile_r3_018.Position 0.000000 6.293678 3.944835
MB_Tile_r3_018.Rotation 32.079208 0 0
MB_Tile_r3_018.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_019
MB_Tile_r3_019.Position 0.000000 6.167950 4.138659
MB_Tile_r3_019.Rotation 33.861386 0 0
MB_Tile_r3_019.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_020
MB_Tile_r3_020.Position 0.000000 6.036255 4.328480
MB_Tile_r3_020.Rotation 35.643564 0 0
MB_Tile_r3_020.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_021
MB_Tile_r3_021.Position 0.000000 5.898720 4.514113
MB_Tile_r3_021.Rotation 37.425743 0 0
MB_Tile_r3_021.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_022
MB_Tile_r3_022.Position 0.000000 5.755478 4.695378
MB_Tile_r3_022.Rotation 39.207921 0 0
MB_Tile_r3_022.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_023
MB_Tile_r3_023.Position 0.000000 5.606668 4.872102
MB_Tile_r3_023.Rotation 40.990099 0 0
MB_Tile_r3_023.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_024
MB_Tile_r3_024.Position 0.000000 5.452435 5.044112
MB_Tile_r3_024.Rotation 42.772277 0 0
MB_Tile_r3_024.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_025
MB_Tile_r3_025.Position 0.000000 5.292926 5.211242
MB_Tile_r3_025.Rotation 44.554455 0 0
MB_Tile_r3_025.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_026
MB_Tile_r3_026.Position 0.000000 5.128297 5.373330
MB_Tile_r3_026.Rotation 46.336634 0 0
MB_Tile_r3_026.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_027
MB_Tile_r3_027.Position 0.000000 4.958706 5.530220
MB_Tile_r3_027.Rotation 48.118812 0 0
MB_Tile_r3_027.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_028
MB_Tile_r3_028.Position 0.000000 4.784319 5.681760
MB_Tile_r3_028.Rotation 49.900990 0 0
MB_Tile_r3_028.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_029
MB_Tile_r3_029.Position 0.000000 4.605303 5.827804
MB_Tile_r3_029.Rotation 51.683168 0 0
MB_Tile_r3_029.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_030
MB_Tile_r3_030.Position 0.000000 4.421831 5.968209
MB_Tile_r3_030.Rotation 53.465347 0 0
MB_Tile_r3_030.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_031
MB_Tile_r3_031.Position 0.000000 4.234082 6.102840
MB_Tile_r3_031.Rotation 55.247525 0 0
MB_Tile_r3_031.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_032
MB_Tile_r3_032.Position 0.000000 4.042236 6.231568
MB_Tile_r3_032.Rotation 57.029703 0 0
MB_Tile_r3_032.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_033
MB_Tile_r3_033.Position 0.000000 3.846480 6.354266
MB_Tile_r3_033.Rotation 58.811881 0 0
MB_Tile_r3_033.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_034
MB_Tile_r3_034.Position 0.000000 3.647002 6.470818
MB_Tile_r3_034.Rotation 60.594059 0 0
MB_Tile_r3_034.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_035
MB_Tile_r3_035.Position 0.000000 3.443997 6.581109
MB_Tile_r3_035.Rotation 62.376238 0 0
MB_Tile_r3_035.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_036
MB_Tile_r3_036.Position 0.000000 3.237659 6.685033
MB_Tile_r3_036.Rotation 64.158416 0 0
MB_Tile_r3_036.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_037
MB_Tile_r3_037.Position 0.000000 3.028189 6.782490
MB_Tile_r3_037.Rotation 65.940594 0 0
MB_Tile_r3_037.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_038
MB_Tile_r3_038.Position 0.000000 2.815790 6.873386
MB_Tile_r3_038.Rotation 67.722772 0 0
MB_Tile_r3_038.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_039
MB_Tile_r3_039.Position 0.000000 2.600667 6.957632
MB_Tile_r3_039.Rotation 69.504950 0 0
MB_Tile_r3_039.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_040
MB_Tile_r3_040.Position 0.000000 2.383027 7.035147
MB_Tile_r3_040.Rotation 71.287129 0 0
MB_Tile_r3_040.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_041
MB_Tile_r3_041.Position 0.000000 2.163083 7.105855
MB_Tile_r3_041.Rotation 73.069307 0 0
MB_Tile_r3_041.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_042
MB_Tile_r3_042.Position 0.000000 1.941045 7.169690
MB_Tile_r3_042.Rotation 74.851485 0 0
MB_Tile_r3_042.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_043
MB_Tile_r3_043.Position 0.000000 1.717130 7.226588
MB_Tile_r3_043.Rotation 76.633663 0 0
MB_Tile_r3_043.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_044
MB_Tile_r3_044.Position 0.000000 1.491553 7.276495
MB_Tile_r3_044.Rotation 78.415842 0 0
MB_Tile_r3_044.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_045
MB_Tile_r3_045.Position 0.000000 1.264534 7.319362
MB_Tile_r3_045.Rotation 80.198020 0 0
MB_Tile_r3_045.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_046
MB_Tile_r3_046.Position 0.000000 1.036291 7.355148
MB_Tile_r3_046.Rotation 81.980198 0 0
MB_Tile_r3_046.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_047
MB_Tile_r3_047.Position 0.000000 0.807046 7.383819
MB_Tile_r3_047.Rotation 83.762376 0 0
MB_Tile_r3_047.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_048
MB_Tile_r3_048.Position 0.000000 0.577020 7.405346
MB_Tile_r3_048.Rotation 85.544554 0 0
MB_Tile_r3_048.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_049
MB_Tile_r3_049.Position 0.000000 0.346435 7.419710
MB_Tile_r3_049.Rotation 87.326733 0 0
MB_Tile_r3_049.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_050
MB_Tile_r3_050.Position 0.000000 0.115516 7.426895
MB_Tile_r3_050.Rotation 89.108911 0 0
MB_Tile_r3_050.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_051
MB_Tile_r3_051.Position 0.000000 -0.115516 7.426895
MB_Tile_r3_051.Rotation 90.891089 0 0
MB_Tile_r3_051.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_052
MB_Tile_r3_052.Position 0.000000 -0.346435 7.419710
MB_Tile_r3_052.Rotation 92.673267 0 0
MB_Tile_r3_052.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_053
MB_Tile_r3_053.Position 0.000000 -0.577020 7.405346
MB_Tile_r3_053.Rotation 94.455446 0 0
MB_Tile_r3_053.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_054
MB_Tile_r3_054.Position 0.000000 -0.807046 7.383819
MB_Tile_r3_054.Rotation 96.237624 0 0
MB_Tile_r3_054.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_055
MB_Tile_r3_055.Position 0.000000 -1.036291 7.355148
MB_Tile_r3_055.Rotation 98.019802 0 0
MB_Tile_r3_055.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_056
MB_Tile_r3_056.Position 0.000000 -1.264534 7.319362
MB_Tile_r3_056.Rotation 99.801980 0 0
MB_Tile_r3_056.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_057
MB_Tile_r3_057.Position 0.000000 -1.491553 7.276495
MB_Tile_r3_057.Rotation 101.584158 0 0
MB_Tile_r3_057.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_058
MB_Tile_r3_058.Position 0.000000 -1.717130 7.226588
MB_Tile_r3_058.Rotation 103.366337 0 0
MB_Tile_r3_058.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_059
MB_Tile_r3_059.Position 0.000000 -1.941045 7.169690
MB_Tile_r3_059.Rotation 105.148515 0 0
MB_Tile_r3_059.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_060
MB_Tile_r3_060.Position 0.000000 -2.163083 7.105855
MB_Tile_r3_060.Rotation 106.930693 0 0
MB_Tile_r3_060.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_061
MB_Tile_r3_061.Position 0.000000 -2.383027 7.035147
MB_Tile_r3_061.Rotation 108.712871 0 0
MB_Tile_r3_061.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_062
MB_Tile_r3_062.Position 0.000000 -2.600667 6.957632
MB_Tile_r3_062.Rotation 110.495050 0 0
MB_Tile_r3_062.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_063
MB_Tile_r3_063.Position 0.000000 -2.815790 6.873386
MB_Tile_r3_063.Rotation 112.277228 0 0
MB_Tile_r3_063.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_064
MB_Tile_r3_064.Position 0.000000 -3.028189 6.782490
MB_Tile_r3_064.Rotation 114.059406 0 0
MB_Tile_r3_064.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_065
MB_Tile_r3_065.Position 0.000000 -3.237659 6.685033
MB_Tile_r3_065.Rotation 115.841584 0 0
MB_Tile_r3_065.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_066
MB_Tile_r3_066.Position 0.000000 -3.443997 6.581109
MB_Tile_r3_066.Rotation 117.623762 0 0
MB_Tile_r3_066.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_067
MB_Tile_r3_067.Position 0.000000 -3.647002 6.470818
MB_Tile_r3_067.Rotation 119.405941 0 0
MB_Tile_r3_067.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_068
MB_Tile_r3_068.Position 0.000000 -3.846480 6.354266
MB_Tile_r3_068.Rotation 121.188119 0 0
MB_Tile_r3_068.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_069
MB_Tile_r3_069.Position 0.000000 -4.042236 6.231568
MB_Tile_r3_069.Rotation 122.970297 0 0
MB_Tile_r3_069.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_070
MB_Tile_r3_070.Position 0.000000 -4.234082 6.102840
MB_Tile_r3_070.Rotation 124.752475 0 0
MB_Tile_r3_070.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_071
MB_Tile_r3_071.Position 0.000000 -4.421831 5.968209
MB_Tile_r3_071.Rotation 126.534653 0 0
MB_Tile_r3_071.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_072
MB_Tile_r3_072.Position 0.000000 -4.605303 5.827804
MB_Tile_r3_072.Rotation 128.316832 0 0
MB_Tile_r3_072.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_073
MB_Tile_r3_073.Position 0.000000 -4.784319 5.681760
MB_Tile_r3_073.Rotation 130.099010 0 0
MB_Tile_r3_073.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_074
MB_Tile_r3_074.Position 0.000000 -4.958706 5.530220
MB_Tile_r3_074.Rotation 131.881188 0 0
MB_Tile_r3_074.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_075
MB_Tile_r3_075.Position 0.000000 -5.128297 5.373330
MB_Tile_r3_075.Rotation 133.663366 0 0
MB_Tile_r3_075.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_076
MB_Tile_r3_076.Position 0.000000 -5.292926 5.211242
MB_Tile_r3_076.Rotation 135.445545 0 0
MB_Tile_r3_076.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_077
MB_Tile_r3_077.Position 0.000000 -5.452435 5.044112
MB_Tile_r3_077.Rotation 137.227723 0 0
MB_Tile_r3_077.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_078
MB_Tile_r3_078.Position 0.000000 -5.606668 4.872102
MB_Tile_r3_078.Rotation 139.009901 0 0
MB_Tile_r3_078.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_079
MB_Tile_r3_079.Position 0.000000 -5.755478 4.695378
MB_Tile_r3_079.Rotation 140.792079 0 0
MB_Tile_r3_079.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_080
MB_Tile_r3_080.Position 0.000000 -5.898720 4.514113
MB_Tile_r3_080.Rotation 142.574257 0 0
MB_Tile_r3_080.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_081
MB_Tile_r3_081.Position 0.000000 -6.036255 4.328480
MB_Tile_r3_081.Rotation 144.356436 0 0
MB_Tile_r3_081.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_082
MB_Tile_r3_082.Position 0.000000 -6.167950 4.138659
MB_Tile_r3_082.Rotation 146.138614 0 0
MB_Tile_r3_082.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_083
MB_Tile_r3_083.Position 0.000000 -6.293678 3.944835
MB_Tile_r3_083.Rotation 147.920792 0 0
MB_Tile_r3_083.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_084
MB_Tile_r3_084.Position 0.000000 -6.413318 3.747194
MB_Tile_r3_084.Rotation 149.702970 0 0
MB_Tile_r3_084.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_085
MB_Tile_r3_085.Position 0.000000 -6.526753 3.545928
MB_Tile_r3_085.Rotation 151.485149 0 0
MB_Tile_r3_085.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_086
MB_Tile_r3_086.Position 0.000000 -6.633873 3.341232
MB_Tile_r3_086.Rotation 153.267327 0 0
MB_Tile_r3_086.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_087
MB_Tile_r3_087.Position 0.000000 -6.734576 3.133303
MB_Tile_r3_087.Rotation 155.049505 0 0
MB_Tile_r3_087.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_088
MB_Tile_r3_088.Position 0.000000 -6.828764 2.922343
MB_Tile_r3_088.Rotation 156.831683 0 0
MB_Tile_r3_088.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_089
MB_Tile_r3_089.Position 0.000000 -6.916345 2.708556
MB_Tile_r3_089.Rotation 158.613861 0 0
MB_Tile_r3_089.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_090
MB_Tile_r3_090.Position 0.000000 -6.997235 2.492148
MB_Tile_r3_090.Rotation 160.396040 0 0
MB_Tile_r3_090.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_091
MB_Tile_r3_091.Position 0.000000 -7.071356 2.273330
MB_Tile_r3_091.Rotation 162.178218 0 0
MB_Tile_r3_091.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_092
MB_Tile_r3_092.Position 0.000000 -7.138636 2.052312
MB_Tile_r3_092.Rotation 163.960396 0 0
MB_Tile_r3_092.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_093
MB_Tile_r3_093.Position 0.000000 -7.199009 1.829309
MB_Tile_r3_093.Rotation 165.742574 0 0
MB_Tile_r3_093.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_094
MB_Tile_r3_094.Position 0.000000 -7.252418 1.604536
MB_Tile_r3_094.Rotation 167.524752 0 0
MB_Tile_r3_094.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_095
MB_Tile_r3_095.Position 0.000000 -7.298811 1.378210
MB_Tile_r3_095.Rotation 169.306931 0 0
MB_Tile_r3_095.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_096
MB_Tile_r3_096.Position 0.000000 -7.338143 1.150552
MB_Tile_r3_096.Rotation 171.089109 0 0
MB_Tile_r3_096.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_097
MB_Tile_r3_097.Position 0.000000 -7.370375 0.921780
MB_Tile_r3_097.Rotation 172.871287 0 0
MB_Tile_r3_097.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_098
MB_Tile_r3_098.Position 0.000000 -7.395477 0.692116
MB_Tile_r3_098.Rotation 174.653465 0 0
MB_Tile_r3_098.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_099
MB_Tile_r3_099.Position 0.000000 -7.413425 0.461783
MB_Tile_r3_099.Rotation 176.435644 0 0
MB_Tile_r3_099.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_100
MB_Tile_r3_100.Position 0.000000 -7.424200 0.231003
MB_Tile_r3_100.Rotation 178.217822 0 0
MB_Tile_r3_100.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_101
MB_Tile_r3_101.Position 0.000000 -7.427793 0.000000
MB_Tile_r3_101.Rotation 180.000000 0 0
MB_Tile_r3_101.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_102
MB_Tile_r3_102.Position 0.000000 -7.424200 -0.231003
MB_Tile_r3_102.Rotation 181.782178 0 0
MB_Tile_r3_102.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_103
MB_Tile_r3_103.Position 0.000000 -7.413425 -0.461783
MB_Tile_r3_103.Rotation 183.564356 0 0
MB_Tile_r3_103.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_104
MB_Tile_r3_104.Position 0.000000 -7.395477 -0.692116
MB_Tile_r3_104.Rotation 185.346535 0 0
MB_Tile_r3_104.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_105
MB_Tile_r3_105.Position 0.000000 -7.370375 -0.921780
MB_Tile_r3_105.Rotation 187.128713 0 0
MB_Tile_r3_105.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_106
MB_Tile_r3_106.Position 0.000000 -7.338143 -1.150552
MB_Tile_r3_106.Rotation 188.910891 0 0
MB_Tile_r3_106.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_107
MB_Tile_r3_107.Position 0.000000 -7.298811 -1.378210
MB_Tile_r3_107.Rotation 190.693069 0 0
MB_Tile_r3_107.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_108
MB_Tile_r3_108.Position 0.000000 -7.252418 -1.604536
MB_Tile_r3_108.Rotation 192.475248 0 0
MB_Tile_r3_108.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_109
MB_Tile_r3_109.Position 0.000000 -7.199009 -1.829309
MB_Tile_r3_109.Rotation 194.257426 0 0
MB_Tile_r3_109.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_110
MB_Tile_r3_110.Position 0.000000 -7.138636 -2.052312
MB_Tile_r3_110.Rotation 196.039604 0 0
MB_Tile_r3_110.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_111
MB_Tile_r3_111.Position 0.000000 -7.071356 -2.273330
MB_Tile_r3_111.Rotation 197.821782 0 0
MB_Tile_r3_111.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_112
MB_Tile_r3_112.Position 0.000000 -6.997235 -2.492148
MB_Tile_r3_112.Rotation 199.603960 0 0
MB_Tile_r3_112.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_113
MB_Tile_r3_113.Position 0.000000 -6.916345 -2.708556
MB_Tile_r3_113.Rotation 201.386139 0 0
MB_Tile_r3_113.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_114
MB_Tile_r3_114.Position 0.000000 -6.828764 -2.922343
MB_Tile_r3_114.Rotation 203.168317 0 0
MB_Tile_r3_114.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_115
MB_Tile_r3_115.Position 0.000000 -6.734576 -3.133303
MB_Tile_r3_115.Rotation 204.950495 0 0
MB_Tile_r3_115.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_116
MB_Tile_r3_116.Position 0.000000 -6.633873 -3.341232
MB_Tile_r3_116.Rotation 206.732673 0 0
MB_Tile_r3_116.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_117
MB_Tile_r3_117.Position 0.000000 -6.526753 -3.545928
MB_Tile_r3_117.Rotation 208.514851 0 0
MB_Tile_r3_117.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_118
MB_Tile_r3_118.Position 0.000000 -6.413318 -3.747194
MB_Tile_r3_118.Rotation 210.297030 0 0
MB_Tile_r3_118.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_119
MB_Tile_r3_119.Position 0.000000 -6.293678 -3.944835
MB_Tile_r3_119.Rotation 212.079208 0 0
MB_Tile_r3_119.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_120
MB_Tile_r3_120.Position 0.000000 -6.167950 -4.138659
MB_Tile_r3_120.Rotation 213.861386 0 0
MB_Tile_r3_120.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_121
MB_Tile_r3_121.Position 0.000000 -6.036255 -4.328480
MB_Tile_r3_121.Rotation 215.643564 0 0
MB_Tile_r3_121.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_122
MB_Tile_r3_122.Position 0.000000 -5.898720 -4.514113
MB_Tile_r3_122.Rotation 217.425743 0 0
MB_Tile_r3_122.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_123
MB_Tile_r3_123.Position 0.000000 -5.755478 -4.695378
MB_Tile_r3_123.Rotation 219.207921 0 0
MB_Tile_r3_123.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_124
MB_Tile_r3_124.Position 0.000000 -5.606668 -4.872102
MB_Tile_r3_124.Rotation 220.990099 0 0
MB_Tile_r3_124.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_125
MB_Tile_r3_125.Position 0.000000 -5.452435 -5.044112
MB_Tile_r3_125.Rotation 222.772277 0 0
MB_Tile_r3_125.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_126
MB_Tile_r3_126.Position 0.000000 -5.292926 -5.211242
MB_Tile_r3_126.Rotation 224.554455 0 0
MB_Tile_r3_126.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_127
MB_Tile_r3_127.Position 0.000000 -5.128297 -5.373330
MB_Tile_r3_127.Rotation 226.336634 0 0
MB_Tile_r3_127.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_128
MB_Tile_r3_128.Position 0.000000 -4.958706 -5.530220
MB_Tile_r3_128.Rotation 228.118812 0 0
MB_Tile_r3_128.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_129
MB_Tile_r3_129.Position 0.000000 -4.784319 -5.681760
MB_Tile_r3_129.Rotation 229.900990 0 0
MB_Tile_r3_129.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_130
MB_Tile_r3_130.Position 0.000000 -4.605303 -5.827804
MB_Tile_r3_130.Rotation 231.683168 0 0
MB_Tile_r3_130.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_131
MB_Tile_r3_131.Position 0.000000 -4.421831 -5.968209
MB_Tile_r3_131.Rotation 233.465347 0 0
MB_Tile_r3_131.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_132
MB_Tile_r3_132.Position 0.000000 -4.234082 -6.102840
MB_Tile_r3_132.Rotation 235.247525 0 0
MB_Tile_r3_132.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_133
MB_Tile_r3_133.Position 0.000000 -4.042236 -6.231568
MB_Tile_r3_133.Rotation 237.029703 0 0
MB_Tile_r3_133.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_134
MB_Tile_r3_134.Position 0.000000 -3.846480 -6.354266
MB_Tile_r3_134.Rotation 238.811881 0 0
MB_Tile_r3_134.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_135
MB_Tile_r3_135.Position 0.000000 -3.647002 -6.470818
MB_Tile_r3_135.Rotation 240.594059 0 0
MB_Tile_r3_135.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_136
MB_Tile_r3_136.Position 0.000000 -3.443997 -6.581109
MB_Tile_r3_136.Rotation 242.376238 0 0
MB_Tile_r3_136.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_137
MB_Tile_r3_137.Position 0.000000 -3.237659 -6.685033
MB_Tile_r3_137.Rotation 244.158416 0 0
MB_Tile_r3_137.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_138
MB_Tile_r3_138.Position 0.000000 -3.028189 -6.782490
MB_Tile_r3_138.Rotation 245.940594 0 0
MB_Tile_r3_138.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_139
MB_Tile_r3_139.Position 0.000000 -2.815790 -6.873386
MB_Tile_r3_139.Rotation 247.722772 0 0
MB_Tile_r3_139.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_140
MB_Tile_r3_140.Position 0.000000 -2.600667 -6.957632
MB_Tile_r3_140.Rotation 249.504950 0 0
MB_Tile_r3_140.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_141
MB_Tile_r3_141.Position 0.000000 -2.383027 -7.035147
MB_Tile_r3_141.Rotation 251.287129 0 0
MB_Tile_r3_141.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_142
MB_Tile_r3_142.Position 0.000000 -2.163083 -7.105855
MB_Tile_r3_142.Rotation 253.069307 0 0
MB_Tile_r3_142.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_143
MB_Tile_r3_143.Position 0.000000 -1.941045 -7.169690
MB_Tile_r3_143.Rotation 254.851485 0 0
MB_Tile_r3_143.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_144
MB_Tile_r3_144.Position 0.000000 -1.717130 -7.226588
MB_Tile_r3_144.Rotation 256.633663 0 0
MB_Tile_r3_144.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_145
MB_Tile_r3_145.Position 0.000000 -1.491553 -7.276495
MB_Tile_r3_145.Rotation 258.415842 0 0
MB_Tile_r3_145.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_146
MB_Tile_r3_146.Position 0.000000 -1.264534 -7.319362
MB_Tile_r3_146.Rotation 260.198020 0 0
MB_Tile_r3_146.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_147
MB_Tile_r3_147.Position 0.000000 -1.036291 -7.355148
MB_Tile_r3_147.Rotation 261.980198 0 0
MB_Tile_r3_147.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_148
MB_Tile_r3_148.Position 0.000000 -0.807046 -7.383819
MB_Tile_r3_148.Rotation 263.762376 0 0
MB_Tile_r3_148.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_149
MB_Tile_r3_149.Position 0.000000 -0.577020 -7.405346
MB_Tile_r3_149.Rotation 265.544554 0 0
MB_Tile_r3_149.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_150
MB_Tile_r3_150.Position 0.000000 -0.346435 -7.419710
MB_Tile_r3_150.Rotation 267.326733 0 0
MB_Tile_r3_150.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_151
MB_Tile_r3_151.Position 0.000000 -0.115516 -7.426895
MB_Tile_r3_151.Rotation 269.108911 0 0
MB_Tile_r3_151.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_152
MB_Tile_r3_152.Position 0.000000 0.115516 -7.426895
MB_Tile_r3_152.Rotation 270.891089 0 0
MB_Tile_r3_152.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_153
MB_Tile_r3_153.Position 0.000000 0.346435 -7.419710
MB_Tile_r3_153.Rotation 272.673267 0 0
MB_Tile_r3_153.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_154
MB_Tile_r3_154.Position 0.000000 0.577020 -7.405346
MB_Tile_r3_154.Rotation 274.455446 0 0
MB_Tile_r3_154.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_155
MB_Tile_r3_155.Position 0.000000 0.807046 -7.383819
MB_Tile_r3_155.Rotation 276.237624 0 0
MB_Tile_r3_155.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_156
MB_Tile_r3_156.Position 0.000000 1.036291 -7.355148
MB_Tile_r3_156.Rotation 278.019802 0 0
MB_Tile_r3_156.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_157
MB_Tile_r3_157.Position 0.000000 1.264534 -7.319362
MB_Tile_r3_157.Rotation 279.801980 0 0
MB_Tile_r3_157.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_158
MB_Tile_r3_158.Position 0.000000 1.491553 -7.276495
MB_Tile_r3_158.Rotation 281.584158 0 0
MB_Tile_r3_158.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_159
MB_Tile_r3_159.Position 0.000000 1.717130 -7.226588
MB_Tile_r3_159.Rotation 283.366337 0 0
MB_Tile_r3_159.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_160
MB_Tile_r3_160.Position 0.000000 1.941045 -7.169690
MB_Tile_r3_160.Rotation 285.148515 0 0
MB_Tile_r3_160.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_161
MB_Tile_r3_161.Position 0.000000 2.163083 -7.105855
MB_Tile_r3_161.Rotation 286.930693 0 0
MB_Tile_r3_161.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_162
MB_Tile_r3_162.Position 0.000000 2.383027 -7.035147
MB_Tile_r3_162.Rotation 288.712871 0 0
MB_Tile_r3_162.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_163
MB_Tile_r3_163.Position 0.000000 2.600667 -6.957632
MB_Tile_r3_163.Rotation 290.495050 0 0
MB_Tile_r3_163.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_164
MB_Tile_r3_164.Position 0.000000 2.815790 -6.873386
MB_Tile_r3_164.Rotation 292.277228 0 0
MB_Tile_r3_164.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_165
MB_Tile_r3_165.Position 0.000000 3.028189 -6.782490
MB_Tile_r3_165.Rotation 294.059406 0 0
MB_Tile_r3_165.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_166
MB_Tile_r3_166.Position 0.000000 3.237659 -6.685033
MB_Tile_r3_166.Rotation 295.841584 0 0
MB_Tile_r3_166.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_167
MB_Tile_r3_167.Position 0.000000 3.443997 -6.581109
MB_Tile_r3_167.Rotation 297.623762 0 0
MB_Tile_r3_167.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_168
MB_Tile_r3_168.Position 0.000000 3.647002 -6.470818
MB_Tile_r3_168.Rotation 299.405941 0 0
MB_Tile_r3_168.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_169
MB_Tile_r3_169.Position 0.000000 3.846480 -6.354266
MB_Tile_r3_169.Rotation 301.188119 0 0
MB_Tile_r3_169.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_170
MB_Tile_r3_170.Position 0.000000 4.042236 -6.231568
MB_Tile_r3_170.Rotation 302.970297 0 0
MB_Tile_r3_170.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_171
MB_Tile_r3_171.Position 0.000000 4.234082 -6.102840
MB_Tile_r3_171.Rotation 304.752475 0 0
MB_Tile_r3_171.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_172
MB_Tile_r3_172.Position 0.000000 4.421831 -5.968209
MB_Tile_r3_172.Rotation 306.534653 0 0
MB_Tile_r3_172.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_173
MB_Tile_r3_173.Position 0.000000 4.605303 -5.827804
MB_Tile_r3_173.Rotation 308.316832 0 0
MB_Tile_r3_173.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_174
MB_Tile_r3_174.Position 0.000000 4.784319 -5.681760
MB_Tile_r3_174.Rotation 310.099010 0 0
MB_Tile_r3_174.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_175
MB_Tile_r3_175.Position 0.000000 4.958706 -5.530220
MB_Tile_r3_175.Rotation 311.881188 0 0
MB_Tile_r3_175.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_176
MB_Tile_r3_176.Position 0.000000 5.128297 -5.373330
MB_Tile_r3_176.Rotation 313.663366 0 0
MB_Tile_r3_176.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_177
MB_Tile_r3_177.Position 0.000000 5.292926 -5.211242
MB_Tile_r3_177.Rotation 315.445545 0 0
MB_Tile_r3_177.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_178
MB_Tile_r3_178.Position 0.000000 5.452435 -5.044112
MB_Tile_r3_178.Rotation 317.227723 0 0
MB_Tile_r3_178.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_179
MB_Tile_r3_179.Position 0.000000 5.606668 -4.872102
MB_Tile_r3_179.Rotation 319.009901 0 0
MB_Tile_r3_179.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_180
MB_Tile_r3_180.Position 0.000000 5.755478 -4.695378
MB_Tile_r3_180.Rotation 320.792079 0 0
MB_Tile_r3_180.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_181
MB_Tile_r3_181.Position 0.000000 5.898720 -4.514113
MB_Tile_r3_181.Rotation 322.574257 0 0
MB_Tile_r3_181.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_182
MB_Tile_r3_182.Position 0.000000 6.036255 -4.328480
MB_Tile_r3_182.Rotation 324.356436 0 0
MB_Tile_r3_182.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_183
MB_Tile_r3_183.Position 0.000000 6.167950 -4.138659
MB_Tile_r3_183.Rotation 326.138614 0 0
MB_Tile_r3_183.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_184
MB_Tile_r3_184.Position 0.000000 6.293678 -3.944835
MB_Tile_r3_184.Rotation 327.920792 0 0
MB_Tile_r3_184.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_185
MB_Tile_r3_185.Position 0.000000 6.413318 -3.747194
MB_Tile_r3_185.Rotation 329.702970 0 0
MB_Tile_r3_185.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_186
MB_Tile_r3_186.Position 0.000000 6.526753 -3.545928
MB_Tile_r3_186.Rotation 331.485149 0 0
MB_Tile_r3_186.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_187
MB_Tile_r3_187.Position 0.000000 6.633873 -3.341232
MB_Tile_r3_187.Rotation 333.267327 0 0
MB_Tile_r3_187.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_188
MB_Tile_r3_188.Position 0.000000 6.734576 -3.133303
MB_Tile_r3_188.Rotation 335.049505 0 0
MB_Tile_r3_188.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_189
MB_Tile_r3_189.Position 0.000000 6.828764 -2.922343
MB_Tile_r3_189.Rotation 336.831683 0 0
MB_Tile_r3_189.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_190
MB_Tile_r3_190.Position 0.000000 6.916345 -2.708556
MB_Tile_r3_190.Rotation 338.613861 0 0
MB_Tile_r3_190.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_191
MB_Tile_r3_191.Position 0.000000 6.997235 -2.492148
MB_Tile_r3_191.Rotation 340.396040 0 0
MB_Tile_r3_191.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_192
MB_Tile_r3_192.Position 0.000000 7.071356 -2.273330
MB_Tile_r3_192.Rotation 342.178218 0 0
MB_Tile_r3_192.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_193
MB_Tile_r3_193.Position 0.000000 7.138636 -2.052312
MB_Tile_r3_193.Rotation 343.960396 0 0
MB_Tile_r3_193.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_194
MB_Tile_r3_194.Position 0.000000 7.199009 -1.829309
MB_Tile_r3_194.Rotation 345.742574 0 0
MB_Tile_r3_194.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_195
MB_Tile_r3_195.Position 0.000000 7.252418 -1.604536
MB_Tile_r3_195.Rotation 347.524752 0 0
MB_Tile_r3_195.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_196
MB_Tile_r3_196.Position 0.000000 7.298811 -1.378210
MB_Tile_r3_196.Rotation 349.306931 0 0
MB_Tile_r3_196.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_197
MB_Tile_r3_197.Position 0.000000 7.338143 -1.150552
MB_Tile_r3_197.Rotation 351.089109 0 0
MB_Tile_r3_197.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_198
MB_Tile_r3_198.Position 0.000000 7.370375 -0.921780
MB_Tile_r3_198.Rotation 352.871287 0 0
MB_Tile_r3_198.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_199
MB_Tile_r3_199.Position 0.000000 7.395477 -0.692116
MB_Tile_r3_199.Rotation 354.653465 0 0
MB_Tile_r3_199.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_200
MB_Tile_r3_200.Position 0.000000 7.413425 -0.461783
MB_Tile_r3_200.Rotation 356.435644 0 0
MB_Tile_r3_200.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r3_201
MB_Tile_r3_201.Position 0.000000 7.424200 -0.231003
MB_Tile_r3_201.Rotation 358.217822 0 0
MB_Tile_r3_201.Mother InstrumentFrame

// ring 4: E=531.0 keV, r=7.148016 cm, 195 tiles
MB_Tile.Copy MB_Tile_r4_000
MB_Tile_r4_000.Position 0.000000 7.148016 0.000000
MB_Tile_r4_000.Rotation 0.000000 0 0
MB_Tile_r4_000.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_001
MB_Tile_r4_001.Position 0.000000 7.144305 0.230280
MB_Tile_r4_001.Rotation 1.846154 0 0
MB_Tile_r4_001.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_002
MB_Tile_r4_002.Position 0.000000 7.133178 0.460320
MB_Tile_r4_002.Rotation 3.692308 0 0
MB_Tile_r4_002.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_003
MB_Tile_r4_003.Position 0.000000 7.114646 0.689883
MB_Tile_r4_003.Rotation 5.538462 0 0
MB_Tile_r4_003.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_004
MB_Tile_r4_004.Position 0.000000 7.088728 0.918730
MB_Tile_r4_004.Rotation 7.384615 0 0
MB_Tile_r4_004.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_005
MB_Tile_r4_005.Position 0.000000 7.055451 1.146622
MB_Tile_r4_005.Rotation 9.230769 0 0
MB_Tile_r4_005.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_006
MB_Tile_r4_006.Position 0.000000 7.014849 1.373325
MB_Tile_r4_006.Rotation 11.076923 0 0
MB_Tile_r4_006.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_007
MB_Tile_r4_007.Position 0.000000 6.966965 1.598602
MB_Tile_r4_007.Rotation 12.923077 0 0
MB_Tile_r4_007.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_008
MB_Tile_r4_008.Position 0.000000 6.911848 1.822219
MB_Tile_r4_008.Rotation 14.769231 0 0
MB_Tile_r4_008.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_009
MB_Tile_r4_009.Position 0.000000 6.849556 2.043944
MB_Tile_r4_009.Rotation 16.615385 0 0
MB_Tile_r4_009.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_010
MB_Tile_r4_010.Position 0.000000 6.780153 2.263548
MB_Tile_r4_010.Rotation 18.461538 0 0
MB_Tile_r4_010.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_011
MB_Tile_r4_011.Position 0.000000 6.703712 2.480802
MB_Tile_r4_011.Rotation 20.307692 0 0
MB_Tile_r4_011.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_012
MB_Tile_r4_012.Position 0.000000 6.620311 2.695480
MB_Tile_r4_012.Rotation 22.153846 0 0
MB_Tile_r4_012.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_013
MB_Tile_r4_013.Position 0.000000 6.530037 2.907360
MB_Tile_r4_013.Rotation 24.000000 0 0
MB_Tile_r4_013.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_014
MB_Tile_r4_014.Position 0.000000 6.432985 3.116222
MB_Tile_r4_014.Rotation 25.846154 0 0
MB_Tile_r4_014.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_015
MB_Tile_r4_015.Position 0.000000 6.329254 3.321849
MB_Tile_r4_015.Rotation 27.692308 0 0
MB_Tile_r4_015.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_016
MB_Tile_r4_016.Position 0.000000 6.218952 3.524027
MB_Tile_r4_016.Rotation 29.538462 0 0
MB_Tile_r4_016.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_017
MB_Tile_r4_017.Position 0.000000 6.102194 3.722547
MB_Tile_r4_017.Rotation 31.384615 0 0
MB_Tile_r4_017.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_018
MB_Tile_r4_018.Position 0.000000 5.979102 3.917202
MB_Tile_r4_018.Rotation 33.230769 0 0
MB_Tile_r4_018.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_019
MB_Tile_r4_019.Position 0.000000 5.849802 4.107791
MB_Tile_r4_019.Rotation 35.076923 0 0
MB_Tile_r4_019.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_020
MB_Tile_r4_020.Position 0.000000 5.714429 4.294115
MB_Tile_r4_020.Rotation 36.923077 0 0
MB_Tile_r4_020.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_021
MB_Tile_r4_021.Position 0.000000 5.573125 4.475982
MB_Tile_r4_021.Rotation 38.769231 0 0
MB_Tile_r4_021.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_022
MB_Tile_r4_022.Position 0.000000 5.426034 4.653201
MB_Tile_r4_022.Rotation 40.615385 0 0
MB_Tile_r4_022.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_023
MB_Tile_r4_023.Position 0.000000 5.273310 4.825591
MB_Tile_r4_023.Rotation 42.461538 0 0
MB_Tile_r4_023.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_024
MB_Tile_r4_024.Position 0.000000 5.115113 4.992970
MB_Tile_r4_024.Rotation 44.307692 0 0
MB_Tile_r4_024.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_025
MB_Tile_r4_025.Position 0.000000 4.951605 5.155166
MB_Tile_r4_025.Rotation 46.153846 0 0
MB_Tile_r4_025.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_026
MB_Tile_r4_026.Position 0.000000 4.782956 5.312011
MB_Tile_r4_026.Rotation 48.000000 0 0
MB_Tile_r4_026.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_027
MB_Tile_r4_027.Position 0.000000 4.609342 5.463341
MB_Tile_r4_027.Rotation 49.846154 0 0
MB_Tile_r4_027.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_028
MB_Tile_r4_028.Position 0.000000 4.430943 5.608999
MB_Tile_r4_028.Rotation 51.692308 0 0
MB_Tile_r4_028.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_029
MB_Tile_r4_029.Position 0.000000 4.247944 5.748834
MB_Tile_r4_029.Rotation 53.538462 0 0
MB_Tile_r4_029.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_030
MB_Tile_r4_030.Position 0.000000 4.060536 5.882702
MB_Tile_r4_030.Rotation 55.384615 0 0
MB_Tile_r4_030.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_031
MB_Tile_r4_031.Position 0.000000 3.868912 6.010462
MB_Tile_r4_031.Rotation 57.230769 0 0
MB_Tile_r4_031.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_032
MB_Tile_r4_032.Position 0.000000 3.673271 6.131982
MB_Tile_r4_032.Rotation 59.076923 0 0
MB_Tile_r4_032.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_033
MB_Tile_r4_033.Position 0.000000 3.473817 6.247137
MB_Tile_r4_033.Rotation 60.923077 0 0
MB_Tile_r4_033.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_034
MB_Tile_r4_034.Position 0.000000 3.270757 6.355807
MB_Tile_r4_034.Rotation 62.769231 0 0
MB_Tile_r4_034.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_035
MB_Tile_r4_035.Position 0.000000 3.064301 6.457878
MB_Tile_r4_035.Rotation 64.615385 0 0
MB_Tile_r4_035.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_036
MB_Tile_r4_036.Position 0.000000 2.854664 6.553245
MB_Tile_r4_036.Rotation 66.461538 0 0
MB_Tile_r4_036.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_037
MB_Tile_r4_037.Position 0.000000 2.642064 6.641809
MB_Tile_r4_037.Rotation 68.307692 0 0
MB_Tile_r4_037.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_038
MB_Tile_r4_038.Position 0.000000 2.426721 6.723478
MB_Tile_r4_038.Rotation 70.153846 0 0
MB_Tile_r4_038.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_039
MB_Tile_r4_039.Position 0.000000 2.208858 6.798167
MB_Tile_r4_039.Rotation 72.000000 0 0
MB_Tile_r4_039.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_040
MB_Tile_r4_040.Position 0.000000 1.988703 6.865799
MB_Tile_r4_040.Rotation 73.846154 0 0
MB_Tile_r4_040.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_041
MB_Tile_r4_041.Position 0.000000 1.766483 6.926303
MB_Tile_r4_041.Rotation 75.692308 0 0
MB_Tile_r4_041.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_042
MB_Tile_r4_042.Position 0.000000 1.542429 6.979616
MB_Tile_r4_042.Rotation 77.538462 0 0
MB_Tile_r4_042.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_043
MB_Tile_r4_043.Position 0.000000 1.316774 7.025684
MB_Tile_r4_043.Rotation 79.384615 0 0
MB_Tile_r4_043.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_044
MB_Tile_r4_044.Position 0.000000 1.089752 7.064458
MB_Tile_r4_044.Rotation 81.230769 0 0
MB_Tile_r4_044.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_045
MB_Tile_r4_045.Position 0.000000 0.861598 7.095899
MB_Tile_r4_045.Rotation 83.076923 0 0
MB_Tile_r4_045.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_046
MB_Tile_r4_046.Position 0.000000 0.632550 7.119973
MB_Tile_r4_046.Rotation 84.923077 0 0
MB_Tile_r4_046.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_047
MB_Tile_r4_047.Position 0.000000 0.402846 7.136655
MB_Tile_r4_047.Rotation 86.769231 0 0
MB_Tile_r4_047.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_048
MB_Tile_r4_048.Position 0.000000 0.172723 7.145929
MB_Tile_r4_048.Rotation 88.615385 0 0
MB_Tile_r4_048.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_049
MB_Tile_r4_049.Position 0.000000 -0.057579 7.147784
MB_Tile_r4_049.Rotation 90.461538 0 0
MB_Tile_r4_049.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_050
MB_Tile_r4_050.Position 0.000000 -0.287822 7.142219
MB_Tile_r4_050.Rotation 92.307692 0 0
MB_Tile_r4_050.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_051
MB_Tile_r4_051.Position 0.000000 -0.517765 7.129239
MB_Tile_r4_051.Rotation 94.153846 0 0
MB_Tile_r4_051.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_052
MB_Tile_r4_052.Position 0.000000 -0.747171 7.108858
MB_Tile_r4_052.Rotation 96.000000 0 0
MB_Tile_r4_052.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_053
MB_Tile_r4_053.Position 0.000000 -0.975801 7.081097
MB_Tile_r4_053.Rotation 97.846154 0 0
MB_Tile_r4_053.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_054
MB_Tile_r4_054.Position 0.000000 -1.203419 7.045986
MB_Tile_r4_054.Rotation 99.692308 0 0
MB_Tile_r4_054.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_055
MB_Tile_r4_055.Position 0.000000 -1.429787 7.003559
MB_Tile_r4_055.Rotation 101.538462 0 0
MB_Tile_r4_055.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_056
MB_Tile_r4_056.Position 0.000000 -1.654671 6.953862
MB_Tile_r4_056.Rotation 103.384615 0 0
MB_Tile_r4_056.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_057
MB_Tile_r4_057.Position 0.000000 -1.877836 6.896946
MB_Tile_r4_057.Rotation 105.230769 0 0
MB_Tile_r4_057.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_058
MB_Tile_r4_058.Position 0.000000 -2.099053 6.832869
MB_Tile_r4_058.Rotation 107.076923 0 0
MB_Tile_r4_058.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_059
MB_Tile_r4_059.Position 0.000000 -2.318090 6.761700
MB_Tile_r4_059.Rotation 108.923077 0 0
MB_Tile_r4_059.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_060
MB_Tile_r4_060.Position 0.000000 -2.534721 6.683511
MB_Tile_r4_060.Rotation 110.769231 0 0
MB_Tile_r4_060.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_061
MB_Tile_r4_061.Position 0.000000 -2.748721 6.598383
MB_Tile_r4_061.Rotation 112.615385 0 0
MB_Tile_r4_061.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_062
MB_Tile_r4_062.Position 0.000000 -2.959867 6.506406
MB_Tile_r4_062.Rotation 114.461538 0 0
MB_Tile_r4_062.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_063
MB_Tile_r4_063.Position 0.000000 -3.167940 6.407674
MB_Tile_r4_063.Rotation 116.307692 0 0
MB_Tile_r4_063.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_064
MB_Tile_r4_064.Position 0.000000 -3.372725 6.302290
MB_Tile_r4_064.Rotation 118.153846 0 0
MB_Tile_r4_064.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_065
MB_Tile_r4_065.Position 0.000000 -3.574008 6.190363
MB_Tile_r4_065.Rotation 120.000000 0 0
MB_Tile_r4_065.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_066
MB_Tile_r4_066.Position 0.000000 -3.771581 6.072010
MB_Tile_r4_066.Rotation 121.846154 0 0
MB_Tile_r4_066.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_067
MB_Tile_r4_067.Position 0.000000 -3.965238 5.947354
MB_Tile_r4_067.Rotation 123.692308 0 0
MB_Tile_r4_067.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_068
MB_Tile_r4_068.Position 0.000000 -4.154779 5.816523
MB_Tile_r4_068.Rotation 125.538462 0 0
MB_Tile_r4_068.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_069
MB_Tile_r4_069.Position 0.000000 -4.340007 5.679654
MB_Tile_r4_069.Rotation 127.384615 0 0
MB_Tile_r4_069.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_070
MB_Tile_r4_070.Position 0.000000 -4.520729 5.536888
MB_Tile_r4_070.Rotation 129.230769 0 0
MB_Tile_r4_070.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_071
MB_Tile_r4_071.Position 0.000000 -4.696759 5.388375
MB_Tile_r4_071.Rotation 131.076923 0 0
MB_Tile_r4_071.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_072
MB_Tile_r4_072.Position 0.000000 -4.867912 5.234268
MB_Tile_r4_072.Rotation 132.923077 0 0
MB_Tile_r4_072.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_073
MB_Tile_r4_073.Position 0.000000 -5.034012 5.074727
MB_Tile_r4_073.Rotation 134.769231 0 0
MB_Tile_r4_073.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_074
MB_Tile_r4_074.Position 0.000000 -5.194886 4.909918
MB_Tile_r4_074.Rotation 136.615385 0 0
MB_Tile_r4_074.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_075
MB_Tile_r4_075.Position 0.000000 -5.350367 4.740011
MB_Tile_r4_075.Rotation 138.461538 0 0
MB_Tile_r4_075.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_076
MB_Tile_r4_076.Position 0.000000 -5.500293 4.565184
MB_Tile_r4_076.Rotation 140.307692 0 0
MB_Tile_r4_076.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_077
MB_Tile_r4_077.Position 0.000000 -5.644509 4.385618
MB_Tile_r4_077.Rotation 142.153846 0 0
MB_Tile_r4_077.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_078
MB_Tile_r4_078.Position 0.000000 -5.782866 4.201498
MB_Tile_r4_078.Rotation 144.000000 0 0
MB_Tile_r4_078.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_079
MB_Tile_r4_079.Position 0.000000 -5.915219 4.013017
MB_Tile_r4_079.Rotation 145.846154 0 0
MB_Tile_r4_079.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_080
MB_Tile_r4_080.Position 0.000000 -6.041432 3.820370
MB_Tile_r4_080.Rotation 147.692308 0 0
MB_Tile_r4_080.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_081
MB_Tile_r4_081.Position 0.000000 -6.161373 3.623757
MB_Tile_r4_081.Rotation 149.538462 0 0
MB_Tile_r4_081.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_082
MB_Tile_r4_082.Position 0.000000 -6.274917 3.423382
MB_Tile_r4_082.Rotation 151.384615 0 0
MB_Tile_r4_082.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_083
MB_Tile_r4_083.Position 0.000000 -6.381947 3.219453
MB_Tile_r4_083.Rotation 153.230769 0 0
MB_Tile_r4_083.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_084
MB_Tile_r4_084.Position 0.000000 -6.482352 3.012182
MB_Tile_r4_084.Rotation 155.076923 0 0
MB_Tile_r4_084.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_085
MB_Tile_r4_085.Position 0.000000 -6.576028 2.801783
MB_Tile_r4_085.Rotation 156.923077 0 0
MB_Tile_r4_085.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_086
MB_Tile_r4_086.Position 0.000000 -6.662876 2.588477
MB_Tile_r4_086.Rotation 158.769231 0 0
MB_Tile_r4_086.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_087
MB_Tile_r4_087.Position 0.000000 -6.742808 2.372483
MB_Tile_r4_087.Rotation 160.615385 0 0
MB_Tile_r4_087.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_088
MB_Tile_r4_088.Position 0.000000 -6.815739 2.154026
MB_Tile_r4_088.Rotation 162.461538 0 0
MB_Tile_r4_088.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_089
MB_Tile_r4_089.Position 0.000000 -6.881595 1.933332
MB_Tile_r4_089.Rotation 164.307692 0 0
MB_Tile_r4_089.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_090
MB_Tile_r4_090.Position 0.000000 -6.940307 1.710632
MB_Tile_r4_090.Rotation 166.153846 0 0
MB_Tile_r4_090.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_091
MB_Tile_r4_091.Position 0.000000 -6.991814 1.486156
MB_Tile_r4_091.Rotation 168.000000 0 0
MB_Tile_r4_091.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_092
MB_Tile_r4_092.Position 0.000000 -7.036063 1.260137
MB_Tile_r4_092.Rotation 169.846154 0 0
MB_Tile_r4_092.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_093
MB_Tile_r4_093.Position 0.000000 -7.073007 1.032810
MB_Tile_r4_093.Rotation 171.692308 0 0
MB_Tile_r4_093.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_094
MB_Tile_r4_094.Position 0.000000 -7.102609 0.804411
MB_Tile_r4_094.Rotation 173.538462 0 0
MB_Tile_r4_094.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_095
MB_Tile_r4_095.Position 0.000000 -7.124837 0.575176
MB_Tile_r4_095.Rotation 175.384615 0 0
MB_Tile_r4_095.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_096
MB_Tile_r4_096.Position 0.000000 -7.139668 0.345345
MB_Tile_r4_096.Rotation 177.230769 0 0
MB_Tile_r4_096.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_097
MB_Tile_r4_097.Position 0.000000 -7.147088 0.115155
MB_Tile_r4_097.Rotation 179.076923 0 0
MB_Tile_r4_097.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_098
MB_Tile_r4_098.Position 0.000000 -7.147088 -0.115155
MB_Tile_r4_098.Rotation 180.923077 0 0
MB_Tile_r4_098.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_099
MB_Tile_r4_099.Position 0.000000 -7.139668 -0.345345
MB_Tile_r4_099.Rotation 182.769231 0 0
MB_Tile_r4_099.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_100
MB_Tile_r4_100.Position 0.000000 -7.124837 -0.575176
MB_Tile_r4_100.Rotation 184.615385 0 0
MB_Tile_r4_100.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_101
MB_Tile_r4_101.Position 0.000000 -7.102609 -0.804411
MB_Tile_r4_101.Rotation 186.461538 0 0
MB_Tile_r4_101.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_102
MB_Tile_r4_102.Position 0.000000 -7.073007 -1.032810
MB_Tile_r4_102.Rotation 188.307692 0 0
MB_Tile_r4_102.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_103
MB_Tile_r4_103.Position 0.000000 -7.036063 -1.260137
MB_Tile_r4_103.Rotation 190.153846 0 0
MB_Tile_r4_103.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_104
MB_Tile_r4_104.Position 0.000000 -6.991814 -1.486156
MB_Tile_r4_104.Rotation 192.000000 0 0
MB_Tile_r4_104.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_105
MB_Tile_r4_105.Position 0.000000 -6.940307 -1.710632
MB_Tile_r4_105.Rotation 193.846154 0 0
MB_Tile_r4_105.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_106
MB_Tile_r4_106.Position 0.000000 -6.881595 -1.933332
MB_Tile_r4_106.Rotation 195.692308 0 0
MB_Tile_r4_106.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_107
MB_Tile_r4_107.Position 0.000000 -6.815739 -2.154026
MB_Tile_r4_107.Rotation 197.538462 0 0
MB_Tile_r4_107.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_108
MB_Tile_r4_108.Position 0.000000 -6.742808 -2.372483
MB_Tile_r4_108.Rotation 199.384615 0 0
MB_Tile_r4_108.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_109
MB_Tile_r4_109.Position 0.000000 -6.662876 -2.588477
MB_Tile_r4_109.Rotation 201.230769 0 0
MB_Tile_r4_109.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_110
MB_Tile_r4_110.Position 0.000000 -6.576028 -2.801783
MB_Tile_r4_110.Rotation 203.076923 0 0
MB_Tile_r4_110.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_111
MB_Tile_r4_111.Position 0.000000 -6.482352 -3.012182
MB_Tile_r4_111.Rotation 204.923077 0 0
MB_Tile_r4_111.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_112
MB_Tile_r4_112.Position 0.000000 -6.381947 -3.219453
MB_Tile_r4_112.Rotation 206.769231 0 0
MB_Tile_r4_112.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_113
MB_Tile_r4_113.Position 0.000000 -6.274917 -3.423382
MB_Tile_r4_113.Rotation 208.615385 0 0
MB_Tile_r4_113.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_114
MB_Tile_r4_114.Position 0.000000 -6.161373 -3.623757
MB_Tile_r4_114.Rotation 210.461538 0 0
MB_Tile_r4_114.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_115
MB_Tile_r4_115.Position 0.000000 -6.041432 -3.820370
MB_Tile_r4_115.Rotation 212.307692 0 0
MB_Tile_r4_115.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_116
MB_Tile_r4_116.Position 0.000000 -5.915219 -4.013017
MB_Tile_r4_116.Rotation 214.153846 0 0
MB_Tile_r4_116.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_117
MB_Tile_r4_117.Position 0.000000 -5.782866 -4.201498
MB_Tile_r4_117.Rotation 216.000000 0 0
MB_Tile_r4_117.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_118
MB_Tile_r4_118.Position 0.000000 -5.644509 -4.385618
MB_Tile_r4_118.Rotation 217.846154 0 0
MB_Tile_r4_118.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_119
MB_Tile_r4_119.Position 0.000000 -5.500293 -4.565184
MB_Tile_r4_119.Rotation 219.692308 0 0
MB_Tile_r4_119.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_120
MB_Tile_r4_120.Position 0.000000 -5.350367 -4.740011
MB_Tile_r4_120.Rotation 221.538462 0 0
MB_Tile_r4_120.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_121
MB_Tile_r4_121.Position 0.000000 -5.194886 -4.909918
MB_Tile_r4_121.Rotation 223.384615 0 0
MB_Tile_r4_121.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_122
MB_Tile_r4_122.Position 0.000000 -5.034012 -5.074727
MB_Tile_r4_122.Rotation 225.230769 0 0
MB_Tile_r4_122.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_123
MB_Tile_r4_123.Position 0.000000 -4.867912 -5.234268
MB_Tile_r4_123.Rotation 227.076923 0 0
MB_Tile_r4_123.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_124
MB_Tile_r4_124.Position 0.000000 -4.696759 -5.388375
MB_Tile_r4_124.Rotation 228.923077 0 0
MB_Tile_r4_124.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_125
MB_Tile_r4_125.Position 0.000000 -4.520729 -5.536888
MB_Tile_r4_125.Rotation 230.769231 0 0
MB_Tile_r4_125.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_126
MB_Tile_r4_126.Position 0.000000 -4.340007 -5.679654
MB_Tile_r4_126.Rotation 232.615385 0 0
MB_Tile_r4_126.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_127
MB_Tile_r4_127.Position 0.000000 -4.154779 -5.816523
MB_Tile_r4_127.Rotation 234.461538 0 0
MB_Tile_r4_127.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_128
MB_Tile_r4_128.Position 0.000000 -3.965238 -5.947354
MB_Tile_r4_128.Rotation 236.307692 0 0
MB_Tile_r4_128.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_129
MB_Tile_r4_129.Position 0.000000 -3.771581 -6.072010
MB_Tile_r4_129.Rotation 238.153846 0 0
MB_Tile_r4_129.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_130
MB_Tile_r4_130.Position 0.000000 -3.574008 -6.190363
MB_Tile_r4_130.Rotation 240.000000 0 0
MB_Tile_r4_130.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_131
MB_Tile_r4_131.Position 0.000000 -3.372725 -6.302290
MB_Tile_r4_131.Rotation 241.846154 0 0
MB_Tile_r4_131.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_132
MB_Tile_r4_132.Position 0.000000 -3.167940 -6.407674
MB_Tile_r4_132.Rotation 243.692308 0 0
MB_Tile_r4_132.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_133
MB_Tile_r4_133.Position 0.000000 -2.959867 -6.506406
MB_Tile_r4_133.Rotation 245.538462 0 0
MB_Tile_r4_133.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_134
MB_Tile_r4_134.Position 0.000000 -2.748721 -6.598383
MB_Tile_r4_134.Rotation 247.384615 0 0
MB_Tile_r4_134.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_135
MB_Tile_r4_135.Position 0.000000 -2.534721 -6.683511
MB_Tile_r4_135.Rotation 249.230769 0 0
MB_Tile_r4_135.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_136
MB_Tile_r4_136.Position 0.000000 -2.318090 -6.761700
MB_Tile_r4_136.Rotation 251.076923 0 0
MB_Tile_r4_136.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_137
MB_Tile_r4_137.Position 0.000000 -2.099053 -6.832869
MB_Tile_r4_137.Rotation 252.923077 0 0
MB_Tile_r4_137.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_138
MB_Tile_r4_138.Position 0.000000 -1.877836 -6.896946
MB_Tile_r4_138.Rotation 254.769231 0 0
MB_Tile_r4_138.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_139
MB_Tile_r4_139.Position 0.000000 -1.654671 -6.953862
MB_Tile_r4_139.Rotation 256.615385 0 0
MB_Tile_r4_139.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_140
MB_Tile_r4_140.Position 0.000000 -1.429787 -7.003559
MB_Tile_r4_140.Rotation 258.461538 0 0
MB_Tile_r4_140.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_141
MB_Tile_r4_141.Position 0.000000 -1.203419 -7.045986
MB_Tile_r4_141.Rotation 260.307692 0 0
MB_Tile_r4_141.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_142
MB_Tile_r4_142.Position 0.000000 -0.975801 -7.081097
MB_Tile_r4_142.Rotation 262.153846 0 0
MB_Tile_r4_142.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_143
MB_Tile_r4_143.Position 0.000000 -0.747171 -7.108858
MB_Tile_r4_143.Rotation 264.000000 0 0
MB_Tile_r4_143.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_144
MB_Tile_r4_144.Position 0.000000 -0.517765 -7.129239
MB_Tile_r4_144.Rotation 265.846154 0 0
MB_Tile_r4_144.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_145
MB_Tile_r4_145.Position 0.000000 -0.287822 -7.142219
MB_Tile_r4_145.Rotation 267.692308 0 0
MB_Tile_r4_145.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_146
MB_Tile_r4_146.Position 0.000000 -0.057579 -7.147784
MB_Tile_r4_146.Rotation 269.538462 0 0
MB_Tile_r4_146.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_147
MB_Tile_r4_147.Position 0.000000 0.172723 -7.145929
MB_Tile_r4_147.Rotation 271.384615 0 0
MB_Tile_r4_147.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_148
MB_Tile_r4_148.Position 0.000000 0.402846 -7.136655
MB_Tile_r4_148.Rotation 273.230769 0 0
MB_Tile_r4_148.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_149
MB_Tile_r4_149.Position 0.000000 0.632550 -7.119973
MB_Tile_r4_149.Rotation 275.076923 0 0
MB_Tile_r4_149.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_150
MB_Tile_r4_150.Position 0.000000 0.861598 -7.095899
MB_Tile_r4_150.Rotation 276.923077 0 0
MB_Tile_r4_150.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_151
MB_Tile_r4_151.Position 0.000000 1.089752 -7.064458
MB_Tile_r4_151.Rotation 278.769231 0 0
MB_Tile_r4_151.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_152
MB_Tile_r4_152.Position 0.000000 1.316774 -7.025684
MB_Tile_r4_152.Rotation 280.615385 0 0
MB_Tile_r4_152.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_153
MB_Tile_r4_153.Position 0.000000 1.542429 -6.979616
MB_Tile_r4_153.Rotation 282.461538 0 0
MB_Tile_r4_153.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_154
MB_Tile_r4_154.Position 0.000000 1.766483 -6.926303
MB_Tile_r4_154.Rotation 284.307692 0 0
MB_Tile_r4_154.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_155
MB_Tile_r4_155.Position 0.000000 1.988703 -6.865799
MB_Tile_r4_155.Rotation 286.153846 0 0
MB_Tile_r4_155.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_156
MB_Tile_r4_156.Position 0.000000 2.208858 -6.798167
MB_Tile_r4_156.Rotation 288.000000 0 0
MB_Tile_r4_156.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_157
MB_Tile_r4_157.Position 0.000000 2.426721 -6.723478
MB_Tile_r4_157.Rotation 289.846154 0 0
MB_Tile_r4_157.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_158
MB_Tile_r4_158.Position 0.000000 2.642064 -6.641809
MB_Tile_r4_158.Rotation 291.692308 0 0
MB_Tile_r4_158.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_159
MB_Tile_r4_159.Position 0.000000 2.854664 -6.553245
MB_Tile_r4_159.Rotation 293.538462 0 0
MB_Tile_r4_159.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_160
MB_Tile_r4_160.Position 0.000000 3.064301 -6.457878
MB_Tile_r4_160.Rotation 295.384615 0 0
MB_Tile_r4_160.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_161
MB_Tile_r4_161.Position 0.000000 3.270757 -6.355807
MB_Tile_r4_161.Rotation 297.230769 0 0
MB_Tile_r4_161.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_162
MB_Tile_r4_162.Position 0.000000 3.473817 -6.247137
MB_Tile_r4_162.Rotation 299.076923 0 0
MB_Tile_r4_162.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_163
MB_Tile_r4_163.Position 0.000000 3.673271 -6.131982
MB_Tile_r4_163.Rotation 300.923077 0 0
MB_Tile_r4_163.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_164
MB_Tile_r4_164.Position 0.000000 3.868912 -6.010462
MB_Tile_r4_164.Rotation 302.769231 0 0
MB_Tile_r4_164.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_165
MB_Tile_r4_165.Position 0.000000 4.060536 -5.882702
MB_Tile_r4_165.Rotation 304.615385 0 0
MB_Tile_r4_165.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_166
MB_Tile_r4_166.Position 0.000000 4.247944 -5.748834
MB_Tile_r4_166.Rotation 306.461538 0 0
MB_Tile_r4_166.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_167
MB_Tile_r4_167.Position 0.000000 4.430943 -5.608999
MB_Tile_r4_167.Rotation 308.307692 0 0
MB_Tile_r4_167.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_168
MB_Tile_r4_168.Position 0.000000 4.609342 -5.463341
MB_Tile_r4_168.Rotation 310.153846 0 0
MB_Tile_r4_168.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_169
MB_Tile_r4_169.Position 0.000000 4.782956 -5.312011
MB_Tile_r4_169.Rotation 312.000000 0 0
MB_Tile_r4_169.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_170
MB_Tile_r4_170.Position 0.000000 4.951605 -5.155166
MB_Tile_r4_170.Rotation 313.846154 0 0
MB_Tile_r4_170.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_171
MB_Tile_r4_171.Position 0.000000 5.115113 -4.992970
MB_Tile_r4_171.Rotation 315.692308 0 0
MB_Tile_r4_171.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_172
MB_Tile_r4_172.Position 0.000000 5.273310 -4.825591
MB_Tile_r4_172.Rotation 317.538462 0 0
MB_Tile_r4_172.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_173
MB_Tile_r4_173.Position 0.000000 5.426034 -4.653201
MB_Tile_r4_173.Rotation 319.384615 0 0
MB_Tile_r4_173.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_174
MB_Tile_r4_174.Position 0.000000 5.573125 -4.475982
MB_Tile_r4_174.Rotation 321.230769 0 0
MB_Tile_r4_174.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_175
MB_Tile_r4_175.Position 0.000000 5.714429 -4.294115
MB_Tile_r4_175.Rotation 323.076923 0 0
MB_Tile_r4_175.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_176
MB_Tile_r4_176.Position 0.000000 5.849802 -4.107791
MB_Tile_r4_176.Rotation 324.923077 0 0
MB_Tile_r4_176.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_177
MB_Tile_r4_177.Position 0.000000 5.979102 -3.917202
MB_Tile_r4_177.Rotation 326.769231 0 0
MB_Tile_r4_177.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_178
MB_Tile_r4_178.Position 0.000000 6.102194 -3.722547
MB_Tile_r4_178.Rotation 328.615385 0 0
MB_Tile_r4_178.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_179
MB_Tile_r4_179.Position 0.000000 6.218952 -3.524027
MB_Tile_r4_179.Rotation 330.461538 0 0
MB_Tile_r4_179.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_180
MB_Tile_r4_180.Position 0.000000 6.329254 -3.321849
MB_Tile_r4_180.Rotation 332.307692 0 0
MB_Tile_r4_180.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_181
MB_Tile_r4_181.Position 0.000000 6.432985 -3.116222
MB_Tile_r4_181.Rotation 334.153846 0 0
MB_Tile_r4_181.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_182
MB_Tile_r4_182.Position 0.000000 6.530037 -2.907360
MB_Tile_r4_182.Rotation 336.000000 0 0
MB_Tile_r4_182.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_183
MB_Tile_r4_183.Position 0.000000 6.620311 -2.695480
MB_Tile_r4_183.Rotation 337.846154 0 0
MB_Tile_r4_183.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_184
MB_Tile_r4_184.Position 0.000000 6.703712 -2.480802
MB_Tile_r4_184.Rotation 339.692308 0 0
MB_Tile_r4_184.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_185
MB_Tile_r4_185.Position 0.000000 6.780153 -2.263548
MB_Tile_r4_185.Rotation 341.538462 0 0
MB_Tile_r4_185.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_186
MB_Tile_r4_186.Position 0.000000 6.849556 -2.043944
MB_Tile_r4_186.Rotation 343.384615 0 0
MB_Tile_r4_186.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_187
MB_Tile_r4_187.Position 0.000000 6.911848 -1.822219
MB_Tile_r4_187.Rotation 345.230769 0 0
MB_Tile_r4_187.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_188
MB_Tile_r4_188.Position 0.000000 6.966965 -1.598602
MB_Tile_r4_188.Rotation 347.076923 0 0
MB_Tile_r4_188.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_189
MB_Tile_r4_189.Position 0.000000 7.014849 -1.373325
MB_Tile_r4_189.Rotation 348.923077 0 0
MB_Tile_r4_189.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_190
MB_Tile_r4_190.Position 0.000000 7.055451 -1.146622
MB_Tile_r4_190.Rotation 350.769231 0 0
MB_Tile_r4_190.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_191
MB_Tile_r4_191.Position 0.000000 7.088728 -0.918730
MB_Tile_r4_191.Rotation 352.615385 0 0
MB_Tile_r4_191.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_192
MB_Tile_r4_192.Position 0.000000 7.114646 -0.689883
MB_Tile_r4_192.Rotation 354.461538 0 0
MB_Tile_r4_192.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_193
MB_Tile_r4_193.Position 0.000000 7.133178 -0.460320
MB_Tile_r4_193.Rotation 356.307692 0 0
MB_Tile_r4_193.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r4_194
MB_Tile_r4_194.Position 0.000000 7.144305 -0.230280
MB_Tile_r4_194.Rotation 358.153846 0 0
MB_Tile_r4_194.Mother InstrumentFrame

// ring 5: E=551.0 keV, r=6.888550 cm, 188 tiles
MB_Tile.Copy MB_Tile_r5_000
MB_Tile_r5_000.Position 0.000000 6.888550 0.000000
MB_Tile_r5_000.Rotation 0.000000 0 0
MB_Tile_r5_000.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_001
MB_Tile_r5_001.Position 0.000000 6.884703 0.230181
MB_Tile_r5_001.Rotation 1.914894 0 0
MB_Tile_r5_001.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_002
MB_Tile_r5_002.Position 0.000000 6.873167 0.460104
MB_Tile_r5_002.Rotation 3.829787 0 0
MB_Tile_r5_002.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_003
MB_Tile_r5_003.Position 0.000000 6.853955 0.689514
MB_Tile_r5_003.Rotation 5.744681 0 0
MB_Tile_r5_003.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_004
MB_Tile_r5_004.Position 0.000000 6.827087 0.918154
MB_Tile_r5_004.Rotation 7.659574 0 0
MB_Tile_r5_004.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_005
MB_Tile_r5_005.Position 0.000000 6.792594 1.145768
MB_Tile_r5_005.Rotation 9.574468 0 0
MB_Tile_r5_005.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_006
MB_Tile_r5_006.Position 0.000000 6.750515 1.372103
MB_Tile_r5_006.Rotation 11.489362 0 0
MB_Tile_r5_006.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_007
MB_Tile_r5_007.Position 0.000000 6.700897 1.596905
MB_Tile_r5_007.Rotation 13.404255 0 0
MB_Tile_r5_007.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_008
MB_Tile_r5_008.Position 0.000000 6.643794 1.819923
MB_Tile_r5_008.Rotation 15.319149 0 0
MB_Tile_r5_008.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_009
MB_Tile_r5_009.Position 0.000000 6.579271 2.040909
MB_Tile_r5_009.Rotation 17.234043 0 0
MB_Tile_r5_009.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_010
MB_Tile_r5_010.Position 0.000000 6.507400 2.259616
MB_Tile_r5_010.Rotation 19.148936 0 0
MB_Tile_r5_010.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_011
MB_Tile_r5_011.Position 0.000000 6.428261 2.475798
MB_Tile_r5_011.Rotation 21.063830 0 0
MB_Tile_r5_011.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_012
MB_Tile_r5_012.Position 0.000000 6.341943 2.689216
MB_Tile_r5_012.Rotation 22.978723 0 0
MB_Tile_r5_012.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_013
MB_Tile_r5_013.Position 0.000000 6.248541 2.899630
MB_Tile_r5_013.Rotation 24.893617 0 0
MB_Tile_r5_013.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_014
MB_Tile_r5_014.Position 0.000000 6.148161 3.106806
MB_Tile_r5_014.Rotation 26.808511 0 0
MB_Tile_r5_014.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_015
MB_Tile_r5_015.Position 0.000000 6.040914 3.310512
MB_Tile_r5_015.Rotation 28.723404 0 0
MB_Tile_r5_015.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_016
MB_Tile_r5_016.Position 0.000000 5.926919 3.510520
MB_Tile_r5_016.Rotation 30.638298 0 0
MB_Tile_r5_016.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_017
MB_Tile_r5_017.Position 0.000000 5.806306 3.706607
MB_Tile_r5_017.Rotation 32.553191 0 0
MB_Tile_r5_017.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_018
MB_Tile_r5_018.Position 0.000000 5.679207 3.898555
MB_Tile_r5_018.Rotation 34.468085 0 0
MB_Tile_r5_018.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_019
MB_Tile_r5_019.Position 0.000000 5.545765 4.086148
MB_Tile_r5_019.Rotation 36.382979 0 0
MB_Tile_r5_019.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_020
MB_Tile_r5_020.Position 0.000000 5.406130 4.269178
MB_Tile_r5_020.Rotation 38.297872 0 0
MB_Tile_r5_020.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_021
MB_Tile_r5_021.Position 0.000000 5.260456 4.447440
MB_Tile_r5_021.Rotation 40.212766 0 0
MB_Tile_r5_021.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_022
MB_Tile_r5_022.Position 0.000000 5.108908 4.620734
MB_Tile_r5_022.Rotation 42.127660 0 0
MB_Tile_r5_022.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_023
MB_Tile_r5_023.Position 0.000000 4.951653 4.788868
MB_Tile_r5_023.Rotation 44.042553 0 0
MB_Tile_r5_023.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_024
MB_Tile_r5_024.Position 0.000000 4.788868 4.951653
MB_Tile_r5_024.Rotation 45.957447 0 0
MB_Tile_r5_024.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_025
MB_Tile_r5_025.Position 0.000000 4.620734 5.108908
MB_Tile_r5_025.Rotation 47.872340 0 0
MB_Tile_r5_025.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_026
MB_Tile_r5_026.Position 0.000000 4.447440 5.260456
MB_Tile_r5_026.Rotation 49.787234 0 0
MB_Tile_r5_026.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_027
MB_Tile_r5_027.Position 0.000000 4.269178 5.406130
MB_Tile_r5_027.Rotation 51.702128 0 0
MB_Tile_r5_027.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_028
MB_Tile_r5_028.Position 0.000000 4.086148 5.545765
MB_Tile_r5_028.Rotation 53.617021 0 0
MB_Tile_r5_028.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_029
MB_Tile_r5_029.Position 0.000000 3.898555 5.679207
MB_Tile_r5_029.Rotation 55.531915 0 0
MB_Tile_r5_029.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_030
MB_Tile_r5_030.Position 0.000000 3.706607 5.806306
MB_Tile_r5_030.Rotation 57.446809 0 0
MB_Tile_r5_030.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_031
MB_Tile_r5_031.Position 0.000000 3.510520 5.926919
MB_Tile_r5_031.Rotation 59.361702 0 0
MB_Tile_r5_031.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_032
MB_Tile_r5_032.Position 0.000000 3.310512 6.040914
MB_Tile_r5_032.Rotation 61.276596 0 0
MB_Tile_r5_032.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_033
MB_Tile_r5_033.Position 0.000000 3.106806 6.148161
MB_Tile_r5_033.Rotation 63.191489 0 0
MB_Tile_r5_033.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_034
MB_Tile_r5_034.Position 0.000000 2.899630 6.248541
MB_Tile_r5_034.Rotation 65.106383 0 0
MB_Tile_r5_034.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_035
MB_Tile_r5_035.Position 0.000000 2.689216 6.341943
MB_Tile_r5_035.Rotation 67.021277 0 0
MB_Tile_r5_035.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_036
MB_Tile_r5_036.Position 0.000000 2.475798 6.428261
MB_Tile_r5_036.Rotation 68.936170 0 0
MB_Tile_r5_036.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_037
MB_Tile_r5_037.Position 0.000000 2.259616 6.507400
MB_Tile_r5_037.Rotation 70.851064 0 0
MB_Tile_r5_037.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_038
MB_Tile_r5_038.Position 0.000000 2.040909 6.579271
MB_Tile_r5_038.Rotation 72.765957 0 0
MB_Tile_r5_038.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_039
MB_Tile_r5_039.Position 0.000000 1.819923 6.643794
MB_Tile_r5_039.Rotation 74.680851 0 0
MB_Tile_r5_039.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_040
MB_Tile_r5_040.Position 0.000000 1.596905 6.700897
MB_Tile_r5_040.Rotation 76.595745 0 0
MB_Tile_r5_040.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_041
MB_Tile_r5_041.Position 0.000000 1.372103 6.750515
MB_Tile_r5_041.Rotation 78.510638 0 0
MB_Tile_r5_041.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_042
MB_Tile_r5_042.Position 0.000000 1.145768 6.792594
MB_Tile_r5_042.Rotation 80.425532 0 0
MB_Tile_r5_042.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_043
MB_Tile_r5_043.Position 0.000000 0.918154 6.827087
MB_Tile_r5_043.Rotation 82.340426 0 0
MB_Tile_r5_043.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_044
MB_Tile_r5_044.Position 0.000000 0.689514 6.853955
MB_Tile_r5_044.Rotation 84.255319 0 0
MB_Tile_r5_044.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_045
MB_Tile_r5_045.Position 0.000000 0.460104 6.873167
MB_Tile_r5_045.Rotation 86.170213 0 0
MB_Tile_r5_045.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_046
MB_Tile_r5_046.Position 0.000000 0.230181 6.884703
MB_Tile_r5_046.Rotation 88.085106 0 0
MB_Tile_r5_046.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_047
MB_Tile_r5_047.Position 0.000000 0.000000 6.888550
MB_Tile_r5_047.Rotation 90.000000 0 0
MB_Tile_r5_047.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_048
MB_Tile_r5_048.Position 0.000000 -0.230181 6.884703
MB_Tile_r5_048.Rotation 91.914894 0 0
MB_Tile_r5_048.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_049
MB_Tile_r5_049.Position 0.000000 -0.460104 6.873167
MB_Tile_r5_049.Rotation 93.829787 0 0
MB_Tile_r5_049.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_050
MB_Tile_r5_050.Position 0.000000 -0.689514 6.853955
MB_Tile_r5_050.Rotation 95.744681 0 0
MB_Tile_r5_050.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_051
MB_Tile_r5_051.Position 0.000000 -0.918154 6.827087
MB_Tile_r5_051.Rotation 97.659574 0 0
MB_Tile_r5_051.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_052
MB_Tile_r5_052.Position 0.000000 -1.145768 6.792594
MB_Tile_r5_052.Rotation 99.574468 0 0
MB_Tile_r5_052.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_053
MB_Tile_r5_053.Position 0.000000 -1.372103 6.750515
MB_Tile_r5_053.Rotation 101.489362 0 0
MB_Tile_r5_053.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_054
MB_Tile_r5_054.Position 0.000000 -1.596905 6.700897
MB_Tile_r5_054.Rotation 103.404255 0 0
MB_Tile_r5_054.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_055
MB_Tile_r5_055.Position 0.000000 -1.819923 6.643794
MB_Tile_r5_055.Rotation 105.319149 0 0
MB_Tile_r5_055.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_056
MB_Tile_r5_056.Position 0.000000 -2.040909 6.579271
MB_Tile_r5_056.Rotation 107.234043 0 0
MB_Tile_r5_056.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_057
MB_Tile_r5_057.Position 0.000000 -2.259616 6.507400
MB_Tile_r5_057.Rotation 109.148936 0 0
MB_Tile_r5_057.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_058
MB_Tile_r5_058.Position 0.000000 -2.475798 6.428261
MB_Tile_r5_058.Rotation 111.063830 0 0
MB_Tile_r5_058.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_059
MB_Tile_r5_059.Position 0.000000 -2.689216 6.341943
MB_Tile_r5_059.Rotation 112.978723 0 0
MB_Tile_r5_059.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_060
MB_Tile_r5_060.Position 0.000000 -2.899630 6.248541
MB_Tile_r5_060.Rotation 114.893617 0 0
MB_Tile_r5_060.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_061
MB_Tile_r5_061.Position 0.000000 -3.106806 6.148161
MB_Tile_r5_061.Rotation 116.808511 0 0
MB_Tile_r5_061.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_062
MB_Tile_r5_062.Position 0.000000 -3.310512 6.040914
MB_Tile_r5_062.Rotation 118.723404 0 0
MB_Tile_r5_062.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_063
MB_Tile_r5_063.Position 0.000000 -3.510520 5.926919
MB_Tile_r5_063.Rotation 120.638298 0 0
MB_Tile_r5_063.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_064
MB_Tile_r5_064.Position 0.000000 -3.706607 5.806306
MB_Tile_r5_064.Rotation 122.553191 0 0
MB_Tile_r5_064.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_065
MB_Tile_r5_065.Position 0.000000 -3.898555 5.679207
MB_Tile_r5_065.Rotation 124.468085 0 0
MB_Tile_r5_065.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_066
MB_Tile_r5_066.Position 0.000000 -4.086148 5.545765
MB_Tile_r5_066.Rotation 126.382979 0 0
MB_Tile_r5_066.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_067
MB_Tile_r5_067.Position 0.000000 -4.269178 5.406130
MB_Tile_r5_067.Rotation 128.297872 0 0
MB_Tile_r5_067.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_068
MB_Tile_r5_068.Position 0.000000 -4.447440 5.260456
MB_Tile_r5_068.Rotation 130.212766 0 0
MB_Tile_r5_068.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_069
MB_Tile_r5_069.Position 0.000000 -4.620734 5.108908
MB_Tile_r5_069.Rotation 132.127660 0 0
MB_Tile_r5_069.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_070
MB_Tile_r5_070.Position 0.000000 -4.788868 4.951653
MB_Tile_r5_070.Rotation 134.042553 0 0
MB_Tile_r5_070.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_071
MB_Tile_r5_071.Position 0.000000 -4.951653 4.788868
MB_Tile_r5_071.Rotation 135.957447 0 0
MB_Tile_r5_071.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_072
MB_Tile_r5_072.Position 0.000000 -5.108908 4.620734
MB_Tile_r5_072.Rotation 137.872340 0 0
MB_Tile_r5_072.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_073
MB_Tile_r5_073.Position 0.000000 -5.260456 4.447440
MB_Tile_r5_073.Rotation 139.787234 0 0
MB_Tile_r5_073.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_074
MB_Tile_r5_074.Position 0.000000 -5.406130 4.269178
MB_Tile_r5_074.Rotation 141.702128 0 0
MB_Tile_r5_074.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_075
MB_Tile_r5_075.Position 0.000000 -5.545765 4.086148
MB_Tile_r5_075.Rotation 143.617021 0 0
MB_Tile_r5_075.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_076
MB_Tile_r5_076.Position 0.000000 -5.679207 3.898555
MB_Tile_r5_076.Rotation 145.531915 0 0
MB_Tile_r5_076.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_077
MB_Tile_r5_077.Position 0.000000 -5.806306 3.706607
MB_Tile_r5_077.Rotation 147.446809 0 0
MB_Tile_r5_077.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_078
MB_Tile_r5_078.Position 0.000000 -5.926919 3.510520
MB_Tile_r5_078.Rotation 149.361702 0 0
MB_Tile_r5_078.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_079
MB_Tile_r5_079.Position 0.000000 -6.040914 3.310512
MB_Tile_r5_079.Rotation 151.276596 0 0
MB_Tile_r5_079.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_080
MB_Tile_r5_080.Position 0.000000 -6.148161 3.106806
MB_Tile_r5_080.Rotation 153.191489 0 0
MB_Tile_r5_080.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_081
MB_Tile_r5_081.Position 0.000000 -6.248541 2.899630
MB_Tile_r5_081.Rotation 155.106383 0 0
MB_Tile_r5_081.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_082
MB_Tile_r5_082.Position 0.000000 -6.341943 2.689216
MB_Tile_r5_082.Rotation 157.021277 0 0
MB_Tile_r5_082.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_083
MB_Tile_r5_083.Position 0.000000 -6.428261 2.475798
MB_Tile_r5_083.Rotation 158.936170 0 0
MB_Tile_r5_083.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_084
MB_Tile_r5_084.Position 0.000000 -6.507400 2.259616
MB_Tile_r5_084.Rotation 160.851064 0 0
MB_Tile_r5_084.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_085
MB_Tile_r5_085.Position 0.000000 -6.579271 2.040909
MB_Tile_r5_085.Rotation 162.765957 0 0
MB_Tile_r5_085.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_086
MB_Tile_r5_086.Position 0.000000 -6.643794 1.819923
MB_Tile_r5_086.Rotation 164.680851 0 0
MB_Tile_r5_086.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_087
MB_Tile_r5_087.Position 0.000000 -6.700897 1.596905
MB_Tile_r5_087.Rotation 166.595745 0 0
MB_Tile_r5_087.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_088
MB_Tile_r5_088.Position 0.000000 -6.750515 1.372103
MB_Tile_r5_088.Rotation 168.510638 0 0
MB_Tile_r5_088.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_089
MB_Tile_r5_089.Position 0.000000 -6.792594 1.145768
MB_Tile_r5_089.Rotation 170.425532 0 0
MB_Tile_r5_089.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_090
MB_Tile_r5_090.Position 0.000000 -6.827087 0.918154
MB_Tile_r5_090.Rotation 172.340426 0 0
MB_Tile_r5_090.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_091
MB_Tile_r5_091.Position 0.000000 -6.853955 0.689514
MB_Tile_r5_091.Rotation 174.255319 0 0
MB_Tile_r5_091.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_092
MB_Tile_r5_092.Position 0.000000 -6.873167 0.460104
MB_Tile_r5_092.Rotation 176.170213 0 0
MB_Tile_r5_092.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_093
MB_Tile_r5_093.Position 0.000000 -6.884703 0.230181
MB_Tile_r5_093.Rotation 178.085106 0 0
MB_Tile_r5_093.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_094
MB_Tile_r5_094.Position 0.000000 -6.888550 0.000000
MB_Tile_r5_094.Rotation 180.000000 0 0
MB_Tile_r5_094.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_095
MB_Tile_r5_095.Position 0.000000 -6.884703 -0.230181
MB_Tile_r5_095.Rotation 181.914894 0 0
MB_Tile_r5_095.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_096
MB_Tile_r5_096.Position 0.000000 -6.873167 -0.460104
MB_Tile_r5_096.Rotation 183.829787 0 0
MB_Tile_r5_096.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_097
MB_Tile_r5_097.Position 0.000000 -6.853955 -0.689514
MB_Tile_r5_097.Rotation 185.744681 0 0
MB_Tile_r5_097.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_098
MB_Tile_r5_098.Position 0.000000 -6.827087 -0.918154
MB_Tile_r5_098.Rotation 187.659574 0 0
MB_Tile_r5_098.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_099
MB_Tile_r5_099.Position 0.000000 -6.792594 -1.145768
MB_Tile_r5_099.Rotation 189.574468 0 0
MB_Tile_r5_099.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_100
MB_Tile_r5_100.Position 0.000000 -6.750515 -1.372103
MB_Tile_r5_100.Rotation 191.489362 0 0
MB_Tile_r5_100.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_101
MB_Tile_r5_101.Position 0.000000 -6.700897 -1.596905
MB_Tile_r5_101.Rotation 193.404255 0 0
MB_Tile_r5_101.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_102
MB_Tile_r5_102.Position 0.000000 -6.643794 -1.819923
MB_Tile_r5_102.Rotation 195.319149 0 0
MB_Tile_r5_102.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_103
MB_Tile_r5_103.Position 0.000000 -6.579271 -2.040909
MB_Tile_r5_103.Rotation 197.234043 0 0
MB_Tile_r5_103.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_104
MB_Tile_r5_104.Position 0.000000 -6.507400 -2.259616
MB_Tile_r5_104.Rotation 199.148936 0 0
MB_Tile_r5_104.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_105
MB_Tile_r5_105.Position 0.000000 -6.428261 -2.475798
MB_Tile_r5_105.Rotation 201.063830 0 0
MB_Tile_r5_105.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_106
MB_Tile_r5_106.Position 0.000000 -6.341943 -2.689216
MB_Tile_r5_106.Rotation 202.978723 0 0
MB_Tile_r5_106.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_107
MB_Tile_r5_107.Position 0.000000 -6.248541 -2.899630
MB_Tile_r5_107.Rotation 204.893617 0 0
MB_Tile_r5_107.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_108
MB_Tile_r5_108.Position 0.000000 -6.148161 -3.106806
MB_Tile_r5_108.Rotation 206.808511 0 0
MB_Tile_r5_108.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_109
MB_Tile_r5_109.Position 0.000000 -6.040914 -3.310512
MB_Tile_r5_109.Rotation 208.723404 0 0
MB_Tile_r5_109.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_110
MB_Tile_r5_110.Position 0.000000 -5.926919 -3.510520
MB_Tile_r5_110.Rotation 210.638298 0 0
MB_Tile_r5_110.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_111
MB_Tile_r5_111.Position 0.000000 -5.806306 -3.706607
MB_Tile_r5_111.Rotation 212.553191 0 0
MB_Tile_r5_111.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_112
MB_Tile_r5_112.Position 0.000000 -5.679207 -3.898555
MB_Tile_r5_112.Rotation 214.468085 0 0
MB_Tile_r5_112.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_113
MB_Tile_r5_113.Position 0.000000 -5.545765 -4.086148
MB_Tile_r5_113.Rotation 216.382979 0 0
MB_Tile_r5_113.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_114
MB_Tile_r5_114.Position 0.000000 -5.406130 -4.269178
MB_Tile_r5_114.Rotation 218.297872 0 0
MB_Tile_r5_114.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_115
MB_Tile_r5_115.Position 0.000000 -5.260456 -4.447440
MB_Tile_r5_115.Rotation 220.212766 0 0
MB_Tile_r5_115.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_116
MB_Tile_r5_116.Position 0.000000 -5.108908 -4.620734
MB_Tile_r5_116.Rotation 222.127660 0 0
MB_Tile_r5_116.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_117
MB_Tile_r5_117.Position 0.000000 -4.951653 -4.788868
MB_Tile_r5_117.Rotation 224.042553 0 0
MB_Tile_r5_117.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_118
MB_Tile_r5_118.Position 0.000000 -4.788868 -4.951653
MB_Tile_r5_118.Rotation 225.957447 0 0
MB_Tile_r5_118.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_119
MB_Tile_r5_119.Position 0.000000 -4.620734 -5.108908
MB_Tile_r5_119.Rotation 227.872340 0 0
MB_Tile_r5_119.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_120
MB_Tile_r5_120.Position 0.000000 -4.447440 -5.260456
MB_Tile_r5_120.Rotation 229.787234 0 0
MB_Tile_r5_120.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_121
MB_Tile_r5_121.Position 0.000000 -4.269178 -5.406130
MB_Tile_r5_121.Rotation 231.702128 0 0
MB_Tile_r5_121.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_122
MB_Tile_r5_122.Position 0.000000 -4.086148 -5.545765
MB_Tile_r5_122.Rotation 233.617021 0 0
MB_Tile_r5_122.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_123
MB_Tile_r5_123.Position 0.000000 -3.898555 -5.679207
MB_Tile_r5_123.Rotation 235.531915 0 0
MB_Tile_r5_123.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_124
MB_Tile_r5_124.Position 0.000000 -3.706607 -5.806306
MB_Tile_r5_124.Rotation 237.446809 0 0
MB_Tile_r5_124.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_125
MB_Tile_r5_125.Position 0.000000 -3.510520 -5.926919
MB_Tile_r5_125.Rotation 239.361702 0 0
MB_Tile_r5_125.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_126
MB_Tile_r5_126.Position 0.000000 -3.310512 -6.040914
MB_Tile_r5_126.Rotation 241.276596 0 0
MB_Tile_r5_126.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_127
MB_Tile_r5_127.Position 0.000000 -3.106806 -6.148161
MB_Tile_r5_127.Rotation 243.191489 0 0
MB_Tile_r5_127.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_128
MB_Tile_r5_128.Position 0.000000 -2.899630 -6.248541
MB_Tile_r5_128.Rotation 245.106383 0 0
MB_Tile_r5_128.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_129
MB_Tile_r5_129.Position 0.000000 -2.689216 -6.341943
MB_Tile_r5_129.Rotation 247.021277 0 0
MB_Tile_r5_129.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_130
MB_Tile_r5_130.Position 0.000000 -2.475798 -6.428261
MB_Tile_r5_130.Rotation 248.936170 0 0
MB_Tile_r5_130.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_131
MB_Tile_r5_131.Position 0.000000 -2.259616 -6.507400
MB_Tile_r5_131.Rotation 250.851064 0 0
MB_Tile_r5_131.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_132
MB_Tile_r5_132.Position 0.000000 -2.040909 -6.579271
MB_Tile_r5_132.Rotation 252.765957 0 0
MB_Tile_r5_132.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_133
MB_Tile_r5_133.Position 0.000000 -1.819923 -6.643794
MB_Tile_r5_133.Rotation 254.680851 0 0
MB_Tile_r5_133.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_134
MB_Tile_r5_134.Position 0.000000 -1.596905 -6.700897
MB_Tile_r5_134.Rotation 256.595745 0 0
MB_Tile_r5_134.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_135
MB_Tile_r5_135.Position 0.000000 -1.372103 -6.750515
MB_Tile_r5_135.Rotation 258.510638 0 0
MB_Tile_r5_135.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_136
MB_Tile_r5_136.Position 0.000000 -1.145768 -6.792594
MB_Tile_r5_136.Rotation 260.425532 0 0
MB_Tile_r5_136.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_137
MB_Tile_r5_137.Position 0.000000 -0.918154 -6.827087
MB_Tile_r5_137.Rotation 262.340426 0 0
MB_Tile_r5_137.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_138
MB_Tile_r5_138.Position 0.000000 -0.689514 -6.853955
MB_Tile_r5_138.Rotation 264.255319 0 0
MB_Tile_r5_138.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_139
MB_Tile_r5_139.Position 0.000000 -0.460104 -6.873167
MB_Tile_r5_139.Rotation 266.170213 0 0
MB_Tile_r5_139.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_140
MB_Tile_r5_140.Position 0.000000 -0.230181 -6.884703
MB_Tile_r5_140.Rotation 268.085106 0 0
MB_Tile_r5_140.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_141
MB_Tile_r5_141.Position 0.000000 -0.000000 -6.888550
MB_Tile_r5_141.Rotation 270.000000 0 0
MB_Tile_r5_141.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_142
MB_Tile_r5_142.Position 0.000000 0.230181 -6.884703
MB_Tile_r5_142.Rotation 271.914894 0 0
MB_Tile_r5_142.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_143
MB_Tile_r5_143.Position 0.000000 0.460104 -6.873167
MB_Tile_r5_143.Rotation 273.829787 0 0
MB_Tile_r5_143.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_144
MB_Tile_r5_144.Position 0.000000 0.689514 -6.853955
MB_Tile_r5_144.Rotation 275.744681 0 0
MB_Tile_r5_144.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_145
MB_Tile_r5_145.Position 0.000000 0.918154 -6.827087
MB_Tile_r5_145.Rotation 277.659574 0 0
MB_Tile_r5_145.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_146
MB_Tile_r5_146.Position 0.000000 1.145768 -6.792594
MB_Tile_r5_146.Rotation 279.574468 0 0
MB_Tile_r5_146.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_147
MB_Tile_r5_147.Position 0.000000 1.372103 -6.750515
MB_Tile_r5_147.Rotation 281.489362 0 0
MB_Tile_r5_147.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_148
MB_Tile_r5_148.Position 0.000000 1.596905 -6.700897
MB_Tile_r5_148.Rotation 283.404255 0 0
MB_Tile_r5_148.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_149
MB_Tile_r5_149.Position 0.000000 1.819923 -6.643794
MB_Tile_r5_149.Rotation 285.319149 0 0
MB_Tile_r5_149.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_150
MB_Tile_r5_150.Position 0.000000 2.040909 -6.579271
MB_Tile_r5_150.Rotation 287.234043 0 0
MB_Tile_r5_150.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_151
MB_Tile_r5_151.Position 0.000000 2.259616 -6.507400
MB_Tile_r5_151.Rotation 289.148936 0 0
MB_Tile_r5_151.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_152
MB_Tile_r5_152.Position 0.000000 2.475798 -6.428261
MB_Tile_r5_152.Rotation 291.063830 0 0
MB_Tile_r5_152.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_153
MB_Tile_r5_153.Position 0.000000 2.689216 -6.341943
MB_Tile_r5_153.Rotation 292.978723 0 0
MB_Tile_r5_153.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_154
MB_Tile_r5_154.Position 0.000000 2.899630 -6.248541
MB_Tile_r5_154.Rotation 294.893617 0 0
MB_Tile_r5_154.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_155
MB_Tile_r5_155.Position 0.000000 3.106806 -6.148161
MB_Tile_r5_155.Rotation 296.808511 0 0
MB_Tile_r5_155.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_156
MB_Tile_r5_156.Position 0.000000 3.310512 -6.040914
MB_Tile_r5_156.Rotation 298.723404 0 0
MB_Tile_r5_156.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_157
MB_Tile_r5_157.Position 0.000000 3.510520 -5.926919
MB_Tile_r5_157.Rotation 300.638298 0 0
MB_Tile_r5_157.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_158
MB_Tile_r5_158.Position 0.000000 3.706607 -5.806306
MB_Tile_r5_158.Rotation 302.553191 0 0
MB_Tile_r5_158.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_159
MB_Tile_r5_159.Position 0.000000 3.898555 -5.679207
MB_Tile_r5_159.Rotation 304.468085 0 0
MB_Tile_r5_159.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_160
MB_Tile_r5_160.Position 0.000000 4.086148 -5.545765
MB_Tile_r5_160.Rotation 306.382979 0 0
MB_Tile_r5_160.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_161
MB_Tile_r5_161.Position 0.000000 4.269178 -5.406130
MB_Tile_r5_161.Rotation 308.297872 0 0
MB_Tile_r5_161.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_162
MB_Tile_r5_162.Position 0.000000 4.447440 -5.260456
MB_Tile_r5_162.Rotation 310.212766 0 0
MB_Tile_r5_162.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_163
MB_Tile_r5_163.Position 0.000000 4.620734 -5.108908
MB_Tile_r5_163.Rotation 312.127660 0 0
MB_Tile_r5_163.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_164
MB_Tile_r5_164.Position 0.000000 4.788868 -4.951653
MB_Tile_r5_164.Rotation 314.042553 0 0
MB_Tile_r5_164.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_165
MB_Tile_r5_165.Position 0.000000 4.951653 -4.788868
MB_Tile_r5_165.Rotation 315.957447 0 0
MB_Tile_r5_165.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_166
MB_Tile_r5_166.Position 0.000000 5.108908 -4.620734
MB_Tile_r5_166.Rotation 317.872340 0 0
MB_Tile_r5_166.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_167
MB_Tile_r5_167.Position 0.000000 5.260456 -4.447440
MB_Tile_r5_167.Rotation 319.787234 0 0
MB_Tile_r5_167.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_168
MB_Tile_r5_168.Position 0.000000 5.406130 -4.269178
MB_Tile_r5_168.Rotation 321.702128 0 0
MB_Tile_r5_168.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_169
MB_Tile_r5_169.Position 0.000000 5.545765 -4.086148
MB_Tile_r5_169.Rotation 323.617021 0 0
MB_Tile_r5_169.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_170
MB_Tile_r5_170.Position 0.000000 5.679207 -3.898555
MB_Tile_r5_170.Rotation 325.531915 0 0
MB_Tile_r5_170.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_171
MB_Tile_r5_171.Position 0.000000 5.806306 -3.706607
MB_Tile_r5_171.Rotation 327.446809 0 0
MB_Tile_r5_171.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_172
MB_Tile_r5_172.Position 0.000000 5.926919 -3.510520
MB_Tile_r5_172.Rotation 329.361702 0 0
MB_Tile_r5_172.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_173
MB_Tile_r5_173.Position 0.000000 6.040914 -3.310512
MB_Tile_r5_173.Rotation 331.276596 0 0
MB_Tile_r5_173.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_174
MB_Tile_r5_174.Position 0.000000 6.148161 -3.106806
MB_Tile_r5_174.Rotation 333.191489 0 0
MB_Tile_r5_174.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_175
MB_Tile_r5_175.Position 0.000000 6.248541 -2.899630
MB_Tile_r5_175.Rotation 335.106383 0 0
MB_Tile_r5_175.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_176
MB_Tile_r5_176.Position 0.000000 6.341943 -2.689216
MB_Tile_r5_176.Rotation 337.021277 0 0
MB_Tile_r5_176.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_177
MB_Tile_r5_177.Position 0.000000 6.428261 -2.475798
MB_Tile_r5_177.Rotation 338.936170 0 0
MB_Tile_r5_177.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_178
MB_Tile_r5_178.Position 0.000000 6.507400 -2.259616
MB_Tile_r5_178.Rotation 340.851064 0 0
MB_Tile_r5_178.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_179
MB_Tile_r5_179.Position 0.000000 6.579271 -2.040909
MB_Tile_r5_179.Rotation 342.765957 0 0
MB_Tile_r5_179.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_180
MB_Tile_r5_180.Position 0.000000 6.643794 -1.819923
MB_Tile_r5_180.Rotation 344.680851 0 0
MB_Tile_r5_180.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_181
MB_Tile_r5_181.Position 0.000000 6.700897 -1.596905
MB_Tile_r5_181.Rotation 346.595745 0 0
MB_Tile_r5_181.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_182
MB_Tile_r5_182.Position 0.000000 6.750515 -1.372103
MB_Tile_r5_182.Rotation 348.510638 0 0
MB_Tile_r5_182.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_183
MB_Tile_r5_183.Position 0.000000 6.792594 -1.145768
MB_Tile_r5_183.Rotation 350.425532 0 0
MB_Tile_r5_183.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_184
MB_Tile_r5_184.Position 0.000000 6.827087 -0.918154
MB_Tile_r5_184.Rotation 352.340426 0 0
MB_Tile_r5_184.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_185
MB_Tile_r5_185.Position 0.000000 6.853955 -0.689514
MB_Tile_r5_185.Rotation 354.255319 0 0
MB_Tile_r5_185.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_186
MB_Tile_r5_186.Position 0.000000 6.873167 -0.460104
MB_Tile_r5_186.Rotation 356.170213 0 0
MB_Tile_r5_186.Mother InstrumentFrame
MB_Tile.Copy MB_Tile_r5_187
MB_Tile_r5_187.Position 0.000000 6.884703 -0.230181
MB_Tile_r5_187.Rotation 358.085106 0 0
MB_Tile_r5_187.Mother InstrumentFrame

// --- support structure (scaled from project OF1 model) ---
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

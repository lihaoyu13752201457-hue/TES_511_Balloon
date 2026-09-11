# Custom materials for DEMO2_DR_v2p2_cu64fix.
Include $(MEGALIB)/resource/examples/geomega/materials/Materials.geo

Material Nb
Nb.Density 8.57
Nb.Component Nb 1

Material W
W.Density 19.30
W.Component W 1

Material Ta
Ta.Density 16.69
Ta.Component Ta 1

Material Be
Be.Density 1.85
Be.Component Be 1

# Standard MEGAlib already defines CsI; use that material name in volumes.

Material Cryoperm
Cryoperm.Density 8.70
Cryoperm.Component Ni 4
Cryoperm.Component Fe 1

Material LowCarbonSteel
LowCarbonSteel.Density 7.87
LowCarbonSteel.Component Fe 99
LowCarbonSteel.Component C 1

Material StainlessSteel
StainlessSteel.Density 8.00
StainlessSteel.Component Fe 70
StainlessSteel.Component Cr 18
StainlessSteel.Component Ni 10
StainlessSteel.Component Mn 2

Material G10
G10.Density 1.85
G10.Component Si 1
G10.Component O 2
G10.Component C 3
G10.Component H 3

Material Kapton
Kapton.Density 1.42
Kapton.Component C 22
Kapton.Component H 10
Kapton.Component N 2
Kapton.Component O 5

Material CuNi
CuNi.Density 8.90
CuNi.Component Cu 7
CuNi.Component Ni 3

Material SilverSinterProxy
SilverSinterProxy.Density 5.00
SilverSinterProxy.Component Ag 1

Material CharcoalTrapProxy
CharcoalTrapProxy.Density 1.20
CharcoalTrapProxy.Component C 1

Material NbTiCableProxy
NbTiCableProxy.Density 6.50
NbTiCableProxy.Component Nb 1
NbTiCableProxy.Component Ti 1


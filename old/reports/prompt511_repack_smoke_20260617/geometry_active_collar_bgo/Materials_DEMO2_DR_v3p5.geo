# Custom materials for DEMO2_DR_v3p5 center-finger MEGAlib proxy.
Include $(MEGALIB)/resource/examples/geomega/materials/Materials.geo

# Copper, Aluminium, Silicon, CsI, and Vacuum are taken from MEGAlib standard materials.

Material Nb
Nb.Density 8.57
Nb.Component Nb 1

Material W
W.Density 19.3
W.Component W 1

Material Ta
Ta.Density 16.69
Ta.Component Ta 1

Material Be
Be.Density 1.85
Be.Component Be 1

Material Cryoperm
Cryoperm.Density 8.7
Cryoperm.Component Ni 4
Cryoperm.Component Fe 1

Material StainlessSteel
StainlessSteel.Density 8
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
CuNi.Density 8.9
CuNi.Component Cu 7
CuNi.Component Ni 3

Material SilverSinterProxy
SilverSinterProxy.Density 5
SilverSinterProxy.Component Ag 1

Material CharcoalProxy
CharcoalProxy.Density 1.2
CharcoalProxy.Component C 1

Material NbTiCableProxy
NbTiCableProxy.Density 6.5
NbTiCableProxy.Component Nb 1
NbTiCableProxy.Component Ti 1


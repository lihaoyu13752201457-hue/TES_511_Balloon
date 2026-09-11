// Minimal host so the InstrumentFrame mother resolves.
Volume WorldVolume
WorldVolume.Material Vacuum
WorldVolume.Shape BRIK 100 100 100
WorldVolume.Mother 0

Volume InstrumentFrame
InstrumentFrame.Material Vacuum
InstrumentFrame.Shape BRIK 60 60 60
InstrumentFrame.Position 0 0 0
InstrumentFrame.Mother WorldVolume

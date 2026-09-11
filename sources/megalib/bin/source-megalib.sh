# MEGAlib Environment Setup
export MEGALIB=~/MEGAlib_Install/megalib-main
source ~/MEGAlib_Install/megalib-main/external/root_v6.36.6/bin/thisroot.sh
source ~/MEGAlib_Install/megalib-main/external/geant4_v10.02.p03/bin/geant4.sh
export PATH=$MEGALIB/bin:$PATH
export LD_LIBRARY_PATH=$MEGALIB/lib:$LD_LIBRARY_PATH
echo "MEGAlib environment (ROOT + Geant4) initialized!"

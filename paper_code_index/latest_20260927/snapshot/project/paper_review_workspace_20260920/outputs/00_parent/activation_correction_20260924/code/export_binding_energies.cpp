#include "G4AtomicShells.hh"
#include "G4SystemOfUnits.hh"
#include <iostream>
#include <iomanip>
int main(){
  std::cout<<std::setprecision(17)<<"Z,K_binding_keV\n";
  for(int z=1;z<=100;++z)std::cout<<z<<','<<G4AtomicShells::GetBindingEnergy(z,0)/keV<<'\n';
}

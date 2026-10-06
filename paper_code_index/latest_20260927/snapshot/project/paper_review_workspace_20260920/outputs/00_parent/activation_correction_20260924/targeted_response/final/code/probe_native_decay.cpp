// Isolated native nuclear-decay kernel diagnostic; no detector transport.
#include "G4SystemOfUnits.hh"
#include "G4ParticleTable.hh"
#include "G4IonTable.hh"
#include "G4GenericIon.hh"
#include "G4ProcessManager.hh"
#include "G4NuclideTable.hh"
#include "G4BosonConstructor.hh"
#include "G4LeptonConstructor.hh"
#include "G4BaryonConstructor.hh"
#include "G4MesonConstructor.hh"
#include "G4IonConstructor.hh"
#include "G4RadioactiveDecay.hh"
#include "G4DecayTable.hh"
#include "G4DecayProducts.hh"
#include "G4DynamicParticle.hh"
#include "G4VDecayChannel.hh"
#include "G4Ions.hh"
#include "Randomize.hh"
#include <map>
#include <fstream>
#include <iostream>
#include <iomanip>

int main(int argc,char** argv) {
  if(argc!=3)return 2;
  G4BosonConstructor().ConstructParticle();G4LeptonConstructor().ConstructParticle();
  G4BaryonConstructor().ConstructParticle();G4MesonConstructor().ConstructParticle();G4IonConstructor().ConstructParticle();
  auto generic=G4GenericIon::GenericIonDefinition();generic->SetProcessManager(new G4ProcessManager(generic));
  G4ParticleTable::GetParticleTable()->SetReadiness(true);
  G4NuclideTable::GetInstance()->SetLevelTolerance(100*eV);
  G4NuclideTable::GetInstance()->SetThresholdOfHalfLife(.0001*ns);
  CLHEP::HepRandom::setTheSeed(26092438);
  auto& decay=*new G4RadioactiveDecay;
  decay.SetHLThreshold(1e-9*second);decay.SetICM(true);decay.SetARM(false);decay.SetVerboseLevel(0);
  std::ifstream f(argv[1]);std::ofstream out(argv[2]);
  out<<std::setprecision(17)<<"parent\tza\texc_keV\tvalid\tcount\tdaughter\tdaughter_exc_keV\n";
  int za,draws;double ex;
  while(f>>za>>ex>>draws) {
    auto p=dynamic_cast<G4Ions*>(G4IonTable::GetIonTable()->GetIon(za/1000,za%1000,ex*keV));
    auto t=decay.LoadDecayTable(*p);std::map<std::tuple<int,std::string,double>,int> counts;
    for(int k=0;k<draws;++k) {
      auto channel=t->SelectADecayChannel(p->GetPDGMass()+30*MeV);
      auto products=channel->DecayIt(p->GetPDGMass());
      int valid=products->entries()!=1;bool any=false;
      for(int j=0;j<products->entries();++j) {
        auto child=dynamic_cast<G4Ions*>((*products)[j]->GetDefinition());
        if(child&&child->GetAtomicNumber()>2) {
          ++counts[std::make_tuple(valid,child->GetParticleName(),child->GetExcitationEnergy()/keV)];any=true;
        }
      }
      if(!any)++counts[std::make_tuple(valid,"none",0.)];
      delete products;
    }
    for(auto item:counts)out<<p->GetParticleName()<<'\t'<<za<<'\t'<<p->GetExcitationEnergy()/keV<<'\t'<<std::get<0>(item.first)<<'\t'<<item.second<<'\t'<<std::get<1>(item.first)<<'\t'<<std::get<2>(item.first)<<'\n';
    std::cout<<p->GetParticleName()<<" complete\n";
  }
}

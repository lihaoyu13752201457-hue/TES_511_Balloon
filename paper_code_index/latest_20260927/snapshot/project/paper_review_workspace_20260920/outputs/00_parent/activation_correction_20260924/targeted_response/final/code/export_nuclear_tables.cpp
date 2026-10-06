// Inspect the installed Geant4 nuclear tables. No detector transport is run.
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
#include "G4VDecayChannel.hh"
#include "G4Ions.hh"
#include "G4NuclearLevelStore.hh"
#include "G4NuclearLevelManager.hh"
#include "G4NuclearLevel.hh"
#include "G4NuclearLevelData.hh"
#include "G4LevelManager.hh"
#include "G4NucLevel.hh"
#include "G4PhotonEvaporation.hh"
#include "G4Fragment.hh"
#include "Randomize.hh"
#include <map>
#include <fstream>
#include <iostream>
#include <iomanip>
#include <set>
#include <deque>
#include <cmath>
int main(int argc,char**argv){
 if(argc!=3)return 2;
 G4BosonConstructor().ConstructParticle();G4LeptonConstructor().ConstructParticle();
 G4BaryonConstructor().ConstructParticle();G4MesonConstructor().ConstructParticle();G4IonConstructor().ConstructParticle();
 auto generic=G4GenericIon::GenericIonDefinition();generic->SetProcessManager(new G4ProcessManager(generic));
 G4ParticleTable::GetParticleTable()->SetReadiness(true);
 G4NuclideTable::GetInstance()->SetLevelTolerance(100*eV);
 G4NuclideTable::GetInstance()->SetThresholdOfHalfLife(0.0001*ns);
 CLHEP::HepRandom::setTheSeed(26092437);
 // Standalone inspection has no Geant4 run-manager teardown. Keep the process
 // alive until process exit to avoid the old messenger's teardown assumption.
 auto& decay=*new G4RadioactiveDecay;decay.SetHLThreshold(1e-9*second);decay.SetICM(true);decay.SetARM(false);decay.SetVerboseLevel(0);
 std::ifstream input(argv[1]);std::ofstream out(std::string(argv[2])+"_states.tsv"),ed(std::string(argv[2])+"_channels.tsv"),lv(std::string(argv[2])+"_levels.tsv");
 out<<std::setprecision(17);ed<<std::setprecision(17);lv<<std::setprecision(17);
 out<<"name\tza\texc_keV\tlifetime_s\tstable\tn_channels\n";
 ed<<"parent\tchannel\tmode\tbr\tdaughter\tdaughter_za\tdaughter_exc_keV\n";
 lv<<"za\texc_keV\thalf_life_s\tgamma_keV\tprobability\tdaughter_exc_keV\n";
 std::ofstream outcome(std::string(argv[2])+"_outcomes.tsv");outcome<<std::setprecision(17)<<"parent\tchannel\tprobability\tvalid\n";
 std::deque<G4Ions*> todo;std::set<std::string>done;std::set<int>levels_done;
 auto ions=G4IonTable::GetIonTable();int za;double ex;
 while(input>>za>>ex){auto p=dynamic_cast<G4Ions*>(ions->GetIon(za/1000,za%1000,ex*keV));if(p)todo.push_back(p);}
 while(!todo.empty()){
  auto p=todo.front();todo.pop_front();std::string name=p->GetParticleName();if(!done.insert(name).second)continue;
  za=p->GetAtomicNumber()*1000+p->GetAtomicMass();ex=p->GetExcitationEnergy()/keV;
  auto mgr=G4NuclearLevelStore::GetInstance()->GetManager(za/1000,za%1000);
  if(mgr&&mgr->IsValid()&&levels_done.insert(za).second){
   for(int i=0;i<mgr->NumberOfLevels();++i){auto l=mgr->GetLevel(i);auto e=l->GammaEnergies();auto prob=l->GammaProbabilities();
    for(size_t g=0;g<e.size();++g){double de=l->Energy()-e[g];auto dl=mgr->NearestLevel(de);double dex=(de<0.1*keV||!dl)?0:dl->Energy()/keV;
     lv<<za<<'\t'<<l->Energy()/keV<<'\t'<<l->HalfLife()/second<<'\t'<<e[g]/keV<<'\t'<<prob[g]<<'\t'<<dex<<'\n';}}
  }
  G4DecayTable* t=nullptr;
  if(!p->GetPDGStable()||ex>0)t=decay.LoadDecayTable(*p);
  int n=t?t->entries():0;
  out<<name<<'\t'<<za<<'\t'<<ex<<'\t'<<p->GetPDGLifeTime()/second<<'\t'<<p->GetPDGStable()<<'\t'<<n<<'\n';
  // G4DecayTable retries when summed BR is below unity; reproduce its
  // accepted-channel probability, including clipping and mass checks.
  std::vector<double> effective(n,0);double cumulative=0,accepted=0;
  for(int c=0;c<n;++c){auto ch=t->GetDecayChannel(c);cumulative+=ch->GetBR();
   if(ch->IsOKWithParentMass(p->GetPDGMass()+30*MeV)){double edge=std::min(1.0,cumulative);effective[c]=std::max(0.0,edge-accepted);accepted=edge;}}
  if(accepted>0)for(auto& x:effective)x/=accepted;
  for(int c=0;c<n;++c){auto ch=t->GetDecayChannel(c);double channel_br=effective[c];if(channel_br==0)continue;
   // RDM kills one-product outcomes before Cosima can schedule a daughter.
   // This occurs for zero-energy IT and beta-plus channels with negative Q.
   // Atomic relaxation is disabled only in this outcome-count diagnostic;
   // it does not change a valid nuclear channel into a one-product outcome.
   bool valid=true;
   if(ch->GetKinematicsName()=="beta+ decay"||ch->GetKinematicsName()=="IT decay"){
    auto trial=ch->DecayIt(p->GetPDGMass());valid=trial->entries()!=1;delete trial;
   }
   outcome<<name<<'\t'<<c<<'\t'<<channel_br<<'\t'<<valid<<'\n';
   if(!valid){std::cerr<<"ONE_PRODUCT_KILLED "<<name<<" channel="<<c<<" probability="<<channel_br<<'\n';continue;}
   // IT's declared daughter is not its sampled daughter: DecayIt asks the
   // modern photon-level manager for one transition. Export that transition.
   if(ch->GetKinematicsName()=="IT decay"&&ex>0){
    G4Fragment testnuc(za%1000,za/1000,G4LorentzVector(G4ThreeVector(),p->GetPDGMass()));
    // Use the same mass-subtracted excitation as G4ITDecay. Micro-eV
    // rounding can select a different member of near-degenerate level data.
    const double actualExc=testnuc.GetExcitationEnergy();
    auto pm=G4NuclearLevelData::GetInstance()->GetLevelManager(za/1000,za%1000);
    if(!pm||actualExc>pm->MaxLevelEnergy()+0.1*keV){
     // Above the discrete level table Geant4 uses a continuum photon model.
     // Inspect that same model, stopping at the first discrete level; this
     // is an isolated nuclear-kernel calculation, with no detector transport.
     const int samples=32768;std::map<G4Ions*,int> outcomes;int failed=0;
     G4PhotonEvaporation evap;evap.RDMForced(true);evap.SetICM(true);
     for(int draw=0;draw<samples;++draw){
      G4Fragment nuc(za%1000,za/1000,G4LorentzVector(G4ThreeVector(),p->GetPDGMass()));
      bool valid=false;double energy=ex*keV;
      for(int step=0;step<128;++step){
       auto gamma=evap.EmittedFragment(&nuc);delete gamma;double now=nuc.GetExcitationEnergy();
       if(now<1*keV){energy=0;valid=true;break;}
       if(pm&&now<=pm->MaxLevelEnergy()+0.1*keV){energy=now;valid=true;break;}
       if(!(now<energy-1e-9*keV))break;energy=now;
      }
      if(!valid){++failed;continue;}
      auto d=dynamic_cast<G4Ions*>(ions->GetIon(za/1000,za%1000,energy));++outcomes[d];
     }
     std::cerr<<"CONTINUUM_IT "<<name<<" samples="<<samples<<" failures="<<failed<<" outcomes="<<outcomes.size()<<'\n';
     for(auto item:outcomes){auto d=item.first;
      ed<<name<<'\t'<<c<<'\t'<<"IT continuum sampled 32768"<<'\t'<<channel_br*item.second/samples<<'\t'<<d->GetParticleName()<<'\t'<<za<<'\t'<<d->GetExcitationEnergy()/keV<<'\n';
      if(d!=p)todo.push_back(d);
     }
     continue;
    }
    auto idx=pm->NearestLevelIndex(actualExc);if(idx==0){std::cerr<<"ZERO_IT_LEVEL "<<name<<'\n';continue;}
    auto level=pm->GetLevel(idx);if(level->IsXLevel()&&idx>0)level=pm->GetLevel(--idx);
    if(level->IsXLevel()){std::cerr<<"UNRESOLVED_XLEVEL "<<name<<'\n';continue;}
    double previous=0;
    for(size_t g=0;g<level->NumberOfTransitions();++g){
     double boundary=1;
     if(g+1<level->NumberOfTransitions()){
      double lo=0,hi=1;for(int it=0;it<48;++it){double mid=(lo+hi)*.5;if(level->SampleGammaETransition(mid)<=g)lo=mid;else hi=mid;}boundary=(lo+hi)*.5;
     }
     double prob=boundary-previous;previous=boundary;if(prob<=0)continue;
     double de=level->FinalExcitationEnergy(g);if(de<1*keV)de=0;
     auto d=dynamic_cast<G4Ions*>(ions->GetIon(za/1000,za%1000,de));
     ed<<name<<'\t'<<c<<'\t'<<"IT photon transition"<<'\t'<<channel_br*prob<<'\t'<<d->GetParticleName()<<'\t'<<za<<'\t'<<d->GetExcitationEnergy()/keV<<'\n';
     if(d!=p)todo.push_back(d);else std::cerr<<"IT_SELF "<<name<<'\n';
    }
    continue;
   }
   for(int k=0;k<ch->GetNumberOfDaughters();++k){auto d=dynamic_cast<G4Ions*>(ch->GetDaughter(k));if(!d)continue;
    int dz=d->GetAtomicNumber()*1000+d->GetAtomicMass();
    ed<<name<<'\t'<<c<<'\t'<<ch->GetKinematicsName()<<'\t'<<channel_br<<'\t'<<d->GetParticleName()<<'\t'<<dz<<'\t'<<d->GetExcitationEnergy()/keV<<'\n';
    if(dz>2004&&d!=p)todo.push_back(d);
   }
  }
 }
 std::cout<<"Exported states "<<done.size()<<", nuclide level sets "<<levels_done.size()<<"\n";
}

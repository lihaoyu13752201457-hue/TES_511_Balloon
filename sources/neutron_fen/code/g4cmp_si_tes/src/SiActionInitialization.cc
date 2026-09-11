#include "SiActionInitialization.hh"

#include "G4CMPStackingAction.hh"
#include "SiPrimaryGeneratorAction.hh"

void SiActionInitialization::Build() const {
  SetUserAction(new SiPrimaryGeneratorAction(config_, groups_));
  SetUserAction(new G4CMPStackingAction);
}

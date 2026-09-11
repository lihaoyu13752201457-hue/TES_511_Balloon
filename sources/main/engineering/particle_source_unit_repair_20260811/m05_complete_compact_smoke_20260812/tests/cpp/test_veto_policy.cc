#include "M05VetoPolicy.hh"

#include <iostream>

int main()
{
  // Binding regression: O8 30-keV BGO + 30-keV plastic is a 60-keV veto.
  if (M05ActiveVetoTotalKeV("s3d_o8", 0.0, 30.0, 30.0) != 60.0) return 1;
  if (!M05PassActiveVeto("s3d_o8", 0.0, 30.0, 30.0, 50.0)) return 2;
  if (!M05PassActiveVeto("s3d_o8", 0.0, 30.0, 30.0, 70.0)) return 3;
  if (!M05PassActiveVeto("s3d_o8", 0.0, 30.0, 30.0, 80.0)) return 4;
  if (M05PassActiveVeto("mass_model_511", 50.0, 0.0, 0.0, 50.0)) return 5;
  if (M05PassActiveVeto("s3d_o8", 0.0, 50.0, 0.0, 50.0)) return 6;
  if (M05PassActiveVeto("s3d_o8", 0.0, 30.0, 50.0, 80.0)) return 7;
  std::cout << "PASS veto_policy_nontransport\n";
  return 0;
}

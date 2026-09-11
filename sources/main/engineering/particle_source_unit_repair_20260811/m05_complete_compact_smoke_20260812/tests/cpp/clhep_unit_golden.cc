#include "G4ThreeVector.hh"

#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>

int main(int argc, char** argv)
{
  if (argc != 4) return 2;
  const G4ThreeVector input(std::stod(argv[1]), std::stod(argv[2]), std::stod(argv[3]));
  const G4ThreeVector output = input.unit();
  for (int i = 0; i < 3; ++i) {
    std::uint64_t bits = 0;
    const double value = output[i];
    std::memcpy(&bits, &value, sizeof(bits));
    if (i != 0) std::cout << ' ';
    std::cout << std::hex << std::setw(16) << std::setfill('0') << bits;
  }
  std::cout << '\n';
  return 0;
}

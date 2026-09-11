#include "G4SystemOfUnits.hh"

#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>

int main(int argc, char** argv)
{
  if (argc < 2) return 2;
  double previousInternal = 0.0;
  for (int i = 1; i < argc; ++i) {
    const double parsedInternal = std::stod(argv[i])*second;
    const double next = parsedInternal - previousInternal;
    const double currentInternal = next + previousInternal;
    const double seconds = currentInternal/second;
    std::uint64_t bits = 0;
    std::memcpy(&bits, &seconds, sizeof(bits));
    if (i != 1) std::cout << ' ';
    std::cout << std::hex << std::setw(16) << std::setfill('0') << bits;
    previousInternal = currentInternal;
  }
  std::cout << '\n';
  return 0;
}

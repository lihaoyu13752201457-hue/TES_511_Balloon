#include "G4SystemOfUnits.hh"
#include "G4ThreeVector.hh"

#include <openssl/sha.h>

#include <cmath>
#include <cstdint>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <string>

int main(int argc, char** argv)
{
  if (argc != 14) return 2;
  const int particle = std::stoi(argv[1]);
  double raw[12];
  for (int i = 0; i < 12; ++i) raw[i] = std::stod(argv[i+2]);
  const G4ThreeVector direction(raw[5], raw[6], raw[7]);
  const G4ThreeVector unit = direction.unit();
  const double values[12] = {
    raw[0], (raw[1]*second)/second,
    (raw[2]*cm)/cm, (raw[3]*cm)/cm, (raw[4]*cm)/cm,
    unit.x(), unit.y(), unit.z(), raw[8], raw[9], raw[10], (raw[11]*keV)/keV
  };
  static const char domain[] = "m05-eventlist-binary64-v1";
  static_assert(sizeof(domain) == 26, "domain length drift");
  std::string payload(domain, sizeof(domain));
  const std::uint32_t particleBits = static_cast<std::uint32_t>(particle);
  for (int shift = 24; shift >= 0; shift -= 8) {
    payload.push_back(static_cast<char>((particleBits >> shift) & 0xffU));
  }
  for (double value : values) {
    if (!std::isfinite(value)) return 3;
    std::uint64_t bits = 0;
    std::memcpy(&bits, &value, sizeof(bits));
    for (int shift = 56; shift >= 0; shift -= 8) {
      payload.push_back(static_cast<char>((bits >> shift) & 0xffULL));
    }
    std::cout << std::hex << std::setw(16) << std::setfill('0') << bits << ' ';
  }
  unsigned char digest[SHA256_DIGEST_LENGTH];
  ::SHA256(reinterpret_cast<const unsigned char*>(payload.data()), payload.size(), digest);
  for (unsigned char byte : digest) {
    std::cout << std::hex << std::setw(2) << std::setfill('0') << static_cast<unsigned int>(byte);
  }
  std::cout << '\n';
  return 0;
}

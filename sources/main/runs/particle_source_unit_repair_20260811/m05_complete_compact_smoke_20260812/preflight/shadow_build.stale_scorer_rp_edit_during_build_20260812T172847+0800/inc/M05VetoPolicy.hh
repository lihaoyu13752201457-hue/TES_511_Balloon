#ifndef __M05VetoPolicy__
#define __M05VetoPolicy__

#include <cmath>
#include <stdexcept>
#include <string>

// Pure, zero-Geant4 policy used by the online scorer and a non-transport
// fixture. active_veto_total_keV is diagnostic only.  Retained F semantics are
// Mass: CsI<T; O8: BGO<T AND plastic<50 keV for every T in {50,70,80}.
inline double M05ActiveVetoTotalKeV(const std::string& geometry,
                                    double massCSIKeV,
                                    double o8BGOKeV,
                                    double o8PlasticKeV)
{
  if (!std::isfinite(massCSIKeV) || !std::isfinite(o8BGOKeV) ||
      !std::isfinite(o8PlasticKeV) || massCSIKeV < 0.0 || o8BGOKeV < 0.0 ||
      o8PlasticKeV < 0.0) {
    throw std::runtime_error("M05 veto policy received invalid energy");
  }
  if (geometry == "mass_model_511") return massCSIKeV;
  if (geometry == "s3d_o8") return o8BGOKeV + o8PlasticKeV;
  throw std::runtime_error("M05 veto policy received unknown geometry");
}

inline bool M05PassActiveVeto(const std::string& geometry,
                              double massCSIKeV,
                              double o8BGOKeV,
                              double o8PlasticKeV,
                              double thresholdKeV)
{
  if (!std::isfinite(thresholdKeV) || thresholdKeV <= 0.0) {
    throw std::runtime_error("M05 veto policy received invalid threshold");
  }
  // Validate all inputs through the diagnostic-total helper first.
  (void) M05ActiveVetoTotalKeV(geometry, massCSIKeV, o8BGOKeV, o8PlasticKeV);
  if (geometry == "mass_model_511") return massCSIKeV < thresholdKeV;
  if (geometry == "s3d_o8") return o8BGOKeV < thresholdKeV && o8PlasticKeV < 50.0;
  throw std::runtime_error("M05 veto policy received unknown geometry");
}

#endif

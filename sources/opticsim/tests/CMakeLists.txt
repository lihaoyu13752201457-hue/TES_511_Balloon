cmake_minimum_required(VERSION 3.12)
project(opticsim LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Geant4 QUIET)

if(Geant4_FOUND)
  include(${Geant4_USE_FILE})
  add_library(gamma_optics_geant4
    geant4_app/src/optics/GammaChannelReflection.cc
  )
  target_include_directories(gamma_optics_geant4 PUBLIC geant4_app/include)
  target_link_libraries(gamma_optics_geant4 PUBLIC ${Geant4_LIBRARIES})

  add_executable(channel_two_wall_demo
    geant4_app/src/channel_two_wall_demo.cc
  )
  target_include_directories(channel_two_wall_demo PRIVATE geant4_app/include)
  target_link_libraries(channel_two_wall_demo PRIVATE gamma_optics_geant4 ${Geant4_LIBRARIES})
else()
  message(WARNING "Geant4 CMake package was not found; Python baselines remain available.")
endif()

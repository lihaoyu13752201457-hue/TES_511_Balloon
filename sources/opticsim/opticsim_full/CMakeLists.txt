cmake_minimum_required(VERSION 3.12)
project(opticsim_full_bfull LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Geant4 REQUIRED)
include(${Geant4_USE_FILE})

add_library(laue_bfull_core
  geant4_app/src/optics/LaueEfficiencyTable.cc
)
target_include_directories(laue_bfull_core PUBLIC geant4_app/include)
target_link_libraries(laue_bfull_core PUBLIC ${Geant4_LIBRARIES})

add_executable(laue_multiring_bfull_demo
  geant4_app/src/laue_multiring_bfull_demo.cc
)
target_include_directories(laue_multiring_bfull_demo PRIVATE geant4_app/include)
target_link_libraries(laue_multiring_bfull_demo PRIVATE laue_bfull_core ${Geant4_LIBRARIES})

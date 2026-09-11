cmake_minimum_required(VERSION 3.16)
project(sh3_g4cmp_si_tes LANGUAGES CXX)

set(CMAKE_PREFIX_PATH "$ENV{G4CMPINSTALL}/../..")
find_package(G4CMP REQUIRED)
include($ENV{G4CMPINSTALL}/FindGeant4.cmake)

include_directories(${CMAKE_CURRENT_SOURCE_DIR}/include)
include_directories(${G4CMP_INCLUDE_DIRS})
include(${G4CMP_USE_FILE})
include(${Geant4_USE_FILE})

set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT DEFINED CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD ${G4CMP_CXX_STANDARD})
endif()

add_executable(sh3_g4cmp_si_tes
  src/main.cc
  src/SimulationData.cc
  src/SiDetectorConstruction.cc
  src/SiPrimaryGeneratorAction.cc
  src/SiActionInitialization.cc
  src/SiPhononSensitivity.cc
)
target_link_libraries(sh3_g4cmp_si_tes ${G4CMP_LIBRARIES} ${Geant4_LIBRARIES})

message(STATUS "Found G4CMP: ${G4CMP_VERSION}")
message(STATUS "Using C++ standard: ${CMAKE_CXX_STANDARD}")

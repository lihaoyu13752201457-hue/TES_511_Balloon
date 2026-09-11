cmake_minimum_required(VERSION 3.12)
project(opticsim LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Geant4 QUIET)

if(Geant4_FOUND)
  include(${Geant4_USE_FILE})
  add_library(gamma_optics_geant4
    geant4_app/src/optics/GammaChannelReflection.cc
    geant4_app/src/optics/LaueEfficiencyTable.cc
    geant4_app/src/optics/ReflectivityTable.cc
  )
  target_include_directories(gamma_optics_geant4 PUBLIC geant4_app/include)
  target_link_libraries(gamma_optics_geant4 PUBLIC ${Geant4_LIBRARIES})

  add_executable(channel_two_wall_demo
    geant4_app/src/channel_two_wall_demo.cc
  )
  target_include_directories(channel_two_wall_demo PRIVATE geant4_app/include)
  target_link_libraries(channel_two_wall_demo PRIVATE gamma_optics_geant4 ${Geant4_LIBRARIES})

  add_executable(channel_two_wall_table_demo
    geant4_app/src/channel_two_wall_table_demo.cc
  )
  target_include_directories(channel_two_wall_table_demo PRIVATE geant4_app/include)
  target_link_libraries(channel_two_wall_table_demo PRIVATE gamma_optics_geant4 ${Geant4_LIBRARIES})

  add_executable(channel_single_curved_demo
    geant4_app/src/channel_single_curved_demo.cc
  )
  target_include_directories(channel_single_curved_demo PRIVATE geant4_app/include)
  target_link_libraries(channel_single_curved_demo PRIVATE gamma_optics_geant4 ${Geant4_LIBRARIES})

  add_executable(detector_only_demo
    geant4_app/src/detector_only_demo.cc
  )
  target_include_directories(detector_only_demo PRIVATE geant4_app/include)
  target_link_libraries(detector_only_demo PRIVATE ${Geant4_LIBRARIES})

  add_executable(all_particle_farfield_demo
    geant4_app/src/all_particle_farfield_demo.cc
  )
  target_include_directories(all_particle_farfield_demo PRIVATE geant4_app/include)
  target_link_libraries(all_particle_farfield_demo PRIVATE ${Geant4_LIBRARIES})

  add_executable(activation_decay_focal_demo
    geant4_app/src/activation_decay_focal_demo.cc
  )
  target_include_directories(activation_decay_focal_demo PRIVATE geant4_app/include)
  target_link_libraries(activation_decay_focal_demo PRIVATE ${Geant4_LIBRARIES})

  add_executable(laue_one_ring_demo
    geant4_app/src/laue_one_ring_demo.cc
  )
  target_include_directories(laue_one_ring_demo PRIVATE geant4_app/include)
  target_link_libraries(laue_one_ring_demo PRIVATE ${Geant4_LIBRARIES})

  add_executable(laue_one_ring_table_demo
    geant4_app/src/laue_one_ring_table_demo.cc
  )
  target_include_directories(laue_one_ring_table_demo PRIVATE geant4_app/include)
  target_link_libraries(laue_one_ring_table_demo PRIVATE gamma_optics_geant4 ${Geant4_LIBRARIES})

  add_executable(laue_multiring_table_demo
    geant4_app/src/laue_multiring_table_demo.cc
  )
  target_include_directories(laue_multiring_table_demo PRIVATE geant4_app/include)
  target_link_libraries(laue_multiring_table_demo PRIVATE gamma_optics_geant4 ${Geant4_LIBRARIES})

  add_executable(laue_multiring_darwin_guan_demo
    geant4_app/src/laue_multiring_darwin_guan_demo.cc
  )
  target_include_directories(laue_multiring_darwin_guan_demo PRIVATE geant4_app/include)
  target_link_libraries(laue_multiring_darwin_guan_demo PRIVATE gamma_optics_geant4 ${Geant4_LIBRARIES})

  add_executable(laue_multiring_bfull_demo
    geant4_app/src/laue_multiring_bfull_demo.cc
  )
  target_include_directories(laue_multiring_bfull_demo PRIVATE geant4_app/include)
  target_link_libraries(laue_multiring_bfull_demo PRIVATE gamma_optics_geant4 ${Geant4_LIBRARIES})

  add_executable(channel_4ring_effective_demo
    geant4_app/src/channel_4ring_effective_demo.cc
  )
  target_include_directories(channel_4ring_effective_demo PRIVATE geant4_app/include)
  target_link_libraries(channel_4ring_effective_demo PRIVATE ${Geant4_LIBRARIES})

  add_executable(channel_4ring_multibounce_demo
    geant4_app/src/channel_4ring_multibounce_demo.cc
  )
  target_include_directories(channel_4ring_multibounce_demo PRIVATE geant4_app/include)
  target_link_libraries(channel_4ring_multibounce_demo PRIVATE gamma_optics_geant4 ${Geant4_LIBRARIES})
else()
  message(WARNING "Geant4 CMake package was not found; Python baselines remain available.")
endif()

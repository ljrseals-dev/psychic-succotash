cmake_minimum_required(VERSION 3.16)
project(ElevenXSpatialBridge VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

add_library(SpatialReverbBridge STATIC
    src/SpatialReverbBridge.cpp
)

target_include_directories(SpatialReverbBridge
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)

# Optional: link FFTW / PortAudio / JUCE later
# find_package(FFTW3 REQUIRED)
# target_link_libraries(SpatialReverbBridge PRIVATE FFTW3::fftw3)

add_executable(spatial_demo
    src/SpatialReverbBridge.cpp
    # add a main.cpp demo if desired
)

target_include_directories(spatial_demo PRIVATE include)

install(TARGETS SpatialReverbBridge
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
)
install(DIRECTORY include/ DESTINATION include)

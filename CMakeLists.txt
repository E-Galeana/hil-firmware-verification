# Generated Cmake Pico project file

cmake_minimum_required(VERSION 3.13)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# Initialise pico_sdk from installed location

if(WIN32)
    set(USERHOME $ENV{USERPROFILE})
else()
    set(USERHOME $ENV{HOME})
endif()
set(sdkVersion 2.2.0)
set(toolchainVersion 14_2_Rel1)
set(picotoolVersion 2.2.0-a4)
set(picoVscode ${USERHOME}/.pico-sdk/cmake/pico-vscode.cmake)
if (EXISTS ${picoVscode})
    include(${picoVscode})
endif()
# ====================================================================================
set(PICO_BOARD pico_w CACHE STRING "Board type")

include(pico_sdk_import.cmake)

project(HIL_Verification C CXX ASM)

# Initialise the Raspberry Pi Pico SDK
pico_sdk_init()


add_executable(HIL_Verification HIL_Verification.c )

pico_set_program_name(HIL_Verification "HIL_Verification")
pico_set_program_version(HIL_Verification "0.1")

pico_enable_stdio_uart(HIL_Verification 0)
pico_enable_stdio_usb(HIL_Verification 1)

target_link_libraries(HIL_Verification
        pico_stdlib)

target_include_directories(HIL_Verification PRIVATE
        ${CMAKE_CURRENT_LIST_DIR}
)

target_link_libraries(HIL_Verification 
        
        )
pico_add_extra_outputs(HIL_Verification)


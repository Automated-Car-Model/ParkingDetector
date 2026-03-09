# Generated Cmake Pico project file

cmake_minimum_required(VERSION 3.13)

set(CMAKE_C_STANDARD 11)
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

# == DO NOT EDIT THE FOLLOWING LINES for the Raspberry Pi Pico VS Code Extension to work ==
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
set(PICO_BOARD pico CACHE STRING "Board type")

#include sdk raspberry pi pico
include(pico_sdk_import.cmake)

project(ArduCAM_Pico4ML_Dev_Kit C CXX ASM)

#inizializza sdk
pico_sdk_init()

#aggiunge l'eseguibile
add_executable(ArduCAM_Pico4ML_Dev_Kit

    main.c 
    
    lib/arducam.c
    lib/st7735.c
    lib/Dev_Config.c
    lib/fonts.c

)

pico_set_program_name(ArduCAM_Pico4ML_Dev_Kit "ArduCAM_Pico4ML_Dev_Kit")
pico_set_program_version(ArduCAM_Pico4ML_Dev_Kit "0.1")

#abbilita la seriale su usb disabilitandola su uart
pico_enable_stdio_uart(ArduCAM_Pico4ML_Dev_Kit 0)
pico_enable_stdio_usb(ArduCAM_Pico4ML_Dev_Kit 1)

pico_generate_pio_header(ArduCAM_Pico4ML_Dev_Kit ${CMAKE_CURRENT_LIST_DIR}/image.pio)

#aggiunge le librerie necessarie
target_link_libraries(ArduCAM_Pico4ML_Dev_Kit

    pico_stdlib
	hardware_dma 
	hardware_i2c
	hardware_pio
	hardware_pwm
	hardware_spi
	pico_multicore
    
)

#aggiunge gli include alle librerie
target_include_directories(ArduCAM_Pico4ML_Dev_Kit PRIVATE

        ${CMAKE_CURRENT_LIST_DIR}
        ${CMAKE_CURRENT_LIST_DIR}/lib

)

pico_add_extra_outputs(ArduCAM_Pico4ML_Dev_Kit)
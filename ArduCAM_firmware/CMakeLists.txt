# Generated CMake Pico project file
# Configured for the Real-Time Free Parking Space Detection project (ArduCAM Pico4ML Dev Kit)

cmake_minimum_required(VERSION 3.13)

# Set standard C/C++ versions
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

# Specify the target board (Raspberry Pi Pico)
set(PICO_BOARD pico CACHE STRING "Board type")

# Include the Raspberry Pi Pico SDK setup script
include(pico_sdk_import.cmake)

# Define the project name and supported languages
project(ArduCAM_Pico4ML_Dev_Kit C CXX ASM)

# Initialize the Pico SDK
pico_sdk_init()

# Add the main executable and define all the source files required for the build
add_executable(ArduCAM_Pico4ML_Dev_Kit

    main.c 
    
    # ArduCAM and LCD display drivers
    lib/arducam.c
    lib/st7735.c
    lib/Dev_Config.c
    lib/fonts.c

)

# Set the program name and version for the compiled binaries
pico_set_program_name(ArduCAM_Pico4ML_Dev_Kit "ArduCAM_Pico4ML_Dev_Kit")
pico_set_program_version(ArduCAM_Pico4ML_Dev_Kit "0.1")

# Configure Standard I/O (stdio) routing
# Disable UART output (0) and enable USB CDC output (1) to transmit raw image data to the PC
pico_enable_stdio_uart(ArduCAM_Pico4ML_Dev_Kit 0)
pico_enable_stdio_usb(ArduCAM_Pico4ML_Dev_Kit 1)

# Compile the PIO (Programmable I/O) assembly file into a C header
# This is crucial for handling the high-speed parallel data coming from the camera sensor
pico_generate_pio_header(ArduCAM_Pico4ML_Dev_Kit ${CMAKE_CURRENT_LIST_DIR}/image.pio)

# Link the required hardware and system libraries to the executable
target_link_libraries(ArduCAM_Pico4ML_Dev_Kit

    pico_stdlib
    hardware_dma       # Direct Memory Access for fast image buffering
    hardware_i2c       # I2C interface for camera configuration
    hardware_pio       # Programmable I/O for camera data capture
    hardware_pwm       # Pulse Width Modulation (e.g., for LCD backlight)
    hardware_spi       # SPI interface for the ST7735 LCD display
    pico_multicore     # Multicore support to run capture/USB tasks on Core 1
    
)

# Add directories to the compiler's include path so header files can be found
target_include_directories(ArduCAM_Pico4ML_Dev_Kit PRIVATE

        ${CMAKE_CURRENT_LIST_DIR}
        ${CMAKE_CURRENT_LIST_DIR}/lib

)

# Generate extra build outputs (e.g., the .uf2 file used to flash the Pico via drag-and-drop)
pico_add_extra_outputs(ArduCAM_Pico4ML_Dev_Kit)
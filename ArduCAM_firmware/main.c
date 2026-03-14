#include <stdio.h>
#include <stdlib.h>
#include "pico/stdlib.h"
#include <tusb.h>
#include "pico/multicore.h"
#include "lib/arducam.h"
#include "lib/st7735.h"
#include "lib/fonts.h"
#include "hardware/vreg.h"
#include "hardware/clocks.h"
#include "pico/stdio_usb.h" 

// Output display and USB stream resolution (cropped and downsampled)
#define VIEW_W 80
#define VIEW_H 160

// Full image buffer (captured by the raw camera sensor)
uint8_t image_buf[324 * 324];

// Buffer for the ST7735 LCD display (requires 16-bit RGB565 format)
uint8_t displayBuf[VIEW_W * VIEW_H * 2];

// Header pattern to synchronize with the PC receiver (prevents frame tearing)
const uint8_t SYNC_PATTERN[4] = {0xAA, 0xBB, 0xCC, 0xDD};

// Temporary buffer to send an entire image row via USB
uint8_t usb_line_buf[VIEW_W];

/**
 * @brief Core 1 entry point.
 * This core handles the camera capture, image processing, display updating,
 * and USB transmission, leaving Core 0 free for other potential tasks.
 */
void core1_entry() {

    // Initialize the onboard LED to indicate system activity
    gpio_init(PIN_LED);
    gpio_set_dir(PIN_LED, GPIO_OUT);

    // Initialize the ST7735 LCD screen and draw the startup logo
    ST7735_Init();
    ST7735_DrawImage(0, 0, 80, 160, arducam_logo);

    // Configure the ArduCAM sensor (HM01B0) hardware interfaces
    struct arducam_config config;
    config.sccb = i2c0;                     // I2C interface for camera control
    config.sccb_mode = I2C_MODE_16_8;       // 16-bit register address, 8-bit value
    config.sensor_address = 0x24;           // I2C address of the sensor
    config.pin_sioc = PIN_CAM_SIOC;         // I2C clock pin
    config.pin_siod = PIN_CAM_SIOD;         // I2C data pin
    config.pin_resetb = PIN_CAM_RESETB;     // Camera reset pin
    config.pin_xclk = PIN_CAM_XCLK;         // External clock pin
    config.pin_vsync = PIN_CAM_VSYNC;       // Vertical sync pin
    config.pin_y2_pio_base = PIN_CAM_Y2_PIO_BASE; // Base pin for parallel data output
    config.pio = pio0;                      // PIO instance used for data capture
    config.pio_sm = 0;                      // PIO state machine index
    config.dma_channel = 0;                 // DMA channel for fast data transfer
    config.image_buf = image_buf;           // Pointer to the destination buffer
    config.image_buf_size = sizeof(image_buf);

    // Apply the configuration to the ArduCAM
    arducam_init(&config);

    // Main continuous capture and transmission loop
    while (true) {

        // Toggle the LED to visually indicate the start of a new frame
        gpio_put(PIN_LED, !gpio_get(PIN_LED));
        
        // Capture a new raw frame from the camera
        arducam_capture_frame(&config);

        // Send synchronization header to the host PC before sending frame data
        fwrite(SYNC_PATTERN, 1, 4, stdout);

        uint16_t index = 0;
        
        // Processing loop: crop and downsample the frame to 80x160
        for (int y = 0; y < 160; y++) {
            
            // Fill the row buffer for USB transmission
            for (int x = 0; x < 80; x++) {

                // Extract grayscale pixel (using native Arducam raw coordinates)
                // The formula maps the 80x160 output window to the center of the 324x324 raw buffer
                uint8_t c = image_buf[(2 + 320 - 2 * y) * 324 + (2 + 40 + 2 * x)];

                // Prepare pixel for LCD (Convert 8-bit Grayscale to 16-bit RGB565 format)
                uint16_t imageRGB = ST7735_COLOR565(c, c, c);
                displayBuf[index++] = (uint8_t)(imageRGB >> 8) & 0xFF;
                displayBuf[index++] = (uint8_t)(imageRGB) & 0xFF;

                // Save the raw grayscale pixel into the USB row buffer
                usb_line_buf[x] = c;
                
            }
            
            // Send the entire row via USB (sending 80 bytes at once to optimize throughput)
            fwrite(usb_line_buf, 1, 80, stdout);

        }
        
        // Force flush the USB packet to ensure immediate transmission to the host PC
        fflush(stdout);

        // Update the onboard LCD with the newly processed frame
        ST7735_DrawImage(0, 0, 80, 160, displayBuf);

    }

}

int main() {

    // Initialize all standard I/O (USB CDC in this case)
    stdio_init_all();
    
    // Disable automatic conversion of \n (10) to \r\n (13, 10) 
    // This is crucial to prevent corruption when transmitting raw binary image data over USB
    stdio_set_translate_crlf(&stdio_usb, false);

    // Wait 2 seconds to allow the USB connection to enumerate on the host PC
    sleep_ms(2000); 

    // Overclock the RP2040 to 250MHz for better performance (default is 133MHz)
    // First, slightly increase the core voltage to support the higher clock speed
    vreg_set_voltage(VREG_VOLTAGE_1_30);
    sleep_ms(10);
    set_sys_clock_khz(250000, true); 

    // Launch the camera and USB handling routine on Core 1
    multicore_launch_core1(core1_entry);

    // Core 0 loop (idle)
    while (1) {

        // Yield the processor to save power on Core 0 while Core 1 does the heavy lifting
        tight_loop_contents();

    }

    return 0;

}
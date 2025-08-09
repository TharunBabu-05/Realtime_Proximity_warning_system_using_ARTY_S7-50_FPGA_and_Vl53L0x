#include "xgpio.h"
#include "xiic.h"
#include "xuartlite.h"
#include "xparameters.h"
#include "unistd.h"
#include "stdio.h"
#include "string.h"

#define IIC_DEVICE_ID      XPAR_AXI_IIC_0_DEVICE_ID
#define GPIO_DEVICE_ID     XPAR_AXI_GPIO_0_DEVICE_ID
#define UART_DEVICE_ID     XPAR_AXI_UARTLITE_0_DEVICE_ID
#define VL53L0X_I2C_ADDR   0x29

#define RED_LED1_MASK      0x01  // LED1 - Bit 0
#define GREEN_LED_MASK     0x02  // LED - Bit 1
#define BLUE_LED_MASK      0x04  // LED - Bit 2
#define RED_LED2_MASK      0x08  // LED2 - Bit 3 (for sensor error)

XIic IicInstance;
XGpio GpioInstance;
XUartLite UartInstance;

#define SYSRANGE_START         0x00
#define RESULT_RANGE_VAL       0x1E

// Function prototypes
int uart_init(void);
void uart_send_string(const char* str);
void uart_send_distance(u16 distance);

int uart_init() {
    int Status;
    XUartLite_Config *Config;

    // Initialize UART
    Status = XUartLite_Initialize(&UartInstance, UART_DEVICE_ID);
    if (Status != XST_SUCCESS) {
        return XST_FAILURE;
    }

    // Configure UART
    Config = XUartLite_LookupConfig(UART_DEVICE_ID);
    if (Config == NULL) {
        return XST_FAILURE;
    }

    Status = XUartLite_CfgInitialize(&UartInstance, Config, Config->RegBaseAddr);
    if (Status != XST_SUCCESS) {
        return XST_FAILURE;
    }

    return XST_SUCCESS;
}

void uart_send_string(const char* str) {
    XUartLite_Send(&UartInstance, (u8*)str, strlen(str));
    // Wait for transmission to complete
    while (XUartLite_IsSending(&UartInstance)) {
        // Wait until transmission is complete
    }
}

void uart_send_distance(u16 distance) {
    char buffer[32];
    if (distance == 0xFFFF) {
        sprintf(buffer, "distance: ERROR\r\n");
    } else {
        sprintf(buffer, "distance: %d\r\n", distance);
    }
    uart_send_string(buffer);
    usleep(100000); // 100ms delay
}

int vl53l0x_start_ranging() {
    u8 cmd[2] = {SYSRANGE_START, 0x01};
    int Status;

    XIic_Start(&IicInstance);
    Status = XIic_Send(IicInstance.BaseAddress, VL53L0X_I2C_ADDR, cmd, 2, XIIC_STOP);
    XIic_Stop(&IicInstance);

    return (Status == 2) ? XST_SUCCESS : XST_FAILURE;
}

u16 vl53l0x_read_distance() {
    u8 reg = RESULT_RANGE_VAL;
    u8 data[2];
    int Status;

    XIic_Start(&IicInstance);
    Status = XIic_Send(IicInstance.BaseAddress, VL53L0X_I2C_ADDR, &reg, 1, XIIC_REPEATED_START);
    if (Status != 1) {
        XIic_Stop(&IicInstance);
        return 0xFFFF;  // Sensor not responding
    }

    Status = XIic_Recv(IicInstance.BaseAddress, VL53L0X_I2C_ADDR, data, 2, XIIC_STOP);
    XIic_Stop(&IicInstance);

    if (Status != 2)
        return 0xFFFF;

    return (data[0] << 8) | data[1];
}

void blink_led(u32 led_mask, int delay_ms) {
    XGpio_DiscreteWrite(&GpioInstance, 1, led_mask);
    usleep(delay_ms * 1000);
    XGpio_DiscreteClear(&GpioInstance, 1, led_mask);
    usleep(delay_ms * 1000);
}

int main() {
    int Status;
    u16 distance;

    // Initialize UART
    Status = uart_init();
    if (Status != XST_SUCCESS) {
        printf("UART initialization failed\n");
        return XST_FAILURE;
    }

    // Initialize IIC
    Status = XIic_Initialize(&IicInstance, IIC_DEVICE_ID);
    if (Status != XST_SUCCESS) return XST_FAILURE;
    XIic_SetAddress(&IicInstance, XII_ADDR_TO_SEND_TYPE, VL53L0X_I2C_ADDR);

    // Initialize GPIO
    Status = XGpio_Initialize(&GpioInstance, GPIO_DEVICE_ID);
    if (Status != XST_SUCCESS) return XST_FAILURE;
    XGpio_SetDataDirection(&GpioInstance, 1, 0x0); // All outputs

    usleep(200000);  // Wait for sensor boot

    // Send startup message
    uart_send_string("distance: READY\r\n");
    printf("VL53L0X Distance Monitor Started\n");

    while (1) {
        vl53l0x_start_ranging();
        usleep(50000); // Wait for measurement

        distance = vl53l0x_read_distance();

        // Send distance via UART
        uart_send_distance(distance);

        // Control LEDs based on distance
        if (distance == 0xFFFF) {
            blink_led(RED_LED2_MASK, 100);  // Sensor not found – blink LED2 (Red)
        } else if (distance < 200) {
            blink_led(RED_LED1_MASK, 250);  // Collision detected – blink LED1 (Red)
        } else if (distance < 500) {
            blink_led(BLUE_LED_MASK, 250);  // Medium range – blink Blue
        } else {
            blink_led(GREEN_LED_MASK, 250); // Safe – blink Green
        }

        // Delay between measurements
        usleep(600000); // 600ms delay for one line per measurement
    }

    return 0;
}

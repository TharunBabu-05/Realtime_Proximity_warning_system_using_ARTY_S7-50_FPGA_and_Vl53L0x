import serial
import time

# --- Configuration ---
SERIAL_PORT = 'COM7'
SERIAL_BAUDRATE = 9600

print(f"Attempting to open {SERIAL_PORT}...")
ser = None # Initialize variable

try:
    # Open the serial port with DTR and RTS explicitly disabled
    ser = serial.Serial(SERIAL_PORT, SERIAL_BAUDRATE, timeout=0.1)
    ser.dtr = False
    ser.rts = False
    print(f"Successfully opened {SERIAL_PORT}. Waiting for data...")
    print("(Press Ctrl+C to stop)")
    time.sleep(1) # Give the port a moment to settle

    # This loop will now run correctly
    while True:
        # Check if there are any bytes waiting in the input buffer
        if ser.in_waiting > 0:
            # Read all the bytes that are waiting
            data_bytes = ser.read(ser.in_waiting)
            try:
                # Try to decode the bytes as text and print them
                data_str = data_bytes.decode('utf-8')
                print(data_str, end='', flush=True)
            except UnicodeDecodeError:
                # This handles cases where data might be corrupted
                print(f"\nReceived {len(data_bytes)} undecodable bytes.\n")
        
        # A small delay to prevent the loop from using 100% CPU
        time.sleep(0.05)

except serial.SerialException as e:
    print(f"ERROR: Could not open or read from serial port. {e}")
except KeyboardInterrupt:
    print("\nProgram stopped by user.")
finally:
    # Ensure the serial port is closed when the script exits
    if ser and ser.is_open:
        ser.close()
        print("\nSerial port closed.")
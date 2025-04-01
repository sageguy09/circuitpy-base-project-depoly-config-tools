# Main CircuitPython file with PyPortal WiFi capabilities

# Standard library imports
import time
import board
import digitalio
import busio
import displayio

# Import WiFi and network modules - using the modern approach
from adafruit_esp32spi import adafruit_esp32spi
import adafruit_requests as requests

# Try to import the home menu module if it exists
try:
    import home_menu
    has_home_menu = True
except ImportError:
    has_home_menu = False

# Secrets file with WiFi credentials
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

print("Starting CircuitPython PyPortal application...")

# Configure ESP32 WiFi
esp32_cs = digitalio.DigitalInOut(board.ESP_CS)
esp32_ready = digitalio.DigitalInOut(board.ESP_BUSY)
esp32_reset = digitalio.DigitalInOut(board.ESP_RESET)

# Set up SPI bus
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

# Connect to WiFi
def connect_to_wifi():
    print("Connecting to WiFi...")
    attempts = 0
    while not esp.is_connected and attempts < 3:
        try:
            esp.connect_AP(secrets["ssid"], secrets["password"])
            print("Connected to", secrets["ssid"])
            print("IP Address:", esp.pretty_ip(esp.ip_address))
            return True
        except Exception as e:
            print("Failed to connect to WiFi:", e)
            attempts += 1
            time.sleep(1)
    if not esp.is_connected:
        print("WiFi connection failed after 3 attempts")
        return False
    return True

# Set up requests using the modern connection manager approach
try:
    import adafruit_connection_manager
    pool = adafruit_connection_manager.get_radio_socketpool(esp)
    ssl_context = adafruit_connection_manager.get_radio_ssl_context(esp)
    requests = adafruit_requests.Session(pool, ssl_context)
    print("Using modern connection manager")
except ImportError:
    # Fall back to legacy approach if connection manager is not available
    import adafruit_esp32spi.adafruit_esp32spi_socket as socket
    requests.set_socket(socket, esp)
    print("Using legacy socket approach")

# Initialize display (needed for PyPortal)
displayio.release_displays()  # Release any previous displays

# Main function
def main():
    # Status LED (if available)
    try:
        led = digitalio.DigitalInOut(board.LED)
        led.direction = digitalio.Direction.OUTPUT
        has_led = True
    except:
        has_led = False
    
    # Try to connect to WiFi
    wifi_connected = connect_to_wifi()
    
    # If home_menu exists, use it
    if has_home_menu:
        print("Loading home menu...")
        # Home menu module will handle the application
        home_menu.run(esp=esp, requests=requests, wifi_connected=wifi_connected)
    else:
        # Basic fallback code with WiFi check
        print("Home menu not found, running basic code")
        
        while True:
            try:
                if wifi_connected:
                    # Basic internet connectivity test
                    print("Making HTTP GET request...")
                    response = requests.get("http://wifitest.adafruit.com/testwifi/index.html")
                    print("-" * 40)
                    print("Response status:", response.status_code)
                    print("Response text:", response.text)
                    print("-" * 40)
                    response.close()
                    
                if has_led:
                    # Blink LED according to WiFi status
                    blink_count = 1 if wifi_connected else 3
                    for _ in range(blink_count):
                        led.value = True
                        time.sleep(0.1)
                        led.value = False
                        time.sleep(0.1)
                
                # Wait before next check
                time.sleep(30 if wifi_connected else 5)
                
            except Exception as e:
                print("Error:", e)
                time.sleep(5)

# Start the program
main()

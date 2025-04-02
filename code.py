"""
PyPortal ArtNet DMX Controller
Implements ArtNet DMX protocol for CircuitPython
"""

import time
import board
import displayio
import terminalio
import neopixel
import os
from adafruit_display_text.label import Label

# Import proper networking modules
import busio
import digitalio
from adafruit_esp32spi import adafruit_esp32spi
import adafruit_requests

# Configuration and secrets
from secrets import secrets

# Constants for ArtNet
ARTNET_PORT = 6454
UNIVERSE = 0  # Default universe to listen to
MAX_CHANNELS = 512

# Create required directories
for directory in ('/fonts', '/images', '/data'):
    try:
        if not directory in os.listdir('/'):
            os.mkdir(directory)
    except OSError:
        pass  # Directory might already exist or cannot be created

class ArtNetController:
    """
    ArtNet DMX Controller for PyPortal
    Manages display, status indication, and DMX data processing
    """
    
    def __init__(self):
        """
        Initialize ArtNet Controller
        """
        # Configure networking
        esp32_cs = digitalio.DigitalInOut(board.ESP_CS)
        esp32_ready = digitalio.DigitalInOut(board.ESP_BUSY)
        esp32_reset = digitalio.DigitalInOut(board.ESP_RESET)
        spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
        self.esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)
        
        # Initialize requests session
        self.requests = None
        
        # Status LED for visual feedback
        self.status_led = neopixel.NeoPixel(board.NEOPIXEL, 1)
        self.status_led[0] = (0, 0, 0)  # Off initially
        
        # Set up display if available
        self.display = None
        self.display_group = None
        self.status_label = None
        self._setup_display()
        
        # DMX data storage
        self.dmx_data = bytearray(MAX_CHANNELS)
    
    def _setup_display(self):
        """Setup display and graphics"""
        try:
            # Get the display
            self.display = board.DISPLAY
            
            # Create display group
            self.display_group = displayio.Group()
            
            # Use the new API method instead of .show()
            self.display.root_group = self.display_group
            
            # Status label for displaying information
            self.status_label = Label(
                terminalio.FONT, 
                text="ArtNet DMX Controller", 
                color=0xFFFFFF, 
                x=10, 
                y=10
            )
            self.display_group.append(self.status_label)
            
            # Set display brightness
            if hasattr(self.display, 'brightness'):
                self.display.brightness = 0.8
            
            # Show initial status
            self._show_status("Initializing...")
        except (AttributeError, NameError) as e:
            print(f"Display setup error: {e}")
            self.display = None
    
    def _show_status(self, message):
        """Display status message"""
        print(message)  # Always print to serial console
        
        if self.status_label:
            self.status_label.text = message
    
    def connect_wifi(self):
        """
        Connect to WiFi network
        
        Returns:
            bool: Connection status
        """
        try:
            # Update status
            self._show_status(f"Connecting to {secrets['ssid']}...")
            
            # Connect to WiFi
            attempts = 0
            while not self.esp.is_connected and attempts < 3:
                try:
                    self.esp.connect_AP(secrets['ssid'], secrets['password'])
                    ip_address = self.esp.ip_address
                    self._show_status(f"Connected: {self.esp.pretty_ip(ip_address)}")
                    
                    # Set up requests - FIXED METHOD
                    try:
                        # Modern connection manager approach
                        import adafruit_connection_manager
                        pool = adafruit_connection_manager.get_radio_socketpool(self.esp)
                        ssl_context = adafruit_connection_manager.get_radio_ssl_context(self.esp)
                        # Create Session object instead of calling set_socket
                        self.requests = adafruit_requests.Session(pool, ssl_context)
                    except ImportError:
                        # Legacy socket approach
                        import adafruit_esp32spi.adafruit_esp32spi_socket as socket
                        socket.set_interface(self.esp)  # Set interface on socket
                        self.requests = adafruit_requests.Session(socket, self.esp)
                    
                    # Green blink for success
                    self.status_led[0] = (0, 50, 0)
                    time.sleep(0.5)
                    self.status_led[0] = (0, 0, 0)
                    
                    return True
                except Exception as e:
                    attempts += 1
                    self._show_status(f"WiFi error: {e}")
                    time.sleep(1)
            
            # Red blink for error
            self._show_status("WiFi connection failed")
            self.status_led[0] = (50, 0, 0)
            time.sleep(0.5)
            self.status_led[0] = (0, 0, 0)
            return False
            
        except Exception as e:
            self._show_status(f"WiFi Error: {e}")
            
            # Red blink for error
            self.status_led[0] = (50, 0, 0)
            time.sleep(0.5)
            self.status_led[0] = (0, 0, 0)
            
            return False
    
    def process_artnet_data(self, data):
        """
        Process incoming ArtNet DMX data
        
        Args:
            data: Raw ArtNet packet
        """
        try:
            # Basic ArtNet packet validation
            if len(data) < 18:
                return False
            
            # Check Art-Net header
            if data[0:8] != b'Art-Net\x00':
                return False
            
            # Extract universe from packet
            packet_universe = int.from_bytes(data[14:16], 'little')
            
            # Check if this is the universe we're interested in
            if packet_universe != UNIVERSE:
                return False
            
            # Extract DMX data length
            data_length = int.from_bytes(data[16:18], 'big')
            
            # Ensure we don't overflow our DMX data buffer
            data_length = min(data_length, MAX_CHANNELS)
            
            # Extract DMX data
            dmx_data = data[18:18+data_length]
            
            # Update our DMX data buffer
            self.dmx_data[0:data_length] = dmx_data
            
            # Update status LED with first 3 channels (RGB)
            if data_length >= 3:
                r = dmx_data[0]
                g = dmx_data[1]
                b = dmx_data[2]
                self.status_led[0] = (r, g, b)
                
                # Update display with DMX info
                self._show_status(f"Univ {packet_universe}: RGB=({r},{g},{b})")
            
            return True
        
        except Exception as e:
            self._show_status(f"DMX Error: {str(e)}")
            return False
    
    def main_loop(self):
        """
        Main control loop for ArtNet DMX reception
        """
        # Connect to WiFi
        if not self.connect_wifi():
            return

        # Test requests if available
        if self.requests:
            try:
                self._show_status("Testing connection...")
                response = self.requests.get("http://wifitest.adafruit.com/testwifi/index.html")
                self._show_status(f"Response: {response.status_code} OK")
                response.close()
            except Exception as e:
                self._show_status(f"Request error: {e}")
        
        # Your main loop code here
        self._show_status("Running ArtNet DMX controller...")
        # For now, just blink the LED to show we're running
        while True:
            self.status_led[0] = (0, 0, 30)  # Blue
            time.sleep(0.5)
            self.status_led[0] = (0, 0, 0)
            time.sleep(0.5)

def main():
    """
    Entry point for ArtNet DMX Controller
    """
    # Create ArtNet controller
    artnet = ArtNetController()
    
    # Run main control loop
    artnet.main_loop()

# Run the main function when the script starts
if __name__ == "__main__":
    main()
# PyPortal Base Project

A CircuitPython base project for PyPortal devices with WiFi connectivity and deployment utilities.

## Overview

This project provides a foundation for PyPortal applications, including:
- WiFi connectivity
- Basic HTTP requests
- A deployment script to easily transfer files to your PyPortal
- Support for a modular design with a home menu

## Requirements

### Python Requirements

Before using the library installation tools, make sure you have:

1. Python 3.6 or newer
2. Required Python packages:

   ```bash
   # First install pipx (if you don't have it already)
   pip install pipx
   pipx ensurepath
   
   # Then install tools with pipx
   pipx install pyserial
   pipx install circup
   
   # OR use pip directly if preferred
   pip install pyserial circup
   ```

   > **Note About Installations**:
   > 
   > - You can use either pipx or pip - the scripts support both methods
   > - Using pipx is recommended as it provides isolated environments
   > - If you encounter "command not found" after pipx install, run `pipx ensurepath`
   >   and restart your terminal

### CircuitPython Libraries

The project requires the following CircuitPython libraries (listed in requirements.txt):
- adafruit_pyportal
- adafruit_esp32spi
- adafruit_requests
- adafruit_io
- adafruit_bitmap_font
- adafruit_display_text
- adafruit_touchscreen

## Getting Started

1. Install the required Python packages as shown in the Requirements section
2. Edit the `secrets.py` file with your WiFi credentials
3. Run `deploy.py` to copy files to your PyPortal device:
   ```bash
   python3 deploy.py
   ```
4. The code will automatically connect to WiFi and perform a simple connection test

## Project Structure

- `code.py`: Main application file that runs on the PyPortal
- `deploy.py`: Utility script to deploy files to the PyPortal
- `secrets.py`: Contains WiFi credentials and other sensitive information
- `requirements.txt`: Lists required CircuitPython libraries
- `lib/`: Directory for CircuitPython libraries
- `host_scripts/`: Helper scripts for development and deployment
  - `circup_installer.py`: Installs libraries via circup
  - `install_libs.py`: Direct library installation helper
  - `scan_dependencies.py`: Analyzes code for library dependencies

## Utility Scripts

### Deployment Script (deploy.py)

The improved deployment script helps you select the correct CircuitPython device and safely transfer files:

```bash
# Basic usage
python3 deploy.py

# Skip copying helper scripts to the device
python3 deploy.py --no-helpers

# Skip backup prompt
python3 deploy.py --no-backup

# Automatic mode (select first device, skip prompts)
python3 deploy.py --auto
```

Key features:
- Automatically detects all connected CircuitPython devices
- Allows you to select from multiple devices
- Offers to backup your device before deployment
- Safely removes existing files with confirmation
- Copies project files and libraries
- Includes helper scripts for REPL-based installations
- Option to run library installation via circup

### Library Dependency Scanner

Scan your code to identify required libraries:

```bash
# Basic scan
python3 host_scripts/scan_dependencies.py

# Clean list of dependencies only
python3 host_scripts/scan_dependencies.py --clean

# Automatically update requirements.txt
python3 host_scripts/scan_dependencies.py --update

# Deep scan for hidden dependencies
python3 host_scripts/scan_dependencies.py --deep
```

### Library Installation

There are several ways to install the required libraries:

#### Method 1: Using deploy.py

When running the deployment script, select "yes" when asked to install libraries.

#### Method 2: Using circup_installer.py

```bash
# Install all libraries in requirements.txt
python3 host_scripts/circup_installer.py

# Fix ESP32SPI socket import issues
python3 host_scripts/circup_installer.py --fix-esp32spi

# Install only essential PyPortal libraries
python3 host_scripts/circup_installer.py --essential-only

# Monitor REPL for installation requests
python3 host_scripts/circup_installer.py --monitor
```

#### Method 3: REPL-Triggered Installation

There are two ways to trigger installation from the REPL:

##### Option A: Using install_req.py
1. Make sure install_req.py is on your CircuitPython device (deploy.py copies it)
2. Connect to your device's REPL
3. In the REPL, import the module:
   ```python
   import install_req
   ```
   This will immediately trigger the installation request.

4. On your computer (not in the REPL), run one of:
   ```bash
   # For systems with pip-installed pyserial:
   python3 host_scripts/circup_installer.py --monitor
   
   # For systems requiring pipx:
   python3 host_scripts/pipx_serial_monitor.py
   ```

##### Option B: Using repl_installer.py
1. Make sure repl_installer.py is on your CircuitPython device
2. Connect to your device's REPL
3. In the REPL, import and run:
   ```python
   import repl_installer
   repl_installer.install()
   ```

4. Follow step 4 from Option A above

#### Method 4: Using circup Directly

```bash
# Install all libraries from requirements.txt
circup install -r requirements.txt

# Update all installed libraries
circup update
```

## Troubleshooting

### Missing Python Modules

If you see errors about missing modules:

```bash
# Install tools with pipx (recommended)
pipx install pyserial
pipx install circup
pipx ensurepath

# OR install with pip
pip install pyserial circup
```

### ESP32SPI Socket Import Error

If you see this error in your CircuitPython device:
```
ImportError: no module named 'adafruit_esp32spi.adafruit_esp32spi_socket'
```

Run our specialized fix:
```bash
python3 host_scripts/circup_installer.py --fix-esp32spi
```

### Circup Not Found in PATH

If you installed circup with pipx but it's not found, ensure pipx binaries are in your PATH:

```bash
pipx ensurepath
# Start a new terminal session after running this
```

### REPL Connection Issues

Only one program can connect to the serial port at a time. If you're running the installer, make sure no other program (like Mu Editor or screen) is connected to the REPL.

### PySerial Installation on Silicon Macs

If you're using a Silicon Mac (M1/M2/M3) and can't use direct pip installation:

1. Use the pipx-compatible serial monitor script:
   ```bash
   python3 host_scripts/pipx_serial_monitor.py
   ```

2. This script works with pipx-installed pyserial and doesn't require pip installation

## Accessing the REPL

### Finding the Serial Port

#### macOS
```bash
ls /dev/tty.usbmodem*
```
or
```bash
ls /dev/cu.usbmodem*
```

#### Linux
```bash
ls /dev/ttyACM*
```

#### Windows
Check Device Manager under "Ports (COM & LPT)" for a COM port (e.g., COM3, COM4).

### Connecting to the REPL

#### Using screen (macOS/Linux)
```bash
screen /dev/tty.usbmodem* 115200
```
To exit: Press `Ctrl+A` then `Ctrl+\` and confirm with `y`.

#### Using PuTTY (Windows)
1. Open PuTTY
2. Select Serial connection
3. Enter the COM port
4. Set Speed to 115200
5. Click "Open"

#### Using Mu Editor
Mu Editor has built-in REPL access for CircuitPython.
1. Click the "Serial" button in the Mu interface.

#### Using Arduino IDE
1. Select the correct board and port
2. Open the Serial Monitor
3. Set the baud rate to 115200

## Code Examples

### Basic WiFi Connection Example

```python
import board
import busio
import digitalio
from adafruit_esp32spi import adafruit_esp32spi
import adafruit_esp32spi.adafruit_esp32spi_socket as socket
import adafruit_requests as requests

# Set up ESP32
esp32_cs = digitalio.DigitalInOut(board.ESP_CS)
esp32_ready = digitalio.DigitalInOut(board.ESP_BUSY)
esp32_reset = digitalio.DigitalInOut(board.ESP_RESET)
spi = busio.SPI(board.SCK, board.MOSI, board.MISO)
esp = adafruit_esp32spi.ESP_SPIcontrol(spi, esp32_cs, esp32_ready, esp32_reset)

# Connect to WiFi
from secrets import secrets
esp.connect_AP(secrets['ssid'], secrets['password'])

# Set up requests
requests.set_socket(socket, esp)

# Make a request
response = requests.get("http://wifitest.adafruit.com/testwifi/index.html")
print(response.text)
response.close()
```

## Notes

Based on the PyPortal examples from Adafruit's CircuitPython libraries. For more information,
visit: https://docs.circuitpython.org/projects/pyportal/en/latest/examples.html

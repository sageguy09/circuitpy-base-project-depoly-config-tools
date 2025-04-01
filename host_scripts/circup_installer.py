#!/usr/bin/env python3

import os
import sys
import time
import argparse
import subprocess

def check_pipx_package_location(package_name):
    """Check if a package is installed via pipx and return its path"""
    try:
        result = subprocess.run(
            ["pipx", "which", package_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None
    except (FileNotFoundError, subprocess.SubprocessError):
        return None

def check_pipx_package(package_name):
    """Check if a package is installed via pipx"""
    try:
        result = subprocess.run(
            ["pipx", "list", "--short"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        return package_name in result.stdout
    except (FileNotFoundError, subprocess.SubprocessError):
        return False

def run_with_pipx(package_name, args):
    """Run a command with a pipx-installed package"""
    try:
        result = subprocess.run(
            ["pipx", "run", package_name] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        return result.returncode == 0, result.stdout
    except (FileNotFoundError, subprocess.SubprocessError):
        return False, "Error running command with pipx"

def check_requirements():
    """
    Check if required packages are installed and can be imported.
    Also checks for command-line tools that might be installed via pipx.
    """
    missing_tools = []
    pyserial_via_pip = False
    pyserial_via_pipx = False
    pyserial_path = None
    
    # Check for pipx itself
    try:
        subprocess.run(
            ["pipx", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False
        )
        pipx_available = True
    except (FileNotFoundError, subprocess.SubprocessError):
        pipx_available = False

    # First, check if pyserial is available through pipx (preferred)
    if pipx_available:
        # Try to get the path of pyserial installed via pipx
        pyserial_path = check_pipx_package_location("pyserial")
        if pyserial_path:
            print(f"Found pyserial via pipx at: {pyserial_path}")
            pyserial_via_pipx = True
        else:
            # Also check if it's in the installed packages
            if check_pipx_package("pyserial"):
                print("pyserial is installed via pipx but path could not be determined")
                pyserial_via_pipx = True
    
    # If not available via pipx, try direct import
    if not pyserial_via_pipx:
        try:
            import serial
            from serial.tools import list_ports
            pyserial_via_pip = True
            print("Using pyserial installed via pip (directly importable)")
        except ImportError:
            pyserial_via_pip = False
            if not pyserial_via_pipx:
                missing_tools.append("pyserial")
    
    # Check for circup as a command-line tool
    try:
        result = subprocess.run(
            ["circup", "--version"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            check=False
        )
        if result.returncode != 0:
            missing_tools.append("circup")
    except (FileNotFoundError, subprocess.SubprocessError):
        missing_tools.append("circup")
    
    if missing_tools:
        print("ERROR: Missing required tools:")
        for tool in missing_tools:
            print(f"  - {tool}")
        
        print("\nPlease install the missing tools with pipx:")
        for tool in missing_tools:
            print(f"  pipx install {tool}")
        
        if "circup" in missing_tools:
            print("  pipx ensurepath  # To add circup to your PATH")
        
        return False, False, False, None
        
    return True, pyserial_via_pip, pyserial_via_pipx, pyserial_path

# Check requirements first
requirements_met, pyserial_via_pip, pyserial_via_pipx, pyserial_path = check_requirements()

if not requirements_met:
    sys.exit(1)

# Use pyserial directly if it's installed via pip
if pyserial_via_pip:
    import serial
    import glob
    from serial.tools import list_ports
    
    def find_serial_port():
        """Find the serial port for the CircuitPython device"""
        # List all ports
        ports = list(list_ports.comports())
        
        # Look for CircuitPython devices
        for port in ports:
            if any(x in port.description.lower() for x in ['circuitpython', 'circuit', 'python', 'microbit', 'adafruit']):
                return port.device
        
        # Common patterns by platform
        if sys.platform.startswith('win'):
            # Windows: Try COM ports
            for i in range(1, 20):
                port = f"COM{i}"
                try:
                    s = serial.Serial(port)
                    s.close()
                    return port
                except (serial.SerialException, OSError):
                    pass
        elif sys.platform.startswith('linux'):
            # Linux: Try ttyACM and ttyUSB
            patterns = ['/dev/ttyACM*', '/dev/ttyUSB*']
            for pattern in patterns:
                matches = glob.glob(pattern)
                if matches:
                    return matches[0]
        elif sys.platform.startswith('darwin'):
            # macOS: Try usbmodem
            patterns = ['/dev/cu.usbmodem*', '/dev/tty.usbmodem*']
            for pattern in patterns:
                matches = glob.glob(pattern)
                if matches:
                    return matches[0]
        
        return None
    
    def monitor_serial_for_install_request(port, baud=115200, timeout=60):
        """Monitor the serial port for an installation request marker"""
        print(f"Monitoring serial port {port} for install request...")
        start_time = time.time()
        
        try:
            ser = serial.Serial(port, baud, timeout=1)
        except serial.SerialException as e:
            print(f"Error opening serial port: {e}")
            print("Is the REPL already in use by another program?")
            return False
        
        # Marker to look for in the output
        marker_start = "===== CIRCUITPY_LIB_INSTALL_REQUEST ====="
        found_marker = False
        
        while time.time() - start_time < timeout:
            try:
                line = ser.readline().decode('utf-8', errors='replace').strip()
                if line:
                    print(f"Serial: {line}")
                    if marker_start in line:
                        found_marker = True
                        break
            except Exception as e:
                print(f"Error reading serial: {e}")
                break
        
        ser.close()
        
        if found_marker:
            print("Installation request detected!")
            return True
        else:
            print(f"Timeout after {timeout} seconds. No installation request detected.")
            print("Try importing install_req.py in your CircuitPython REPL")
            return False
elif pyserial_via_pipx:
    # If pyserial is installed via pipx, use subprocess to run it
    print("Using pyserial via pipx for serial port operations")
    
    def find_serial_port():
        """Find the serial port for the CircuitPython device using pipx-installed pyserial"""
        # First try 'pipx run pyserial-ports' which is part of pyserial
        success, output = run_with_pipx("pyserial", ["pyserial-ports", "-v"])
        if not success:
            # Fallback to list-ports command if available
            success, output = run_with_pipx("pyserial", ["list-ports", "-v"])
            if not success:
                return None
            
        # Process the output to find CircuitPython devices
        lines = output.strip().split('\n')
        for line in lines:
            if any(x in line.lower() for x in ['circuitpython', 'circuit', 'python', 'microbit', 'adafruit']):
                # Extract port from line (format varies, but port is typically at the beginning)
                port = line.split()[0]
                return port
                
        # Common patterns by platform
        if sys.platform.startswith('darwin'):  # macOS
            success, output = run_with_pipx("pyserial", ["pyserial-ports"])
            if success:
                lines = output.strip().split('\n')
                for line in lines:
                    if 'usbmodem' in line:
                        return line.strip()
            return "/dev/cu.usbmodem14101"  # Common for macOS
        elif sys.platform.startswith('win'):  # Windows
            return "COM3"  # Just a guess for Windows
        else:  # Linux and others
            return "/dev/ttyACM0"  # Common for Linux
        
        return None
    
    def monitor_serial_for_install_request(port, baud=115200, timeout=60):
        """
        Monitor serial port using external tool since pyserial is only available via pipx
        This implementation uses a temporary script and pipx run
        """
        print(f"Monitoring serial port {port} for install request using pipx pyserial...")
        
        # Create a temporary script to run with pipx
        temp_script = os.path.join(os.getcwd(), "_temp_serial_monitor.py")
        with open(temp_script, "w") as f:
            f.write(f"""
import serial
import time
import sys

def monitor_port():
    print(f"Monitoring {port} at {baud} baud for {timeout} seconds...")
    
    try:
        ser = serial.Serial("{port}", {baud}, timeout=1)
    except Exception as e:
        print(f"Error opening port: {e}")
        return False
    
    start_time = time.time()
    marker = "===== CIRCUITPY_LIB_INSTALL_REQUEST ====="
    
    while time.time() - start_time < {timeout}:
        try:
            line = ser.readline().decode('utf-8', errors='replace').strip()
            if line:
                print(f"Serial: {{line}}")
                if marker in line:
                    print("Marker detected!")
                    ser.close()
                    return True
        except Exception as e:
            print(f"Error: {{e}}")
            break
    
    ser.close()
    return False

if monitor_port():
    sys.exit(0)
else:
    sys.exit(1)
""")
        
        try:
            # Run the script with pipx
            result = subprocess.run(
                ["pipx", "run", "pyserial", "python", temp_script],
                check=False
            )
            success = result.returncode == 0
        finally:
            # Clean up temporary script
            if os.path.exists(temp_script):
                os.remove(temp_script)
        
        if success:
            print("Installation request detected!")
            return True
        else:
            print(f"Timeout after {timeout} seconds. No installation request detected.")
            print("Try importing install_req.py in your CircuitPython REPL")
            return False
else:
    print("ERROR: No usable installation of pyserial found")
    print("Please install pyserial using either pip or pipx")
    sys.exit(1)

# Import the library installer
try:
    from install_libs import install_libraries
except ImportError:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(script_dir)
    try:
        from install_libs import install_libraries
    except ImportError:
        print("ERROR: Cannot import install_libs.py")
        print("Make sure you're running this script from the project root directory")
        print("or that host_scripts/install_libs.py exists.")
        sys.exit(1)

# Essential PyPortal libraries - make sure these are always installed 
# even if not explicitly requested
ESSENTIAL_LIBRARIES = [
    "adafruit_esp32spi",     # For WiFi connectivity (including socket submodule)
    "adafruit_requests",     # For HTTP requests
    "adafruit_pyportal",     # PyPortal base library
    "adafruit_io",           # For Adafruit IO integration
    "adafruit_bitmap_font",  # For text rendering
    "adafruit_display_text", # For text display
    "adafruit_touchscreen"   # For touch input
]

def ensure_essential_libraries():
    """Ensure that essential PyPortal libraries are installed"""
    print("Checking for essential PyPortal libraries...")
    
    # Install libraries using circup
    for library in ESSENTIAL_LIBRARIES:
        try:
            print(f"Ensuring {library} is installed...")
            # Try to install the library (will update if already installed)
            subprocess.run(
                ["circup", "install", library],
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                check=False
            )
        except Exception as e:
            print(f"Warning: Error checking {library}: {e}")
    
    print("Essential libraries check complete")

def find_circuitpy_drive():
    """Find the CircuitPython drive"""
    # Common mount points
    possible_mounts = [
        "/Volumes/CIRCUITPY",  # macOS
        "/media/$USER/CIRCUITPY",  # Linux
        "D:\\",  # Windows (common, but could be any drive letter)
        "E:\\",
        "F:\\"
    ]
    
    for mount in possible_mounts:
        # Expand user if needed
        mount = os.path.expandvars(os.path.expanduser(mount))
        if os.path.exists(mount):
            # Basic check that this is likely a CircuitPython drive
            code_py = os.path.join(mount, "code.py")
            if os.path.exists(code_py):
                return mount
    
    return None

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="CircuitPython Library Installer")
    parser.add_argument('--monitor', action='store_true',
                        help='Monitor serial port for install request')
    parser.add_argument('--essential-only', action='store_true', 
                        help='Only install essential libraries for PyPortal')
    parser.add_argument('--fix-esp32spi', action='store_true',
                        help='Specifically reinstall adafruit_esp32spi to fix socket issues')
    args = parser.parse_args()
    
    print("CircuitPython Library Installer (Host)")
    print("=====================================")
    
    if pyserial_via_pipx:
        print(f"Using pyserial installed via pipx: {pyserial_path}")
    elif pyserial_via_pip:
        import serial
        print(f"Using pyserial installed via pip: {serial.__file__}")
    
    # Handle the fix-esp32spi flag (specifically for socket issues)
    if args.fix_esp32spi:
        print("\nFIXING ESP32SPI SOCKET ISSUE:")
        print("Reinstalling adafruit_esp32spi library...")
        try:
            # Force reinstall of the library
            subprocess.run(
                ["circup", "install", "--force", "adafruit_esp32spi"],
                check=True
            )
            print("adafruit_esp32spi reinstalled successfully!")
            print("This should fix the 'no module named adafruit_esp32spi.adafruit_esp32spi_socket' error")
            print("\nYou may need to reset your PyPortal device for changes to take effect.")
            return 0
        except Exception as e:
            print(f"Error reinstalling adafruit_esp32spi: {e}")
            return 1
    
    # Handle essential-only flag
    if args.essential_only:
        print("\nInstalling essential PyPortal libraries only...")
        ensure_essential_libraries()
        return 0
        
    # When monitoring is requested
    if args.monitor:
        # Find the serial port
        port = find_serial_port()
        if not port:
            print("Error: CircuitPython serial port not found")
            print("Please make sure your device is connected")
            return 1
            
        print(f"Found CircuitPython device at: {port}")
        
        # Monitor for install request
        if not monitor_serial_for_install_request(port):
            return 1
    
    # Find the CircuitPython drive
    circuit_dir = find_circuitpy_drive()
    if not circuit_dir:
        print("Warning: CircuitPython drive not found")
        print("Libraries will be installed but verification is limited")
    else:
        print(f"Found CircuitPython drive at: {circuit_dir}")
    
    # Always make sure essential libraries are installed first
    ensure_essential_libraries()
    
    # Run the library installer for all libraries in requirements.txt
    print("\nInstalling libraries from requirements.txt...\n")
    success = install_libraries(verbose=True)
    
    # Signal completion
    message = "All libraries installed successfully!" if success else "Some libraries failed to install."
    print(f"\n{message}")
    print("Installation complete.")
    print("\nIf you're seeing 'no module named adafruit_esp32spi.adafruit_esp32spi_socket' errors,")
    print("try running this command: python3 host_scripts/circup_installer.py --fix-esp32spi")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
CircuitPython Library Installer
A utility for managing CircuitPython libraries on devices
"""
import os
import sys
import time
import argparse
import subprocess
import threading
import queue
import re

# Default CircuitPython library directory
DEFAULT_LIB_DIR = "lib"

# Monitor timeout in seconds
DEFAULT_MONITOR_TIMEOUT = 60

def run_command(cmd, shell=False):
    """Run a command and return its output and status"""
    try:
        result = subprocess.run(
            cmd, 
            shell=shell, 
            check=True, 
            capture_output=True, 
            text=True
        )
        return True, result.stdout
    except subprocess.CalledProcessError as e:
        return False, e.stderr
    except Exception as e:
        return False, str(e)

def is_circup_installed():
    """Check if circup is installed"""
    success, _ = run_command(["circup", "--version"])
    return success

def install_circup():
    """Install circup using pip"""
    print("Installing circup...")
    
    try:
        # Try with pip first
        success, output = run_command([sys.executable, "-m", "pip", "install", "--user", "circup"])
        if success:
            print("circup installed successfully with pip")
            return True
            
        # Try with pipx if pip fails
        success, output = run_command(["pipx", "install", "circup"])
        if success:
            print("circup installed successfully with pipx")
            # Add pipx bin directory to PATH
            run_command(["pipx", "ensurepath"])
            return True
            
        print("Failed to install circup. Please install it manually:")
        print("  pip install circup")
        print("  or")
        print("  pipx install circup")
        return False
    except Exception as e:
        print(f"Error installing circup: {e}")
        return False

def find_circuitpy_devices():
    """Find all connected CircuitPython devices"""
    devices = []
    
    # macOS
    if os.path.exists("/Volumes"):
        import glob
        for device in glob.glob("/Volumes/CIRCUIT*"):
            if os.path.isdir(device):
                devices.append(device)
    
    # Linux
    linux_paths = []
    for base in ["/media", "/mnt"]:
        if os.path.exists(base):
            for user_dir in os.listdir(base):
                user_path = os.path.join(base, user_dir)
                if os.path.isdir(user_path):
                    for device in os.listdir(user_path):
                        if device.startswith("CIRCUIT"):
                            device_path = os.path.join(user_path, device)
                            if os.path.isdir(device_path):
                                linux_paths.append(device_path)
    devices.extend(linux_paths)
    
    # Windows
    if os.name == 'nt':
        import string
        for drive in string.ascii_uppercase:
            drive_path = f"{drive}:\\"
            if os.path.exists(drive_path):
                try:
                    volume_name = os.path.basename(drive_path)
                    if "CIRCUIT" in volume_name:
                        devices.append(drive_path)
                except:
                    pass
    
    return devices

def get_installed_libraries(device_path=None):
    """Get a list of installed libraries"""
    if device_path:
        lib_dir = os.path.join(device_path, DEFAULT_LIB_DIR)
        if os.path.exists(lib_dir):
            libs = [name for name in os.listdir(lib_dir) if os.path.isdir(os.path.join(lib_dir, name))]
            return libs
    
    # If no device or no libraries found, use circup to list installed libraries
    success, output = run_command(["circup", "list", "--json"])
    if success:
        import json
        try:
            libs = json.loads(output)
            return [lib["name"] for lib in libs]
        except json.JSONDecodeError:
            pass
    
    # Fallback to simple parsing of output
    success, output = run_command(["circup", "list"])
    if success:
        libs = []
        for line in output.splitlines():
            if "==" in line:
                lib_name = line.split("==")[0].strip()
                libs.append(lib_name)
        return libs
    
    return []

def read_requirements(file_path="requirements.txt"):
    """Read library requirements from a file"""
    try:
        with open(file_path, "r") as f:
            # Filter out empty lines and comments
            requirements = [
                line.strip() for line in f 
                if line.strip() and not line.strip().startswith('#')
            ]
        return requirements
    except (IOError, OSError):
        print(f"Failed to read requirements file: {file_path}")
        return []

def install_library(library, device_path=None, force=False, update=False):
    """Install a specific library"""
    cmd = ["circup"]
    
    if update:
        cmd.append("update")
        cmd.append(library)
    else:
        cmd.append("install")
        if force:
            cmd.append("--force")
        cmd.append(library)
    
    print(f"{'Updating' if update else 'Installing'} {library}...")
    success, output = run_command(cmd)
    
    if success:
        print(f"Successfully {'updated' if update else 'installed'} {library}")
        return True
    else:
        print(f"Failed to {'update' if update else 'install'} {library}: {output}")
        return False

def find_matching_libraries(pattern):
    """Find libraries matching a pattern using bundle listing"""
    success, output = run_command(["circup", "show", "--all"])
    if not success:
        return []
    
    matches = []
    pattern_re = re.compile(pattern, re.IGNORECASE)
    
    for line in output.splitlines():
        line = line.strip()
        if line and "==" in line:
            lib_name = line.split("==")[0].strip()
            if pattern_re.search(lib_name):
                matches.append(lib_name)
    
    return matches

def prompt_for_library_selection(matches):
    """Prompt the user to select a library from matches"""
    if not matches:
        return None
    
    print("\nMultiple matching libraries found:")
    for i, lib in enumerate(matches, 1):
        print(f"{i}. {lib}")
    
    while True:
        try:
            choice = input("\nSelect a library (number) or 'q' to cancel: ")
            if choice.lower() in ('q', 'quit', 'exit'):
                return None
            
            idx = int(choice) - 1
            if 0 <= idx < len(matches):
                return matches[idx]
            print("Invalid selection, try again.")
        except ValueError:
            print("Please enter a number or 'q'.")
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            return None

def serial_monitor(port=None, baud=115200, timeout=DEFAULT_MONITOR_TIMEOUT):
    """
    Monitor the serial port for library installation requests
    Returns True if request was found, False otherwise
    """
    # First check if PySerial is directly importable
    try:
        import serial.tools.list_ports
        pyserial_importable = True
    except ImportError:
        pyserial_importable = False
        
    # If PySerial is not directly importable, check if it's installed via pipx
    if not pyserial_importable:
        try:
            # Check if pipx is available
            subprocess.run(["pipx", "--version"], check=True, capture_output=True)
            
            # Check if pyserial is installed via pipx
            result = subprocess.run(["pipx", "list"], check=True, capture_output=True, text=True)
            if "pyserial" in result.stdout:
                print("PySerial is installed via pipx but not importable by this script.")
                print("Please install PySerial directly with pip for script import:")
                print("  pip install pyserial")
                print("\nAlternately, use the pipx-compatible script:")
                print("  pipx run pyserial-miniterm --help")
                return False
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
        
        # Standard message if no pipx installation found
        print("PySerial not installed or not importable. Install it with:")
        print("  pip install pyserial")
        return False
    
    # Find CircuitPython device if port not specified
    if not port:
        for p in serial.tools.list_ports.comports():
            if "CircuitPython" in p.description or "CIRCUITPY" in p.description:
                port = p.device
                break
    
    if not port:
        print("No CircuitPython device found")
        return False
    
    print(f"Monitoring {port} at {baud} baud for installation requests...")
    print("Press Ctrl+C to cancel")
    
    try:
        ser = serial.Serial(port, baud, timeout=1)
    except serial.SerialException as e:
        print(f"Error opening serial port: {e}")
        print("Is it already in use by another program?")
        return False
    
    # Queue to hold found markers
    marker_queue = queue.Queue()
    
    # Flag to signal when to stop
    stop_event = threading.Event()
    
    # Marker to look for
    marker_start = "===== CIRCUITPY_LIB_INSTALL_REQUEST ====="
    
    # Thread function to read serial and look for markers
    def reader_thread():
        try:
            while not stop_event.is_set():
                line = ser.readline().decode('utf-8', errors='replace').strip()
                if line:
                    print(f"Serial> {line}")
                    
                    if marker_start in line:
                        marker_queue.put(True)
                        # Keep reading to show all output
                        continue
        except Exception as e:
            print(f"Error in reader thread: {e}")
        finally:
            if not ser.closed:
                ser.close()
    
    # Start reader thread
    reader = threading.Thread(target=reader_thread)
    reader.daemon = True
    reader.start()
    
    # Wait for marker or timeout
    try:
        result = False
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                marker_queue.get(timeout=1)
                result = True
                print("\nInstallation request detected!")
                break
            except queue.Empty:
                # No marker found yet, keep waiting
                pass
        
        if not result:
            print(f"\nTimeout after {timeout} seconds. No installation request detected.")
    except KeyboardInterrupt:
        print("\nMonitoring cancelled.")
    finally:
        # Signal thread to stop and wait for it
        stop_event.set()
        reader.join(2)  # Give it 2 seconds to join
        
        # Close serial port if still open
        if not ser.closed:
            ser.close()
    
    return result

def fix_esp32spi_socket_issue():
    """Fix the ESP32SPI socket import issue by reinstalling the library"""
    print("Reinstalling adafruit_esp32spi library to fix socket import issue...")
    
    success = install_library("adafruit_esp32spi", force=True)
    
    if success:
        print("\nFix applied successfully!")
        print("This should resolve the 'no module named adafruit_esp32spi.adafruit_esp32spi_socket' error")
        return True
    else:
        print("\nFailed to apply fix.")
        print("Try manually reinstalling the adafruit_esp32spi library")
        return False

def main():
    parser = argparse.ArgumentParser(description="CircuitPython Library Installer")
    parser.add_argument('libraries', nargs='*', help='Libraries to install or update')
    parser.add_argument('--force', action='store_true', help='Force installation even if already installed')
    parser.add_argument('--update', action='store_true', help='Update libraries instead of installing')
    parser.add_argument('--requirements', '-r', help='Requirements file to read libraries from')
    parser.add_argument('--device', '-d', help='Path to CircuitPython device (autodetect if not specified)')
    parser.add_argument('--monitor', action='store_true', help='Monitor serial port for install requests')
    parser.add_argument('--fix-esp32spi', action='store_true', help='Fix ESP32SPI socket import issue')
    parser.add_argument('--list', action='store_true', help='List installed libraries')
    args = parser.parse_args()
    
    # Check if circup is installed
    if not is_circup_installed():
        if not install_circup():
            return 1
    
    # Auto-detect device if not specified
    device_path = args.device
    if not device_path:
        devices = find_circuitpy_devices()
        if len(devices) == 1:
            device_path = devices[0]
            print(f"Found CircuitPython device: {device_path}")
        elif len(devices) > 1:
            print("Multiple CircuitPython devices found:")
            for i, device in enumerate(devices, 1):
                print(f"{i}. {device}")
            
            try:
                choice = int(input("Select device (number): ")) - 1
                if 0 <= choice < len(devices):
                    device_path = devices[choice]
                else:
                    print("Invalid selection")
                    return 1
            except (ValueError, KeyboardInterrupt, EOFError):
                print("No device selected")
                return 1
        else:
            print("No CircuitPython devices found")
            device_path = None  # Will use circup's default behavior
    
    # Apply ESP32SPI socket fix if requested
    if args.fix_esp32spi:
        fix_esp32spi_socket_issue()
        return 0
    
    # List installed libraries if requested
    if args.list:
        print("Installed libraries:")
        for lib in get_installed_libraries(device_path):
            print(f"- {lib}")
        return 0
    
    # Monitor for install requests if requested
    if args.monitor:
        import importlib.util
        if importlib.util.find_spec("serial") is None:
            print("PySerial is required for monitoring. Install with:")
            print("pip install pyserial")
            return 1
        
        # Start monitoring
        if serial_monitor():
            # If request detected, read requirements and install
            if args.requirements:
                libs = read_requirements(args.requirements)
            else:
                # Try default requirements file
                libs = read_requirements("requirements.txt")
            
            if not libs:
                print("No libraries to install")
                return 0
            
            for lib in libs:
                install_library(lib, device_path, args.force, args.update)
            
            print("\nLibrary installation completed")
        
        return 0
    
    # Get libraries to install/update
    libraries = []
    
    # From command line arguments
    if args.libraries:
        libraries.extend(args.libraries)
    
    # From requirements file
    if args.requirements:
        libraries.extend(read_requirements(args.requirements))
    elif not libraries:
        # Try default requirements file if no libraries specified
        default_reqs = read_requirements("requirements.txt")
        if default_reqs:
            libraries.extend(default_reqs)
    
    # Process libraries
    if libraries:
        print(f"{'Updating' if args.update else 'Installing'} {len(libraries)} libraries...")
        
        for lib in libraries:
            # Check if this is a pattern or partial match
            if '*' in lib or '?' in lib or len(lib) < 5:
                matches = find_matching_libraries(lib)
                if len(matches) > 1:
                    # Multiple matches, ask user to choose
                    selected = prompt_for_library_selection(matches)
                    if selected:
                        install_library(selected, device_path, args.force, args.update)
                    else:
                        print(f"Skipping {lib}")
                elif len(matches) == 1:
                    # Single match, install it
                    install_library(matches[0], device_path, args.force, args.update)
                else:
                    print(f"No libraries found matching '{lib}'")
            else:
                # Direct library name
                install_library(lib, device_path, args.force, args.update)
        
        print("\nOperation completed")
    else:
        print("No libraries specified for installation")
        parser.print_help()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
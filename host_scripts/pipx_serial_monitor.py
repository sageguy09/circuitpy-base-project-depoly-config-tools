#!/usr/bin/env python3

import os
import sys
import subprocess
import argparse
import time
import glob
import tempfile

def find_circuitpy_serial_ports():
    """Find CircuitPython serial ports using multiple methods"""
    devices = []
    
    # macOS - use multiple detection methods to ensure we find the ports
    if sys.platform == 'darwin':
        print("Detecting serial ports on macOS...")
        
        # Method 1: Direct glob pattern
        try:
            # Use both tty and cu devices
            tty_devices = glob.glob('/dev/tty.usbmodem*')
            cu_devices = glob.glob('/dev/cu.usbmodem*')
            if tty_devices:
                print(f"Found tty devices: {', '.join(tty_devices)}")
                devices.extend(tty_devices)
            if cu_devices:
                print(f"Found cu devices: {', '.join(cu_devices)}")
                devices.extend(cu_devices)
        except Exception as e:
            print(f"Error in glob detection: {e}")
            
        # Method 2: Use ls command directly
        if not devices:
            print("Trying shell command detection...")
            try:
                # Look for tty devices
                result = subprocess.run("ls -la /dev/tty.usbmodem* 2>/dev/null || true", 
                                      shell=True, capture_output=True, text=True)
                if result.stdout.strip():
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if '/dev/tty.usbmodem' in line:
                            parts = line.split()
                            device = parts[-1] if len(parts) > 0 else None
                            if device and device.startswith('/dev/tty.usbmodem'):
                                print(f"Found device via ls: {device}")
                                devices.append(device)
                
                # Look for cu devices
                result = subprocess.run("ls -la /dev/cu.usbmodem* 2>/dev/null || true", 
                                      shell=True, capture_output=True, text=True)
                if result.stdout.strip():
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if '/dev/cu.usbmodem' in line:
                            parts = line.split()
                            device = parts[-1] if len(parts) > 0 else None
                            if device and device.startswith('/dev/cu.usbmodem'):
                                print(f"Found device via ls: {device}")
                                devices.append(device)
            except subprocess.SubprocessError as e:
                print(f"Error in ls command: {e}")
                
        # Method 3: Check for any USB serial devices
        if not devices:
            print("Looking for any USB serial devices...")
            try:
                result = subprocess.run("ls /dev/*usb* 2>/dev/null || true", 
                                      shell=True, capture_output=True, text=True)
                usb_devices = [line for line in result.stdout.strip().split('\n') if line.strip()]
                if usb_devices:
                    print(f"Found USB devices: {', '.join(usb_devices)}")
                    devices.extend(usb_devices)
            except Exception as e:
                print(f"Error finding USB devices: {e}")
    
    # Linux
    elif sys.platform.startswith('linux'):
        try:
            result = subprocess.run("ls /dev/ttyACM* 2>/dev/null || true", 
                                   shell=True, capture_output=True, text=True)
            if result.stdout.strip():
                devices.extend(result.stdout.strip().split('\n'))
        except subprocess.SubprocessError:
            pass
    
    # Windows detection would go here
            
    # Filter out empty strings and duplicates
    devices = list(dict.fromkeys([d for d in devices if d.strip()]))
    
    # If we still don't have any devices, try a fallback approach
    if not devices:
        print("No devices found using standard methods. Trying alternative approaches...")
        
        # Check if the main serial tools are installed via pipx
        try:
            result = subprocess.run(["pipx", "run", "pyserial-list"], 
                                  capture_output=True, text=True, check=False)
            if result.returncode == 0 and result.stdout.strip():
                print("Found devices via pyserial-list:")
                print(result.stdout)
                # Extract port names from the output
                for line in result.stdout.strip().split('\n'):
                    if '/dev/' in line:
                        port = line.split()[0]
                        if port.startswith('/dev/'):
                            devices.append(port)
        except Exception as e:
            print(f"Error running pyserial-list: {e}")
        
        # Last resort - check bash aliases
        try:
            result = subprocess.run("bash -c 'pygetrepl' 2>/dev/null || true",
                                  shell=True, capture_output=True, text=True)
            if result.returncode == 0 and result.stdout.strip():
                print(f"Found devices via bash alias: {result.stdout.strip()}")
                devices.extend(result.stdout.strip().split('\n'))
        except Exception:
            pass
    
    # If we found devices, show them
    if devices:
        print(f"Found {len(devices)} potential serial ports: {', '.join(devices)}")
    else:
        print("No serial ports found. Make sure your CircuitPython device is connected.")
    
    return devices

def create_temp_monitor_script(port, baud=115200, timeout=60):
    """
    Create a temporary Python script to monitor serial port
    using pyserial when executed through pipx
    """
    temp_script = tempfile.NamedTemporaryFile(suffix='.py', delete=False)
    script_path = temp_script.name
    
    script_content = f'''
import serial
import sys
import time

def monitor_for_install_request():
    print(f"Monitoring {port} at {baud} baud for installation requests...")
    print("Press Ctrl+C to cancel")
    
    marker_start = "===== CIRCUITPY_LIB_INSTALL_REQUEST ====="
    marker_end = "===== CIRCUITPY_LIB_INSTALL_END ====="
    in_marker_section = False
    found_marker = False
    start_time = time.time()
    timeout = {timeout}
    
    try:
        ser = serial.Serial("{port}", {baud}, timeout=1)
    except serial.SerialException as e:
        print(f"Error opening serial port: {{e}}")
        print("Is the port already in use by another program?")
        return False
        
    while time.time() - start_time < timeout:
        try:
            line = ser.readline().decode('utf-8', errors='replace').strip()
            if not line:
                continue
                
            print(f"Serial> {{line}}")
            
            if marker_start in line:
                print("\\nInstallation request detected!")
                in_marker_section = True
                found_marker = True
            elif marker_end in line and in_marker_section:
                in_marker_section = False
                
        except KeyboardInterrupt:
            print("\\nMonitoring cancelled.")
            ser.close()
            return found_marker
        except Exception as e:
            print(f"Error: {{e}}")
            break
    
    ser.close()
    
    if found_marker:
        print("Installation request confirmed")
        return True
    else:
        print(f"\\nTimeout after {{timeout}} seconds. No installation request detected.")
        return False

# Run the monitor and exit with appropriate code
print("Starting serial monitor...")
success = monitor_for_install_request()
sys.exit(0 if success else 1)
'''
    
    with open(script_path, 'w') as f:
        f.write(script_content)
    
    return script_path

def select_port(ports):
    """Let the user select a port if multiple are found"""
    if not ports:
        return None
    
    if len(ports) == 1:
        return ports[0]
    
    print("Multiple CircuitPython ports found. Please select one:")
    for i, port in enumerate(ports):
        print(f"{i+1}. {port}")
    
    while True:
        try:
            choice = input("Select port (number): ").strip()
            try:
                num = int(choice)
                if 1 <= num <= len(ports):
                    return ports[num-1]
                print("Invalid choice")
            except ValueError:
                print("Please enter a number")
        except (KeyboardInterrupt, EOFError):
            print("\nCancelled")
            return None
    
    return None

def monitor_with_pipx(port, baud=115200, timeout=60):
    """Monitor serial port using pipx-installed pyserial"""
    print(f"Monitoring {port} with pipx-installed pyserial...")
    
    # Create temporary script
    script_path = create_temp_monitor_script(port, baud, timeout)
    
    try:
        # Check if pyserial is installed in pipx
        check_result = subprocess.run(["pipx", "list"], capture_output=True, text=True)
        if "pyserial" not in check_result.stdout:
            print("pyserial not found in pipx. Installing...")
            subprocess.run(["pipx", "install", "pyserial"], check=False)
        
        # Run the temporary script with pipx
        print(f"Running monitor script via pipx...")
        result = subprocess.run(
            ["pipx", "run", "pyserial", "python", script_path],
            check=False
        )
        
        success = result.returncode == 0
        
        if success:
            print("\nProcessing library installation...")
            # Find install_libs.py path
            script_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(script_dir)
            install_libs = os.path.join(script_dir, "install_libs.py")
            
            if os.path.exists(install_libs):
                try:
                    subprocess.run(
                        [sys.executable, install_libs],
                        check=False
                    )
                    print("Library installation complete")
                except subprocess.SubprocessError as e:
                    print(f"Error running library installer: {e}")
            else:
                # Try running circup directly as a fallback
                print(f"Could not find installer at {install_libs}")
                print("Trying to run circup directly...")
                try:
                    subprocess.run(
                        ["circup", "install", "-r", 
                         os.path.join(project_root, "requirements.txt")],
                        check=False
                    )
                    print("Installation complete")
                except subprocess.SubprocessError as e:
                    print(f"Error running circup: {e}")
                    print("Please run the library installer manually")
        
        return success
    finally:
        # Clean up temporary script
        try:
            os.unlink(script_path)
        except OSError:
            pass

def main():
    parser = argparse.ArgumentParser(description="CircuitPython Serial Monitor (pipx compatible)")
    parser.add_argument("-p", "--port", help="Serial port to monitor")
    parser.add_argument("-b", "--baud", type=int, default=115200, help="Baud rate (default: 115200)")
    parser.add_argument("-t", "--timeout", type=int, default=60, 
                       help="Timeout in seconds (default: 60)")
    parser.add_argument("-v", "--verbose", action="store_true",
                       help="Show verbose output for debugging")
    parser.add_argument("--list-only", action="store_true",
                       help="Just list available serial ports and exit")
    args = parser.parse_args()
    
    print("CircuitPython Serial Monitor (pipx compatible)")
    print("=============================================")
    
    # Set verbose mode based on argument
    verbose_mode = args.verbose
    
    # Find ports
    ports = find_circuitpy_serial_ports()
    
    # If list-only mode, just exit after listing ports
    if args.list_only:
        return 0 if ports else 1
    
    # Find or select port
    port = args.port
    if not port:
        if not ports:
            print("\nERROR: No CircuitPython serial ports found")
            print("Make sure your board is connected and mounted")
            print("Try running with --verbose for more debugging information")
            print("\nYou can specify the port manually with the --port option:")
            print("  python3 host_scripts/pipx_serial_monitor.py --port /dev/tty.usbmodem123456")
            return 1
        
        port = select_port(ports)
        if not port:
            return 1
    
    print(f"Using port: {port}")
    
    # Monitor with pipx
    success = monitor_with_pipx(port, args.baud, args.timeout)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

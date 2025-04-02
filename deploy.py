#!/usr/bin/env python3

import os
import shutil
import sys
import time
import glob
import subprocess
import argparse

# Configuration
SOURCE_DIR = os.path.dirname(os.path.abspath(__file__))
REQUIRED_FILES = [
    "code.py",
    "secrets.py",
]
HELPER_FILES = [
    "install_req.py",
    "repl_installer.py",  # Added repl_installer.py to helper files
]
REQUIRED_LIBS = [
    "adafruit_pyportal",
    "adafruit_esp32spi",
    "adafruit_requests",
    "adafruit_io",
    "adafruit_bitmap_font",
    "adafruit_display_text",
    "adafruit_touchscreen"
]

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Deploy CircuitPython files to PyPortal device")
    parser.add_argument("--no-helpers", action="store_true", 
                      help="Skip copying helper files like install_req.py")
    parser.add_argument("--no-backup", action="store_true", 
                      help="Skip backup prompt")
    parser.add_argument("--auto", action="store_true", 
                      help="Automatic mode (select first device, assume yes to prompts)")
    return parser.parse_args()

def find_circuitpy_devices():
    """Find all CircuitPython devices mounted on the system"""
    devices = []
    
    # macOS
    if os.path.exists("/Volumes"):
        for device in glob.glob("/Volumes/CIRCUIT*"):
            if os.path.isdir(device):
                devices.append(device)
    
    # Linux
    linux_paths = glob.glob("/media/**/CIRCUIT*") + glob.glob("/mnt/**/CIRCUIT*")
    devices.extend([p for p in linux_paths if os.path.isdir(p)])
    
    # Windows (look for drive letters)
    if os.name == 'nt':
        import string
        for letter in string.ascii_uppercase:
            drive = f"{letter}:\\"
            if os.path.exists(drive):
                try:
                    volume_name = os.path.basename(drive)
                    if "CIRCUIT" in volume_name:
                        devices.append(drive)
                except:
                    pass
    
    return devices

def select_device(devices):
    """Let the user select a device if multiple are found"""
    if not devices:
        print("No CircuitPython devices found.")
        return None
    
    if len(devices) == 1:
        return devices[0]
    
    print("\nMultiple CircuitPython devices found. Please select one:")
    for i, device in enumerate(devices):
        space_mb = get_free_space(device)
        print(f"{i+1}. {device} ({space_mb:.1f} MB free)")
    
    while True:
        try:
            choice = int(input("\nEnter the number of your device (or 0 to cancel): "))
            if choice == 0:
                return None
            if 1 <= choice <= len(devices):
                return devices[choice-1]
            print("Invalid choice, please try again.")
        except ValueError:
            print("Please enter a number.")

def get_free_space(path):
    """Get free space on device in MB"""
    if os.path.exists(path):
        try:
            total, used, free = shutil.disk_usage(path)
            return free / (1024 * 1024)  # Convert to MB
        except:
            return 0
    return 0

def confirm_action(prompt):
    """Ask for confirmation before proceeding"""
    response = input(f"{prompt} (y/n): ").strip().lower()
    return response == 'y' or response == 'yes'

def run_backup_alias():
    """Run the circuitpy-backup alias or local backup script"""
    print("\nRunning backup script...")
    
    # First try using the local backup script
    local_backup = os.path.join(SOURCE_DIR, "host_scripts", "backup_circuitpy.py")
    
    if os.path.exists(local_backup):
        try:
            backup_dir = os.path.expanduser("~/Developer/micropy/backups/pyportal")
            print(f"Backing up to: {backup_dir}")
            subprocess.run([sys.executable, local_backup, "--auto", "--directory", backup_dir], check=True)
            print("Backup completed successfully.")
            return True
        except subprocess.SubprocessError as e:
            print(f"Error using local backup script: {e}")
            print("Trying system backup alias...")
    
    # Fall back to system backup alias if local script fails
    try:
        subprocess.run(["bash", "-c", "circuitpy-backup"], check=True)
        print("Backup completed successfully using system alias.")
        return True
    except subprocess.SubprocessError as e:
        print(f"Error during backup: {e}")
        print("You can try running 'circuitpy-backup' manually.")
        return False

def clean_target_directory(target_dir):
    """Remove all files from the target directory"""
    print(f"\nCleaning target directory: {target_dir}")
    try:
        # List all items in the directory
        for item in os.listdir(target_dir):
            item_path = os.path.join(target_dir, item)
            
            # Skip .Trashes and other system files
            if item.startswith('.'):
                continue
                
            # Remove files and directories
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)
                
        print("Target directory cleaned successfully.")
        return True
    except Exception as e:
        print(f"Error cleaning target directory: {e}")
        return False

def copy_files(target_dir, include_helpers=True):
    """Copy required files to the CircuitPython device"""
    print(f"Copying files to {target_dir}...")
    
    # Copy main files
    for filename in REQUIRED_FILES:
        src = os.path.join(SOURCE_DIR, filename)
        dst = os.path.join(target_dir, filename)
        if os.path.exists(src):
            print(f"Copying {filename}...")
            shutil.copy2(src, dst)
        else:
            print(f"WARNING: Required file {filename} not found!")
    
    # Copy helper files if requested
    if include_helpers:
        for filename in HELPER_FILES:
            src = os.path.join(SOURCE_DIR, filename)
            dst = os.path.join(target_dir, filename)
            if os.path.exists(src):
                print(f"Copying helper: {filename}...")
                shutil.copy2(src, dst)
            else:
                print(f"WARNING: Helper file {filename} not found!")
    
    # Create lib directory if it doesn't exist
    target_lib = os.path.join(target_dir, "lib")
    if not os.path.exists(target_lib):
        os.makedirs(target_lib)
    
    # Check for required libraries
    source_lib = os.path.join(SOURCE_DIR, "lib")
    if not os.path.exists(source_lib):
        print("WARNING: lib directory not found! Please install required libraries.")
        print("See requirements.txt for the list of required libraries.")
        return False
    
    # Copy libraries if they exist
    for lib in REQUIRED_LIBS:
        src_lib = os.path.join(source_lib, lib)
        dst_lib = os.path.join(target_lib, lib)
        
        if os.path.exists(src_lib):
            if os.path.exists(dst_lib):
                shutil.rmtree(dst_lib)
            if os.path.isdir(src_lib):
                shutil.copytree(src_lib, dst_lib)
            else:
                shutil.copy2(src_lib, dst_lib)
            print(f"Copied library: {lib}")
        else:
            print(f"WARNING: Required library {lib} not found!")
    
    return True

def run_circup_installer():
    """Run the CircuitPython library installer"""
    print("\nDo you want to install required libraries using circup?")
    if confirm_action("Run python3 host_scripts/circup_installer.py?"):
        try:
            subprocess.run(["python3", "host_scripts/circup_installer.py"], check=True)
            print("Library installation completed.")
            return True
        except subprocess.SubprocessError as e:
            print(f"Error during library installation: {e}")
            return False
    return True

def create_secrets_if_not_exists():
    """Create a secrets.py file with template if it doesn't exist"""
    secrets_path = os.path.join(SOURCE_DIR, "secrets.py")
    if not os.path.exists(secrets_path):
        print("Creating template secrets.py file...")
        with open(secrets_path, "w") as f:
            f.write("""# This file is where you keep secret settings, passwords, and tokens!
# If you put them in the code you risk committing that info or sharing it

secrets = {
    'ssid' : 'your_wifi_ssid',
    'password' : 'your_wifi_password',
    'timezone' : "America/New_York", # http://worldtimeapi.org/timezones
    'aio_username' : 'your_adafruit_io_username',
    'aio_key' : 'your_adafruit_io_key',
}
""")
        print("Please edit secrets.py with your WiFi credentials before deploying")
        return False
    return True

def main():
    print("PyPortal Deployment Script")
    print("=========================")
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Find and select CircuitPython device
    devices = find_circuitpy_devices()
    
    if args.auto and devices:
        target_dir = devices[0]
        print(f"Auto-selecting device: {target_dir}")
    else:
        target_dir = select_device(devices)
    
    if not target_dir:
        print("No CircuitPython device selected. Exiting.")
        return 1
    
    print(f"\nSelected device: {target_dir}")
    
    # Check for secrets.py
    if not create_secrets_if_not_exists():
        return 1
    
    # Ask if the user wants to backup first
    if not args.no_backup:
        print("\nWARNING: All files on the device will be removed before deployment.")
        if args.auto or confirm_action("Do you want to backup the device first?"):
            run_backup_alias()
    
    # Confirm before cleaning
    if not args.auto and not confirm_action(f"\nWARNING: This will remove ALL files from {target_dir}. Continue?"):
        print("Deployment cancelled.")
        return 1
    
    # Clean the target directory
    if not clean_target_directory(target_dir):
        if not args.auto and not confirm_action("Error cleaning directory. Continue anyway?"):
            return 1
    
    # Copy files
    if not copy_files(target_dir, include_helpers=not args.no_helpers):
        print("Error copying files.")
        return 1
    
    # Offer to run circup installer
    if not args.auto and confirm_action("\nDo you want to install required libraries using circup?"):
        try:
            subprocess.run(["python3", "host_scripts/circup_installer.py"], check=True)
            print("Library installation completed.")
        except subprocess.SubprocessError as e:
            print(f"Error during library installation: {e}")
    
    print("\nDeployment complete!")
    print("Reset your PyPortal device to run the new code.")
    
    if not args.no_helpers:
        print("\nTo install libraries from REPL, connect to REPL and run:")
        print("  import install_req")
        print("Then on your computer run:")
        print("  python3 host_scripts/circup_installer.py --monitor")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

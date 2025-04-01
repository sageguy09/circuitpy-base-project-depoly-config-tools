#!/usr/bin/env python3

import os
import sys
import shutil
import datetime
import glob
import argparse
from pathlib import Path

# Default backup directory
DEFAULT_BACKUP_DIR = os.path.expanduser("~/Developer/micropy/backups/pyportal")

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
    
    # Windows
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
        print(f"{i+1}. {device}")
    
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

def backup_device(source_dir, backup_dir=None):
    """Backup CircuitPython device to specified directory"""
    if backup_dir is None:
        backup_dir = DEFAULT_BACKUP_DIR
    
    # Create the backup directory if it doesn't exist
    os.makedirs(backup_dir, exist_ok=True)
    
    # Create a timestamp for the backup folder
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    device_name = os.path.basename(source_dir)
    backup_folder = os.path.join(backup_dir, f"{device_name}_{timestamp}")
    
    print(f"Backing up {source_dir} to {backup_folder}...")
    
    try:
        # Create backup folder
        os.makedirs(backup_folder)
        
        # Copy all files and directories, excluding system files
        for item in os.listdir(source_dir):
            source_item = os.path.join(source_dir, item)
            dest_item = os.path.join(backup_folder, item)
            
            # Skip system files like .Trashes, .fseventsd, etc.
            if item.startswith('.'):
                continue
                
            if os.path.isdir(source_item):
                shutil.copytree(source_item, dest_item)
            else:
                shutil.copy2(source_item, dest_item)
        
        # Create a metadata file with information about the backup
        with open(os.path.join(backup_folder, "backup_info.txt"), "w") as f:
            f.write(f"Backup created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Source device: {source_dir}\n")
            
            # If code.py exists, include its modification time
            code_py = os.path.join(source_dir, "code.py")
            if os.path.exists(code_py):
                mod_time = os.path.getmtime(code_py)
                mod_time_str = datetime.datetime.fromtimestamp(mod_time).strftime('%Y-%m-%d %H:%M:%S')
                f.write(f"code.py last modified: {mod_time_str}\n")
        
        print(f"Backup completed successfully to {backup_folder}")
        return True
    except Exception as e:
        print(f"Error during backup: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Backup CircuitPython device")
    parser.add_argument("-d", "--directory", 
                       help=f"Backup directory (default: {DEFAULT_BACKUP_DIR})")
    parser.add_argument("-a", "--auto", action="store_true",
                       help="Automatically select device if only one is found")
    args = parser.parse_args()
    
    # Find devices
    devices = find_circuitpy_devices()
    
    if not devices:
        print("No CircuitPython devices found.")
        return 1
    
    # Select device
    if args.auto and len(devices) == 1:
        device = devices[0]
        print(f"Auto-selected device: {device}")
    else:
        device = select_device(devices)
    
    if not device:
        print("No device selected. Exiting.")
        return 1
    
    # Backup device
    backup_dir = args.directory or DEFAULT_BACKUP_DIR
    success = backup_device(device, backup_dir)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

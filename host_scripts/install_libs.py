#!/usr/bin/env python3

import os
import subprocess
import sys

def install_libraries(requirements_file="requirements.txt", verbose=True):
    """
    Install CircuitPython libraries using circup based on requirements.txt
    
    Args:
        requirements_file: Path to requirements.txt file
        verbose: Whether to print detailed information
    """
    # Find the root directory (where requirements.txt is located)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    req_path = os.path.join(root_dir, requirements_file)
    
    if not os.path.exists(req_path):
        print(f"Error: {req_path} not found")
        return False
        
    if verbose:
        print(f"Reading requirements from {req_path}")
    
    # Read requirements
    try:
        with open(req_path, 'r') as f:
            libraries = [line.strip() for line in f.readlines() if line.strip() and not line.startswith('//')]
    except Exception as e:
        print(f"Error reading requirements file: {e}")
        return False
    
    if not libraries:
        print("No libraries found in requirements.txt")
        return False
        
    # Check if circup is installed
    try:
        subprocess.run(["circup", "--version"], 
                       stdout=subprocess.PIPE, 
                       stderr=subprocess.PIPE, 
                       check=True)
    except (subprocess.SubprocessError, FileNotFoundError):
        print("Error: circup not found. Please install it with 'pip install circup'")
        return False

    # Install each library
    success_count = 0
    for lib in libraries:
        if verbose:
            print(f"Installing {lib}...")
        
        try:
            result = subprocess.run(
                ["circup", "install", lib], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )
            
            if result.returncode == 0:
                if verbose:
                    print(f"Successfully installed {lib}")
                success_count += 1
            else:
                print(f"Failed to install {lib}: {result.stderr.strip()}")
                
        except subprocess.SubprocessError as e:
            print(f"Error installing {lib}: {e}")
    
    # Print summary
    if verbose:
        print(f"\nInstallation complete: {success_count}/{len(libraries)} libraries installed successfully")
    
    return success_count == len(libraries)

def main():
    """Main function when script is run directly"""
    print("CircuitPython Library Installer")
    print("===============================")
    
    # Get verbose flag from command line
    verbose = "--quiet" not in sys.argv
    
    # Run the installation
    success = install_libraries(verbose=verbose)
    
    # Return appropriate exit code
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())

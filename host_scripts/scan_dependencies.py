#!/usr/bin/env python3

import os
import re
import ast
from pathlib import Path
import sys
import argparse

# Built-in CircuitPython modules that don't need to be in requirements.txt
# Updated for PyPortal-specific modules
BUILTIN_MODULES = {
    # Core CircuitPython modules
    'array', 'board', 'builtins', 'busio', 'collections', 'digitalio', 'displayio', 
    'errno', 'gc', 'io', 'json', 'math', 'microcontroller', 'os', 'random', 
    're', 'storage', 'struct', 'supervisor', 'sys', 'time', 'traceback',
    
    # PyPortal specific built-in modules
    'neopixel', 'terminalio', 'pulseio', 'analogio', 'audioio', 'touchio',
    'usb_hid', 'usb_midi', 'vectorio', 'bitmaptools', 'keypad',
    'rainbowio', 'rotaryio', 'sdcardio', 'wifi', 'socketpool', 'alarm',
    'audiocore', 'audiobusio', 'audiopwmio', 'framebufferio', 'rgbmatrix',
    'pwmio', 'bitbangio', 'countio', 'paralleldisplay', 'frequencyio', 'gamepadshift',
    'msgpack', 'sharpdisplay', 'ulab', 'usb_cdc', 'usb_midi', 'i2cperipheral',
    'canio', 'dualbank', 'fontio', 'imagecapture', 'onewireio', 'tracing', 'triangle',
    'synthio', 'ssl', 'socket',
    
    # Standard Python modules that might be in CircuitPython
    'asyncio', 'binascii', 'hashlib', 'itertools', 'unittest', 
    
    # ESP32-specific modules
    'esp', 'esp32', 'espidf',
}

# Pattern to detect import statements 
IMPORT_PATTERNS = [
    re.compile(r'^\s*import\s+([\w\.]+)(?:\s+as\s+[\w\.]+)?$'),
    re.compile(r'^\s*from\s+([\w\.]+)\s+import\s+.+$'),
    re.compile(r'^\s*try:\s*$'),  # To detect try/except import blocks
]

# Enhanced mapping for PyPortal modules - this now includes submodules
PYPORTAL_MODULE_MAPPING = {
    # Core PyPortal dependencies
    'pyportal': 'adafruit_pyportal',
    'esp32spi': 'adafruit_esp32spi',
    'requests': 'adafruit_requests',
    'urequests': 'adafruit_requests',  # Alternative name
    'io': 'adafruit_io',
    'bitmap_font': 'adafruit_bitmap_font',
    'display_text': 'adafruit_display_text',
    'touchscreen': 'adafruit_touchscreen',
    
    # Handle nested imports - these are important for resolution
    'adafruit_esp32spi.adafruit_esp32spi_socket': 'adafruit_esp32spi',
    'adafruit_esp32spi.adafruit_esp32spi_wifimanager': 'adafruit_esp32spi',
    'adafruit_esp32spi.adafruit_esp32spi_wsgiserver': 'adafruit_esp32spi',
    'adafruit_io.adafruit_io': 'adafruit_io',
    'adafruit_io.adafruit_io_errors': 'adafruit_io',
    'adafruit_io.adafruit_io_mqtt': 'adafruit_io',
    'adafruit_io.adafruit_io_restapi': 'adafruit_io',
    
    # Common PyPortal add-ons
    'miniqr': 'adafruit_miniqr',
    'minimqtt': 'adafruit_minimqtt',
    'wiznet': 'adafruit_wiznet5k',
    'wiznet5k': 'adafruit_wiznet5k',
    'rgb_display': 'adafruit_rgb_display',
    'hcsr04': 'adafruit_hcsr04',
    'thermal_printer': 'adafruit_thermal_printer',
    'simpleio': 'adafruit_simpleio',
    'feedparser': 'adafruit_feedparser',
    'portalbase': 'adafruit_portalbase',
    'matrixportal': 'adafruit_matrixportal',
    'fakerequests': 'adafruit_fakerequests',
    'imageload': 'adafruit_imageload',
    'gizmo': 'adafruit_gizmo',
    'lis3dh': 'adafruit_lis3dh',
    
    # Display libraries
    'display_shapes': 'adafruit_display_shapes',
    'display_text': 'adafruit_display_text',
    'bitmap_font': 'adafruit_bitmap_font',
    'display_button': 'adafruit_button',
}

# Map these to None as they're built-in
for module in BUILTIN_MODULES:
    PYPORTAL_MODULE_MAPPING[module] = None

def extract_imports_from_ast(file_path):
    """Extract imports from Python file using AST (more accurate)"""
    full_imports = set()  # This will include full paths like adafruit_esp32spi.adafruit_esp32spi_socket
    base_imports = set()  # This will include only base modules like adafruit_esp32spi
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
        
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for name in node.names:
                    # Store both the full name and the base module name
                    full_imports.add(name.name)
                    base_imports.add(name.name.split('.')[0])
                    
            elif isinstance(node, ast.ImportFrom):
                if node.level == 0:  # Absolute import
                    if node.module:
                        # Store both the full name and the base module name
                        full_imports.add(node.module)
                        base_imports.add(node.module.split('.')[0])
        
        return full_imports, base_imports
    except (SyntaxError, UnicodeDecodeError, IOError):
        # Fall back to regex-based extraction for files with syntax errors
        return extract_imports_with_regex(file_path)

def extract_imports_with_regex(file_path):
    """Extract imports using regex as fallback"""
    full_imports = set()
    base_imports = set()
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
        for line in lines:
            for pattern in IMPORT_PATTERNS:
                match = pattern.match(line)
                if match and len(match.groups()) > 0:
                    # Get the full module path
                    full_module = match.group(1)
                    full_imports.add(full_module)
                    
                    # Extract the base module name
                    base_module = full_module.split('.')[0]
                    base_imports.add(base_module)
    except (IOError, UnicodeDecodeError):
        print(f"Warning: Could not parse {file_path}")
    
    return full_imports, base_imports

def find_python_files(directory):
    """Find all Python files in the directory recursively"""
    python_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                python_files.append(os.path.join(root, file))
    return python_files

def read_requirements(req_file):
    """Read requirements from requirements.txt"""
    requirements = set()
    if os.path.exists(req_file):
        with open(req_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('//') and not line.startswith('#'):
                    requirements.add(line)
    return requirements

def get_adafruit_module_names(import_name):
    """Convert import name to the corresponding Adafruit module name(s)"""
    # Check full path mapping first
    if import_name in PYPORTAL_MODULE_MAPPING:
        module = PYPORTAL_MODULE_MAPPING[import_name]
        return [module] if module else []
    
    # Then check base module
    base_module = import_name.split('.')[0]
    if base_module in PYPORTAL_MODULE_MAPPING:
        module = PYPORTAL_MODULE_MAPPING[base_module]
        return [module] if module else []
    
    # If it starts with adafruit_, it's an Adafruit library
    if base_module.startswith('adafruit_'):
        return [base_module]
    
    return []

def extract_socket_dependencies(file_path):
    """Extract socket-related dependencies that might be missed"""
    additional_deps = set()
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Check for specific socket imports that indicate adafruit_esp32spi dependency
        if "import adafruit_esp32spi.adafruit_esp32spi_socket as socket" in content:
            additional_deps.add('adafruit_esp32spi')
        if "from adafruit_esp32spi import adafruit_esp32spi_socket" in content:
            additional_deps.add('adafruit_esp32spi')
            
    except (IOError, UnicodeDecodeError):
        pass
    
    return additional_deps

def update_requirements_file(req_file, missing_requirements):
    """Update requirements.txt file with missing requirements"""
    try:
        with open(req_file, 'a') as f:
            f.write('\n# Added by dependency scanner\n')
            for req in sorted(missing_requirements):
                f.write(f"{req}\n")
        return True
    except (IOError, PermissionError) as e:
        print(f"Error updating requirements file: {e}")
        return False

def get_common_adafruit_modules():
    """Get a list of common Adafruit CircuitPython modules"""
    common_modules = [
        # Display modules
        'adafruit_display_text',
        'adafruit_display_shapes',
        'adafruit_bitmap_font',
        'adafruit_imageload',
        'adafruit_button',
        
        # Hardware interfaces
        'adafruit_esp32spi',
        'adafruit_bus_device',
        'adafruit_register',
        'adafruit_requests',
        'adafruit_connection_manager',
        
        # Sensors
        'adafruit_bme280',
        'adafruit_dht',
        'adafruit_lis3dh',
        'adafruit_lsm6ds',
        'adafruit_bno055',
        'adafruit_hcsr04',
        
        # Displays
        'adafruit_ili9341',
        'adafruit_st7735r',
        'adafruit_st7789',
        'adafruit_pcd8544',
        'adafruit_rgb_display',
        
        # Special devices
        'adafruit_pyportal',
        'adafruit_matrixportal',
        'adafruit_portalbase',
        'adafruit_magtag',
        'adafruit_funhouse',
        'adafruit_clue',
        
        # Input
        'adafruit_touchscreen',
        'adafruit_neokey',
        'adafruit_neotrellis',
        
        # Networking and connectivity
        'adafruit_io',
        'adafruit_minimqtt',
        'adafruit_wiznet5k',
        'adafruit_esp32spi_wifimanager',
        
        # Other common libraries
        'adafruit_simpleio',
        'adafruit_thermal_printer',
        'adafruit_motor',
        'adafruit_led_animation',
        'adafruit_typing',
        'adafruit_neopixel',
        'adafruit_framebuf',
        'adafruit_pixel_framebuf',
    ]
    
    return common_modules

def select_additional_libraries(detected_modules, existing_requirements):
    """Interactive mode to select additional libraries to include"""
    print("\n=== Interactive Library Selection ===")
    print("Select additional libraries to include in requirements.txt")
    
    # Get common libraries that aren't already detected
    common_libraries = get_common_adafruit_modules()
    candidates = []
    
    # First add libraries from existing requirements that aren't detected
    for lib in sorted(existing_requirements):
        if lib not in detected_modules:
            candidates.append((lib, True, "From existing requirements.txt"))
    
    # Then add common libraries that aren't detected or in requirements
    for lib in sorted(common_libraries):
        if lib not in detected_modules and lib not in existing_requirements:
            candidates.append((lib, False, "Common CircuitPython library"))
    
    # Allow custom entry
    print("\nCurrent libraries:")
    for lib in sorted(detected_modules):
        print(f"  ✓ {lib} (auto-detected)")
    
    print("\nAdditional libraries:")
    if not candidates:
        print("  No additional libraries found")
        return []
    
    # Display candidates with numbers
    for i, (lib, is_selected, source) in enumerate(candidates):
        status = "✓" if is_selected else " "
        print(f"  [{i+1}] [{status}] {lib} ({source})")
    
    # Prompt for selection
    print("\nEnter numbers to toggle selection (comma-separated), 'a' to select all,")
    print("'n' to select none, 'c' to add a custom library, or 'q' to finish:")
    
    selected = [lib for lib, is_selected, _ in candidates if is_selected]
    
    while True:
        choice = input("> ").strip().lower()
        
        if choice == 'q':
            break
        elif choice == 'a':
            selected = [lib for lib, _, _ in candidates]
            print("Selected all libraries")
        elif choice == 'n':
            selected = []
            print("Deselected all libraries")
        elif choice == 'c':
            custom = input("Enter custom library name: ").strip()
            if custom and custom not in detected_modules and custom not in selected:
                selected.append(custom)
                print(f"Added {custom}")
        else:
            try:
                # Parse comma-separated list of numbers
                indices = [int(idx.strip()) - 1 for idx in choice.split(',')]
                for idx in indices:
                    if 0 <= idx < len(candidates):
                        lib = candidates[idx][0]
                        if lib in selected:
                            selected.remove(lib)
                            print(f"Deselected {lib}")
                        else:
                            selected.append(lib)
                            print(f"Selected {lib}")
                    else:
                        print(f"Invalid selection: {idx+1}")
            except ValueError:
                print("Invalid input. Enter numbers, 'a', 'n', 'c', or 'q'")
    
    return selected

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='CircuitPython PyPortal Dependency Scanner')
    parser.add_argument('-u', '--update', action='store_true', 
                        help='Update requirements.txt with missing dependencies')
    parser.add_argument('-c', '--clean', action='store_true',
                        help='Show only clean list of requirements without extra info')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Minimal output (works well with --clean)')
    parser.add_argument('-d', '--deep', action='store_true',
                        help='Perform deeper analysis for hard-to-detect dependencies')
    parser.add_argument('-i', '--interactive', action='store_true',
                        help='Interactive mode to select additional libraries')
    args = parser.parse_args()

    # Find project root directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.dirname(script_dir)
    
    # Path to requirements.txt
    req_file = os.path.join(root_dir, 'requirements.txt')
    
    if not args.quiet:
        print("CircuitPython PyPortal Dependency Scanner")
        print("===============================")
        print(f"Project directory: {root_dir}")
    
    # Find all Python files
    python_files = find_python_files(root_dir)
    if not args.quiet:
        print(f"Found {len(python_files)} Python files to scan")
    
    # Read existing requirements
    existing_requirements = read_requirements(req_file)
    if not args.quiet:
        print(f"Found {len(existing_requirements)} entries in requirements.txt")
    
    # Extract imports from all files
    all_full_imports = set()
    all_base_imports = set()
    additional_deps = set()
    
    for file in python_files:
        # Skip files in lib directory as they are installed packages
        if '/lib/' in file or '\\lib\\' in file:
            continue
        
        # Print progress for larger projects
        if not args.quiet and not args.clean and len(python_files) > 10:
            print(f"Scanning {os.path.relpath(file, root_dir)}...")
        
        full_imports, base_imports = extract_imports_from_ast(file)
        all_full_imports.update(full_imports)
        all_base_imports.update(base_imports)
        
        # If deep scanning is enabled, look for special cases
        if args.deep:
            additional_deps.update(extract_socket_dependencies(file))
    
    # Convert to potential Adafruit library names
    adafruit_modules = set()
    
    # Process full imports (including submodules)
    for imp in all_full_imports:
        modules = get_adafruit_module_names(imp)
        adafruit_modules.update([m for m in modules if m])
    
    # Process base imports
    for imp in all_base_imports:
        modules = get_adafruit_module_names(imp)
        adafruit_modules.update([m for m in modules if m])
    
    # Add any additional dependencies found through deeper analysis
    adafruit_modules.update(additional_deps)
    
    # Find modules not in requirements.txt
    missing_requirements = adafruit_modules - existing_requirements
    
    # Ensure required core dependencies are suggested for PyPortal
    core_pyportal_deps = {
        'adafruit_pyportal', 'adafruit_esp32spi', 'adafruit_requests',
        'adafruit_io', 'adafruit_bitmap_font', 'adafruit_display_text'
    }
    
    # If the project imports adafruit_pyportal or seems to be a PyPortal project,
    # suggest adding the core PyPortal dependencies that might be missing
    if 'adafruit_pyportal' in adafruit_modules or any('pyportal' in file.lower() for file in python_files):
        for dep in core_pyportal_deps:
            if dep not in existing_requirements:
                missing_requirements.add(dep)
    
    # Interactive mode to select additional libraries
    additional_libraries = []
    if args.interactive and not args.clean and not args.quiet:
        additional_libraries = select_additional_libraries(adafruit_modules, existing_requirements)
        if additional_libraries:
            print(f"\nAdding {len(additional_libraries)} manually selected libraries:")
            for lib in sorted(additional_libraries):
                print(f"  + {lib}")
            missing_requirements.update(additional_libraries)
    
    # Show results
    if args.clean:
        # Clean output - just the requirements
        if missing_requirements:
            print("\n".join(sorted(missing_requirements)))
    elif not args.quiet:
        print("\nResults:")
        print(f"Total imports found: {len(all_base_imports)} base modules, {len(all_full_imports)} full paths")
        print(f"Potential Adafruit libraries: {len(adafruit_modules)}")
        
        if missing_requirements:
            print("\nMissing from requirements.txt:")
            for req in sorted(missing_requirements):
                if req in additional_libraries:
                    print(f"  - {req} (manually selected)")
                else:
                    print(f"  - {req}")
            
            print("\nConsider adding these to requirements.txt:")
            print("----------------------------------------")
            for req in sorted(missing_requirements):
                print(req)
        else:
            print("\nAll detected dependencies are already in requirements.txt")
        
        # Verify existing requirements are actually used
        unused_requirements = existing_requirements - adafruit_modules - set(additional_libraries)
        if unused_requirements:
            print("\nPossibly unused requirements (but keep them if needed):")
            for req in sorted(unused_requirements):
                print(f"  - {req}")
    
    # Update requirements.txt if requested
    if args.update and missing_requirements:
        if not args.quiet:
            print("\nUpdating requirements.txt...")
        
        success = update_requirements_file(req_file, missing_requirements)
        
        if not args.quiet:
            if success:
                print(f"Successfully added {len(missing_requirements)} dependencies to {req_file}")
            else:
                print("Failed to update requirements.txt")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

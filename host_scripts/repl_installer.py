# Small helper to trigger library installation from the REPL

def install():
    """
    Function to be called from CircuitPython REPL to install libraries
    
    Usage from REPL:
    >>> import repl_installer
    >>> repl_installer.install()
    """
    import os
    import sys
    
    print("Starting library installation from REPL...")
    
    # Change directory to the script location
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    try:
        # Import and run the library installer
        from host_scripts import install_libs
        success = install_libs.install_libraries()
        
        if success:
            print("\nAll libraries installed successfully!")
        else:
            print("\nSome libraries failed to install. Check output for details.")
            
    except Exception as e:
        print(f"Error during installation: {e}")
        
    return

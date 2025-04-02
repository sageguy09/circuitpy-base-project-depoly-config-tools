# CircuitPython REPL helper to install libraries
# Copy this file to your CircuitPython device, then import it in REPL

import board
import time
import gc

def install():
    """
    Print a marker that can be detected by the host-side script
    to trigger library installation
    """
    # Free memory before we start
    gc.collect()
    
    print("\n\n")  # Clear some space
    print("===== CIRCUITPY_LIB_INSTALL_REQUEST =====")
    print(f"Device: {board.board_id if hasattr(board, 'board_id') else 'unknown'}")
    print(f"Time: {time.monotonic()}")
    print("----------------------------------------")
    print("To install libraries, run THIS command on your computer:")
    print("python3 host_scripts/circup_installer.py --monitor")
    print("----------------------------------------")
    print("Keep this REPL connection open until you see")
    print("confirmation that installation is complete.")
    print("===== CIRCUITPY_LIB_INSTALL_END =====")
    print("\n")
    
    # Some boards might need a small delay
    time.sleep(0.1)
    
    return True

# Automatically run the function when imported by default
print("CircuitPython Library Installation Helper")
print("========================================")
print("Run repl_installer.install() to start installation")

# CircuitPython REPL helper to install libraries from requirements.txt
# Copy this file to your CircuitPython device, then import it in REPL

import board
import time
import gc

def install_reqs():
    """
    Print special marker codes that can be detected by a host-side script
    to trigger library installation using circup
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

# Auto-run when imported
print("CircuitPython Library Installation Helper")
print("========================================")
install_reqs()

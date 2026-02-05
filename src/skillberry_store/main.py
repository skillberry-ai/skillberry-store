import os
import signal
import atexit
from skillberry_store.fast_api.server import SBS
from skillberry_store.modules.ui_manager import UIManager

# Global UI manager instance
ui_manager = None

def cleanup_ui():
    """Cleanup function to stop UI server on exit."""
    global ui_manager
    if ui_manager and ui_manager.is_running():
        ui_manager.stop()

def signal_handler(signum, frame):
    """Handle termination signals."""
    cleanup_ui()
    exit(0)

def main():
    """
    The main entry point of the application.

    Initializes and runs the SBS server with UI.
    """
    global ui_manager
    
    # Initialize server to get settings
    server = SBS()
    
    # Check if UI should be enabled (default: True, can be disabled via env var)
    enable_ui = os.getenv("ENABLE_UI", "true").lower() in ("true", "1", "yes")
    
    if enable_ui:
        # Initialize and start UI manager with configured port
        ui_manager = UIManager(ui_port=server.settings.ui_port)
        
        # Register cleanup handlers
        atexit.register(cleanup_ui)
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Start UI server
        if ui_manager.start():
            print(f"\n{'='*60}")
            print(f"  Skillberry Store UI: http://localhost:{ui_manager.ui_port}")
            print(f"  Backend API: http://localhost:{server.settings.bts_port}/docs")
            print(f"{'='*60}\n")
        else:
            print("Warning: Failed to start UI server. Backend will run without UI.")
    
    # Start the backend server
    try:
        server.run()
    finally:
        cleanup_ui()

if __name__ == "__main__":
    main()

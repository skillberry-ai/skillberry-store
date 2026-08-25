import os
import sys
import signal
import atexit
from skillberry_store.fast_api.server import SBS
from skillberry_store.modules.ui_manager import UIManager

# Global instances
ui_manager = None
server_instance = None

def cleanup_ui():
    """Cleanup function to stop UI server on exit."""
    global ui_manager
    if ui_manager and ui_manager.is_running():
        ui_manager.stop()

def cleanup_vmcp_servers():
    """Cleanup function to stop all VMCP servers on exit."""
    global server_instance
    if server_instance and hasattr(server_instance.state, 'vmcp_server_manager'):
        try:
            server_instance.state.vmcp_server_manager.cleanup_all_servers()
        except Exception as e:
            print(f"Error cleaning up VMCP servers: {e}")

def cleanup_all():
    """Cleanup all resources on exit."""
    cleanup_vmcp_servers()
    cleanup_ui()

def signal_handler(signum, frame):
    """Handle termination signals."""
    cleanup_all()
    exit(0)

def main():
    """
    The main entry point of the application.

    Initializes and runs the SBS server with UI.
    """
    global ui_manager, server_instance

    # Initialize server to get settings
    server = SBS()
    server_instance = server

    # Register cleanup handlers
    atexit.register(cleanup_all)
    signal.signal(signal.SIGINT, signal_handler)
    # SIGTERM is not supported on Windows
    if os.name != "nt":
        signal.signal(signal.SIGTERM, signal_handler)

    # The UI is now served in-process by FastAPI (StaticFiles at /ui).
    # UIManager (npx vite preview) is kept as a dev-only fallback:
    # set ENABLE_UI_SUBPROCESS=true to restore the old Vite preview behaviour.
    ui_started = False
    ui_manager = None
    if os.getenv("ENABLE_UI_SUBPROCESS", "false").lower() in ("true", "1", "yes"):
        ui_manager = UIManager(ui_port=server.settings.ui_port)
        ui_started = ui_manager.start()
        if not ui_started:
            print("Warning: Failed to start UI subprocess. UI is still available via FastAPI at /ui.")

    print(f"\n{'='*60}")
    print(f"  Skillberry Store UI:  http://{server.settings.display_host}:{server.settings.sbs_port}/ui")
    print(f"  Backend API:          http://{server.settings.display_host}:{server.settings.sbs_port}/docs")
    if ui_started:
        print(f"  Vite preview (dev):  http://{server.settings.display_host}:{ui_manager.ui_port}")
    print(f"{'='*60}\n")
    sys.stdout.flush()

    # Start the backend server
    try:
        server.run()
    finally:
        cleanup_all()

if __name__ == "__main__":
    main()

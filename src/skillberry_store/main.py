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
    ui_started = False
    ui_manager = None

    # Check if UI should be enabled (default: True, can be disabled via env var)
    enable_ui = os.getenv("ENABLE_UI", "true").lower() in ("true", "1", "yes")
    
    if enable_ui:
        # Initialize and start UI manager with configured port
        ui_manager = UIManager(ui_port=server.settings.ui_port)
        
        # Register cleanup handlers
        atexit.register(cleanup_all)
        signal.signal(signal.SIGINT, signal_handler)
        # SIGTERM is not supported on Windows
        if os.name != "nt":
            signal.signal(signal.SIGTERM, signal_handler)
        
        # Start UI server
        ui_started = ui_manager.start()

        if not ui_started:
            print("Warning: Failed to start UI server. Backend will run without UI.")

    host = server.settings.display_host
    port = server.settings.sbs_port
    agent_mcp_port = server.settings.agent_mcp_port
    agent_mcp_url = f"http://{host}:{agent_mcp_port}/sse"

    print(f"\n{'='*60}")
    if ui_started:
        print(f"  Skillberry Store UI: http://{host}:{ui_manager.ui_port}")
    print(f"  Backend API: http://{host}:{port}/docs")
    if getattr(server, "agent_mcp", None) is not None:
        print(f"  Store MCP:   {agent_mcp_url}")
        print()
        print(f"  Connect Claude Code to the Store MCP:")
        print(f"    claude mcp add skillberry-store -s user -t sse {agent_mcp_url}")
        print(f"  Remove:")
        print(f"    claude mcp remove skillberry-store -s user")
    print(f"{'='*60}\n")
    sys.stdout.flush()

    # Start the backend server
    try:
        server.run()
    finally:
        cleanup_all()

if __name__ == "__main__":
    main()

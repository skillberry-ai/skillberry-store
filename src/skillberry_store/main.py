from blueberry_tools_service.fast_api.server import BTS

def main():
    """
    The main entry point of the application.

    Initializes and runs the BTS server.
    """
    server = BTS()
    server.run()

if __name__ == "__main__":
    main()

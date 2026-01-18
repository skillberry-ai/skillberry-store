from skillberry_store.fast_api.server import SBS

def main():
    """
    The main entry point of the application.

    Initializes and runs the SBS server.
    """
    server = SBS()
    server.run()

if __name__ == "__main__":
    main()

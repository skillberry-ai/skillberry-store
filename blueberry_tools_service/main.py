from blueberry_tools_service.fast_api.server import BTS


def main():
    server=BTS()
    server.run()


if __name__ == "__main__":
    main()

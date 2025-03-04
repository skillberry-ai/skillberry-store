# A basic client for the tools service

from tools.configure import configure_logger
import logging

class ToolsClient:

    def __init__(self, name="MyToolsClient", log_level=logging.DEBUG):
        """
        Initializes a tools client instance.
        TODO add server host, port and connect

        Args:
            name (str): The name of the tools client.
            log_level (int): The logging level.
        """
        self.name = name
        self.logger = configure_logger(self.name, log_level)

        self.logger.debug(f"Tools client: {self.name} initialized.")

    def add_artifact(self, data):
        """
        A mock-up method for adding an artifact
        TODO generate full concrete methods from the server JSON using openapi-python-client

        Args:
            data: Some data to process.

        Returns:
            The processed data.
        """
        self.logger.debug(f"my_method called with data: {data}")

        try:
            # Your method logic here
            processed_data = data * 2  # Example processing
            self.logger.info(f"Data processed: {processed_data}")
            return processed_data
        except Exception as e:
            self.logger.error(f"Error processing data: {e}")
            self.logger.exception("Exception occurred:") #includes stack trace
            return None  # Or raise the exception if appropriate
        


if __name__ == "__main__":
    # Example usage
    my_instance = MyClass(name="MyInstance", log_level=logging.DEBUG) #Change log level here
    result = my_instance.my_method(10)
    print(f"Result: {result}")

    my_instance.another_method(-1)
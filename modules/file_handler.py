import inspect
import logging
import os
from typing import List, Dict

from fastapi import HTTPException
from fastapi.responses import FileResponse
from tools.shell_hook import ShellHook

logger = logging.getLogger(__name__)


class FileHandler:
    def __init__(self, directory_path: str):
        """
        Initialize the FileHandler with a directory path.

        Args:
            directory_path (str): The path of the directory to manage files.
        """
        self.directory_path = directory_path
        os.makedirs(self.directory_path, exist_ok=True)
        logger.info(f"Initialized FileHandler with directory: {self.directory_path}")
        ShellHook().execute("init_filehandler", directory_path=self.directory_path)

    def list_files(self) -> List[str]:
        """
        List all files in the directory.

        Returns:
            List[str]: A list of filenames present in the directory.

        Raises:
            HTTPException: If there is an error accessing the directory.
        """
        ShellHook().execute(
            "pre_" + inspect.stack()[0].function, directory_path=self.directory_path
        )
        try:
            files = os.listdir(self.directory_path)
            ShellHook().execute(
                "post_" + inspect.stack()[0].function,
                directory_path=self.directory_path,
            )
            logger.info(f"Listed files: {files}")
            return files
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            raise HTTPException(
                status_code=500, detail=f"Error listing files: {str(e)}"
            )
            ShellHook().execute(
                "post_fail_" + inspect.stack()[0].function,
                directory_path=self.directory_path,
            )

    def read_file(self, filename: str, raw_content: bool = False):
        """
        Read and return the contents of a file.

        Raises:
            HTTPException: If there is an error reading the file.
        """

        ShellHook().execute(
            "pre_" + inspect.stack()[0].function,
            directory_path=self.directory_path,
            filename=filename,
        )
        file_path = os.path.join(self.directory_path, filename)
        if not os.path.exists(file_path):
            ShellHook().execute(
                "post_fail_" + inspect.stack()[0].function,
                directory_path=self.directory_path,
                filename=filename,
            )
            logger.warning(f"File not found: {file_path}")
            raise HTTPException(status_code=404, detail="File not found")
        logger.info(f"Reading file: {file_path}")

        if raw_content:
            try:
                with open(file_path, "r") as file:
                    content = file.read()
            except Exception as e:
                ShellHook().execute(
                    "post_raw_content_fail_" + inspect.stack()[0].function,
                    directory_path=self.directory_path,
                    filename=filename,
                )
                logger.error(f"Error reading file '{file.filename}': {e}")
                raise HTTPException(
                    status_code=500, detail=f"Error reading file: {str(e)}"
                )
            ShellHook().execute(
                "post_raw_content_" + inspect.stack()[0].function,
                directory_path=self.directory_path,
                filename=filename,
            )
            return content
        else:
            ShellHook().execute(
                "post_" + inspect.stack()[0].function,
                directory_path=self.directory_path,
                filename=filename,
            )
            return FileResponse(file_path)

    def write_file(self, file_bytes: bytes, filename: str) -> Dict:
        """
        Write a file to the directory.

        Args:
            file (bytes): The file to save.
            filename (str): The name of the file. If not provided
                            file.filename being used

        Returns:
            dict: A message confirming the file was saved successfully.

        Raises:
            HTTPException: If there is an error saving the file.
        """
        file_path = os.path.join(self.directory_path, filename)

        ShellHook().execute(
            "pre_" + inspect.stack()[0].function,
            directory_path=self.directory_path,
            filename=filename,
        )
        try:
            with open(file_path, "wb") as f:
                f.write(file_bytes)
            logger.info(f"File saved: {file_path}")
            ShellHook().execute(
                "post_" + inspect.stack()[0].function,
                directory_path=self.directory_path,
                filename=filename,
            )
            return {"message": f"File '{filename}' saved successfully."}
        except Exception as e:
            ShellHook().execute(
                "post_fail_" + inspect.stack()[0].function,
                directory_path=self.directory_path,
                filename=filename,
            )
            logger.error(f"Error saving file '{filename}': {e}")
            raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

    def write_file_content(self, filename: str, file_content: str) -> dict:
        """
        Write a file to the directory by content.

        Args:
            filename: The file name.
            file_content: The file content to save.

        Returns:
            dict: A message confirming the file was saved successfully.

        Raises:
            HTTPException: If there is an error saving the file.
        """

        ShellHook().execute(
            "pre_" + inspect.stack()[0].function,
            directory_path=self.directory_path,
            filename=filename,
        )
        file_path = os.path.join(self.directory_path, filename)
        try:
            with open(file_path, "wb") as f:
                binary_file_content = file_content.encode("utf-8")
                f.write(binary_file_content)
            logger.info(f"File saved: {file_path}")
            ShellHook().execute(
                "post_" + inspect.stack()[0].function,
                directory_path=self.directory_path,
                filename=filename,
            )
            return {"message": f"File '{filename}' saved successfully."}
        except Exception as e:
            ShellHook().execute(
                "post_fail_" + inspect.stack()[0].function,
                directory_path=self.directory_path,
                filename=filename,
            )
            logger.error(f"Error saving file '{filename}': {e}")
            raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

    def delete_file(self, filename: str) -> dict:
        """
        Delete a file from the directory.
        """
        ShellHook().execute(
            "pre_" + inspect.stack()[0].function,
            directory_path=self.directory_path,
            filename=filename,
        )
        file_path = os.path.join(self.directory_path, filename)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"File deleted: {file_path}")
                ShellHook().execute(
                    "post_" + inspect.stack()[0].function,
                    directory_path=self.directory_path,
                    filename=filename,
                )
                return {"message": f"File '{filename}' deleted successfully."}
            else:
                raise HTTPException(
                    status_code=404, detail=f"File '{filename}' not found."
                )
        except Exception as e:
            ShellHook().execute(
                "post_fail_" + inspect.stack()[0].function,
                directory_path=self.directory_path,
                filename=filename,
            )
            logger.error(f"Error deleting file '{filename}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting file: {str(e)}"
            )

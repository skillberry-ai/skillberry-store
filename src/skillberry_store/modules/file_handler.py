import inspect
import logging
import os
import shutil
from typing import List, Dict, Optional

from fastapi import HTTPException
from fastapi.responses import FileResponse
from skillberry_store.tools.shell_hook import ShellHook

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

    def _get_full_path(self, filename: str, subdirectory: Optional[str] = None) -> str:
        """
        Get the full file path, optionally within a subdirectory.

        Args:
            filename (str): The name of the file.
            subdirectory (Optional[str]): Optional subdirectory path relative to directory_path.

        Returns:
            str: The full file path.
        """
        if subdirectory:
            # Ensure subdirectory exists
            subdir_path = os.path.join(self.directory_path, subdirectory)
            os.makedirs(subdir_path, exist_ok=True)
            return os.path.join(subdir_path, filename)
        return os.path.join(self.directory_path, filename)

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
            # Ensure directory exists before listing
            os.makedirs(self.directory_path, exist_ok=True)
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

    def read_file(self, filename: str, raw_content: bool = False, subdirectory: Optional[str] = None):
        """
        Read and return the contents of a file.

        Args:
            filename (str): The name of the file to read.
            raw_content (bool): If True, return raw content as string. If False, return FileResponse.
            subdirectory (Optional[str]): Optional subdirectory path relative to directory_path.

        Returns:
            str or FileResponse: File content as string if raw_content=True, FileResponse otherwise.

        Raises:
            HTTPException: If there is an error reading the file.
        """

        ShellHook().execute(
            "pre_" + inspect.stack()[0].function,
            directory_path=self.directory_path,
            filename=filename,
        )
        # Get full path (creates subdirectory if needed)
        file_path = self._get_full_path(filename, subdirectory)
        
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
                logger.error(f"Error reading file '{filename}': {e}")
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

    def write_file(self, file_bytes: bytes, filename: str, subdirectory: Optional[str] = None) -> Dict:
        """
        Write a file to the directory.

        Args:
            file_bytes (bytes): The file content to save.
            filename (str): The name of the file.
            subdirectory (Optional[str]): Optional subdirectory path relative to directory_path.

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
        # Get full path (creates subdirectory if needed)
        file_path = self._get_full_path(filename, subdirectory)
        
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

    def write_file_content(self, filename: str, file_content: str, subdirectory: Optional[str] = None) -> dict:
        """
        Write a file to the directory by content.

        Args:
            filename (str): The file name.
            file_content (str): The file content to save.
            subdirectory (Optional[str]): Optional subdirectory path relative to directory_path.

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
        # Get full path (creates subdirectory if needed)
        file_path = self._get_full_path(filename, subdirectory)
        
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

    def delete_file(self, filename: str, subdirectory: Optional[str] = None) -> dict:
        """
        Delete a file from the directory.

        Args:
            filename (str): The name of the file to delete.
            subdirectory (Optional[str]): Optional subdirectory path relative to directory_path.

        Returns:
            dict: A message confirming the file was deleted successfully.

        Raises:
            HTTPException: If file not found (404) or deletion fails (500).
        """
        ShellHook().execute(
            "pre_" + inspect.stack()[0].function,
            directory_path=self.directory_path,
            filename=filename,
        )
        # Get full path
        file_path = self._get_full_path(filename, subdirectory)
        
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
        except HTTPException:
            # Re-raise HTTPException without modification
            raise
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

    def delete_subdirectory(self, subdirectory: str) -> dict:
        """
        Delete a subdirectory and all its contents.

        Args:
            subdirectory (str): The subdirectory path relative to directory_path.

        Returns:
            dict: A message confirming the subdirectory was deleted successfully.

        Raises:
            HTTPException: If subdirectory not found (404) or deletion fails (500).
        """
        ShellHook().execute(
            "pre_" + inspect.stack()[0].function,
            directory_path=self.directory_path,
            subdirectory=subdirectory,
        )
        
        subdir_path = os.path.join(self.directory_path, subdirectory)
        
        try:
            if os.path.exists(subdir_path):
                shutil.rmtree(subdir_path)
                logger.info(f"Subdirectory deleted: {subdir_path}")
                ShellHook().execute(
                    "post_" + inspect.stack()[0].function,
                    directory_path=self.directory_path,
                    subdirectory=subdirectory,
                )
                return {"message": f"Subdirectory '{subdirectory}' deleted successfully."}
            else:
                raise HTTPException(
                    status_code=404, detail=f"Subdirectory '{subdirectory}' not found."
                )
        except HTTPException:
            # Re-raise HTTPException without modification
            raise
        except Exception as e:
            ShellHook().execute(
                "post_fail_" + inspect.stack()[0].function,
                directory_path=self.directory_path,
                subdirectory=subdirectory,
            )
            logger.error(f"Error deleting subdirectory '{subdirectory}': {e}")
            raise HTTPException(
                status_code=500, detail=f"Error deleting subdirectory: {str(e)}"
            )

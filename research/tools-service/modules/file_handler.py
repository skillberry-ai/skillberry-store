import os
import logging
from fastapi import  HTTPException, UploadFile
from fastapi.responses import FileResponse
from typing import List

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

    def list_files(self) -> List[str]:
        """
        List all files in the directory.

        Returns:
            List[str]: A list of filenames present in the directory.

        Raises:
            HTTPException: If there is an error accessing the directory.
        """
        try:
            files = os.listdir(self.directory_path)
            logger.info(f"Listed files: {files}")
            return files
        except Exception as e:
            logger.error(f"Error listing files: {e}")
            raise HTTPException(status_code=500, detail=f"Error listing files: {str(e)}")

    def read_file(self, filename: str):
        """
        Read and return the contents of a file.

        Args:
            filename (str): The name of the file to read.

        Returns:
            FileResponse: The file content as a downloadable response.

        Raises:
            HTTPException: If the file does not exist.
        """
        file_path = os.path.join(self.directory_path, filename)
        if not os.path.exists(file_path):
            logger.warning(f"File not found: {file_path}")
            raise HTTPException(status_code=404, detail="File not found")
        logger.info(f"Reading file: {file_path}")
        return FileResponse(file_path)

    def write_file(self, file: UploadFile) -> dict:
        """
        Write a file to the directory.

        Args:
            file (UploadFile): The file to save.

        Returns:
            dict: A message confirming the file was saved successfully.

        Raises:
            HTTPException: If there is an error saving the file.
        """
        file_path = os.path.join(self.directory_path, file.filename)
        try:
            with open(file_path, "wb") as f:
                f.write(file.file.read())
            logger.info(f"File saved: {file_path}")
            return {"message": f"File '{file.filename}' saved successfully."}
        except Exception as e:
            logger.error(f"Error saving file '{file.filename}': {e}")
            raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")

    def write_text_file(self, filename: str, content: str) -> dict:
        """
        Write a text file with specified content.

        Args:
            filename (str): The name of the text file to create.
            content (str): The content to write into the file.

        Returns:
            dict: A message confirming the file was created successfully.

        Raises:
            HTTPException: If there is an error writing the file.
        """
        file_path = os.path.join(self.directory_path, filename)
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Text file created: {file_path}")
            return {"message": f"File '{filename}' created successfully."}
        except Exception as e:
            logger.error(f"Error writing file '{filename}': {e}")
            raise HTTPException(status_code=500, detail=f"Error writing file: {str(e)}")

    def delete_file(self, filename: str) -> dict:
        """
        Delete a file from the directory.
        """
        file_path = os.path.join(self.directory_path, filename)
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"File deleted: {file_path}")
                return {"message": f"File '{filename}' deleted successfully."}
            else:
                raise HTTPException(status_code=404, detail=f"File '{filename}' not found.")
        except Exception as e:
                logger.error(f"Error deleting file '{filename}': {e}")
                raise HTTPException(status_code=500, detail=f"Error deleting file: {str(e)}")

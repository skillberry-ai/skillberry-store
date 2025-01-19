import logging
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from modules.description import Description
from modules.description_vector_index import DescriptionVectorIndex
from modules.file_handler import FileHandler
from modules.python_executor import PythonExecutor
from tools.configure import get_directory_path, get_descriptions_directory

logger = logging.getLogger(__name__)


def create_app():
    directory_path = get_directory_path()
    descriptions_directory = get_descriptions_directory()

    file_handler = FileHandler(directory_path)
    python_executor = PythonExecutor(directory_path)
    descriptions = Description(descriptions_directory=descriptions_directory,
                               vector_index=DescriptionVectorIndex)

    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/files", response_model=List[str])
    def list_files():
        logger.info("Request to list files")
        return file_handler.list_files()

    @app.get("/files/{filename}")
    def read_file(filename: str):
        logger.info(f"Request to read file: {filename}")
        description = descriptions.read_description(filename)
        if description:
            logger.info(f"Description for {filename}: {description}")
        return file_handler.read_file(filename)

    @app.post("/files")
    def write_file(file: UploadFile = File(...), description: Optional[str] = None):
        logger.info(f"Request to upload file: {file.filename}")
        file_response = file_handler.write_file(file)
        if description:
            descriptions.write_description(file.filename, description)
        return file_response

    @app.post("/files/text")
    def write_text_file(filename: str = Form(...), content: str = Form(...), description: Optional[str] = None):
        logger.info(f"Request to create text file: {filename}")
        file_response = file_handler.write_text_file(filename, content)
        if description:
            descriptions.write_description(filename, description)
        return file_response

    @app.delete("/files/{filename}")
    def delete_file(filename: str):
        logger.info(f"Request to delete file: {filename}")
        file_handler.delete_file(filename)
        descriptions.delete_description(filename)  # Delete associated description as well
        return {"message": f"File and its description '{filename}' deleted successfully."}

    @app.post("/files/execute/{filename}")
    def execute_python_file(filename: str):
        logger.info(f"Request to execute Python file: {filename}")
        return python_executor.execute_python_file(filename)

    @app.post("/description/update/{filename}")
    def update_description(filename: str, new_description: str):
        logger.info(f"Request to update description for file: {filename}")
        return descriptions.update_description(filename, new_description)

    @app.get("/description/search",response_model= list[dict[str, str]] )
    def search_description(search_term: str):
        logger.info(f"Request to search descriptions for term: {search_term}")
        return descriptions.search_description(search_term)

    @app.post("/files/execute/{filename}")
    def execute_python_file(filename: str):
        logger.info(f"Request to execute Python file: {filename}")
        return python_executor.execute_python_file(filename)

    return app

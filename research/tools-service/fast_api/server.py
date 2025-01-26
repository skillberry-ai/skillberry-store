import logging
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware

from modules.metadata import Metadata
from modules.description import Description
from modules.description_vector_index import DescriptionVectorIndex
from modules.file_handler import FileHandler
from modules.file_executor import FileExecutor
from tools.configure import get_files_directory_path, get_descriptions_directory, get_metadata_directory

logger = logging.getLogger(__name__)


def file_api(app, descriptions: Description, metadata: Metadata, tags: str):
    files_directory_path = get_files_directory_path()
    file_handler = FileHandler(files_directory_path)

    @app.get("/files", response_model=List[str], tags=tags)
    def list_files():
        logger.info("Request to list files")
        return file_handler.list_files()

    @app.get("/file/json/{filename}", tags=tags)
    def read_file_json(filename: str):
        logger.info(f"Request to read file: {filename}")
        file_description = descriptions.read_description(filename)
        file_metadata = metadata.read_metadata(filename)
        content = file_handler.read_file(filename, raw_content=True)
        return {"content": content, "description": file_description, "metadata": file_metadata}

    @app.get("/file/{filename}", tags=tags)
    def read_file(filename: str):
        logger.info(f"Request to read file: {filename}")
        file_description = descriptions.read_description(filename)
        file_metadata = metadata.read_metadata(filename)
        if file_description:
            logger.info(f"Description for {filename}: {file_description}")
        if file_metadata:
            logger.info(f"metadata for {filename}: {file_metadata}")
        return file_handler.read_file(filename)

    @app.post("/file", tags=tags)
    def write_file(file: UploadFile = File(...),
                   file_description: Optional[str] = None,
                   file_metadata: Optional[str] = None):
        logger.info(f"Request to upload file: {file.filename}")
        file_response = file_handler.write_file(file)
        if file_description:
            descriptions.write_description(file.filename, file_description)
        if metadata:
            metadata.write_metadata(file.filename, file_metadata)
        return file_response

    @app.delete("/file/{filename}", tags=tags)
    def delete_file(filename: str):
        logger.info(f"Request to delete file: {filename}")
        file_handler.delete_file(filename)
        # Delete associated description as well
        descriptions.delete_description(filename)
        return {"message": f"File and its description '{filename}' deleted successfully."}

    return file_handler


def descriptions_api(app, tags: str):
    descriptions_directory = get_descriptions_directory()
    descriptions = Description(descriptions_directory=descriptions_directory,
                               vector_index=DescriptionVectorIndex)

    @app.post("/description/update/{filename}", tags=tags)
    def update_description(filename: str, new_description: str):
        logger.info(f"Request to update description for file: {filename}")
        return descriptions.update_description(filename, new_description)

    @app.get("/description/search", response_model=list[dict[str, str | Any]], tags=tags)
    def search_description(search_term: str, max_numer_of_results: int = 5, similarity_threshold: float = 1):
        logger.info(f"Request to search descriptions for term: {search_term}")
        search_results = descriptions.search_description(search_term=search_term, k=max_numer_of_results)

        search_results_filtered = [search_result for search_result in search_results if
                                   search_result["similarity_score"] <= similarity_threshold]
        return search_results_filtered

    @app.get("/description/{filename}", tags=tags)
    def read_description(filename: str):
        logger.info(f"Request to read description for file: {filename}")
        file_description = descriptions.read_description(filename)
        if file_description:
            logger.info(f"Description for {filename}: {file_description}")
        return file_description

    return descriptions


def metadata_api(app, tags: str):
    metadata_directory = get_metadata_directory()
    metadata = Metadata(metadata_directory=metadata_directory)

    @app.post("/metadata/update/{filename}", tags=tags)
    def update_metadata(filename: str, new_metadata: Dict[str, Any]):
        logger.info(f"Request to update metadata for file: {filename}")
        return metadata.update_metadata(filename, new_metadata)

    @app.get("/metadata/{filename}", tags=tags)
    def read_metadata(filename: str):
        logger.info(f"Request to read metadata for file: {filename}")
        file_metadata = metadata.read_metadata(filename)
        if file_metadata:
            logger.info(f"Metadata for {filename}: {file_metadata}")
        return file_metadata

    return metadata


def execute_api(app, tags: str, file_handler: FileHandler, metadata: Metadata):
    @app.post("/execute/{filename}", tags=tags)
    def execute_file(filename: str, parameters: Optional[Dict[str, Any]] = None):
        logger.info(f"Request to execute file: {filename} with parameters: {parameters}")

        file_content = file_handler.read_file(filename, raw_content=True)
        file_metadata = metadata.read_metadata(filename)

        file_executor = FileExecutor(filename=filename, file_content=file_content, file_metadata=file_metadata)
        return file_executor.execute_file(parameters=parameters)


def create_app():
    openapi_tags = [
        {
            "name": "files",
            "description": "Operations for files (Agentic tools)",
        },
        {
            "name": "descriptions",
            "description": "Operations for descriptions (tool descriptions, semantic search, etc.)",
        },
        {
            "name": "metadata",
            "description": "Operations for metadata (tools metadata, programming language, packaging format, "
                           "security, etc.)",
        },
        {
            "name": "execution",
            "description": "Execution operations (tools execution) ",
        },
    ]
    app = FastAPI(title="blueberry",
                  summary="Towards hallucination-less AI systems",
                  openapi_tags=openapi_tags,
                  contact={
                      "name": "Eran Raichstein",
                      "email": "eranra@il.ibm.com",
                  })

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    descriptions = descriptions_api(app=app, tags=["descriptions"])
    metadata = metadata_api(app=app, tags=["metadata"])
    file_handler = file_api(app=app, descriptions=descriptions, metadata=metadata, tags=["files"])
    execute_api(app=app, metadata=metadata, file_handler=file_handler, tags=["execution"])

    return app

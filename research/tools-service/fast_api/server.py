import json
import logging
import os
import re
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, File, UploadFile, Path, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from modules.lifecycle import LifecycleState, LifecycleManager
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
    def list_files(lifecycle_state: LifecycleState = LifecycleState.ANY):
        logger.info("Request to list files")
        files = file_handler.list_files()

        # if we are requested to limit the view to a specific lifecycle state, we filter the results
        if lifecycle_state is not LifecycleState.ANY:
            lifecycle_filtered_matched_files = []
            for file_name in files:
                file_metadata = metadata.read_metadata(file_name)
                if file_metadata is None:
                    continue
                life_cycle_manager = LifecycleManager(file_metadata)
                if life_cycle_manager.get_state() != lifecycle_state:
                    continue
                lifecycle_filtered_matched_files.append(file_name)
            files = lifecycle_filtered_matched_files

        return files

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
        if file_metadata:
            metadata_as_dict = json.loads(file_metadata)
            metadata.write_metadata(file.filename, metadata_as_dict)
        return file_response

    @app.post("/file/json/{filename}", tags=tags)
    def write_file_json(file_name: str, file_json: dict):
        logger.info(f"Request to write file (from json): {file_name}")
        file_content = file_json.get("content", "")
        file_description = file_json.get("description", "")
        file_metadata = file_json.get("metadata", {})

        file_response = file_handler.write_file_content(file_name, file_content)
        if file_description:
            descriptions.write_description(file_name, file_description)
        if file_metadata:
            metadata.write_metadata(file_name, file_metadata)

        return file_response

    @app.delete("/file/{filename}", tags=tags)
    def delete_file(filename: str):
        logger.info(f"Request to delete file: {filename}")
        file_handler.delete_file(filename)
        # Delete associated description as well
        descriptions.delete_description(filename)
        # Delete associated metadata as well
        metadata.delete_metadata(filename)
        return {"message": f"File and its description '{filename}' deleted successfully."}

    @app.post("/rename/file/{filename}", tags=tags)
    def rename_file(src_filename: str, dest_filename: str):
        logger.info(f"Request to rename file: {src_filename} to {dest_filename}")
        try:
            file_json = read_file_json(src_filename)
            write_file_json(dest_filename, file_json)
        except Exception as e:
            logger.error(f"Error renaming file '{src_filename}': {e}")
            raise HTTPException(status_code=500, detail=f"Error renaming file: {str(e)}")
        delete_file(src_filename)
        return {"message": f"File: {src_filename} renamed to {dest_filename} successfully."}

    @app.delete("/files", tags=tags)
    def delete_files(regex: str = ".", lifecycle_state: LifecycleState = LifecycleState.UNKNOWN):
        logger.info("Request to delete files")
        files = get_filtered_matched_files(file_handler.list_files(),
                                           metadata,
                                           regex,
                                           lifecycle_state)

        # delete the files after filtering
        for file_name in files:
            delete_file(file_name)
            logger.info(f"File {file_name} Deleted.")

        return f"Files {files} Deleted."

    @app.post("/export/files", tags=tags)
    def export_files(path: str,
                     regex: str = ".",
                     lifecycle_state: LifecycleState = LifecycleState.UNKNOWN):
        logger.info("Request to export files")
        files = get_filtered_matched_files(file_handler.list_files(),
                                           metadata,
                                           regex,
                                           lifecycle_state)
        # export the files to the destination folder
        for file_name in files:
            file_json = read_file_json(file_name)
            with open(f"{path}/{file_name}", "w") as file:
                json.dump(file_json, file, indent=4)

        return f"Files {files} exported to {path}."

    @app.post("/import/files", tags=tags)
    def import_files(path: str):
        logger.info("Request to import files")

        # for each file in the path, read and import
        files = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        for file in files:
            with open(f"{path}/{file}", "r") as f:
                file_json = json.load(f)
                _ = write_file_json(file_name=file, file_json=file_json)

        return f"Files {files} imported from {path}."

    return file_handler


def get_filtered_matched_files(files: List[str],
                               metadata: Metadata,
                               regex: str = ".",
                               lifecycle_state: LifecycleState = LifecycleState.UNKNOWN) -> List[str]:
    lifecycle_filtered_matched_files = []
    for file_name in files:
        file_metadata = metadata.read_metadata(file_name)
        if file_metadata is None:
            continue
        life_cycle_manager = LifecycleManager(file_metadata)

        # Skip comparing to lifecycle_state if it is ANY
        if lifecycle_state is not LifecycleState.ANY:
            if life_cycle_manager.get_state() != lifecycle_state:
                continue

        if not re.match(regex, file_name):
            continue
        lifecycle_filtered_matched_files.append(file_name)
    files = lifecycle_filtered_matched_files
    return files


def descriptions_api(app, metadata, tags: str):
    descriptions_directory = get_descriptions_directory()
    descriptions = Description(descriptions_directory=descriptions_directory,
                               vector_index=DescriptionVectorIndex)

    @app.post("/description/update/{filename}", tags=tags)
    def update_description(filename: str, new_description: str):
        logger.info(f"Request to update description for file: {filename}")
        return descriptions.update_description(filename, new_description)

    @app.get("/description/search", response_model=list[dict[str, str | Any]], tags=tags)
    def search_description(search_term: str,
                           max_numer_of_results: int = 5,
                           similarity_threshold: float = 1,
                           lifecycle_state: LifecycleState = LifecycleState.APPROVED):
        logger.info(f"Request to search descriptions for term: {search_term}")
        matched_files = descriptions.search_description(
            search_term=search_term,
            k=max_numer_of_results)

        filtered_matched_files = [matched_file for matched_file in matched_files if
                                  matched_file["similarity_score"] <= similarity_threshold]

        # if we are requested to limit the search to a specific lifecycle state, we filter the results
        if lifecycle_state is not LifecycleState.ANY:
            lifecycle_filtered_matched_files = []
            for matched_file in filtered_matched_files:
                file_metadata = metadata.read_metadata(matched_file["filename"])
                if file_metadata is None:
                    continue
                life_cycle_manager = LifecycleManager(file_metadata)
                if life_cycle_manager.get_state() != lifecycle_state:
                    continue
                lifecycle_filtered_matched_files.append(matched_file)
            return lifecycle_filtered_matched_files

        return filtered_matched_files

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

    @app.get("/lifecycle_state/{filename}", tags=tags)
    def read_lifecycle_state(filename: str) -> LifecycleState:
        logger.info(f"Request to read lifecycle state for file: {filename}")
        file_metadata = metadata.read_metadata(filename)
        if file_metadata is None:
            logger.info(f"Metadata for {filename}: {file_metadata}")
            return LifecycleState.UNKNOWN

        life_cycle_manager = LifecycleManager(file_metadata)
        return life_cycle_manager.get_state()

    @app.post("/lifecycle_state/update/{filename}", tags=tags)
    def update_lifecycle_state(filename: str, state: LifecycleState):
        logger.info(f"Request to update lifecycle state for file: {filename} into {state}")
        file_metadata = read_metadata(filename)

        if state is LifecycleState.ANY:
            logger.info(f"Metadata for {filename} can't be updated to {state}")
            return {"message": f"Metadata for {filename} can't be updated to {state}"}

        if file_metadata is None:
            logger.info(f"Metadata for {filename} Doesnt exist")
            return {"message": f"Metadata for {filename} doesnt exist"}
        try:
            life_cycle_manager = LifecycleManager(file_metadata)
            life_cycle_manager.set_state(state)
            metadata.update_metadata(filename, life_cycle_manager.get_metadata())
        except Exception as e:
            logger.error(f"Error updating lifecycle state for file {filename}: {e}")
            return {"message": f"Error updating lifecycle state for file {filename}: {e}"}

        return {"message": f"Metadata for {filename} updated successfully."}

    return metadata


def execute_api(app, tags: str, file_handler: FileHandler, metadata: Metadata):
    @app.post("/execute/{filename}", tags=tags)
    def execute_file(filename: str, parameters: Optional[Dict[str, Any]] = None):
        logger.info(f"Request to execute file: {filename} with parameters: {parameters}")

        file_content = file_handler.read_file(filename, raw_content=True)
        file_metadata = metadata.read_metadata(filename)

        file_executor = FileExecutor(
            filename=filename, file_content=file_content, file_metadata=file_metadata)
        return file_executor.execute_file(parameters=parameters)


def custom_openapi(app: FastAPI, openapi_tags):
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="blueberry",
        summary="Towards hallucination-less AI systems",
        version="0.0.1",
        tags=openapi_tags,
        contact={
            "name": "Eran Raichstein",
            "email": "eranra@il.ibm.com",
        },
        routes=app.routes,
    )

    for path, methods in openapi_schema["paths"].items():
        for method in methods.keys():  # e.g., "get", "post"
            if method in ["get", "post", "put", "delete", "patch"]:  # Only HTTP methods
                url = f"http://127.0.0.1:8000{path}"

                python_example_requests = f"""import requests

response = requests.{method}("{url}")
print(response.json())"""

                curl_example = f"""curl -X {method.upper()} "{url}" """

                example_obj = {
                    "python_requests": {
                        "summary": "Python (requests)",
                        "value": python_example_requests
                    },
                    "curl": {
                        "summary": "cURL example",
                        "value": curl_example
                    }
                }

                # Add examples to the responses
                if "responses" in methods[method]:
                    methods[method]["responses"]["200"]["content"] = {
                        "text/plain": {
                            "examples": example_obj
                        }
                    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


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

    app = FastAPI()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    metadata = metadata_api(app=app, tags=["metadata"])
    descriptions = descriptions_api(app=app, metadata=metadata, tags=["descriptions"])
    file_handler = file_api(
        app=app, descriptions=descriptions, metadata=metadata, tags=["files"])
    execute_api(app=app, metadata=metadata,
                file_handler=file_handler, tags=["execution"])

    app.openapi = lambda: custom_openapi(app, openapi_tags)
    return app

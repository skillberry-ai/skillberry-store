import pytest

from skillberry_store.modules.description import Description
from skillberry_store.vdbs.identify_vdb import VectorDBType, identify_vector_db

test_descriptions_directory = "/tmp/test_vdb"

def _test_vdb(sbs_vdb):
    """Test that the health endpoint returns the expected response."""

    vector_index = identify_vector_db(sbs_vdb)
    descriptions = Description(
        descriptions_directory=test_descriptions_directory,
        vector_index=vector_index,
        vdb_type=sbs_vdb,
    )
    filename = "test_add_vectors.txt"
    descriptions.write_description(filename=filename, description="test1")
    search_results = descriptions.search_description("test1", 2)
    assert len(search_results) != 0
    assert(search_results[0]["filename"] == filename)

    descriptions.update_description(filename=filename, new_description="different")
    search_results = descriptions.search_description("different", 2)
    assert len(search_results) != 0
    assert(search_results[0]["filename"] == filename)


def test_vdb_faiss():
    sbs_vdb = "faiss"
    _test_vdb(sbs_vdb)


def test_vdb_chrome():
    sbs_vdb = "chroma"
    _test_vdb(sbs_vdb)


def test_vdb_lancedb():
    sbs_vdb = "lancedb"
    _test_vdb(sbs_vdb)


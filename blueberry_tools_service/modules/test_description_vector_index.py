import os
import pytest
import numpy as np
import faiss
from fastembed import TextEmbedding
from blueberry_tools_service.modules.description_vector_index import (
    DescriptionVectorIndex,
)


@pytest.fixture
def temp_index_file(tmp_path):
    """Fixture to create a temporary index file path."""
    return str(tmp_path / "test_index.faiss")


@pytest.fixture
def vector_index(temp_index_file):
    """Fixture to create a DescriptionVectorIndex instance."""
    return DescriptionVectorIndex(index_file=temp_index_file)


def test_initialization(vector_index, temp_index_file):
    """Test the initialization of DescriptionVectorIndex."""
    assert vector_index.index_file == temp_index_file
    assert vector_index.dimension == 384
    assert isinstance(vector_index.model, TextEmbedding)
    assert isinstance(vector_index.index, faiss.IndexFlatL2)


def test_add_description(vector_index):
    """Test adding a description to the index."""
    test_description = "This is a test description"
    test_filename = "test_file.txt"
    initial_size = vector_index.index.ntotal

    vector_index.add_description(test_description, test_filename)

    assert vector_index.index.ntotal == initial_size + 1


def test_search_description(vector_index):
    """Test searching for similar descriptions."""
    test_descriptions = [
        "The quick brown fox jumps over the lazy dog",
        "A lazy dog sleeps in the sun",
        "The cat chases the mouse",
    ]
    test_filenames = ["file1.txt", "file2.txt", "file3.txt"]

    # Add test descriptions
    for desc, fname in zip(test_descriptions, test_filenames):
        vector_index.add_description(desc, fname)

    # Search for similar descriptions
    query = "lazy dog sleeping"
    results = vector_index.search(query, k=3)

    assert len(results) == 3
    assert results[0]["filename"] == "file2.txt"


def test_update_description(vector_index):
    """Test updating a description in the index."""
    original_desc = "Original description"
    updated_desc = "Updated description"
    test_filename = "original_file.txt"

    # Add original description
    vector_index.add_description(original_desc, test_filename)
    original_size = vector_index.index.ntotal

    # Update the description
    vector_index.update_description(updated_desc, test_filename)

    assert vector_index.index.ntotal == original_size


def test_delete_description(vector_index):
    """Test deleting a description from the index."""

    # Add the descriptions
    test_descriptions = [
        "The quick brown fox jumps over the lazy dog",
        "A lazy dog sleeps in the sun",
        "The cat chases the mouse",
    ]
    test_filenames = ["file1.txt", "file2.txt", "file3.txt"]

    # Add test descriptions
    for desc, fname in zip(test_descriptions, test_filenames):
        vector_index.add_description(desc, fname)

    initial_size = vector_index.index.ntotal

    # Delete the description
    vector_index.delete_description("file1.txt")

    assert vector_index.index.ntotal == initial_size - 1


def test_save_and_load_index(temp_index_file):
    """Test saving and loading the index."""
    # Create a new index and add some data
    vector_index = DescriptionVectorIndex(index_file=temp_index_file)
    test_desc = "Test description for saving"
    test_filename = "save_file.txt"
    vector_index.add_description(test_desc, test_filename)

    # Create a new instance that should load the saved index
    new_vector_index = DescriptionVectorIndex(index_file=temp_index_file)

    assert new_vector_index.index.ntotal == 1


def test_empty_index_creation(temp_index_file):
    """Test creation of index when no file exists."""
    vector_index = DescriptionVectorIndex(index_file=temp_index_file)
    assert vector_index.index.ntotal == 0


@pytest.mark.parametrize("k", [1, 3, 5])
def test_search_with_different_k(vector_index, k):
    """Test searching with different k values."""
    descriptions = [f"Test description {i}" for i in range(5)]
    filenames = [f"file{i}.txt" for i in range(5)]
    for desc, fname in zip(descriptions, filenames):
        vector_index.add_description(desc, fname)

    results = vector_index.search("test", k=k)
    assert len(results) == min(k, len(descriptions))


def test_index_persistence(temp_index_file):
    """Test that index persists between instances."""
    # First instance
    vector_index1 = DescriptionVectorIndex(index_file=temp_index_file)
    vector_index1.add_description("Test persistence", "persistence_file.txt")

    # Second instance should load the saved index
    vector_index2 = DescriptionVectorIndex(index_file=temp_index_file)
    assert vector_index2.index.ntotal == 1

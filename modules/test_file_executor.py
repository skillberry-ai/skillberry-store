import pytest
import pytest_asyncio

from modules.file_executor import FileExecutor


@pytest.fixture
def manifest_test_tool():
    """
    Minimal manifest for the file executor usage.

    """
    return {
    "programming_language": "python",
    "packaging_format": "code",
    "name": "test_tool",
}


@pytest.fixture
def file_content_add():
    """
    Single tool code.

    """
    return (
"""
def test_tool(a: int, b: int) -> int:
    '''
    Adds two integer numbers and returns the result.

    Args:
        a (int): The first number to be added.
        b (int): The second number to be added.

    Returns:
        int: The result of adding a and b.
    '''
    return a + b
""")
@pytest.fixture
def executor_instance_add(manifest_test_tool, file_content_add):
    """Fixture to create a FileExecutor instance."""
    return FileExecutor(
        name=manifest_test_tool["name"],
        file_content=file_content_add,
        file_manifest=manifest_test_tool
    )
@pytest.mark.parametrize(
        "parameters,expected",
            [
                ({"a": 5, "b": 8}, "13"),
                ({"a": -5, "b": 2}, "-3"),
                ({"a": 0, "b": 0}, "0")
            ],
                ids=[
                    "test_one",
                    "test_two",
                    "test_three"
                ]
    )
@pytest.mark.asyncio
async def test_execute_add(executor_instance_add, parameters, expected):
    result = await executor_instance_add.execute_file(parameters)
    # pytest -vs to print
    print (result)
    assert result["return value"] == expected


@pytest.fixture
def file_content_add_float():
    """
    Single tool code.

    """
    return (
"""
def test_tool(a: float, b: float) -> float:
    '''
    Adds two floating-point numbers and returns the result.

    Args:
        a (float): The first number to be added.
        b (float): The second number to be added.

    Returns:
        float: The result of adding a and b.
    '''
    return a + b
""")
@pytest.fixture
def executor_instance_add_float(manifest_test_tool, file_content_add_float):
    """Fixture to create a FileExecutor instance."""
    return FileExecutor(
        name=manifest_test_tool["name"],
        file_content=file_content_add_float,
        file_manifest=manifest_test_tool
    )
@pytest.mark.parametrize(
        "parameters,expected",
            [
                ({"a": 5, "b": 8}, "13.0"),
                ({"a": -5, "b": 2}, "-3.0"),
                ({"a": 0, "b": 0}, "0.0"),
                ({"a": 5.5, "b": 4.5}, "10.0")
            ],
                ids=[
                    "test_one",
                    "test_two",
                    "test_three",
                    "test_four"
                ]
    )
@pytest.mark.asyncio
async def test_execute_add_float(executor_instance_add_float, parameters, expected):
    result = await executor_instance_add_float.execute_file(parameters)
    # pytest -vs to print
    print (result)
    assert result["return value"] == expected


@pytest.fixture
def file_content_string():
    """
    Single tool code.

    """

    return (
"""
def test_tool(a: str, b: str = None) -> str:
    '''
    Returns a message depending on the argument passed.

    Args:
        a (str): The first string.
        b (str): The second string.

    Returns:
        str: message result.
    '''
    if b is not None:
        return "a and b passed"
    else:
        return "only a passed"
""")
@pytest.fixture
def executor_instance_string(manifest_test_tool, file_content_string):
    """Fixture to create a FileExecutor instance."""
    return FileExecutor(
        name=manifest_test_tool["name"],
        file_content=file_content_string,
        file_manifest=manifest_test_tool
    )
@pytest.mark.parametrize(
        "parameters,expected",
            [
                ({"a": "Hello", "b": "there"}, "a and b passed"),
                ({"a": "Hello"}, "only a passed")
            ],
                ids=[
                    "test_one",
                    "test_two"
                ]
    )
@pytest.mark.asyncio
async def test_execute_string(executor_instance_string, parameters, expected):
    result = await executor_instance_string.execute_file(parameters)
    # pytest -vs to print
    print (result)
    assert result["return value"] == f'"{expected}"'


@pytest.fixture
def file_content_GetQuarter():
    """
    Single tool code.

    """

    return (
"""
def test_tool(input_string: str) -> str:
    '''
    Returns the quarter of the year for a given string.
    
    Parameters:
        input_string (str): The input string containing the quarter information.
    
    Returns:
        str: The quarter of the year, e.g., 1Q, 2Q, 3Q, or 4Q.
    '''
    import re
    pattern = r'(\dQ)'
    match = re.search(pattern, input_string)
    if match:
        return match.group()
    else:
        return "Quarter not found"
""")
@pytest.fixture
def executor_instance_GetQuarter(manifest_test_tool, file_content_GetQuarter):
    """Fixture to create a FileExecutor instance."""
    return FileExecutor(
        name=manifest_test_tool["name"],
        file_content=file_content_GetQuarter,
        file_manifest=manifest_test_tool
    )
@pytest.mark.parametrize(
        "parameters,expected",
            [
                ({"input_string": "4Q 2020"}, "4Q"),
                ({"input_string": "2020"}, "Quarter not found")
            ],
                ids=[
                    "test_one",
                    "test_two"
                ]
    )
@pytest.mark.asyncio
async def test_execute_GetQuarter(executor_instance_GetQuarter, parameters, expected):
    result = await executor_instance_GetQuarter.execute_file(parameters)
    # pytest -vs to print
    print (result)
    assert result["return value"] == f'"{expected}"'


@pytest.fixture
def file_content_inner():
    """
    Single tool code.

    """

    return (
"""
def test_tool(a: int, b: int) -> int:
    '''
    Adds two floating-point numbers and returns the result.

    Args:
        a (int): The first number to be added.
        b (int): The second number to be added.

    Returns:
        int: The result of adding a and b.
    '''
    def inner_helper(a, b)
        return a + b
    return inner_helper(a, b)
""")
@pytest.fixture
def executor_instance_inner(manifest_test_tool, file_content_inner):
    """Fixture to create a FileExecutor instance."""
    return FileExecutor(
        name=manifest_test_tool["name"],
        file_content=file_content_inner,
        file_manifest=manifest_test_tool
    )
@pytest.mark.parametrize(
        "parameters,expected",
            [
                ({"a": 5, "b": 8}, "13")
            ],
                ids=[
                    "test_one"
                ]
    )
@pytest.mark.asyncio
async def test_execute_inner(executor_instance_inner, parameters, expected):
    result = await executor_instance_inner.execute_file(parameters)
    # pytest -vs to print
    print (result)
    assert result["return value"] == f'"{expected}"'

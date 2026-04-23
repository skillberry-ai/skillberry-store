import pytest
import os
from unittest.mock import patch

from skillberry_store.modules.file_executor import FileExecutor


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
    return """
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
"""


@pytest.fixture
def executor_instance_add(manifest_test_tool, file_content_add):
    """Fixture to create a FileExecutor instance."""
    return FileExecutor(
        name=manifest_test_tool["name"],
        file_content=file_content_add,
        file_manifest=manifest_test_tool,
    )


@pytest.mark.parametrize(
    "parameters,expected",
    [({"a": 5, "b": 8}, "13"), ({"a": -5, "b": 2}, "-3")],
    ids=["test_positive", "test_negative"],
)
@pytest.mark.asyncio
async def test_execute_add(executor_instance_add, parameters, expected):
    result = await executor_instance_add.execute_file(parameters)
    # pytest -vs to print
    print(result)
    assert result["return value"] == expected


@pytest.fixture
def file_content_add_float():
    """
    Single tool code.

    """
    return """
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
"""


@pytest.fixture
def executor_instance_add_float(manifest_test_tool, file_content_add_float):
    """Fixture to create a FileExecutor instance."""
    return FileExecutor(
        name=manifest_test_tool["name"],
        file_content=file_content_add_float,
        file_manifest=manifest_test_tool,
    )


@pytest.mark.parametrize(
    "parameters,expected",
    [
        ({"a": 5.5, "b": 4.5}, "10.0"),
        ({"a": -5, "b": 2}, "-3"),
    ],
    ids=["test_float", "test_negative"],
)
@pytest.mark.asyncio
async def test_execute_add_float(executor_instance_add_float, parameters, expected):
    result = await executor_instance_add_float.execute_file(parameters)
    # pytest -vs to print
    print(result)
    assert result["return value"] == expected


@pytest.fixture
def file_content_string():
    """
    Single tool code.

    """

    return """
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
"""


@pytest.fixture
def executor_instance_string(manifest_test_tool, file_content_string):
    """Fixture to create a FileExecutor instance."""
    return FileExecutor(
        name=manifest_test_tool["name"],
        file_content=file_content_string,
        file_manifest=manifest_test_tool,
    )


@pytest.mark.parametrize(
    "parameters,expected",
    [
        ({"a": "Hello", "b": "there"}, "a and b passed"),
        ({"a": "Hello"}, "only a passed"),
    ],
    ids=["test_one", "test_two"],
)
@pytest.mark.asyncio
async def test_execute_string(executor_instance_string, parameters, expected):
    result = await executor_instance_string.execute_file(parameters)
    # pytest -vs to print
    print(result)
    assert result["return value"] == expected


@pytest.fixture
def file_content_GetQuarter():
    """
    Single tool code.

    """

    return """
def test_tool(input_string: str) -> str:
    '''
    Returns the quarter of the year for a given string.
    
    Parameters:
        input_string (str): The input string containing the quarter information.
    
    Returns:
        str: The quarter of the year, e.g., 1Q, 2Q, 3Q, or 4Q.
    '''
    import re
    pattern = r'(\\dQ)'
    match = re.search(pattern, input_string)
    if match:
        return match.group()
    else:
        return "Quarter not found"
"""


@pytest.fixture
def executor_instance_GetQuarter(manifest_test_tool, file_content_GetQuarter):
    """Fixture to create a FileExecutor instance."""
    return FileExecutor(
        name=manifest_test_tool["name"],
        file_content=file_content_GetQuarter,
        file_manifest=manifest_test_tool,
    )


@pytest.mark.parametrize(
    "parameters,expected",
    [
        ({"input_string": "4Q 2020"}, "4Q"),
        ({"input_string": "2020"}, "Quarter not found"),
    ],
    ids=["test_one", "test_two"],
)
@pytest.mark.asyncio
async def test_execute_GetQuarter(executor_instance_GetQuarter, parameters, expected):
    result = await executor_instance_GetQuarter.execute_file(parameters)
    # pytest -vs to print
    print(result)
    assert result["return value"] == expected


@pytest.fixture
def file_content_inner():
    """
    Single tool code.

    """

    return """
def test_tool(a: int, b: int) -> int:
    '''
    Adds two numbers and returns the result.

    Args:
        a (int): The first number to be added.
        b (int): The second number to be added.

    Returns:
        int: The result of adding a and b.
    '''
    def inner_helper(a, b):
        return a + b
    return inner_helper(a, b)
"""


@pytest.fixture
def executor_instance_inner(manifest_test_tool, file_content_inner):
    """Fixture to create a FileExecutor instance."""
    return FileExecutor(
        name=manifest_test_tool["name"],
        file_content=file_content_inner,
        file_manifest=manifest_test_tool,
    )


@pytest.mark.parametrize(
    "parameters,expected", [({"a": 5, "b": 8}, "13")], ids=["test_one"]
)
@pytest.mark.asyncio
async def test_execute_inner(executor_instance_inner, parameters, expected):
    result = await executor_instance_inner.execute_file(parameters)
    # pytest -vs to print
    print(result)
    assert result["return value"] == expected


@pytest.fixture
def file_content_date_converter():
    """
    Single tool code.

    """
    return """
def test_tool(date_str: str) -> str:
    '''
    Converts a string representing a valid date to a string representing a date in ISO format.

    Args:
        date_str (str): The input date string.

    Returns:
        str: The date in ISO format.

    Raises:
        ValueError: If the input string is not a valid recognizable date.
    '''
    import dateutil
    try:
        date = dateutil.parser.parse(date_str)
        return date.strftime('%Y-%m-%d')
    except ValueError:
        raise ValueError("Invalid date string")
"""


@pytest.fixture
def executor_instance_date_converter(manifest_test_tool, file_content_date_converter):
    """Fixture to create a FileExecutor instance."""
    return FileExecutor(
        name=manifest_test_tool["name"],
        file_content=file_content_date_converter,
        file_manifest=manifest_test_tool,
    )


@pytest.mark.parametrize(
    "parameters,expected",
    [
        ({"date_str": "January 1, 2022"}, "2022-01-01"),
        ({"date_str": "5Feb2020"}, "2020-02-05"),
    ],
    ids=["test_text_date", "test_compact_date"],
)
@pytest.mark.asyncio
async def test_execute_date_converter(
    executor_instance_date_converter, parameters, expected
):
    result = await executor_instance_date_converter.execute_file(parameters)
    # pytest -vs to print
    print(result)
    assert result["return value"] == expected


@pytest.fixture
def file_content_date_converter_from():
    """
    Single tool code.

    """

    return """
def test_tool(date_str: str) -> str:
    '''
    Converts a string representing a valid date to a string representing a date in ISO format.

    Args:
        date_str (str): The input date string.

    Returns:
        str: The date in ISO format.

    Raises:
        ValueError: If the input string is not a valid recognizable date.
    '''
    from dateutil.parser import parse
    try:
        date = parse(date_str)
        return date.strftime('%Y-%m-%d')
    except ValueError:
        raise ValueError("Invalid date string")
"""


@pytest.fixture
def executor_instance_date_converter_from(
    manifest_test_tool, file_content_date_converter_from
):
    """Fixture to create a FileExecutor instance."""
    return FileExecutor(
        name=manifest_test_tool["name"],
        file_content=file_content_date_converter_from,
        file_manifest=manifest_test_tool,
    )


@pytest.fixture
def file_content_date_converter_from2():
    """
    Single tool code.

    """

    return """
def test_tool(date_str: str) -> str:
    '''
    Converts a string representing a valid date to a string representing a date in ISO format.

    Args:
        date_str (str): The input date string.

    Returns:
        str: The date in ISO format.

    Raises:
        ValueError: If the input string is not a valid recognizable date.
    '''
    from dateutil import parser
    try:
        date = parser.parse(date_str)
        return date.strftime('%Y-%m-%d')
    except ValueError:
        raise ValueError("Invalid date string")
"""


@pytest.fixture
def executor_instance_date_converter_from2(
    manifest_test_tool, file_content_date_converter_from2
):
    """Fixture to create a FileExecutor instance."""
    return FileExecutor(
        name=manifest_test_tool["name"],
        file_content=file_content_date_converter_from2,
        file_manifest=manifest_test_tool,
    )


@pytest.mark.parametrize(
    "parameters,expected",
    [
        ({"date_str": "January 1, 2022"}, "2022-01-01"),
        ({"date_str": "2022-01-01"}, "2022-01-01"),
        ({"date_str": "5Feb2020"}, "2020-02-05"),
    ],
    ids=["test_one", "test_two", "test_three"],
)
@pytest.mark.asyncio
async def test_execute_date_converter_from2(
    executor_instance_date_converter_from2, parameters, expected
):
    result = await executor_instance_date_converter_from2.execute_file(parameters)
    # pytest -vs to print
    print(result)
    assert result["return value"] == expected


@pytest.fixture
def file_content_multiple_imports():
    """
    Single tool code.

    """

    return """
def test_tool(date_str: str) -> str:
    '''
    Converts a string representing a valid date to a string representing a date in ISO format.

    Args:
        date_str (str): The input date string.

    Returns:
        str: The date in ISO format.

    Raises:
        ValueError: If the input string is not a valid recognizable date.
    '''
    import dateutil, json
    try:
        date = dateutil.parser.parse(date_str)
        # just ensure loads work
        json.loads('{"a": "1"}')
        return date.strftime('%Y-%m-%d')
    except ValueError:
        raise ValueError("Invalid date string")
"""


@pytest.fixture
def executor_instance_multiple_imports(
    manifest_test_tool, file_content_multiple_imports
):
    """Fixture to create a FileExecutor instance."""
    return FileExecutor(
        name=manifest_test_tool["name"],
        file_content=file_content_multiple_imports,
        file_manifest=manifest_test_tool,
    )


@pytest.mark.parametrize(
    "parameters,expected",
    [
        ({"date_str": "January 1, 2022"}, "2022-01-01"),
        ({"date_str": "2022-01-01"}, "2022-01-01"),
        ({"date_str": "5Feb2020"}, "2020-02-05"),
    ],
    ids=["test_one", "test_two", "test_three"],
)
@pytest.mark.asyncio
async def test_execute_multiple_imports(
    executor_instance_multiple_imports, parameters, expected
):
    result = await executor_instance_multiple_imports.execute_file(parameters)
    # pytest -vs to print
    print(result)
    assert result["return value"] == expected


@pytest.fixture
def file_content_transform_total():
    """
    Single tool code.

    """

    return """
def test_tool(total: str) -> float:
    '''
    This function transforms a string representing the final total amount including all charges into a float.
    It removes any non-numeric characters and converts the resulting string to a float.
    If the input string does not contain a decimal point, it appends '.00' to the end.

    Parameters:
        total (str): The final total amount including all charges as a string.

    Returns:
        float: The total amount as a float.
    '''
    # Remove any non-numeric characters except for the decimal point
    total = ''.join(char for char in total if char.isdigit() or char == '.')

    # If the total does not contain a decimal point, append '.00'
    if '.' not in total:
        total += '.00'

    # Convert the total to a float and return it
    return float(total)
"""


@pytest.fixture
def executor_instance_transform_total(manifest_test_tool, file_content_transform_total):
    """Fixture to create a FileExecutor instance."""
    return FileExecutor(
        name=manifest_test_tool["name"],
        file_content=file_content_transform_total,
        file_manifest=manifest_test_tool,
    )


@pytest.mark.parametrize(
    "parameters,expected",
    [({"total": "$34,690.64"}, "34690.64"), ({"total": "‚Ç¨4,898.58"}, "4898.58")],
    ids=["test_one", "test_two"],
)
@pytest.mark.asyncio
async def test_execute_transform_total(
    executor_instance_transform_total, parameters, expected
):
    result = await executor_instance_transform_total.execute_file(parameters)
    # pytest -vs to print
    print(result)
    assert result["return value"] == expected


@pytest.fixture
def file_content_nth_number_in_list():
    return """
def test_tool(numbers: list, n: int) -> int:
    '''Returns the nth number in a list.

    Parameters:
        numbers (list): A list of numbers.
        n (int): The position of the number to be returned.

    Returns:
        int: The nth number in the list.
    '''
    if n < 1 or n > len(numbers):
        raise ValueError("n is out of range")

    return numbers[n-1]
"""


@pytest.fixture
def executor_instance_nth_number(manifest_test_tool, file_content_nth_number_in_list):
    """Fixture to create a FileExecutor instance."""
    return FileExecutor(
        name=manifest_test_tool["name"],
        file_content=file_content_nth_number_in_list,
        file_manifest=manifest_test_tool,
    )


@pytest.mark.parametrize(
    "parameters,expected",
    [
        ({"numbers": [10, 20, 30], "n": 1}, "10"),
        ({"numbers": [10, 20, 30], "n": 2}, "20"),
        ({"numbers": [-1, 0, 1], "n": 3}, "1"),
    ],
    ids=["test_one", "test_two", "test_three"],
)
@pytest.mark.asyncio
async def test_execute_nth_number_in_list(
    executor_instance_nth_number, parameters, expected
):
    result = await executor_instance_nth_number.execute_file(parameters)
    # pytest -vs to print
    print(result)
    assert result["return value"] == expected


###################### Composite tests #############################################


@pytest.fixture
def manifest_test_tool_add_operation():
    """
    Minimal manifest for the file executor usage.

    """
    return {
        "programming_language": "python",
        "packaging_format": "code",
        "name": "test_tool_add_operation",
    }


@pytest.fixture
def manifest_test_tool_sub_operation():
    """
    Minimal manifest for the file executor usage.

    """
    return {
        "programming_language": "python",
        "packaging_format": "code",
        "name": "test_tool_sub_operation",
    }


@pytest.fixture
def manifest_test_tool_arithmetic_operation():
    """
    Minimal manifest for the file executor usage.

    """
    return {
        "programming_language": "python",
        "packaging_format": "code",
        "name": "test_tool_arithmetic_operation",
        "dependent_manifest_uids": [
            "test_tool_add_operation",
            "test_tool_sub_operation",
        ],
    }


@pytest.fixture
def file_content_add_operation():
    """
    Single tool code.

    """
    return """
def test_tool_add_operation(a: int, b: int) -> int:
    '''
    Adds two integer numbers and returns the result.

    Args:
        a (int): The first number to be added.
        b (int): The second number to be added.

    Returns:
        int: The result of adding a and b.
    '''
    return a + b
"""


@pytest.fixture
def file_content_sub_operation():
    """
    Single tool code.

    """
    return """
def test_tool_sub_operation(a: int, b: int) -> int:
    '''
    Subtract two integer numbers and returns the result.

    Args:
        a (int): The first number to subtract.
        b (int): The second number to subtract.

    Returns:
        int: The result of subtracting a and b.
    '''
    return a - b
"""


@pytest.fixture
def file_content_arithmetic_operation():
    return """
def test_tool_arithmetic_operation(operation: str, num1: float, num2: float) -> float:
    '''
    Perform a basic arithmetic operation on two numbers.

    Parameters:
        operation (str): The arithmetic operation to perform. Supported operations are '+', '-'.
        num1 (float): The first number.
        num2 (float): The second number.

    Returns:
        float: The result of the operation.
    '''
    if operation not in ['+', '-']:
        raise ValueError("Invalid operation. Supported operations are '+', '-'")

    if operation == '+':
        return test_tool_add_operation(num1, num2)
    elif operation == '-':
        return test_tool_sub_operation(num1, num2)
"""


@pytest.fixture
def executor_instance_arithmetic_operation(
    manifest_test_tool_arithmetic_operation,
    file_content_arithmetic_operation,
    file_content_add_operation,
    file_content_sub_operation,
    manifest_test_tool_add_operation,
    manifest_test_tool_sub_operation,
):
    """Fixture to create a FileExecutor instance."""
    return FileExecutor(
        name=manifest_test_tool_arithmetic_operation["name"],
        file_content=file_content_arithmetic_operation,
        file_manifest=manifest_test_tool_arithmetic_operation,
        dependent_file_contents=[
            file_content_add_operation,
            file_content_sub_operation,
        ],
        dependent_tools_as_dict=[
            manifest_test_tool_add_operation,
            manifest_test_tool_sub_operation,
        ],
    )


@pytest.mark.parametrize(
    "parameters,expected",
    [
        ({"operation": "+", "num1": 5, "num2": 8}, "13"),
        ({"operation": "-", "num1": -5, "num2": 2}, "-7"),
        ({"operation": "-", "num1": 0, "num2": 0}, "0"),
    ],
    ids=["test_one", "test_two", "test_three"],
)
@pytest.mark.asyncio
async def test_execute_arithmetic_operation(
    executor_instance_arithmetic_operation, parameters, expected
):
    result = await executor_instance_arithmetic_operation.execute_file(parameters)
    # pytest -vs to print
    print(result)
    assert result["return value"] == expected


@pytest.fixture
def manifest_square_root():
    """
    Minimal manifest for the file executor usage.

    """
    return {
        "programming_language": "python",
        "packaging_format": "code",
        "name": "square_root",
    }


@pytest.fixture
def manifest_random_number():
    """
    Minimal manifest for the file executor usage.

    """
    return {
        "programming_language": "python",
        "packaging_format": "code",
        "name": "random_number",
    }


@pytest.fixture
def manifest_calculate():
    """
    Minimal manifest for the file executor usage.

    """
    return {
        "programming_language": "python",
        "packaging_format": "code",
        "name": "calculate",
        "dependent_manifest_uids": ["square_root", "random_number"],
    }


@pytest.fixture
def file_content_square_root():
    return """
import math
def square_root(x: float) -> float:    
    '''
    Calculate the square root of a given number.

    Parameters:
        x (float): The number to calculate the square root of.

    Returns:
        float: The square root of the input number.
    '''
    return math.sqrt(x)
"""


@pytest.fixture
def file_content_random_number():
    return """
import random
def random_number(num: int) -> int:
    '''
    Generate a random 'integer' which is always num.

    Returns:
        int: A randomly generated integer.
    '''
    return random.randint(num, num)
"""


@pytest.fixture
def file_content_calculate():
    return """
def calculate(x: float):
    '''
    Process a number by calculating its square root and generating a random number.

    Args:
        x (float): The number to process.

    Returns:
        str: A formatted string containing the square root and a random number.
    '''
    root: float = square_root(x)
    rand: int = random_number(int(root))
    return f"Square root of {x} is {root:.2f}, and a random number is {rand}"
"""


@pytest.fixture
def executor_instance_calculate(
    manifest_calculate,
    file_content_calculate,
    file_content_square_root,
    file_content_random_number,
    manifest_square_root,
    manifest_random_number,
):
    """Fixture to create a FileExecutor instance."""
    return FileExecutor(
        name=manifest_calculate["name"],
        file_content=file_content_calculate,
        file_manifest=manifest_calculate,
        dependent_file_contents=[file_content_square_root, file_content_random_number],
        dependent_tools_as_dict=[
            manifest_square_root,
            manifest_random_number,
        ],
    )


@pytest.mark.parametrize(
    "parameters,expected",
    [({"x": 4}, "Square root of 4 is 2.00, and a random number is 2")],
    ids=["test_one"],
)
@pytest.mark.asyncio
async def test_execute_calculate(executor_instance_calculate, parameters, expected):
    result = await executor_instance_calculate.execute_file(parameters)
    # pytest -vs to print
    print(result)
    assert result["return value"] == expected


@pytest.fixture
def manifest_get_month_from_date():
    """
    Minimal manifest for the file executor usage.

    """
    return {
        "programming_language": "python",
        "packaging_format": "code",
        "name": "get_month_from_date",
    }


@pytest.fixture
def manifest_get_year_from_date():
    """
    Minimal manifest for the file executor usage.

    """
    return {
        "programming_language": "python",
        "packaging_format": "code",
        "name": "get_year_from_date",
    }


@pytest.fixture
def manifest_describe_date():
    """
    Minimal manifest for the file executor usage.

    """
    return {
        "programming_language": "python",
        "packaging_format": "code",
        "name": "describe_date",
        "dependent_manifest_uids": ["get_month_from_date", "get_year_from_date"],
    }


@pytest.fixture
def file_content_get_month_from_date():
    return """
from dateutil.parser import parse

def get_month_from_date(date_str: str) -> int:
    '''
    Extract the month from a given date string.

    Args:
        date_str (str): A string representing a date.

    Returns:
        int: The month extracted from the date (1–12).
    '''
    dt = parse(date_str)
    return dt.month
"""


@pytest.fixture
def file_content_get_year_from_date():
    return """
from dateutil.parser import parse
def get_year_from_date(date_str: str) -> int:
    '''
    Extract the year from a given date string.

    Args:
        date_str (str): A string representing a date.

    Returns:
        int: The year extracted from the date.
    '''
    dt = parse(date_str)
    return dt.year
"""


@pytest.fixture
def file_content_describe_date():
    return """
def describe_date(date_str: str, reference_date_str: str) -> str:
    '''
    Describe a date by extracting its month and comparing it to a reference date's year.

    Args:
        date_str (str): A string representing the date to describe.
        reference_date_str (str): A string representing the reference date.

    Returns:
        str: A description of the extracted month and reference year.
    '''
    month = get_month_from_date(date_str)
    reference_year = get_year_from_date(reference_date_str)
    return f"The date '{date_str}' is in month {month}. Reference year is {reference_year}."
"""


@pytest.fixture
def executor_instance_describe_date(
    manifest_describe_date,
    file_content_describe_date,
    file_content_get_month_from_date,
    file_content_get_year_from_date,
    manifest_get_month_from_date,
    manifest_get_year_from_date,
):
    """Fixture to create a FileExecutor instance."""
    return FileExecutor(
        name=manifest_describe_date["name"],
        file_content=file_content_describe_date,
        file_manifest=manifest_describe_date,
        dependent_file_contents=[
            file_content_get_month_from_date,
            file_content_get_year_from_date,
        ],
        dependent_tools_as_dict=[
            manifest_get_month_from_date,
            manifest_get_year_from_date,
        ],
    )


@pytest.mark.parametrize(
    "parameters,expected",
    [
        (
            {"date_str": "April 1st", "reference_date_str": "1-1-2035"},
            "The date 'April 1st' is in month 4. Reference year is 2035.",
        )
    ],
    ids=["test_one"],
)
@pytest.mark.asyncio
async def test_execute_describe_date(
    executor_instance_describe_date, parameters, expected
):
    result = await executor_instance_describe_date.execute_file(parameters)
    # pytest -vs to print
    print(result)
    assert result["return value"] == expected


@pytest.mark.parametrize(
    "execute_locally,params,expected",
    [
        (True, {"a": 5, "b": 8}, "13"),
        (False, {"a": 5, "b": 8}, "13"),
    ],
    ids=["local_mode", "docker_mode"],
)
@pytest.mark.asyncio
async def test_execute_modes(
    manifest_test_tool, file_content_add, execute_locally, params, expected
):
    executor = FileExecutor(
        name=manifest_test_tool["name"],
        file_content=file_content_add,
        file_manifest=manifest_test_tool,
        dependent_file_contents=[],
        dependent_tools_as_dict=[],
        execute_python_locally=execute_locally,
    )

    result = await executor.execute_file(params)
    assert result["return value"] == expected

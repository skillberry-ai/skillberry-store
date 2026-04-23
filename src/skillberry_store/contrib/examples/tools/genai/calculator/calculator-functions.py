import math


def add(a: float, b: float) -> float:
    """
    Adds two floating-point numbers and returns the result.

    Args:
        a (float): The first number to be added.
        b (float): The second number to be added.

    Returns:
        float: The result of adding a and b.
    """
    return a + b


def subtract(a: float, b: float) -> float:
    """
    Subtracts the second number from the first and returns the result.

    Args:
        a (float): The number from which to subtract.
        b (float): The number to subtract from a.

    Returns:
        float: The result of a - b.
    """
    return a - b


def multiply(a: float, b: float) -> float:
    """
    Multiplies two floating-point numbers and returns the result.

    Args:
        a (float): The first number.
        b (float): The second number.

    Returns:
        float: The result of multiplying a and b.
    """
    return a * b


def divide(a: float, b: float) -> float:
    """
    Divides the first number by the second and returns the result.

    Args:
        a (float): The numerator.
        b (float): The denominator.

    Returns:
        float: The result of a divided by b.

    Raises:
        ValueError: If b is zero, since division by zero is undefined.
    """
    if b == 0:
        raise ValueError("Division by zero")
    return a / b


def nth_root(a: float, b: float) -> float:
    """
    Calculates the b-th root of a and returns the result.

    Args:
        a (float): The number to find the root of.
        b (float): The degree of the root.

    Returns:
        float: The b-th root of a.

    Raises:
        ValueError: If b is zero, since the 0th root is undefined.
    """
    if b == 0:
        raise ValueError("Cannot take the 0th root")
    return math.pow(a, 1 / b)


def power(a: float, b: float) -> float:
    """
    Raises a to the power of b and returns the result.

    Args:
        a (float): The base number.
        b (float): The exponent.

    Returns:
        float: The result of a raised to the power of b.
    """
    return math.pow(a, b)


def modulo(a: float, b: float) -> float:
    """
    Calculates the remainder of a divided by b and returns it.

    Args:
        a (float): The dividend.
        b (float): The divisor.

    Returns:
        float: The remainder when a is divided by b.

    Raises:
        ValueError: If b is zero, since modulo by zero is undefined.
    """
    if b == 0:
        raise ValueError("Modulo by zero")
    return math.fmod(a, b)

import operator

def multiply(a: float, b: float) -> float:
    '''
    Multiplies two numbers using the operator module and returns the result.

    Args:
        a (float): The first number to subtract.
        b (float): The second number to subtract.

    Returns:
        float: The result of multiplying a with b.
    '''
    return add(a, operator.mul(a, subtract(b, 1)))  # a * b = a + a * (b - 1)

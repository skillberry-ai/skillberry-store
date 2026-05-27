import operator

def subtract(a: float, b: float) -> float:
    '''
    Subtracts two numbers using the operator module and returns the result.

    Args:
        a (float): The first number to subtract.
        b (float): The second number to subtract.

    Returns:
        float: The result of subtracting b from a.
    '''
    return operator.sub(a, b)

import operator

def subtract(a: int, b: int) -> int:
    '''
    Subtracts two integer numbers using the operator module and returns the result.

    Args:
        a (int): The first number to subtract.
        b (int): The second number to subtract.

    Returns:
        int: The result of subtracting b from a.
    '''
    return operator.sub(a, b)

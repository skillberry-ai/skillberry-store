import operator

def add(a: int, b: int) -> int:
    '''
    Adds two integer numbers using the operator module and returns the result.

    Args:
        a (int): The first number to be added.
        b (int): The second number to be added.

    Returns:
        int: The result of adding a and b.
    '''
    return operator.add(a, b)

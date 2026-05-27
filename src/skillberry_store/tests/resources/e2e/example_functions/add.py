import operator

def add(a: float, b: float) -> float:
    '''
    Adds two numbers using the operator module and returns the result.

    Args:
        a (float): The first number to be added.
        b (float): The second number to be added.

    Returns:
        float: The result of adding a and b.
    '''
    return operator.add(a, b)

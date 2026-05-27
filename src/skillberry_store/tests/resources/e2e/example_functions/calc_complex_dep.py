import numpy as np

def calc(operation: str, num1: float, num2: float) -> float:
    '''
    Perform a basic arithmetic operation on two numbers.
    Delegates multiplication, addition and subtraction.

    Parameters:
        operation (str): The arithmetic operation to perform. Supported operations are '+', '-', '*'.
        num1 (float): The first number.
        num2 (float): The second number.

    Returns:
        float: The result of the operation.
    '''
    if operation == '*':
        return multiply(num1, num2)
    elif operation in ('+', '-'):
        return calc_add_subtract(operation, num1, num2)
    else:
        raise ValueError(f"Unsupported operation: {operation}")

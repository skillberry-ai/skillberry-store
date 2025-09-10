def calc_add_subtract(operation: str, num1: float, num2: float) -> float:
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
        return add(num1, num2)
    elif operation == '-':
        return subtract(num1, num2)

def GetQuarter(input_string):
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
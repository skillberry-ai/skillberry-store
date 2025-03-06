import re


def GetQuarter(input_string):
    '''
    Returns the quarter of the year for a given string. For example: for the string 'Deal closed: 2Q 2024' the function will return 2Q.
    
    Parameters:
    input_string (str): The input string containing the quarter information.
    
    Returns:
    str: The quarter of the year, e.g., 1Q, 2Q, 3Q, or 4Q.
    '''
    # Split the string into parts based on spaces
    pattern = r'(\dQ)'
    match = re.search(pattern, input_string)
    if match:
        return match.group()
    else:
        return "Quarter not found"


def GetYear(date_string):
    '''
    Returns the year for a given string. For example: for the string 'Deal closed: 2Q 2024' the function will return 2024.
    
    Parameters:
    date_string (str): The input string containing the year.
    
    Returns:
    str: The year extracted from the input string.
    '''
    import re
    year = re.search(r'\b\d{4}\b', date_string)
    if year:
        return year.group()
    else:
        return ''


def GetCurrencySymbol(deal_string):
    """
    Extracts the currency symbol from a given string.

    Args:
        deal_string (str): The input string containing the deal size.

    Returns:
        str: The extracted currency symbol.
    """
    # Use a regular expression to find the pattern of one or more alphabets followed by a currency symbol
    match = re.search(r"[A-Za-z]*[$€£¥₹]", deal_string)

    # If a match is found, return the matched group
    if match:
        return match.group()
    else:
        return None


def ParseDealSize(deal_size_str):
    """
    Parses the deal size string and returns the deal size as a float.

    Args:
        deal_size_str (str): The input string containing the deal size.

    Returns:
        str: The deal size as a float, followed by a comma.
    """
    # Remove the "Deal size: " part from the string
    deal_size_str = deal_size_str.replace("Deal size: ", "")

    # Use a regular expression to extract the deal size and unit suffix
    match = re.search(r"([0-9\.]+)([A-Z])?", deal_size_str)

    # If a match is found, extract the deal size and unit suffix
    if match:
        deal_size = float(match.group(1))
        unit_suffix = match.group(2)

        # Initialize a dictionary to map the unit suffix to its corresponding multiplier
        units = {"M": 10**6, "B": 10**9, "K": 10**3, "T": 10**12}

        # If a unit suffix is found, multiply the deal size by its corresponding multiplier
        if unit_suffix:
            deal_size *= units[unit_suffix]

        # Return the deal size as a string, followed by a comma
        return "{:.1f},".format(deal_size)
    else:
        return None


def GetTime():
    """
    Returns the current time.
    
    Returns:
    str: The current time in the format 'HH:MM:SS'.
    """
    from datetime import datetime
    current_time = datetime.now().strftime('%H:%M:%S')
    return current_time


def add_two_numbers(a: float, b: float) -> float:
    """
    Adds two numbers and returns the result.

    Parameters:
        a (float): The first number to add.
        b (float): The second number to add.

    Returns:
        float: The sum of the two input numbers.
    """
    return a + b

import re


def GetQuarter(input_string):
    """
    Extracts the deal quarter from a given string.

    Args:
        input_string (str): The input string containing the deal quarter.

    Returns:
        str: The extracted deal quarter.
    """
    # Split the string into parts based on spaces
    parts = input_string.split()

    # Iterate over each part
    for part in parts:
        # Check if the part contains 'Q' (assuming it's the quarter)
        if "Q" in part:
            # Return the part as the deal quarter
            return part


def GetYear(date_string):
    """
    Extracts the deal year from a given string.

    Args:
        date_string (str): The input string containing the deal year.

    Returns:
        str: The extracted deal year.
    """
    # Split the string into parts based on spaces
    parts = date_string.split()

    # Iterate over each part
    for part in parts:
        # Check if the part is numeric and has a length of 4 (assuming it's the year)
        if part.isdigit() and len(part) == 4:
            # Return the part as the deal year
            return part


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

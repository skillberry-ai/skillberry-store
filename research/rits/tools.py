from langchain_core.tools import tool

@tool
def count_chars(string: str, char: str) -> int:
    """
    Counts how many times a specific character appears in a string.

    Parameters:
        string (str): The string to search in.
        char (str): The character to count.

    Returns:
        int: The number of occurrences of the character in the string.
    """
    if len(char) != 1:
        raise ValueError("The 'char' parameter must be a single character.")

    return string.count(char)

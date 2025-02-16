def GetYear(date_string):
    '''
    Returns the year for a given string.
    
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
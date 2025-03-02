def GetTime():
    """
    Returns the current time.
    
    Returns:
    str: The current time in the format 'HH:MM:SS'.
    """
    from datetime import datetime
    current_time = datetime.now().strftime('%H:%M:%S')
    return current_time
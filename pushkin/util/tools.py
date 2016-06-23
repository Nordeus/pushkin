
def is_integer(value):
    """
    Checks if a value is of integer type

    :param value:
    :return: True if value is integer, False otherwise
    """
    try:
        int(value)
        return True
    except ValueError:
        return False
def is_password_error(error):
    """Check if a 7zz error is password-related.

    Args:
        error: An exception or string containing the error message.

    Returns:
        True if the error indicates a missing or wrong password.
    """
    error_str = str(error)
    return (
        'Wrong password' in error_str
        or 'Data Error in encrypted file' in error_str
        or 'Enter password' in error_str
        or 'Break signaled' in error_str
    )

def nth_prime(n):
    """
    Returns the n-th prime number.

    Parameters:
    n (int): The position of the prime number to return (1-based index).

    Returns:
    int: The n-th prime number.

    Raises:
    ValueError: If n is less than 1.
    """
    if n < 1:
        raise ValueError("Input must be a positive integer greater than or equal to 1.")

    def is_prime(num):
        """Checks if a number is prime."""
        if num < 2:
            return False
        for i in range(2, int(num ** 0.5) + 1):
            if num % i == 0:
                return False
        return True

    prime_count = 0
    candidate = 1

    while prime_count < n:
        candidate += 1
        if is_prime(candidate):
            prime_count += 1

    return candidate

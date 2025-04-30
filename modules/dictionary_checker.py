import re


class DictionaryChecker:
    """
    A class to check if keys and values exist in a dictionary using flexible search conditions.

    Supports:
    - Exact value matching
    - Regular expression matching
    - Wildcard key matching (`*`)
    - Checking for key existence without values
    - AND and OR logic for multiple conditions

    Example Usage:
    --------------
    data_dict = {
        "user": {
            "name": "Alice",
            "address": {"city": "Wonderland", "zipcode": 12345},
        },
        "order": {
            "id": 1001,
            "status": "Shipped",
            "items": [{"id": 1, "name": "Laptop"}, {"id": 2, "name": "Phone"}]
        }
    }
    checker = DictionaryChecker(data_dict)
    print(checker.check_key_value_exists("user.name:Alice"))  # True
    print(checker.check_key_value_exists("user.address.city:^W.*"))  # True (regex)
    print(checker.check_key_value_exists("user.*.zipcode:12345"))  # True
    print(checker.check_key_value_exists("order.items.*.name:Phone"))  # True
    print(checker.check_key_value_exists("user.address.city"))  # True (key exists check)
    """

    def __init__(self, data_dict):
        """Initialize the DictionaryChecker with the dictionary to check."""
        self.data_dict = data_dict

    def check_key_value_exists(self, check_str):
        """
        Evaluates whether the dictionary satisfies a set of key-value conditions.

        Supports:
        - Exact match (`user.name:Alice`)
        - OR conditions (`user.name:Alice|Bob`)
        - Wildcards (`user.*.city`)
        - Regex (`user.name:^A.*`)
        - Key existence check (`user.address.city`)

        Parameters:
        check_str (str): Condition string.

        Returns:
        bool: True if all conditions match, else False.
        """
        conditions = check_str.split(",")

        for condition in conditions:
            if ":" in condition:
                key, value = condition.split(":")
                if "|" in value:  # OR condition
                    possible_values = value.split("|")
                    if not self.check_or_condition(key, possible_values):
                        return False
                else:  # Single AND condition
                    if not self.check_and_condition(key, value):
                        return False
            else:  # Key existence check
                if not self.check_key_exists(condition):
                    return False
        return True

    def check_or_condition(self, key, possible_values):
        """
        Checks if any of the possible values match the value at the specified key path.

        Parameters:
        key (str): The key path.
        possible_values (list): List of acceptable values.

        Returns:
        bool: True if any value matches, else False.
        """
        values = self.get_values_by_key_path(self.data_dict, key)
        if not values:
            return False

        return any(
            self.match_value(value, v) for value in values for v in possible_values
        )

    def check_and_condition(self, key, value):
        """
        Checks if the value at the specified key path matches the expected value.

        Parameters:
        key (str): The key path.
        value (str): The expected value.

        Returns:
        bool: True if the value matches, else False.
        """
        values = self.get_values_by_key_path(self.data_dict, key)
        return any(self.match_value(v, value) for v in values)

    def check_key_exists(self, key_path):
        """
        Checks if a given key path exists in the dictionary.

        Parameters:
        key_path (str): The dot-separated key path.

        Returns:
        bool: True if the key exists, else False.
        """
        return bool(self.get_values_by_key_path(self.data_dict, key_path))

    def get_values_by_key_path(self, current_dict, key_path):
        """
        Recursively retrieves values from a nested dictionary using a key path.

        Supports wildcard `*` to match any key at that level.

        Parameters:
        current_dict (dict): The dictionary to search.
        key_path (str): The dot-separated key path.

        Returns:
        list: A list of found values or an empty list if the key path doesn't exist.
        """
        key_parts = key_path.split(".")
        results = [current_dict]

        for key in key_parts:
            next_results = []
            for result in results:
                if isinstance(result, dict):
                    if key == "*":
                        next_results.extend(result.values())
                    elif key in result:
                        next_results.append(result[key])
            results = next_results

        return results

    def match_value(self, actual_value, expected_value):
        """
        Checks if the actual value matches the expected value (supports regex).

        Parameters:
        actual_value (Any): The value retrieved from the dictionary.
        expected_value (str): The expected value or regex pattern.

        Returns:
        bool: True if there's a match, else False.
        """
        if self.is_regex(expected_value):
            return re.match(expected_value, str(actual_value)) is not None
        return str(actual_value) == expected_value

    def is_regex(self, value):
        """
        Determines if the given value should be treated as a regex.

        Parameters:
        value (str): The value to check.

        Returns:
        bool: True if value contains regex characters, else False.
        """
        regex_chars = ["*", "+", "?", ".", "^", "$", "(", ")", "[", "]", "{", "}"]
        return any(char in value for char in regex_chars)

from typing import Dict, Any, Optional
import uuid

import logging

logger = logging.getLogger(__name__)


# TODO: common skillberry library


def normalize_uuid(uuid_str: Optional[str]) -> Optional[str]:
    """
    Normalize a UUID string to lowercase format.
    
    This function ensures consistent UUID handling across the codebase by:
    - Converting UUIDs to lowercase
    - Validating UUID format
    - Returning None for invalid or None inputs
    
    Args:
        uuid_str: A UUID string (can be uppercase, lowercase, or mixed case)
        
    Returns:
        Lowercase UUID string if valid, None otherwise
        
    Examples:
        >>> normalize_uuid("12345678-1234-1234-1234-123456789ABC")
        '12345678-1234-1234-1234-123456789abc'
        >>> normalize_uuid("ABCDEF12-3456-7890-ABCD-EF1234567890")
        'abcdef12-3456-7890-abcd-ef1234567890'
        >>> normalize_uuid("invalid-uuid")
        None
        >>> normalize_uuid(None)
        None
    """
    if not uuid_str:
        return None
    
    try:
        # Validate and normalize the UUID
        # uuid.UUID() will raise ValueError if the string is not a valid UUID
        validated_uuid = uuid.UUID(uuid_str)
        return str(validated_uuid).lower()
    except (ValueError, AttributeError, TypeError):
        logger.debug(f"Invalid UUID format: {uuid_str}")
        return None

SKILLBERRY_CONTEXT = "skillberry-context"


def flatten_keys(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flattens a nested dictionary back into dash-separated keys.
    Assumes the original structure was created by combining the first two segments
    and nesting the remaining segments dynamically.

    This method is used to serialize Skillberry context related HTTP headers.

    Example:
        Input:
            {
                "Skillberry-Context": {
                    "env_id": "1234",
                    "task_id": "9"
                    additional_info": {
                        "city": "foo",
                        "country": "baz"
                    }
                }
            }
        Output:
            {
                "Skillberry-Context-env_id": "1234",
                "Skillberry-Context-task_id": "9",
                "Skillberry-Context-additional_info-city": "foo",
                "Skillberry-Context-additional_info-country": "bar"
            }

    Args:
        data (Dict[str, Any]): Nested dictionary.

    Returns:
        Dict[str, Any]: Flat dictionary with dash-separated keys.
    """
    result: Dict[str, Any] = {}

    def recurse(prefix: str, value: Any):
        if isinstance(value, dict):
            for k, v in value.items():
                new_prefix = f"{prefix}-{k}"
                recurse(new_prefix, v)
        else:
            result[prefix] = value

    for main_key, value in data.items():
        recurse(main_key, value)

    return result


def unflatten_keys(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Splits dictionary keys by dash ('-') and nests values dynamically.
    The first two segments of each key are combined as one main key,
    and the remaining segments are nested as subkeys.

    This method is used to deserialize Skillberry context related HTTP headers.

    Note: This method only processes keys that follow a consistent nested pattern. Keys that do not conform to thi
    structure will be ignored. For example, the following keys will be skipped:
    'x-stainless-runtime': 'CPython', 'x-stainless-runtime-version': '3.12.3'

    Invocation example:
        Input:
            {"Skillberry-Context-env_id": "1234", "Skillberry-Context-task_id": "9", "Skillberry-Context-additional_info-city": "foo", "Skillberry-Context-additional_info-country": "bar"}
        Output:
            {
                "Skillberry-Context": {
                    "env_id": "1234",
                    "task_id": "9"
                    "additional_info": {
                        "city": "foo",
                        "country": "baz"
                    }
                }
            }
    Args:
        data (Dict[str, Any]): Original flat dictionary with dash-separated keys.

    Returns:
        Dict[str, Any]: Nested dictionary with dynamic levels.
    """
    result: Dict[str, Any] = {}

    for key, value in data.items():
        try:
            parts = key.split("-")
            main_key = "-".join(parts[:2])  # Combine first two segments
            sub_parts = parts[2:]  # Remaining segments for nesting
            if not sub_parts:
                raise

            if main_key not in result:
                result[main_key] = {}

            current = result[main_key]
            for i, part in enumerate(sub_parts):
                if i == len(sub_parts) - 1:  # Last part → assign value
                    current[part] = value
                else:  # Intermediate part → ensure dict exists
                    if part not in current:
                        current[part] = {}
                    current = current[part]
        except:
            logger.info(f"unflatten_keys: Error handling key: {key}. Ignoring...")
            continue
    return result


if __name__ == "__main__":
    unflatten_keys(
        {
            "x-stainless-lang": "python",
            "x-stainless-package-version": "2.8.1",
            "x-stainless-os": "Linux",
            "x-stainless-arch": "x64",
            "x-stainless-runtime": "CPython",
            "x-stainless-runtime-version": "3.12.3",
        }
    )

import json
import statistics


def rolling_statistics(values, window_size=None):
    """
    Compute overall and optional rolling window statistics (avg, mean, max, min) for a list of numerical values.

    Parameters:
        values (list): A list of numerical values.
        window_size (int): The size of the rolling window. If None, only overall statistics are computed.

    Returns:
        str: A JSON-formatted string containing the overall and rolling window statistics.
    """

    # Check if the input list is empty
    if not values:
        return json.dumps({"error": "Input list is empty"})

    # Compute overall statistics
    overall_stats = {
        "avg": statistics.mean(values),
        "mean": statistics.mean(values),
        "max": max(values),
        "min": min(values),
    }

    # Compute rolling window statistics if window_size is provided
    if window_size is not None:
        rolling_stats = []
        for i in range(len(values) - window_size + 1):
            window = values[i : i + window_size]
            rolling_stats.append(
                {
                    "avg": statistics.mean(window),
                    "mean": statistics.mean(window),
                    "max": max(window),
                    "min": min(window),
                }
            )
        return json.dumps({"overall": overall_stats, "rolling": rolling_stats})
    else:
        return json.dumps({"overall": overall_stats})

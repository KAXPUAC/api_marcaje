from typing import Any


def force_strings(data: Any) -> Any:
    if isinstance(data, (int, float)):
        return str(data)
    elif isinstance(data, bool):
        return str(data).lower()
    elif isinstance(data, dict):
        return {key: force_strings(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [force_strings(item) for item in data]
    else:
        return data

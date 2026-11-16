def _value(result: dict, name: str, default=None):
    if not isinstance(result, dict):
        return default
    for key, value in result.items():
        if str(key).upper() == name:
            return value
    return default


def normalize_marking_response(result) -> dict:
    """Garantiza la misma respuesta para ambos procedimientos de marcaje."""
    return {
        "RETORNO_FUNCION": _value(result, "RETORNO_FUNCION", result if isinstance(result, str) else None),
        "PMENSAJE": _value(result, "PMENSAJE"),
        "PSQLCODE": _value(result, "PSQLCODE"),
    }

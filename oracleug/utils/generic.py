def to_bool(value: str) -> bool:
    return value.lower() in ('yes', 'true', 't', 'y', '1', 'on', 'True')

def to_int(value: str) -> int:
    return int(value)
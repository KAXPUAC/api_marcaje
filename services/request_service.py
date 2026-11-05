from fastapi import Request


def get_client_ip(request: Request) -> str:
    """Obtiene la IP del cliente para la petición actual.

    Cuando la API está detrás de un proxy, se utiliza la primera IP de
    X-Forwarded-For. En caso contrario se usa la IP del socket.
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    return request.client.host if request.client else "0.0.0.0"

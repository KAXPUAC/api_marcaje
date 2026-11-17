import ipaddress
import os

from fastapi import Request


def _is_trusted_proxy(host: str | None) -> bool:
    if not host:
        return False
    trusted_proxies = os.getenv("TRUSTED_PROXY_IPS", "")
    if not trusted_proxies.strip():
        return False
    try:
        client_ip = ipaddress.ip_address(host)
        return any(
            client_ip in ipaddress.ip_network(item.strip(), strict=False)
            for item in trusted_proxies.split(",")
            if item.strip()
        )
    except ValueError:
        return False


def get_client_ip(request: Request) -> str:
    """Obtiene la IP del cliente para la petición actual.

    Cuando la API está detrás de un proxy, se utiliza la primera IP de
    X-Forwarded-For. En caso contrario se usa la IP del socket.
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    proxy_host = request.client.host if request.client else None
    if forwarded_for and _is_trusted_proxy(proxy_host):
        return forwarded_for.split(",")[0].strip()

    return proxy_host or "0.0.0.0"

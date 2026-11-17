import hashlib
import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen

from oracleug.models.pkg_ci import PkgCi
from oracleug.scripts.empleados import Empleados
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from oracleug.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    decode_refresh_token,
)
import logging
import time
from typing import Optional
from oracleug.oracle_settings import OracleSettings
from jose import jwt

logger = logging.getLogger(__name__)

__pkg_ci = PkgCi()
__empleados = Empleados()
__oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
__settings = OracleSettings()

# Registro local de refresh tokens. Para varios workers/instancias debe migrarse
# a Redis o a una tabla de base de datos compartida.
__active_refresh_tokens: dict[str, int] = {}


def _cleanup_refresh_tokens() -> None:
    now = int(time.time())
    expired = [jti for jti, exp in __active_refresh_tokens.items() if exp <= now]
    for jti in expired:
        del __active_refresh_tokens[jti]


def _register_refresh_token(token: str, payload: Optional[dict] = None) -> None:
    payload = payload or decode_refresh_token(token)
    if payload and payload.get("jti") and payload.get("exp"):
        _cleanup_refresh_tokens()
        __active_refresh_tokens[payload["jti"]] = int(payload["exp"])


def _is_active_refresh_token(payload: dict) -> bool:
    _cleanup_refresh_tokens()
    jti = payload.get("jti")
    return bool(jti and __active_refresh_tokens.get(jti) == int(payload.get("exp", 0)))


def _revoke_refresh_token(payload: dict) -> None:
    jti = payload.get("jti")
    if jti:
        __active_refresh_tokens.pop(jti, None)


def _get_value(data: dict, *names: str, default=None):
    """Obtiene un campo independientemente de las mayúsculas de Oracle."""
    if not isinstance(data, dict):
        return default
    for name in names:
        if name in data:
            return data[name]
    normalized = {str(key).upper(): value for key, value in data.items()}
    for name in names:
        if name.upper() in normalized:
            return normalized[name.upper()]
    return default


def _get_first_user(result):
    """Normaliza una fila devuelta por Oracle como dict o lista de dicts."""
    if isinstance(result, dict):
        return result
    if isinstance(result, list) and result:
        return result[0] if isinstance(result[0], dict) else None
    return None


def _token_response(access_token: str, refresh_token: str, user: dict, auth_method: str):
    username = str(_get_value(user, "USUARIO", "username", default=""))
    email = _get_value(user, "EMAIL", "GMAIL", "email")
    correlativo = _get_value(user, "CORRELATIVO", "correlativo")
    coddepa = _get_value(user, "CODDEPA", "coddepa")
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": __settings.get_access_token_expire_minutes() * 60,
        "refresh_expires_in": __settings.get_refresh_token_expire_days() * 24 * 60 * 60,
        "token_type": "bearer",
        "username": username,
        "email": email,
        "correlativo": str(correlativo) if correlativo is not None else None,
        "coddepa": str(coddepa) if coddepa is not None else None,
        "auth_method": auth_method,
        "datos_usuario": user,
    }


def _create_auth_tokens(user: dict, auth_method: str):
    username = str(_get_value(user, "USUARIO", "username", default=""))
    email = _get_value(user, "EMAIL", "GMAIL", "email")
    correlativo = _get_value(user, "CORRELATIVO", "correlativo")
    coddepa = _get_value(user, "CODDEPA", "coddepa")
    departamento = _get_value(user, "DEPARTAMENTO", "departamento")
    user_data = {
        "username": username,
        "email": email,
        "correlativo": correlativo,
        "coddepa": coddepa,
        "departamento": departamento,
        "auth_method": auth_method,
    }
    access_token = create_access_token(data=user_data)
    refresh_token = create_refresh_token(data=user_data)
    _register_refresh_token(refresh_token)
    return _token_response(access_token, refresh_token, user, auth_method)


def login_api(username: str, password: str, ip: str = "0.0.0.0"):
    """
    Método para autenticar a un usuario en el sistema.
    :param username: Nombre de usuario.
    :param password: Contraseña del usuario.
    :param ip: IP del cliente que solicita la autenticación.
    :return: Diccionario con información del usuario si la autenticación es exitosa, None en caso contrario.
    """
    logger.info("Solicitud de autenticación para %s desde %s", username, ip)

    try:
        users = __empleados.get_usuario_por_usuario(usuario=username)
    except Exception:
        logger.exception("Error consultando el usuario %s", username)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error consultando la información del usuario",
        )

    user = _get_first_user(users)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado",
        )

    usuario_db = str(_get_value(user, "USUARIO", "username", default=username)).upper()
    contrasena = hashlib.sha512(str(password).encode("UTF-8")).hexdigest().upper()

    try:
        user_info = __pkg_ci.autenticar_administrativo(
            usuario=usuario_db,
            contrasena=contrasena,
        )
    except Exception:
        logger.exception("Error autenticando al usuario %s", usuario_db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error durante la autenticación",
        )

    retorno = _get_value(user_info or {}, "RETORNO_FUNCION", "retorno_funcion")
    if retorno != 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return _create_auth_tokens(user, "password")


def refresh_access_token(refresh_token: str, ip: str = "0.0.0.0"):
    """Genera un nuevo par de tokens a partir de un refresh token válido."""
    payload = decode_refresh_token(refresh_token)
    if payload is None or not payload.get("username") or not _is_active_refresh_token(payload):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload["username"]
    user = __empleados.get_usuario_por_usuario(usuario=username)
    user = _get_first_user(user)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario no encontrado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    logger.info("Renovación de token para %s desde %s", username, ip)
    _revoke_refresh_token(payload)
    response = _create_auth_tokens(user, payload.get("auth_method", "password"))
    return response


def facial_login(correlativo: str, ip: str = "0.0.0.0", auth_method: str = "facial"):
    """Genera tokens usando el usuario asociado al correlativo reconocido."""
    users = __empleados.get_usuario_por_correlativo(correlativo=int(correlativo))
    user = _get_first_user(users)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El rostro fue reconocido, pero no tiene un usuario activo asociado",
        )
    logger.info("Autenticación facial para correlativo %s desde %s", correlativo, ip)
    return _create_auth_tokens(user, auth_method)


def _fetch_json(url: str, params: dict[str, str] | None = None) -> dict:
    if params:
        url = f"{url}?{urlencode(params)}"
    try:
        with urlopen(UrlRequest(url, headers={"Accept": "application/json"}), timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="El token del proveedor no es válido",
        ) from exc


def _verify_google_token(id_token: str) -> str:
    claims = _fetch_json(
        "https://oauth2.googleapis.com/tokeninfo",
        {"id_token": id_token},
    )
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    if not client_id:
        raise HTTPException(status_code=500, detail="GOOGLE_CLIENT_ID no está configurado")
    if claims.get("aud") != client_id:
        raise HTTPException(status_code=401, detail="El token de Google no pertenece a esta aplicación")
    if claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise HTTPException(status_code=401, detail="Emisor de Google no válido")
    if str(claims.get("email_verified", "")).lower() != "true":
        raise HTTPException(status_code=401, detail="El correo de Google no está verificado")
    email = claims.get("email", "").strip()
    if not email:
        raise HTTPException(status_code=401, detail="Google no proporcionó un correo")
    return email


def _verify_microsoft_token(id_token: str) -> str:
    try:
        unverified = jwt.get_unverified_claims(id_token)
        header = jwt.get_unverified_header(id_token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="El token de Microsoft no es válido") from exc

    tenant_id = str(unverified.get("tid", "")).strip()
    configured_tenant = os.getenv("MICROSOFT_TENANT_ID", "").strip()
    if not tenant_id or (configured_tenant and configured_tenant not in {"common", tenant_id}):
        raise HTTPException(status_code=401, detail="El tenant de Microsoft no está autorizado")

    client_id = os.getenv("MICROSOFT_CLIENT_ID", "").strip()
    if not client_id:
        raise HTTPException(status_code=500, detail="MICROSOFT_CLIENT_ID no está configurado")

    keys = _fetch_json(
        f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
    ).get("keys", [])
    key_data = next((key for key in keys if key.get("kid") == header.get("kid")), None)
    if not key_data:
        raise HTTPException(status_code=401, detail="No se encontró la clave de Microsoft")
    try:
        issuer = f"https://login.microsoftonline.com/{tenant_id}/v2.0"
        jwt.decode(id_token, key_data, algorithms=["RS256"], audience=client_id, issuer=issuer)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="El token de Microsoft no es válido") from exc

    email = (unverified.get("email") or unverified.get("preferred_username") or "").strip()
    if not email:
        raise HTTPException(status_code=401, detail="Microsoft no proporcionó un correo")
    return email


def social_login(provider: str, id_token: str, ip: str = "0.0.0.0"):
    provider = provider.lower().strip()
    if provider == "google":
        email = _verify_google_token(id_token)
    elif provider == "microsoft":
        email = _verify_microsoft_token(id_token)
    else:
        raise HTTPException(status_code=400, detail="Proveedor no soportado")

    user = _get_first_user(__empleados.get_usuario_por_email(email))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El correo autenticado no está registrado o no tiene acceso",
        )
    logger.info("Autenticación %s para %s desde %s", provider, email, ip)
    return _create_auth_tokens(user, provider)


def logout(refresh_token: str) -> None:
    """Revoca un refresh token sin revelar si era válido o no."""
    payload = decode_refresh_token(refresh_token)
    if payload:
        _revoke_refresh_token(payload)


def get_current_user(token: str = Depends(__oauth2_scheme)) -> dict:
    """
    Obtiene el usuario actual a partir del token de acceso.
    :param token:
    :return:
    """
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload

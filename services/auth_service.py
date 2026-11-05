import hashlib

from oracleug.models.pkg_ci import PkgCi
from oracleug.scripts.usuarios import Usuarios
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

logger = logging.getLogger(__name__)

__pkg_ci = PkgCi()
__usuarios = Usuarios()
__oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
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


def _token_response(access_token: str, refresh_token: str, username: str, email: str):
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": __settings.get_access_token_expire_minutes() * 60,
        "refresh_expires_in": __settings.get_refresh_token_expire_days() * 24 * 60 * 60,
        "token_type": "bearer",
        "username": username,
        "email": email,
    }


def login_api(username: str, password: str, ip: str = "0.0.0.0"):
    """
    Método para autenticar a un usuario en el sistema.
    :param username: Nombre de usuario.
    :param password: Contraseña del usuario.
    :param ip: IP del cliente que solicita la autenticación.
    :return: Diccionario con información del usuario si la autenticación es exitosa, None en caso contrario.
    """
    try:
        logger.info("Solicitud de autenticación para %s desde %s", username, ip)
        get_user = __usuarios.get_usuario_adm(usuario=username)

        if len(get_user) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        else:
            get_user = get_user[0]

        try:
            contrasena = hashlib.sha512(str(password).encode("UTF-8")).hexdigest().upper()
            user_info = __pkg_ci.autenticar_administrativo(usuario=username.upper(), contrasena=contrasena)
            if 'RETORNO_FUNCION' in user_info:
                if user_info["RETORNO_FUNCION"] == 1:
                    user_data = {
                        "username": username,
                        "email": get_user.get("Gmail"),
                    }

                    token = create_access_token(data=user_data)
                    refresh_token = create_refresh_token(data=user_data)
                    _register_refresh_token(refresh_token)
                    return _token_response(token, refresh_token, username, get_user.get("Gmail"))
                else:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                    )

            if 'OOPS' in user_info:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credenciales inválidas",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        except:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Credenciales inválidas",
                headers={"WWW-Authenticate": "Bearer"},
            )

    except Exception as e:
        # Manejo de errores y logging
        print(f"Error during authentication: {e}")
        return None


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
    email = payload.get("email", "")
    user_data = {"username": username, "email": email}
    logger.info("Renovación de token para %s desde %s", username, ip)
    access_token = create_access_token(data=user_data)
    new_refresh_token = create_refresh_token(data=user_data)
    _revoke_refresh_token(payload)
    _register_refresh_token(new_refresh_token)
    return _token_response(access_token, new_refresh_token, username, email)


def logout(refresh_token: str) -> None:
    """Revoca un refresh token sin revelar si era válido o no."""
    payload = decode_refresh_token(refresh_token)
    if payload:
        _revoke_refresh_token(payload)


async def get_current_user(token: str = Depends(__oauth2_scheme)) -> dict:
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

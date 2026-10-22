import hashlib

from oracleug.models.pkg_ci import PkgCi
from oracleug.scripts.usuarios import Usuarios
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from oracleug.security import create_access_token, decode_access_token
import logging

logger = logging.getLogger(__name__)

__pkg_ci = PkgCi()
__usuarios = Usuarios()
__oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def login_api(username: str, password: str):
    """
    Método para autenticar a un usuario en el sistema.
    :param username: Nombre de usuario.
    :param password: Contraseña del usuario.
    :return: Diccionario con información del usuario si la autenticación es exitosa, None en caso contrario.
    """
    try:
        get_user = __usuarios.get_usuario_adm(usuario=username)

        if len(get_user) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuario no encontrado",
            )
        else:
            get_user = get_user[0]

        try:
            contrasena = hashlib.sha512(password.encode()).hexdigest().upper()
            user_info = __pkg_ci.autenticar_administrativo(usuario=username.upper(), contrasena=contrasena)
            if 'RETORNO_FUNCION' in user_info:
                if user_info["RETORNO_FUNCION"] == 1:
                    user_data = {
                        "username": username,
                        "email": get_user.get("Gmail"),
                    }
                    print(f"Datos del usuario para token: {user_data}")

                    token = create_access_token(data=user_data)
                    return {"access_token": token, "token_type": "bearer", "username": username,
                            "email": get_user.get("Gmail")}
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

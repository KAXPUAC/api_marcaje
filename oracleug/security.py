from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import jwt, JWTError
from oracleug.oracle_settings import OracleSettings

settings = OracleSettings()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
            expires_delta or timedelta(minutes=settings.get_access_token_expire_minutes())
    )
    to_encode.update({"exp": expire, "token_type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.get_secret_key(), algorithm=settings.get_algorithm())
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.get_refresh_token_expire_days())
    )
    to_encode.update({"exp": expire, "token_type": "refresh"})
    return jwt.encode(to_encode, settings.get_secret_key(), algorithm=settings.get_algorithm())


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.get_secret_key(), algorithms=[settings.get_algorithm()])
        if payload.get("token_type", "access") != "access":
            return None
        return payload
    except JWTError:
        return None


def decode_refresh_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.get_secret_key(), algorithms=[settings.get_algorithm()])
        if payload.get("token_type") != "refresh":
            return None
        return payload
    except JWTError:
        return None

import time
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, status


@dataclass
class LivenessSession:
    session_id: str
    owner: Optional[str]
    flow: str
    expires_at: float
    used: bool = False


class LivenessSessionService:
    """Control local de sesiones Face Liveness.

    Debe reemplazarse por Redis u Oracle cuando la API utilice varias
    instancias o workers independientes.
    """

    _sessions: dict[str, LivenessSession] = {}

    @classmethod
    def register(cls, session_id: str, owner: Optional[str], flow: str, ttl: int) -> None:
        cls._cleanup()
        cls._sessions[session_id] = LivenessSession(
            session_id=session_id,
            owner=owner,
            flow=flow,
            expires_at=time.time() + ttl,
        )

    @classmethod
    def consume(cls, session_id: str, flow: str, owner: Optional[str] = None) -> LivenessSession:
        cls._cleanup()
        session = cls._sessions.get(session_id)
        if session is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sesión de liveness inexistente o expirada",
            )
        if session.used:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="La sesión de liveness ya fue utilizada",
            )
        if session.flow not in ("generic", flow):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La sesión no corresponde al flujo solicitado",
            )
        if session.owner and session.owner != owner:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="La sesión de liveness pertenece a otro operador",
            )
        session.used = True
        return session

    @classmethod
    def _cleanup(cls) -> None:
        now = time.time()
        expired = [key for key, value in cls._sessions.items() if value.expires_at <= now]
        for key in expired:
            del cls._sessions[key]

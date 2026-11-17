import time
from dataclasses import dataclass
from typing import Optional

from fastapi import HTTPException, status
from services.sqlite_store import sqlite_store


@dataclass
class LivenessSession:
    session_id: str
    owner: Optional[str]
    flow: str
    expires_at: float
    used: bool = False


class LivenessSessionService:
    """Control persistente de sesiones Face Liveness mediante SQLite."""

    @classmethod
    def register(cls, session_id: str, owner: Optional[str], flow: str, ttl: int) -> None:
        sqlite_store.register_liveness_session(
            session_id=session_id,
            owner=owner,
            flow=flow,
            expires_at=time.time() + ttl,
        )

    @classmethod
    def consume(cls, session_id: str, flow: str, owner: Optional[str] = None) -> LivenessSession:
        row = sqlite_store.consume_liveness_session(session_id)
        session = (
            LivenessSession(
                session_id=row["session_id"],
                owner=row["owner"],
                flow=row["flow"],
                expires_at=row["expires_at"],
                used=bool(row["used"]),
            )
            if row is not None
            else None
        )
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
        return session

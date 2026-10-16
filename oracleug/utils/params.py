from typing import Any
import datetime
import oracledb


def _parse_date(value: Any):
    """Convierte a datetime/date. Acepta objeto date/datetime o string DD/MM/YYYY[THH:MM[:SS]]."""
    if isinstance(value, datetime.datetime):
        return value
    if isinstance(value, datetime.date):
        return value
    if not value:
        return datetime.datetime.now()
    text = str(value)
    if "T" in text:
        date_part, time_part = text.split("T", 1)
        d, m, y = (int(x) for x in date_part.split("/"))
        hh, mm, *rest = time_part.split(":")
        ss = int(rest[0]) if rest else 0
        return datetime.datetime(y, m, d, hh, mm, ss)
    d, m, y = (int(x) for x in text.split("/"))
    return datetime.date(y, m, d)


def _to_int(value: Any):
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _to_float(value: Any):
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _to_str(value: Any):
    return None if value is None else str(value)


# ODBType -> (tipo oracledb, convertidor)
_TYPE_MAP = {
    "VARCHAR2": (oracledb.DB_TYPE_VARCHAR, _to_str),
    "NUMBER": (oracledb.DB_TYPE_NUMBER, _to_float),
    "INTEGER": (oracledb.DB_TYPE_NUMBER, _to_int),
    "CURSOR": (oracledb.DB_TYPE_CURSOR, lambda v: v),
    "DATE": (oracledb.DB_TYPE_DATE, _parse_date),
    "BLOB": (oracledb.DB_TYPE_BLOB, lambda v: v),
    "PSQLCODE": (oracledb.DB_TYPE_VARCHAR, _to_str),
    "ARRAYVARCHAR2": (oracledb.DB_TYPE_VARCHAR, _to_str),
}


def params(pnombre: str, pvalor: Any, ptipo: str, direc: str = "IN") -> dict:
    key = str(ptipo).upper()
    ora_type, converter = _TYPE_MAP.get(key, (oracledb.DB_TYPE_VARCHAR, _to_str))
    return {
        "nombre": pnombre,
        "valor": converter(pvalor),
        "tipo": ora_type,
        "direccion": direc,
    }

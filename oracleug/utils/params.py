from typing import Any
import datetime
import oracledb


def new_param(pnombre: str, pvalor: Any, ptipo: str, pdireccion: str):
    return {
        'nombre': pnombre,
        'valor': pvalor,
        'tipo': ptipo,
        'direccion': pdireccion
    }


def params(pnombre: str, pvalor: Any, ptipo: str, direc: str = 'IN'):
    ora_type = oracledb.DB_TYPE_VARCHAR
    py_type = str
    t_param = str(ptipo).lower()
    param = {
        "nombre": pnombre,
        "valor": pvalor,
        "tipo": ora_type,
        "tpy": py_type,
        "direccion": direc
    }
    if t_param == 'date':
        param['tipo'] = oracledb.DB_TYPE_DATE
        date_values = pvalor.split("T")
        if len(date_values) == 2:
            date = date_values[0].split("/")
            hours = date_values[1].split(":")
            param['valor'] = datetime.datetime(int(date[0]), int(date[1]), int(date[2]), int(hours[0]), int(hours[1]))
        elif len(date_values) == 1:
            date = date_values[0].split("/")
            param['valor'] = datetime.date(int(date[0]), int(date[1]), int(date[2]))
        else:
            param['valor'] = datetime.datetime.now()
    elif t_param == 'cursor':
        param['tipo'] = oracledb.DB_TYPE_CURSOR
    elif t_param == 'int':
        param['tipo'] = oracledb.DB_TYPE_NUMBER
        try:
            param['valor'] = int(pvalor) if pvalor else None
        except ValueError:
            param['valor'] = None
        param['tpy'] = int
    elif t_param == 'decimal' or t_param == 'number':
        param['tipo'] = oracledb.DB_TYPE_NUMBER
        try:
            param['valor'] = float(pvalor) if pvalor else None
        except ValueError:
            param['valor'] = None
        param['tpy'] = float
    else:
        param['tipo'] = ora_type
        param['valor'] = str(param['valor'])
    return param

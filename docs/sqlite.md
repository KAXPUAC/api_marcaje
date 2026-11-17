# Operación de SQLite

La aplicación utiliza dos volúmenes Docker:

- `api_sqlite`: base activa en `/data/api_marcaje.sqlite3`.
- `api_sqlite_backups`: respaldos en `/backups`.

## Crear un respaldo

Con el contenedor activo:

```bash
docker compose exec api python scripts/backup_sqlite.py
```

El script utiliza la API de backup de SQLite, ejecuta `integrity_check`, conserva
los últimos siete respaldos y limita sus permisos a `0600`.

La retención se puede cambiar con:

```env
SQLITE_BACKUP_RETENTION=14
```

## Restaurar un respaldo

1. Detener la API para evitar escrituras:

```bash
docker compose stop api
```

2. Copiar el respaldo al volumen de datos. Por ejemplo, usando un contenedor
   temporal:

```bash
docker run --rm \
  -v api_marcaje_api_sqlite:/data \
  -v "$PWD/backups:/backups:ro" \
  alpine sh -c \
  'cp /backups/api_marcaje-YYYYMMDDTHHMMSSZ.sqlite3 /data/api_marcaje.sqlite3'
```

3. Iniciar nuevamente la API:

```bash
docker compose start api
```

El endpoint `GET /health` verifica la integridad rápida de SQLite y devuelve
`sqlite: ok` cuando la base está disponible.

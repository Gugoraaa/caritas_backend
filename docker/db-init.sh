#!/bin/sh
# Espera a que SQL Server acepte consultas, crea la base "caritas" y le aplica
# los .sql de db/ en tres pasos, cada uno con su propia condicion:
#
#   db/schema/*.sql     estructura       solo si la base no tiene ninguna tabla
#   db/seed/*.sql       datos mock       solo si no hay donantes (ver DB_SEED)
#   db/bootstrap/*.sql  usuario admin    siempre (los scripts son idempotentes)
#
# Dentro de cada carpeta los archivos se aplican en orden alfabetico, por eso
# van numerados (01_, 02_, ...).
#
# DB_SEED controla el paso de datos mock:
#   auto  (default)  carga los mock solo si la tabla Donantes esta vacia
#   force            los recarga siempre (el script mock borra y reinserta)
#   skip             no los carga
set -eu

# sqlcmd 18 cambio de ruta y exige -C para aceptar el certificado autofirmado
# del contenedor; sqlcmd 17 no conoce esa bandera. Soportamos las dos imagenes.
if [ -x /opt/mssql-tools18/bin/sqlcmd ]; then
    SQLCMD=/opt/mssql-tools18/bin/sqlcmd
    TLS_ARGS="-C"
elif [ -x /opt/mssql-tools/bin/sqlcmd ]; then
    SQLCMD=/opt/mssql-tools/bin/sqlcmd
    TLS_ARGS=""
else
    echo "No se encontro sqlcmd en la imagen." >&2
    exit 1
fi

HOST="${DB_HOST:-sqlserver}"
PORT="${DB_PORT:-1433}"
USER="${DB_USER:-sa}"
NAME="${DB_NAME:-caritas}"
SCHEMA_DIR="${SCHEMA_DIR:-/schema}"
WAIT_ATTEMPTS="${WAIT_ATTEMPTS:-60}"
DB_SEED="${DB_SEED:-auto}"

: "${DB_PASSWORD:?falta la variable de entorno DB_PASSWORD}"

# Los .sql son UTF-8 sin BOM y traen acentos (María, Rehabilitación, ...).
# sqlcmd no los lee como UTF-8 salvo que se le diga con -f 65001; abajo se
# comprueba que la version instalada acepte la bandera antes de usarla.
CODEPAGE_ARGS=""

# -b: cortar con exit != 0 ante cualquier error de SQL.
# -I: QUOTED_IDENTIFIER ON, que el esquema usa identificadores entre comillas.
sql() {
    # shellcheck disable=SC2086
    "$SQLCMD" -S "$HOST,$PORT" -U "$USER" -P "$DB_PASSWORD" \
        $TLS_ARGS $CODEPAGE_ARGS -b -I -l 10 "$@"
}

# Devuelve un unico valor escalar, sin encabezados ni espacios.
scalar() {
    sql -d "$NAME" -h -1 -W -Q "SET NOCOUNT ON; $1" | tr -d '[:space:]'
}

# Aplica todos los .sql de una carpeta, en orden alfabetico. Falla si la
# carpeta no existe o esta vacia: eso significa que el volumen ./db no quedo
# montado, y arrancar la API contra una base a medias es peor que cortar aca.
apply_dir() {
    dir="$SCHEMA_DIR/$1"
    if [ ! -d "$dir" ]; then
        echo "No existe $dir. Revisa que el volumen ./db este montado." >&2
        return 1
    fi

    applied=0
    for file in "$dir"/*.sql; do
        [ -f "$file" ] || continue
        echo "  -> $(basename "$file")"
        sql -d "$NAME" -i "$file"
        applied=$((applied + 1))
    done

    if [ "$applied" -eq 0 ]; then
        echo "No se encontro ningun .sql en $dir." >&2
        return 1
    fi
    return 0
}

echo "Esperando a SQL Server en $HOST,$PORT ..."
attempt=1
while [ "$attempt" -le "$WAIT_ATTEMPTS" ]; do
    if sql -Q "SELECT 1" >/dev/null 2>&1; then
        break
    fi
    if [ "$attempt" -eq "$WAIT_ATTEMPTS" ]; then
        echo "SQL Server no respondio tras $WAIT_ATTEMPTS intentos." >&2
        sql -Q "SELECT 1" >&2 || true
        exit 1
    fi
    attempt=$((attempt + 1))
    sleep 2
done
echo "SQL Server responde."

# shellcheck disable=SC2086
if "$SQLCMD" -S "$HOST,$PORT" -U "$USER" -P "$DB_PASSWORD" $TLS_ARGS \
        -f 65001 -b -l 10 -Q "SELECT 1" >/dev/null 2>&1; then
    CODEPAGE_ARGS="-f 65001"
    echo "sqlcmd leera los .sql como UTF-8."
else
    echo "Aviso: este sqlcmd no acepta '-f 65001'; los acentos de los .sql" >&2
    echo "pueden quedar mal codificados en la base." >&2
fi

sql -Q "IF DB_ID(N'$NAME') IS NULL CREATE DATABASE [$NAME];"

# --- 1. Esquema -------------------------------------------------------------
tables=$(scalar "SELECT COUNT(*) FROM sys.tables;")
if [ "$tables" = "0" ]; then
    echo "La base '$NAME' esta vacia: aplicando esquema."
    apply_dir schema
else
    echo "La base '$NAME' ya tiene $tables tabla(s): no se aplica el esquema."
fi

# --- 2. Datos mock ----------------------------------------------------------
# Se cuenta con sys.partitions para no romper si la tabla todavia no existe.
donantes=$(scalar "SELECT ISNULL(SUM(p.rows), 0) FROM sys.partitions p WHERE p.object_id = OBJECT_ID(N'dbo.Donantes') AND p.index_id IN (0, 1);")

case "$DB_SEED" in
    skip)
        echo "DB_SEED=skip: no se cargan los datos mock."
        ;;
    force)
        echo "DB_SEED=force: recargando los datos mock."
        apply_dir seed
        ;;
    auto)
        if [ "$donantes" = "0" ]; then
            echo "Sin datos: cargando los datos mock."
            apply_dir seed
        else
            echo "Ya hay $donantes donante(s): no se recargan los datos mock (usa DB_SEED=force)."
        fi
        ;;
    *)
        echo "DB_SEED='$DB_SEED' no es un valor valido (auto|force|skip)." >&2
        exit 1
        ;;
esac

# --- 3. Usuario admin -------------------------------------------------------
echo "Asegurando el usuario administrador."
apply_dir bootstrap

echo "Base '$NAME' lista:"
sql -d "$NAME" -Q "SET NOCOUNT ON; SELECT name FROM sys.tables ORDER BY name;"

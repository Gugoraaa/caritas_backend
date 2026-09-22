import logging
from datetime import datetime, timedelta

from ...database import Database
from ...errors import HttpException
from .repository import LlamadaRow, LlamadasRepository

INTERNAL_ERROR = "Error interno del servidor"

DIAS_VERDE = 30
DIAS_AMARILLO = 60

log = logging.getLogger(__name__)


class LlamadasService:
    def __init__(self, database: Database) -> None:
        self.llamadas = LlamadasRepository(database)

    def agendadas_hoy_manana(self, user_id: int) -> list[dict]:
        hoy = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        manana_fin = hoy + timedelta(days=2)

        try:
            rows = self.llamadas.find_agendadas_entre(user_id, hoy, manana_fin)
        except Exception as error:
            log.exception("Fallo la consulta de llamadas agendadas")
            raise HttpException(500, INTERNAL_ERROR) from error

        return [to_public_llamada(row, hoy) for row in rows]


def to_public_llamada(row: LlamadaRow, hoy: datetime) -> dict:
    ultimo_abono_fecha = row["ultimo_abono_fecha"]
    dias_desde_ultimo_abono = (
        (hoy - ultimo_abono_fecha).days if ultimo_abono_fecha else None
    )

    return {
        "donante_id": row["donante_id"],
        "nombre": row["nombre"],
        "apellido_paterno": row["apellido_paterno"],
        "apellido_materno": row["apellido_materno"],
        "llamada_id": row["llamada_id"],
        "llamada_estado": row["llamada_estado"],
        "fecha_agendada": row["fecha_agendada"].isoformat(),
        "dias_desde_ultimo_abono": dias_desde_ultimo_abono,
        "monto_ultimo_abono": row["ultimo_abono_monto"],
        "color": color_for(dias_desde_ultimo_abono),
    }


def color_for(dias: int | None) -> str:
    if dias is not None and dias < DIAS_VERDE:
        return "verde"
    if dias is not None and dias < DIAS_AMARILLO:
        return "amarillo"
    return "rojo"

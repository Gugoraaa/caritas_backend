import logging
from datetime import datetime, timedelta

from ...database import Database
from ...errors import HttpException
from ..donantes.repository import nombre_completo
from .repository import HistorialRepository

INTERNAL_ERROR = "Error interno del servidor"

DIAS_POR_FRECUENCIA = {
    "mensual": 30,
    "trimestral": 90,
    "semestral": 180,
    "anual": 365,
}

VERDE_PALABRAS = ("confirmado", "compromiso")
GRIS_PALABRAS = ("no contesta", "incorrecto", "buzon", "buzón")

log = logging.getLogger(__name__)


def fecha_iso(momento: datetime) -> str:
    """ISO 8601 con sufijo Z; las fechas de la base son naive pero UTC de facto."""
    return momento.isoformat() + "Z"


class HistorialService:
    def __init__(self, database: Database) -> None:
        self.repo = HistorialRepository(database)

    def buscar(self, donante_id: int | None, tipo: str, q: str | None) -> list[dict]:
        try:
            filas = self._buscar(donante_id, tipo, q)
        except HttpException:
            raise
        except Exception as error:
            log.exception("Fallo la consulta del historial")
            raise HttpException(500, INTERNAL_ERROR) from error

        filas.sort(key=lambda fila: fila["fecha"], reverse=True)
        return filas

    def _buscar(self, donante_id: int | None, tipo: str, q: str | None) -> list[dict]:
        filas: list[dict] = []

        if tipo != "llamadas":
            abonos = self.repo.find_abonos(donante_id, q)
            filas += [to_public_abono(row) for row in abonos]
            filas += self._pagos_pendientes(donante_id, q)

        if tipo != "donativos":
            filas += [
                to_public_llamada(row) for row in self.repo.find_llamadas(donante_id, q)
            ]

        return filas

    def _pagos_pendientes(self, donante_id: int | None, q: str | None) -> list[dict]:
        ahora = datetime.now()
        pendientes = []

        for row in self.repo.find_promesas_activas(donante_id, q):
            dias = DIAS_POR_FRECUENCIA.get(row["tipo_frquencia"])
            if dias is None or not row["numero_frequencia"]:
                continue

            desde = row["ultimo_abono_fecha"] or row["fecha_inicio"]
            vencimiento = desde + timedelta(days=dias)
            if vencimiento > ahora:
                continue

            pendientes.append(to_public_pago_pendiente(row, vencimiento))

        return pendientes


def to_public_abono(row: dict) -> dict:
    return {
        "donante_id": row["donante_id"],
        "donante_nombre": nombre_completo(row),
        "tipo": "donativo",
        "fecha": fecha_iso(row["fecha_deposito"]),
        "detalle": row["metodo"] or "Transferencia",
        "monto": float(row["monto"]),
        "cumplida": True,
        "color_punto": "gris",
    }


def to_public_pago_pendiente(row: dict, vencimiento: datetime) -> dict:
    cuota = float(row["monto_objetivo"]) / row["numero_frequencia"]
    return {
        "donante_id": row["donante_id"],
        "donante_nombre": nombre_completo(row),
        "tipo": "donativo",
        "fecha": fecha_iso(vencimiento),
        "detalle": f"Pago pendiente · {row['tipo_frquencia']}",
        "monto": round(cuota, 2),
        "cumplida": False,
        "color_punto": "gris",
    }


def to_public_llamada(row: dict) -> dict:
    detalle = row["resultado_llamado"]
    if row["nota"]:
        detalle += f" · {row['nota']}"

    return {
        "donante_id": row["donante_id"],
        "donante_nombre": nombre_completo(row),
        "tipo": "llamada",
        "fecha": fecha_iso(row["fecha_agendada"]),
        "detalle": detalle,
        "monto": None,
        "cumplida": False,
        "color_punto": color_desde_resultado(row["resultado_llamado"]),
    }


def color_desde_resultado(resultado: str) -> str:
    texto = (resultado or "").lower()
    if any(palabra in texto for palabra in VERDE_PALABRAS):
        return "verde"
    if any(palabra in texto for palabra in GRIS_PALABRAS):
        return "gris"
    return "naranja"

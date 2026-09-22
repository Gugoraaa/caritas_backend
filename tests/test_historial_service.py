from datetime import datetime, timedelta
from decimal import Decimal

from caritas_backend.modules.historial.service import (
    HistorialService,
    color_desde_resultado,
)
from fakes import FakeDatabase

DONANTE = {
    "donante_id": 1,
    "nombre": "María",
    "apellido_paterno": "Guzmán",
    "apellido_materno": "Treviño",
}

ABONO_ROW = {
    **DONANTE,
    "monto": Decimal("1200.00"),
    "fecha_deposito": datetime(2026, 5, 12),
    "metodo": "SPEI",
}

LLAMADA_ROW = {
    **DONANTE,
    "resultado_llamado": "compromiso confirmado",
    "nota": "Dijo que retomaria la transferencia",
    "fecha_agendada": datetime(2026, 6, 6),
}


def promesa_activa(ultimo_abono_hace_dias: int) -> dict:
    return {
        "promesa_id": 10,
        "donante_id": 1,
        **{k: v for k, v in DONANTE.items() if k != "donante_id"},
        "monto_objetivo": Decimal("6000.00"),
        "fecha_inicio": datetime(2025, 1, 1),
        "numero_frequencia": 12,
        "tipo_frquencia": "mensual",
        "ultimo_abono_fecha": datetime.now() - timedelta(days=ultimo_abono_hace_dias),
    }


def test_buscar_todos_combina_abonos_pendientes_y_llamadas():
    database = FakeDatabase(
        {
            "a.metodo": [ABONO_ROW],
            "AS promesa_id": [promesa_activa(ultimo_abono_hace_dias=45)],
            "FROM Llamadas l": [LLAMADA_ROW],
        }
    )
    service = HistorialService(database)

    filas = service.buscar(donante_id=1, tipo="todos", q=None)

    tipos_detalle = [(f["tipo"], f["cumplida"]) for f in filas]
    assert ("donativo", True) in tipos_detalle  # abono real
    assert ("donativo", False) in tipos_detalle  # cuota vencida
    assert ("llamada", False) in tipos_detalle
    assert len(filas) == 3


def test_abono_real_es_siempre_cumplida_y_verde_en_monto():
    database = FakeDatabase(
        {"a.metodo": [ABONO_ROW], "AS promesa_id": [], "FROM Llamadas l": []}
    )
    service = HistorialService(database)

    [fila] = service.buscar(donante_id=1, tipo="donativos", q=None)

    assert fila["cumplida"] is True
    assert fila["monto"] == 1200.0
    assert fila["detalle"] == "SPEI"
    assert fila["color_punto"] == "gris"


def test_promesa_con_ultimo_abono_reciente_no_genera_pendiente():
    database = FakeDatabase(
        {
            "a.metodo": [],
            "AS promesa_id": [promesa_activa(ultimo_abono_hace_dias=5)],
            "FROM Llamadas l": [],
        }
    )
    service = HistorialService(database)

    filas = service.buscar(donante_id=1, tipo="donativos", q=None)

    assert filas == []


def test_promesa_vencida_genera_pago_pendiente_con_cuota_prorrateada():
    database = FakeDatabase(
        {
            "a.metodo": [],
            "AS promesa_id": [promesa_activa(ultimo_abono_hace_dias=45)],
            "FROM Llamadas l": [],
        }
    )
    service = HistorialService(database)

    [fila] = service.buscar(donante_id=1, tipo="donativos", q=None)

    assert fila["cumplida"] is False
    assert fila["monto"] == 500.0  # 6000 / 12 cuotas
    assert "Pago pendiente" in fila["detalle"]


def test_tipo_llamadas_excluye_donativos_y_pendientes():
    database = FakeDatabase(
        {
            "a.metodo": [ABONO_ROW],
            "AS promesa_id": [promesa_activa(ultimo_abono_hace_dias=45)],
            "FROM Llamadas l": [LLAMADA_ROW],
        }
    )
    service = HistorialService(database)

    filas = service.buscar(donante_id=1, tipo="llamadas", q=None)

    assert len(filas) == 1
    assert filas[0]["tipo"] == "llamada"


def test_llamada_incluye_nota_en_el_detalle():
    database = FakeDatabase(
        {"a.metodo": [], "AS promesa_id": [], "FROM Llamadas l": [LLAMADA_ROW]}
    )
    service = HistorialService(database)

    [fila] = service.buscar(donante_id=1, tipo="llamadas", q=None)

    assert (
        fila["detalle"] == "compromiso confirmado · Dijo que retomaria la transferencia"
    )
    assert fila["color_punto"] == "verde"


def test_color_desde_resultado():
    assert color_desde_resultado("compromiso confirmado") == "verde"
    assert color_desde_resultado("Donativo Confirmado") == "verde"
    assert color_desde_resultado("no contesta") == "gris"
    assert color_desde_resultado("numero incorrecto") == "gris"
    assert color_desde_resultado("solicita volver a llamar") == "naranja"

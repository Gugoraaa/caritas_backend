from decimal import Decimal

import pytest

from caritas_backend.modules.causas.labels import (
    NOMBRE_CORTO_MAX,
    build_clave,
    build_nombre_corto,
)
from caritas_backend.modules.causas.service import CausaService

# Los 8 titulos del seed mock.
SEED_TITLES = [
    ("Despensas para familias vulnerables", "DF", "Despensas"),
    ("Becas escolares ciclo 2026-2027", "BE", "Becas escolares"),
    ("Rehabilitación del comedor comunitario", "RC", "Rehabilitación"),
    ("Apoyo a damnificados por inundaciones", "AD", "Apoyo a damnificados"),
    ("Medicamentos para adultos mayores", "MA", "Medicamentos"),
    ("Construcción de aulas rurales", "CA", "Construcción"),
    ("Campaña de invierno: cobijas y abrigos", "CI", "Campaña de invierno"),
    ("Equipamiento de casa hogar", "EC", "Equipamiento de casa"),
]


@pytest.mark.parametrize(("titulo", "clave", "nombre_corto"), SEED_TITLES)
def test_seed_titles(titulo, clave, nombre_corto):
    assert build_clave(titulo) == clave
    assert build_nombre_corto(titulo) == nombre_corto


@pytest.mark.parametrize(
    ("titulo", "clave"),
    [
        ("Comedor Comunitario San Bernabé", "CC"),
        ("La Casa Hogar Santa Clara", "CH"),
        ("Óbolo único", "OU"),
        ("Ñandú", "NA"),
        ("Comedor", "CO"),
        ("Becas 2026", "BE"),
        ("de la y", "DE"),
        ("2026", "20"),
    ],
)
def test_clave(titulo, clave):
    assert build_clave(titulo) == clave


@pytest.mark.parametrize(
    ("titulo", "nombre_corto"),
    [
        ("Comedor Comunitario San Bernabé", "Comedor Comunitario"),
        ("Para las familias del norte", "familias del norte"),
        ("Comedor", "Comedor"),
        ("Supercalifragilisticoespialidoso", "Supercalifragilisticoespialidoso"),
        ("Becas, útiles y uniformes", "Becas útiles"),
        ("de la y", "de la y"),
    ],
)
def test_nombre_corto(titulo, nombre_corto):
    assert build_nombre_corto(titulo) == nombre_corto


def test_nombre_corto_never_cuts_words():
    for titulo, _, _ in SEED_TITLES:
        nombre_corto = build_nombre_corto(titulo)
        assert titulo.startswith(nombre_corto)
        assert len(nombre_corto) <= NOMBRE_CORTO_MAX


class FakeCausaRepository:
    ROW = {
        "id": 3,
        "titulo": "Rehabilitación del comedor comunitario",
        "descripcion": None,
        "monto_objetivo": Decimal("110000.00"),
        "beneficiario": None,
        "responsable": None,
        "lugar": None,
        "fecha_fin": None,
        "monto_recaudado": Decimal("0.00"),
    }

    def find_all(self):
        return [self.ROW]

    def find_by_id(self, causa_id):
        return self.ROW


def make_service():
    service = CausaService.__new__(CausaService)
    service.causas = FakeCausaRepository()
    return service


def test_list_and_detail_include_labels():
    service = make_service()
    expected = {
        **FakeCausaRepository.ROW,
        "clave": "RC",
        "nombre_corto": "Rehabilitación",
    }
    assert service.list_all() == [expected]
    assert service.get_detail(3) == expected

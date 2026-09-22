from caritas_backend.modules.donantes.service import DonantesService
from fakes import FakeDatabase

DONANTES_ROWS = [
    {
        "id": 1,
        "nombre": "María",
        "apellido_paterno": "Guzmán",
        "apellido_materno": "Treviño",
    },
    {"id": 2, "nombre": "Jorge", "apellido_paterno": None, "apellido_materno": None},
]


def test_list_donantes_arma_nombre_completo():
    database = FakeDatabase({"FROM Donantes": DONANTES_ROWS})
    service = DonantesService(database)

    donantes = service.list_donantes()

    assert donantes == [
        {"id": 1, "nombre": "María Guzmán Treviño"},
        {"id": 2, "nombre": "Jorge"},
    ]

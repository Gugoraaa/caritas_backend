"""Static OpenAPI 3.0 spec for the API, served under /docs."""

# Los montos salen de columnas decimal y Flask los serializa como string
# ("12345.00"), no como numero.
DECIMAL = {"type": "string", "format": "decimal", "example": "12345.00"}
NULLABLE_DECIMAL = {**DECIMAL, "nullable": True}

# Las fechas que arma el codigo son ISO 8601 sin zona: "2026-10-17T12:00:00".
LOCAL_DATE_TIME = {
    "type": "string",
    "format": "date-time",
    "description": "ISO 8601 sin zona horaria (hora local de la base)",
    "example": "2026-10-17T12:00:00",
}

ERROR_SCHEMA = {
    "type": "object",
    "properties": {
        "message": {
            "oneOf": [
                {"type": "string"},
                {"type": "array", "items": {"type": "string"}},
            ]
        },
        "error": {"type": "string"},
        "statusCode": {"type": "integer"},
    },
}

USER_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "name": {"type": "string"},
        "email": {"type": "string"},
        "role": {"type": "string"},
    },
}

RISK_SCHEMA = {
    "type": "object",
    "properties": {
        "level": {"type": "string", "enum": ["green", "yellow", "red"]},
        "months_without_donating": {"type": "integer", "nullable": True},
        "last_donation_at": {**LOCAL_DATE_TIME, "nullable": True},
    },
}

DONOR_DETAIL_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "full_name": {"type": "string"},
        "initials": {"type": "string"},
        "email": {"type": "string", "nullable": True},
        "phone": {"type": "string", "nullable": True},
        "neighborhood": {"type": "string", "nullable": True},
        "age": {"type": "integer", "nullable": True},
        "years_as_donor": {"type": "integer"},
        "risk": RISK_SCHEMA,
        "contribution": {
            **NULLABLE_DECIMAL,
            "description": "Monto del ultimo abono del donante",
        },
    },
}

# Etiquetas derivadas del titulo (no son columnas). Ver causas/labels.py.
CAUSA_LABELS = {
    "clave": {
        "type": "string",
        "description": (
            "2 letras en mayusculas: iniciales de las 2 primeras palabras "
            "significativas del titulo, sin acentos e ignorando conectores "
            "(de, del, la, para, y...). Con una sola palabra, sus 2 primeras "
            "letras. No es unica."
        ),
        "example": "RC",
    },
    "nombre_corto": {
        "type": "string",
        "description": (
            "Titulo hasta la 2a palabra significativa si cabe en 20 caracteres; "
            "si no, la 1a palabra significativa. Nunca corta palabras."
        ),
        "example": "Becas escolares",
    },
}

CAUSA_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "titulo": {"type": "string"},
        "descripcion": {"type": "string", "nullable": True},
        "monto_objetivo": DECIMAL,
        "beneficiario": {"type": "string", "nullable": True},
        "responsable": {"type": "string", "nullable": True},
        "lugar": {"type": "string", "nullable": True},
        "fecha_fin": {
            "type": "string",
            "nullable": True,
            "description": "Formato RFC 1123, p. ej. 'Mon, 21 Dec 2026 00:00:00 GMT'",
        },
        "monto_recaudado": {
            **DECIMAL,
            "description": "Suma de los abonos de las promesas de la causa",
        },
        **CAUSA_LABELS,
    },
}

CAUSA_INPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "titulo": {"type": "string"},
        "descripcion": {"type": "string", "nullable": True},
        "monto_objetivo": {"type": "number"},
        "beneficiario": {"type": "string", "nullable": True},
        "responsable": {"type": "string", "nullable": True},
        "lugar": {"type": "string", "nullable": True},
        "fecha_fin": {"type": "string", "nullable": True},
    },
}

ADMIN_DONOR_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "full_name": {"type": "string"},
        "initials": {"type": "string"},
        "neighborhood": {"type": "string", "nullable": True},
        "causa": {
            "type": "object",
            "nullable": True,
            "description": (
                "Causa de la promesa principal: la activa mas reciente o, si no "
                "hay, la ultima por fecha_inicio. null si no tiene promesas."
            ),
            "properties": {
                "id": {"type": "integer"},
                "titulo": {"type": "string"},
                **CAUSA_LABELS,
            },
        },
        "last_donation_at": {**LOCAL_DATE_TIME, "nullable": True},
        "last_donation_amount": NULLABLE_DECIMAL,
        "payment_method": {
            "type": "string",
            "enum": ["efectivo", "spei"],
            "nullable": True,
            "description": "Metodo de pago del ultimo abono",
        },
        "risk": {
            "type": "object",
            "properties": {
                "level": {
                    "type": "string",
                    "enum": ["green", "yellow", "red"],
                    "description": "<30 dias green, <60 yellow; si no, red",
                },
                "days_without_donating": {"type": "integer", "nullable": True},
            },
        },
    },
}

SCHEDULED_CALL_SCHEMA = {
    "type": "object",
    "properties": {
        "donor_id": {"type": "integer"},
        "name": {"type": "string"},
        "last_name": {"type": "string", "nullable": True},
        "mother_last_name": {"type": "string", "nullable": True},
        "call_id": {"type": "integer"},
        "call_status": {"type": "string"},
        "scheduled_date": LOCAL_DATE_TIME,
        "days_since_last_payment": {"type": "integer", "nullable": True},
        "latest_payment_amount": NULLABLE_DECIMAL,
        "status_color": {"type": "string", "enum": ["green", "yellow", "red"]},
    },
}

HISTORY_DONOR_SCHEMA = {
    "type": "object",
    "properties": {
        "donor_id": {"type": "integer"},
        "name": {"type": "string"},
        "last_name": {"type": "string", "nullable": True},
        "mother_last_name": {"type": "string", "nullable": True},
    },
}

HISTORY_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "type": {"type": "string", "enum": ["call", "donation"]},
        "donor_id": {"type": "integer"},
        "name": {"type": "string"},
        "last_name": {"type": "string", "nullable": True},
        "mother_last_name": {"type": "string", "nullable": True},
        "date": {**LOCAL_DATE_TIME, "nullable": True},
        "amount": NULLABLE_DECIMAL,
        "status_color": {
            "type": "string",
            "enum": ["green", "red", "blue", "gray", "orange"],
        },
        "call_status": {"type": "string", "nullable": True},
        "purpose": {"type": "string", "nullable": True},
        "result": {"type": "string", "nullable": True},
        "is_paid": {"type": "boolean", "nullable": True},
    },
}

CALL_UPDATE_SCHEMA = {
    "type": "object",
    "required": ["resultado_llamado"],
    "properties": {
        "resultado_llamado": {"type": "string", "minLength": 1},
        "proposito": {"type": "string", "maxLength": 30, "nullable": True},
        "monto_comprometido": {"type": "number", "minimum": 0, "nullable": True},
        "estado": {
            "type": "string",
            "enum": ["completada", "cancelada"],
            "default": "completada",
        },
    },
}

CALL_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "call_id": {"type": "integer"},
        "donor_id": {"type": "integer"},
        "call_status": {"type": "string"},
        "scheduled_date": {**LOCAL_DATE_TIME, "nullable": True},
        "purpose": {"type": "string", "nullable": True},
        "result": {"type": "string"},
        "amount": NULLABLE_DECIMAL,
    },
}

BEARER = [{"bearerAuth": []}]
# Sin header sigue funcionando con ?user_id; con token valido manda el token.
OPTIONAL_BEARER = [{}, {"bearerAuth": []}]

USER_ID_PARAM = {
    "name": "user_id",
    "in": "query",
    "required": False,
    "description": "Obligatorio si no se manda token; si hay token, se ignora",
    "schema": {"type": "integer"},
}

ERROR_RESPONSES = {
    str(code): {
        "description": description,
        "content": {
            "application/json": {"schema": {"$ref": "#/components/schemas/Error"}}
        },
    }
    for code, description in {
        400: "Bad request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not found",
        500: "Internal server error",
    }.items()
}


def build_spec() -> dict:
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Caritas Backend API",
            "version": "1.0.0",
        },
        "components": {
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT",
                }
            },
            "schemas": {
                "Error": ERROR_SCHEMA,
                "User": USER_SCHEMA,
                "Causa": CAUSA_SCHEMA,
                "CausaInput": CAUSA_INPUT_SCHEMA,
                "CallUpdate": CALL_UPDATE_SCHEMA,
                "CallResult": CALL_RESULT_SCHEMA,
                "DonorDetail": DONOR_DETAIL_SCHEMA,
                "AdminDonor": ADMIN_DONOR_SCHEMA,
                "ScheduledCall": SCHEDULED_CALL_SCHEMA,
                "HistoryDonor": HISTORY_DONOR_SCHEMA,
                "HistoryItem": HISTORY_ITEM_SCHEMA,
            }
        },
        "paths": {
            "/login": {
                "post": {
                    "tags": ["auth"],
                    "summary": "Log in with email and password",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "required": ["email", "password"],
                                    "properties": {
                                        "email": {"type": "string", "format": "email"},
                                        "password": {"type": "string"},
                                    },
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Login successful",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "token": {"type": "string"},
                                            "user": {
                                                "$ref": "#/components/schemas/User"
                                            },
                                        },
                                    }
                                }
                            },
                        },
                        "400": ERROR_RESPONSES["400"],
                        "401": ERROR_RESPONSES["401"],
                        "500": ERROR_RESPONSES["500"],
                    },
                }
            },
            "/me": {
                "get": {
                    "tags": ["auth"],
                    "summary": "Usuario del token",
                    "security": BEARER,
                    "responses": {
                        "200": {
                            "description": "Current user",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/User"}
                                }
                            },
                        },
                        "401": ERROR_RESPONSES["401"],
                        "404": ERROR_RESPONSES["404"],
                        "500": ERROR_RESPONSES["500"],
                    },
                }
            },
            "/causas": {
                "get": {
                    "tags": ["causas"],
                    "summary": "List all causas",
                    "responses": {
                        "200": {
                            "description": "Causas",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {"$ref": "#/components/schemas/Causa"},
                                    }
                                }
                            },
                        },
                        "500": ERROR_RESPONSES["500"],
                    },
                },
                "post": {
                    "tags": ["causas"],
                    "summary": "Create a causa",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/CausaInput"}
                            }
                        },
                    },
                    "responses": {
                        "201": {
                            "description": "Causa created",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Causa"}
                                }
                            },
                        },
                        "400": ERROR_RESPONSES["400"],
                        "500": ERROR_RESPONSES["500"],
                    },
                },
            },
            "/causas/{causa_id}": {
                "get": {
                    "tags": ["causas"],
                    "summary": "Get a causa",
                    "parameters": [
                        {
                            "name": "causa_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Causa",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Causa"}
                                }
                            },
                        },
                        "404": ERROR_RESPONSES["404"],
                        "500": ERROR_RESPONSES["500"],
                    },
                },
                "put": {
                    "tags": ["causas"],
                    "summary": "Update a causa",
                    "parameters": [
                        {
                            "name": "causa_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/CausaInput"}
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Causa updated",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/Causa"}
                                }
                            },
                        },
                        "400": ERROR_RESPONSES["400"],
                        "404": ERROR_RESPONSES["404"],
                        "500": ERROR_RESPONSES["500"],
                    },
                },
                "delete": {
                    "tags": ["causas"],
                    "summary": "Delete a causa",
                    "parameters": [
                        {
                            "name": "causa_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "responses": {
                        "204": {"description": "Causa deleted"},
                        "404": ERROR_RESPONSES["404"],
                        "500": ERROR_RESPONSES["500"],
                    },
                },
            },
            "/donors/{donor_id}": {
                "get": {
                    "tags": ["donors"],
                    "summary": "Get donor detail",
                    "parameters": [
                        {
                            "name": "donor_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "responses": {
                        "200": {
                            "description": "Donor detail",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/DonorDetail"
                                    }
                                }
                            },
                        },
                        "404": ERROR_RESPONSES["404"],
                        "500": ERROR_RESPONSES["500"],
                    },
                }
            },
            "/admin/donors": {
                "get": {
                    "tags": ["admin"],
                    "summary": "Donantes con riesgo, para la app de administracion",
                    "description": (
                        "Requiere role admin (sin distinguir mayusculas; se lee de "
                        "Users, no del token). Sin filtros devuelve todos los "
                        "donantes, ordenados por full_name."
                    ),
                    "security": BEARER,
                    "parameters": [
                        {
                            "name": "q",
                            "in": "query",
                            "required": False,
                            "description": (
                                "Busca en nombre completo y colonia, "
                                "sin mayusculas ni acentos"
                            ),
                            "schema": {"type": "string"},
                        },
                        {
                            "name": "risk",
                            "in": "query",
                            "required": False,
                            "schema": {
                                "type": "string",
                                "enum": ["green", "yellow", "red"],
                            },
                        },
                        {
                            "name": "causa_id",
                            "in": "query",
                            "required": False,
                            "description": "Causa de la promesa principal",
                            "schema": {"type": "integer"},
                        },
                        {
                            "name": "metodo",
                            "in": "query",
                            "required": False,
                            "description": "Metodo de pago del ultimo abono",
                            "schema": {"type": "string", "enum": ["efectivo", "spei"]},
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Donantes",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "$ref": "#/components/schemas/AdminDonor"
                                        },
                                    }
                                }
                            },
                        },
                        "400": ERROR_RESPONSES["400"],
                        "401": ERROR_RESPONSES["401"],
                        "403": ERROR_RESPONSES["403"],
                        "500": ERROR_RESPONSES["500"],
                    },
                }
            },
            "/calls/scheduled": {
                "get": {
                    "tags": ["calls"],
                    "security": OPTIONAL_BEARER,
                    "summary": "Obtiene el perfil de los donantes para las llamadas agendadas para hoy y manana",
                    "description": (
                        "Se usa en la pantalla principal de las telemarketinas en donde ven las "
                        "llamadas agendadas para el dia de hoy y manana. Tambien sirve para que "
                        "las telemarketinas vean el semaforo de los donantes y su progreso con "
                        "las llamadas."
                    ),
                    "parameters": [
                        USER_ID_PARAM
                    ],
                    "responses": {
                        "200": {
                            "description": "Scheduled calls",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "$ref": "#/components/schemas/ScheduledCall"
                                        },
                                    }
                                }
                            },
                        },
                        "400": ERROR_RESPONSES["400"],
                        "401": ERROR_RESPONSES["401"],
                        "500": ERROR_RESPONSES["500"],
                    },
                }
            },
            "/calls/{call_id}": {
                "patch": {
                    "tags": ["calls"],
                    "summary": "Registra el resultado de una llamada existente",
                    "description": (
                        "Actualiza la fila de Llamadas (no inserta). Solo el "
                        "responsable de la promesa o un usuario con role 'admin' "
                        "(sin distinguir mayusculas) puede hacerlo. proposito y "
                        "monto_comprometido solo cambian si vienen en el body."
                    ),
                    "security": BEARER,
                    "parameters": [
                        {
                            "name": "call_id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/CallUpdate"}
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Call updated",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/CallResult"
                                    }
                                }
                            },
                        },
                        "400": ERROR_RESPONSES["400"],
                        "401": ERROR_RESPONSES["401"],
                        "403": ERROR_RESPONSES["403"],
                        "404": ERROR_RESPONSES["404"],
                        "500": ERROR_RESPONSES["500"],
                    },
                }
            },
            "/history": {
                "get": {
                    "tags": ["history"],
                    "security": OPTIONAL_BEARER,
                    "summary": "Donation and call history for a user",
                    "parameters": [
                        USER_ID_PARAM,
                        {
                            "name": "donor_id",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "integer"},
                        },
                        {
                            "name": "type",
                            "in": "query",
                            "required": False,
                            "schema": {
                                "type": "string",
                                "enum": ["all", "donations", "calls"],
                                "default": "all",
                            },
                        },
                        {
                            "name": "q",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "History entries",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "$ref": "#/components/schemas/HistoryItem"
                                        },
                                    }
                                }
                            },
                        },
                        "400": ERROR_RESPONSES["400"],
                        "401": ERROR_RESPONSES["401"],
                        "500": ERROR_RESPONSES["500"],
                    },
                }
            },
            "/history/donors": {
                "get": {
                    "tags": ["history"],
                    "security": OPTIONAL_BEARER,
                    "summary": "Donors that appear in a user's history",
                    "parameters": [
                        USER_ID_PARAM
                    ],
                    "responses": {
                        "200": {
                            "description": "History donors",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "array",
                                        "items": {
                                            "$ref": "#/components/schemas/HistoryDonor"
                                        },
                                    }
                                }
                            },
                        },
                        "400": ERROR_RESPONSES["400"],
                        "401": ERROR_RESPONSES["401"],
                        "500": ERROR_RESPONSES["500"],
                    },
                }
            },
        },
    }

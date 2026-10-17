"""Static OpenAPI 3.0 spec for the API, served under /docs."""

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
        "last_donation_at": {"type": "string", "format": "date-time", "nullable": True},
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
        "contribution": {"type": "number", "nullable": True},
    },
}

CAUSA_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "integer"},
        "titulo": {"type": "string"},
        "descripcion": {"type": "string", "nullable": True},
        "monto_objetivo": {"type": "number"},
        "beneficiario": {"type": "string", "nullable": True},
        "responsable": {"type": "string", "nullable": True},
        "lugar": {"type": "string", "nullable": True},
        "fecha_fin": {"type": "string", "format": "date-time", "nullable": True},
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
        "scheduled_date": {"type": "string", "format": "date-time"},
        "days_since_last_payment": {"type": "integer", "nullable": True},
        "latest_payment_amount": {"type": "number", "nullable": True},
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
        "date": {"type": "string", "format": "date-time"},
        "amount": {"type": "number", "nullable": True},
        "status_color": {"type": "string", "enum": ["green", "yellow", "red"]},
        "call_status": {"type": "string", "nullable": True},
        "purpose": {"type": "string", "nullable": True},
        "result": {"type": "string", "nullable": True},
        "is_paid": {"type": "boolean", "nullable": True},
    },
}

REGISTER_CALL_REQUEST_SCHEMA = {
    "type": "object",
    "required": ["llamada_id", "user_id", "resultado"],
    "properties": {
        "llamada_id": {"type": "integer"},
        "user_id": {
            "type": "integer",
            "description": "Usuario que registra; responsable de la promesa nueva.",
        },
        "resultado": {
            "type": "string",
            "enum": [
                "promesa de donativo",
                "volver a llamar",
                "rechazó",
                "solicitar baja",
                "no contestó",
            ],
        },
        "monto_comprometido": {
            "type": "number",
            "description": "Obligatorio para 'promesa de donativo'.",
        },
        "notas": {
            "type": "string",
            "description": "Obligatorio para 'promesa de donativo'.",
        },
        "fecha_seguimiento": {
            "type": "string",
            "format": "date-time",
            "description": "Obligatoria para 'volver a llamar' y 'no contestó'.",
        },
    },
}

REGISTER_CALL_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "llamada_id": {"type": "integer"},
        "estado": {"type": "string", "enum": ["agendada", "completada"]},
        "resultado": {"type": "string"},
        "notas": {"type": "string", "nullable": True},
        "fecha_agendada": {"type": "string", "format": "date-time", "nullable": True},
        "nueva_llamada_id": {"type": "integer", "nullable": True},
        "promesa_id": {"type": "integer", "nullable": True},
    },
}

REGISTER_CALL_RESPONSE_REF = "#/components/schemas/RegisterCallResponse"

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
        404: "Not found",
        409: "Conflict",
        500: "Internal server error",
    }.items()
}

COLLECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "promise_id": {"type": "integer"},
        "donor_id": {"type": "integer"},
        "name": {"type": "string"},
        "last_name": {"type": "string", "nullable": True},
        "mother_last_name": {"type": "string", "nullable": True},
        "phone": {"type": "string", "nullable": True},
        "address": {"type": "string", "nullable": True},
        "interior_number": {"type": "string", "nullable": True},
        "amount": {"type": "string", "example": "300.00"},
        "status": {"type": "string", "enum": ["pendiente", "confirmada"]},
        "collected_at": {"type": "string", "format": "date-time", "nullable": True},
        "abono_id": {"type": "integer", "nullable": True},
    },
}

COLLECTION_REASON_SCHEMA = {
    "type": "object",
    "properties": {
        "code": {"type": "string"},
        "label": {"type": "string"},
    },
}

COLLECTION_REF = "#/components/schemas/Collection"
PROMISE_ID_PARAM = {
    "name": "promise_id",
    "in": "path",
    "required": True,
    "schema": {"type": "integer"},
}


def _collection_response(description: str) -> dict:
    return {
        "description": description,
        "content": {"application/json": {"schema": {"$ref": COLLECTION_REF}}},
    }


COLLECTION_PATHS = {
    "/collections/reasons": {
        "get": {
            "tags": ["collections"],
            "summary": "Motivos de no recoleccion",
            "responses": {
                "200": {
                    "description": "Catalogo de motivos",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "array",
                                "items": {
                                    "$ref": "#/components/schemas/CollectionReason"
                                },
                            }
                        }
                    },
                }
            },
        }
    },
    "/collections/{promise_id}": {
        "get": {
            "tags": ["collections"],
            "summary": "Detalle de la recoleccion de una promesa",
            "parameters": [PROMISE_ID_PARAM],
            "responses": {
                "200": _collection_response("Detalle de la recoleccion"),
                "404": ERROR_RESPONSES["404"],
                "500": ERROR_RESPONSES["500"],
            },
        }
    },
    "/collections/{promise_id}/confirm": {
        "post": {
            "tags": ["collections"],
            "summary": "Confirma la recoleccion y registra el abono",
            "description": (
                "Crea un Abono con la cuota de la promesa (o con monto si se "
                "manda). Solo una confirmacion por promesa al dia."
            ),
            "parameters": [PROMISE_ID_PARAM],
            "requestBody": {
                "required": False,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {"monto": {"type": "number"}},
                        }
                    }
                },
            },
            "responses": {
                "201": _collection_response("Recoleccion confirmada"),
                "400": ERROR_RESPONSES["400"],
                "404": ERROR_RESPONSES["404"],
                "409": ERROR_RESPONSES["409"],
                "500": ERROR_RESPONSES["500"],
            },
        }
    },
    "/collections/{promise_id}/not-collected": {
        "post": {
            "tags": ["collections"],
            "summary": "Motivo de no recoleccion",
            "description": (
                "Valida el motivo. Todavia no se guarda: la base no tiene tabla "
                "de recolecciones, por eso responde 501."
            ),
            "parameters": [PROMISE_ID_PARAM],
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["reason"],
                            "properties": {
                                "reason": {
                                    "type": "string",
                                    "enum": [
                                        "nadie_en_domicilio",
                                        "reprogramar",
                                        "domicilio_incorrecto",
                                        "ya_no_desea_donar",
                                    ],
                                }
                            },
                        }
                    }
                },
            },
            "responses": {
                "400": ERROR_RESPONSES["400"],
                "404": ERROR_RESPONSES["404"],
                "501": {
                    "description": "Motivo valido, pero aun no se puede guardar",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Error"}
                        }
                    },
                },
            },
        }
    },
}


def build_spec() -> dict:
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Caritas Backend API",
            "version": "1.0.0",
        },
        "components": {
            "schemas": {
                "Error": ERROR_SCHEMA,
                "User": USER_SCHEMA,
                "Causa": CAUSA_SCHEMA,
                "DonorDetail": DONOR_DETAIL_SCHEMA,
                "ScheduledCall": SCHEDULED_CALL_SCHEMA,
                "HistoryDonor": HISTORY_DONOR_SCHEMA,
                "HistoryItem": HISTORY_ITEM_SCHEMA,
                "RegisterCallRequest": REGISTER_CALL_REQUEST_SCHEMA,
                "RegisterCallResponse": REGISTER_CALL_RESPONSE_SCHEMA,
                "Collection": COLLECTION_SCHEMA,
                "CollectionReason": COLLECTION_REASON_SCHEMA,
            }
        },
        "paths": {
            **COLLECTION_PATHS,
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
                                "schema": {"$ref": "#/components/schemas/Causa"}
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
                                "schema": {"$ref": "#/components/schemas/Causa"}
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
            "/calls/scheduled": {
                "get": {
                    "tags": ["calls"],
                    "summary": "Obtiene el perfil de los donantes para las llamadas agendadas para hoy y manana",
                    "description": (
                        "Se usa en la pantalla principal de las telemarketinas en donde ven las "
                        "llamadas agendadas para el dia de hoy y manana. Tambien sirve para que "
                        "las telemarketinas vean el semaforo de los donantes y su progreso con "
                        "las llamadas."
                    ),
                    "parameters": [
                        {
                            "name": "user_id",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
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
                        "500": ERROR_RESPONSES["500"],
                    },
                }
            },
            "/registro/llamada": {
                "post": {
                    "tags": ["calls"],
                    "summary": "Registra el resultado de una llamada agendada",
                    "description": (
                        "'no contestó' deja la llamada agendada y la mueve a "
                        "fecha_seguimiento. Los demas resultados la marcan como "
                        "completada. 'volver a llamar' agenda una llamada nueva en "
                        "fecha_seguimiento y 'promesa de donativo' crea una promesa "
                        "unica por monto_comprometido."
                    ),
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/RegisterCallRequest"
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Llamada registrada",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": REGISTER_CALL_RESPONSE_REF}
                                }
                            },
                        },
                        "400": ERROR_RESPONSES["400"],
                        "404": ERROR_RESPONSES["404"],
                        "409": ERROR_RESPONSES["409"],
                        "500": ERROR_RESPONSES["500"],
                    },
                }
            },
            "/history": {
                "get": {
                    "tags": ["history"],
                    "summary": "Donation and call history for a user",
                    "parameters": [
                        {
                            "name": "user_id",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "integer"},
                        },
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
                        "500": ERROR_RESPONSES["500"],
                    },
                }
            },
            "/history/donors": {
                "get": {
                    "tags": ["history"],
                    "summary": "Donors that appear in a user's history",
                    "parameters": [
                        {
                            "name": "user_id",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "integer"},
                        }
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
                        "500": ERROR_RESPONSES["500"],
                    },
                }
            },
        },
    }

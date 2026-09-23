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
            "schemas": {
                "Error": ERROR_SCHEMA,
                "User": USER_SCHEMA,
                "DonorDetail": DONOR_DETAIL_SCHEMA,
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
                    "summary": "Calls scheduled for today and tomorrow",
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

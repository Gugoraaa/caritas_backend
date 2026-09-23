from flask import Blueprint, Response, current_app, jsonify

from ...validation import is_email, is_not_empty, is_string, validate_body

blueprint = Blueprint("auth", __name__)

LOGIN_RULES = {
    "email": [
        (is_email, "must be an email"),
        (is_not_empty, "should not be empty"),
        (is_string, "must be a string"),
    ],
    "password": [
        (is_not_empty, "should not be empty"),
        (is_string, "must be a string"),
    ],
}


@blueprint.post("/login")
@validate_body(LOGIN_RULES)
def login(body: dict) -> Response:
    """Iniciar sesion
    ---
    post:
      summary: Iniciar sesion
      tags:
        - Auth
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [email, password]
              properties:
                email:
                  type: string
                  format: email
                password:
                  type: string
      responses:
        200:
          description: Token de sesion y datos del usuario
          content:
            application/json:
              schema:
                type: object
                properties:
                  token:
                    type: string
                  user:
                    type: object
        400:
          description: Datos invalidos
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Error"
        401:
          description: Credenciales incorrectas
          content:
            application/json:
              schema:
                $ref: "#/components/schemas/Error"
    """
    auth = current_app.extensions["auth"]
    return jsonify(auth.login(body["email"], body["password"]))

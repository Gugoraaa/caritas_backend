import logging

from ...database import Database
from ...errors import HttpException
from ...security import ABSENT_USER_HASH, sign_token, verify_password
from ..users.repository import UserRecord, UsersRepository, to_public_user

INVALID_CREDENTIALS = "Correo o contrasena incorrectos"
INTERNAL_ERROR = "Error interno del servidor"

log = logging.getLogger(__name__)


class AuthService:
    def __init__(self, database: Database, secret: str, expires_in: int) -> None:
        self.users = UsersRepository(database)
        self._secret = secret
        self._expires_in = expires_in

    def login(self, email: str, password: str) -> dict:
        user = self._find_by_email(email)
        password_hash = user["password_hash"] if user else ABSENT_USER_HASH
        password_matches = verify_password(password, password_hash)

        if user is None or not password_matches:
            raise HttpException(401, INVALID_CREDENTIALS)

        return {"token": self._sign(user), "user": to_public_user(user)}

    def _sign(self, user: UserRecord) -> str:
        payload = {"userId": user["id"], "role": user["role"]}
        return sign_token(payload, self._secret, self._expires_in)

    def _find_by_email(self, email: str) -> UserRecord | None:
        try:
            return self.users.find_by_email(email)
        except Exception as error:
            log.exception("Fallo la busqueda del usuario durante el login")
            raise HttpException(500, INTERNAL_ERROR) from error

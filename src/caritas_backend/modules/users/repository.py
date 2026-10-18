from ...database import Database

UserRecord = dict

QUERY = """SELECT id, name, email, password_hash, role
           FROM Users
          WHERE email = %s;"""

BY_ID_QUERY = """SELECT id, name, email, role
                 FROM Users
                WHERE id = %s;"""


class UsersRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def find_by_email(self, email: str) -> UserRecord | None:
        return self._fetch_one(QUERY, email)

    def find_by_id(self, user_id: int) -> UserRecord | None:
        return self._fetch_one(BY_ID_QUERY, user_id)

    def _fetch_one(self, query: str, param: object) -> UserRecord | None:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(query, (param,))
                return cursor.fetchone()
            finally:
                cursor.close()


def to_public_user(user: UserRecord) -> dict:
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "role": user["role"],
    }

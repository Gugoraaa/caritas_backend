from ...database import Database

UserRecord = dict

QUERY = """SELECT id, name, email, password_hash, role
           FROM Users
          WHERE email = %s;"""


class UsersRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def find_by_email(self, email: str) -> UserRecord | None:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(QUERY, (email,))
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

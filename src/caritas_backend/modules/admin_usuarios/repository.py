from ...database import Database

AdminUserRow = dict

# Sin password_hash: al admin solo le interesan id, nombre y rol.
USERS_QUERY = """SELECT id, name, role
                   FROM Users
                  ORDER BY name, id;"""


class AdminUsersRepository:
    def __init__(self, database: Database) -> None:
        self._database = database

    def find_users(self) -> list[AdminUserRow]:
        return self._fetch_all(USERS_QUERY)

    def _fetch_all(self, query: str) -> list[dict]:
        with self._database.connection() as connection:
            cursor = connection.cursor(as_dict=True)
            try:
                cursor.execute(query)
                return cursor.fetchall()
            finally:
                cursor.close()

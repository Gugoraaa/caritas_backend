import atexit
import logging

from dotenv import load_dotenv
from flask import Flask

from .config import get, required
from .database import Database
from .errors import register_error_handlers
from .modules.auth.service import AuthService
from .modules.historial.service import HistoryService
from .modules.llamadas.service import CallsService
from .routes import register_routes
from .security import parse_duration

log = logging.getLogger(__name__)


def create_app() -> Flask:
    load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    app = Flask(__name__)
    app.json.sort_keys = False
    app.json.ensure_ascii = False

    database = Database()
    app.extensions["database"] = database
    expires_in = parse_duration(get("JWT_EXPIRES_IN", "8h"))
    app.extensions["auth"] = AuthService(database, required("JWT_SECRET"), expires_in)
    app.extensions["calls"] = CallsService(database)
    app.extensions["history"] = HistoryService(database)

    register_error_handlers(app)
    register_routes(app)
    atexit.register(database.close)

    try:
        database.connect()
    except Exception as error:
        log.warning("Failed to connect to SQL Server: %s", error)

    return app

import os

from .app import create_app


def main() -> None:
    app = create_app()  
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT") or 3000))


if __name__ == "__main__":
    main()

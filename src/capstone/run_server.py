import uvicorn

from capstone.api.server import create_app
from capstone.storage import BASE_DIR

DEFAULT_DB_DIR = str(BASE_DIR / "data")
app = create_app(db_dir=DEFAULT_DB_DIR, auth_token=None)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)

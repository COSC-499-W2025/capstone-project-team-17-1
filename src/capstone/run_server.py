import uvicorn

from capstone.api.server import create_app

app = create_app(auth_token=None)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8002)

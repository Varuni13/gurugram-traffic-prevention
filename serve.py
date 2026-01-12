from waitress import serve
from server.api import app

if __name__ == "__main__":
    print("starting server")
    serve(app, host="127.0.0.1", port=9110)


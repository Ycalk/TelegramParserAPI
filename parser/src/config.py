import os

class Config:
    SESSION_DIR = os.path.join(os.path.dirname(__file__), "..", "telegram", "sessions")
    TDATA_PATH = os.path.join(os.path.dirname(__file__), "..", "telegram", "tdata")

TORTOISE_ORM = {
    "connections": {
        "default": os.getenv('MYSQL_URL')
    },
    "apps": {
        "models": {
            "models": ["src.telegram.models"],
            "default_connection": "default",
        }
    }
}
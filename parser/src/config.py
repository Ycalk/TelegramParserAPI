import os

class Config:
    SESSION_DIR = os.path.join(os.path.dirname(__file__), "..", "telegram", "sessions")
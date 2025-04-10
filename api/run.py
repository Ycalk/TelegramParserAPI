import os
import uvicorn
from app.main import app
from uuid import uuid4

port = os.getenv('SERVER_PORT', '5000')

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=int(port))
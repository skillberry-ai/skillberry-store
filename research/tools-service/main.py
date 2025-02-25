import logging
import os

import uvicorn

from fast_api.server import create_app
from tools.configure import configure_logging

uvicorn_host = os.getenv('UVICORN_HOST', '0.0.0.0')

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    configure_logging()
    app = create_app()
    logger.info("Starting application")
    uvicorn.run(app, host=uvicorn_host, port=8000)

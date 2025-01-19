import logging
import uvicorn

from fast_api.server import create_app
from tools.configure import configure_logging

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    configure_logging()
    app = create_app()
    logger.info("Starting application")
    uvicorn.run(app, host="0.0.0.0", port=8000)

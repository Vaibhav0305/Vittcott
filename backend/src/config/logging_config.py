import logging
import sys

# Unified logging setup for the backend
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    stream=sys.stdout
)

logger = logging.getLogger("vittcott-backend")

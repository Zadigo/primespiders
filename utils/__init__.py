import logging
import pathlib

import dotenv

# from utils.clients import get_postgres, get_redis

BASE_DIR = pathlib.Path(__file__).parent.parent.absolute()

dotenv.load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# __all__ = [
#     "BASE_DIR",
#     "get_postgres",
#     "get_redis",
# ]

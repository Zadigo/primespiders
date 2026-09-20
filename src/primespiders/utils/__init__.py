import logging
import pathlib

import dotenv

BASE_DIR = pathlib.Path(__file__).parent.parent.absolute()

dotenv.load_dotenv(BASE_DIR / ".env")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(BASE_DIR / "primespiders.log")
    ]
)

logger = logging.getLogger(__name__)


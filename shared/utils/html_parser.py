from bs4 import BeautifulSoup
from bs4.exceptions import FeatureNotFound
from loguru import logger


def parse_markup(html: str) -> BeautifulSoup | None:
    try:
        logger.debug("Parsing HTML...")
        return BeautifulSoup(html, "lxml")
    except FeatureNotFound as e:
        logger.error(f"HTML parser not found: {e}")
        return None
    except TypeError as e:
        logger.error(f"Invalid HTML: {e}")
        return None
    except Exception as e:
        logger.error(f"Error parsing HTML: {e}")
        return None

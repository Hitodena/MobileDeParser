from bs4 import BeautifulSoup
from bs4.exceptions import FeatureNotFound
from loguru import logger

from shared.exceptions.html_exceptions import HTMLParsingError


def parse_markup(html: str) -> BeautifulSoup:
    try:
        logger.bind(service="HTMLParser").debug("Parsing HTML with lxml...")
        return BeautifulSoup(html, "lxml")
    except FeatureNotFound as e:
        logger.bind(
            service="HTMLParser",
            error_type=type(e).__name__,
            error_message=str(e),
        ).warning("lxml parser not available, falling back to html.parser")
        try:
            return BeautifulSoup(html, "html.parser")
        except Exception as fallback_error:
            raise HTMLParsingError(
                f"Both lxml and html.parser failed: {fallback_error}"
            )
    except TypeError as e:
        raise HTMLParsingError(f"Invalid HTML: {e}")
    except Exception as e:
        raise HTMLParsingError(f"Error parsing HTML: {e}")

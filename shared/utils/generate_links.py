import re
from typing import List


def generate_links(
    base_search_url: str, pages: int, items_per_page: int
) -> List[str]:
    url_without_pgn = re.sub(r",pgn:\d+", "", base_search_url)
    url_without_pagination = re.sub(r",pgs:\d+", "", url_without_pgn)

    links = []
    for page in range(1, pages + 1):
        link = f"{url_without_pagination},pgn:{page},pgs:{items_per_page}"
        links.append(link)

    return links

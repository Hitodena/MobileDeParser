from typing import List


def generate_links(
    base_search_url: str, pages: int, items_per_page: int
) -> List[str]:
    return [
        f"{base_search_url},pgn:{page},pgs:{items_per_page}"
        for page in range(1, pages + 1)
    ]

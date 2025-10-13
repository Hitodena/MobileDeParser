import asyncio
import csv
import sys

import aiohttp
from loguru import logger

from core.parsers.mobilede_ru_parser import MobileDeRuParser

url = "https://www.mobile.de/ru/%D1%82%D1%80%D0%B0%D0%BD%D1%81%D0%BF%D0%BE%D1%80%D1%82%D0%BD%D1%8B%D0%B5-%D1%81%D1%80%D0%B5%D0%B4%D1%81%D1%82%D0%B2%D0%B0/%D0%BF%D0%BE%D0%B8%D1%81%D0%BA.html?isSearchRequest=true&ref=quickSearch&s=Car&vc=Car"

logger.remove()
logger.add(
    sys.stderr,
    level="INFO",
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
    " <dim>({extra})</dim>",
)


async def main():
    async with aiohttp.ClientSession() as session:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        }
        async with session.get(url, headers=headers) as response:
            html = await response.text()
            parser = MobileDeRuParser(html, "https://www.mobile.de", url)
            print(parser.parse_for_links())


if __name__ == "__main__":
    asyncio.run(main())

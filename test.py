import asyncio
import sys

import aiohttp
from loguru import logger

from core.parsers.mobilede_ru_parser import MobileDeRuParser

url = "https://www.mobile.de/ru/%D0%90%D0%B2%D1%82%D0%BE%D0%BC%D0%BE%D0%B1%D0%B8%D0%BB%D1%8C/Mercedes-Benz-A-250-e-Kompaktlimousine-AMG/vhc:car,cnt:de,pgn:12,pgs:50,srt:date,sro:desc,frn:2020,frx:2022,prn:10000,prx:60000,ccx:1799,dmg:false,rdv:true,vat:1/pg:vipcar/436847018.html"

logger.remove()
logger.add(
    sys.stderr,
    level="DEBUG",
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
            print(parser.parse_for_data().to_csv_dict())


if __name__ == "__main__":
    asyncio.run(main())

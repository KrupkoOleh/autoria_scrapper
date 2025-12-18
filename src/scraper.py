import asyncio
import os
import re

import aiohttp
from bs4 import BeautifulSoup
from dotenv import load_dotenv

sem = asyncio.Semaphore(2)

load_dotenv()

BASE_URL = os.getenv('SITE_URL')


def clean_price(text):
    return int(re.sub(r"[^\d]", "", text))


async def fetch_html(session, url):
    async with session.get(url) as response:
        response.raise_for_status()
        return await response.text(encoding='utf-8', errors='replace')


def parse_listing_page(soup):
    links = []
    for item in soup.select("section.ticket-item"):
        ad_type = item.get("data-advertisement-type")
        if ad_type == "NewAuto":
            continue
        link_tag = item.select_one("a.m-link-ticket")
        if link_tag and link_tag.get("href"):
            links.append(link_tag["href"])
    return links


async def fetch_car_details(session, car_url):
    async with sem:
        html = await fetch_html(session, car_url)
        soup = BeautifulSoup(html, "html.parser")

        price_tag = soup.select_one("#sidePrice strong")
        if not price_tag:
            return None

        data = {
            "url": car_url,
            "price_usd": clean_price(price_tag.get_text(strip=True)),
        }
        return data


async def parse_page(session, page):
    url = f"{BASE_URL}?page={page}"
    html = await fetch_html(session, url)
    soup = BeautifulSoup(html, "html.parser")

    car_links = parse_listing_page(soup)
    if not car_links:
        print('car_links', car_links)
        return None, None

    tasks = [fetch_car_details(session, link) for link in car_links]
    results = await asyncio.gather(*tasks)
    results = [r for r in results if r is not None]

    next_btn = soup.select_one("a.js-next")
    has_next = next_btn and "disabled" not in next_btn.get("class", [])
    print('has_next', has_next)
    return results, has_next


async def main():
    headers = {"User-Agent": "Mozilla/5.0"}
    all_results = []
    page = 1

    async with aiohttp.ClientSession(headers=headers) as session:
        while True:
            results, has_next = await parse_page(session, page)
            if results:
                all_results.extend(results)

            if not has_next:
                break

            page += 1
            await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
